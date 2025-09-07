from mcp.server.fastmcp import FastMCP
import os
import requests

FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL", "").strip()
if not FHIR_SERVER_URL:
    raise ValueError("FHIR_SERVER_URL environment variable is not set by the MCP launcher.")

# Initialize local MCP server instance
mcp = FastMCP("FHIR-MCP")

@mcp.tool()
def find_patient(patient_id: str) -> dict:
    """Retrieve a FHIR Patient resource by ID."""
    url = f"{FHIR_SERVER_URL}/Patient/{patient_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def find_patient_by_name(first_name: str, last_name: str) -> dict:
    """Search for a patient by first and last name."""
    url = f"{FHIR_SERVER_URL}/Patient?given={first_name}&family={last_name}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def find_observations_by_patient_id(patient_id: str) -> dict:
    """Retrieve all Observation resources for a given patient."""
    url = f"{FHIR_SERVER_URL}/Observation?patient={patient_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def find_medication_requests_by_patient_id(patient_id: str) -> dict:
    """Retrieve all MedicationRequest resources for a given patient."""
    url = f"{FHIR_SERVER_URL}/MedicationRequest?patient={patient_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def write_resource(resource_type: str, resource: dict) -> dict:
    """Write a new FHIR resource (e.g., Observation, DiagnosticReport) to the server."""
    url = f"{FHIR_SERVER_URL}/{resource_type}"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(url, headers=headers, json=resource)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
