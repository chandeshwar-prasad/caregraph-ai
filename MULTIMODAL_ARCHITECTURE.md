# CareGraph AI — Multimodal Coordination Architecture (Phase 11+)

**Status:** Design Phase (Not MVP)  
**Version:** 1.0  
**Last Updated:** 2026-09-08

> **IMPORTANT DISCLAIMER:** This document outlines the **planned multimodal architecture** for Phase 11 and beyond. The current implementation (Phases 1–10) is **text-only**. Vision, Voice, and Messaging endpoints exist as **isolated utility services** for future integration and are NOT currently woven into the main care coordination graph.

---

## 1. Multimodal Architecture Overview

### 1.1 Current State (Phases 1–10)
- **Text-only chat coordination** via `POST /chat` endpoint
- **Vision/Voice/Messaging as isolated HTTP utilities** (no graph integration)
- **Single input modality** per request

### 1.2 Planned State (Phase 11+)
- **Unified multimodal input layer** that normalizes all modalities to structured form
- **Modality-aware intent classification** adapted for context-rich inputs
- **Coordinated multi-output** (text response + optional SMS/Voice/Follow-up)
- **Priority routing** when users submit concurrent modalities

---

## 2. Core Principles

### 2.1 Modality Priority Hierarchy
```
Priority 1: Voice (user-initiated speech, most intentional)
Priority 2: Text (explicit, unambiguous)
Priority 3: Vision (supporting/evidence)
Priority 4: Async (incoming SMS/notification, lowest priority)
```

**Rationale:**
- Voice indicates real-time user engagement; treat as primary intent
- Text is explicit and unambiguous
- Vision is evidence/supporting material, not the primary request
- Async messages are background notifications

### 2.2 Multimodal Input Principle
If a user submits:
```
Voice: "Show me my blood pressure"
Vision: [image of BP monitor]
```

The system should:
1. Transcribe voice → "show me blood pressure"
2. Analyze vision → "BP: 120/80 visible in image"
3. **Synthesize**: "I see you're asking about your blood pressure, and you've shared a BP monitor image. Retrieving your recorded readings and analyzing the image…"
4. **Execute**: Patient Data Node retrieves structured vitals + Vision Node extracts reading from image
5. **Respond**: Return text response + optional voice reading + confirmation SMS

---

## 3. Modality Abstraction Layer

### 3.1 InputModality Data Structure

```python
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

class ModalityType(str, Enum):
    """Supported input modalities."""
    TEXT = "text"
    VOICE = "voice"
    VISION = "vision"
    DOCUMENT = "document"
    ASYNC_SMS = "async_sms"
    ASYNC_EMAIL = "async_email"

class ModalityConfidence(str, Enum):
    """Confidence in extracted/transcribed content."""
    HIGH = "high"          # < 5% error rate
    MEDIUM = "medium"      # 5-20% error rate
    LOW = "low"            # > 20% error rate

@dataclass
class InputModality:
    """
    Normalized representation of a user input in any modality.
    All modalities are converted to this standard form for uniform processing.
    """
    # Core Identity
    type: ModalityType
    session_id: str
    user_id: int
    timestamp: str  # ISO 8601
    
    # Primary Content (REQUIRED)
    extracted_text: str  # Normalized text representation of user intent
    raw_content: bytes | str  # Original input (for audit/analysis)
    
    # Confidence & Quality Metrics
    extraction_confidence: float  # 0.0-1.0: How confident is the transcription/translation?
    semantic_confidence: float    # 0.0-1.0: How well does this represent the user's intent?
    
    # Extracted Metadata (OPTIONAL, modality-specific)
    metadata: Dict[str, Any]
    """
    Examples:
    TEXT:
      - language: "en"
      - sentiment: "neutral"
    
    VOICE:
      - language: "en"
      - detected_emotion: "neutral"
      - speaker_confidence: 0.95
      - duration_seconds: 2.5
      - accent_region: "US-East"
    
    VISION:
      - detected_objects: ["blood pressure monitor", "vital sign display"]
      - text_extracted_from_image: "BP: 120/80"
      - image_resolution: (1920, 1080)
      - document_type: "medical_device_display"
      - orientation: "upright"
    
    DOCUMENT:
      - filename: "bp_readings_2026.pdf"
      - page_count: 5
      - extracted_tables: [...]
      - document_classification: "health_record"
    """
    
    # Priority & Routing Hints (SET BY COORDINATOR)
    priority: int = 0  # Higher = more urgent (0-100)
    inferred_intent: Optional[str] = None  # Pre-classified intent (if known)
    requires_high_confidence: bool = False  # Must extraction be confident?
    
    # Audit Trail
    raw_request_id: str = ""  # Reference to original HTTP request
    processing_notes: str = ""  # Human-readable context

@dataclass
class MultimodalInputCoordination:
    """
    When multiple modalities are submitted together, this represents their coordination.
    """
    primary_modality: InputModality  # The "main" request
    supporting_modalities: List[InputModality]  # Evidence/context
    conflict_detected: bool  # e.g., voice says "approve" but text says "reject"
    recommended_action: str  # "use_primary" | "synthesize" | "escalate_to_human"
    synthesis_note: str  # Why this recommendation?
```

### 3.2 Modality Extraction Functions

```python
# app/services/modality.py

from app.services.voice import get_stt_service
from app.services.vision import get_vision_service
import logging

logger = logging.getLogger("caregraph.modality")

def extract_text_modality(
    text: str,
    session_id: str,
    user_id: int
) -> InputModality:
    """Direct text input — minimal processing."""
    return InputModality(
        type=ModalityType.TEXT,
        session_id=session_id,
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        extracted_text=text.strip(),
        raw_content=text,
        extraction_confidence=1.0,
        semantic_confidence=0.95,  # Text is explicit but may be ambiguous
        metadata={"language": "en", "input_method": "direct_text"}
    )

def extract_voice_modality(
    audio_bytes: bytes,
    filename: str,
    session_id: str,
    user_id: int
) -> InputModality:
    """
    Voice → Text via STT provider.
    Extracts both the transcript AND confidence metrics.
    """
    try:
        stt_service = get_stt_service()
        stt_result = stt_service.transcribe(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type="audio/wav"
        )
        
        transcript = stt_result.get("transcript", "")
        detected_language = stt_result.get("detected_language", "en")
        duration = stt_result.get("duration_seconds", 0.0)
        
        # Confidence heuristics
        word_count = len(transcript.split())
        extraction_confidence = 0.9 if word_count > 3 else 0.75  # Longer = more reliable
        
        return InputModality(
            type=ModalityType.VOICE,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            extracted_text=transcript,
            raw_content=audio_bytes,
            extraction_confidence=extraction_confidence,
            semantic_confidence=0.85,  # Voice can be unclear or context-dependent
            metadata={
                "language": detected_language,
                "duration_seconds": duration,
                "word_count": word_count,
                "transcription_provider": "groq_whisper" if not stt_service.is_mock_mode() else "mock"
            }
        )
    except Exception as e:
        logger.error(f"Voice extraction failed: {e}")
        raise

def extract_vision_modality(
    image_bytes: bytes,
    filename: str,
    session_id: str,
    user_id: int
) -> InputModality:
    """
    Image → Description + OCR via Vision provider.
    Extracts visual features and any readable text.
    """
    try:
        vision_service = get_vision_service()
        vision_result = vision_service.analyze_image(
            image_bytes=image_bytes,
            filename=filename,
            content_type="image/png"
        )
        
        description = vision_result.get("description", "")
        detected_features = vision_result.get("detected_features", [])
        media_type = vision_result.get("media_type", "image/png")
        width = vision_result.get("width")
        height = vision_result.get("height")
        
        # Build extracted text from description
        # (In a real system, you'd do OCR + object detection here)
        extracted_text = f"Visual analysis: {description}"
        
        # Vision is supporting evidence, not primary intent
        return InputModality(
            type=ModalityType.VISION,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            extracted_text=extracted_text,
            raw_content=image_bytes,
            extraction_confidence=0.80,  # Vision can have false positives
            semantic_confidence=0.70,  # Vision alone doesn't clearly indicate intent
            metadata={
                "media_type": media_type,
                "resolution": f"{width}x{height}" if width and height else "unknown",
                "detected_features": detected_features,
                "vision_provider": "groq_vision" if not vision_service.is_mock_mode() else "mock",
                "raw_description": description
            }
        )
    except Exception as e:
        logger.error(f"Vision extraction failed: {e}")
        raise

def extract_document_modality(
    file_bytes: bytes,
    filename: str,
    session_id: str,
    user_id: int
) -> InputModality:
    """
    Document (PDF, image, etc.) → Extracted text + structure.
    
    For MVP, this is a placeholder. Full implementation would:
    - Use PyPDF2 or similar for PDFs
    - Apply OCR for scanned documents
    - Extract tables/structured data
    """
    try:
        # Placeholder: Just note that we received a document
        extracted_text = f"Document uploaded: {filename}. Document processing not yet implemented in MVP."
        
        return InputModality(
            type=ModalityType.DOCUMENT,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            extracted_text=extracted_text,
            raw_content=file_bytes,
            extraction_confidence=0.5,  # Not implemented yet
            semantic_confidence=0.3,
            metadata={
                "filename": filename,
                "file_size_bytes": len(file_bytes),
                "status": "not_yet_implemented"
            }
        )
    except Exception as e:
        logger.error(f"Document extraction failed: {e}")
        raise
```

---

## 4. Multimodal Input Coordinator

### 4.1 Receive & Coordinate Multiple Modalities

```python
# app/services/multimodal_coordinator.py

from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger("caregraph.multimodal")

class MultimodalInputCoordinator:
    """
    Receives inputs in any modality, normalizes them,
    prioritizes them, and detects conflicts.
    """
    
    PRIORITY_ORDER = {
        ModalityType.VOICE: 100,      # Highest priority
        ModalityType.TEXT: 80,
        ModalityType.VISION: 60,
        ModalityType.DOCUMENT: 50,
        ModalityType.ASYNC_SMS: 20,   # Background notifications
        ModalityType.ASYNC_EMAIL: 10,
    }
    
    @staticmethod
    def score_modality(modality: InputModality) -> int:
        """
        Score a modality based on type, confidence, and contextual factors.
        Higher score = higher priority.
        """
        base_score = MultimodalInputCoordinator.PRIORITY_ORDER.get(modality.type, 0)
        confidence_factor = modality.extraction_confidence * 20  # Max +20 points
        return int(base_score + confidence_factor)
    
    @staticmethod
    def coordinate(
        modalities: List[InputModality]
    ) -> MultimodalInputCoordination:
        """
        Given a list of modalities submitted together (or within a small time window),
        coordinate them and establish priority.
        
        Returns a coordination plan with recommended action.
        """
        if not modalities:
            raise ValueError("At least one modality must be provided.")
        
        if len(modalities) == 1:
            return MultimodalInputCoordination(
                primary_modality=modalities[0],
                supporting_modalities=[],
                conflict_detected=False,
                recommended_action="use_primary",
                synthesis_note="Single modality input, no coordination needed."
            )
        
        # Score and rank by priority
        scored = [
            (modality, MultimodalInputCoordinator.score_modality(modality))
            for modality in modalities
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        primary = scored[0][0]
        supporting = [m[0] for m in scored[1:]]
        
        # Detect conflicts
        conflict = MultimodalInputCoordinator._detect_conflict(primary, supporting)
        
        # Recommend action
        if conflict:
            recommendation = "escalate_to_human"
            note = f"Conflict: {primary.extracted_text} vs {supporting[0].extracted_text if supporting else ''}"
        elif primary.extraction_confidence < 0.7:
            recommendation = "synthesize"
            note = f"Primary modality ({primary.type}) has low confidence ({primary.extraction_confidence}). Synthesizing with supporting modalities."
        else:
            recommendation = "use_primary"
            note = f"Using {primary.type} as primary modality (score: {scored[0][1]}). Supporting modalities: {[m.type for m in supporting]}"
        
        return MultimodalInputCoordination(
            primary_modality=primary,
            supporting_modalities=supporting,
            conflict_detected=conflict,
            recommended_action=recommendation,
            synthesis_note=note
        )
    
    @staticmethod
    def _detect_conflict(
        primary: InputModality,
        supporting: List[InputModality]
    ) -> bool:
        """
        Detect semantic conflicts between modalities.
        
        Examples:
        - Voice: "Approve appointment" + Text: "Reject appointment"
        - Vision: BP monitor shows 180/110 + Text: "My BP is normal"
        """
        primary_text_lower = primary.extracted_text.lower()
        
        for support in supporting:
            support_text_lower = support.extracted_text.lower()
            
            # Simple heuristic: Look for opposing keywords
            approve_keywords = ["approve", "yes", "confirm", "ok", "accept"]
            reject_keywords = ["reject", "no", "deny", "cancel", "decline"]
            
            primary_approves = any(kw in primary_text_lower for kw in approve_keywords)
            primary_rejects = any(kw in primary_text_lower for kw in reject_keywords)
            
            support_approves = any(kw in support_text_lower for kw in approve_keywords)
            support_rejects = any(kw in support_text_lower for kw in reject_keywords)
            
            if (primary_approves and support_rejects) or (primary_rejects and support_approves):
                return True
        
        return False
    
    @staticmethod
    def synthesize_narrative(coordination: MultimodalInputCoordination) -> str:
        """
        Generate a human-readable narrative of what the user is trying to do.
        This can be logged for audit purposes.
        """
        primary = coordination.primary_modality
        supporting = coordination.supporting_modalities
        
        lines = [
            f"User Intent Analysis (Session: {primary.session_id})",
            f"Primary Input: {primary.type.value.upper()} - {primary.extracted_text[:100]}",
        ]
        
        if supporting:
            for i, mod in enumerate(supporting, 1):
                lines.append(f"Supporting Input {i}: {mod.type.value.upper()} - {mod.extracted_text[:100]}")
        
        lines.append(f"Recommendation: {coordination.recommended_action}")
        lines.append(f"Confidence: {coordination.primary_modality.extraction_confidence * 100:.1f}%")
        
        if coordination.conflict_detected:
            lines.append(f"⚠️ CONFLICT DETECTED: {coordination.synthesis_note}")
        
        return "\n".join(lines)
```

---

## 5. Updated Graph State & Intent Classification

### 5.1 Extended CareGraphState

```python
# In app/services/graph.py, update the TypedDict:

class CareGraphState(TypedDict, total=False):
    # === Original Fields (Phases 1-10) ===
    session_id: str
    user_id: int
    user_role: Optional[str]
    user_message: str  # For backward compatibility (text modality only)
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
    
    # === NEW: Multimodal Input (Phase 11+) ===
    # These fields ONLY appear in multimodal-aware graph instances
    primary_modality: Optional[InputModality] = None
    supporting_modalities: Optional[List[InputModality]] = None
    modality_coordination: Optional[MultimodalInputCoordination] = None
    
    # Modality-specific processing results
    vision_analysis: Optional[Dict[str, Any]] = None  # From vision node
    voice_transcript: Optional[str] = None  # From voice STT
    
    # Output modality preference (set by user or default)
    output_modalities: List[str] = ["text"]  # ["text", "voice", "sms"] etc.
```

### 5.2 Multimodal-Aware Intent Classification

```python
# In app/services/llm.py, add:

def extract_intent_multimodal(
    self,
    primary_modality: InputModality,
    supporting_modalities: Optional[List[InputModality]] = None
) -> IntentExtraction:
    """
    Extract intent with modality-aware context.
    
    Modality provides hints to the LLM:
    - If vision shows medical document, hint toward RECORDS intent
    - If voice input is lengthy, hint toward conversational intent
    - If vision shows vital sign display, hint toward RECORDS intent
    """
    
    # Build context string
    context_lines = [
        f"User submitted input via {primary_modality.type.value.upper()}.",
        f"Primary Message: {primary_modality.extracted_text}",
    ]
    
    if supporting_modalities:
        for i, mod in enumerate(supporting_modalities, 1):
            context_lines.append(f"Supporting {mod.type.value.upper()}: {mod.extracted_text[:200]}")
    
    # Modality-specific hints
    if primary_modality.type == ModalityType.VISION:
        detected = primary_modality.metadata.get("detected_features", [])
        if any("vital" in f.lower() or "chart" in f.lower() for f in detected):
            context_lines.append("HINT: Vision analysis detected vital signs or medical chart. Consider RECORDS intent.")
    
    if primary_modality.type == ModalityType.VOICE:
        duration = primary_modality.metadata.get("duration_seconds", 0)
        if duration > 30:
            context_lines.append("HINT: Voice input is lengthy and conversational. Consider allowing follow-up.")
    
    # Prepare system prompt with modality context
    system_prompt = (
        "You are a healthcare intent classifier. Consider the modality of user input when classifying intent. "
        "\n".join(context_lines)
    )
    
    # Use existing extraction but with enhanced system prompt
    intent_info = self.extract_intent(
        primary_modality.extracted_text,
        system_prompt_override=system_prompt
    )
    
    return intent_info
```

---

## 6. Integration Points: How Modalities Feed into Graph

### 6.1 Text Chat Endpoint (Current, Phases 1-10)

```python
# In app/main.py (EXISTING - UNCHANGED)
@app.post("/chat", response_model=schemas_ai.ChatResponse)
def chat_coordination(
    request: schemas_ai.ChatRequest,
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    """Text-only chat (backward compatible)."""
    # ... existing implementation ...
```

### 6.2 Voice Endpoint (NEW, Phase 11)

```python
# In app/main.py (NEW - Phase 11+)
@app.post("/chat/voice", response_model=schemas_ai.ChatResponse)
async def chat_via_voice(
    file: UploadFile = File(..., description="Audio to transcribe and process as chat"),
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    """
    Voice chat: Transcribe → Inject into coordination graph → Optionally return voice response.
    Phase 11+ feature.
    """
    try:
        audio_bytes = await file.read()
        session_id = "voice_" + str(current_user.id) + "_" + datetime.utcnow().isoformat()
        
        # Step 1: Extract voice modality
        from app.services.modality import extract_voice_modality
        voice_modality = extract_voice_modality(
            audio_bytes=audio_bytes,
            filename=file.filename or "voice_input.wav",
            session_id=session_id,
            user_id=current_user.id
        )
        
        # Step 2: Create graph state with multimodal input
        thread_id = f"user_{current_user.id}_{session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "user_message": voice_modality.extracted_text,  # Backward compatible
            "user_id": current_user.id,
            "user_role": current_user.role,
            "session_id": thread_id,
            "primary_modality": voice_modality,  # NEW: Multimodal aware
            "output_modalities": ["text", "voice"],  # Also return voice response
            "is_mock": voice_modality.metadata.get("transcription_provider") == "mock"
        }
        
        # Step 3: Run through graph
        graph.invoke(initial_state, config=config)
        snapshot = graph.get_state(config)
        state_values = snapshot.values
        
        # Step 4: Prepare response (text by default)
        response_message = state_values.get("final_response", "")
        
        # Step 5: If output_modalities includes voice, synthesize TTS
        if "voice" in state_values.get("output_modalities", ["text"]):
            from app.services.voice import get_tts_service
            tts_service = get_tts_service()
            tts_result = tts_service.synthesize(response_message)
            # Return audio bytes instead of text
            return Response(
                content=tts_result["audio_bytes"],
                media_type="audio/wav",
                headers={"X-Transcript": response_message}  # Include text for debugging
            )
        
        return {
            "message": response_message,
            "intent": state_values.get("intent", "general"),
            "entities": state_values.get("extracted_entities", {}),
            "is_mock": state_values.get("is_mock", True),
            "session_id": session_id,
            "approval_required": state_values.get("approval_required", False),
            "risk_level": state_values.get("risk_level"),
            "safety_escalated": state_values.get("safety_escalated", False),
            "modality_used": "voice"
        }
    
    except Exception as e:
        logger.error(f"Voice chat error: {e}")
        raise HTTPException(status_code=500, detail="Voice processing failed")


@app.post("/chat/vision", response_model=schemas_ai.ChatResponse)
async def chat_with_vision(
    file: UploadFile = File(..., description="Image to analyze and discuss"),
    query: Optional[str] = Query(None, description="Optional text query to accompany image"),
    current_user: models.User = Depends(auth.require_role("patient")),
    db: Session = Depends(get_db)
):
    """
    Vision chat: Analyze image → Synthesize with optional text query → Inject into graph.
    Phase 11+ feature.
    """
    try:
        image_bytes = await file.read()
        session_id = "vision_" + str(current_user.id) + "_" + datetime.utcnow().isoformat()
        
        # Step 1: Extract vision modality
        from app.services.modality import extract_vision_modality
        vision_modality = extract_vision_modality(
            image_bytes=image_bytes,
            filename=file.filename or "vision_input.png",
            session_id=session_id,
            user_id=current_user.id
        )
        
        # Step 2: If user also provided text, coordinate modalities
        modalities = [vision_modality]
        if query:
            from app.services.modality import extract_text_modality
            text_modality = extract_text_modality(query, session_id, current_user.id)
            modalities.append(text_modality)
        
        from app.services.multimodal_coordinator import MultimodalInputCoordinator
        coordination = MultimodalInputCoordinator.coordinate(modalities)
        
        # Step 3: Create graph state
        thread_id = f"user_{current_user.id}_{session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Synthesize the message
        combined_message = f"{coordination.primary_modality.extracted_text}"
        if coordination.supporting_modalities:
            combined_message += "\n\n[Additional context from: " + ", ".join(
                m.type.value for m in coordination.supporting_modalities
            ) + "]"
        
        initial_state = {
            "user_message": combined_message,
            "user_id": current_user.id,
            "user_role": current_user.role,
            "session_id": thread_id,
            "primary_modality": coordination.primary_modality,
            "supporting_modalities": coordination.supporting_modalities,
            "modality_coordination": coordination,
            "output_modalities": ["text"],
            "is_mock": vision_modality.metadata.get("vision_provider") == "mock"
        }
        
        # Step 4: Run through graph
        graph.invoke(initial_state, config=config)
        snapshot = graph.get_state(config)
        state_values = snapshot.values
        
        return {
            "message": state_values.get("final_response", ""),
            "intent": state_values.get("intent", "general"),
            "entities": state_values.get("extracted_entities", {}),
            "is_mock": state_values.get("is_mock", True),
            "session_id": session_id,
            "modality_used": "vision",
            "vision_analysis": state_values.get("vision_analysis")
        }
    
    except Exception as e:
        logger.error(f"Vision chat error: {e}")
        raise HTTPException(status_code=500, detail="Vision processing failed")
```

---

## 7. Phase 11 Rollout Plan

### Phase 11.1 — Voice Integration (Weeks 1-2)
- [ ] Implement `InputModality` and `extract_voice_modality()`
- [ ] Create `/chat/voice` endpoint
- [ ] Add voice → text → graph → voice TTS pipeline
- [ ] Test: "What's my next appointment?" via voice
- [ ] Create integration tests for voice input

### Phase 11.2 — Vision Integration (Weeks 3-4)
- [ ] Implement `extract_vision_modality()`
- [ ] Create `/chat/vision` endpoint
- [ ] Implement `MultimodalInputCoordinator`
- [ ] Update intent classification with modality hints
- [ ] Test: "Analyze this BP monitor photo" via vision
- [ ] Test: "Show me my vitals" (text) + upload BP image (vision) = coordinated response

### Phase 11.3 — Output Modality (Weeks 5-6)
- [ ] Implement `output_modalities` in state
- [ ] Create `responder_node_multimodal()` that adapts output format
- [ ] Implement voice response synthesis in responder
- [ ] Test: Approval via voice (interrupt + voice synthesis)

### Phase 11.4 — Messaging Integration (Weeks 7-8)
- [ ] Wire messaging service into appointment confirmation flow
- [ ] On appointment approval → auto-send SMS confirmation
- [ ] Add user preference for output channel (SMS/Email/Voice/None)
- [ ] Test: "Book an appointment" → voice approval → SMS confirmation

### Phase 11.5 — Document Processing (Weeks 9-10)
- [ ] Implement PDF/document OCR extraction
- [ ] Create `/chat/document` endpoint
- [ ] Parse medical documents → structured health data
- [ ] Test: Upload BP readings PDF → extract values → populate vitals

---

## 8. Safety & Validation

### 8.1 Multimodal Safety Rules
- Voice approvals bypass HITL confirmation only if confidence > 0.95
- Vision-only medical claims (e.g., "this shows diabetes") require human verification
- Conflicting modalities must be escalated to human review
- Document uploads limited to 50MB and approved file types only

### 8.2 Modality-Specific Rate Limits
```python
MODALITY_RATE_LIMITS = {
    ModalityType.TEXT: 100_per_minute,     # 100 requests/min
    ModalityType.VOICE: 60_per_hour,       # 60 requests/hour (more expensive)
    ModalityType.VISION: 50_per_hour,      # 50 requests/hour (more expensive)
    ModalityType.DOCUMENT: 10_per_hour,    # 10 requests/hour (most expensive)
}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests
- `test_extract_voice_modality()`: Transcription accuracy
- `test_extract_vision_modality()`: Image analysis correctness
- `test_multimodal_coordination()`: Priority ordering and conflict detection
- `test_modality_priority_hierarchy()`: Verify priority order

### 9.2 Integration Tests
- `test_voice_to_chat_workflow()`: Voice input → transcription → graph → text response
- `test_vision_to_chat_workflow()`: Vision input → analysis → graph → grounded response
- `test_concurrent_modalities()`: Submit text + vision simultaneously
- `test_modality_conflict_handling()`: Conflicting inputs are escalated
- `test_voice_output_tts()`: Text response → voice synthesis → audio bytes

### 9.3 E2E Tests
- User submits voice request, receives voice response
- User uploads BP monitor photo, system extracts reading and compares to stored vitals
- User provides voice approval for appointment (no HITL delay)
- User uploads document, system extracts structured data

---

## 10. Deprecation & Backward Compatibility

### Phases 1-10 (Current)
- `/chat` endpoint is **text-only** and remains unchanged
- Vision/Voice/Messaging endpoints exist as **isolated utilities** (no graph integration)
- State schema uses only `user_message: str`

### Phase 11 (Multimodal)
- `/chat` remains **text-only** for backward compatibility
- NEW: `/chat/voice`, `/chat/vision`, `/chat/document` endpoints with full graph integration
- State schema extended with `primary_modality`, `supporting_modalities`, etc.
- Old clients (text-only) continue to work; new clients can opt into multimodal

### Phase 12+ (Future)
- Unified `/chat` endpoint that auto-detects modality based on input
- Deprecate isolated `/vision/analyze`, `/voice/transcribe` endpoints

---

## 11. References & Further Reading

- LangGraph StateGraph documentation: Multimodal state design
- Speech recognition best practices: Confidence thresholds for approval
- Vision ML: Object detection for medical devices
- Multimodal LLMs: Handling mixed-modality reasoning

