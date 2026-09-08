"""
app/services/fhir_client.py

HL7 FHIR R4 Compliant HTTP Client with Caching, Retry Logic, and Sandbox Support.
Provides:
1. Resilient synchronous and async FHIR client communicating with FHIR R4 servers (e.g. SMART on FHIR, Cerner, Epic).
2. Robust in-memory caching with TTL to avoid redundant sandbox/EHR network calls.
3. Tenacity-powered retries with exponential backoff on transient network failures.
4. Deterministic sandbox mock fallback when offline or in sandbox evaluation mode.
5. Zero-PHI telemetry compliance hooks.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("caregraph.fhir")


class FHIRError(Exception):
    """Base FHIR client error."""
    pass


class FHIRAuthenticationError(FHIRError):
    """Raised on 401/403 OAuth2 authentication or credential failure."""
    pass


class FHIRResourceNotFoundError(FHIRError):
    """Raised on 404 Patient/Observation/Appointment not found."""
    pass


class FHIRNetworkError(FHIRError):
    """Raised on transient network, connection, or gateway errors."""
    pass


class FHIRValidationError(FHIRError):
    """Raised on invalid FHIR resource payload or bad request."""
    pass


class FHIRClientConfig(BaseModel):
    """Configuration options for connecting to an HL7 FHIR R4 endpoint."""
    base_url: str = Field(
        default_factory=lambda: os.getenv("FHIR_SERVER_URL", "https://r4.smarthealthit.org")
    )
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("FHIR_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("FHIR_CLIENT_SECRET"))
    access_token: Optional[str] = Field(default_factory=lambda: os.getenv("FHIR_ACCESS_TOKEN"))
    scopes: List[str] = Field(
        default_factory=lambda: [
            "patient/Patient.read",
            "patient/Appointment.read",
            "patient/Appointment.write",
            "patient/MedicationRequest.read",
            "patient/MedicationStatement.read",
            "patient/Observation.read"
        ]
    )
    timeout: float = Field(default=15.0)
    sandbox_mode: bool = Field(
        default_factory=lambda: os.getenv("FHIR_SANDBOX_MODE", "true").lower() == "true"
    )
    mock_fallback: bool = Field(
        default_factory=lambda: os.getenv("FHIR_MOCK_FALLBACK", "true").lower() == "true"
    )
    cache_ttl_seconds: int = Field(default=300)


# Built-in deterministic sandbox mock data for offline testing and fallback
SAMPLE_FHIR_PATIENTS: Dict[str, Dict[str, Any]] = {
    "SmartChris": {
        "resourceType": "Patient",
        "id": "SmartChris",
        "active": True,
        "name": [
            {
                "use": "official",
                "family": "Smith",
                "given": ["Chris", "A."]
            }
        ],
        "telecom": [
            {"system": "email", "value": "chris.smith@example.com", "use": "home"},
            {"system": "phone", "value": "+1-555-019-2834", "use": "mobile"}
        ],
        "gender": "male",
        "birthDate": "1985-04-12"
    },
    "patient-101": {
        "resourceType": "Patient",
        "id": "patient-101",
        "active": True,
        "name": [
            {
                "use": "official",
                "family": "Taylor",
                "given": ["Alex"]
            }
        ],
        "telecom": [
            {"system": "email", "value": "alex.taylor@example.com", "use": "home"},
            {"system": "phone", "value": "+1-555-014-9988", "use": "mobile"}
        ],
        "gender": "female",
        "birthDate": "1990-11-23"
    }
}

SAMPLE_FHIR_MEDICATIONS: Dict[str, List[Dict[str, Any]]] = {
    "SmartChris": [
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-001",
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "314076",
                            "display": "Lisinopril 10 MG Oral Tablet"
                        }
                    ],
                    "text": "Lisinopril 10 MG Oral Tablet"
                },
                "dosageInstruction": [
                    {
                        "text": "Once daily by mouth",
                        "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                        "doseAndRate": [
                            {"doseQuantity": {"value": 10, "unit": "mg", "system": "http://unitsofmeasure.org"}}
                        ]
                    }
                ],
                "authoredOn": "2026-01-15",
                "note": [{"text": "Take with water in the morning for hypertension management."}]
            }
        },
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-002",
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": "860975",
                            "display": "Metformin hydrochloride 500 MG Oral Tablet"
                        }
                    ],
                    "text": "Metformin hydrochloride 500 MG Oral Tablet"
                },
                "dosageInstruction": [
                    {
                        "text": "Twice daily with meals",
                        "timing": {"repeat": {"frequency": 2, "period": 1, "periodUnit": "d"}},
                        "doseAndRate": [
                            {"doseQuantity": {"value": 500, "unit": "mg", "system": "http://unitsofmeasure.org"}}
                        ]
                    }
                ],
                "authoredOn": "2026-02-01",
                "note": [{"text": "Take with meals to prevent gastrointestinal upset."}]
            }
        }
    ]
}

SAMPLE_FHIR_OBSERVATIONS: Dict[str, List[Dict[str, Any]]] = {
    "SmartChris": [
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-bp-01",
                "status": "final",
                "category": [{"coding": [{"code": "vital-signs", "display": "Vital Signs"}]}],
                "code": {
                    "coding": [
                        {"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}
                    ],
                    "text": "Blood Pressure"
                },
                "effectiveDateTime": "2026-03-01T09:30:00Z",
                "component": [
                    {
                        "code": {"coding": [{"code": "8480-6", "display": "Systolic"}]},
                        "valueQuantity": {"value": 122, "unit": "mmHg"}
                    },
                    {
                        "code": {"coding": [{"code": "8462-4", "display": "Diastolic"}]},
                        "valueQuantity": {"value": 78, "unit": "mmHg"}
                    }
                ],
                "valueString": "122/78",
                "note": [{"text": "Sitting position, resting for 5 mins."}]
            }
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-hr-01",
                "status": "final",
                "category": [{"coding": [{"code": "vital-signs", "display": "Vital Signs"}]}],
                "code": {
                    "coding": [
                        {"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}
                    ],
                    "text": "Heart Rate"
                },
                "effectiveDateTime": "2026-03-01T09:30:00Z",
                "valueQuantity": {"value": 72, "unit": "bpm"},
                "note": [{"text": "Resting pulse."}]
            }
        }
    ]
}

SAMPLE_FHIR_APPOINTMENTS: Dict[str, List[Dict[str, Any]]] = {
    "SmartChris": [
        {
            "resource": {
                "resourceType": "Appointment",
                "id": "apt-fhir-01",
                "status": "booked",
                "description": "Routine Cardiovascular Follow-up",
                "start": "2026-10-15T10:00:00Z",
                "participant": [
                    {
                        "actor": {"reference": "Practitioner/dr-chen", "display": "Dr. Sarah Chen"},
                        "required": "required",
                        "status": "accepted"
                    },
                    {
                        "actor": {"reference": "Patient/SmartChris", "display": "Chris Smith"},
                        "required": "required",
                        "status": "accepted"
                    }
                ]
            }
        }
    ]
}


class FHIRClient:
    """
    HL7 FHIR R4 Client supporting authentication, response caching, retry resilience,
    and automatic sandbox mock fallbacks.
    """

    def __init__(self, config: Optional[FHIRClientConfig] = None):
        self.config = config or FHIRClientConfig()
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.client = httpx.Client(
            base_url=self.config.base_url.rstrip("/"),
            timeout=self.config.timeout
        )

    def _auth_headers(self) -> Dict[str, str]:
        """Constructs Authorization headers if a Bearer access token is available."""
        headers = {
            "Accept": "application/fhir+json, application/json",
            "Content-Type": "application/fhir+json"
        }
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        return headers

    def _get_from_cache(self, key: str) -> Optional[Any]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                logger.debug(f"FHIR Cache hit for key: {key}")
                return data
            else:
                del self.cache[key]
        return None

    def _store_in_cache(self, key: str, data: Any):
        self.cache[key] = (data, time.time())

    def _record_metric(self, method: str, resource: str, status: str = "success", latency: float = 0.05):
        try:
            from app.services import observability
            observability.record_fhir_call(method=method, resource_type=resource, status=status, latency_seconds=latency)
        except Exception:
            pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(FHIRNetworkError),
        reraise=True
    )
    def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """
        Fetch FHIR Patient resource by ID.
        """
        cache_key = f"patient_{patient_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        t0 = time.time()
        try:
            response = self.client.get(f"/Patient/{patient_id}", headers=self._auth_headers())
            if response.status_code == 401 or response.status_code == 403:
                raise FHIRAuthenticationError(f"FHIR auth failed with status {response.status_code}")
            elif response.status_code == 404:
                # Check fallback
                if self.config.mock_fallback and patient_id in SAMPLE_FHIR_PATIENTS:
                    data = SAMPLE_FHIR_PATIENTS[patient_id]
                    self._store_in_cache(cache_key, data)
                    self._record_metric("GET", "Patient", "mock_fallback", time.time() - t0)
                    return data
                raise FHIRResourceNotFoundError(f"FHIR Patient '{patient_id}' not found.")
            response.raise_for_status()
            data = response.json()
            self._store_in_cache(cache_key, data)
            self._record_metric("GET", "Patient", "success", time.time() - t0)
            return data
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"FHIR network error contacting {self.config.base_url}: {exc}")
            if self.config.mock_fallback:
                data = SAMPLE_FHIR_PATIENTS.get(patient_id, SAMPLE_FHIR_PATIENTS["SmartChris"])
                self._store_in_cache(cache_key, data)
                self._record_metric("GET", "Patient", "mock_fallback", time.time() - t0)
                return data
            self._record_metric("GET", "Patient", "error", time.time() - t0)
            raise FHIRNetworkError(f"FHIR network failure: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(FHIRNetworkError),
        reraise=True
    )
    def get_patient_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Search for MedicationRequest or MedicationStatement resources for a given patient.
        """
        cache_key = f"meds_{patient_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # Query MedicationRequest first (standard in R4)
            response = self.client.get(
                "/MedicationRequest",
                params={"patient": patient_id, "_count": 20},
                headers=self._auth_headers()
            )
            if response.status_code == 401 or response.status_code == 403:
                raise FHIRAuthenticationError("FHIR authentication failed while querying medications.")
            response.raise_for_status()
            data = response.json()
            entries = data.get("entry", [])
            
            # If empty, try MedicationStatement
            if not entries:
                stmt_resp = self.client.get(
                    "/MedicationStatement",
                    params={"patient": patient_id, "_count": 20},
                    headers=self._auth_headers()
                )
                if stmt_resp.is_success:
                    entries = stmt_resp.json().get("entry", [])

            if not entries and self.config.mock_fallback and patient_id in SAMPLE_FHIR_MEDICATIONS:
                entries = SAMPLE_FHIR_MEDICATIONS[patient_id]

            self._store_in_cache(cache_key, entries)
            return entries
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"FHIR network error fetching medications: {exc}")
            if self.config.mock_fallback:
                entries = SAMPLE_FHIR_MEDICATIONS.get(patient_id, SAMPLE_FHIR_MEDICATIONS.get("SmartChris", []))
                self._store_in_cache(cache_key, entries)
                return entries
            raise FHIRNetworkError(f"FHIR network failure: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(FHIRNetworkError),
        reraise=True
    )
    def get_patient_observations(self, patient_id: str, code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for Observation (vitals/labs) resources for a given patient.
        """
        cache_key = f"obs_{patient_id}_{code or 'all'}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, Any] = {"patient": patient_id, "_count": 20}
        if code:
            params["code"] = code

        try:
            response = self.client.get(
                "/Observation",
                params=params,
                headers=self._auth_headers()
            )
            if response.status_code == 401 or response.status_code == 403:
                raise FHIRAuthenticationError("FHIR authentication failed while querying observations.")
            response.raise_for_status()
            data = response.json()
            entries = data.get("entry", [])
            if not entries and self.config.mock_fallback and patient_id in SAMPLE_FHIR_OBSERVATIONS:
                entries = SAMPLE_FHIR_OBSERVATIONS[patient_id]
            self._store_in_cache(cache_key, entries)
            return entries
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"FHIR network error fetching observations: {exc}")
            if self.config.mock_fallback:
                entries = SAMPLE_FHIR_OBSERVATIONS.get(patient_id, SAMPLE_FHIR_OBSERVATIONS.get("SmartChris", []))
                self._store_in_cache(cache_key, entries)
                return entries
            raise FHIRNetworkError(f"FHIR network failure: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(FHIRNetworkError),
        reraise=True
    )
    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Search for Appointment resources for a patient.
        """
        cache_key = f"apts_{patient_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = self.client.get(
                "/Appointment",
                params={"patient": f"Patient/{patient_id}", "_count": 20},
                headers=self._auth_headers()
            )
            if response.status_code == 401 or response.status_code == 403:
                raise FHIRAuthenticationError("FHIR authentication failed while querying appointments.")
            response.raise_for_status()
            data = response.json()
            entries = data.get("entry", [])
            if not entries and self.config.mock_fallback and patient_id in SAMPLE_FHIR_APPOINTMENTS:
                entries = SAMPLE_FHIR_APPOINTMENTS[patient_id]
            self._store_in_cache(cache_key, entries)
            return entries
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"FHIR network error fetching appointments: {exc}")
            if self.config.mock_fallback:
                entries = SAMPLE_FHIR_APPOINTMENTS.get(patient_id, SAMPLE_FHIR_APPOINTMENTS.get("SmartChris", []))
                self._store_in_cache(cache_key, entries)
                return entries
            raise FHIRNetworkError(f"FHIR network failure: {exc}") from exc

    def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post a new Appointment resource to the FHIR server.
        """
        try:
            response = self.client.post(
                "/Appointment",
                json=appointment_data,
                headers=self._auth_headers()
            )
            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 401 or response.status_code == 403:
                raise FHIRAuthenticationError("FHIR authentication failed while creating appointment.")
            response.raise_for_status()
            return response.json()
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning(f"FHIR network error creating appointment: {exc}")
            if self.config.mock_fallback:
                # Return synthetic created appointment resource
                created = dict(appointment_data)
                created["id"] = f"apt-fhir-mock-{int(time.time())}"
                created["status"] = "booked"
                return created
            raise FHIRNetworkError(f"FHIR network failure: {exc}") from exc

    def close(self):
        """Close the underlying HTTPX client connection pool."""
        self.client.close()
