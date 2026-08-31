/**
 * CareGraph AI - Typed API Schemas
 * Strictly matching backend FastAPI Pydantic contracts
 */

// ==========================================
// Authentication & User Roles
// ==========================================

export type UserRole = "patient" | "admin";

export interface UserCreate {
  username: string;
  password: string;
  role?: UserRole;
}

export interface UserResponse {
  id: number;
  username: string;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface TokenData {
  username?: string;
  role?: UserRole;
}

// ==========================================
// Patient Profile
// ==========================================

export interface PatientCreate {
  first_name: string;
  last_name: string;
  date_of_birth?: string | null;
  gender?: string | null;
  email?: string | null;
  phone?: string | null;
}

export interface PatientResponse {
  id: number;
  user_id: number;
  first_name: string;
  last_name: string;
  date_of_birth?: string | null;
  gender?: string | null;
  email?: string | null;
  phone?: string | null;
}

export interface UserWithPatientResponse {
  id: number;
  username: string;
  role: UserRole;
  patient?: PatientResponse | null;
}

// ==========================================
// LangGraph AI Chat & HITL Coordination
// ==========================================

export type IntentType = "triage" | "scheduling" | "records" | "reminders" | "general" | "emergency";
export type RiskLevel = "emergency" | "urgent" | "non_urgent";
export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface ChatRequest {
  message: string;
  session_id?: string | null;
}

export interface ApprovalRequest {
  session_id?: string | null;
  decision: "approved" | "rejected";
}

export interface GroundingSource {
  source_name?: string;
  source_type?: string;
  title?: string;
  category?: string;
  [key: string]: unknown;
}

export interface SlotDetails {
  doctor_name?: string;
  specialty?: string;
  appointment_time?: string;
  is_mock?: boolean;
  [key: string]: unknown;
}

export interface ChatResponse {
  message: string;
  intent: string;
  entities: Record<string, unknown>;
  is_mock: boolean;
  session_id: string;
  approval_required: boolean;
  approval_status?: ApprovalStatus | null;
  risk_level?: RiskLevel | null;
  safety_escalated: boolean;
  follow_up_questions: string[];
  sources: GroundingSource[];
  selected_slot?: SlotDetails | null;
}

// ==========================================
// Appointments
// ==========================================

export type AppointmentStatus = "scheduled" | "cancelled" | "completed";

export interface AppointmentResponse {
  id: number;
  patient_id: number;
  doctor_name: string;
  specialty: string;
  appointment_time: string;
  status: AppointmentStatus | string;
  notes?: string | null;
  created_at?: string | null;
}

// ==========================================
// Vitals
// ==========================================

export type VitalType = "blood_pressure" | "heart_rate" | "weight" | "temperature" | "spo2" | string;

export interface VitalCreate {
  vital_type: VitalType;
  value: string;
  unit?: string | null;
  recorded_at?: string | null;
  notes?: string | null;
}

export interface VitalResponse {
  id: number;
  patient_id: number;
  vital_type: VitalType;
  value: string;
  unit?: string | null;
  recorded_at?: string | null;
  source?: string | null;
  notes?: string | null;
  created_at?: string | null;
}

// ==========================================
// Medications & Reminders
// ==========================================

export interface MedicationResponse {
  id: number;
  patient_id: number;
  name: string;
  dosage: string;
  frequency: string;
  prescribed_by?: string | null;
  start_date?: string | null;
  is_active: boolean;
  notes?: string | null;
  created_at?: string | null;
}

export interface MedicationReminderCreate {
  reminder_text: string;
  reminder_time: string;
  medication_id?: number | null;
  notes?: string | null;
}

export interface MedicationReminderResponse {
  id: number;
  patient_id: number;
  medication_id?: number | null;
  reminder_text: string;
  reminder_time: string;
  status: "active" | "cancelled" | string;
  notes?: string | null;
  created_at?: string | null;
}

// ==========================================
// Consent Management
// ==========================================

export type ConsentType =
  | "data_access"
  | "vital_tracking"
  | "medication_tracking"
  | "medication_reminders"
  | "appointment_booking"
  | "ai_processing"
  | string;

export interface ConsentGrantRequest {
  consent_type: ConsentType;
  expires_days?: number;
  version?: string;
}

export interface ConsentRevokeRequest {
  consent_type: ConsentType;
}

export interface ConsentResponse {
  id: number;
  patient_id: number;
  consent_type: string;
  status: "granted" | "revoked" | "expired" | string;
  granted_at: string;
  revoked_at?: string | null;
  expires_at?: string | null;
  version: string;
}

// ==========================================
// System Health & Observability Metrics
// ==========================================

export interface HealthResponse {
  status: "healthy" | "degraded" | string;
  database: "connected" | "disconnected" | string;
  mode: string;
}

export interface TelemetrySummary {
  total_events: number;
  avg_latency_ms: number;
  safety_escalations: number;
  error_rate: number;
  intents_breakdown: Record<string, number>;
  agents_breakdown: Record<string, number>;
  status_breakdown: Record<string, number>;
  tool_breakdown: Record<string, number>;
  zero_phi: boolean;
}

export interface QuantitativeScorecard {
  total_scenarios_evaluated: number;
  emergency_safety_recall_pct: number;
  prompt_injection_resistance_pct: number;
  unsupported_claim_rate_pct: number;
  intent_classification_accuracy_pct: number;
  routing_precision_pct: number;
  tool_selection_rate_pct: number;
  rag_grounding_faithfulness_pct: number;
  source_attribution_completeness_pct: number;
  overall_composite_score_pct: number;
  timestamp?: string;
}

export interface CostSummaryResponse {
  cost_summary: {
    total_tokens: number;
    total_cost_usd: number;
    avg_cost_per_workflow_usd: number;
    prompt_tokens?: number;
    completion_tokens?: number;
  };
  routing_policy: Record<string, unknown>;
  comparative_analysis: {
    cost_savings_percentage?: number;
    [key: string]: unknown;
  };
}

// ==========================================
// Phase 11A Analytics & Power BI Exports
// ==========================================

export interface AppointmentsAnalytics {
  total_count: number;
  by_status: Record<string, number>;
  by_specialty: Record<string, number>;
  by_doctor: Record<string, number>;
}

export interface MedicationsAnalytics {
  total_count: number;
  active_count: number;
  inactive_count: number;
  by_name: Record<string, number>;
  by_frequency: Record<string, number>;
}

export interface VitalsAnalytics {
  total_count: number;
  by_type: Record<string, number>;
}

export interface ConsentsAnalytics {
  total_count: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

export interface RemindersAnalytics {
  total_count: number;
  by_status: Record<string, number>;
}

export interface ClinicalOperationsAnalyticsResponse {
  total_patients: number;
  appointments: AppointmentsAnalytics;
  medications: MedicationsAnalytics;
  vitals: VitalsAnalytics;
  consents: ConsentsAnalytics;
  reminders: RemindersAnalytics;
  zero_phi: boolean;
}

export interface AgentTelemetryAnalyticsResponse {
  total_events: number;
  avg_latency_ms: number;
  safety_escalations: number;
  error_rate: number;
  intents_breakdown: Record<string, number>;
  agents_breakdown: Record<string, number>;
  status_breakdown: Record<string, number>;
  tool_breakdown: Record<string, number>;
  recent_traces_count: number;
  zero_phi: boolean;
}

export interface CostIntelligenceAnalyticsResponse {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_cost_per_workflow_usd: number;
  model_usage: Record<string, Record<string, unknown>>;
  tier_distribution: Record<string, number>;
  pricing_table: Record<string, Record<string, unknown>>;
  zero_phi: boolean;
}

// ==========================================
// Phase 11B Voice
// ==========================================

export interface VoiceTranscriptionResponse {
  transcript: string;
  detected_language: string;
  duration_seconds: number;
  is_mock: boolean;
}

export interface VoiceSynthesisRequest {
  text: string;
  voice_id?: string | null;
}

// ==========================================
// Phase 11C Vision
// ==========================================

export interface VisionAnalysisResponse {
  detected_features: string[];
  description: string;
  media_type: string;
  width?: number | null;
  height?: number | null;
  confidence: number;
  clinical_disclaimer: string;
  is_mock: boolean;
}

// ==========================================
// Phase 11D Messaging
// ==========================================

export type MessagingChannel = "sms" | "whatsapp";

export interface MessagingSendRequest {
  recipient: string;
  body: string;
  channel?: MessagingChannel;
  template_name?: string | null;
  template_params?: Record<string, unknown> | null;
}

export interface MessagingSendResponse {
  success: boolean;
  channel: string;
  provider: string;
  message_id: string;
  status: string;
  error_category?: string | null;
  is_mock: boolean;
}

export interface MessagingOptOutRequest {
  recipient: string;
  keyword: string;
  channel?: MessagingChannel;
}

export interface MessagingOptOutResponse {
  success: boolean;
  opted_out: boolean;
  keyword_matched: boolean;
  channel: string;
  status: string;
}
