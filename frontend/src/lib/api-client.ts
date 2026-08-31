/**
 * CareGraph AI - Typed API Client
 * Centralized HTTP client interfacing strictly with FastAPI endpoints
 */

import {
  UserCreate,
  UserResponse,
  Token,
  PatientCreate,
  PatientResponse,
  ChatRequest,
  ChatResponse,
  ApprovalRequest,
  AppointmentResponse,
  VitalCreate,
  VitalResponse,
  MedicationResponse,
  MedicationReminderCreate,
  MedicationReminderResponse,
  ConsentGrantRequest,
  ConsentRevokeRequest,
  ConsentResponse,
  HealthResponse,
  TelemetrySummary,
  QuantitativeScorecard,
  CostSummaryResponse,
  ClinicalOperationsAnalyticsResponse,
  AgentTelemetryAnalyticsResponse,
  CostIntelligenceAnalyticsResponse,
  VoiceTranscriptionResponse,
  VoiceSynthesisRequest,
  VisionAnalysisResponse,
  MessagingSendRequest,
  MessagingSendResponse,
  MessagingOptOutRequest,
  MessagingOptOutResponse,
} from "../types/api";

export class ApiClientError extends Error {
  public status: number;
  public detail: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail || message;
  }
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor() {
    this.baseUrl = (
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    ).replace(/\/$/, "");
  }

  public setToken(token: string | null): void {
    this.token = token;
  }

  public getToken(): string | null {
    return this.token;
  }

  private getHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...customHeaders,
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

    let res: Response;
    try {
      res = await fetch(url, options);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Network error";
      throw new ApiClientError(0, `Cannot connect to CareGraph API: ${errorMsg}`);
    }

    if (!res.ok) {
      let detail = "An unexpected error occurred.";
      try {
        const errorData = await res.json();
        if (typeof errorData?.detail === "string") {
          detail = errorData.detail;
        } else if (Array.isArray(errorData?.detail)) {
          detail = errorData.detail.map((d: { msg?: string }) => d.msg || "").join(", ");
        }
      } catch {
        detail = res.statusText || `HTTP Error ${res.status}`;
      }

      if (res.status === 401) {
        throw new ApiClientError(401, "Authentication session expired or invalid credentials.", detail);
      }
      if (res.status === 403) {
        throw new ApiClientError(403, "Access denied. Operation not permitted for your user role.", detail);
      }

      throw new ApiClientError(res.status, `Request failed with status ${res.status}`, detail);
    }

    // Handle empty responses
    if (res.status === 204) {
      return {} as T;
    }

    return res.json() as Promise<T>;
  }

  // ==========================================
  // Authentication Endpoints
  // ==========================================

  public async register(payload: UserCreate): Promise<UserResponse> {
    return this.request<UserResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  public async login(username: string, password: string): Promise<Token> {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const tokenRes = await this.request<Token>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (tokenRes?.access_token) {
      this.setToken(tokenRes.access_token);
    }

    return tokenRes;
  }

  // ==========================================
  // Patient Profile Endpoints
  // ==========================================

  public async getMyProfile(): Promise<PatientResponse> {
    return this.request<PatientResponse>("/patients/me", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async createMyProfile(payload: PatientCreate): Promise<PatientResponse> {
    return this.request<PatientResponse>("/patients/me", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // Admin Endpoints
  // ==========================================

  public async getAllPatients(): Promise<PatientResponse[]> {
    return this.request<PatientResponse[]>("/admin/patients", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  // ==========================================
  // LangGraph AI Chat & HITL Coordination
  // ==========================================

  public async sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>("/chat", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  public async approveCoordination(payload: ApprovalRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>("/chat/approve", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // Appointments Endpoints
  // ==========================================

  public async getMyAppointments(): Promise<AppointmentResponse[]> {
    return this.request<AppointmentResponse[]>("/appointments/me", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async cancelMyAppointment(appointmentId: number): Promise<AppointmentResponse> {
    return this.request<AppointmentResponse>(`/appointments/${appointmentId}/cancel`, {
      method: "POST",
      headers: this.getHeaders(),
    });
  }

  // ==========================================
  // Vitals Endpoints
  // ==========================================

  public async getMyVitals(vitalType?: string, limit: number = 20): Promise<VitalResponse[]> {
    const params = new URLSearchParams();
    if (vitalType) params.append("vital_type", vitalType);
    params.append("limit", limit.toString());

    return this.request<VitalResponse[]>(`/vitals/me?${params.toString()}`, {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async recordMyVital(payload: VitalCreate): Promise<VitalResponse> {
    return this.request<VitalResponse>("/vitals/me", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // Medications & Reminders Endpoints
  // ==========================================

  public async getMyMedications(): Promise<MedicationResponse[]> {
    return this.request<MedicationResponse[]>("/medications/me", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async getMyReminders(): Promise<MedicationReminderResponse[]> {
    return this.request<MedicationReminderResponse[]>("/reminders/me", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async createMyReminder(payload: MedicationReminderCreate): Promise<MedicationReminderResponse> {
    return this.request<MedicationReminderResponse>("/reminders/me", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  public async cancelMyReminder(reminderId: number): Promise<MedicationReminderResponse> {
    return this.request<MedicationReminderResponse>(`/reminders/${reminderId}/cancel`, {
      method: "POST",
      headers: this.getHeaders(),
    });
  }

  // ==========================================
  // Consent Management Endpoints
  // ==========================================

  public async getMyConsents(): Promise<ConsentResponse[]> {
    return this.request<ConsentResponse[]>("/consents/me", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async grantMyConsent(payload: ConsentGrantRequest): Promise<ConsentResponse> {
    return this.request<ConsentResponse>("/consents/me/grant", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  public async revokeMyConsent(payload: ConsentRevokeRequest): Promise<ConsentResponse> {
    return this.request<ConsentResponse>("/consents/me/revoke", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  // ==========================================
  // System Health & Observability Metrics
  // ==========================================

  public async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health", { method: "GET" });
  }

  public async getTelemetryMetrics(): Promise<TelemetrySummary> {
    return this.request<TelemetrySummary>("/metrics/telemetry", { method: "GET" });
  }

  public async getEvaluationMetrics(): Promise<QuantitativeScorecard> {
    return this.request<QuantitativeScorecard>("/metrics/evaluation", { method: "GET" });
  }

  public async getCostMetrics(): Promise<CostSummaryResponse> {
    return this.request<CostSummaryResponse>("/metrics/costs", { method: "GET" });
  }

  // ==========================================
  // Phase 11A Analytics Endpoints
  // ==========================================

  public async getClinicalOperationsAnalytics(): Promise<ClinicalOperationsAnalyticsResponse> {
    return this.request<ClinicalOperationsAnalyticsResponse>("/analytics/clinical-operations", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async getAgentTelemetryAnalytics(): Promise<AgentTelemetryAnalyticsResponse> {
    return this.request<AgentTelemetryAnalyticsResponse>("/analytics/agent-telemetry", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public async getCostIntelligenceAnalytics(): Promise<CostIntelligenceAnalyticsResponse> {
    return this.request<CostIntelligenceAnalyticsResponse>("/analytics/cost-intelligence", {
      method: "GET",
      headers: this.getHeaders(),
    });
  }

  public getExportDatasetUrl(datasetName: string, format: "json" | "csv" = "csv"): string {
    return `${this.baseUrl}/analytics/export/${encodeURIComponent(datasetName)}?format=${format}`;
  }

  // ==========================================
  // Phase 11B Voice Endpoints
  // ==========================================

  public async transcribeAudio(audioBlob: Blob, filename: string = "audio.wav"): Promise<VoiceTranscriptionResponse> {
    const formData = new FormData();
    formData.append("file", audioBlob, filename);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    return this.request<VoiceTranscriptionResponse>("/voice/transcribe", {
      method: "POST",
      headers,
      body: formData,
    });
  }

  public async synthesizeSpeech(payload: VoiceSynthesisRequest): Promise<Blob> {
    const url = `${this.baseUrl}/voice/synthesize`;
    const headers = this.getHeaders({ "Content-Type": "application/json" });

    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new ApiClientError(res.status, "Voice synthesis failed.");
    }

    return res.blob();
  }

  // ==========================================
  // Phase 11C Vision Endpoints
  // ==========================================

  public async analyzeImage(imageBlob: Blob, filename: string = "image.png"): Promise<VisionAnalysisResponse> {
    const formData = new FormData();
    formData.append("file", imageBlob, filename);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    return this.request<VisionAnalysisResponse>("/vision/analyze", {
      method: "POST",
      headers,
      body: formData,
    });
  }

  // ==========================================
  // Phase 11D Messaging Endpoints
  // ==========================================

  public async sendMessage(payload: MessagingSendRequest): Promise<MessagingSendResponse> {
    return this.request<MessagingSendResponse>("/messaging/send", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }

  public async optOutMessaging(payload: MessagingOptOutRequest): Promise<MessagingOptOutResponse> {
    return this.request<MessagingOptOutResponse>("/messaging/opt-out", {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  }
}

export const apiClient = new ApiClient();
