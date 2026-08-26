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

