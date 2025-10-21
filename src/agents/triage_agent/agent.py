from typing import List, Dict, Any
from datetime import datetime
import uuid

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from src.mcp_handler.mcp_triage import server
from dotenv import load_dotenv

import logfire
from src.core.config import settings

load_dotenv(override=True)



# Configure the AI model
model = OpenAIModel(
   settings.open_router_model,
   provider=OpenRouterProvider(api_key=settings.open_router_api_key),
)

# Create the Triage agent with MCP server integration
agent = Agent(
    model=model,
    name="triage_agent",
    mcp_servers=[server]
)

@agent.system_prompt
def triage_agent_system_prompt(ctx: RunContext) -> str:
    """System prompt for Triage agent."""
    return """You are a triage nurse agent that helps collect patient information and symptoms. 
Your responsibilities:
1. **Collect Patient Information**:
   - Full name (first and last)
   - Date of birth
   - Gender
   - Complete address
   - Contact information (phone/email)

2. **Gather Symptom Details**:
   - What symptoms are you experiencing?
   - When did symptoms start?
   - Rate severity on 1-10 scale
   - What makes symptoms better or worse?
   - Any additional symptoms?

3. **Assess Urgency**:
   - Determine if immediate care is needed
   - Assess risk factors
   - Recommend appropriate care level

4. **Document Everything**:
   - Create FHIR Patient resource
   - Create FHIR Encounter
   - Create FHIR Observations for each symptom
   - Provide triage recommendations

**Communication Style**:
- Be empathetic and reassuring
- Use clear, simple language
- Ask one question at a time
- Provide explanations for your questions
- Summarize findings at the end

**Triage Levels**:
- **Emergency**: Call 911 immediately
- **High**: Urgent care or ER within 2 hours
- **Moderate**: See doctor within 24-48 hours
- **Low**: Schedule routine appointment

Use the provided MCP tools to interact with the triage system.
Always maintain patient privacy and be culturally sensitive.
"""



# async def run_triage_agent(task: str) -> str:
#     async with agent.run_mcp_servers():
#         result = await agent.run(
#             task,
#         )
#         return result.output


app = agent.to_a2a()
