"""
Finance MCP server for US healthcare revenue cycle operations.

Provides tools for medical coding, claim scrubbing, EDI X12 837P claim
generation/submission, claim status (276/277), remittance (835), and
denial/appeal management. Submissions go to a clearinghouse endpoint when
FINANCE_CLEARINGHOUSE_URL is configured; otherwise they are simulated in
an in-memory sandbox so the workflow can be exercised end-to-end.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests
from mcp.server.fastmcp import FastMCP

from src.core.config import settings
import logfire

logfire.configure()

# Initialize FastMCP server
mcp = FastMCP("Finance-MCP")

DEFAULT_TIMEOUT = settings.fhir_http_timeout
CLEARINGHOUSE_URL = os.getenv("FINANCE_CLEARINGHOUSE_URL", "").strip().rstrip("/")

# Sandbox sender/receiver identifiers for EDI envelopes
SENDER_ID = os.getenv("FINANCE_EDI_SENDER_ID", "HACSUBMITTER")
RECEIVER_ID = os.getenv("FINANCE_EDI_RECEIVER_ID", "CLEARINGHOUSE")

# ---------------------------------------------------------------------------
# In-memory sandbox claim store: claim_id -> claim record with lifecycle state
# ---------------------------------------------------------------------------
_CLAIM_STORE: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Minimal reference data (US context). A production system would call a
# licensed coding API (AMA CPT, CMS HCPCS/ICD-10) or payer fee schedule.
# ---------------------------------------------------------------------------
PROCEDURE_CODES: Dict[str, Dict[str, Any]] = {
    "99213": {"description": "Office outpatient visit, established patient, low complexity", "category": "E/M", "typical_charge": 125.00},
    "99214": {"description": "Office outpatient visit, established patient, moderate complexity", "category": "E/M", "typical_charge": 185.00},
    "99203": {"description": "Office outpatient visit, new patient, low complexity", "category": "E/M", "typical_charge": 175.00},
    "99284": {"description": "Emergency department visit, moderate-high complexity", "category": "E/M", "typical_charge": 450.00},
    "36415": {"description": "Collection of venous blood by venipuncture", "category": "Laboratory", "typical_charge": 25.00},
    "85025": {"description": "Complete blood count (CBC), automated", "category": "Laboratory", "typical_charge": 35.00},
    "93000": {"description": "Electrocardiogram (ECG), 12-lead, with interpretation", "category": "Cardiology", "typical_charge": 75.00},
    "71046": {"description": "Chest X-ray, 2 views", "category": "Radiology", "typical_charge": 150.00},
    "90471": {"description": "Immunization administration, one vaccine", "category": "Immunization", "typical_charge": 40.00},
    "J3420": {"description": "Injection, vitamin B-12 (cyanocobalamin), up to 1000 mcg", "category": "HCPCS Drug", "typical_charge": 20.00},
}

DIAGNOSIS_CODES: Dict[str, str] = {
    "J06.9": "Acute upper respiratory infection, unspecified",
    "R05.9": "Cough, unspecified",
    "R50.9": "Fever, unspecified",
    "M54.50": "Low back pain, unspecified",
    "E11.9": "Type 2 diabetes mellitus without complications",
    "I10": "Essential (primary) hypertension",
    "J02.9": "Acute pharyngitis, unspecified",
    "N39.0": "Urinary tract infection, site not specified",
    "R10.9": "Unspecified abdominal pain",
    "F41.9": "Anxiety disorder, unspecified",
}

# Common CARC (Claim Adjustment Reason Codes) seen on 835 denials
CARC_REASONS: Dict[str, str] = {
    "16": "Claim/service lacks information needed for adjudication",
    "50": "Non-covered services - not deemed a medical necessity",
    "97": "Benefit included in payment/allowance for another service",
    "109": "Claim/service not covered by this payer - send to correct payer",
    "197": "Precertification/authorization/notification absent",
    "204": "Service/equipment/drug not covered under patient's current benefit plan",
    "252": "An attachment/other documentation is required to adjudicate this claim",
    "29": "The time limit for filing has expired",
}

VALID_MODIFIERS = {
    "25", "26", "59", "76", "77", "91", "LT", "RT", "TC", "XE", "XS", "XP", "XU", "GP", "GO", "GN", "KX", "QW", "GA", "GY", "GZ",
}


# ---------------------------------------------------------------------------
# X12 helpers
# ---------------------------------------------------------------------------
def _seg(*elements: str) -> str:
    return "*".join(elements) + "~"


def _fmt_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to CCYYMMDD."""
    return date_str.replace("-", "")


def _fmt_now_ccyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _fmt_now_hhmm() -> str:
    return datetime.now().strftime("%H%M")


# ---------------------------------------------------------------------------
# Tools: Medical coding
# ---------------------------------------------------------------------------
@mcp.tool()
def lookup_procedure_code(code: str) -> Dict[str, Any]:
    """
    Look up a CPT or HCPCS Level II procedure code and get its description
    and typical charge amount.

    Args:
        code: CPT (e.g., '99213') or HCPCS (e.g., 'J3420') code
    """
    entry = PROCEDURE_CODES.get(code.upper())
    if not entry:
        return {"code": code, "valid": False, "message": "Code not found in reference set. Verify against AMA CPT / CMS HCPCS."}
    return {"code": code.upper(), "valid": True, **entry}


@mcp.tool()
def lookup_diagnosis_code(code: str) -> Dict[str, Any]:
    """
    Look up an ICD-10-CM diagnosis code and get its description.

    Args:
        code: ICD-10-CM code (e.g., 'J06.9')
    """
    description = DIAGNOSIS_CODES.get(code.upper())
    if not description:
        return {"code": code, "valid": False, "message": "Code not found in reference set. Verify against ICD-10-CM."}
    return {"code": code.upper(), "valid": True, "description": description}


# ---------------------------------------------------------------------------
# Tools: Claim scrubbing and EDI 837P generation
# ---------------------------------------------------------------------------
@mcp.tool()
def scrub_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a claim before submission (like a clearinghouse claim scrubber).
    Checks coding validity, required identifiers (NPI, Tax ID, member ID),
    charge totals, and diagnosis pointers.

    Args:
        claim: Claim dict with patient, subscriber, payer, provider,
               diagnoses (ICD-10-CM), and service_lines (CPT/HCPCS)
    """
    errors: List[str] = []
    warnings: List[str] = []

    provider = claim.get("provider", {})
    npi = str(provider.get("npi", ""))
    if not (npi.isdigit() and len(npi) == 10):
        errors.append("Provider NPI must be a 10-digit number")
    if not provider.get("tax_id"):
        errors.append("Provider Tax ID (EIN/SSN) is required")

    subscriber = claim.get("subscriber", {})
    if not subscriber.get("member_id"):
        errors.append("Subscriber member ID is required")
    if not claim.get("payer", {}).get("payer_id"):
        errors.append("Payer ID (EDI) is required")

    diagnoses = claim.get("diagnoses", [])
    if not diagnoses:
        errors.append("At least one ICD-10-CM diagnosis code is required")
    for dx in diagnoses:
        if dx.upper() not in DIAGNOSIS_CODES:
            warnings.append(f"Diagnosis {dx} not found in local reference set - verify against ICD-10-CM")

    total_charge = 0.0
    for i, line in enumerate(claim.get("service_lines", []), start=1):
        proc = str(line.get("procedure_code", "")).upper()
        if proc not in PROCEDURE_CODES:
            warnings.append(f"Line {i}: procedure {proc} not in local reference set - verify CPT/HCPCS")
        for mod in line.get("modifiers", []):
            if mod.upper() not in VALID_MODIFIERS:
                errors.append(f"Line {i}: invalid modifier '{mod}'")
        for ptr in line.get("diagnosis_pointers", []):
            if not (1 <= ptr <= len(diagnoses)):
                errors.append(f"Line {i}: diagnosis pointer {ptr} is out of range (1-{len(diagnoses)})")
        charge = float(line.get("charge_amount", 0))
        if charge <= 0:
            errors.append(f"Line {i}: charge amount must be greater than zero")
        total_charge += charge * int(line.get("units", 1))

    return {
        "clean": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_charge": round(total_charge, 2),
        "line_count": len(claim.get("service_lines", [])),
    }


@mcp.tool()
def build_837p(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an EDI X12 5010 837P (professional claim) transaction from a
    validated claim. Returns the raw X12 text plus the claim control number.

    Args:
        claim: Claim dict with claim_id, patient, subscriber, payer,
               provider, diagnoses, and service_lines
    """
    claim_id = claim.get("claim_id") or f"CLM-{uuid.uuid4().hex[:8].upper()}"
    patient = claim.get("patient", {})
    subscriber = claim.get("subscriber", {})
    payer = claim.get("payer", {})
    provider = claim.get("provider", {})
    diagnoses = claim.get("diagnoses", [])
    service_lines = claim.get("service_lines", [])

    total_charge = sum(float(l.get("charge_amount", 0)) * int(l.get("units", 1)) for l in service_lines)

    isa_ctrl = datetime.now().strftime("%y%m%d%H%M")[-9:]
    segments: List[str] = []
    segments.append(_seg(
        "ISA", "00", "          ", "00", "          ",
        "ZZ", SENDER_ID.ljust(15), "ZZ", RECEIVER_ID.ljust(15),
        isa_ctrl[:6], _fmt_now_hhmm(), "^", "00501", isa_ctrl.ljust(9), "0", "P", ":",
    ))
    segments.append(_seg("GS", "HC", SENDER_ID, RECEIVER_ID, _fmt_now_ccyymmdd(), _fmt_now_hhmm(), "1", "X", "005010X222A1"))
    segments.append(_seg("ST", "837", "0001", "005010X222A1"))
    segments.append(_seg("BHT", "0019", "00", claim_id, _fmt_now_ccyymmdd(), _fmt_now_hhmm(), "CH"))

    # 1000A Submitter / 1000B Receiver
    segments.append(_seg("NM1", "41", "2", provider.get("organization_name", "SUBMITTER"), "", "", "", "", "46", SENDER_ID))
    segments.append(_seg("NM1", "40", "2", payer.get("payer_name", "PAYER"), "", "", "", "", "46", payer.get("payer_id", "")))

    # 2000A Billing provider
    segments.append(_seg("HL", "1", "", "20", "1"))
    segments.append(_seg("NM1", "85", "2", provider.get("organization_name", "BILLING PROVIDER"), "", "", "", "", "XX", str(provider.get("npi", ""))))
    addr = provider.get("address") or {}
    if addr:
        segments.append(_seg("N3", addr.get("line1", "")))
        segments.append(_seg("N4", addr.get("city", ""), addr.get("state", ""), addr.get("zip_code", "")))
    segments.append(_seg("REF", "EI", str(provider.get("tax_id", ""))))

    # 2000B Subscriber
    segments.append(_seg("HL", "2", "1", "22", "0"))
    segments.append(_seg("SBR", "P", "18", subscriber.get("group_number", ""), "", "", "", "", "", payer.get("claim_filing_indicator", "CI")))
    segments.append(_seg(
        "NM1", "IL", "1", subscriber.get("last_name", ""), subscriber.get("first_name", ""),
        "", "", "", "MI", subscriber.get("member_id", ""),
    ))
    segments.append(_seg("DMG", "D8", _fmt_date(subscriber.get("date_of_birth", "1900-01-01")), subscriber.get("gender", "U")))

    # 2000C Patient (only when patient differs from subscriber)
    relationship = patient.get("relationship_to_subscriber", "self")
    if relationship != "self":
        segments.append(_seg("HL", "3", "2", "23", "0"))
        segments.append(_seg("PAT", {"spouse": "01", "child": "19", "other": "G8"}.get(relationship, "G8")))
        segments.append(_seg("NM1", "QC", "1", patient.get("last_name", ""), patient.get("first_name", "")))
        segments.append(_seg("DMG", "D8", _fmt_date(patient.get("date_of_birth", "1900-01-01")), patient.get("gender", "U")))

    # 2010AA Payer
    segments.append(_seg("NM1", "PR", "2", payer.get("payer_name", "PAYER"), "", "", "", "", "PI", payer.get("payer_id", "")))

    # 2300 Claim
    segments.append(_seg("CLM", claim_id, f"{total_charge:.2f}", "", "", f"{service_lines[0].get('place_of_service', '11')}:B:1" if service_lines else "11:B:1", "Y", "A", "Y", "Y"))
    if claim.get("prior_authorization"):
        segments.append(_seg("REF", "G1", claim["prior_authorization"]))
    if claim.get("referral_number"):
        segments.append(_seg("REF", "9F", claim["referral_number"]))
    for idx, dx in enumerate(diagnoses[:12]):
        qualifier = "ABK" if idx == 0 else "ABF"
        segments.append(_seg("HI", f"{qualifier}:{dx}"))

    # 2400 Service lines
    for i, line in enumerate(service_lines, start=1):
        proc = str(line.get("procedure_code", "")).upper()
        mods = ":".join(m.upper() for m in line.get("modifiers", [])[:4])
        hcpcs = f"HC:{proc}" + (f":{mods}" if mods else "")
        segments.append(_seg("LX", str(i)))
        segments.append(_seg("SV1", hcpcs, f"{float(line.get('charge_amount', 0)):.2f}", "UN", str(line.get("units", 1)), line.get("place_of_service", "11"), "", ",".join(str(p) for p in line.get("diagnosis_pointers", []))))
        segments.append(_seg("DTP", "472", "D8", _fmt_date(line.get("service_date", datetime.now().strftime("%Y-%m-%d")))))

    seg_count = len(segments) - 2 + 1  # segments inside ST..SE
    segments.append(_seg("SE", str(seg_count + 1), "0001"))
    segments.append(_seg("GE", "1", "1"))
    segments.append(_seg("IEA", "1", isa_ctrl.ljust(9)))

    x12 = "\n".join(segments)
    return {"claim_id": claim_id, "transaction": "837P", "version": "005010X222A1", "x12": x12, "segment_count": len(segments)}


# ---------------------------------------------------------------------------
# Tools: Submission, status, and remittance
# ---------------------------------------------------------------------------
@mcp.tool()
def submit_claim(x12: str, claim_id: str, payer_id: str) -> Dict[str, Any]:
    """
    Submit an EDI 837P transaction to the clearinghouse/payer. Uses the
    configured clearinghouse endpoint when available; otherwise simulates
    acceptance in the sandbox store and queues an adjudication outcome.

    Args:
        x12: Raw X12 837P text (from build_837p)
        claim_id: Claim control number
        payer_id: EDI payer ID
    """
    if CLEARINGHOUSE_URL:
        response = requests.post(
            f"{CLEARINGHOUSE_URL}/claims",
            data=x12,
            headers={"Content-Type": "text/plain"},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        _CLAIM_STORE[claim_id] = {"claim_id": claim_id, "payer_id": payer_id, "status": result.get("status", "submitted"), "x12": x12}
        return {"mode": "clearinghouse", "claim_id": claim_id, "response": result}

    # Sandbox: simulate a 999 acknowledgment and park the claim as accepted
    ack = _seg("ISA", "00", "          ", "00", "          ", "ZZ", RECEIVER_ID.ljust(15), "ZZ", SENDER_ID.ljust(15), _fmt_now_ccyymmdd()[2:], _fmt_now_hhmm(), "^", "00501", "000000001", "0", "P", ":") \
        + _seg("ST", "999", "0001", "005010X231A1") \
        + _seg("AK1", "HC", "1", "005010X222A1") \
        + _seg("AK2", "837", "0001", "005010X222A1") \
        + _seg("IK5", "A") \
        + _seg("AK9", "A", "1", "1", "1") \
        + _seg("SE", "5", "0001") \
        + _seg("GE", "1", "1") \
        + _seg("IEA", "1", "000000001")
    _CLAIM_STORE[claim_id] = {
        "claim_id": claim_id,
        "payer_id": payer_id,
        "status": "accepted",
        "x12": x12,
        "submitted_at": datetime.now().isoformat(),
        "acknowledgment_999": ack,
    }
    return {
        "mode": "sandbox",
        "claim_id": claim_id,
        "status": "accepted",
        "acknowledgment": "999",
        "acknowledgment_x12": ack,
        "message": "Claim accepted by sandbox clearinghouse (999/AK5-A). Poll check_claim_status for adjudication.",
    }


@mcp.tool()
def check_claim_status(claim_id: str) -> Dict[str, Any]:
    """
    Check claim status with the payer (equivalent of an EDI 276/277 claim
    status inquiry/response).

    Args:
        claim_id: Claim control number from submission
    """
    record = _CLAIM_STORE.get(claim_id)
    if not record:
        return {"claim_id": claim_id, "found": False, "message": "Claim not found. Verify the claim control number."}
    status = record.get("status", "accepted")
    status_map = {
        "accepted": ("A2", "Acknowledgement/Receipt - claim received by payer"),
        "in_process": ("P1", "In Process - claim is being adjudicated"),
        "paid": ("F1", "Finalized/Payment - claim paid, see 835 remittance"),
        "denied": ("F4", "Finalized/Denial - claim denied, see 835 remittance"),
    }
    cat, desc = status_map.get(status, ("A1", "Acknowledgement/Receipt"))
    return {"claim_id": claim_id, "found": True, "transaction": "277", "status_category": cat, "status_description": desc, "status": status}


@mcp.tool()
def get_remittance(claim_id: str) -> Dict[str, Any]:
    """
    Retrieve the 835 ERA (Electronic Remittance Advice) for an adjudicated
    claim, including line-level payments and adjustment reason codes.

    Args:
        claim_id: Claim control number
    """
    record = _CLAIM_STORE.get(claim_id)
    if not record:
        return {"claim_id": claim_id, "found": False, "message": "Claim not found."}
    remittance = record.get("remittance")
    if not remittance:
        return {"claim_id": claim_id, "found": True, "status": record.get("status"), "message": "No remittance available yet - claim has not been finalized."}
    return {"claim_id": claim_id, "found": True, "transaction": "835", "remittance": remittance}


@mcp.tool()
def simulate_adjudication(claim_id: str, outcome: str = "paid", denial_code: Optional[str] = None) -> Dict[str, Any]:
    """
    SANDBOX ONLY: move a submitted claim to a final adjudication outcome
    ('paid' or 'denied') and generate the corresponding 835 remittance.
    In production the payer does this; this tool exists to exercise the
    denial/appeal workflow without a live clearinghouse.

    Args:
        claim_id: Claim control number
        outcome: 'paid' or 'denied'
        denial_code: CARC code when outcome is 'denied' (e.g., '197')
    """
    record = _CLAIM_STORE.get(claim_id)
    if not record:
        return {"claim_id": claim_id, "found": False, "message": "Claim not found."}

    if outcome == "denied":
        code = denial_code or "197"
        record["status"] = "denied"
        record["remittance"] = {
            "check_number": None,
            "payment_date": _fmt_now_ccyymmdd(),
            "total_paid": 0.0,
            "claim_status": "denied",
            "adjustment_group": "CO" if code != "197" else "OA",
            "adjustment_reason_code": code,
            "denial_reason": CARC_REASONS.get(code, "See remittance"),
        }
    else:
        record["status"] = "paid"
        record["remittance"] = {
            "check_number": f"EFT{uuid.uuid4().hex[:10].upper()}",
            "payment_date": _fmt_now_ccyymmdd(),
            "total_paid": None,  # populated by payer fee schedule in production
            "claim_status": "paid",
            "adjustment_group": None,
            "adjustment_reason_code": None,
        }
    return {"claim_id": claim_id, "status": record["status"], "remittance": record["remittance"]}


# ---------------------------------------------------------------------------
# Tools: Denials and appeals
# ---------------------------------------------------------------------------
@mcp.tool()
def explain_denial(denial_code: str, remark_codes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Explain a CARC denial code and recommend next steps (correct and
    resubmit vs. appeal).

    Args:
        denial_code: CARC code from the 835 (e.g., '197')
        remark_codes: Optional RARC codes providing more detail
    """
    reason = CARC_REASONS.get(denial_code, "Unknown CARC code - refer to the Washington Publishing Company code list")
    guidance = {
        "16": "Correct the claim with the missing information and resubmit as a corrected claim (frequency code 7).",
        "50": "Gather clinical documentation supporting medical necessity and file a first-level appeal.",
        "97": "Review bundling; if services were distinct, resubmit with appropriate modifier (e.g., 59/X{EPSU}) or appeal.",
        "109": "Verify eligibility and resubmit to the correct payer.",
        "197": "If authorization was obtained, resubmit with the auth number in REF*G1; otherwise appeal with clinical justification.",
        "204": "Verify plan benefits; bill the patient only if an ABN/notice was issued.",
        "252": "Attach the requested documentation and resubmit.",
        "29": "Check timely filing; appeal only with proof of timely submission.",
    }
    return {
        "denial_code": denial_code,
        "reason": reason,
        "remark_codes": remark_codes or [],
        "recommended_action": guidance.get(denial_code, "Review the remittance and payer policy; correct and resubmit or appeal."),
        "appeal_deadline_note": "Most commercial payers allow 90-180 days from the remittance date to appeal; Medicare allows 120 days.",
    }


@mcp.tool()
def generate_appeal_letter(
    claim_id: str,
    payer_name: str,
    patient_name: str,
    denial_code: str,
    rationale: str,
    appeal_level: int = 1,
    supporting_documents: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Draft a professional appeal letter for a denied claim, ready to send to
    the payer's appeals/correspondence address.

    Args:
        claim_id: Denied claim ID
        payer_name: Insurance company name
        patient_name: Patient full name
        denial_code: CARC code being appealed
        rationale: Clinical/administrative rationale for overturning the denial
        appeal_level: Appeal level (1, 2, or 3/external)
        supporting_documents: Documents attached to the appeal
    """
    reason = CARC_REASONS.get(denial_code, "as indicated on the remittance advice")
    docs = supporting_documents or []
    docs_text = "\n".join(f"  - {d}" for d in docs) if docs else "  - None attached"
    today = datetime.now().strftime("%B %d, %Y")

    letter = f"""{today}

{payer_name}
Appeals and Correspondence Department

RE: Appeal Level {appeal_level} - Claim {claim_id}
    Patient: {patient_name}
    Denial Reason (CARC {denial_code}): {reason}

Dear Appeals Reviewer,

We are writing to formally appeal the denial of the above-referenced claim.
After reviewing the remittance advice and the patient's clinical record, we
believe this claim was denied in error for the following reasons:

{rationale}

Supporting documentation enclosed:
{docs_text}

We respectfully request that you reprocess this claim and issue payment in
accordance with the patient's benefit plan and applicable state and federal
regulations (including ERISA Section 503 where applicable). Please respond
within the timeframe required by your plan's appeal procedures.

Sincerely,

Revenue Cycle Department
Health Agents Collective (Finance Agent)
"""
    return {
        "claim_id": claim_id,
        "appeal_level": appeal_level,
        "letter": letter,
        "deadline_note": "Verify the appeal deadline on the remittance; typical windows are 90-180 days (commercial) or 120 days (Medicare).",
    }


@mcp.tool()
def send_payer_correspondence(claim_id: str, payer_name: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send general correspondence to the payer regarding a claim (e.g.,
    records request response, appeal letter, status inquiry follow-up).
    Posts to the clearinghouse correspondence endpoint when configured;
    otherwise records the correspondence in the sandbox store.

    Args:
        claim_id: Related claim ID
        payer_name: Insurance company name
        subject: Correspondence subject line
        body: Correspondence body text
    """
    correspondence = {
        "id": f"CORR-{uuid.uuid4().hex[:8].upper()}",
        "claim_id": claim_id,
        "payer_name": payer_name,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now().isoformat(),
    }
    if CLEARINGHOUSE_URL:
        response = requests.post(
            f"{CLEARINGHOUSE_URL}/correspondence",
            json=correspondence,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return {"mode": "clearinghouse", "correspondence": correspondence, "response": response.json()}

    record = _CLAIM_STORE.setdefault(claim_id, {"claim_id": claim_id, "status": "unknown"})
    record.setdefault("correspondence", []).append(correspondence)
    return {"mode": "sandbox", "correspondence": correspondence, "message": "Correspondence recorded and queued for payer."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
