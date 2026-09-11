from a2a.types import AgentCard, AgentSkill
import uuid

FinanceAgentCard = AgentCard(
    name="Finance Agent",
    description="A US healthcare revenue cycle agent that handles medical coding (CPT/HCPCS/ICD-10), EDI claim submissions (837P), claim status and remittance (276/277/835), denial management, appeals, and payer correspondence.",
    url="http://localhost:10030/",
    version="1.0.0",
    defaultInputModes=["text", "text/plain"],
    defaultOutputModes=["text", "text/plain"],
    capabilities={"streaming": True},
    skills=[
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Medical Coding",
            description="Assign and validate CPT/HCPCS procedure codes and ICD-10-CM diagnosis codes, including modifiers and place-of-service codes.",
            tags=["coding", "cpt", "hcpcs", "icd-10"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Claim Submission (EDI 837P)",
            description="Scrub claims, generate X12 5010 837P transactions, and submit them to insurance payers via a clearinghouse.",
            tags=["claims", "edi", "837", "submission"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Claim Status & Remittance",
            description="Track claim adjudication via 276/277 status inquiries and interpret 835 remittance advices, payments, and adjustments.",
            tags=["276", "277", "835", "remittance"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Denial Management & Appeals",
            description="Interpret CARC/RARC denial codes, determine correct-and-resubmit vs. appeal strategy, and draft appeal letters.",
            tags=["denials", "appeals", "carc"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Payer Correspondence",
            description="Send and track correspondence with insurance companies, including appeals, records requests, and status follow-ups.",
            tags=["correspondence", "payer"]
        ),
    ],
)
