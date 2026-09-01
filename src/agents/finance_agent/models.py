from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import date


class Address(BaseModel):
    line1: str = Field(..., description="Street address line 1")
    line2: Optional[str] = Field(default=None, description="Street address line 2")
    city: str = Field(..., description="City")
    state: str = Field(..., description="Two-letter US state abbreviation")
    zip_code: str = Field(..., description="US ZIP code (5 or 9 digits)")


class SubscriberInfo(BaseModel):
    """The insured/member on the insurance policy (US context)."""
    first_name: str = Field(..., description="Subscriber's first name")
    last_name: str = Field(..., description="Subscriber's last name")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: str = Field(..., description="M | F | U")
    member_id: str = Field(..., description="Payer-assigned member/subscriber ID")
    group_number: Optional[str] = Field(default=None, description="Employer group number on the policy")
    address: Optional[Address] = Field(default=None, description="Subscriber mailing address")


class PatientInfo(BaseModel):
    """The patient who received services, if different from the subscriber."""
    first_name: str = Field(..., description="Patient's first name")
    last_name: str = Field(..., description="Patient's last name")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: str = Field(..., description="M | F | U")
    relationship_to_subscriber: str = Field(
        default="self",
        description="Relationship code: self | spouse | child | other",
    )
    address: Optional[Address] = Field(default=None, description="Patient mailing address")


class PayerInfo(BaseModel):
    """US insurance payer details."""
    payer_name: str = Field(..., description="Name of the insurance company (e.g., 'Aetna', 'UnitedHealthcare')")
    payer_id: str = Field(..., description="Payer ID used for EDI submissions (clearinghouse payer list ID)")
    plan_type: Optional[str] = Field(default=None, description="Plan type: HMO | PPO | EPO | POS | Medicare | Medicaid")
    claim_filing_indicator: str = Field(
        default="CI",
        description="X12 claim filing indicator: MB (Medicare), MC (Medicaid), CI (Commercial), BL (BCBS), etc.",
    )


class ProviderInfo(BaseModel):
    """Billing/rendering provider identifiers (US context)."""
    npi: str = Field(..., description="10-digit National Provider Identifier (NPI)")
    tax_id: str = Field(..., description="Federal Tax ID (EIN or SSN) for the billing provider")
    organization_name: Optional[str] = Field(default=None, description="Billing organization name")
    rendering_name: Optional[str] = Field(default=None, description="Rendering provider full name")
    taxonomy_code: Optional[str] = Field(default=None, description="Provider taxonomy code (e.g., 207Q00000X for family medicine)")
    address: Optional[Address] = Field(default=None, description="Service facility address")


class ServiceLine(BaseModel):
    """A single claim service line with medical coding."""
    procedure_code: str = Field(..., description="CPT or HCPCS Level II procedure code (e.g., 99213)")
    modifiers: List[str] = Field(default_factory=list, description="Up to 4 CPT/HCPCS modifiers (e.g., 25, 59, RT)")
    diagnosis_pointers: List[int] = Field(..., description="Indexes (1-based) into the claim's diagnosis list")
    charge_amount: float = Field(..., ge=0, description="Line charge in USD")
    units: int = Field(default=1, ge=1, description="Number of units")
    service_date: str = Field(..., description="Date of service in YYYY-MM-DD format")
    place_of_service: str = Field(default="11", description="CMS place of service code (11=office, 21=inpatient, 22=outpatient, 23=ER)")


class Claim(BaseModel):
    """A professional (CMS-1500 / 837P) claim."""
    claim_id: str = Field(..., description="Unique claim identifier (CLM01)")
    patient: PatientInfo = Field(..., description="Patient demographic info")
    subscriber: SubscriberInfo = Field(..., description="Insurance subscriber info")
    payer: PayerInfo = Field(..., description="Payer details")
    provider: ProviderInfo = Field(..., description="Billing provider details")
    diagnoses: List[str] = Field(..., description="ICD-10-CM diagnosis codes in priority order (first is principal)")
    service_lines: List[ServiceLine] = Field(..., description="Procedure lines")
    prior_authorization: Optional[str] = Field(default=None, description="Prior authorization number, if applicable")
    referral_number: Optional[str] = Field(default=None, description="Referral number, if applicable")


class RemittanceLine(BaseModel):
    procedure_code: str = Field(..., description="Procedure code adjudicated")
    charged_amount: float = Field(..., description="Billed amount")
    paid_amount: float = Field(..., description="Amount paid by the payer")
    patient_responsibility: float = Field(default=0, description="Patient responsibility (copay/coins/deductible)")
    adjustment_group: Optional[str] = Field(default=None, description="Claim adjustment group code: CO | PR | OA | PI | CR")
    adjustment_reason_code: Optional[str] = Field(default=None, description="CARC (Claim Adjustment Reason Code)")
    remark_codes: List[str] = Field(default_factory=list, description="RARC (Remittance Advice Remark Codes)")


class Remittance(BaseModel):
    """Parsed 835 remittance advice."""
    claim_id: str = Field(..., description="Claim ID from the remittance")
    check_number: Optional[str] = Field(default=None, description="Payment check/EFT number")
    payment_date: Optional[str] = Field(default=None, description="Date of payment (YYYY-MM-DD)")
    total_paid: float = Field(..., description="Total paid on the claim")
    lines: List[RemittanceLine] = Field(default_factory=list, description="Line-level adjudication details")


class Denial(BaseModel):
    """A claim denial to be worked."""
    claim_id: str = Field(..., description="Denied claim ID")
    denial_code: str = Field(..., description="CARC code (e.g., 16, 50, 97, 197)")
    remark_codes: List[str] = Field(default_factory=list, description="RARC codes providing additional detail")
    denied_lines: List[str] = Field(default_factory=list, description="Denied procedure codes")
    denial_reason: Optional[str] = Field(default=None, description="Human-readable denial reason")
    received_date: Optional[str] = Field(default=None, description="Date denial was received (YYYY-MM-DD)")


class Appeal(BaseModel):
    """An appeal of a denied claim."""
    claim_id: str = Field(..., description="Claim being appealed")
    appeal_level: int = Field(default=1, ge=1, le=3, description="Appeal level (1=first level internal, 2=second level, 3=external review)")
    rationale: str = Field(..., description="Clinical/administrative rationale for overturning the denial")
    supporting_documents: List[str] = Field(default_factory=list, description="List of supporting documents (e.g., medical records, auth number)")
    letter: Optional[str] = Field(default=None, description="Generated appeal letter text")
