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


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document text or guidance content")
    source: str = Field(..., description="Originating source name")
    source_type: str = Field(default="clinical_guideline", description="Type of source")
    category: str = Field(default="triage", description="Content category")
    version: str = Field(default="v1.0", description="Document version")
    status: str = Field(default="active", description="Status ('active', 'stale', 'superseded', 'draft')")
    region: Optional[str] = Field(default="US", description="Geographic region")
    publication_date: Optional[str] = Field(None, description="Publication date")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding float list")


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    source: str
    source_type: str
    category: str
    version: str
    status: str
    region: Optional[str] = None
    publication_date: Optional[str] = None
    ingestion_date: Optional[datetime] = None
    created_at: Optional[datetime] = None


# --- Phase 11B Voice Schemas ---

class VoiceTranscriptionResponse(BaseModel):
    transcript: str
    detected_language: str = "en"
    duration_seconds: float = 0.0
    is_mock: bool = True

class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to synthesize to speech (max 2000 chars)")
    voice_id: Optional[str] = Field(None, description="Optional voice identifier")


# --- Phase 11C Vision Schemas ---

class VisionAnalysisResponse(BaseModel):
    detected_features: List[str] = Field(default_factory=list, description="Visual features, document fields, or objects detected")
    description: str = Field(..., description="High-level descriptive overview of the image")
    media_type: str = Field(default="image/png", description="Image MIME type")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Analysis confidence score")
    clinical_disclaimer: str = Field(
        default="CareGraph AI Vision is for care navigation and symptom observation assistance only, and does not provide clinical diagnosis or diagnostic decisions.",
        description="Mandatory clinical safety disclaimer"
    )
    is_mock: bool = Field(default=True, description="Flag indicating mock mode vs cloud model execution")


# --- Phase 11D Messaging Schemas ---


class MessagingSendRequest(BaseModel):
    recipient: str = Field(..., min_length=7, max_length=25, description="E.164 formatted phone number or validated recipient string")
    body: str = Field(..., min_length=1, max_length=1600, description="Message text content (max 1600 chars)")
    channel: str = Field(default="sms", description="Delivery channel ('sms' or 'whatsapp')")
    template_name: Optional[str] = Field(None, description="Optional approved WhatsApp template identifier")
    template_params: Optional[Dict[str, Any]] = Field(None, description="Optional template parameters")

class MessagingSendResponse(BaseModel):
    success: bool
    channel: str
    provider: str
    message_id: str
    status: str
    error_category: Optional[str] = None
    is_mock: bool = True


class MessagingOptOutRequest(BaseModel):
    recipient: str = Field(..., min_length=7, max_length=25, description="E.164 formatted phone number")
    keyword: str = Field(..., min_length=1, max_length=50, description="Opt-out command text or keyword (e.g. STOP, UNSUBSCRIBE)")
    channel: str = Field(default="sms", description="Channel from which to opt out ('sms' or 'whatsapp')")


class MessagingOptOutResponse(BaseModel):
    success: bool
    opted_out: bool
    keyword_matched: bool
    channel: str
    status: str

