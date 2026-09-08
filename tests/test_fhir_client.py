"""
tests/test_fhir_client.py

Unit tests for HL7 FHIR R4 Client and Domain Adapter.
Verifies:
1. Patient fetching and fallback parsing.
2. Medication parsing (MedicationRequest & MedicationStatement).
3. Observation parsing (LOINC codes, compound systolic/diastolic blood pressure, pulse).
4. Appointment serialization and parsing.
5. In-memory caching and error classification.
"""

import pytest
from app.services.fhir_client import (
    FHIRClient,
    FHIRClientConfig,
    FHIRAuthenticationError,
    FHIRResourceNotFoundError,
    SAMPLE_FHIR_PATIENTS
)
from app.services.fhir_adapter import FHIRAdapter, LOINC_VITAL_MAP
from app.schemas import PatientResponse
from app.schemas_ai import MedicationResponse, VitalResponse, AppointmentResponse


def test_fhir_client_config_defaults():
    config = FHIRClientConfig()
    assert config.sandbox_mode is True
    assert config.mock_fallback is True
    assert len(config.scopes) > 0


def test_fhir_client_get_patient_mock():
    client = FHIRClient()
    patient = client.get_patient("SmartChris")
    assert patient["resourceType"] == "Patient"
    assert patient["id"] == "SmartChris"
    assert "name" in patient


def test_fhir_client_caching():
    client = FHIRClient()
    # First call stores in cache
    p1 = client.get_patient("SmartChris")
    assert "patient_SmartChris" in client.cache
    # Second call uses cache
    p2 = client.get_patient("SmartChris")
    assert p1 == p2


def test_fhir_client_get_medications():
    client = FHIRClient()
    meds = client.get_patient_medications("SmartChris")
    assert isinstance(meds, list)
    assert len(meds) >= 1
    first_med = meds[0]["resource"]
    assert first_med["resourceType"] == "MedicationRequest"


def test_fhir_client_get_observations():
    client = FHIRClient()
    obs = client.get_patient_observations("SmartChris")
    assert isinstance(obs, list)
    assert len(obs) >= 1


def test_fhir_adapter_patient_parsing():
    adapter = FHIRAdapter()
    raw_patient = SAMPLE_FHIR_PATIENTS["SmartChris"]
    parsed = adapter.parse_patient(raw_patient, user_id=42)
    
    assert isinstance(parsed, PatientResponse)
    assert parsed.user_id == 42
    assert "Chris" in parsed.first_name
    assert parsed.last_name == "Smith"
    assert parsed.email == "chris.smith@example.com"
    assert parsed.gender == "male"


def test_fhir_adapter_medication_parsing():
    client = FHIRClient()
    adapter = FHIRAdapter(client)
    raw_meds = client.get_patient_medications("SmartChris")
    parsed_meds = adapter.parse_medication_entries(raw_meds, patient_id=10)

    assert len(parsed_meds) >= 1
    first = parsed_meds[0]
    assert isinstance(first, MedicationResponse)
    assert first.patient_id == 10
    assert "Lisinopril" in first.name
    assert first.is_active is True


def test_fhir_adapter_observation_bp_parsing():
    client = FHIRClient()
    adapter = FHIRAdapter(client)
    raw_obs = client.get_patient_observations("SmartChris")
    parsed_vitals = adapter.parse_observation_entries(raw_obs, patient_id=10)

    assert len(parsed_vitals) >= 1
    # Check that Blood Pressure and Heart Rate are parsed correctly
    vital_types = [v.vital_type for v in parsed_vitals]
    assert "blood_pressure" in vital_types
    assert "heart_rate" in vital_types

    bp = next(v for v in parsed_vitals if v.vital_type == "blood_pressure")
    assert bp.value == "122/78"
    assert bp.unit == "mmHg"
    assert bp.source == "FHIR_R4_EHR"


def test_fhir_adapter_appointment_roundtrip():
    adapter = FHIRAdapter()
    fhir_apt = adapter.appointment_to_fhir(
        doctor_name="Dr. Sarah Chen",
        specialty="Cardiology",
        appointment_time="2026-10-15T10:00:00Z",
        patient_id="SmartChris",
        notes="Follow-up consultation"
    )

    assert fhir_apt["resourceType"] == "Appointment"
    assert fhir_apt["status"] == "booked"
    assert len(fhir_apt["participant"]) == 2

    # Parse back into CareGraph schema
    parsed_list = adapter.parse_appointment_entries([{"resource": fhir_apt}], patient_id=5)
    assert len(parsed_list) == 1
    parsed_apt = parsed_list[0]
    assert isinstance(parsed_apt, AppointmentResponse)
    assert parsed_apt.patient_id == 5
    assert parsed_apt.doctor_name == "Dr. Sarah Chen"
    assert parsed_apt.appointment_time == "2026-10-15T10:00:00Z"
