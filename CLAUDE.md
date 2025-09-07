# Claude Configuration

This file contains configuration and context for Claude Code assistant.

## Project Overview
Health Agents Collective - A multi-agent system for healthcare AI applications, featuring triage nurse functionality with FHIR integration and orchestration capabilities.

## Development Commands
- Install dependencies: `uv sync`
- Run the application: `python app.py`
- Run tests: `uv run pytest`
- Lint code: `uv run ruff check`
- Format code: `uv run ruff format`

## Project Structure
```
src/
├── agents/
│   ├── common/                 # Shared agent infrastructure
│   │   ├── agent.py           # Background agent execution utilities
│   │   ├── agent_executor.py  # Pydantic AI executor for A2A
│   │   ├── server.py          # A2A server creation utilities
│   │   └── tool_client.py     # A2A client for remote agent communication
│   ├── orchestration_agent/   # Master orchestration agent
│   │   ├── __init__.py
│   │   ├── agent.py          # Personal assistant orchestration agent
│   │   └── agent_card.py     # Orchestration agent metadata
│   └── triage_agent/         # Healthcare triage specialist
│       ├── __init__.py
│       ├── agent.py          # TriageNurseAgent class and factory functions
│       ├── agent_card.py     # Agent capabilities and metadata
│       └── models.py         # FHIR models and data structures
├── core/
│   ├── __init__.py
│   └── config.py             # Configuration management with environment variables
└── mcp_handler/
    └── fhir_mcp.py           # MCP tools for FHIR integration (currently empty)

app.py                      # Main application entry point - runs multi-agent servers
main.py                    # Original FHIR data fetching
pyproject.toml             # Project configuration and dependencies
CLAUDE.md                  # This file
TASKS.md                   # Implementation tasks and roadmap
```

## Key Dependencies
- `pydantic-ai>=0.4.11` - AI agent framework
- `fastmcp>=2.11.1` - MCP (Model Context Protocol) integration
- `logfire>=4.1.0` - Logging and observability
- `requests>=2.32.4` - HTTP library for API calls
- `a2a-sdk>=0.3.0` - Agent-to-Agent communication protocol
- `asyncpg>=0.30.0` - Async PostgreSQL driver
- Uses Python 3.13+

## Current Focus
- **Triage Nurse Agent**: Patient assessment and symptom evaluation with FHIR R4 compliance
- **Orchestration Agent**: Master agent that coordinates between specialized agents
- **A2A Protocol**: Agent-to-Agent communication using Google's A2A SDK
- **Multi-agent Architecture**: Scalable system with background servers running on different ports

## Agent Servers
- **Triage Agent**: Port 10020 - Healthcare triage and FHIR resource creation
- **Orchestration Agent**: Port 10024 - Master coordination agent

## Configuration
- Environment variables loaded from `.env` file
- FHIR server configuration: `http://192.168.68.211:8080/fhir`
- API keys and settings managed through `src/core/config.py`

## Architecture Notes
- **A2A Protocol**: Uses Google's Agent-to-Agent protocol for inter-agent communication
- **Background Servers**: Each agent runs as a separate Starlette server in background threads
- **FHIR Models**: Comprehensive FHIR R4 compliant models for Patient, Encounter, Observation
- **Scalable Design**: Easy to add new specialized agents following the established pattern
- **Observability**: Integrated Logfire instrumentation for monitoring and debugging

## Key Capabilities
- **Triage Agent**: Patient registration, symptom assessment, FHIR resource creation, severity assessment, care recommendations
- **Orchestration Agent**: Coordinates between multiple specialized agents, handles user requests through appropriate agent delegation

## How to Implement New Agents

Follow this exact pattern to add new specialized agents to the system:

### 1. Create Agent Directory Structure

Create a new directory under `src/agents/` with the following files:

```
src/agents/your_agent_name/
├── __init__.py          # Exports agent and card
├── agent.py             # Agent definition and prompts
├── agent_card.py        # Agent metadata and capabilities
└── models.py            # (Optional) Domain-specific models
```

### 2. Agent Implementation Template

#### agent.py
```python
from typing import List, Dict, Any
from datetime import datetime
import uuid

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

# Configure the AI model
model = OpenAIModel(
    'anthropic/claude-3.5-sonnet',
    provider=OpenRouterProvider(api_key='your-openrouter-api-key'),
)

# Create the agent instance
agent = Agent(
    model=model,
    name="your_agent_name",  # Must match directory name
)

@agent.system_prompt
def your_agent_system_prompt(ctx: RunContext) -> str:
    return """You are a [specialized agent description].
    
Your responsibilities:
1. **Primary Function**: [Main purpose]
2. **Capabilities**: [List specific abilities]
3. **Communication Style**: [Tone and approach guidelines]

**Key Guidelines**:
- [Specific rule 1]
- [Specific rule 2]
- [Specific rule 3]

**Example Interactions**:
- User: "[Example input]"
- Response: "[Example output]"
"""

# Export the agent for A2A protocol - THIS IS REQUIRED
app = agent.to_a2a()
```

#### agent_card.py
```python
from a2a.types import AgentSkill


class YourAgentCard:
    """
    Brief description of what this agent does.
    """
    
    name: str = "Your Agent Name"           # Human-readable name
    description: str = "Brief description"  # One-line description
    skills: list[AgentSkill] = []           # List of AgentSkill objects (can be empty)
    organization: str = "Your Organization" # Source/owner identifier
    url: str = "http://localhost:10021"     # Unique port per agent
```

#### __init__.py
```python
from .agent import app as your_agent_name
from .agent_card import YourAgentCard

__all__ = ["your_agent_name", "YourAgentCard"]
```

To run a single agent, you can run: `uvicorn src.agents.fhir_agent.agent:app --port 8080 --reload`
and visit https://localhost:8080/docs

### 3. Register Agent in Main Application

#### Step 1: Import your agent in app.py
Add to the imports section:
```python
from src.agents.your_agent_name import (
    your_agent_name,
    YourAgentCard,
)
```

#### Step 2: Create server function
Add a new server creation function:
```python
def create_your_agent_server(host="localhost", port=10021) -> A2AStarletteApplication:
    """Create A2A server for Your Agent."""
    return create_agent_a2a_server(
        agent=your_agent_name,
        name=YourAgentCard.name,
        description=YourAgentCard.description,
        skills=YourAgentCard.skills,
        host=host,
        port=port,
        status_message="Processing your request...",
        artifact_name="response",
    )
```

#### Step 3: Add to agents list
Add your agent to the `agents` list:
```python
agents: list[Dict[str, Callable[[str, int], A2AStarletteApplication]]] = [
    {
        "name": "Triage Agent",
        "agent": create_triage_agent_server,
        "port": 10020,
    },
    {
        "name": "Orchestration Agent", 
        "agent": create_orchestration_agent_server,
        "port": 10024,
    },
    {
        "name": "Your Agent",
        "agent": create_your_agent_server,
        "port": 10021,  # Use unique port
    },
]
```

### 4. Port Assignment Guidelines

Use these port ranges for different agent types:
- **Healthcare Agents**: 10020-10029
- **Productivity Agents**: 10030-10039  
- **Data Processing Agents**: 10040-10049
- **Integration Agents**: 10050-10059
- **Custom Agents**: 10060+

### 5. Complete Example: Weather Agent

Here's a complete example for a weather information agent:

#### src/agents/weather_agent/agent.py
```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

model = OpenAIModel(
    'anthropic/claude-3.5-sonnet',
    provider=OpenRouterProvider(api_key='your-openrouter-api-key'),
)

agent = Agent(
    model=model,
    name="weather_agent",
)

@agent.system_prompt
def weather_agent_system_prompt(ctx: RunContext) -> str:
    return """You are a weather information agent that provides accurate weather forecasts and conditions.
    
Your responsibilities:
1. **Provide Current Weather**: Give current conditions for any location
2. **Forecast Weather**: Provide 7-day forecasts with details
3. **Severe Weather Alerts**: Warn about dangerous conditions
4. **Travel Weather**: Give weather for travel destinations
    
**Communication Style**:
- Be concise but informative
- Include temperature, precipitation, and wind
- Mention if conditions are unusual for the season
- Provide practical advice (umbrella, jacket, etc.)
"""

# Export the agent for A2A protocol - THIS IS REQUIRED
app = agent.to_a2a()
```

#### src/agents/weather_agent/agent_card.py
```python
from a2a.types import AgentSkill


class WeatherAgentCard:
    """
    Provides weather forecasts and current conditions for any location.
    """
    
    name: str = "Weather Agent"
    description: str = "Provides weather forecasts and current conditions"
    skills: list[AgentSkill] = []
    organization: str = "Weather Service"
    url: str = "http://localhost:10030"
```

### 6. Testing Your Agent

After implementation:

1. **Start the system**: `python app.py`
2. **Verify agent starts**: Check console output for your agent's port
3. **Test via orchestration**: The orchestration agent will automatically discover your new agent
4. **Direct testing**: Use curl or HTTP client to test the A2A endpoint directly

### 7. Advanced Features

#### Adding Tools
To add specialized tools to your agent:

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import Tool

def your_custom_tool(location: str) -> str:
    """Tool description for the agent."""
    # Implement tool logic
    return "Tool result"

agent = Agent(
    model=model,
    name="your_agent_name",
    tools=[your_custom_tool],  # Add tools here
)
```

#### Custom Models
Add domain-specific models in `models.py`:

```python
from pydantic import BaseModel

class YourAgentRequest(BaseModel):
    field1: str
    field2: int
    
class YourAgentResponse(BaseModel):
    result: str
    confidence: float
```

This pattern ensures consistency across the multi-agent system while allowing each agent to specialize in its domain.