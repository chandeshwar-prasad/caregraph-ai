"""
app/services/patient_data.py

Controlled Python tools for Patient Data management (Profile, Medications, Vitals, Reminders, Trends).
These tools are invoked by graph nodes or API endpoints. They NEVER trust user-supplied patient_ids;
patient identity is strictly resolved from the authenticated user_id -> Patient model.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app import models, crud

ALLOWED_VITAL_TYPES = {"blood_pressure", "heart_rate", "weight", "temperature", "spo2"}

def _get_patient_by_user_id(db: Session, user_id: int) -> Optional[models.Patient]:
    """Helper to resolve Patient model from authenticated user_id."""
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def get_patient_profile(db: Session, user_id: int) -> Dict[str, Any]:
    """Retrieve demographics and profile info for the authenticated patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return {"error": "Patient profile not found"}
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "email": patient.email,
        "phone": patient.phone,
    }


def get_patient_medications(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Retrieve active prescribed medications for the authenticated patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return []
    meds = crud.get_patient_medications(db, patient.id)
    return [
        {
            "id": m.id,
            "patient_id": m.patient_id,
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "prescribed_by": m.prescribed_by,
            "start_date": m.start_date,
            "is_active": m.is_active,
            "notes": m.notes,
        }
        for m in meds
    ]


def get_patient_vitals(
    db: Session,
    user_id: int,
    vital_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Retrieve vital sign history for the authenticated patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return []
    vitals = crud.get_patient_vitals(db, patient.id, vital_type=vital_type, limit=limit)
    return [
        {
            "id": v.id,
            "patient_id": v.patient_id,
            "vital_type": v.vital_type,
            "value": v.value,
            "unit": v.unit,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            "source": v.source,
            "notes": v.notes,
        }
        for v in vitals
    ]


def store_vital(
    db: Session,
    user_id: int,
    vital_type: str,
    value: str,
    unit: Optional[str] = None,
    recorded_at: Optional[datetime] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Store a new vital reading for the authenticated patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return {"error": "Patient profile not found"}

    if vital_type not in ALLOWED_VITAL_TYPES:
        return {
            "error": f"Invalid vital_type '{vital_type}'. Must be one of: {sorted(ALLOWED_VITAL_TYPES)}"
        }

    vital = crud.create_vital(
        db=db,
        patient_id=patient.id,
        vital_type=vital_type,
        value=value,
        unit=unit,
        recorded_at=recorded_at,
        notes=notes
    )
    return {
        "id": vital.id,
        "patient_id": vital.patient_id,
        "vital_type": vital.vital_type,
        "value": vital.value,
        "unit": vital.unit,
        "recorded_at": vital.recorded_at.isoformat() if vital.recorded_at else None,
        "source": vital.source,
        "notes": vital.notes,
    }


def calculate_vital_trend(
    db: Session,
    user_id: int,
    vital_type: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Calculate deterministic trend direction for a numeric vital type.
    Pure Python math -- no LLM clinical interpretation.
    """
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return {"error": "Patient profile not found"}

    vitals = crud.get_patient_vitals(db, patient.id, vital_type=vital_type, limit=limit)
    if not vitals:
        return {
            "vital_type": vital_type,
            "count": 0,
            "trend": "no_data",
            "message": f"No recordings found for {vital_type}."
        }

    if vital_type == "blood_pressure":
        return {
            "vital_type": vital_type,
            "count": len(vitals),
            "trend": "not_applicable",
            "message": "Blood pressure readings are stored as systolic/diastolic compound values. Displaying historical readings.",
            "most_recent": {
                "value": vitals[0].value,
                "unit": vitals[0].unit,
                "recorded_at": vitals[0].recorded_at.isoformat() if vitals[0].recorded_at else None
            }
        }

    # Attempt numeric calculation for scalar vitals
    numeric_values = []
    for v in vitals:
        try:
            numeric_values.append((float(v.value), v))
        except (ValueError, TypeError):
            pass

    if not numeric_values:
        return {
            "vital_type": vital_type,
            "count": len(vitals),
            "trend": "non_numeric",
            "message": "Readings could not be converted to numbers for trend analysis."
        }

    # vitals are ordered recorded_at desc: [0] is most recent, [-1] is oldest in window
    recent_val, recent_obj = numeric_values[0]
    oldest_val, oldest_obj = numeric_values[-1]

    if recent_val > oldest_val:
        trend_dir = "increasing"
    elif recent_val < oldest_val:
        trend_dir = "decreasing"
    else:
        trend_dir = "stable"

    return {
        "vital_type": vital_type,
        "count": len(vitals),
        "trend": trend_dir,
        "most_recent": {
            "value": recent_obj.value,
            "unit": recent_obj.unit,
            "recorded_at": recent_obj.recorded_at.isoformat() if recent_obj.recorded_at else None
        },
        "oldest_in_window": {
            "value": oldest_obj.value,
            "unit": oldest_obj.unit,
            "recorded_at": oldest_obj.recorded_at.isoformat() if oldest_obj.recorded_at else None
        }
    }


def get_medication_schedule(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Retrieve active medication reminders for the authenticated patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return []
    reminders = crud.get_medication_reminders(db, patient.id)
    return [
        {
            "id": r.id,
            "medication_id": r.medication_id,
            "medication_name": r.medication.name if r.medication else None,
            "reminder_text": r.reminder_text,
            "reminder_time": r.reminder_time,
            "status": r.status,
            "notes": r.notes,
        }
        for r in reminders
        if r.status == "active"
    ]


def create_medication_reminder(
    db: Session,
    user_id: int,
    reminder_text: str,
    reminder_time: str,
    medication_id: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new medication reminder schedule for the patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return {"error": "Patient profile not found"}

    if not reminder_text or not reminder_time:
        return {"error": "reminder_text and reminder_time are required"}

    reminder = crud.create_medication_reminder(
        db=db,
        patient_id=patient.id,
        reminder_text=reminder_text,
        reminder_time=reminder_time,
        medication_id=medication_id,
        notes=notes
    )
    return {
        "id": reminder.id,
        "patient_id": reminder.patient_id,
        "medication_id": reminder.medication_id,
        "reminder_text": reminder.reminder_text,
        "reminder_time": reminder.reminder_time,
        "status": reminder.status,
        "notes": reminder.notes,
    }


def cancel_reminder(db: Session, user_id: int, reminder_id: int) -> Optional[Dict[str, Any]]:
    """Cancel a medication reminder owned by the patient."""
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return None

    reminder = crud.cancel_medication_reminder(db, patient_id=patient.id, reminder_id=reminder_id)
    if not reminder:
        return None

    return {
        "id": reminder.id,
        "patient_id": reminder.patient_id,
        "medication_id": reminder.medication_id,
        "reminder_text": reminder.reminder_text,
        "reminder_time": reminder.reminder_time,
        "status": reminder.status,
        "notes": reminder.notes,
    }
