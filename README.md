# ⚡ VoltEdge AI — Industrial EV Supply Chain & Asset Intelligence Platform

> Powering India's industrial EV transition with intelligent operations.

VoltEdge AI is a full-stack decision-support platform for fleet operators and supply-chain
managers running **electric and diesel commercial vehicles across India**. It unifies four
operational pillars — battery health, fleet electrification, supply-chain risk, and carbon
accounting — into a single command center, with a Gemini-powered AI copilot layered on top.

Built for the **Economic Times EV Supply Chain** challenge.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [Environment Variables](#environment-variables)
7. [API Reference](#api-reference)
8. [The Four Modules](#the-four-modules)
9. [Data Model](#data-model)
10. [Troubleshooting](#troubleshooting)

---

## Key Features

- **🔋 Battery APM (Asset Performance Management)** — State-of-Health (SoH) tracking,
  degradation forecasting, Remaining-Useful-Life (RUL) prediction, thermal-event monitoring,
  and predictive maintenance scheduling across the EV fleet.
- **🚚 Fleet Electrification Readiness** — An Electrification Readiness Index (ERI) that scores
  each diesel vehicle for EV conversion, with diesel-vs-EV Total Cost of Ownership (TCO)
  comparison, break-even analysis, and OEM procurement recommendations.
- **🛡️ Supply Chain Risk & Traceability** — Multi-tier (mining → refining → cathode/anode →
  cells → pack assembly) supplier mapping, geopolitical exposure scoring, China-dependency vs
  India-localization tracking, and live risk alerts.
- **🌱 Net Zero Carbon Tracker** — Scope 1/2/3 emissions accounting, per-route carbon intensity,
  counterfactual "diesel-if-not-electrified" savings, and AI-prioritized next-best-action
  recommendations for maximum decarbonization impact.
- **🤖 VoltEdge AI Copilot** — A context-aware chat assistant (Google Gemini) that answers
  questions using live module data, with a graceful rule-based fallback when no API key is set.

---

## Architecture

```
┌──────────────────────────────┐         ┌───────────────────────────────┐
│      Next.js 16 Frontend      │         │        FastAPI Backend        │
│         (port 3000)           │  HTTP   │          (port 8000)          │
│                               │ ──────► │                               │
│  • Command Center (dashboard) │  JSON   │  Routers:                     │
│  • Battery APM page           │ ◄────── │   /api/battery                │
│  • Fleet Readiness page       │         │   /api/fleet                  │
│  • Supply Chain page          │         │   /api/supply-chain           │
│  • Net Zero page              │         │   /api/carbon                 │
│  • AI Copilot (floating)      │         │   /api/ai   ──► Gemini Agent  │
│                               │         │                               │
│  Charts: Recharts             │         │  In-memory seeded data store  │
│  Icons:  lucide-react         │         │  (deterministic, seed=42)     │
└──────────────────────────────┘         └───────────────────────────────┘
```

The backend seeds a **deterministic synthetic dataset** at startup (no external database
required) — roughly 50 vehicles (20 EV + 30 diesel) across 8 Indian cities, and 15 suppliers
spanning 5 supply-chain tiers. The frontend is a pure client that reads from the API.

---

## Tech Stack

| Layer        | Technology                                              |
|--------------|---------------------------------------------------------|
| Frontend     | Next.js 16 (App Router), React 19, CSS Modules          |
| Charts       | Recharts 3                                              |
| Icons        | lucide-react                                            |
| Backend      | FastAPI 0.115, Uvicorn                                  |
| Validation   | Pydantic 2                                              |
| AI           | Google Generative AI (`gemini-2.0-flash`)               |
| Config       | python-dotenv                                           |
| Language     | JavaScript (frontend), Python 3.10+ (backend)           |

---

## Project Structure

```
Economics_times_EV_supplychain/
├── backend/
│   ├── main.py                 # FastAPI app, CORS, dashboard endpoint
│   ├── requirements.txt
│   ├── routers/
│   │   ├── battery.py          # /api/battery/*
│   │   ├── fleet.py            # /api/fleet/*
│   │   ├── supply_chain.py     # /api/supply-chain/*
│   │   ├── carbon.py           # /api/carbon/*
│   │   └── ai.py               # /api/ai/chat
│   ├── services/
│   │   └── gemini_agent.py     # Gemini wrapper + rule-based fallback
│   └── data/
│       └── seed_data.py        # Deterministic synthetic data generator
└── frontend/
    ├── package.json
    └── src/
        ├── app/
        │   ├── page.js          # Command Center (dashboard)
        │   ├── battery-apm/      # Battery APM module page
        │   ├── fleet-readiness/  # Fleet Readiness module page
        │   ├── supply-chain/     # Supply Chain module page
        │   ├── net-zero/         # Net Zero module page
        │   └── layout.js
        ├── components/
        │   ├── layout/  (Sidebar, TopBar, Layout)
        │   ├── dashboard/ (KPICard)
        │   └── ai/ (AICopilot)
        └── lib/
            └── api.js           # Typed API client
```

---

## Getting Started

### Prerequisites

- **Node.js 18+** (Next.js 16 requires a modern Node)
- **Python 3.10+**
- A **Google Gemini API key** (optional — the copilot falls back to rule-based answers without it)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: enable the Gemini copilot
export GEMINI_API_KEY="your_key_here"   # Windows: set GEMINI_API_KEY=...

uvicorn main:app --reload --port 8000
```

The API is now live at **http://localhost:8000**. Interactive docs (Swagger UI) are at
**http://localhost:8000/docs**.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** to view the Command Center.

> The frontend expects the backend at `http://localhost:8000/api` (configured in
> `frontend/src/lib/api.js`). Start the backend first.

---

## Environment Variables

| Variable         | Where     | Required | Purpose                                                |
|------------------|-----------|----------|--------------------------------------------------------|
| `GEMINI_API_KEY` | backend   | No       | Enables the live Gemini copilot                        |
| `GOOGLE_API_KEY` | backend   | No       | Alternate name accepted for the Gemini key             |

When neither key is present, the copilot logs a warning and serves intelligent rule-based
responses, so the demo works fully offline.

---

## API Reference

Base URL: `http://localhost:8000`

### Common

| Method | Endpoint          | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/`               | Service metadata and module list         |
| GET    | `/api/dashboard`  | Cross-module KPI roll-up (Command Center)|

### Battery APM — `/api/battery`

| Method | Endpoint                         | Description                          |
|--------|----------------------------------|--------------------------------------|
| GET    | `/fleet-health`                  | SoH overview + per-vehicle health    |
| GET    | `/vehicle/{vehicle_id}`          | Full battery detail for one vehicle  |
| GET    | `/degradation/{vehicle_id}`      | Degradation curve / RUL forecast     |
| GET    | `/alerts`                        | Active battery alerts                |
| GET    | `/maintenance-schedule`          | Predictive maintenance schedule      |

### Fleet Readiness — `/api/fleet`

| Method | Endpoint                          | Description                         |
|--------|-----------------------------------|-------------------------------------|
| GET    | `/readiness-scores`               | ERI scores for all diesel vehicles  |
| GET    | `/vehicle/{vehicle_id}/tco`       | Diesel-vs-EV TCO for one vehicle    |
| GET    | `/procurement-recommendations`    | Recommended EV models to procure    |
| GET    | `/transition-roadmap`             | Phased electrification roadmap       |

### Supply Chain — `/api/supply-chain`

| Method | Endpoint                        | Description                            |
|--------|---------------------------------|----------------------------------------|
| GET    | `/overview`                     | Risk summary + tier/risk breakdown     |
| GET    | `/suppliers`                    | All suppliers with risk scores         |
| GET    | `/map`                          | Geo-coordinates for map rendering      |
| GET    | `/risk-alerts`                  | Active supply-chain risk alerts        |
| GET    | `/supplier/{supplier_id}`       | Single-supplier detail                 |
| GET    | `/traceability/{material}`      | Material traceability chain            |

### Net Zero — `/api/carbon`

| Method | Endpoint            | Description                                 |
|--------|---------------------|---------------------------------------------|
| GET    | `/summary`          | Overall carbon summary                      |
| GET    | `/emissions`        | Monthly emissions + counterfactual          |
| GET    | `/scope-breakdown`  | Scope 1 / 2 / 3 totals                       |
| GET    | `/route-intensity`  | Per-route carbon intensity                  |
| GET    | `/next-best-action` | AI-prioritized electrification actions      |
| GET    | `/progress`         | Electrification progress vs target          |

### AI Copilot — `/api/ai`

| Method | Endpoint  | Body                                  | Description                       |
|--------|-----------|---------------------------------------|-----------------------------------|
| POST   | `/chat`   | `{ "message": str, "module": str? }`  | Context-aware AI response         |

`module` is one of `battery`, `fleet`, `supply-chain`, `carbon` — it scopes the live data
context passed to the model.

---

## The Four Modules

**Battery APM** treats each battery pack as a managed asset. It models calendar aging,
cycle aging, fast-charge penalty, and India-climate thermal stress to produce SoH, degradation
rate, and RUL, then flags critical (<75% SoH) and warning (75–85%) vehicles.

**Fleet Readiness** scores every diesel vehicle on an Electrification Readiness Index that
blends route suitability, daily distance, duty cycle, and age, then attaches a diesel-vs-EV
TCO comparison (with FAME-II subsidy context), a recommended EV/OEM, and a transition priority.

**Supply Chain Risk** maps the battery raw-material supply chain across five tiers and tracks
geopolitical exposure — notably China dependency vs India localization — plus quality, ESG,
and financial-health signals, surfacing critical/high-risk suppliers as alerts.

**Net Zero Tracker** accounts for Scope 1 (diesel combustion), Scope 2 (grid electricity via
CEA/state grid factors), and Scope 3 emissions, computes carbon saved versus an all-diesel
counterfactual, and recommends the next electrification move for maximum abatement.

---

## Data Model

All data is **synthetic and deterministic** (`random.seed(42)` in `seed_data.py`), so every run
produces identical numbers — ideal for demos and screenshots. The dataset is India-specific:

- **Cities:** Mumbai, Delhi, Pune, Chennai, Bangalore, Hyderabad, Kolkata, Ahmedabad
- **EV OEMs:** Tata Motors, Mahindra Electric, Ashok Leyland, BYD India, Euler Motors
- **Regulatory context:** FAME-II subsidies, CEA grid emission factors, BRSR compliance
- **Materials tracked:** Lithium, Cobalt, Nickel, Graphite

No external database is required; the store lives in memory and is initialized on app startup.

---

## Troubleshooting

| Symptom                                    | Fix                                                            |
|--------------------------------------------|---------------------------------------------------------------|
| Frontend shows "Error" / blank KPIs        | Backend isn't running — start Uvicorn on port 8000 first.     |
| CORS errors in browser console             | Access the frontend via `localhost:3000` / `127.0.0.1:3000`.  |
| Copilot gives generic answers              | `GEMINI_API_KEY` isn't set — export it and restart the backend.|
| `npm run dev` fails                        | Ensure Node 18+; delete `node_modules` and reinstall.         |
| Port already in use                        | Change `--port` (backend) or run `next dev -p 3001` (frontend).|

---

## License

Provided for the Economic Times EV Supply Chain challenge. See repository for terms.
