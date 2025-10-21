from typing import List, Dict, Any
from datetime import datetime
import uuid

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from src.agents.common.tool_client import A2AToolClient
from dotenv import load_dotenv

import logfire
from src.core.config import settings

load_dotenv(override=True)



# Configure the AI model
model = OpenAIModel(
    settings.open_router_model,
    provider=OpenRouterProvider(api_key=settings.open_router_api_key),
)

# Create A2A tool client for agent delegation
a2a_client = A2AToolClient()

# Register known remote agents so list_remote_agents reflects the running services
for remote_agent_url in (settings.triage_agent_url, settings.fhir_agent_url):
    if remote_agent_url:
        a2a_client.add_remote_agent(remote_agent_url)

agent = Agent(
    model=model,
    name="orchestration_agent",
    tools=[a2a_client.list_remote_agents, a2a_client.create_task],
)

@agent.system_prompt
def orchestration_agent_system_prompt(ctx: RunContext) -> str:
    return """You are the central coordinator for the Health Agents Collective. Your role is to:

1. **Understand user requests** and determine which specialized agents to involve
2. **Delegate to appropriate agents** using the available tools (`list_remote_agents`, `create_task`)
3. **Coordinate between agents** like the FHIR Agent for patient data and Triage Agent for assessments
4. **Provide clear guidance** on what actions are being taken

**Available Agents:**
- **FHIR Agent (port 10028)**: Handles patient data retrieval and clinical records
- **Triage Agent (port 10020)**: Manages patient registration, symptom assessment, and triage
- **Orchestration Agent (you)**: Coordinates workflows and manages agent communication

**Delegation Rules:**
- For any patient lookup, chart review, or condition-based search: call the **FHIR Agent** (`http://localhost:10028`).
- For symptom assessment or initial intake: call the **Triage Agent** (`http://localhost:10020`).
- When in doubt, prefer delegating and include each agent's response in your final answer.

**How to delegate:**
1. Use `list_remote_agents()` to confirm availability.
2. Use `create_task(agent_url, message)` to delegate tasks (e.g. `create_task("http://localhost:10028", "Find patients with diabetes")`).
3. Parse the response and provide a clear summary to the user.

**Example:**
- User: "What patients do we have with diabetes?"
- You: Call `list_remote_agents()` – confirm FHIR Agent is present.
- Then call `create_task("http://localhost:10028", "Retrieve patients diagnosed with diabetes mellitus")` and return the FHIR Agent's findings.

Always clearly state what you're doing and which agents you're delegating to."""

app = agent.to_a2a()
