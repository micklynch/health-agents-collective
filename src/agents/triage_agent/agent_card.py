from a2a.types import AgentSkill


class TriageAgentCard:
    """
    This agent is used to triage patients based on symptoms.
    """

    name: str = "Triage Agent"
    description: str = "Triage Agent"
    skills: list[AgentSkill] = []
    organization: str = "Triage Agent"
    url: str = "http://localhost:10019"