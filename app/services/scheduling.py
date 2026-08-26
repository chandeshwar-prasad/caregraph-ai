from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app import crud, models


def search_available_slots(specialty: str = "General Practitioner", date_pref: str = "tomorrow") -> List[Dict[str, Any]]:
    """
    Generates synthetic available appointment slots for demo and development testing.
    Clearly attributes returned slots as Mock/Demo availability data.
    """
    spec = specialty.capitalize() if specialty else "General Practitioner"
    pref = date_pref if date_pref else "tomorrow"

    # Synthetic demo slot choices
    return [
        {
            "slot_id": "slot_01",
            "doctor_name": f"Dr. Alex Smith ({spec})",
            "specialty": spec,
            "appointment_time": f"{pref} at 10:00 AM",
            "is_mock": True,
            "source_name": "Mock Demo Availability Provider"
        },
        {
            "slot_id": "slot_02",
            "doctor_name": f"Dr. Jordan Lee ({spec})",
            "specialty": spec,
            "appointment_time": f"{pref} at 02:30 PM",
            "is_mock": True,
            "source_name": "Mock Demo Availability Provider"
        }
    ]


def book_appointment_slot(
    db: Session,
    patient_id: int,
    doctor_name: str,
    specialty: str,
    appointment_time: str,
    notes: Optional[str] = "Phase 5 Demo Appointment"
) -> models.Appointment:
    """
    Persists appointment slot into SQLite/PostgreSQL database and verifies insertion before returning.
    Follows Plan-Act-Verify workflow.
    """
    appointment = crud.create_appointment(
        db=db,
        patient_id=patient_id,
        doctor_name=doctor_name,
        specialty=specialty,
        appointment_time=appointment_time,
        notes=notes
    )

    # Verification assertion
    if not appointment or not appointment.id:
        raise RuntimeError("Database persistence verification failed: Appointment record was not created.")

    return appointment


def cancel_appointment_slot(db: Session, patient_id: int, appointment_id: int) -> Optional[models.Appointment]:
    """
    Updates status of an existing appointment to 'cancelled'.
    """
    return crud.cancel_appointment(db=db, patient_id=patient_id, appointment_id=appointment_id)
