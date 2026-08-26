import pytest
from datetime import datetime, timezone, timedelta
from app.database import Base, engine, SessionLocal
from app import models, crud, schemas
from app.services import patient_data

@pytest.fixture
def db_session():
    """Provides a fresh database session for testing patient_data service tools."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    crud.seed_initial_data(db)
    yield db
    db.close()


def test_get_patient_profile(db_session):
    # Patient demo exists from seed
    patient_user = db_session.query(models.User).filter_by(username="patient_demo").first()
    profile = patient_data.get_patient_profile(db_session, user_id=patient_user.id)
    assert profile["first_name"] == "John"
    assert profile["last_name"] == "Doe"
    assert "email" in profile

    # Non-existent user
    not_found = patient_data.get_patient_profile(db_session, user_id=99999)
    assert "error" in not_found


def test_get_patient_medications(db_session):
    patient_user = db_session.query(models.User).filter_by(username="patient_demo").first()
    meds = patient_data.get_patient_medications(db_session, user_id=patient_user.id)
    assert len(meds) >= 2
    med_names = [m["name"] for m in meds]
    assert "Lisinopril" in med_names
    assert "Vitamin D3" in med_names


def test_get_patient_vitals_and_filtering(db_session):
    patient_user = db_session.query(models.User).filter_by(username="patient_demo").first()
    all_vitals = patient_data.get_patient_vitals(db_session, user_id=patient_user.id)
    assert len(all_vitals) >= 5

    bp_vitals = patient_data.get_patient_vitals(db_session, user_id=patient_user.id, vital_type="blood_pressure")
    assert all(v["vital_type"] == "blood_pressure" for v in bp_vitals)
    assert len(bp_vitals) == 3

    hr_vitals = patient_data.get_patient_vitals(db_session, user_id=patient_user.id, vital_type="heart_rate")
    assert all(v["vital_type"] == "heart_rate" for v in hr_vitals)
    assert len(hr_vitals) == 2


def test_store_vital_and_validation(db_session):
    patient_user = db_session.query(models.User).filter_by(username="patient_demo").first()
    
    # Store valid vital
    new_vital = patient_data.store_vital(
        db=db_session,
        user_id=patient_user.id,
        vital_type="temperature",
        value="98.6",
        unit="°F"
    )
    assert "id" in new_vital
    assert new_vital["vital_type"] == "temperature"
    assert new_vital["value"] == "98.6"

    # Store invalid vital type
    invalid = patient_data.store_vital(
        db=db_session,
        user_id=patient_user.id,
        vital_type="invalid_type",
        value="120"
    )
    assert "error" in invalid


def test_calculate_vital_trend(db_session):
    patient_user = db_session.query(models.User).filter_by(username="patient_demo").first()

    # Heart rate trend (seeded 72 bpm 3 days ago, 75 bpm 1 day ago => increasing)
    hr_trend = patient_data.calculate_vital_trend(db_session, user_id=patient_user.id, vital_type="heart_rate")
    assert hr_trend["vital_type"] == "heart_rate"
    assert hr_trend["trend"] == "increasing"
    assert hr_trend["count"] == 2

    # Blood pressure trend special case (compound systolic/diastolic)
    bp_trend = patient_data.calculate_vital_trend(db_session, user_id=patient_user.id, vital_type="blood_pressure")
    assert bp_trend["vital_type"] == "blood_pressure"
    assert bp_trend["trend"] == "not_applicable"

    # Vital type with no records
    empty_trend = patient_data.calculate_vital_trend(db_session, user_id=patient_user.id, vital_type="weight")
    assert empty_trend["trend"] == "no_data"


def test_medication_reminders_creation_and_cancellation(db_session):
    # 1. Create Patient B
    user_b = crud.get_user_by_username(db_session, "patient_service_b")
    if not user_b:
        user_b = crud.create_user(db_session, schemas.UserCreate(username="patient_service_b", password="password_b", role="patient"))
        patient_b = crud.create_patient_profile(
            db_session,
            user_id=user_b.id,
            patient=schemas.PatientCreate(first_name="Jane", last_name="Smith", email="jane@example.com")
        )

    patient_a_user = db_session.query(models.User).filter_by(username="patient_demo").first()
    
    # 2. Patient A gets seeded reminders
    reminders_a = patient_data.get_medication_schedule(db_session, user_id=patient_a_user.id)
    assert len(reminders_a) >= 2
    reminder_id_a = reminders_a[0]["id"]

    # 3. Patient B creates a reminder
    new_rem_b = patient_data.create_medication_reminder(
        db=db_session,
        user_id=user_b.id,
        reminder_text="Take Allergy Medicine",
        reminder_time="09:00 PM"
    )
    assert new_rem_b["status"] == "active"
    assert new_rem_b["reminder_text"] == "Take Allergy Medicine"

    # 4. Cross-patient cancellation check: Patient B cannot cancel Patient A's reminder
    failed_cancel = patient_data.cancel_reminder(db_session, user_id=user_b.id, reminder_id=reminder_id_a)
    assert failed_cancel is None

    # 5. Patient A can cancel own reminder
    cancelled_a = patient_data.cancel_reminder(db_session, user_id=patient_a_user.id, reminder_id=reminder_id_a)
    assert cancelled_a is not None
    assert cancelled_a["status"] == "cancelled"

    # 6. Verify schedule now excludes cancelled reminder
    updated_reminders_a = patient_data.get_medication_schedule(db_session, user_id=patient_a_user.id)
    active_ids_a = [r["id"] for r in updated_reminders_a]
    assert reminder_id_a not in active_ids_a
