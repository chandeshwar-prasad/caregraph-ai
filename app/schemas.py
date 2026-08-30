from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any, List

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

from datetime import datetime

class ConsentGrantRequest(BaseModel):
    consent_type: str = Field(..., description="Type of consent ('data_access', 'vital_tracking', 'medication_tracking', 'medication_reminders', 'appointment_booking', 'ai_processing')")
    expires_days: Optional[int] = Field(365, ge=1, le=1825, description="Validity period in days (default 365)")
    version: Optional[str] = Field("v1.0", description="Consent policy version")

class ConsentRevokeRequest(BaseModel):
    consent_type: str = Field(..., description="Type of consent to revoke")

class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    consent_type: str
    status: str
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    version: str


# --- Phase 11A Analytics Schemas ---

class AppointmentsAnalytics(BaseModel):
    total_count: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_specialty: dict[str, int] = Field(default_factory=dict)
    by_doctor: dict[str, int] = Field(default_factory=dict)

class MedicationsAnalytics(BaseModel):
    total_count: int
    active_count: int
    inactive_count: int
    by_name: dict[str, int] = Field(default_factory=dict)
    by_frequency: dict[str, int] = Field(default_factory=dict)

class VitalsAnalytics(BaseModel):
    total_count: int
    by_type: dict[str, int] = Field(default_factory=dict)

class ConsentsAnalytics(BaseModel):
    total_count: int
    by_type: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)

class RemindersAnalytics(BaseModel):
    total_count: int
    by_status: dict[str, int] = Field(default_factory=dict)

class ClinicalOperationsAnalyticsResponse(BaseModel):
    total_patients: int
    appointments: AppointmentsAnalytics
    medications: MedicationsAnalytics
    vitals: VitalsAnalytics
    consents: ConsentsAnalytics
    reminders: RemindersAnalytics
    zero_phi: bool = True

class AgentTelemetryAnalyticsResponse(BaseModel):
    total_events: int
    avg_latency_ms: float
    safety_escalations: int
    error_rate: float
    intents_breakdown: dict[str, int] = Field(default_factory=dict)
    agents_breakdown: dict[str, int] = Field(default_factory=dict)
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    tool_breakdown: dict[str, int] = Field(default_factory=dict)
    recent_traces_count: int
    zero_phi: bool = True

class CostIntelligenceAnalyticsResponse(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    avg_cost_per_workflow_usd: float
    model_usage: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tier_distribution: dict[str, int] = Field(default_factory=dict)
    pricing_table: dict[str, dict[str, Any]] = Field(default_factory=dict)
    zero_phi: bool = True

