from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from src.core.config import settings
from src.mcp_handler.mcp_fhir import server
from dotenv import load_dotenv

load_dotenv(override=True)

# Configure the AI model
model = OpenAIModel(
    settings.open_router_model,
    provider=OpenRouterProvider(api_key=settings.open_router_api_key),
)

# Create the FHIR agent with MCP server integration
fhir_agent = Agent(
    model=model,
    name="fhir_agent",
    mcp_servers=[server]
)

@fhir_agent.system_prompt
def system_prompt(_: RunContext) -> str:
    """System prompt for FHIR agent."""
    return """You are the FHIR Agent responsible for reading from and writing to the hospital's FHIR server.

Capabilities:
1. Retrieve patient data, medical history, allergies from the FHIR R4 API
2. Write back new resources such as Diagnoses, Test Results, Observations
3. Maintain secure, standards-compliant communication with the FHIR server
4. Enforce data provenance: always record the identity of the agent and references to inputs
5. Support lookup by patient ID or by patient demographic details
6. Use the provided MCP tools to interact with the FHIR server
7. Always validate responses against FHIR R4 schemas

FHIR Endpoint: https://r4.smarthealthit.org
FHIR Version: R4

Follow HL7 FHIR resource schemas exactly and ensure all responses are valid JSON conforming to FHIR R4.
"""

app = fhir_agent.to_a2a()
