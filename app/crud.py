from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import hash_password

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        password_hash=hash_password(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_patient_profile(db: Session, user_id: int, patient: schemas.PatientCreate):
    db_patient = models.Patient(
        user_id=user_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        email=patient.email,
        phone=patient.phone
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)

    # Initialize default patient consent grants (valid for 1 year)
    now = datetime.now(timezone.utc)
    standard_consents = [
        "data_access",
        "vital_tracking",
        "medication_tracking",
        "medication_reminders",
        "appointment_booking",
        "ai_processing",
    ]
    for c_type in standard_consents:
        c = models.PatientConsent(
            patient_id=db_patient.id,
            consent_type=c_type,
            status="granted",
            granted_at=now,
            expires_at=now + timedelta(days=365),
            version="v1.0"
        )
        db.add(c)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def seed_initial_data(db: Session):
    # Check if we already have users
    if db.query(models.User).count() == 0:
        print("Seeding initial demo accounts...")
        
        # 1. Create Patient account
        patient_user = models.User(
            username="patient_demo",
            password_hash=hash_password("patient_pass"),
            role="patient"
        )
        db.add(patient_user)
        db.commit()
        db.refresh(patient_user)

        # Create corresponding Patient demographics
        patient_profile = models.Patient(
            user_id=patient_user.id,
            first_name="John",
            last_name="Doe",
            date_of_birth="1980-05-15",
            gender="Male",
            email="john.doe@example.com",
            phone="+1-555-0199"
        )
        db.add(patient_profile)
        db.commit()
        db.refresh(patient_profile)
        
        # 2. Create Admin account
        admin_user = models.User(
            username="admin_demo",
            password_hash=hash_password("admin_pass"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        print("Demo accounts created.")
    else:
        patient_user = db.query(models.User).filter(models.User.username == "patient_demo").first()
        patient_profile = patient_user.patient if patient_user else None

    # Seed Phase 6 synthetic data for patient_demo if not present
    if patient_profile and db.query(models.Medication).filter(models.Medication.patient_id == patient_profile.id).count() == 0:
        print("Seeding Phase 6 synthetic medications, vitals, and reminders...")
        med1 = models.Medication(
            patient_id=patient_profile.id,
            name="Lisinopril",
            dosage="10mg",
            frequency="Once daily",
            prescribed_by="Dr. Sarah Jenkins",
            start_date="2026-01-15",
            is_active=True,
            notes="For blood pressure management"
        )
        med2 = models.Medication(
            patient_id=patient_profile.id,
            name="Vitamin D3",
            dosage="1000 IU",
            frequency="Once daily",
            prescribed_by="Dr. Sarah Jenkins",
            start_date="2026-02-01",
            is_active=True,
            notes="Dietary supplement"
        )
        db.add(med1)
        db.add(med2)
        db.commit()
        db.refresh(med1)

        now = datetime.now(timezone.utc)
        vitals_data = [
            models.Vital(
                patient_id=patient_profile.id,
                vital_type="blood_pressure",
                value="120/80",
                unit="mmHg",
                recorded_at=now - timedelta(days=5),
                notes="Morning reading"
            ),
            models.Vital(
                patient_id=patient_profile.id,
                vital_type="blood_pressure",
                value="122/82",
                unit="mmHg",
                recorded_at=now - timedelta(days=3),
                notes="Morning reading"
            ),
            models.Vital(
                patient_id=patient_profile.id,
                vital_type="blood_pressure",
                value="118/78",
                unit="mmHg",
                recorded_at=now - timedelta(days=1),
                notes="Evening reading"
            ),
            models.Vital(
                patient_id=patient_profile.id,
                vital_type="heart_rate",
                value="72",
                unit="bpm",
                recorded_at=now - timedelta(days=3),
                notes="Resting pulse"
            ),
            models.Vital(
                patient_id=patient_profile.id,
                vital_type="heart_rate",
                value="75",
                unit="bpm",
                recorded_at=now - timedelta(days=1),
                notes="Resting pulse"
            ),
        ]
        db.add_all(vitals_data)

        reminders_data = [
            models.MedicationReminder(
                patient_id=patient_profile.id,
                medication_id=med1.id,
                reminder_text="Take Lisinopril 10mg",
                reminder_time="08:00 AM",
                status="active",
                notes="Take with morning meal"
            ),
            models.MedicationReminder(
                patient_id=patient_profile.id,
                medication_id=med2.id,
                reminder_text="Take Vitamin D3 1000 IU",
                reminder_time="08:00 AM",
                status="active",
                notes="Take with breakfast"
            ),
        ]
        db.add_all(reminders_data)

        db.commit()
        print("Phase 6 synthetic data seeding complete.")

    # Seed Phase 7 Knowledge Documents if not present
    if db.query(models.KnowledgeDocument).count() == 0:
        print("Seeding Phase 7 knowledge documents...")
        from app.services.embeddings import get_embedding_service
        emb_service = get_embedding_service()

        docs_data = [
            {
                "title": "Fever Symptom Navigation & Care Guidance",
                "content": "Rest, stay well-hydrated, and monitor body temperature. Seek professional medical evaluation if fever exceeds 103°F (39.4°C), lasts longer than 3 days, or is accompanied by severe headache or stiff neck.",
                "source": "CareGraph Curated Care Navigation Summary",
                "source_type": "clinical_guideline",
                "category": "triage",
                "version": "v1.0",
                "status": "active",
                "region": "US",
                "publication_date": "2026-01-01"
            },
            {
                "title": "Cough Assessment & Care Guidance",
                "content": "Stay hydrated, use warm liquids or throat lozenges, and rest. Consult a healthcare provider if cough persists beyond 2-3 weeks, produces blood, or causes shortness of breath.",
                "source": "CareGraph Curated Care Navigation Summary",
                "source_type": "clinical_guideline",
                "category": "triage",
                "version": "v1.0",
                "status": "active",
                "region": "US",
                "publication_date": "2026-01-01"
            },
            {
                "title": "Headache Triage & Management Guidance",
                "content": "Rest in a quiet, dark room, stay hydrated, and manage stress. Seek immediate medical attention if headache is sudden and unusually severe, or occurs with neurological symptoms.",
                "source": "CareGraph Curated Care Navigation Summary",
                "source_type": "clinical_guideline",
                "category": "triage",
                "version": "v1.0",
                "status": "active",
                "region": "US",
                "publication_date": "2026-01-01"
            },
            {
                "title": "Sore Throat Care Navigation & Warning Signs",
                "content": "Gargle with warm salt water, drink warm liquids, and rest your voice. Seek medical care if accompanied by difficulty swallowing, joint pain, or rash.",
                "source": "CareGraph Curated Care Navigation Summary",
                "source_type": "clinical_guideline",
                "category": "triage",
                "version": "v1.0",
                "status": "active",
                "region": "US",
                "publication_date": "2026-01-01"
            },
            {
                "title": "Skin Rash Evaluation & Care Guidance",
                "content": "Keep the area clean and dry, avoid scratching, and note any changes. Seek urgent medical attention if rash spreads rapidly, forms blisters, or is accompanied by fever or severe pain.",
                "source": "CareGraph Curated Care Navigation Summary",
                "source_type": "clinical_guideline",
                "category": "triage",
                "version": "v1.0",
                "status": "active",
                "region": "US",
                "publication_date": "2026-01-01"
            },
        ]
        initial_docs = [
            models.KnowledgeDocument(
                title=d["title"],
                content=d["content"],
                source=d["source"],
                source_type=d["source_type"],
                category=d["category"],
                version=d["version"],
                status=d["status"],
                region=d["region"],
                publication_date=d["publication_date"],
                embedding=emb_service.get_embedding(f"{d['title']} {d['content']}")
            )
            for d in docs_data
        ]
        db.add_all(initial_docs)
        db.commit()
        print("Phase 7 knowledge documents seeded.")

    # Seed Phase 8 default patient consents for patient_demo if not present
    if patient_profile and db.query(models.PatientConsent).filter(models.PatientConsent.patient_id == patient_profile.id).count() == 0:
        print("Seeding Phase 8 default patient consents...")
        standard_consents = [
            "data_access",
            "vital_tracking",
            "medication_tracking",
            "medication_reminders",
            "appointment_booking",
            "ai_processing",
        ]
        now = datetime.now(timezone.utc)
        for c_type in standard_consents:
            c = models.PatientConsent(
                patient_id=patient_profile.id,
                consent_type=c_type,
                status="granted",
                granted_at=now,
                expires_at=now + timedelta(days=365),
                version="v1.0"
            )
            db.add(c)
        db.commit()
        print("Phase 8 default patient consents seeded.")



def create_appointment(
    db: Session,
    patient_id: int,
    doctor_name: str,
    specialty: str,
    appointment_time: str,
    notes: str = None
):
    db_appointment = models.Appointment(
        patient_id=patient_id,
        doctor_name=doctor_name,
        specialty=specialty,
        appointment_time=appointment_time,
        status="scheduled",
        notes=notes
    )
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def get_patient_appointments(db: Session, patient_id: int):
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.patient_id == patient_id)
        .order_by(models.Appointment.created_at.desc())
        .all()
    )


def cancel_appointment(db: Session, patient_id: int, appointment_id: int):
    apt = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id, models.Appointment.patient_id == patient_id)
        .first()
    )
    if apt:
        apt.status = "cancelled"
        db.commit()
        db.refresh(apt)
    return apt


def get_patient_medications(db: Session, patient_id: int):
    return (
        db.query(models.Medication)
        .filter(models.Medication.patient_id == patient_id, models.Medication.is_active == True)
        .order_by(models.Medication.created_at.desc())
        .all()
    )


def get_patient_vitals(db: Session, patient_id: int, vital_type: str = None, limit: int = 10):
    query = db.query(models.Vital).filter(models.Vital.patient_id == patient_id)
    if vital_type:
        query = query.filter(models.Vital.vital_type == vital_type)
    return query.order_by(models.Vital.recorded_at.desc()).limit(limit).all()


def create_vital(
    db: Session,
    patient_id: int,
    vital_type: str,
    value: str,
    unit: str = None,
    recorded_at: datetime = None,
    source: str = "manual_entry",
    notes: str = None
):
    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)
    db_vital = models.Vital(
        patient_id=patient_id,
        vital_type=vital_type,
        value=value,
        unit=unit,
        recorded_at=recorded_at,
        source=source,
        notes=notes
    )
    db.add(db_vital)
    db.commit()
    db.refresh(db_vital)
    return db_vital


def get_medication_reminders(db: Session, patient_id: int):
    return (
        db.query(models.MedicationReminder)
        .filter(models.MedicationReminder.patient_id == patient_id)
        .order_by(models.MedicationReminder.created_at.desc())
        .all()
    )


def create_medication_reminder(
    db: Session,
    patient_id: int,
    reminder_text: str,
    reminder_time: str,
    medication_id: int = None,
    notes: str = None
):
    db_reminder = models.MedicationReminder(
        patient_id=patient_id,
        medication_id=medication_id,
        reminder_text=reminder_text,
        reminder_time=reminder_time,
        status="active",
        notes=notes
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


def cancel_medication_reminder(db: Session, patient_id: int, reminder_id: int):
    reminder = (
        db.query(models.MedicationReminder)
        .filter(models.MedicationReminder.id == reminder_id, models.MedicationReminder.patient_id == patient_id)
        .first()
    )
    if reminder:
        reminder.status = "cancelled"
        db.commit()
        db.refresh(reminder)
    return reminder


def create_knowledge_document(
    db: Session,
    title: str,
    content: str,
    source: str,
    source_type: str = "clinical_guideline",
    category: str = "triage",
    version: str = "v1.0",
    status: str = "active",
    region: str = "US",
    publication_date: str = None,
    embedding: list = None
):
    db_doc = models.KnowledgeDocument(
        title=title,
        content=content,
        source=source,
        source_type=source_type,
        category=category,
        version=version,
        status=status,
        region=region,
        publication_date=publication_date,
        embedding=embedding
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def get_knowledge_documents(
    db: Session,
    category: str = None,
    status: str = "active",
    limit: int = 50
):
    query = db.query(models.KnowledgeDocument)
    if status:
        query = query.filter(models.KnowledgeDocument.status == status)
    if category:
        query = query.filter(models.KnowledgeDocument.category == category)
    return query.order_by(models.KnowledgeDocument.id.asc()).limit(limit).all()


def get_knowledge_document_by_id(db: Session, doc_id: int):
    return db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()


# --- Phase 8 Consent Management CRUD Operations ---

def get_patient_consents(db: Session, patient_id: int):
    """Retrieve all consent records for a patient."""
    return db.query(models.PatientConsent).filter(
        models.PatientConsent.patient_id == patient_id
    ).order_by(models.PatientConsent.id.asc()).all()


def get_patient_consent_by_type(db: Session, patient_id: int, consent_type: str):
    """Retrieve the most recent consent record for a specific patient and consent type."""
    return db.query(models.PatientConsent).filter(
        models.PatientConsent.patient_id == patient_id,
        models.PatientConsent.consent_type == consent_type
    ).order_by(models.PatientConsent.id.desc()).first()


def grant_patient_consent(
    db: Session,
    patient_id: int,
    consent_type: str,
    expires_days: int = 365,
    version: str = "v1.0"
):
    """Grant or renew patient consent for a specified scope."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=expires_days) if expires_days else None

    existing = get_patient_consent_by_type(db, patient_id, consent_type)
    if existing:
        existing.status = "granted"
        existing.granted_at = now
        existing.revoked_at = None
        existing.expires_at = expires_at
        existing.version = version
        db.commit()
        db.refresh(existing)
        return existing

    consent = models.PatientConsent(
        patient_id=patient_id,
        consent_type=consent_type,
        status="granted",
        granted_at=now,
        expires_at=expires_at,
        version=version
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def revoke_patient_consent(db: Session, patient_id: int, consent_type: str):
    """Revoke patient consent for a specified scope."""
    now = datetime.now(timezone.utc)
    consent = get_patient_consent_by_type(db, patient_id, consent_type)
    if consent:
        consent.status = "revoked"
        consent.revoked_at = now
        db.commit()
        db.refresh(consent)
        return consent

    consent = models.PatientConsent(
        patient_id=patient_id,
        consent_type=consent_type,
        status="revoked",
        granted_at=now,
        revoked_at=now,
        version="v1.0"
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent




