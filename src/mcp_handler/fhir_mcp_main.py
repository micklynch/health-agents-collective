import asyncio
from mcp.server.fastmcp import FastMCP
import os
import requests

from src.agents.fhir_agent.search_planner import (
    ConditionSearchPlan,
    plan_condition_search,
)

from src.core.config import settings

DEFAULT_TIMEOUT = settings.fhir_http_timeout

FHIR_SERVER_URL = settings.fhir_base_url.strip()

# Initialize local MCP server instance
mcp = FastMCP("FHIR-MCP")

@mcp.tool()
def find_patient(patient_id: str) -> dict:
    """Retrieve a FHIR Patient resource by ID."""
    url = f"{FHIR_SERVER_URL}/Patient/{patient_id}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def find_patient_by_name(first_name: str, last_name: str) -> dict:
    """Search for a patient by first and last name."""
    url = f"{FHIR_SERVER_URL}/Patient?given={first_name}&family={last_name}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def find_observations_by_patient_id(patient_id: str) -> dict:
    """Retrieve all Observation resources for a given patient."""
    url = f"{FHIR_SERVER_URL}/Observation?patient={patient_id}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def find_medication_requests_by_patient_id(patient_id: str) -> dict:
    """Retrieve all MedicationRequest resources for a given patient."""
    url = f"{FHIR_SERVER_URL}/MedicationRequest?patient={patient_id}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def find_patients_by_condition(condition_text: str, max_results: int = 20) -> dict:
    """Find patients who have conditions matching the provided text.

    This uses an LLM-backed planner to derive optimal search terms before querying
    the FHIR endpoint. The original user text is preserved in the summary for
    provenance.
    """

    plan: ConditionSearchPlan = await plan_condition_search(condition_text)

    search_terms = plan.search_terms if plan.search_terms else [condition_text]

    payload = {}
    matched_term = search_terms[0]
    for term in search_terms:
        params = {
            "code:text": term,
            "_include": "Condition:subject",
            "_count": max_results,
        }
        url = f"{FHIR_SERVER_URL}/Condition"
        def _do_request() -> dict:
            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.json()

        payload = await asyncio.to_thread(_do_request)
        matched_term = term
        if payload.get("total", 0):
            break

    condition_entries = []
    patient_records: dict[str, dict] = {}
    patient_refs = []

    for entry in payload.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        if resource_type == "Condition":
            subject_ref = resource.get("subject", {}).get("reference")
            if subject_ref:
                patient_refs.append(subject_ref)
            condition_entries.append(
                {
                    "id": resource.get("id"),
                    "code": resource.get("code", {}).get("text")
                    or resource.get("code", {}).get("coding", [{}])[0].get("display"),
                    "recordedDate": resource.get("recordedDate"),
                    "subject": subject_ref,
                }
            )
        elif resource_type == "Patient":
            name = ""
            names = resource.get("name", [])
            if names:
                given = " ".join(names[0].get("given", []))
                family = names[0].get("family", "")
                name = (given + " " + family).strip()
            patient_records[resource.get("id", "")] = {
                "id": resource.get("id"),
                "name": name or None,
                "gender": resource.get("gender"),
                "birthDate": resource.get("birthDate"),
            }

    # Deduplicate while preserving order
    seen_refs = set()
    unique_refs = []
    for ref in patient_refs:
        patient_id = ref.split("/")[-1]
        if patient_id and patient_id not in seen_refs:
            seen_refs.add(patient_id)
            unique_refs.append(
                {
                    "reference": ref,
                    "patient": patient_records.get(patient_id),
                }
            )

    return {
        "summary": {
            "condition": condition_text,
            "total_conditions": payload.get("total", 0),
            "patients_found": len(unique_refs),
            "matched_search_term": matched_term,
            "search_plan": plan.model_dump(mode="json"),
        },
        "patients": unique_refs,
        "conditions": condition_entries,
    }

@mcp.tool()
def write_resource(resource_type: str, resource: dict) -> dict:
    """Write a new FHIR resource (e.g., Observation, DiagnosticReport) to the server."""
    url = f"{FHIR_SERVER_URL}/{resource_type}"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(url, headers=headers, json=resource, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
