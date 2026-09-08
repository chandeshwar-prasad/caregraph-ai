# CareGraph AI — Phase 11 Implementation Roadmap
## FHIR Integration + Observability Dashboard (Parallel Track)

**Timeline:** 4 weeks | **Effort:** Medium-High | **Impact:** Portfolio Gold  
**Target Completion:** Mid-October 2026

---

## 🎯 Executive Overview

### What You're Building

**Track A (Weeks 1-2): FHIR/EHR Integration**
- Connect agent to real FHIR-compliant systems
- Read/write patient data (appointments, medications, vitals)
- OAuth2 authentication flow
- Live demo with HL7 FHIR sandbox

**Track B (Weeks 2-3, parallel): Observability Dashboard**
- Real-time agent performance metrics
- LLM cost/quality trade-offs
- Safety escalation patterns
- Intent routing accuracy
- Public Grafana dashboard (zero PHI)

**Week 4: Consolidation**
- Documentation
- Demo video
- Blog post / case study

### Portfolio Narrative

> "Built a healthcare AI agent with FHIR interoperability connecting to real EHR systems, while instrumenting it with production-grade observability. The result: transparent, auditable, measurable clinical decision support."

---

## 📅 Week-by-Week Breakdown

---

## **WEEK 1: FHIR Integration Foundation**

### Day 1-2: FHIR Learning & Architecture Design

**Goals:**
- Understand FHIR resource model
- Design CareGraph ↔ FHIR mapping
- Choose sandbox environment

**Tasks:**

1. **FHIR Fundamentals (2 hours)**
   - Read: [FHIR Overview](http://hl7.org/fhir/overview.html)
   - Key concepts: Resources, profiles, references
   - Understand Patient, Appointment, Medication, Observation resources
   - Study: [SMART on FHIR](http://www.hl7.org/fhir/smart-app-launch/) OAuth2 flow

2. **Choose FHIR Sandbox (1 hour)**
   - Option A: HL7 Argonaut Test Server (public, no auth required)
   - Option B: Cerner Sandbox (requires registration, realistic)
   - Option C: SMART Sandbox (best for OAuth2 testing)
   - **Recommendation:** Start with HL7 Argonaut (easiest), then add Cerner

3. **Design Resource Mapping (2 hours)**
   
   Create mapping document:
   ```
   CareGraph Domain → FHIR Resource
   ─────────────────────────────────
   Patient (our model)
   └─ First Name, Last Name, DOB, Gender, Email, Phone
      → FHIR Patient resource (id, name, birthDate, gender, telecom)
   
   Appointment (our model)
   └─ Doctor Name, Specialty, Appointment Time, Status, Notes
      → FHIR Appointment resource (id, participant, start, status, description)
      → Include Practitioner reference (doctor)
   
   Medication (our model)
   └─ Name, Dosage, Frequency, Start Date
      → FHIR MedicationStatement resource
      → Reference to Medication + Patient
   
   Vital (our model)
   └─ Type (BP, HR, etc), Value, Unit, Timestamp
      → FHIR Observation resource (code, value, effectiveDateTime)
      → Link to Patient + Device
   ```

4. **Architecture Sketch (1 hour)**
   ```
   CareGraph Agent (existing)
         ↓
   FHIR Adapter Layer (NEW)
         ↓
   FHIR Client (abstracts FHIR API calls)
         ↓
   FHIR Server (Sandbox or Real EHR)
   ```

**Deliverables:**
- `docs/FHIR_MAPPING.md` (resource mapping guide)
- `docs/FHIR_ARCHITECTURE.md` (architecture diagram)
- `SANDBOX_SETUP.md` (how to connect to sandbox)

---

### Day 3-4: FHIR Client Implementation

**Goals:**
- Build reusable FHIR client library
- Handle OAuth2, REST calls, error handling
- Implement CRUD operations

**Tasks:**

1. **Create FHIR Client Abstraction (3 hours)**

   File: `app/services/fhir_client.py`

   ```python
   from typing import Optional, Dict, Any
   import httpx
   from pydantic import BaseModel
   
   class FHIRClientConfig(BaseModel):
       base_url: str  # e.g., "https://r4.smarthealthit.org/api/smartstu3/fhir"
       client_id: Optional[str] = None
       client_secret: Optional[str] = None
       access_token: Optional[str] = None
       scopes: List[str] = ["patient/Patient.read", "patient/Appointment.read"]
   
   class FHIRClient:
       """
       FHIR-compliant API client with OAuth2 support.
       Handles authentication, request/response serialization, error handling.
       """
       
       def __init__(self, config: FHIRClientConfig):
           self.config = config
           self.client = httpx.AsyncClient(
               base_url=config.base_url,
               timeout=30.0
           )
       
       async def get_patient(self, patient_id: str) -> Dict[str, Any]:
           """Fetch FHIR Patient resource"""
           response = await self.client.get(
               f"/Patient/{patient_id}",
               headers=self._auth_headers()
           )
           response.raise_for_status()
           return response.json()
       
       async def get_patient_appointments(self, patient_id: str) -> List[Dict]:
           """Search for appointments for a patient"""
           response = await self.client.get(
               "/Appointment",
               params={"patient": f"Patient/{patient_id}"},
               headers=self._auth_headers()
           )
           response.raise_for_status()
           data = response.json()
           return data.get("entry", [])
       
       async def create_appointment(self, appointment_data: Dict) -> Dict:
           """Create new FHIR Appointment"""
           response = await self.client.post(
               "/Appointment",
               json=appointment_data,
               headers=self._auth_headers()
           )
           response.raise_for_status()
           return response.json()
       
       async def get_medications(self, patient_id: str) -> List[Dict]:
           """Search for medication statements for a patient"""
           response = await self.client.get(
               "/MedicationStatement",
               params={"patient": f"Patient/{patient_id}"},
               headers=self._auth_headers()
           )
           response.raise_for_status()
           data = response.json()
           return data.get("entry", [])
       
       async def get_observations(self, patient_id: str, code: Optional[str] = None) -> List[Dict]:
           """Search for observations (vitals) for a patient"""
           params = {"patient": f"Patient/{patient_id}"}
           if code:
               params["code"] = code  # e.g., "8867-4" for heart rate
           
           response = await self.client.get(
               "/Observation",
               params=params,
               headers=self._auth_headers()
           )
           response.raise_for_status()
           data = response.json()
           return data.get("entry", [])
       
       def _auth_headers(self) -> Dict[str, str]:
           """Build authorization headers"""
           if self.config.access_token:
               return {"Authorization": f"Bearer {self.config.access_token}"}
           return {}
       
       async def oauth2_authorize(self, auth_code: str) -> str:
           """Exchange authorization code for access token"""
           # Implement OAuth2 token exchange
           pass
   ```

2. **Create FHIR → CareGraph Converter (2 hours)**

   File: `app/services/fhir_adapter.py`

   ```python
   from app.services.fhir_client import FHIRClient
   from app import schemas
   from typing import Optional
   
   class FHIRAdapter:
       """
       Convert between FHIR resources and CareGraph domain models.
       """
       
       def __init__(self, fhir_client: FHIRClient):
           self.fhir_client = fhir_client
       
       async def get_patient_profile(self, fhir_patient_id: str) -> schemas.PatientResponse:
           """Fetch from FHIR server and convert to CareGraph PatientResponse"""
           fhir_patient = await self.fhir_client.get_patient(fhir_patient_id)
           
           # Extract fields from FHIR resource
           name = fhir_patient.get("name", [{}])[0]
           telecom = fhir_patient.get("telecom", [])
           
           return schemas.PatientResponse(
               id=fhir_patient.get("id"),
               first_name=name.get("given", [""])[0],
               last_name=name.get("family", ""),
               date_of_birth=fhir_patient.get("birthDate"),
               gender=fhir_patient.get("gender"),
               email=next((t["value"] for t in telecom if t["system"] == "email"), None),
               phone=next((t["value"] for t in telecom if t["system"] == "phone"), None)
           )
       
       async def get_patient_medications(self, fhir_patient_id: str) -> List[schemas_ai.MedicationResponse]:
           """Fetch MedicationStatements from FHIR and convert"""
           fhir_meds = await self.fhir_client.get_medications(fhir_patient_id)
           
           medications = []
           for entry in fhir_meds:
               med = entry.get("resource", {})
               medications.append(schemas_ai.MedicationResponse(
                   id=med.get("id"),
                   name=med.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
                   dosage=med.get("dosage", [{}])[0].get("doseAndRate", [{}])[0].get("doseQuantity", {}).get("value"),
                   frequency=med.get("dosage", [{}])[0].get("timing", {}).get("repeat", {}).get("frequency"),
                   start_date=med.get("effectiveDateTime"),
                   notes=med.get("note", [{}])[0].get("text") if med.get("note") else None
               ))
           
           return medications
       
       async def get_patient_vitals(self, fhir_patient_id: str) -> List[schemas_ai.VitalResponse]:
           """Fetch Observations (vitals) from FHIR and convert"""
           fhir_obs = await self.fhir_client.get_observations(fhir_patient_id)
           
           vitals = []
           for entry in fhir_obs:
               obs = entry.get("resource", {})
               vitals.append(schemas_ai.VitalResponse(
                   id=obs.get("id"),
                   vital_type=obs.get("code", {}).get("coding", [{}])[0].get("code"),
                   value=obs.get("valueQuantity", {}).get("value"),
                   unit=obs.get("valueQuantity", {}).get("unit"),
                   recorded_at=obs.get("effectiveDateTime"),
                   notes=obs.get("note", [{}])[0].get("text") if obs.get("note") else None
               ))
           
           return vitals
       
       def appointment_to_fhir(self, appointment: schemas_ai.AppointmentResponse) -> Dict:
           """Convert CareGraph appointment to FHIR Appointment resource"""
           return {
               "resourceType": "Appointment",
               "status": appointment.status or "proposed",
               "description": appointment.notes or f"Appointment with {appointment.doctor_name}",
               "start": appointment.appointment_time,
               "participant": [
                   {
                       "actor": {"reference": f"Practitioner/{appointment.doctor_id}"},
                       "required": "required",
                       "status": "accepted"
                   },
                   {
                       "actor": {"reference": f"Patient/{appointment.patient_id}"},
                       "required": "required",
                       "status": "needs-action"
                   }
               ]
           }
   ```

3. **Create FHIR Sandbox Credentials File (1 hour)**

   File: `.env.fhir.example`

   ```
   # FHIR Sandbox Configuration
   FHIR_SERVER_URL=https://r4.smarthealthit.org/api/smartstu3/fhir
   FHIR_CLIENT_ID=your-client-id-here
   FHIR_CLIENT_SECRET=your-client-secret-here
   FHIR_SCOPES=patient/Patient.read,patient/Appointment.read,patient/Medication.read,patient/Observation.read
   FHIR_AUTH_METHOD=sandbox  # sandbox, oauth2, or basic
   
   # For sandbox (public), no auth needed:
   FHIR_SANDBOX_MODE=true
   ```

**Deliverables:**
- `app/services/fhir_client.py` (FHIR HTTP client)
- `app/services/fhir_adapter.py` (domain model converter)
- `.env.fhir.example` (configuration template)
- Tests: `tests/test_fhir_client.py` (unit tests against sandbox)

---

### Day 5: Integration & Testing

**Goals:**
- Wire FHIR adapter into existing patient_data_node
- Test against public sandbox
- Document setup instructions

**Tasks:**

1. **Update patient_data_node to support FHIR (1 hour)**

   File: `app/services/graph.py` (modify existing node)

   ```python
   async def patient_data_node(state: CareGraphState):
       """
       Enhanced to check: use FHIR if configured, else use local DB
       """
       user_id = state.get("user_id")
       patient_id = state.get("patient_id")  # Either DB ID or FHIR ID
       data_tool = state.get("patient_data_tool")
       
       # Check if FHIR is configured
       if os.getenv("FHIR_SANDBOX_MODE") == "true":
           fhir_config = FHIRClientConfig(
               base_url=os.getenv("FHIR_SERVER_URL"),
               access_token=state.get("fhir_access_token")
           )
           fhir_client = FHIRClient(fhir_config)
           adapter = FHIRAdapter(fhir_client)
           
           # Fetch from FHIR instead of local DB
           if data_tool == "medications":
               result = await adapter.get_patient_medications(patient_id)
           elif data_tool == "vitals":
               result = await adapter.get_patient_vitals(patient_id)
           # ... etc
       else:
           # Fall back to existing local DB logic
           result = patient_data.get_patient_medications(db, user_id)
       
       return {"patient_data_result": result}
   ```

2. **Test Against Sandbox (2 hours)**

   File: `tests/test_fhir_integration.py`

   ```python
   @pytest.mark.asyncio
   async def test_fhir_get_patient():
       """Test fetching real patient from FHIR sandbox"""
       config = FHIRClientConfig(
           base_url="https://r4.smarthealthit.org/api/smartstu3/fhir"
       )
       client = FHIRClient(config)
       
       # Use example patient from sandbox
       patient = await client.get_patient("SmartChris")
       
       assert patient["resourceType"] == "Patient"
       assert "name" in patient
       assert len(patient["name"]) > 0
   
   @pytest.mark.asyncio
   async def test_fhir_get_appointments():
       """Test fetching appointments from FHIR sandbox"""
       config = FHIRClientConfig(
           base_url="https://r4.smarthealthit.org/api/smartstu3/fhir"
       )
       client = FHIRClient(config)
       
       appointments = await client.get_patient_appointments("SmartChris")
       
       assert isinstance(appointments, list)
       # Sandbox may have appointments or not; just verify no error
   
   @pytest.mark.asyncio
   async def test_fhir_adapter_patient_conversion():
       """Test converting FHIR Patient → CareGraph PatientResponse"""
       adapter = FHIRAdapter(mock_fhir_client)
       
       patient = await adapter.get_patient_profile("SmartChris")
       
       assert isinstance(patient, schemas.PatientResponse)
       assert patient.first_name is not None
   ```

3. **Create Setup Documentation (1 hour)**

   File: `docs/FHIR_QUICKSTART.md`

   ```markdown
   # FHIR Integration Quickstart
   
   ## Option 1: Public Sandbox (No Auth Required)
   
   1. Set environment variables:
      ```
      FHIR_SANDBOX_MODE=true
      FHIR_SERVER_URL=https://r4.smarthealthit.org/api/smartstu3/fhir
      ```
   
   2. Run tests:
      ```bash
      pytest tests/test_fhir_integration.py -v
      ```
   
   3. Try the agent:
      ```bash
      curl -X POST http://localhost:8000/chat \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "message": "Get my medications",
          "patient_id": "SmartChris",
          "use_fhir": true
        }'
      ```
   
   ## Example FHIR Patients in Sandbox
   - SmartChris (has rich data)
   - SmartMom (family example)
   - SmartDad
   
   ## Option 2: Cerner Sandbox (Realistic Environment)
   
   1. Register at: https://code.cerner.com/
   2. Create app and get OAuth2 credentials
   3. Set environment variables:
      ```
      FHIR_SANDBOX_MODE=false
      FHIR_SERVER_URL=https://fhir-ehr.cerner.com/r4/cerner/ec2458f2-1e24-41c8-b71b-0e701af7583d/
      FHIR_CLIENT_ID=your_app_client_id
      FHIR_CLIENT_SECRET=your_app_client_secret
      FHIR_AUTH_METHOD=oauth2
      ```
   4. Follow OAuth2 authorization flow
   ```

**Deliverables:**
- Updated `patient_data_node` with FHIR support
- Integration tests passing against sandbox
- `docs/FHIR_QUICKSTART.md` (setup guide)
- Example FHIR API calls documented

---

## **WEEK 2: FHIR Production Patterns + Observability Setup**

### Day 1-2: FHIR Error Handling & Caching

**Goals:**
- Production-grade error handling
- Local caching (avoid hitting sandbox repeatedly)
- Retry logic for transient failures

**Tasks:**

1. **Enhanced FHIR Client with Resilience (2 hours)**

   File: `app/services/fhir_client.py` (extend)

   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   import logging
   
   logger = logging.getLogger("caregraph.fhir")
   
   class FHIRError(Exception):
       """Base FHIR client error"""
       pass
   
   class FHIRAuthenticationError(FHIRError):
       """OAuth2 or credentials error"""
       pass
   
   class FHIRResourceNotFoundError(FHIRError):
       """404 Patient/Appointment not found"""
       pass
   
   class FHIRNetworkError(FHIRError):
       """Network/connectivity error"""
       pass
   
   class FHIRClient:
       """Enhanced with error handling, caching, retry logic"""
       
       def __init__(self, config: FHIRClientConfig, cache_ttl_seconds: int = 300):
           self.config = config
           self.client = httpx.AsyncClient(base_url=config.base_url, timeout=30.0)
           self.cache = {}  # Simple in-memory cache
           self.cache_ttl = cache_ttl_seconds
       
       @retry(
           stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           reraise=True
       )
       async def get_patient(self, patient_id: str) -> Dict[str, Any]:
           """Fetch with retry logic and caching"""
           cache_key = f"patient_{patient_id}"
           
           # Check cache
           if cache_key in self.cache:
               cached_data, timestamp = self.cache[cache_key]
               if time.time() - timestamp < self.cache_ttl:
                   logger.info(f"Cache hit for patient {patient_id}")
                   return cached_data
           
           try:
               response = await self.client.get(
                   f"/Patient/{patient_id}",
                   headers=self._auth_headers()
               )
               
               if response.status_code == 401:
                   raise FHIRAuthenticationError(f"Invalid credentials for FHIR server")
               elif response.status_code == 404:
                   raise FHIRResourceNotFoundError(f"Patient {patient_id} not found")
               
               response.raise_for_status()
               data = response.json()
               
               # Cache the result
               self.cache[cache_key] = (data, time.time())
               
               return data
           
           except httpx.RequestError as e:
               logger.error(f"FHIR network error: {e}")
               raise FHIRNetworkError(f"Could not connect to FHIR server: {e}")
   ```

2. **FHIR Error Middleware (1 hour)**

   File: `app/middleware/fhir_error_handler.py`

   ```python
   from fastapi import Request
   from starlette.responses import JSONResponse
   from app.services.fhir_client import (
       FHIRError, FHIRAuthenticationError, 
       FHIRResourceNotFoundError, FHIRNetworkError
   )
   
   async def fhir_exception_handler(request: Request, exc: FHIRError):
       if isinstance(exc, FHIRAuthenticationError):
           return JSONResponse(
               status_code=401,
               content={"detail": "FHIR authentication failed. Check credentials."}
           )
       elif isinstance(exc, FHIRResourceNotFoundError):
           return JSONResponse(
               status_code=404,
               content={"detail": str(exc)}
           )
       elif isinstance(exc, FHIRNetworkError):
           return JSONResponse(
               status_code=503,
               content={"detail": "FHIR server temporarily unavailable"}
           )
       else:
           return JSONResponse(
               status_code=500,
               content={"detail": "Unexpected FHIR error"}
           )
   ```

**Deliverables:**
- Enhanced `fhir_client.py` with retry + caching
- Error handling middleware
- Error handling tests

---

### Day 3-5: Observability Dashboard Foundation

**Goals:**
- Set up metrics collection infrastructure
- Create Prometheus metrics
- Build Grafana dashboard template

**Tasks:**

1. **Prometheus Metrics Setup (2 hours)**

   File: `app/services/observability.py` (new, comprehensive)

   ```python
   from prometheus_client import Counter, Histogram, Gauge, generate_latest
   from typing import Optional, Dict, Any
   import time
   
   # Counter metrics
   graph_node_executions = Counter(
       'graph_node_executions_total',
       'Total executions of each graph node',
       ['node_name', 'status']  # status: success, error, interrupted
   )
   
   intent_classifications = Counter(
       'intent_classifications_total',
       'Intent classification results',
       ['detected_intent', 'correct_intent', 'match']  # match: true/false
   )
   
   safety_escalations = Counter(
       'safety_escalations_total',
       'Safety escalations triggered',
       ['escalation_type', 'risk_level']  # type: red_flag, approval_required
   )
   
   tool_executions = Counter(
       'tool_executions_total',
       'Tool execution attempts',
       ['tool_name', 'status']  # status: authorized, denied, executed
   )
   
   # Histogram metrics (latency, tokens, cost)
   graph_node_latency = Histogram(
       'graph_node_latency_seconds',
       'Latency of each graph node',
       ['node_name'],
       buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
   )
   
   llm_token_usage = Histogram(
       'llm_token_usage_total',
       'LLM token usage',
       ['model', 'token_type'],  # token_type: input, output
       buckets=(100, 500, 1000, 5000, 10000)
   )
   
   llm_request_latency = Histogram(
       'llm_request_latency_seconds',
       'LLM API request latency',
       ['model'],
       buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
   )
   
   # Gauge metrics (current state)
   active_sessions = Gauge(
       'active_sessions_current',
       'Number of active user sessions'
   )
   
   authorization_denials = Counter(
       'tool_authorization_denials_total',
       'Tool authorization denials by role',
       ['role', 'tool_name', 'reason']
   )
   
   consent_gate_checks = Counter(
       'consent_gate_checks_total',
       'Consent verification gate results',
       ['consent_type', 'result']  # result: granted, denied, expired
   )
   
   fhir_api_calls = Counter(
       'fhir_api_calls_total',
       'FHIR server API calls',
       ['method', 'resource_type', 'status_code']  # method: GET, POST, etc
   )
   
   fhir_api_latency = Histogram(
       'fhir_api_latency_seconds',
       'FHIR server API call latency',
       ['resource_type'],
       buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
   )
   
   # Model routing decisions
   model_selection = Counter(
       'model_selection_total',
       'Model selection by router policy',
       ['task_type', 'selected_model', 'reason']
   )
   
   class ObservabilityContext:
       """Context manager for tracking execution spans"""
       
       def __init__(self, node_name: str, metadata: Optional[Dict] = None):
           self.node_name = node_name
           self.metadata = metadata or {}
           self.start_time = None
       
       def __enter__(self):
           self.start_time = time.time()
           return self
       
       def __exit__(self, exc_type, exc_val, exc_tb):
           elapsed = time.time() - self.start_time
           status = 'error' if exc_type else 'success'
           
           graph_node_executions.labels(
               node_name=self.node_name,
               status=status
           ).inc()
           
           graph_node_latency.labels(
               node_name=self.node_name
           ).observe(elapsed)
           
           if exc_type:
               logger.error(f"Node {self.node_name} failed: {exc_val}")
           
           return False  # Re-raise exceptions
   
   def record_llm_call(model: str, input_tokens: int, output_tokens: int, latency: float):
       """Record LLM API call metrics"""
       llm_token_usage.labels(model=model, token_type='input').observe(input_tokens)
       llm_token_usage.labels(model=model, token_type='output').observe(output_tokens)
       llm_request_latency.labels(model=model).observe(latency)
   
   def record_fhir_call(method: str, resource_type: str, status_code: int, latency: float):
       """Record FHIR API call metrics"""
       fhir_api_calls.labels(
           method=method,
           resource_type=resource_type,
           status_code=status_code
       ).inc()
       
       fhir_api_latency.labels(resource_type=resource_type).observe(latency)
   ```

2. **Integrate Metrics into Existing Code (2 hours)**

   File: `app/services/graph.py` (add to each node)

   ```python
   from app.services.observability import ObservabilityContext, record_llm_call
   
   def triage_node(state: CareGraphState):
       with ObservabilityContext("triage_node", {"user_id": state.get("user_id")}):
           # ... existing triage logic ...
           pass
   
   def supervisor_node(state: CareGraphState):
       with ObservabilityContext("supervisor_node"):
           start = time.time()
           
           llm_service = get_llm_service()
           intent_info = llm_service.extract_intent(state.get("user_message"))
           
           latency = time.time() - start
           record_llm_call("llama-3.3-70b", input_tokens=450, output_tokens=50, latency=latency)
           
           # Record intent classification result
           from app.services.observability import intent_classifications
           intent_classifications.labels(
               detected_intent=intent_info.intent,
               correct_intent=intent_info.intent,  # In real scenario, track actual accuracy
               match="true"
           ).inc()
           
           return {"intent": intent_info.intent, ...}
   ```

3. **Expose Metrics Endpoint (1 hour)**

   File: `app/main.py` (add endpoint)

   ```python
   from prometheus_client import generate_latest
   
   @app.get("/metrics")
   def metrics():
       """Prometheus-compatible metrics endpoint"""
       return Response(
           content=generate_latest(),
           media_type="text/plain; charset=utf-8"
       )
   ```

4. **Create Grafana Dashboard Template (1 hour)**

   File: `grafana/caregraph-dashboard.json` (Grafana JSON export)

   ```json
   {
     "dashboard": {
       "title": "CareGraph AI Agent Performance",
       "panels": [
         {
           "title": "Graph Node Execution Latency (95th percentile)",
           "targets": [
             {
               "expr": "histogram_quantile(0.95, graph_node_latency_seconds)"
             }
           ]
         },
         {
           "title": "Intent Classification Accuracy",
           "targets": [
             {
               "expr": "rate(intent_classifications_total{match='true'}[5m]) / rate(intent_classifications_total[5m])"
             }
           ]
         },
         {
           "title": "Safety Escalations Over Time",
           "targets": [
             {
               "expr": "rate(safety_escalations_total[5m])"
             }
           ]
         },
         {
           "title": "LLM Token Usage",
           "targets": [
             {
               "expr": "rate(llm_token_usage_total[5m])"
             }
           ]
         },
         {
           "title": "FHIR API Call Latency",
           "targets": [
             {
               "expr": "histogram_quantile(0.95, fhir_api_latency_seconds)"
             }
           ]
         }
       ]
     }
   }
   ```

**Deliverables:**
- `app/services/observability.py` (metrics infrastructure)
- Metrics integrated into graph nodes
- `/metrics` endpoint (Prometheus-compatible)
- `grafana/caregraph-dashboard.json` (dashboard template)
- Docker setup for Prometheus + Grafana

---

## **WEEK 3: Polish, Testing, Documentation**

### Day 1-2: End-to-End Integration Testing

**Goals:**
- Test full workflow: User → Agent → FHIR Server
- Test observability: Metrics appear in Prometheus
- Test error scenarios

**Tasks:**

1. **E2E Test: FHIR Patient Retrieval (1 hour)**

   File: `tests/test_fhir_e2e.py`

   ```python
   @pytest.mark.asyncio
   async def test_e2e_patient_lookup_and_triage():
       """Full workflow: patient login → lookup via FHIR → triage"""
       
       # 1. Patient logs in
       auth_res = await client.post("/auth/login", json={
           "username": "patient_demo",
           "password": "patient_pass"
       })
       token = auth_res.json()["access_token"]
       
       # 2. Request chat with FHIR integration enabled
       chat_res = await client.post(
           "/chat",
           json={"message": "Get my medications"},
           headers={"Authorization": f"Bearer {token}"},
           params={"use_fhir": "true", "fhir_patient_id": "SmartChris"}
       )
       
       # 3. Verify response contains FHIR data
       assert "medication" in chat_res.json()["message"].lower()
       
       # 4. Verify metrics recorded
       metrics = await client.get("/metrics")
       assert b"graph_node_executions_total" in metrics.content
       assert b"fhir_api_calls_total" in metrics.content
   ```

2. **E2E Test: Observability Metrics (1 hour)**

   File: `tests/test_observability_e2e.py`

   ```python
   def test_prometheus_metrics_collected():
       """Verify metrics appear in Prometheus format"""
       metrics_response = client.get("/metrics")
       
       assert metrics_response.status_code == 200
       content = metrics_response.text
       
       # Check expected metrics are present
       assert "graph_node_latency_seconds" in content
       assert "intent_classifications_total" in content
       assert "fhir_api_calls_total" in content
       assert "safety_escalations_total" in content
       assert "llm_token_usage_total" in content
   
   def test_intent_accuracy_metric():
       """Verify intent classification accuracy is tracked"""
       # Run 10 triage requests
       for _ in range(10):
           client.post("/chat", json={"message": "I have chest pain"})
       
       # Check metric
       metrics = client.get("/metrics").text
       assert "intent_classifications_total" in metrics
   ```

### Day 3: Documentation & Guides

**Goals:**
- Write setup guides for FHIR + Observability
- Create demo scenarios
- Document architecture decisions

**Tasks:**

1. **Create FHIR Integration Guide (1 hour)**

   File: `docs/FHIR_INTEGRATION_GUIDE.md`

   ```markdown
   # FHIR Integration Guide for CareGraph AI
   
   ## Overview
   CareGraph AI can integrate with any FHIR-compliant EHR system using standard OAuth2.
   
   ## Supported Integrations
   - HL7 FHIR R4 Standard
   - Epic (via SMART on FHIR)
   - Cerner (via SMART on FHIR)
   - Athena Health
   - Any SMART-enabled EHR
   
   ## Setup Steps
   
   ### Step 1: Choose Your EHR
   ...
   
   ### Step 2: Configure OAuth2
   ...
   
   ### Step 3: Test Patient Lookup
   ...
   
   ### Step 4: Enable FHIR Mode in Agent
   ...
   ```

2. **Create Observability Guide (1 hour)**

   File: `docs/OBSERVABILITY_GUIDE.md`

   ```markdown
   # Observability & Monitoring Guide
   
   ## What We Measure
   
   - **Agent Performance**: Latency by node, execution success rate
   - **Intent Routing**: Accuracy of intent classification
   - **Safety**: Escalation rates, approval flow metrics
   - **LLM Efficiency**: Token usage, cost per query
   - **FHIR Integration**: API call latency, success rate
   
   ## Dashboard Access
   
   Local: http://localhost:3000 (Grafana)
   
   Production: [your-deployed-dashboard-url]
   
   ## Key Metrics Explained
   ...
   ```

3. **Demo Scenarios Document (1 hour)**

   File: `docs/DEMO_SCENARIOS.md`

   ```markdown
   # Live Demo Scenarios
   
   ## Scenario 1: Patient Looks Up Medications via FHIR
   
   **Setup:**
   - FHIR sandbox configured
   - Patient "SmartChris" available in sandbox
   
   **Flow:**
   1. User: "Show me my medications"
   2. Agent triages intent → RECORDS
   3. Agent queries FHIR server for MedicationStatements
   4. Dashboard shows FHIR API latency spike
   5. Response: "Your medications are [list from FHIR]"
   
   **Show in Demo:**
   - Prometheus dashboard showing FHIR call
   - Grafana showing intent classification
   - Real FHIR data in response
   
   ## Scenario 2: Safety Escalation Tracked in Observability
   
   **Flow:**
   1. User: "I have severe chest pain and shortness of breath"
   2. Red-flag detection triggers (deterministic, pre-LLM)
   3. Safety escalation counter increments
   4. Grafana dashboard shows spike in safety_escalations_total
   5. Agent: "This requires emergency care. Call 911."
   
   **Show in Demo:**
   - Real-time Grafana update
   - Metrics show escalation was recorded
   - Audit trail of decision
   ```

### Day 4-5: Docker Compose + Deployment

**Goals:**
- Containerize observability stack
- Full local deployment with FHIR + Prometheus + Grafana
- Ready for Render / cloud deployment

**Tasks:**

1. **Update docker-compose.yml (1 hour)**

   File: `docker-compose.yml` (add services)

   ```yaml
   version: '3.8'
   services:
     caregraph-db:
       # ... existing ...
     
     caregraph-api:
       # ... existing ...
       environment:
         FHIR_SANDBOX_MODE: 'true'
         FHIR_SERVER_URL: 'https://r4.smarthealthit.org/api/smartstu3/fhir'
     
     prometheus:
       image: prom/prometheus:latest
       volumes:
         - ./prometheus.yml:/etc/prometheus/prometheus.yml
         - prometheus-data:/prometheus
       ports:
         - "9090:9090"
       command:
         - '--config.file=/etc/prometheus/prometheus.yml'
     
     grafana:
       image: grafana/grafana:latest
       ports:
         - "3000:3000"
       environment:
         GF_SECURITY_ADMIN_PASSWORD: admin
         GF_INSTALL_PLUGINS: grafana-worldmap-panel
       volumes:
         - grafana-data:/var/lib/grafana
         - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
         - ./grafana/datasources:/etc/grafana/provisioning/datasources
       depends_on:
         - prometheus
   
   volumes:
     prometheus-data:
     grafana-data:
   ```

2. **Create Prometheus Configuration (30 min)**

   File: `prometheus.yml`

   ```yaml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
   
   scrape_configs:
     - job_name: 'caregraph-api'
       static_configs:
         - targets: ['localhost:8000']
       metrics_path: '/metrics'
   ```

3. **Create Grafana Datasource Config (30 min)**

   File: `grafana/datasources/prometheus.yml`

   ```yaml
   apiVersion: 1
   datasources:
     - name: Prometheus
       type: prometheus
       access: proxy
       url: http://prometheus:9090
       isDefault: true
   ```

**Deliverables:**
- Updated `docker-compose.yml` with Prometheus + Grafana
- `prometheus.yml` config
- Grafana provisioning files
- Full local stack deployment tested

---

## **WEEK 4: Documentation, Demo Video, Blog Post**

### Day 1-2: Comprehensive Documentation

**Files to create:**
- `PHASE_11_COMPLETION.md` (executive summary)
- `FHIR_ARCHITECTURE_DECISIONS.md` (technical deep-dive)
- `OBSERVABILITY_BEST_PRACTICES.md` (what we learned)
- Updated `README.md` with new Phase 11 features

### Day 3: Demo Video Script & Recording

**Demo Video: "Healthcare AI Agent with FHIR Integration & Real-Time Observability" (5 min)**

Script outline:
```
0:00 - Intro: "CareGraph AI now integrates with real EHR systems via FHIR"
0:30 - Dashboard view: Show Prometheus + Grafana running locally
1:00 - Demo flow: Patient message → Agent processes → FHIR query
2:00 - Show FHIR response: Real medication data from sandbox
2:30 - Zoom into Grafana: Show metrics in real-time
3:00 - Intent accuracy dashboard
3:30 - Safety escalation metrics
4:00 - FHIR API latency visualization
4:30 - Recap + "Production-ready healthcare AI"
```

### Day 4-5: Blog Post

**Blog Post: "Building Production Healthcare AI: FHIR Integration & Observability"**

Structure:
1. **Problem Statement** (why healthcare needs this)
2. **Architecture Overview** (diagram)
3. **FHIR Integration** (code walkthrough)
4. **Observability Design** (metrics, dashboards)
5. **Live Demo** (screenshots + video link)
6. **Lessons Learned** (what went well, what was hard)
7. **Next Steps** (evaluation framework, production deployment)

**Publish on:**
- Medium (healthcare AI audience)
- Dev.to (dev audience)
- LinkedIn (professional audience)
- GitHub README

---

## 📊 Success Criteria

### FHIR Integration ✅
- [ ] FHIR client connects to public sandbox without errors
- [ ] Successfully retrieves: Patient, Medications, Vitals, Appointments
- [ ] Error handling gracefully manages 404, 401, network errors
- [ ] Caching reduces redundant API calls
- [ ] Agent can answer "Show me my medications" using FHIR data
- [ ] OAuth2 flow documented (ready for real EHR integration)
- [ ] E2E tests passing against live sandbox

### Observability Dashboard ✅
- [ ] Prometheus metrics endpoint exposed at `/metrics`
- [ ] Grafana dashboard visualizes: latency, intent accuracy, safety escalations
- [ ] All graph nodes instrumented with timing + status metrics
- [ ] LLM token usage tracked per model
- [ ] FHIR API calls tracked (latency, success rate)
- [ ] Docker Compose brings up full stack: API + Prometheus + Grafana
- [ ] Zero PHI in metrics (anonymized, safe to share)
- [ ] Dashboard accessible locally + via cloud deployment

### Documentation ✅
- [ ] Setup guide: "How to connect to FHIR sandbox" (< 5 min)
- [ ] FHIR integration guide: "How to connect to real EHR" (detailed)
- [ ] Observability guide: "What metrics mean + how to use dashboard"
- [ ] Demo scenarios: Step-by-step workflows
- [ ] Architecture decisions documented

### Demo & Communication ✅
- [ ] Video demo: FHIR query + observability in action (5 min, published)
- [ ] Blog post published (Medium, Dev.to, LinkedIn)
- [ ] GitHub README updated with Phase 11 section
- [ ] Screenshots of Grafana dashboard in docs

---

## 🎓 Portfolio Narrative

### For Interviews/Hiring
> "In Phase 11, I integrated CareGraph AI with real FHIR-compliant EHR systems, enabling data retrieval from actual healthcare providers. Simultaneously, I instrumented the agent with production-grade observability using Prometheus and Grafana, allowing real-time monitoring of intent accuracy, safety escalation patterns, and LLM efficiency. The result is a transparently auditable healthcare AI system ready for clinical deployment."

### For Healthcare Organizations
> "CareGraph AI now connects to your EHR via FHIR, retrieving real patient data while maintaining full observability. Every decision is traceable: intent classification accuracy, safety escalations, tool authorizations, and cost metrics are all visible in real-time dashboards. This transparency builds clinical trust and regulatory compliance."

### For Investors/VC
> "We've demonstrated production healthcare AI with measurable outcomes: FHIR interoperability (go-to-market enabler), quantified safety metrics (regulatory requirement), and cost intelligence (unit economics). The agent is observable, auditable, and ready for institutional deployment."

---

## 📦 Deliverables Summary

### Code
- ✅ `app/services/fhir_client.py` (FHIR HTTP client)
- ✅ `app/services/fhir_adapter.py` (domain model converter)
- ✅ `app/services/observability.py` (Prometheus metrics)
- ✅ Updated `app/services/graph.py` (instrumented nodes)
- ✅ Updated `docker-compose.yml` (Prometheus + Grafana)
- ✅ Tests: `tests/test_fhir_*.py`, `tests/test_observability_*.py`

### Documentation
- ✅ `docs/FHIR_QUICKSTART.md`
- ✅ `docs/FHIR_INTEGRATION_GUIDE.md`
- ✅ `docs/FHIR_ARCHITECTURE_DECISIONS.md`
- ✅ `docs/OBSERVABILITY_GUIDE.md`
- ✅ `docs/DEMO_SCENARIOS.md`
- ✅ `PHASE_11_COMPLETION.md`

### Demo & Communication
- ✅ Demo video (5 min, YouTube)
- ✅ Blog post (Medium + Dev.to + LinkedIn)
- ✅ Updated README.md with Phase 11
- ✅ Grafana dashboard screenshots

### Configuration
- ✅ `.env.fhir.example` (FHIR credentials template)
- ✅ `prometheus.yml` (Prometheus scrape config)
- ✅ `grafana/datasources/*.yml` (Grafana provisioning)
- ✅ `grafana/caregraph-dashboard.json` (dashboard template)

---

## 🚀 Next Steps (After Phase 11)

1. **Phase 12: Comparative Evaluation** (1-2 weeks)
   - Benchmark CareGraph vs GPT-4, Claude on 100 scenarios
   - Publish results publicly

2. **Phase 13: Production Deployment** (1-2 weeks)
   - Deploy to cloud (Render, Azure, AWS)
   - Connect to real EHR sandbox (Cerner, Epic)
   - Public live demo

3. **Phase 14: Outcome Tracking** (2-3 weeks)
   - Feedback loops for continuous improvement
   - Measure real-world impact (adherence, ER prevention)

---

**Let's build this. You're ready. 🏥🚀**

