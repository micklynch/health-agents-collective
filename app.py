import time

import asyncio
import logfire
from src.core.config import settings

# ---------------------------------------------------------------------------
# Configure Logfire for comprehensive observability. This will print a link
# to the local Logfire Live view and automatically display logs in the
# console. You can set LOGFIRE_TOKEN or other env vars to forward traces to
# the hosted Logfire backend if desired.
# ---------------------------------------------------------------------------

# Configure logfire with token support
logfire_config = {}
if settings.logfire_token:
    logfire_config["token"] = settings.logfire_token
    logfire_config["send_to_logfire"] = True
    logfire_config["project_name"] = settings.logfire_project_name
    logfire_config["environment"] = settings.logfire_environment
else:
    logfire_config["send_to_logfire"] = False
    logfire_config["console"] = False  # Disable console output to avoid conflicts

logfire.configure(**logfire_config)

# Capture Pydantic-AI and HTTPX calls which power the agent runtime.
try:
    logfire.instrument_pydantic_ai()
except AttributeError:
    # Older versions of Logfire may not have this helper; skip gracefully.
    pass

try:
    logfire.instrument_httpx()
except AttributeError:
    pass

from typing import Callable, Dict
from src.agents.orchestration_agent import (
    orchestration_agent,
    OrchestrationAgentCard,
)
from src.agents.triage_agent import (
    triage_agent,
    TriageAgentCard,
)
from src.agents.fhir_agent.agent import fhir_agent
from src.agents.fhir_agent.agent_card import FHIRAgentCard
from src.agents.common.tool_client import A2AToolClient
from src.agents.common.agent import run_agent_in_background
from src.agents.common.server import create_agent_a2a_server
from a2a.server.apps import A2AStarletteApplication
from pydantic_ai import Agent

a2a_client = A2AToolClient()


def create_triage_agent_server(host="localhost", port=10020) -> A2AStarletteApplication:
    """Create A2A server for Triage Agent using the unified wrapper."""
    return create_agent_a2a_server(
        agent=triage_agent,
        name=TriageAgentCard.name,
        description=TriageAgentCard.description,
        skills=TriageAgentCard.skills,
        host=host,
        port=port,
        status_message="Processing patient triage assessment...",
        artifact_name="response",
    )


def create_orchestration_agent_server(
    host="localhost", port=10024
) -> A2AStarletteApplication:
    """Create A2A server for Orchestration Agent using the unified wrapper."""
    return create_agent_a2a_server(
        agent=orchestration_agent,
        name=OrchestrationAgentCard.name,
        description=OrchestrationAgentCard.description,
        skills=OrchestrationAgentCard.skills,
        host=host,
        port=port,
        status_message="Coordinating agent communication...",
        artifact_name="response",
    )


def create_fhir_agent_server(host="localhost", port=10028) -> A2AStarletteApplication:
    """Create A2A server for FHIR Agent."""
    return create_agent_a2a_server(
        agent=fhir_agent,
        name=FHIRAgentCard.name,
        description=FHIRAgentCard.description,
        skills=FHIRAgentCard.skills,
        host=host,
        port=port,
        status_message="Processing FHIR requests...",
        artifact_name="response",
    )

agents: list[Dict[str, Callable[[str, int], A2AStarletteApplication]]] = [
    {
        "name": "Triage Agent",
        "agent": create_triage_agent_server,
        "port": 10020,
    },
    {
        "name": "FHIR Agent",
        "agent": create_fhir_agent_server,
        "port": 10028,
    },
    {
        "name": "Orchestration Agent",
        "agent": create_orchestration_agent_server,
        "port": 10024,
    },
]

# Start agent servers with corrected function calls
print("Starting agent servers...\n")

threads = []
for agent_config in agents:
    threads.append(
        run_agent_in_background(agent_config["agent"], agent_config["port"], agent_config["name"])
    )


# Wait for servers to start
time.sleep(3)

# Check if threads are alive
if all(thread.is_alive() for thread in threads):
    print("\n✅ Agent servers are running!")
    for agent_config in agents:
        print(f"   - {agent_config['name']}: http://127.0.0.1:{agent_config['port']}")
else:
    print("\n❌ Agent servers failed to start. Check the error messages above.")


# Register all remote agents
for agent in agents:
    a2a_client.add_remote_agent(f"http://localhost:{agent['port']}")

# List all registered agents
remote_agents = a2a_client.list_remote_agents()
for k, v in remote_agents.items():
    print(f"Remote agent url: {k}")
    print(f"Remote agent name: {v['name']}")
    print(f"Remote agent skills: {v['skills']}")
    print(f"Remote agent version: {v['version']}")
    print("----\n")


def interactive_mode_sync():
    """Synchronous interactive REPL loop for continuous user interaction."""
    print("\n🤖 Health Agents Collective - Interactive Mode")
    print("Available agents:")
    print("  ✅ Triage Agent (port 10020) - Patient assessment and symptom evaluation")
    print("  ✅ FHIR Agent (port 10028) - Patient data retrieval and clinical records")
    print("  ✅ Orchestration Agent (port 10024) - Master coordinator for agent delegation")
    print("\nType your questions or requests below. Enter '/quit' to exit.\n")
    
    while True:
        try:
            # Get user input
            user_input = input("💬 What would you like to do today? ").strip()
            
            # Check for quit command
            if user_input.lower() == '/quit':
                print("\n👋 Goodbye!")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Check registered agents
            print("\n🔍 Checking registered agents...")
            try:
                remote_agents = a2a_client.list_remote_agents()
                print(f"   📋 {len(remote_agents)} agents available:")
                for url, info in remote_agents.items():
                    print(f"      - {info['name']}")
            except Exception as e:
                print(f"   ⚠️  Could not list agents: {e}")
            
            # Send request to orchestration agent
            print("\n🔄 Sending to orchestration agent...")
            try:
                # Run async create_task in event loop
                task = asyncio.run(a2a_client.create_task(
                    "http://localhost:10024", 
                    user_input
                ))
                
                print(f"\n🎯 Task created: {task.id}")
                print(f"   Status: {task.status}")
                
                if task.artifacts and task.artifacts[0].parts:
                    response_text = task.artifacts[0].parts[0].text
                    if response_text:
                        print(f"   Response: {response_text}")
                    else:
                        print("   No response text available")
                else:
                    print("   No response received")
                    
            except Exception as e:
                print(f"\n❌ Task failed: {e}")
                print("   The orchestration agent will delegate to appropriate specialized agents")
                print("   Try asking specific questions like:")
                print("   - 'Find patient data for John Smith'")
                print("   - 'Help me with patient triage'")
                print("   - 'What agents are available?'")
                print("   - 'I need to register a new patient'")
            
            print()  # Empty line for readability
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Make sure all agents are running on their ports")
            print()

async def interactive_mode():
    """Async wrapper for interactive mode."""
    # Run the sync version in a separate thread to avoid input conflicts
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, interactive_mode_sync)


async def main():
    """Main function that starts interactive mode."""
    print("🧪 Health Agents Collective - Starting up...")
    
    # Test if agents are available
    try:
        print("🔍 Testing agent connectivity...")
        
        # Check registered remote agents
        remote_agents = a2a_client.list_remote_agents()
        print(f"✅ Found {len(remote_agents)} registered agents:")
        for url, info in remote_agents.items():
            print(f"   - {info['name']} at {url}")
        
        # Start interactive mode
        await interactive_mode()
        
    except Exception as e:
        print(f"❌ Agent connectivity test failed: {e}")
        print("Please ensure all agent servers are running:")
        for agent_config in agents:
            print(f"  - {agent_config['name']} on port {agent_config['port']}")


if __name__ == "__main__":
    asyncio.run(main())
