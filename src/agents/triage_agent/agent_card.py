from a2a.types import AgentCard, AgentSkill
import uuid

TriageAgentCard = AgentCard(
    name="Triage Agent",
    description="A triage nurse agent that collects patient information, assesses symptoms, determines urgency, and documents findings in FHIR.",
    url="http://localhost:10020/",
    version="1.0.0",
    defaultInputModes=["text", "text/plain"],
    defaultOutputModes=["text", "text/plain"],
    capabilities={"streaming": True},
    skills=[
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Patient Intake",
            description="Collect patient demographics including name, DOB, gender, address, and contact information.",
            tags=["intake", "demographics"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Symptom Assessment",
            description="Gather detailed information about symptoms, including onset, severity, and aggravating/relieving factors.",
            tags=["assessment", "symptoms"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Urgency Assessment",
            description="Determine the urgency of the patient's condition and recommend appropriate level of care.",
            tags=["triage", "urgency"]
        ),
        AgentSkill(
            id=str(uuid.uuid4()),
            name="Documentation",
            description="Create FHIR resources (Patient, Encounter, Observations) to document the triage assessment.",
            tags=["documentation", "fhir"]
        ),
    ],
)