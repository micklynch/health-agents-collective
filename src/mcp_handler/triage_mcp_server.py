import os
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP

from src.core.config import settings
import logfire

logfire.configure()

# Initialize FastMCP server
mcp = FastMCP("Triage-MCP")

DEFAULT_TIMEOUT = settings.fhir_http_timeout
FHIR_SERVER_URL = settings.fhir_base_url.strip()

@mcp.tool()
def search_patient(name: str, birth_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for a patient by name and optionally birth date.
    
    Args:
        name: Patient's name (first or last)
        birth_date: Optional birth date in YYYY-MM-DD format
    """
    params = {"name": name}
    if birth_date:
        params["birthdate"] = birth_date
        
    url = f"{FHIR_SERVER_URL}/Patient"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def get_patient(patient_id: str) -> Dict[str, Any]:
    """
    Retrieve a patient by their FHIR ID.
    
    Args:
        patient_id: The logical ID of the patient
    """
    url = f"{FHIR_SERVER_URL}/Patient/{patient_id}"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def create_patient(
    first_name: str,
    last_name: str,
    birth_date: str,
    gender: str,
    address: Optional[Dict[str, str]] = None,
    telecom: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a new Patient resource.
    
    Args:
        first_name: Given name
        last_name: Family name
        birth_date: Date of birth (YYYY-MM-DD)
        gender: male | female | other | unknown
        address: Optional address dict (line, city, state, postalCode)
        telecom: Optional list of contact details (system, value, use)
    """
    resource = {
        "resourceType": "Patient",
        "name": [{
            "use": "official",
            "family": last_name,
            "given": [first_name]
        }],
        "gender": gender,
        "birthDate": birth_date,
        "active": True
    }
    
    if address:
        addr_obj = {
            "use": "home",
            "line": [address.get("line", "")],
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "postalCode": address.get("postalCode", ""),
            "country": address.get("country", "US")
        }
        resource["address"] = [addr_obj]
        
    if telecom:
        resource["telecom"] = telecom

    url = f"{FHIR_SERVER_URL}/Patient"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(url, headers=headers, json=resource, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def create_encounter(
    patient_id: str,
    status: str = "triaged",
    class_code: str = "EMER",
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new Encounter resource.
    
    Args:
        patient_id: Reference to the patient
        status: planned | arrived | triaged | in-progress | onleave | finished | cancelled
        class_code: AMB (ambulatory) | EMER (emergency) | IMP (inpatient)
        reason: Reason for the encounter
    """
    resource = {
        "resourceType": "Encounter",
        "status": status,
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": class_code
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "period": {
            "start": datetime.now().isoformat()
        }
    }
    
    if reason:
        resource["reasonCode"] = [{
            "text": reason
        }]

    url = f"{FHIR_SERVER_URL}/Encounter"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(url, headers=headers, json=resource, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def create_observation(
    patient_id: str,
    code_text: str,
    value_string: Optional[str] = None,
    value_quantity: Optional[Dict[str, Any]] = None,
    encounter_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new Observation resource (e.g., for symptoms).
    
    Args:
        patient_id: Reference to the patient
        code_text: Description of the observation (e.g., "Abdominal pain")
        value_string: Text result
        value_quantity: Quantity result (value, unit)
        encounter_id: Optional reference to the encounter
    """
    resource = {
        "resourceType": "Observation",
        "status": "preliminary",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "exam",
                "display": "Exam"
            }]
        }],
        "code": {
            "text": code_text
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": datetime.now().isoformat()
    }
    
    if encounter_id:
        resource["encounter"] = {
            "reference": f"Encounter/{encounter_id}"
        }
        
    if value_string:
        resource["valueString"] = value_string
    elif value_quantity:
        resource["valueQuantity"] = value_quantity

    url = f"{FHIR_SERVER_URL}/Observation"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(url, headers=headers, json=resource, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
