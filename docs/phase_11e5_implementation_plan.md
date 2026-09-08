# CareGraph AI — Phase 11E-5 Implementation Plan
## Multi-Modal Integration Suite: Voice, Vision & WhatsApp/SMS Messaging

---

### Executive Summary

Phase 11E-5 expands CareGraph AI's Next.js App Router frontend with complete multi-modal interfaces connecting directly to the verified FastAPI backend services delivered in Phase 11B (Voice), Phase 11C (Vision), and Phase 11D (Messaging).

All integrations leverage browser-native Web APIs (`MediaRecorder`, `Blob`, `FileReader`, HTML5 `<audio>`), the existing typed `apiClient` (`api-client.ts`), and the Vanilla CSS design system without introducing third-party UI or media processing dependencies.

---

### 1. Repository Baseline Verification

- **Branch**: `main`
- **Synchronized Remote**: `origin/main`
- **Baseline HEAD**: `6c9daee` (`feat: implement Phase 11E-4 patient health records and care management suite`)
- **Working Tree**: Clean (0 uncommitted changes)
- **Backend Test Baseline**: 215 / 215 passed
- **Frontend Test Baseline**: 48 / 48 passed
- **Frontend Type-Check**: 0 TypeScript errors
- **Production Build**: 17 / 17 static pages prerendered successfully

---

### 2. Backend Contracts & Security Invariants

#### A. Voice Endpoints (Phase 11B)
| Method | Path | Auth | Request | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/voice/transcribe` | Bearer JWT (Patient/Admin) | `multipart/form-data` with `file` (audio binary, max 10MB) | `VoiceTranscriptionResponse` (`transcript`, `detected_language`, `duration_seconds`, `is_mock`) |
| `POST` | `/voice/synthesize` | Bearer JWT (Patient/Admin) | JSON `VoiceSynthesisRequest` (`text`, `voice_id?`) | Streaming `audio/wav` binary response |

**Invariants**:
- Zero disk retention: all audio processed in-memory.
- Zero raw audio or transcripts in server/client debug logs.
- Automatic mock fallback when cloud credentials are omitted.

#### B. Vision Endpoint (Phase 11C)
| Method | Path | Auth | Request | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/vision/analyze` | Bearer JWT (Patient/Admin) | `multipart/form-data` with `file` (PNG/JPEG/WEBP image, max 10MB) | `VisionAnalysisResponse` (`detected_features`, `description`, `media_type`, `width`, `height`, `confidence`, `clinical_disclaimer`, `is_mock`) |

**Invariants**:
- Zero disk retention: images analyzed in-memory.
- Mandatory clinical non-diagnostic disclaimer required on all visual observation outputs.
- No autonomous diagnosis or treatment advice generated.

#### C. Messaging Endpoints (Phase 11D)
| Method | Path | Auth | Request | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/messaging/send` | Bearer JWT (Patient/Admin) | JSON `MessagingSendRequest` (`recipient`, `body`, `channel: "sms" \| "whatsapp"`, `template_name?`, `template_params?`) | `MessagingSendResponse` (`success`, `channel`, `provider`, `message_id`, `status`, `is_mock`) |
| `POST` | `/messaging/opt-out` | Bearer JWT (Patient/Admin) | JSON `MessagingOptOutRequest` (`recipient`, `keyword`, `channel?`) | `MessagingOptOutResponse` (`success`, `opted_out`, `keyword_matched`, `channel`, `status`) |

**Invariants**:
- E.164 recipient validation and masking (`+1 ***-***-1234`).
- Keyword opt-out enforcement (`STOP`, `UNSUBSCRIBE`, `CANCEL`).
- Consent verification before dispatch.

---

### 3. Frontend Architecture & Dependency Strategy

#### Zero-Dependency Browser-Native Media Architecture
- **Voice Recording**: Pure `navigator.mediaDevices.getUserMedia` + `MediaRecorder` generating `Blob` (`audio/webm` or `audio/wav`).
- **Voice Synthesis Playback**: Pure `URL.createObjectURL(blob)` piped to standard HTML5 `<audio>` element with auto-cleanup via `URL.revokeObjectURL()`.
- **Vision Image Handling**: Pure HTML `<input type="file" accept="image/png,image/jpeg,image/webp">` + `FileReader` / `URL.createObjectURL` for instant UI preview.
- **Styling**: Vanilla CSS tokens in `globals.css` (media player card, dropzones, recording pulse animation, structured observation tag pills).

---

### 4. Logical Substeps & Implementation Breakdown

```
Phase 11E-5
├── 11E-5-1: Voice Navigation & Synthesis UI (/voice)
├── 11E-5-2: Vision Document Analyzer UI (/vision)
├── 11E-5-3: Outbound Messaging Gateway Console (/admin/messaging)
└── 11E-5-4: Automated Multi-Modal Test Suite & Regression Verification
```

---

#### Step 11E-5-1: Voice Navigation & Synthesis UI
- **Target Page**: `frontend/src/app/(authenticated)/voice/page.tsx`
- **Features**:
  - Live in-browser microphone capture with visual timer and pulsating recording indicator.
  - Manual audio file upload fallback.
  - Transcription call to `apiClient.transcribeAudio()`.
  - Structured transcription results card (Transcript text, Detected language, Duration, Mock status).
  - Quick action: "Send to AI Care Coordinator (`/chat`)".
  - Text-to-Speech synthesis input calling `apiClient.synthesizeSpeech()` with voice selector.
  - Native HTML audio playback controls.
- **Files Modified/Created**:
  - `frontend/src/app/(authenticated)/voice/page.tsx`
  - `frontend/src/styles/globals.css` (audio player & record pulse styles)
- **Proposed Commit**:
  `feat: implement Phase 11E-5-1 voice recording, transcription, and speech synthesis UI`

---

#### Step 11E-5-2: Vision Document Analyzer UI
- **Target Page**: `frontend/src/app/(authenticated)/vision/page.tsx`
- **Features**:
  - Drag-and-drop file upload dropzone for PNG, JPEG, WEBP.
  - Instant client-side preview with image dimensions display.
  - Analysis action calling `apiClient.analyzeImage()`.
  - Structured visual observation report:
    - Detected features tag badges
    - Observational description
    - Confidence indicator bar
    - Mock vs. Cloud provider badge
    - Prominent mandatory non-diagnostic disclaimer alert
- **Files Modified/Created**:
  - `frontend/src/app/(authenticated)/vision/page.tsx`
  - `frontend/src/styles/globals.css` (dropzone & tag pill styles)
- **Proposed Commit**:
  `feat: implement Phase 11E-5-2 vision document analyzer and observation report UI`

---

#### Step 11E-5-3: Outbound Messaging Gateway Console
- **Target Page**: `frontend/src/app/(authenticated)/admin/messaging/page.tsx`
- **Features**:
  - SMS vs. WhatsApp channel switcher tab.
  - E.164 phone recipient input with format validation.
  - Message body textarea with character counter (160 for SMS, 4096 for WhatsApp).
  - Dispatch action calling `apiClient.sendMessage()`.
  - Delivery response card (Message ID, Status, Provider, Mock badge).
  - Interactive Opt-Out Simulator drawer calling `apiClient.optOutMessaging()` to test keywords (`STOP`, `UNSUBSCRIBE`).
- **Files Modified/Created**:
  - `frontend/src/app/(authenticated)/admin/messaging/page.tsx`
- **Proposed Commit**:
  `feat: implement Phase 11E-5-3 SMS and WhatsApp outbound messaging gateway console`

---

#### Step 11E-5-4: Multi-Modal Automated Test Suite & Hardening
- **Target Test File**: `frontend/tests/multimodal.test.mjs`
- **Test Coverage**:
  - Voice transcription payload generation and schema validation.
  - Voice synthesis request parameters and Blob stream handling.
  - Vision image format validation (PNG, JPEG, WEBP) and size limits.
  - Vision structured observation schema and clinical disclaimer invariants.
  - Messaging channel normalization, E.164 recipient validation, and opt-out keyword logic.
  - Security review: Zero PHI and zero unmasked tokens in client logs.
- **Files Created**:
  - `frontend/tests/multimodal.test.mjs`
- **Proposed Commit**:
  `test: add Phase 11E-5 multi-modal automated test suite for voice, vision, and messaging`

---

### 5. Testing & Validation Checklist

1. **Frontend Tests**:
   ```bash
   npm --prefix frontend test
   ```
2. **TypeScript Compilation**:
   ```bash
   npm --prefix frontend run type-check
   ```
3. **Next.js Production Build**:
   ```bash
   npm --prefix frontend run build
   ```
4. **Backend Regression Pytest**:
   ```bash
   .venv\Scripts\python.exe -m pytest -v
   ```
5. **Git Whitespace & Formatting**:
   ```bash
   git diff --check
   ```

---

### 6. Risk Assessment & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Browser denies microphone access | Provide audio file upload input as seamless fallback |
| Browser does not support MediaRecorder codec | Use standard `audio/webm` or `audio/wav` fallback MIME types |
| Large image file upload memory exhaustion | Client-side 10MB size validation check before initiating request |
| Sensitive message text leaked to console | Strictly prohibit `console.log` of raw message bodies or recipient numbers |
