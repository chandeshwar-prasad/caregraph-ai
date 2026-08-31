# CareGraph AI — Render Production Deployment Guide

## 1. Executive Deployment Architecture

CareGraph AI deploys to **Render** as a modern, decoupled 3-tier cloud architecture:

```
+-------------------------------------------------------------+
|                      Render Cloud                           |
|                                                             |
|   +-----------------------------------------------------+   |
|   |   caregraph-ui (Next.js 14 Web Service)             |   |
|   |   URL: https://caregraph-ui.onrender.com            |   |
|   |   Port: 3000 (Node.js runtime / Container)          |   |
|   +--------------------------+--------------------------+   |
|                              | HTTPS API Requests           |
|                              v                              |
|   +-----------------------------------------------------+   |
|   |   caregraph-api (FastAPI Python ASGI Web Service)   |   |
|   |   URL: https://caregraph-api.onrender.com           |   |
|   |   Port: 8000 (Docker container)                     |   |
|   |   Healthcheck: /health                              |   |
|   +--------------------------+--------------------------+   |
|                              | SQLAlchemy (psycopg2)        |
|                              v                              |
|   +-----------------------------------------------------+   |
|   |   caregraph-db (Render Managed PostgreSQL 16)       |   |
|   |   Database: caregraph                               |   |
|   |   Extensions: pgvector (optional / self-healing)    |   |
|   +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

---

## 2. Deployment Method A: Render Blueprint (Recommended)

Render Blueprints (`render.yaml`) deploy all 3 services automatically with synchronized environment variables and database linkings.

### Steps:
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository: `chandeshwar-prasad/caregraph-ai`.
4. Select the `main` branch.
5. Render automatically parses `render.yaml` and provisions:
   - `caregraph-db` (PostgreSQL instance)
   - `caregraph-api` (FastAPI Docker Web Service)
   - `caregraph-ui` (Next.js Node Web Service)
6. Under **Environment Variables**, provide your secret keys:
   - `GROQ_API_KEY`: Your Groq Cloud API key (leave blank to run in deterministic offline synthetic mode).
7. Click **Apply**.
8. Render will build and deploy all services.

---

## 3. Deployment Method B: Manual Service Provisioning

If preferred, services can be created individually via the Render UI:

### Step 1: Provision PostgreSQL Database
- **Name**: `caregraph-db`
- **Database**: `caregraph`
- **User**: `postgres`
- **Region**: Oregon (or your preferred region)
- **Plan**: Free or Starter
- Copy the **Internal Database URL** once provisioned.

### Step 2: Provision Backend API Web Service
- **Name**: `caregraph-api`
- **Environment**: Docker
- **Dockerfile Path**: `./Dockerfile.backend`
- **Region**: Same as database
- **Plan**: Free or Starter
- **Health Check Path**: `/health`
- **Environment Variables**:
  | Variable | Value | Description |
  | :--- | :--- | :--- |
  | `PORT` | `8000` | Backend listening port |
  | `ENVIRONMENT` | `production` | Production mode toggle |
  | `DATABASE_URL` | `<Internal Database URL>` | Linked from caregraph-db |
  | `SEED_DEMO_DATA` | `true` | Auto-seeds demo accounts and clinical records |
  | `JWT_SECRET` | `<Generate random 32+ hex chars>` | JWT signature key |
  | `JWT_ALGORITHM` | `HS256` | Token algorithm |
  | `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Session lifetime |
  | `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model name |
  | `GROQ_API_KEY` | `<your-groq-key>` | LLM inference key (optional for mock mode) |
  | `TELEMETRY_ENABLED` | `true` | Telemetry event recording |
  | `ALLOWED_ORIGINS` | `https://caregraph-ui.onrender.com,http://localhost:3000` | Production CORS origins |

### Step 3: Provision Frontend Web Service
- **Name**: `caregraph-ui`
- **Environment**: Node
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm run start`
- **Region**: Same as backend
- **Plan**: Free or Starter
- **Environment Variables**:
  | Variable | Value | Description |
  | :--- | :--- | :--- |
  | `NODE_ENV` | `production` | Production Node runtime |
  | `NEXT_PUBLIC_API_BASE_URL` | `https://caregraph-api.onrender.com` | Production backend API endpoint |

---

## 4. Production Database Initialization & Schema

- **Automatic Table Creation**: On backend startup, `models.Base.metadata.create_all(bind=engine)` initializes all required relational tables:
  - `users`
  - `patients`
  - `appointments`
  - `medications`
  - `vitals`
  - `consents`
  - `medication_reminders`
- **Automatic Demo Seeding**: When `SEED_DEMO_DATA=true`, the system seeds default demonstration credentials:
  - Patient: `patient_demo` / `patient123`
  - Administrator: `admin_demo` / `admin123`
- **Resilience**: The database connector (`app/database.py`) automatically translates `postgres://` to `postgresql://` and configures `pool_pre_ping=True` to recycle idle cloud connections.

---

## 5. Post-Deployment Smoke Test Checklist

Once deployed, verify the following:

1. **Backend Health Check**:
   ```bash
   curl -f https://caregraph-api.onrender.com/health
   # Expected: {"status":"healthy","database":"connected","mode":"production"}
   ```
2. **Frontend Availability**:
   Navigate to `https://caregraph-ui.onrender.com/login` and verify UI renders cleanly.
3. **Patient Workflow Verification**:
   - Quick login with Patient preset (`patient_demo`).
   - Navigate to `/dashboard`, `/appointments`, `/vitals`, `/medications`, `/reminders`, `/consents`, `/chat`, `/voice`, `/vision`.
4. **Admin Workflow Verification**:
   - Quick login with Admin preset (`admin_demo`).
   - Navigate to `/admin/analytics` and verify all 4 tabs (Clinical Operations, Agent Telemetry, Cost Intelligence, Power BI Exports).
   - Navigate to `/admin/benchmarks` and verify the 56-scenario scorecard (100% Emergency Recall, 100% Injection Resistance, 0.0% Prohibited Claims).
   - Navigate to `/admin/messaging` and test outbound SMS / WhatsApp simulation.
5. **Zero-PHI & Security Confirmation**:
   - Confirm patient role is restricted from `/admin/*` routes.
   - Confirm zero PHI is leaked across analytics exports or browser consoles.
