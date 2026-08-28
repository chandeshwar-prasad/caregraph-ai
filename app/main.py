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

import os
import logging
from langgraph.types import Command
from app.services.graph import graph

logger = logging.getLogger(__name__)

# Environment Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()

# Initialize database schemas
models.Base.metadata.create_all(bind=engine)

# Seed database on startup (only in development/test or when explicitly requested)
if ENVIRONMENT != "production" or os.getenv("SEED_DEMO_DATA", "false").lower() == "true":
    db = SessionLocal()
    try:
        crud.seed_initial_data(db)
    finally:
        db.close()

app = FastAPI(
    title="CareGraph AI - Care Coordination API",
    description="Multi-Agent, Multi-Model Healthcare Navigation & Care-Management Assistant",
    version="1.0.0"
)

# CORS Middleware Setup
raw_allowed_origins = os.getenv("ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", ""))
if raw_allowed_origins.strip():
    allowed_origins = [origin.strip() for origin in raw_allowed_origins.split(",") if origin.strip()]
else:
    # Safe development/local defaults
    allowed_origins = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ]
    if ENVIRONMENT != "production":
        allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        "mode": ENVIRONMENT
    }



@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    return current_user.patient

@app.post("/patients/me", response_model=schemas.PatientResponse, status_code=status.HTTP_201_CREATED)
def create_my_patient_profile(
    patient: schemas.PatientCreate,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    if current_user.patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient profile already exists"
        )
    return crud.create_patient_profile(db=db, user_id=current_user.id, patient=patient)

@app.get("/admin/patients", response_model=List[schemas.PatientResponse])
def get_all_patients(
    current_user: models.User = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db)
):
    patients = db.query(models.Patient).all()
    return patients


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
            "user_role": current_user.role,
            "session_id": thread_id
        }
        
        graph.invoke(initial_state, config=config)
        snapshot = graph.get_state(config)
        state_values = snapshot.values
        
        # Check if execution interrupted for HITL approval
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
        logger.error(f"LLM timeout during chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The AI assistant request timed out. Please try again."
        )
    except LLMAuthenticationError as e:
        logger.error(f"LLM auth failure during chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to authenticate with the underlying language model service."
        )
    except LLMConnectionError as e:
        logger.error(f"LLM connection error during chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the language model service. Please check network connectivity."
        )
    except LLMRateLimitError as e:
        logger.error(f"LLM rate limit error during chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI assistant is currently busy. Please wait a moment and retry."
        )
    except Exception as e:
        logger.error(f"Unhandled error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The care coordination service encountered an error processing your request."
        )


@app.post("/chat/approve", response_model=schemas_ai.ChatResponse)
def approve_coordination(
    request: schemas_ai.ApprovalRequest,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    if request.decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'approved' or 'rejected'."
        )
    try:
        user_session_key = request.session_id or "default"
        thread_id = f"user_{current_user.id}_{user_session_key}"
        config = {"configurable": {"thread_id": thread_id}}

        snapshot = graph.get_state(config)
        if not snapshot.next or snapshot.next[0] != "scheduling":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending approval workflow found for this session."
            )

        resumed_state = graph.invoke(
            Command(resume={"approval_status": request.decision}),
            config=config
        )

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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant service encountered an error processing your approval decision."
        )


@app.get("/appointments/me", response_model=List[schemas_ai.AppointmentResponse])
def get_my_appointments(
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(
            db,
            current_user.id,
            schemas.PatientCreate(
                first_name=current_user.username,
                last_name="Patient",
                email=f"{current_user.username}@example.com"
            )
        )
    return crud.get_patient_appointments(db, patient.id)


@app.post("/appointments/{appointment_id}/cancel", response_model=schemas_ai.AppointmentResponse)
def cancel_my_appointment(
    appointment_id: int,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(
            db,
            current_user.id,
            schemas.PatientCreate(
                first_name=current_user.username,
                last_name="Patient",
                email=f"{current_user.username}@example.com"
            )
        )
    
    cancelled_apt = crud.cancel_appointment(db, patient.id, appointment_id)
    if not cancelled_apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or does not belong to current patient."
        )
    return cancelled_apt


# --- Phase 6 Patient Data Endpoints ---

@app.get("/vitals/me", response_model=List[schemas_ai.VitalResponse])
def get_my_vitals(
    vital_type: Optional[str] = Query(None, description="Optional vital type filter ('blood_pressure', 'heart_rate', etc.)"),
    limit: int = Query(10, ge=1, le=100),
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    return patient_data.get_patient_vitals(db, current_user.id, vital_type=vital_type, limit=limit)


@app.post("/vitals/me", response_model=schemas_ai.VitalResponse, status_code=status.HTTP_201_CREATED)
def record_my_vital(
    payload: schemas_ai.VitalCreate,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    result = patient_data.store_vital(
        db,
        user_id=current_user.id,
        vital_type=payload.vital_type,
        value=payload.value,
        unit=payload.unit,
        recorded_at=payload.recorded_at,
        notes=payload.notes
    )
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    return result


@app.get("/medications/me", response_model=List[schemas_ai.MedicationResponse])
def get_my_medications(
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    return patient_data.get_patient_medications(db, current_user.id)


@app.get("/reminders/me", response_model=List[schemas_ai.MedicationReminderResponse])
def get_my_reminders(
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        return []
    return crud.get_medication_reminders(db, patient.id)


@app.post("/reminders/me", response_model=schemas_ai.MedicationReminderResponse, status_code=status.HTTP_201_CREATED)
def create_my_reminder(
    payload: schemas_ai.MedicationReminderCreate,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    result = patient_data.create_medication_reminder(
        db,
        user_id=current_user.id,
        reminder_text=payload.reminder_text,
        reminder_time=payload.reminder_time,
        medication_id=payload.medication_id,
        notes=payload.notes
    )
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    return result


@app.post("/reminders/{reminder_id}/cancel", response_model=schemas_ai.MedicationReminderResponse)
def cancel_my_reminder(
    reminder_id: int,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    cancelled = patient_data.cancel_reminder(db, current_user.id, reminder_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication reminder not found or does not belong to current patient."
        )
    return cancelled


# --- Phase 8 Consent Management Endpoints ---

@app.get("/consents/me", response_model=List[schemas.ConsentResponse])
def get_my_consents(
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(
            db,
            current_user.id,
            schemas.PatientCreate(
                first_name=current_user.username,
                last_name="Patient",
                email=f"{current_user.username}@example.com"
            )
        )
    return crud.get_patient_consents(db, patient.id)


@app.post("/consents/me/grant", response_model=schemas.ConsentResponse)
def grant_my_consent(
    payload: schemas.ConsentGrantRequest,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(
            db,
            current_user.id,
            schemas.PatientCreate(
                first_name=current_user.username,
                last_name="Patient",
                email=f"{current_user.username}@example.com"
            )
        )
    return crud.grant_patient_consent(
        db=db,
        patient_id=patient.id,
        consent_type=payload.consent_type,
        expires_days=payload.expires_days or 365,
        version=payload.version or "v1.0"
    )


@app.post("/consents/me/revoke", response_model=schemas.ConsentResponse)
def revoke_my_consent(
    payload: schemas.ConsentRevokeRequest,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = crud.create_patient_profile(
            db,
            current_user.id,
            schemas.PatientCreate(
                first_name=current_user.username,
                last_name="Patient",
                email=f"{current_user.username}@example.com"
            )
        )
    return crud.revoke_patient_consent(
        db=db,
        patient_id=patient.id,
        consent_type=payload.consent_type
    )


# --- Phase 9 Observability & Telemetry Endpoints ---

from app.services.telemetry import global_telemetry

@app.get("/metrics/telemetry")
def get_telemetry_metrics():
    """Retrieve operational telemetry summary metrics with zero PHI."""
    return global_telemetry.get_summary()


from app.services.evaluation import compute_quantitative_metrics

@app.get("/metrics/evaluation")
def get_evaluation_metrics():
    """Retrieve multi-agent, RAG, safety, and security quantitative evaluation scorecard."""
    return compute_quantitative_metrics().to_dict()


from app.services.telemetry import global_cost_tracker
from app.services.llm import evaluate_model_router_performance, ModelRouter

@app.get("/metrics/costs")
def get_cost_and_routing_metrics():
    """Retrieve cumulative token costs, pricing distribution, and model routing comparative evaluation."""
    return {
        "cost_summary": global_cost_tracker.get_cost_summary(),
        "routing_policy": ModelRouter.get_routing_policy_summary(),
        "comparative_analysis": evaluate_model_router_performance(sample_queries_count=50)
    }