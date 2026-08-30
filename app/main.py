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


# --- Phase 11A Power BI & Analytics Endpoints ---

from fastapi import Response
from app.services import analytics

@app.get("/analytics/clinical-operations", response_model=schemas.ClinicalOperationsAnalyticsResponse)
def get_clinical_operations_analytics(
    current_user: models.User = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Retrieve aggregated clinical operations metrics (appointments, medications, vitals, consents).
    Admin-only, zero-PHI server-side aggregation for Power BI executive dashboards.
    """
    return analytics.get_clinical_operations_metrics(db)


@app.get("/analytics/agent-telemetry", response_model=schemas.AgentTelemetryAnalyticsResponse)
def get_agent_telemetry_analytics(
    current_user: models.User = Depends(auth.require_role("admin"))
):
    """
    Retrieve real-time multi-agent performance and operational telemetry metrics.
    Admin-only, zero-PHI server-side aggregation for Power BI agent monitoring.
    """
    return analytics.get_agent_telemetry_metrics()


@app.get("/analytics/cost-intelligence", response_model=schemas.CostIntelligenceAnalyticsResponse)
def get_cost_intelligence_analytics(
    current_user: models.User = Depends(auth.require_role("admin"))
):
    """
    Retrieve cumulative token consumption, tier distributions, and financial cost accounting.
    Admin-only, zero-PHI server-side aggregation for Power BI cost intelligence.
    """
    return analytics.get_cost_intelligence_metrics()


@app.get("/analytics/export/{dataset_name}")
def export_analytics_dataset(
    dataset_name: str,
    format: str = Query("json", description="Export format: 'json' or 'csv'"),
    current_user: models.User = Depends(auth.require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Export structured, zero-PHI tabular datasets formatted for Power Query / Power BI Desktop.
    Supported dataset names: clinical-operations, appointments, medications, vitals, consents, agent-telemetry, cost-intelligence.
    Supported formats: json, csv.
    """
    fmt = format.lower().strip()
    if fmt not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Choose 'json' or 'csv'."
        )

    records, csv_data = analytics.get_export_dataset(db, dataset_name=dataset_name, format_type=fmt)
    if records is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_name}' not found. Available datasets: clinical-operations, appointments, medications, vitals, consents, agent-telemetry, cost-intelligence."
        )

    if fmt == "csv":
        return Response(
            content=csv_data or "",
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={dataset_name}.csv"}
        )

    return records


# --- Phase 11B Voice API Endpoints ---

from fastapi import UploadFile, File
from app.services import voice
from app.services.voice import VoiceError, VoicePayloadError, VoiceAuthenticationError, VoiceConnectionError

@app.post("/voice/transcribe", response_model=schemas_ai.VoiceTranscriptionResponse)
async def transcribe_audio_endpoint(
    file: UploadFile = File(..., description="Audio file to transcribe (in-memory processing only)"),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Transcribe speech audio into text using in-memory STT provider.
    JWT authenticated (patient or admin). Zero disk retention.
    """
    try:
        audio_bytes = await file.read()
        stt_service = voice.get_stt_service()
        result = stt_service.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            content_type=file.content_type or "audio/wav"
        )
        return result
    except VoicePayloadError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VoiceAuthenticationError as e:
        logger.error(f"Voice authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Voice transcription service authentication failure."
        )
    except VoiceConnectionError as e:
        logger.error(f"Voice connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transcription service temporarily unavailable."
        )
    except VoiceError as e:
        logger.error(f"Voice processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech transcription failed."
        )
    except Exception as e:
        logger.error(f"Unexpected error in voice transcription: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the audio."
        )


@app.post("/voice/synthesize")
def synthesize_speech_endpoint(
    payload: schemas_ai.VoiceSynthesisRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Synthesize safe text into spoken audio stream.
    JWT authenticated (patient or admin). Zero disk retention.
    """
    try:
        tts_service = voice.get_tts_service()
        result = tts_service.synthesize(text=payload.text, voice_id=payload.voice_id)
        return Response(
            content=result["audio_bytes"],
            media_type=result.get("media_type", "audio/wav"),
            headers={"Content-Disposition": "inline; filename=synthesis.wav"}
        )
    except VoicePayloadError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VoiceError as e:
        logger.error(f"Voice synthesis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech synthesis failed."
        )
    except Exception as e:
        logger.error(f"Unexpected error in voice synthesis: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while synthesizing speech."
        )


# --- Phase 11C Vision API Endpoints ---

from app.services import vision
from app.services.vision import VisionError, VisionPayloadError, VisionAuthenticationError, VisionConnectionError, VisionProcessingError

@app.post("/vision/analyze", response_model=schemas_ai.VisionAnalysisResponse)
async def analyze_image_endpoint(
    file: UploadFile = File(..., description="Image file to analyze (in-memory processing only)"),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Analyze healthcare documents or visual observations for care navigation assistance.
    JWT authenticated (patient or admin). Zero disk retention. Strictly non-diagnostic.
    """
    try:
        image_bytes = await file.read()
        vision_service = vision.get_vision_service()
        result = vision_service.analyze_image(
            image_bytes=image_bytes,
            filename=file.filename or "image.png",
            content_type=file.content_type or "image/png"
        )
        return result
    except VisionPayloadError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VisionAuthenticationError as e:
        logger.error(f"Vision authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vision analysis service authentication failure."
        )
    except VisionConnectionError as e:
        logger.error(f"Vision connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vision analysis service temporarily unavailable."
        )
    except (VisionError, VisionProcessingError) as e:
        logger.error(f"Vision processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vision image analysis failed."
        )
    except Exception as e:
        logger.error(f"Unexpected error in vision analysis: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the image."
        )


# --- Phase 11D Messaging API Endpoints ---

from app.services import messaging
from app.services.messaging import (
    MessagingError,
    MessagingPayloadError,
    MessagingRecipientError,
    MessagingAuthenticationError,
    MessagingConnectionError,
    MessagingProviderError,
    MessagingConsentError,
)

@app.post("/messaging/send", response_model=schemas_ai.MessagingSendResponse)
def send_message_endpoint(
    payload: schemas_ai.MessagingSendRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Send an outbound notification via SMS or WhatsApp.
    JWT authenticated (patient or admin). Zero disk retention. PHI-sanitized metadata.
    """
    try:
        service = messaging.get_messaging_service(channel=payload.channel)
        result = service.send_message(
            recipient=payload.recipient,
            body=payload.body,
            channel=payload.channel,
            template_name=payload.template_name,
            template_params=payload.template_params
        )
        return result
    except (MessagingPayloadError, MessagingRecipientError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except MessagingConsentError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except MessagingAuthenticationError as e:
        logger.error(f"Messaging authentication error on channel {payload.channel}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Messaging provider authentication failure."
        )
    except MessagingConnectionError as e:
        logger.error(f"Messaging connection error on channel {payload.channel}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Messaging service temporarily unavailable."
        )
    except (MessagingProviderError, MessagingError) as e:
        logger.error(f"Messaging provider error on channel {payload.channel}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message via provider."
        )
    except Exception as e:
        logger.error(f"Unexpected error in messaging send: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending the message."
        )


@app.post("/messaging/opt-out", response_model=schemas_ai.MessagingOptOutResponse)
def messaging_opt_out_endpoint(
    payload: schemas_ai.MessagingOptOutRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Process recipient opt-out request (e.g. STOP, UNSUBSCRIBE, CANCEL).
    JWT authenticated. Zero disk retention. Sanitized metadata.
    """
    try:
        norm_channel = messaging.validate_channel(payload.channel)
        messaging.normalize_and_validate_recipient(payload.recipient)
        is_opted_out = messaging.is_opt_out_keyword(payload.keyword)

        logger.info(f"Processed messaging opt-out check for channel '{norm_channel}'. Keyword matched: {is_opted_out}")

        return {
            "success": True,
            "opted_out": is_opted_out,
            "keyword_matched": is_opted_out,
            "channel": norm_channel,
            "status": "opted_out" if is_opted_out else "active"
        }
    except (MessagingPayloadError, MessagingRecipientError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in messaging opt-out: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the opt-out request."
        )