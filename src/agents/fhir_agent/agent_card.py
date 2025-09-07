from a2a.types import AgentCard, AgentSkill
import uuid

FHIRAgentCard = AgentCard(
    name="FHIR Agent",
    description="Handles all communication with the hospital's FHIR server, enabling secure read/write of patient data and ensuring full HL7 R4 compliance.",
    url="http://localhost:10028/",
    version="1.0.0",
    defaultInputModes=["text", "text/plain"],
    defaultOutputModes=["text", "text/plain"],
    capabilities={"streaming": True},
    skills=[
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Retrieve Patient Data",
            description="Fetch patient demographic and clinical information by ID or by demographic details.",
            tags=[]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Write Clinical Data",
            description="Write new resources such as Diagnoses, Observations, or Test Results into FHIR.",
            tags=[]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Data Provenance Enforcement",
            description="Record agent identity, inputs used, and maintain an auditable history for all updates.",
            tags=[]
        ),
    ],
)
