# CareGraph AI — WhatsApp/SMS Messaging Integration Guide
## Provider-Agnostic Messaging & Zero-Persistence Architecture

This document describes the design, API endpoints, security invariants, and consent boundary for the CareGraph AI WhatsApp and SMS Messaging service layer.

---

## 1. Overview & Architecture

CareGraph AI provides provider-agnostic messaging capabilities across `sms` and `whatsapp` channels. The messaging service operates in-memory with strict zero-persistence, PHI-sanitized logging, and decoupled vendor abstraction.

```
┌────────────────────────────────────────────────────────┐
│               CareGraph AI Client Application          │
│               (Patient Portal / Admin Portal)          │
└───────────────────────────┬────────────────────────────┘
                            │ Bearer <JWT>
                            ▼
┌────────────────────────────────────────────────────────┐
│           CareGraph AI FastAPI Backend                 │
│                                                        │
│   POST /messaging/send     POST /messaging/opt-out     │
│   ┌────────────────────────────────────────────────┐   │
│   │ JWT Authentication & RBAC Enforcement          │   │
│   └───────────────────────┬────────────────────────┘   │
│                           ▼                            │
│   ┌────────────────────────────────────────────────┐   │
│   │ Messaging Service Layer (`app/services/messaging.py`)│
│   │  • E.164 Recipient Validation                  │   │
│   │  • Clamped Body Length Validation              │   │
│   │  • Zero-Persistence / In-Memory Dispatch       │   │
│   │  • PHI-Sanitized Logging (No Body/Phone)       │   │
│   │  • Consent & Opt-Out Keyword Detection         │   │
│   └───────────────────────┬────────────────────────┘   │
└───────────────────────────┼────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌───────────────────────┐       ┌────────────────────────┐
│  MockMessagingService │       │  CloudMessagingService │
│  (Deterministic CI/Dev│       │  (REST Adapter via     │
│   Zero Network Calls) │       │   httpx / Twilio / Meta)│
└───────────────────────┘       └────────────────────────┘
```

---

## 2. API Specifications

### 2.1 Send Outbound Message (`POST /messaging/send`)
- **Authentication**: `Bearer <JWT>` (Patient or Admin)
- **Supported Channels**: `sms`, `whatsapp`
- **Payload Limits**: Max 1,600 characters per message (`DEFAULT_MAX_MESSAGE_LENGTH`)
- **Recipient Format**: Valid E.164 phone string (`^\+?[1-9]\d{6,14}$`)

#### Example Request:
```json
{
  "recipient": "+12025550143",
  "body": "CareGraph AI: Your prescription has been sent to the pharmacy.",
  "channel": "sms"
}
```

#### Example Response:
```json
{
  "success": true,
  "channel": "sms",
  "provider": "mock_messaging",
  "message_id": "mock_msg_a1b2c3d4e5f6",
  "status": "mock_delivered",
  "error_category": null,
  "is_mock": true
}
```

---

### 2.2 Process Opt-Out / Compliance Request (`POST /messaging/opt-out`)
- **Authentication**: `Bearer <JWT>`
- **Keywords Recognized**: `STOP`, `UNSUBSCRIBE`, `CANCEL`, `END`, `QUIT`
- **Behavior**: Checks incoming keyword for carrier compliance without persisting message content.

#### Example Request:
```json
{
  "recipient": "+12025550143",
  "keyword": "STOP",
  "channel": "sms"
}
```

#### Example Response:
```json
{
  "success": true,
  "opted_out": true,
  "keyword_matched": true,
  "channel": "sms",
  "status": "opted_out"
}
```

---

## 3. Security & PHI Protection Controls

1. **Zero Message Body Persistence**: Outbound message contents are processed entirely in-memory and are never stored in `/tmp`, log files, or databases.
2. **Sanitized Application Logging**: Application logs record only structured delivery metadata (`channel`, `provider`, `message_id`, `success`). Phone numbers and message bodies are strictly excluded from log statements.
3. **Safe Offline Fallback**: In the absence of cloud provider credentials, the system automatically uses `MockMessagingService` without throwing startup exceptions or making network sockets.
4. **Clinical Boundary**: The messaging service functions purely as a transport layer. Autonomous clinical diagnosis, prescription alterations, and emergency decisions are strictly prohibited from originating within the messaging layer.
