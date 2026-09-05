
# Rebound — AI Revenue Recovery Agent
### Razorpay AI Buildathon — Track 3: AI Revenue Recovery

> **"Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."**  
> — Track 3 Bar, Razorpay AI Buildathon

---

## Executive Summary & Prime Directive

**Rebound** is an institutional revenue recovery system built exclusively for **failed recurring subscription payments**. 

Its core architectural innovation is a strict **AI / Deterministic Boundary**:
- **AI does Selection, not Invention**: An AI diagnosis engine identifies the root cause of payment failure from raw gateway decline signals, and scores a **fixed 5-action playbook** by calculating Expected Value in Rupees:
  $$\text{Expected Value (₹)} = (P_{\text{success}} \times \text{Amount}) - \text{Execution Cost}$$
- **The Sentinel is the Sole Gate Touching Money**: A standalone, zero-AI deterministic rules engine enforces hard mathematical constraints (retry limits, cooldown periods, amount bounds, dunning velocity, and fraud risk thresholds). An LLM is never permitted to touch money, invent actions, or call payment APIs directly.

---

## Key Benchmark Results (55-Record Calibrated Dataset)

Across our 55-record benchmark covering all 5 recurring failure classes:

| Metric | Rebound (AI + Sentinel) | Naive Blind Retry Baseline | Performance Uplift |
|---|---|---|---|
| **Total Revenue Recovered** | **₹3,27,463.00** | ₹1,11,290.00 | **+₹2,16,173.00** |
| **Successful Recoveries** | **41 payments** | 11 payments | **+30 subscriptions preserved** |
| **Net Financial Impact** | **₹3,27,231.50** | ₹1,05,530.00 | **+₹2,21,701.50 Net (+210.1%)** |
| **Recovery Precision** | **35.04%** | 7.64% | **4.6x Higher Recovery Efficiency** |
| **Futile Retries Prevented** | **48 attempts** | 0 (blindly burned) | Eliminates customer friction |
| **Fraud & Chargeback Penalties** | **₹0.00 (100% blocked)** | ₹1,800.00 (charged) | Complete capital preservation |
| **Diagnosis Accuracy** | **100.0% (55/55)** | N/A (no diagnosis) | Ground-truth validated |

---

## System Architecture: The 8-Stage Pipeline

```
                     ┌─────────────────────────────────────────────────┐
                     │ 1. DETECT                                       │
                     │ Ingest decline code, latency, tenure & history  │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                     ┌─────────────────────────────────────────────────┐
                     │ 2. DIAGNOSE [AI Engine]                         │
                     │ Classify: Bank Downtime | Insufficient Funds | │
                     │ Card Expired | Issuer Decline | Risk Block      │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                     ┌─────────────────────────────────────────────────┐
                     │ 3. RANK [AI Engine]                             │
                     │ Score 5-action playbook with Expected Value (₹) │
                     │ EV = (P_success * Amount) - Action Cost         │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                     ┌─────────────────────────────────────────────────┐
  ┌──────────────────┤ 4. GATE [The Sentinel — Deterministic Gate]     │
  │                  │ Evaluates EV cutoff, Cooldown, Retries, Bounds  │
  │                  └───────────────────────┬─────────────────────────┘
  │ Vetoed / Blocked                         │ Approved (SENTINEL_OK)
  ▼                                          ▼
┌──────────────────┐ ┌─────────────────────────────────────────────────┐
│ 6. FALLBACK      │ │ 5. EXECUTE                                      │
│ Step down to     │ │ Razorpay Test-Mode API / Structured Test Stub   │
│ next strategy    │ └───────────────────────┬─────────────────────────┘
│ OR stop cleanly  │                         ▼
└────────┬─────────┘ ┌─────────────────────────────────────────────────┐
         │           │ 6. OBSERVE                                      │
         │           │ Success: Capture ₹ and Stop                     │
         │           │ Failure: Route to Fallback loop                 │
         │           └───────────────────────┬─────────────────────────┘
         │                                   ▼
         │           ┌─────────────────────────────────────────────────┐
         └──────────►│ 7. AUDIT TRAIL                                  │
                     │ Immutable, timestamped, structured JSON entries │
                     └───────────────────────┬─────────────────────────┘
                                             ▼
                     ┌─────────────────────────────────────────────────┐
                     │ 8. REPORT & HONEST COUNTERFACTUAL EV            │
                     │ Net ₹ vs Baseline + Expected Value Paths Unused │
                     └─────────────────────────────────────────────────┘
```

---

## The Standalone Sentinel & The Closing Demo Beat

A central architectural mandate of Rebound is that **The Sentinel is a standalone, action-agnostic policy evaluator**, not an inline function bolted onto a recovery script:
- It accepts a generic `PolicyRequest(subject_id, action_type, amount, permissions, context)`.
- It returns a structured `SentinelDecision(approved, policy_code, reason, expected_value, constraints_evaluated)`.
- **Zero LLMs inside the gate**: 100% deterministic rules.

### The Unannounced Reveal Beat
To prove that The Sentinel is a genuinely reusable safety system, the closing demo points **the exact same unmodified module** at an **Autonomous AI Buyer Agent** attempting to procure cloud compute and SaaS seats against monthly budget caps and permission scopes:
- Over-budget orders or requests lacking permission tokens are instantly vetoed (`POLICY_BUDGET_EXCEEDED`, `POLICY_PERMISSION_DENIED`).
- Compliant orders are approved (`SENTINEL_OK`).
- **Conclusion**: A single governance engine protects both revenue inflow and autonomous agent outflow.

---

## Project Structure

```
AI REVENUE RECOVERY/
├── backend/
│   ├── api/
│   │   └── main.py              # FastAPI REST endpoints & batch manager
│   ├── core/
│   │   ├── sentinel.py          # The Sentinel (pure deterministic rules engine)
│   │   ├── dataset.py           # 55-record calibrated synthetic dataset
│   │   ├── diagnose.py          # Stage 2 AI Diagnosis Engine
│   │   ├── rank.py              # Stage 3 AI Playbook Ranking Engine (EV)
│   │   ├── executor.py          # Stage 5 Razorpay Test-Mode Executor & Stub
│   │   ├── pipeline.py          # 8-stage pipeline coordinator & fallback loop
│   │   ├── baseline.py          # Naive Blind-Retry Baseline runner
│   │   └── buyer_agent_demo.py  # Standalone Buyer Agent demonstration module
│   ├── models/
│   │   └── schemas.py           # Pydantic schemas for all entities
│   └── tests/
│       ├── test_sentinel.py     # Sentinel rule boundary & dual-use unit tests
│       └── test_pipeline.py     # Full integration & pre-submission batch eval
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx               # Telemetry header & mode tabs
│   │   │   ├── MetricsHeader.tsx        # Executive Metrics Strip
│   │   │   ├── RecoveryDecisionCard.tsx # High-polish Recovery Decision Card
│   │   │   ├── PaymentsTable.tsx        # Batch record grid with filters
│   │   │   ├── AuditTrailViewer.tsx     # Structured audit trail inspector
│   │   │   ├── BuyerAgentDemo.tsx       # The Closing Reveal Beat
│   │   │   ├── EvalReportView.tsx       # Pre-submission scorecard & Judge QA
│   │   │   └── ArchitectureModal.tsx    # Visual pipeline diagram modal
│   │   ├── App.tsx                      # Main React application
│   │   └── types.ts                     # TypeScript data interfaces
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md          # In-depth architectural blueprint
│   ├── JUDGE_QA.md              # Rehearsed answers to the 5 core judge questions
│   └── PITCH_SCRIPT.md          # 5-minute timed video script & storyboard
└── README.md
```

---

## Quickstart & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup & Test Suite Execution
```bash
# In project root:
# Run Sentinel isolated unit tests (all 6 constraints):
python -m pytest backend/tests/test_sentinel.py -v

# Run the complete 55-record benchmark evaluation:
python -m pytest backend/tests/test_pipeline.py -v

# Launch the FastAPI backend server:
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```
FastAPI interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Launch (React Operations Console)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` (or `http://localhost:5173`) in your browser to inspect the full operations console.

---

## Razorpay Test-Mode API Integration

Rebound supports live Razorpay test-mode credentials. Set the following environment variables in `.env`:
```env
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
```
When credentials are not provided, Rebound operates in a **transparent, structured Test Stub mode** clearly labeled in the audit trail as `execution_backend: "razorpay_test_stub"`. It produces realistic responses without silent mocking or fabricating results.

---

## Pre-Submission Evaluation Verification (Sections 8.A – 8.F)

The automated test suite in `backend/tests/test_pipeline.py` asserts:
- **8.A (Correctness)**: ₹ recovered > baseline, net uplift > 0, precision > baseline, 100% diagnosis accuracy on labeled ground truth.
- **8.B (Sentinel Integrity)**: 74 policy blocks recorded across batch, risk blocks vetoed, pure rules with 0 LLM calls.
- **8.C (Audit Completeness)**: Full 8-stage state tracking verifiable on every record.
- **8.D (Failure Handling)**: 17 graceful multi-step fallback cases demonstrated and cleanly stopped.
- **8.E (Closing Demo Beat)**: Exact same Sentinel instance approves/blocks simulated buyer agent requests.
- **8.F (Judge QA)**: Complete written, rehearsed answers provided in `docs/JUDGE_QA.md`.
=======


