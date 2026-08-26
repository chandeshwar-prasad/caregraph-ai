# HealthSync AI — Complete Codebase Bundle (Phases 1–6)

This document consolidates all core source code files of the HealthSync AI Agent (Phases 1–6) for technical architecture, security, and code-level review by Claude.

---

## Table of Contents
1. [`app/database.py`](#appdatabasepy)
2. [`app/models.py`](#appmodelspy)
3. [`app/schemas.py`](#appschemaspy)
4. [`app/schemas_ai.py`](#appschemas_aipy)
5. [`app/auth.py`](#appauthpy)
6. [`app/crud.py`](#appcrudpy)
7. [`app/main.py`](#appmainpy)
8. [`app/services/graph.py`](#appservicesgraphpy)
9. [`app/services/triage.py`](#appservicestriagepy)
10. [`app/services/scheduling.py`](#appservicesschedulingpy)
11. [`app/services/patient_data.py`](#appservicespatient_datapy)
12. [`app/services/audit.py`](#appservicesauditpy)
13. [`app/services/llm.py`](#appservicesllmpy)
14. [`.env.example`](#envexample)
15. [`walkthrough_phase6.md`](#walkthrough_phase6md)

---

### `app/database.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Helper to automatically create the database if it doesn't exist
def ensure_database_exists():
    try:
        # Parse the connection string to connect to 'postgres' default database first
        base_url, db_name = DATABASE_URL.rsplit('/', 1)
        
        # Connect to the default 'postgres' database
        conn = psycopg2.connect(f"{base_url}/postgres")
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if target database exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not automatically verify or create database: {e}")

# Call the helper
ensure_database_exists()

# Initialize SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### `app/models.py`

```python
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
    date_of_birth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    vitals = relationship("Vital", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    medication_reminders = relationship("MedicationReminder", back_populates="patient", cascade="all, delete-orphan")

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
```

---

### `app/schemas.py`

```python
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field("patient", pattern="^(patient|admin)$")

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class UserWithPatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    patient: Optional[PatientResponse] = None
```

---

### `app/schemas_ai.py`

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

class IntentEnum(str, Enum):
    TRIAGE = "triage"
    SCHEDULING = "scheduling"
    RECORDS = "records"
    REMINDERS = "reminders"
    GENERAL = "general"
    EMERGENCY = "emergency"

class IntentExtraction(BaseModel):
    intent: IntentEnum = Field(
        description="The primary intent category parsed from the user message."
    )
    confidence: float = Field(
        description="Confidence score for this classification, between 0.0 and 1.0."
    )
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value dictionary containing extracted entities (dates, symptoms, medication names)."
    )

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query message.")
    session_id: Optional[str] = Field(None, description="Optional conversation/thread session identifier.")

class ApprovalRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Conversation/thread session identifier.")
    decision: str = Field(..., description="Approval decision: 'approved' or 'rejected'.")

class ChatResponse(BaseModel):
    message: str = Field(description="The coordinator's reply response.")
    intent: str = Field(description="The classified user intent.")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entities extracted from the user's input.")
    is_mock: bool = Field(description="Flag indicating if the response was generated in mock/development mode.")
    session_id: str = Field(description="The active conversation session/thread identifier.")
    approval_required: bool = Field(default=False, description="Flag indicating if human approval is pending.")
    approval_status: Optional[str] = Field(default=None, description="Current approval status ('pending', 'approved', 'rejected', or None).")
    risk_level: Optional[str] = Field(default=None, description="Triage risk level ('emergency', 'urgent', 'non_urgent').")
    safety_escalated: bool = Field(default=False, description="Flag indicating if deterministic red-flag safety escalation occurred.")
    follow_up_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions for symptom screening.")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Grounded knowledge citations.")
    selected_slot: Optional[Dict[str, Any]] = Field(default=None, description="Scheduling slot details presented for HITL confirmation.")

class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_name: str
    specialty: str
    appointment_time: str
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class VitalCreate(BaseModel):
    vital_type: str = Field(..., description="Vital sign type ('blood_pressure', 'heart_rate', 'weight', 'temperature', 'spo2')")
    value: str = Field(..., description="Measurement value (e.g. '120/80', '72')")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g. 'mmHg', 'bpm')")
    recorded_at: Optional[datetime] = Field(None, description="Recorded timestamp")
    notes: Optional[str] = Field(None, description="Optional notes")

class VitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    vital_type: str
    value: str
    unit: Optional[str] = None
    recorded_at: Optional[datetime] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    name: str
    dosage: str
    frequency: str
    prescribed_by: Optional[str] = None
    start_date: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class MedicationReminderCreate(BaseModel):
    reminder_text: str = Field(..., description="Reminder text (e.g. 'Take Lisinopril 10mg')")
    reminder_time: str = Field(..., description="Reminder time string (e.g. '08:00 AM')")
    medication_id: Optional[int] = Field(None, description="Optional linked medication ID")
    notes: Optional[str] = Field(None, description="Optional notes")

class MedicationReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    medication_id: Optional[int] = None
    reminder_text: str
    reminder_time: str
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
```

---

### `app/auth.py`

```python
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import bcrypt
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

JWT_SECRET = os.getenv("JWT_SECRET", "default_secret_key_if_none_set_in_env_file_12345")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username, role=role)
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for current user role"
            )
        return current_user

require_role = lambda role: RoleChecker([role])
```

---

### `app/crud.py`

```python
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
    return db_patient

def seed_initial_data(db: Session):
    if db.query(models.User).count() == 0:
        patient_user = models.User(
            username="patient_demo",
            password_hash=hash_password("patient_pass"),
            role="patient"
        )
        db.add(patient_user)
        db.commit()
        db.refresh(patient_user)

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
        
        admin_user = models.User(
            username="admin_demo",
            password_hash=hash_password("admin_pass"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()

    else:
        patient_user = db.query(models.User).filter(models.User.username == "patient_demo").first()
        patient_profile = patient_user.patient if patient_user else None

    if patient_profile and db.query(models.Medication).filter(models.Medication.patient_id == patient_profile.id).count() == 0:
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
            models.Vital(patient_id=patient_profile.id, vital_type="blood_pressure", value="120/80", unit="mmHg", recorded_at=now - timedelta(days=5), notes="Morning reading"),
            models.Vital(patient_id=patient_profile.id, vital_type="blood_pressure", value="122/82", unit="mmHg", recorded_at=now - timedelta(days=3), notes="Morning reading"),
            models.Vital(patient_id=patient_profile.id, vital_type="blood_pressure", value="118/78", unit="mmHg", recorded_at=now - timedelta(days=1), notes="Evening reading"),
            models.Vital(patient_id=patient_profile.id, vital_type="heart_rate", value="72", unit="bpm", recorded_at=now - timedelta(days=3), notes="Resting pulse"),
            models.Vital(patient_id=patient_profile.id, vital_type="heart_rate", value="75", unit="bpm", recorded_at=now - timedelta(days=1), notes="Resting pulse"),
        ]
        db.add_all(vitals_data)

        reminders_data = [
            models.MedicationReminder(patient_id=patient_profile.id, medication_id=med1.id, reminder_text="Take Lisinopril 10mg", reminder_time="08:00 AM", status="active", notes="Take with morning meal"),
            models.MedicationReminder(patient_id=patient_profile.id, medication_id=med2.id, reminder_text="Take Vitamin D3 1000 IU", reminder_time="08:00 AM", status="active", notes="Take with breakfast"),
        ]
        db.add_all(reminders_data)
        db.commit()

def create_appointment(db: Session, patient_id: int, doctor_name: str, specialty: str, appointment_time: str, notes: str = None):
    db_appointment = models.Appointment(patient_id=patient_id, doctor_name=doctor_name, specialty=specialty, appointment_time=appointment_time, status="scheduled", notes=notes)
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

def get_patient_appointments(db: Session, patient_id: int):
    return db.query(models.Appointment).filter(models.Appointment.patient_id == patient_id).order_by(models.Appointment.created_at.desc()).all()

def cancel_appointment(db: Session, patient_id: int, appointment_id: int):
    apt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id, models.Appointment.patient_id == patient_id).first()
    if apt:
        apt.status = "cancelled"
        db.commit()
        db.refresh(apt)
    return apt

def get_patient_medications(db: Session, patient_id: int):
    return db.query(models.Medication).filter(models.Medication.patient_id == patient_id, models.Medication.is_active == True).order_by(models.Medication.created_at.desc()).all()

def get_patient_vitals(db: Session, patient_id: int, vital_type: str = None, limit: int = 10):
    query = db.query(models.Vital).filter(models.Vital.patient_id == patient_id)
    if vital_type:
        query = query.filter(models.Vital.vital_type == vital_type)
    return query.order_by(models.Vital.recorded_at.desc()).limit(limit).all()

def create_vital(db: Session, patient_id: int, vital_type: str, value: str, unit: str = None, recorded_at: datetime = None, source: str = "manual_entry", notes: str = None):
    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)
    db_vital = models.Vital(patient_id=patient_id, vital_type=vital_type, value=value, unit=unit, recorded_at=recorded_at, source=source, notes=notes)
    db.add(db_vital)
    db.commit()
    db.refresh(db_vital)
    return db_vital

def get_medication_reminders(db: Session, patient_id: int):
    return db.query(models.MedicationReminder).filter(models.MedicationReminder.patient_id == patient_id).order_by(models.MedicationReminder.created_at.desc()).all()

def create_medication_reminder(db: Session, patient_id: int, reminder_text: str, reminder_time: str, medication_id: int = None, notes: str = None):
    db_reminder = models.MedicationReminder(patient_id=patient_id, medication_id=medication_id, reminder_text=reminder_text, reminder_time=reminder_time, status="active", notes=notes)
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder

def cancel_medication_reminder(db: Session, patient_id: int, reminder_id: int):
    reminder = db.query(models.MedicationReminder).filter(models.MedicationReminder.id == reminder_id, models.MedicationReminder.patient_id == patient_id).first()
    if reminder:
        reminder.status = "cancelled"
        db.commit()
        db.refresh(reminder)
    return reminder
```

---

### `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from app import models, schemas, crud, auth, schemas_ai
from app.services import patient_data
from app.services.llm import (
    get_llm_service,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMError
)
from app.database import engine, SessionLocal, get_db

import logging
from langgraph.types import Command
from app.services.graph import graph

logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    crud.seed_initial_data(db)
finally:
    db.close()

app = FastAPI(
    title="HealthSync AI - Care Coordination API",
    description="Multi-Agent, Multi-Model Healthcare Navigation & Care-Management Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "mode": "development"
    }

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/patients/me", response_model=schemas.PatientResponse)
def get_my_patient_profile(
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    if not current_user.patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return current_user.patient

@app.post("/patients/me", response_model=schemas.PatientResponse, status_code=status.HTTP_201_CREATED)
def create_my_patient_profile(
    patient: schemas.PatientCreate,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    if current_user.patient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient profile already exists")
    return crud.create_patient_profile(db=db, user_id=current_user.id, patient=patient)

@app.get("/admin/patients", response_model=List[schemas.PatientResponse])
def get_all_patients(
    current_user: models.User = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db)
):
    return db.query(models.Patient).all()

@app.post("/chat", response_model=schemas_ai.ChatResponse)
def chat_coordination(
    request: schemas_ai.ChatRequest,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    try:
        user_session_key = request.session_id or "default"
        thread_id = f"user_{current_user.id}_{user_session_key}"
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "user_message": request.message,
            "user_id": current_user.id,
            "session_id": thread_id
        }
        
        graph.invoke(initial_state, config=config)
        snapshot = graph.get_state(config)
        state_values = snapshot.values
        
        is_interrupted = len(snapshot.tasks) > 0 and len(snapshot.tasks[0].interrupts) > 0
        
        if is_interrupted:
            interrupt_val = snapshot.tasks[0].interrupts[0].value
            msg = interrupt_val.get("message") if isinstance(interrupt_val, dict) else str(interrupt_val)
            slot = interrupt_val.get("selected_slot") if isinstance(interrupt_val, dict) else None
            return {
                "message": msg,
                "intent": state_values.get("intent", "scheduling"),
                "entities": state_values.get("extracted_entities", {}),
                "is_mock": state_values.get("is_mock", True),
                "session_id": user_session_key,
                "approval_required": True,
                "approval_status": "pending",
                "risk_level": state_values.get("risk_level"),
                "safety_escalated": state_values.get("safety_escalated", False),
                "follow_up_questions": state_values.get("follow_up_questions", []),
                "sources": state_values.get("retrieved_sources", []),
                "selected_slot": slot
            }
        else:
            return {
                "message": state_values.get("final_response", state_values.get("response_draft", "")),
                "intent": state_values.get("intent", "general"),
                "entities": state_values.get("extracted_entities", {}),
                "is_mock": state_values.get("is_mock", True),
                "session_id": user_session_key,
                "approval_required": state_values.get("approval_required", False),
                "approval_status": state_values.get("approval_status"),
                "risk_level": state_values.get("risk_level"),
                "safety_escalated": state_values.get("safety_escalated", False),
                "follow_up_questions": state_values.get("follow_up_questions", []),
                "sources": state_values.get("retrieved_sources", []),
                "selected_slot": state_values.get("selected_slot")
            }

    except LLMTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="The AI assistant request timed out.")
    except Exception as e:
        logger.error(f"Unhandled error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The care coordination service encountered an error processing your request.")

@app.post("/chat/approve", response_model=schemas_ai.ChatResponse)
def approve_coordination(
    request: schemas_ai.ApprovalRequest,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    if request.decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be either 'approved' or 'rejected'.")
    try:
        user_session_key = request.session_id or "default"
        thread_id = f"user_{current_user.id}_{user_session_key}"
        config = {"configurable": {"thread_id": thread_id}}

        snapshot = graph.get_state(config)
        if not snapshot.next or snapshot.next[0] != "scheduling":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending approval workflow found for this session.")

        resumed_state = graph.invoke(Command(resume={"approval_status": request.decision}), config=config)

        return {
            "message": resumed_state.get("final_response", resumed_state.get("response_draft", "")),
            "intent": resumed_state.get("intent", "scheduling"),
            "entities": resumed_state.get("extracted_entities", {}),
            "is_mock": resumed_state.get("is_mock", True),
            "session_id": user_session_key,
            "approval_required": False,
            "approval_status": request.decision,
            "risk_level": resumed_state.get("risk_level"),
            "safety_escalated": resumed_state.get("safety_escalated", False),
            "follow_up_questions": resumed_state.get("follow_up_questions", []),
            "sources": resumed_state.get("retrieved_sources", []),
            "selected_slot": resumed_state.get("selected_slot")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in approve endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The assistant service encountered an error processing your approval decision.")

@app.get("/appointments/me", response_model=List[schemas_ai.AppointmentResponse])
def get_my_appointments(current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(db, current_user.id, schemas.PatientCreate(first_name=current_user.username, last_name="Patient", email=f"{current_user.username}@example.com"))
    return crud.get_patient_appointments(db, patient.id)

@app.post("/appointments/{appointment_id}/cancel", response_model=schemas_ai.AppointmentResponse)
def cancel_my_appointment(appointment_id: int, current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(db, current_user.id, schemas.PatientCreate(first_name=current_user.username, last_name="Patient", email=f"{current_user.username}@example.com"))
    cancelled_apt = crud.cancel_appointment(db, patient.id, appointment_id)
    if not cancelled_apt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found or does not belong to current patient.")
    return cancelled_apt

@app.get("/vitals/me", response_model=List[schemas_ai.VitalResponse])
def get_my_vitals(vital_type: Optional[str] = Query(None), limit: int = Query(10, ge=1, le=100), current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    return patient_data.get_patient_vitals(db, current_user.id, vital_type=vital_type, limit=limit)

@app.post("/vitals/me", response_model=schemas_ai.VitalResponse, status_code=status.HTTP_201_CREATED)
def record_my_vital(payload: schemas_ai.VitalCreate, current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    result = patient_data.store_vital(db, user_id=current_user.id, vital_type=payload.vital_type, value=payload.value, unit=payload.unit, recorded_at=payload.recorded_at, notes=payload.notes)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result

@app.get("/medications/me", response_model=List[schemas_ai.MedicationResponse])
def get_my_medications(current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    return patient_data.get_patient_medications(db, current_user.id)

@app.get("/reminders/me", response_model=List[schemas_ai.MedicationReminderResponse])
def get_my_reminders(current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        return []
    return crud.get_medication_reminders(db, patient.id)

@app.post("/reminders/me", response_model=schemas_ai.MedicationReminderResponse, status_code=status.HTTP_201_CREATED)
def create_my_reminder(payload: schemas_ai.MedicationReminderCreate, current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    result = patient_data.create_medication_reminder(db, user_id=current_user.id, reminder_text=payload.reminder_text, reminder_time=payload.reminder_time, medication_id=payload.medication_id, notes=payload.notes)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result

@app.post("/reminders/{reminder_id}/cancel", response_model=schemas_ai.MedicationReminderResponse)
def cancel_my_reminder(reminder_id: int, current_user: models.User = Depends(auth.require_role("patient")), db: Session = Depends(get_db)):
    cancelled = patient_data.cancel_reminder(db, current_user.id, reminder_id)
    if not cancelled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication reminder not found or does not belong to current patient.")
    return cancelled
```

---

### `app/services/graph.py`

```python
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.database import SessionLocal
import app.models as models
from app.schemas_ai import IntentEnum, IntentExtraction

import app.services.llm as llm_module
from app.services.triage import evaluate_red_flags, get_deterministic_emergency_response, evaluate_triage_risk, build_triage_response
from app.services.knowledge import get_grounded_knowledge
from app.services.audit import log_audit_event
from app.services.scheduling import search_available_slots, book_appointment_slot, cancel_appointment_slot
from app.services import patient_data

class HealthSyncState(TypedDict, total=False):
    session_id: str
    user_id: int
    user_message: str
    intent: Optional[str]
    confidence: float
    extracted_entities: Dict[str, Any]
    current_agent: str
    approval_required: bool
    approval_status: Optional[str]
    risk_level: Optional[str]
    safety_escalated: bool
    retrieved_sources: List[Dict[str, Any]]
    follow_up_questions: List[str]
    selected_slot: Dict[str, Any]
    appointment_id: Optional[int]
    patient_data_result: Optional[Dict[str, Any]]
    patient_data_tool: Optional[str]
    response_draft: str
    final_response: str
    is_mock: bool

def input_screening_node(state: HealthSyncState) -> Dict[str, Any]:
    user_msg = state.get("user_message", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", 0)

    if len(user_msg) > 2000:
        log_audit_event(session_id, user_id, "unknown", "input_screening", "non_urgent", True, True)
        return {"current_agent": "input_screening", "safety_escalated": True, "risk_level": "non_urgent", "response_draft": "Your query exceeds the maximum allowed message length."}

    injection_keywords = ["ignore your safety", "ignore previous instructions", "override safety", "bypass safety"]
    if any(kw in user_msg.lower() for kw in injection_keywords):
        log_audit_event(session_id, user_id, "unknown", "input_screening", "non_urgent", True, True)
        return {"current_agent": "input_screening", "safety_escalated": True, "risk_level": "non_urgent", "response_draft": "I am a healthcare coordination assistant. I cannot follow instructions to bypass safety rules."}

    if evaluate_red_flags(user_msg):
        log_audit_event(session_id, user_id, "emergency", "emergency_safety", "emergency", True, True)
        return {"current_agent": "emergency_safety", "intent": "emergency", "risk_level": "emergency", "safety_escalated": True, "response_draft": get_deterministic_emergency_response()}

    return {"safety_escalated": False}

def route_after_screening(state: HealthSyncState) -> str:
    if state.get("safety_escalated"):
        return "responder"
    return "supervisor"

def supervisor_node(state: HealthSyncState) -> Dict[str, Any]:
    user_msg = state.get("user_message", "")
    llm_service: llm_module.BaseLLMService = llm_module.get_llm_service()
    intent_info: IntentExtraction = llm_service.extract_intent(user_msg)
    return {"intent": intent_info.intent.value, "confidence": intent_info.confidence, "extracted_entities": intent_info.extracted_entities, "is_mock": llm_service.is_mock_mode(), "current_agent": "supervisor"}

def route_by_intent(state: HealthSyncState) -> str:
    intent = state.get("intent", IntentEnum.GENERAL.value)
    if intent == IntentEnum.TRIAGE.value: return "triage"
    elif intent == IntentEnum.SCHEDULING.value: return "scheduling"
    elif intent == IntentEnum.RECORDS.value: return "records"
    elif intent == IntentEnum.REMINDERS.value: return "reminders"
    elif intent == IntentEnum.EMERGENCY.value: return "emergency"
    else: return "general"

def triage_node(state: HealthSyncState) -> Dict[str, Any]:
    user_msg = state.get("user_message", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", 0)
    entities = state.get("extracted_entities", {})

    knowledge_items = get_grounded_knowledge(user_msg)
    risk_level = evaluate_triage_risk(user_msg, entities)
    resp_text, follow_ups = build_triage_response(user_msg, risk_level, knowledge_items)

    log_audit_event(session_id=session_id, user_id=user_id, intent="triage", selected_agent="triage", risk_level=risk_level, safety_escalated=False, is_mock=state.get("is_mock", True))

    return {"current_agent": "triage", "risk_level": risk_level, "safety_escalated": False, "retrieved_sources": knowledge_items, "follow_up_questions": follow_ups, "response_draft": resp_text, "approval_required": False}

def scheduling_node(state: HealthSyncState) -> Dict[str, Any]:
    approval_status = state.get("approval_status")
    user_id = state.get("user_id", 1)
    entities = state.get("extracted_entities", {})
    pref = entities.get("date_preference", "tomorrow")
    spec = entities.get("doctor_specialty", "the doctor")

    available_slots = search_available_slots(specialty=spec, date_pref=pref)
    selected_slot = available_slots[0] if available_slots else {"doctor_name": f"Dr. Alex Smith ({spec})", "specialty": spec, "appointment_time": f"{pref} at 10:00 AM"}

    if approval_status == "approved":
        db = SessionLocal()
        try:
            patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
            if not patient:
                patient = models.Patient(user_id=user_id, first_name="Demo", last_name="Patient")
                db.add(patient)
                db.commit()
                db.refresh(patient)
            apt = book_appointment_slot(db=db, patient_id=patient.id, doctor_name=selected_slot["doctor_name"], specialty=selected_slot["specialty"], appointment_time=selected_slot["appointment_time"], notes="Phase 5 Demo Appointment")
            msg = f"✅ **Mock Demo Appointment Confirmed!**\n\n• **Doctor:** {apt.doctor_name}\n• **Specialty:** {apt.specialty}\n• **Time:** {apt.appointment_time}\n• **Appointment ID:** #{apt.id}\n\n*(Note: Phase 5 mock appointment verified.)*"
            return {"current_agent": "scheduling", "approval_required": False, "approval_status": "approved", "appointment_id": apt.id, "selected_slot": selected_slot, "response_draft": msg}
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    elif approval_status == "rejected":
        msg = f"Appointment request with {selected_slot['doctor_name']} around {selected_slot['appointment_time']} was REJECTED by user. No action was taken."
        return {"current_agent": "scheduling", "approval_required": False, "approval_status": "rejected", "selected_slot": selected_slot, "response_draft": msg}
    else:
        confirm_msg = f"Please confirm: Do you want to schedule an appointment with {selected_slot['doctor_name']} around {selected_slot['appointment_time']}?"
        decision = interrupt({"action": "approval_required", "message": confirm_msg, "selected_slot": selected_slot})
        status = decision.get("approval_status", "approved") if isinstance(decision, dict) else (decision if isinstance(decision, str) else "approved")

        if status == "approved":
            db = SessionLocal()
            try:
                patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
                if not patient:
                    patient = models.Patient(user_id=user_id, first_name="Demo", last_name="Patient")
                    db.add(patient)
                    db.commit()
                    db.refresh(patient)
                apt = book_appointment_slot(db=db, patient_id=patient.id, doctor_name=selected_slot["doctor_name"], specialty=selected_slot["specialty"], appointment_time=selected_slot["appointment_time"], notes="Phase 5 Demo Appointment")
                res_msg = f"✅ **Mock Demo Appointment Confirmed!**\n\n• **Doctor:** {apt.doctor_name}\n• **Specialty:** {apt.specialty}\n• **Time:** {apt.appointment_time}\n• **Appointment ID:** #{apt.id}\n\n*(Note: Phase 5 mock appointment verified.)*"
                return {"current_agent": "scheduling", "approval_required": False, "approval_status": "approved", "appointment_id": apt.id, "selected_slot": selected_slot, "response_draft": res_msg}
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            res_msg = f"Appointment request with {selected_slot['doctor_name']} around {selected_slot['appointment_time']} was REJECTED by user. No action was taken."
            return {"current_agent": "scheduling", "approval_required": False, "approval_status": "rejected", "selected_slot": selected_slot, "response_draft": res_msg}

def patient_data_node(state: HealthSyncState) -> Dict[str, Any]:
    intent = state.get("intent", "records")
    user_id = state.get("user_id", 1)
    session_id = state.get("session_id", "default")
    user_msg = state.get("user_message", "")
    entities = state.get("extracted_entities", {})
    msg_lower = user_msg.lower()

    db = SessionLocal()
    try:
        patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
        if not patient:
            patient = models.Patient(user_id=user_id, first_name="Demo", last_name="Patient")
            db.add(patient)
            db.commit()
            db.refresh(patient)

        tool_result = None
        tool_name = "patient_data"
        draft = ""

        if intent == IntentEnum.RECORDS.value or intent == "records":
            vital_keywords = ["vital", "vitals", "bp", "blood pressure", "heart rate", "pulse", "weight", "temp", "temperature", "spo2"]
            med_keywords = ["medication", "medications", "medicine", "medicines", "drug", "drugs", "prescription", "rx", "pill", "pills"]

            if any(kw in msg_lower for kw in vital_keywords):
                is_trend = any(kw in msg_lower for kw in ["trend", "trending", "history", "track", "tracking", "over time"])
                vital_type = "blood_pressure" if ("blood pressure" in msg_lower or "bp" in msg_lower) else ("heart_rate" if ("heart rate" in msg_lower or "pulse" in msg_lower) else ("weight" if "weight" in msg_lower else ("temperature" if ("temp" in msg_lower or "temperature" in msg_lower) else ("spo2" if ("spo2" in msg_lower or "oxygen" in msg_lower) else None))))

                if is_trend and vital_type:
                    tool_name = "calculate_vital_trend"
                    tool_result = patient_data.calculate_vital_trend(db, user_id=user_id, vital_type=vital_type)
                    draft = f"📊 **{vital_type.replace('_', ' ').title()} Trend Analysis**\n\n• **Readings Analyzed:** {tool_result.get('count', 0)}\n• **Trend Direction:** {tool_result.get('trend', 'no_data').title()}"
                else:
                    tool_name = "get_patient_vitals"
                    tool_result = patient_data.get_patient_vitals(db, user_id=user_id, vital_type=vital_type)
                    if tool_result:
                        v_lines = [f"• **{v['vital_type'].replace('_', ' ').title()}:** {v['value']} {v.get('unit') or ''}" for v in tool_result]
                        draft = "📈 **Your Vital Sign Readings**\n\n" + "\n".join(v_lines)
                    else:
                        draft = "No vital sign readings found for your profile."

            elif any(kw in msg_lower for kw in med_keywords):
                tool_name = "get_patient_medications"
                tool_result = patient_data.get_patient_medications(db, user_id=user_id)
                if tool_result:
                    m_lines = [f"• **{m['name']}** ({m['dosage']}) - {m['frequency']}" for m in tool_result]
                    draft = "💊 **Your Active Medications**\n\n" + "\n".join(m_lines)
                else:
                    draft = "No active medications found in your records."

            else:
                tool_name = "get_patient_profile"
                profile = patient_data.get_patient_profile(db, user_id=user_id)
                meds = patient_data.get_patient_medications(db, user_id=user_id)
                vitals = patient_data.get_patient_vitals(db, user_id=user_id, limit=3)
                tool_result = {"profile": profile, "medications": meds, "vitals": vitals}
                draft = f"📋 **Patient Health Record Summary**\n\n• **Patient Name:** {profile.get('first_name', '')} {profile.get('last_name', '')}\n• **Active Medications:** {len(meds)}\n• **Recent Vitals Recorded:** {len(vitals)}"

        elif intent == IntentEnum.REMINDERS.value or intent == "reminders":
            create_keywords = ["remind me", "set reminder", "create reminder", "schedule reminder", "add reminder", "new reminder"]
            cancel_keywords = ["cancel reminder", "remove reminder", "delete reminder"]

            if any(kw in msg_lower for kw in create_keywords):
                tool_name = "create_medication_reminder"
                rem_text = entities.get("reminder_text") or user_msg
                rem_time = entities.get("reminder_time") or "08:00 AM"
                tool_result = patient_data.create_medication_reminder(db, user_id=user_id, reminder_text=rem_text, reminder_time=rem_time)
                draft = f"⏰ **Medication Reminder Scheduled!**\n\n• **Reminder:** {tool_result.get('reminder_text')}\n• **Time:** {tool_result.get('reminder_time')}\n• **Status:** Active"

            elif any(kw in msg_lower for kw in cancel_keywords):
                tool_name = "cancel_reminder"
                rem_id = entities.get("reminder_id")
                if rem_id:
                    tool_result = patient_data.cancel_reminder(db, user_id=user_id, reminder_id=int(rem_id))
                    draft = f"❌ Medication reminder #{rem_id} has been cancelled." if tool_result else f"Reminder #{rem_id} was not found."
                else:
                    tool_result = {"error": "reminder_id missing"}
                    draft = "Please specify the reminder ID you would like to cancel."

            else:
                tool_name = "get_medication_schedule"
                tool_result = patient_data.get_medication_schedule(db, user_id=user_id)
                if tool_result:
                    r_lines = [f"• **Reminder #{r['id']}:** {r['reminder_text']} at {r['reminder_time']}" for r in tool_result]
                    draft = "⏰ **Your Active Medication Reminders**\n\n" + "\n".join(r_lines)
                else:
                    draft = "You have no active medication reminders."

        else:
            tool_name = "get_patient_profile"
            tool_result = patient_data.get_patient_profile(db, user_id=user_id)
            draft = "Patient Record Service ready."

        log_audit_event(session_id=session_id, user_id=user_id, intent=intent, selected_agent="patient_data", risk_level="non_urgent", safety_escalated=False, is_mock=state.get("is_mock", True), tool_name=tool_name, patient_id=patient.id, tool_result="success")

        return {"current_agent": intent, "patient_data_result": tool_result, "patient_data_tool": tool_name, "response_draft": draft, "approval_required": False}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def emergency_stub_node(state: HealthSyncState) -> Dict[str, Any]:
    return {"current_agent": "emergency", "risk_level": "emergency", "safety_escalated": True, "response_draft": get_deterministic_emergency_response(), "approval_required": False}

def general_stub_node(state: HealthSyncState) -> Dict[str, Any]:
    llm_service: llm_module.BaseLLMService = llm_module.get_llm_service()
    user_msg = state.get("user_message", "")
    resp = llm_service.generate_response(user_msg, IntentExtraction(intent=IntentEnum.GENERAL, confidence=state.get("confidence", 0.8), extracted_entities=state.get("extracted_entities", {})))
    return {"current_agent": "general", "response_draft": resp, "approval_required": False}

def responder_node(state: HealthSyncState) -> Dict[str, Any]:
    return {"final_response": state.get("response_draft", "I am your HealthSync assistant.")}

builder = StateGraph(HealthSyncState)

builder.add_node("input_screening", input_screening_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("triage", triage_node)
builder.add_node("scheduling", scheduling_node)
builder.add_node("records", patient_data_node)
builder.add_node("reminders", patient_data_node)
builder.add_node("emergency", emergency_stub_node)
builder.add_node("general", general_stub_node)
builder.add_node("responder", responder_node)

builder.add_edge(START, "input_screening")
builder.add_conditional_edges("input_screening", route_after_screening, {"responder": "responder", "supervisor": "supervisor"})
builder.add_conditional_edges("supervisor", route_by_intent, {"triage": "triage", "scheduling": "scheduling", "records": "records", "reminders": "reminders", "emergency": "emergency", "general": "general"})
builder.add_edge("triage", "responder")
builder.add_edge("scheduling", "responder")
builder.add_edge("records", "responder")
builder.add_edge("reminders", "responder")
builder.add_edge("emergency", "responder")
builder.add_edge("general", "responder")
builder.add_edge("responder", END)

memory_checkpointer = MemorySaver()
graph = builder.compile(checkpointer=memory_checkpointer)
```

---

### `app/services/triage.py`

```python
from typing import List, Dict, Any, Tuple

RED_FLAG_PATTERNS = [
    "chest pain", "shortness of breath", "can't breathe", "cannot breathe", "difficulty breathing",
    "sudden numbness", "sudden weakness", "severe bleeding", "unconscious", "anaphylaxis",
    "loss of consciousness", "stroke symptoms", "slurred speech", "face drooping", "heart attack",
    "cardiac arrest", "stopped breathing", "not breathing"
]

URGENT_PATTERNS = [
    "high fever", "severe headache", "persistent vomiting", "spreading rash", "severe abdominal pain", "stiff neck"
]

def evaluate_red_flags(text: str) -> bool:
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in RED_FLAG_PATTERNS)

def get_deterministic_emergency_response() -> str:
    return (
        "🚨 **EMERGENCY SAFETY ESCALATION DETECTED**\n\n"
        "Your symptoms indicate a potential medical emergency that requires immediate professional clinical evaluation.\n\n"
        "**Recommended Action:**\n"
        "• Contact your local emergency services (such as 911 / 112 / 102) immediately or go to the nearest emergency room.\n"
        "• Do not attempt self-treatment or delay emergency care.\n\n"
        "*Disclaimer: HealthSync AI is a care-coordination assistant, not an emergency medical service.*"
    )

def evaluate_triage_risk(text: str, entities: Dict[str, Any]) -> str:
    if evaluate_red_flags(text):
        return "emergency"
    if any(pattern in text.lower() for pattern in URGENT_PATTERNS):
        return "urgent"
    return "non_urgent"

def build_triage_response(user_msg: str, risk_level: str, knowledge_items: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    if risk_level == "emergency":
        return get_deterministic_emergency_response(), []

    disclaimer = "*(Note: I am a care-coordination assistant, not a doctor. I cannot provide clinical diagnoses or prescribe medications.)*\n\n"
    content_parts = [disclaimer]

    if risk_level == "urgent":
        content_parts.append("⚠️ **Urgent Evaluation Advised:** Your reported symptoms warrant prompt evaluation by a healthcare provider.\n")

    if knowledge_items:
        content_parts.append("**Care Navigation Guidance:**\n")
        for item in knowledge_items:
            content_parts.append(f"• {item['guidance']}\n")
    else:
        content_parts.append("For your reported symptoms, please monitor your condition, rest, and stay hydrated.\n")

    follow_up_questions = [
        "How long have you been experiencing these symptoms?",
        "Are your symptoms getting progressively worse or staying the same?",
        "Would you like me to help schedule an appointment with a healthcare provider?"
    ]

    return "\n".join(content_parts).strip(), follow_up_questions
```

---

### `app/services/scheduling.py`

```python
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app import crud, models

def search_available_slots(specialty: str = "General Practitioner", date_pref: str = "tomorrow") -> List[Dict[str, Any]]:
    spec = specialty.capitalize() if specialty else "General Practitioner"
    pref = date_pref if date_pref else "tomorrow"
    return [
        {"slot_id": "slot_01", "doctor_name": f"Dr. Alex Smith ({spec})", "specialty": spec, "appointment_time": f"{pref} at 10:00 AM", "is_mock": True, "source_name": "Mock Availability Provider"},
        {"slot_id": "slot_02", "doctor_name": f"Dr. Jordan Lee ({spec})", "specialty": spec, "appointment_time": f"{pref} at 02:30 PM", "is_mock": True, "source_name": "Mock Availability Provider"}
    ]

def book_appointment_slot(db: Session, patient_id: int, doctor_name: str, specialty: str, appointment_time: str, notes: Optional[str] = "Phase 5 Demo Appointment") -> models.Appointment:
    appointment = crud.create_appointment(db=db, patient_id=patient_id, doctor_name=doctor_name, specialty=specialty, appointment_time=appointment_time, notes=notes)
    if not appointment or not appointment.id:
        raise RuntimeError("Database persistence verification failed: Appointment record was not created.")
    return appointment

def cancel_appointment_slot(db: Session, patient_id: int, appointment_id: int) -> Optional[models.Appointment]:
    return crud.cancel_appointment(db=db, patient_id=patient_id, appointment_id=appointment_id)
```

---

### `app/services/patient_data.py`

```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app import models, crud

ALLOWED_VITAL_TYPES = {"blood_pressure", "heart_rate", "weight", "temperature", "spo2"}

def _get_patient_by_user_id(db: Session, user_id: int) -> Optional[models.Patient]:
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()

def get_patient_profile(db: Session, user_id: int) -> Dict[str, Any]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient:
        return {"error": "Patient profile not found"}
    return {"id": patient.id, "first_name": patient.first_name, "last_name": patient.last_name, "date_of_birth": patient.date_of_birth, "gender": patient.gender, "email": patient.email, "phone": patient.phone}

def get_patient_medications(db: Session, user_id: int) -> List[Dict[str, Any]]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return []
    meds = crud.get_patient_medications(db, patient.id)
    return [{"id": m.id, "patient_id": m.patient_id, "name": m.name, "dosage": m.dosage, "frequency": m.frequency, "prescribed_by": m.prescribed_by, "start_date": m.start_date, "is_active": m.is_active, "notes": m.notes} for m in meds]

def get_patient_vitals(db: Session, user_id: int, vital_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return []
    vitals = crud.get_patient_vitals(db, patient.id, vital_type=vital_type, limit=limit)
    return [{"id": v.id, "patient_id": v.patient_id, "vital_type": v.vital_type, "value": v.value, "unit": v.unit, "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None, "source": v.source, "notes": v.notes} for v in vitals]

def store_vital(db: Session, user_id: int, vital_type: str, value: str, unit: Optional[str] = None, recorded_at: Optional[datetime] = None, notes: Optional[str] = None) -> Dict[str, Any]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return {"error": "Patient profile not found"}
    if vital_type not in ALLOWED_VITAL_TYPES:
        return {"error": f"Invalid vital_type '{vital_type}'. Must be one of: {sorted(ALLOWED_VITAL_TYPES)}"}
    vital = crud.create_vital(db=db, patient_id=patient.id, vital_type=vital_type, value=value, unit=unit, recorded_at=recorded_at, notes=notes)
    return {"id": vital.id, "patient_id": vital.patient_id, "vital_type": vital.vital_type, "value": vital.value, "unit": vital.unit, "recorded_at": vital.recorded_at.isoformat() if vital.recorded_at else None, "source": vital.source, "notes": vital.notes}

def calculate_vital_trend(db: Session, user_id: int, vital_type: str, limit: int = 10) -> Dict[str, Any]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return {"error": "Patient profile not found"}
    vitals = crud.get_patient_vitals(db, patient.id, vital_type=vital_type, limit=limit)
    if not vitals:
        return {"vital_type": vital_type, "count": 0, "trend": "no_data", "message": f"No recordings found for {vital_type}."}
    if vital_type == "blood_pressure":
        return {"vital_type": vital_type, "count": len(vitals), "trend": "not_applicable", "message": "Blood pressure readings are compound values.", "most_recent": {"value": vitals[0].value, "unit": vitals[0].unit}}

    numeric_values = []
    for v in vitals:
        try: numeric_values.append((float(v.value), v))
        except (ValueError, TypeError): pass

    if not numeric_values:
        return {"vital_type": vital_type, "count": len(vitals), "trend": "non_numeric"}

    recent_val, recent_obj = numeric_values[0]
    oldest_val, oldest_obj = numeric_values[-1]

    trend_dir = "increasing" if recent_val > oldest_val else ("decreasing" if recent_val < oldest_val else "stable")
    return {"vital_type": vital_type, "count": len(vitals), "trend": trend_dir, "most_recent": {"value": recent_obj.value, "unit": recent_obj.unit}, "oldest_in_window": {"value": oldest_obj.value, "unit": oldest_obj.unit}}

def get_medication_schedule(db: Session, user_id: int) -> List[Dict[str, Any]]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return []
    reminders = crud.get_medication_reminders(db, patient.id)
    return [{"id": r.id, "medication_id": r.medication_id, "reminder_text": r.reminder_text, "reminder_time": r.reminder_time, "status": r.status, "notes": r.notes} for r in reminders if r.status == "active"]

def create_medication_reminder(db: Session, user_id: int, reminder_text: str, reminder_time: str, medication_id: Optional[int] = None, notes: Optional[str] = None) -> Dict[str, Any]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return {"error": "Patient profile not found"}
    if not reminder_text or not reminder_time: return {"error": "reminder_text and reminder_time are required"}
    reminder = crud.create_medication_reminder(db=db, patient_id=patient.id, reminder_text=reminder_text, reminder_time=reminder_time, medication_id=medication_id, notes=notes)
    return {"id": reminder.id, "patient_id": reminder.patient_id, "medication_id": reminder.medication_id, "reminder_text": reminder.reminder_text, "reminder_time": reminder.reminder_time, "status": reminder.status, "notes": reminder.notes}

def cancel_reminder(db: Session, user_id: int, reminder_id: int) -> Optional[Dict[str, Any]]:
    patient = _get_patient_by_user_id(db, user_id)
    if not patient: return None
    reminder = crud.cancel_medication_reminder(db, patient_id=patient.id, reminder_id=reminder_id)
    if not reminder: return None
    return {"id": reminder.id, "patient_id": reminder.patient_id, "medication_id": reminder.medication_id, "reminder_text": reminder.reminder_text, "reminder_time": reminder.reminder_time, "status": reminder.status, "notes": reminder.notes}
```

---

### `app/services/audit.py`

```python
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("healthsync.audit")
logger.setLevel(logging.INFO)

def log_audit_event(
    session_id: str,
    user_id: int,
    intent: str,
    selected_agent: str,
    risk_level: str,
    safety_escalated: bool,
    is_mock: bool = True,
    tool_name: Optional[str] = None,
    patient_id: Optional[int] = None,
    tool_result: Optional[str] = None
) -> Dict[str, Any]:
    audit_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_id": user_id,
        "intent": intent,
        "selected_agent": selected_agent,
        "risk_level": risk_level,
        "safety_escalated": safety_escalated,
        "is_mock": is_mock
    }
    if tool_name is not None: audit_record["tool_name"] = tool_name
    if patient_id is not None: audit_record["patient_id"] = patient_id
    if tool_result is not None: audit_record["tool_result"] = tool_result

    logger.info(f"AUDIT_EVENT: {audit_record}")
    return audit_record
```

---

### `app/services/llm.py`

```python
import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

from app.schemas_ai import IntentExtraction, IntentEnum

logger = logging.getLogger(__name__)

class LLMError(Exception): pass
class LLMAuthenticationError(LLMError): pass
class LLMTimeoutError(LLMError): pass
class LLMConnectionError(LLMError): pass
class LLMRateLimitError(LLMError): pass

class BaseLLMService(ABC):
    @abstractmethod
    def extract_intent(self, text: str) -> IntentExtraction: pass
    @abstractmethod
    def generate_response(self, text: str, intent_info: IntentExtraction) -> str: pass
    @abstractmethod
    def is_mock_mode(self) -> bool: pass

class MockLLMService(BaseLLMService):
    def extract_intent(self, text: str) -> IntentExtraction:
        text_lower = text.lower()
        emergency_triggers = ["emergency", "911", "chest pain", "bleeding", "severe", "suicide", "hurt", "die", "unconscious"]
        if any(trigger in text_lower for trigger in emergency_triggers):
            return IntentExtraction(intent=IntentEnum.EMERGENCY, confidence=1.0, extracted_entities={"emergency_keyword_detected": True})

        scheduling_triggers = ["appointment", "schedule", "book", "meet", "doctor", "dermatologist", "reschedule", "calendar", "cancel"]
        if any(trigger in text_lower for trigger in scheduling_triggers) and not any(r_kw in text_lower for r_kw in ["reminder", "reminders"]):
            entities = {}
            if "dermatologist" in text_lower: entities["doctor_specialty"] = "dermatologist"
            if "tomorrow" in text_lower: entities["date_preference"] = "tomorrow"
            elif "wednesday" in text_lower: entities["date_preference"] = "wednesday"
            return IntentExtraction(intent=IntentEnum.SCHEDULING, confidence=0.95, extracted_entities=entities)

        records_triggers = ["record", "records", "vital", "vitals", "blood pressure", "summary", "report", "test", "bp", "result", "history", "medication", "medications"]
        if any(trigger in text_lower for trigger in records_triggers) and not any(r_kw in text_lower for r_kw in ["remind", "reminder"]):
            entities = {}
            if "blood pressure" in text_lower or "bp" in text_lower: entities["record_type"] = "blood pressure"
            elif "medication" in text_lower or "medications" in text_lower: entities["record_type"] = "medications"
            return IntentExtraction(intent=IntentEnum.RECORDS, confidence=0.95, extracted_entities=entities)

        reminders_triggers = ["remind", "reminder", "pill", "schedule", "take my"]
        if any(trigger in text_lower for trigger in reminders_triggers):
            return IntentExtraction(intent=IntentEnum.REMINDERS, confidence=0.95, extracted_entities={})

        triage_triggers = ["fever", "cough", "symptom", "pain", "headache", "cold", "sick", "ill", "ache"]
        if any(trigger in text_lower for trigger in triage_triggers):
            return IntentExtraction(intent=IntentEnum.TRIAGE, confidence=0.90, extracted_entities={})

        return IntentExtraction(intent=IntentEnum.GENERAL, confidence=0.85, extracted_entities={})

    def generate_response(self, text: str, intent_info: IntentExtraction) -> str:
        return f"I am your HealthSync assistant (Mock Mode). I received your query regarding '{intent_info.intent.value}' and am ready to assist."

    def is_mock_mode(self) -> bool:
        return True

def get_llm_service() -> BaseLLMService:
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.strip() and api_key != "your_groq_api_key_here":
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return GroqLLMService(api_key=api_key, model=model)
    else:
        return MockLLMService()
```

---

### `.env.example`

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/healthsync
JWT_SECRET=YOUR_32_BYTE_HEX_JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

---

### `walkthrough_phase6.md`

```markdown
# Phase 6 — Patient Data Tools Implementation & Verification Walkthrough

**Phase Status:** COMPLETE  
**Verified Baseline:** 46/46 pytest automated tests passing (100% pass rate)

---

## 1. Overview

Phase 6 introduces secure, patient-scoped data tools for managing **Patient Profiles, Medications, Vitals, and Medication Reminders**. It integrates these capabilities into the existing HealthSync AI architecture without breaking the safety boundaries, triage workflows, or LangGraph Human-in-the-Loop (HITL) scheduling mechanisms established in Phases 1–5.

### Key Achievements

1. **SQLAlchemy Data Models**:
   - Added `Medication`, `Vital`, and `MedicationReminder` models with foreign key constraints to `patients.id` and `cascade="all, delete-orphan"`.
   - Updated `Patient` model with additive 1:N relationships.

2. **Controlled Python Tool Layer (`app/services/patient_data.py`)**:
   - Implemented 8 deterministic Python functions (profile, medications, vitals, vital trends, reminder schedule, reminder creation, reminder cancellation).
   - Validates `vital_type` against strict vocabulary (`["blood_pressure", "heart_rate", "weight", "temperature", "spo2"]`).
   - Performs pure Python mathematical trend calculations (`increasing`, `decreasing`, `stable`) for scalar vitals, bypassing LLM clinical interpretation.

3. **FastAPI Endpoints (`app/main.py`) & Schemas (`app/schemas_ai.py`)**:
   - Added 6 new patient-scoped REST endpoints (`/vitals/me` GET/POST, `/medications/me` GET, `/reminders/me` GET/POST, `/reminders/{id}/cancel` POST).
   - Protected via `Depends(auth.require_role("patient"))`. Identity resolved strictly from JWT token -> `user_id` -> `Patient`. Client-supplied `patient_id` parameters are rejected.

4. **LangGraph Unified `patient_data_node` (`app/services/graph.py`)**:
   - Replaced `records_stub_node` and `reminders_stub_node` with a single, unified `patient_data_node`.
   - Dispatches deterministically based on classified intent (`RECORDS` vs `REMINDERS`).
   - Extended `HealthSyncState` with `patient_data_result` and `patient_data_tool`.

5. **Streamlit Console Integration (`streamlit_app.py`)**:
   - Added 3 new patient navigation tabs: `❤️ My Vitals`, `💊 My Medications`, and `⏰ My Reminders`.
   - Rendered interactive logging forms, historical tables, and reminder cancellation controls with clear clinical disclaimers.

---

## 2. Architecture & Security Model

```text
User / Client
  │
  ├──► FastAPI Endpoint / LangGraph State
  │       │
  │       ▼ (Auth Check: require_role("patient"))
  │    JWT Token ---> sub: username, role: patient
  │       │
  │       ▼ (Identity Resolution)
  │    User.id ---> Patient.user_id ---> patient.id
  │       │
  │       ▼ (Controlled Tool Dispatch)
  │    app/services/patient_data.py
  │       │
  │       ▼ (Patient-Scoped SQL Query)
  │    app/crud.py (WHERE patient_id == patient.id)
  │       │
  │       ▼
  └──► Database (medications, vitals, medication_reminders)
```

### Authorization & Isolation Rules
- **No LLM Identity Choice:** Patient identity is sourced exclusively from the authenticated JWT context. Any `patient_id` mentioned in natural language prompt text is ignored.
- **Cross-Patient Isolation:** Verified by unit and integration tests; attempting to query or cancel another patient's data returns HTTP 404 or empty results (`[]`).
- **Role Hierarchy:** Admin role token receives HTTP 403 Forbidden for all `/me` patient-data endpoints.

---

## 3. Medical Safety Boundaries & Disclaimers

Phase 6 strictly maintains all safety precedence established in Phase 4:
- **Red-Flag Precedence:** Deterministic safety check (`evaluate_red_flags`) executes in `input_screening_node` BEFORE intent classification or `patient_data_node` dispatch. Emergency queries ("Show my vitals, I have severe chest pain") trigger immediate emergency escalation.
- **Non-Diagnostic / Non-Prescribing:** Tools return stored facts only. The agent explicitly disclaims issuing medical diagnoses, changing prescription dosages, or prescribing medications.
- **Mathematical Trends:** Vital trend directions are simple numeric comparisons between oldest and newest readings in a window. No clinical claims are generated.

---

## 4. Test Suite Summary

Total Test Count: **46 automated pytest tests passing**

```text
tests/test_graph.py ......                                               [ 13%]
tests/test_main.py ...........                                           [ 36%]
tests/test_patient_data_api.py .....                                     [ 47%]
tests/test_patient_data_graph.py ......                                  [ 60%]
tests/test_patient_data_service.py ......                                [ 73%]
tests/test_scheduling.py .....                                           [ 84%]
tests/test_triage.py .......                                             [100%]

======================= 46 passed, 9 warnings in 7.12s =======================
```

---

## 5. Scope Limitations & Phase Deferrals

- **Care Coordination Scope Only:** Phase 6 patient data tools provide reference and scheduling capabilities only. They do not constitute medical diagnosis, treatment planning, prescription, or clinical decision-making.
- **Deferred to Phase 7:** Vector database integration (pgvector), document embeddings, semantic search over records, and RAG document summaries.
- **Deferred to Phase 8:** Database-level PostgreSQL Row-Level Security (RLS), consent enforcement matrix, and granular tool permissions.
- **Deferred to Phase 9:** LangSmith telemetry, token tracking, and database-persisted audit logs table.
```
