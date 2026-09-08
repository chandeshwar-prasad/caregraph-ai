"""
app/services/fhir_adapter.py

Bidirectional Domain Adapter for HL7 FHIR R4 Resources and CareGraph Data Models.
Provides:
1. Parsing of FHIR Patient, MedicationRequest, MedicationStatement, Observation, and Appointment resources.
2. Canonical conversion to CareGraph Pydantic models (PatientResponse, MedicationResponse, VitalResponse, AppointmentResponse).
3. LOINC code mapping for vital signs (BP, Heart Rate, Weight, Temperature, SpO2).
4. Transformation of CareGraph scheduling actions into compliant FHIR R4 Appointment payloads.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.schemas import PatientResponse
from app.schemas_ai import (
    MedicationResponse,
    VitalResponse,
    AppointmentResponse
)
from app.services.fhir_client import FHIRClient

logger = logging.getLogger("caregraph.fhir.adapter")

# LOINC code to CareGraph canonical vital type mapping
LOINC_VITAL_MAP: Dict[str, str] = {
    "85354-9": "blood_pressure",
    "8480-6": "blood_pressure",
    "8462-4": "blood_pressure",
    "8867-4": "heart_rate",
    "29463-7": "weight",
    "3141-9": "weight",
    "8310-5": "temperature",
    "2708-6": "spo2",
    "59408-5": "spo2"
}


class FHIRAdapter:
    """
    Adapter converting between HL7 FHIR R4 JSON payloads and CareGraph domain schemas.
    """

    def __init__(self, fhir_client: Optional[FHIRClient] = None):
        self.fhir_client = fhir_client or FHIRClient()

    # --- Patient Transformations ---

    def parse_patient(self, resource: Dict[str, Any], user_id: int = 1) -> PatientResponse:
        """Converts FHIR Patient resource into CareGraph PatientResponse."""
        names = resource.get("name", [{}])
        primary_name = names[0] if names else {}
        given_list = primary_name.get("given", [""])
        first_name = " ".join(given_list) if isinstance(given_list, list) else str(given_list)
        last_name = primary_name.get("family", "")

        telecoms = resource.get("telecom", [])
        email = next((t.get("value") for t in telecoms if t.get("system") == "email"), None)
        phone = next((t.get("value") for t in telecoms if t.get("system") == "phone"), None)

        # Generate integer fallback ID if FHIR string ID
        raw_id = resource.get("id", "1")
        try:
            numeric_id = int("".join(filter(str.isdigit, str(raw_id)))) or user_id
        except Exception:
            numeric_id = user_id

        return PatientResponse(
            id=numeric_id,
            user_id=user_id,
            first_name=first_name or "FHIR",
            last_name=last_name or "Patient",
            date_of_birth=resource.get("birthDate"),
            gender=resource.get("gender"),
            email=email,
            phone=phone
        )

    # --- Medication Transformations ---

    def parse_medication_entries(
        self, entries: List[Dict[str, Any]], patient_id: int = 1
    ) -> List[MedicationResponse]:
        """Converts FHIR MedicationRequest or MedicationStatement bundle entries."""
        results: List[MedicationResponse] = []
        for idx, entry in enumerate(entries, start=1):
            resource = entry.get("resource", entry)
            res_type = resource.get("resourceType", "")
            if res_type not in ["MedicationRequest", "MedicationStatement"]:
                continue

            # Extract medication name
            med_cc = resource.get("medicationCodeableConcept", {})
            codings = med_cc.get("coding", [{}])
            name = med_cc.get("text") or codings[0].get("display") or "Prescribed Medication"

            # Extract dosage & frequency
            dosage_list = resource.get("dosageInstruction", resource.get("dosage", [{}]))
            dosage_inst = dosage_list[0] if dosage_list else {}
            dosage_text = dosage_inst.get("text", "")
            dose_and_rate = dosage_inst.get("doseAndRate", [{}])
            dose_qty = dose_and_rate[0].get("doseQuantity", {}) if dose_and_rate else {}
            
            val = dose_qty.get("value")
            unit = dose_qty.get("unit", "")
            dosage = f"{val} {unit}".strip() if val else (dosage_text or "Standard Dose")
            
            timing = dosage_inst.get("timing", {}).get("repeat", {})
            freq_val = timing.get("frequency")
            period = timing.get("period")
            period_unit = timing.get("periodUnit", "day")
            if freq_val:
                frequency = f"{freq_val}x per {period or 1} {period_unit}"
            else:
                frequency = dosage_text or "As Directed"

            status = resource.get("status", "active")
            is_active = status in ["active", "completed", "intended"]

            notes_list = resource.get("note", [])
            notes = notes_list[0].get("text") if notes_list else None

            results.append(
                MedicationResponse(
                    id=idx,
                    patient_id=patient_id,
                    name=name,
                    dosage=dosage,
                    frequency=frequency,
                    prescribed_by=resource.get("requester", {}).get("display", "EHR Provider"),
                    start_date=resource.get("authoredOn", resource.get("effectiveDateTime")),
                    is_active=is_active,
                    notes=notes,
                    created_at=datetime.utcnow()
                )
            )
        return results

    # --- Observation (Vitals) Transformations ---

    def parse_observation_entries(
        self,
        entries: List[Dict[str, Any]],
        patient_id: int = 1,
        vital_type_filter: Optional[str] = None
    ) -> List[VitalResponse]:
        """Converts FHIR Observation resources into CareGraph VitalResponse list."""
        results: List[VitalResponse] = []
        for idx, entry in enumerate(entries, start=1):
            resource = entry.get("resource", entry)
            if resource.get("resourceType") != "Observation":
                continue

            # Identify vital type from LOINC code
            code_obj = resource.get("code", {})
            codings = code_obj.get("coding", [])
            code_val = codings[0].get("code") if codings else ""
            display = code_obj.get("text") or (codings[0].get("display") if codings else "Vital Sign")

            vital_type = LOINC_VITAL_MAP.get(code_val)
            if not vital_type:
                disp_lower = display.lower()
                if "blood pressure" in disp_lower or "bp" in disp_lower:
                    vital_type = "blood_pressure"
                elif "heart rate" in disp_lower or "pulse" in disp_lower:
                    vital_type = "heart_rate"
                elif "weight" in disp_lower:
                    vital_type = "weight"
                elif "temp" in disp_lower:
                    vital_type = "temperature"
                elif "spo2" in disp_lower or "oxygen" in disp_lower:
                    vital_type = "spo2"
                else:
                    vital_type = "other"

            if vital_type_filter and vital_type != vital_type_filter:
                continue

            # Extract measurement value and unit
            value_str = ""
            unit_str = None
            if "component" in resource and resource["component"]:
                # Compound observation e.g. Systolic / Diastolic
                components = resource["component"]
                systolic = next(
                    (c.get("valueQuantity", {}).get("value") for c in components
                     if any(cd.get("code") == "8480-6" for cd in c.get("code", {}).get("coding", []))),
                    None
                )
                diastolic = next(
                    (c.get("valueQuantity", {}).get("value") for c in components
                     if any(cd.get("code") == "8462-4" for cd in c.get("code", {}).get("coding", []))),
                    None
                )
                if systolic is not None and diastolic is not None:
                    value_str = f"{int(systolic)}/{int(diastolic)}"
                    unit_str = "mmHg"
                elif components and "valueQuantity" in components[0]:
                    value_str = str(components[0].get("valueQuantity", {}).get("value", ""))
                    unit_str = components[0].get("valueQuantity", {}).get("unit", "mmHg")
            elif "valueQuantity" in resource:
                vq = resource["valueQuantity"]
                value_str = str(vq.get("value", ""))
                unit_str = vq.get("unit")
            elif "valueString" in resource:
                value_str = resource["valueString"]
                if vital_type == "blood_pressure":
                    unit_str = "mmHg"

            if not unit_str and vital_type == "blood_pressure":
                unit_str = "mmHg"
            elif not unit_str and vital_type == "heart_rate":
                unit_str = "bpm"

            notes_list = resource.get("note", [])
            notes = notes_list[0].get("text") if notes_list else None

            rec_date = None
            date_str = resource.get("effectiveDateTime") or resource.get("issued")
            if date_str:
                try:
                    rec_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    rec_date = datetime.utcnow()

            results.append(
                VitalResponse(
                    id=idx,
                    patient_id=patient_id,
                    vital_type=vital_type,
                    value=value_str or "Recorded",
                    unit=unit_str,
                    recorded_at=rec_date or datetime.utcnow(),
                    source="FHIR_R4_EHR",
                    notes=notes,
                    created_at=datetime.utcnow()
                )
            )
        return results

    # --- Appointment Transformations ---

    def parse_appointment_entries(
        self, entries: List[Dict[str, Any]], patient_id: int = 1
    ) -> List[AppointmentResponse]:
        """Converts FHIR Appointment bundle entries into CareGraph AppointmentResponse list."""
        results: List[AppointmentResponse] = []
        for idx, entry in enumerate(entries, start=1):
            resource = entry.get("resource", entry)
            if resource.get("resourceType") != "Appointment":
                continue

            # Extract Practitioner
            participants = resource.get("participant", [])
            doctor_display = "Doctor"
            specialty = "General Practice"
            for p in participants:
                actor = p.get("actor", {})
                ref = actor.get("reference", "")
                disp = actor.get("display")
                if "Practitioner" in ref or "doctor" in ref.lower():
                    doctor_display = disp or "Attending Physician"
                    break

            results.append(
                AppointmentResponse(
                    id=idx,
                    patient_id=patient_id,
                    doctor_name=doctor_display,
                    specialty=specialty,
                    appointment_time=resource.get("start", "Upcoming"),
                    status=resource.get("status", "booked"),
                    notes=resource.get("description"),
                    created_at=datetime.utcnow()
                )
            )
        return results

    def appointment_to_fhir(
        self,
        doctor_name: str,
        specialty: str,
        appointment_time: str,
        patient_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Serializes CareGraph appointment booking into an HL7 FHIR R4 Appointment resource.
        """
        return {
            "resourceType": "Appointment",
            "status": "booked",
            "description": notes or f"Consultation with {doctor_name} ({specialty})",
            "start": appointment_time,
            "participant": [
                {
                    "actor": {
                        "reference": f"Practitioner/{specialty.lower().replace(' ', '-')}",
                        "display": doctor_name
                    },
                    "required": "required",
                    "status": "accepted"
                },
                {
                    "actor": {
                        "reference": f"Patient/{patient_id}",
                        "display": f"Patient #{patient_id}"
                    },
                    "required": "required",
                    "status": "accepted"
                }
            ]
        }
