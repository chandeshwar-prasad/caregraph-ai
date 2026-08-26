from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="patient")  # "patient" or "admin"

    patient = relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(String, nullable=True)  # Keeping simple string for flexibility, or Date
    gender = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    vitals = relationship("Vital", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    medication_reminders = relationship("MedicationReminder", back_populates="patient", cascade="all, delete-orphan")
    consents = relationship("PatientConsent", back_populates="patient", cascade="all, delete-orphan")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    appointment_time = Column(String, nullable=False)
    status = Column(String, nullable=False, default="scheduled")  # "scheduled", "cancelled"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="appointments")

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    prescribed_by = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="medications")
    reminders = relationship("MedicationReminder", back_populates="medication")

class MedicationReminder(Base):
    __tablename__ = "medication_reminders"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id", ondelete="CASCADE"), nullable=True)
    reminder_text = Column(String, nullable=False)
    reminder_time = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")  # "active", "cancelled"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="medication_reminders")
    medication = relationship("Medication", back_populates="reminders")

class Vital(Base):
    __tablename__ = "vitals"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    vital_type = Column(String, nullable=False)  # "blood_pressure", "heart_rate", "weight", "temperature", "spo2"
    value = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String, nullable=True, default="manual_entry")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="vitals")


from sqlalchemy import JSON

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=False)  # e.g. "CareGraph Curated Care Navigation Summary"
    source_type = Column(String, nullable=False, default="clinical_guideline")  # "clinical_guideline", "symptom_guide", "faq"
    category = Column(String, nullable=False, default="triage")  # "triage", "respiratory", "cardiology", "general"
    version = Column(String, nullable=False, default="v1.0")
    status = Column(String, nullable=False, default="active")  # "active", "stale", "superseded", "draft"
    region = Column(String, nullable=True, default="US")
    publication_date = Column(String, nullable=True)
    embedding = Column(JSON, nullable=True)
    ingestion_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())



class PatientConsent(Base):
    __tablename__ = "patient_consents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String, nullable=False, index=True)  # "data_access", "vital_tracking", "medication_tracking", "medication_reminders", "appointment_booking", "ai_processing"
    status = Column(String, nullable=False, default="granted")  # "granted", "revoked", "expired"
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(String, nullable=False, default="v1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="consents")



