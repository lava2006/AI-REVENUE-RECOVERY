# Rebound: Technical Architecture Document
### Razorpay AI Buildathon — Track 3: AI Revenue Recovery

---

## 1. System Philosophy & The AI/Deterministic Split

Modern payment systems handle mission-critical financial flows. When subscription charges fail, merchants typically face a painful trade-off:
1. **The Naive Status Quo**: Blindly retrying failed cards every 24 hours, burning gateway fees, triggering customer churn, and racking up chargeback fines on stolen cards.
2. **The Fragile "Agentic" Anti-Pattern**: Letting an unconstrained LLM generate arbitrary recovery steps, hallucinate refund amounts, or call payment APIs directly.

**Rebound** eliminates this dichotomy through a strict, unbreachable boundary:
- **AI is confined to Selection, not Invention**: AI reads multi-dimensional failure telemetry, diagnoses the true underlying root cause, and ranks a **fixed, pre-approved 5-action recovery playbook** using Expected Value ($EV = P \times \text{Amount} - \text{Cost}$).
- **The Sentinel is the Sole Arbiter of Capital Movement**: A pure Python, zero-LLM deterministic rules engine enforces hard mathematical constraints (retry limits, cooldown windows, amount bounds, dunning velocity, and fraud risk thresholds). No money is ever touched unless The Sentinel issues an immutable `SENTINEL_OK` verdict.

---

## 2. The 8-Stage Revenue Recovery Pipeline

```
  [Payment Fails]
         │
         ▼
 1. DETECT             Ingests decline code, switch telemetry, customer tenure, retry history
         │
         ▼
 2. DIAGNOSE [AI]      Classifies failure cause + confidence (Bank Downtime, Insufficient Funds,
         │             Card Expired, Issuer Decline, Risk Block)
         ▼
 3. RANK [AI]          Calculates Expected Value ₹ for each action in the fixed 5-action playbook:
         │             EV = (P_success * Amount) - Marginal Execution Cost
         ▼
 4. GATE [Sentinel]    DETERMINISTIC ZERO-AI RULES GATE: Evaluates Bounds, Cooldown,
         │             Max Retries, Velocity, Risk Score, and Positive EV.
         ├── [Rejected] ──► Fallback Step / Stop per Policy
         ▼ [Approved]
 5. EXECUTE            Calls Razorpay Test-Mode APIs (or transparently labeled Test Stub)
         │
         ▼
 6. OBSERVE & FALLBACK Success ──► Capture ₹ + Stop
         │             Failure ──► Step down to next viable candidate in playbook
         ▼
 7. AUDIT TRAIL        Structured, timestamped, immutable JSON log of every stage and state transition
         │
         ▼
 8. REPORT & EV        Calculates ₹ recovered vs Naive Baseline + Honest Counterfactual EV View
```

---

## 3. The Standalone Sentinel: Generic Action-Agnostic Design

A critical requirement of Rebound is that **The Sentinel is built as an independent, generic policy engine** from the ground up, rather than inline validation logic tangled inside the recovery workflow.

### Generic Policy Request Schema
```python
class PolicyRequest(BaseModel):
    subject_id: str                   # e.g. "pay_rec_001" or "buyer_agent_apollo"
    subject_type: str                 # "payment_recovery" or "buyer_agent_purchase"
    action_type: str                  # "RETRY_NOW", "PURCHASE_GPU_CLUSTER"
    amount: float                     # Transaction or order amount in INR
    current_attempt_count: int        # Prior attempts
    last_attempt_timestamp: Optional[str]
    escalation_count: int             # Dunning or alert velocity
    expected_value: float             # Projected EV
    confidence: float                 # Diagnostic confidence
    granted_permissions: List[str]    # Security scopes
    context: Dict[str, Any]           # Custom thresholds
```

### Deterministic Constraints Enforced
1. **Expected Value Positive Cutoff**: Rejects any action where $EV \le 0.0$ (`POLICY_EV_NEGATIVE`).
2. **Amount Boundaries**: Rejects transactions below ₹1.00 or above ceiling limits (`POLICY_AMOUNT_EXCEEDS_LIMIT`, `POLICY_AMOUNT_BELOW_MINIMUM`).
3. **Retry Velocity Limits**: Enforces a strict ceiling of 3 attempts (`POLICY_MAX_RETRIES_EXCEEDED`).
4. **Mandatory Cooldown Periods**: Prohibits repeated immediate attempts if elapsed time is less than the required cooldown window, e.g. 4 hours (`POLICY_COOLDOWN_ACTIVE`).
5. **Dunning Escalation Frequency**: Restricts customer alerts to a maximum of 2 notifications per cycle (`POLICY_ESCALATION_THROTTLED`).
6. **Risk Shield**: Intercepts transactions with an elevated risk score (> 0.70) to prevent chargeback penalties (`POLICY_RISK_THRESHOLD_EXCEEDED`).
7. **Permission Scopes & Budget Caps**: Validates cryptographic/RBAC permission tokens and monthly spending caps when gating autonomous agents (`POLICY_PERMISSION_DENIED`, `POLICY_BUDGET_EXCEEDED`).

---

## 4. The 5-Action Recovery Playbook & Marginal Costs

Rebound uses a fixed, battle-tested playbook tailored to recurring payment rails:

| Action Code | Description | Best Suited For | Marginal Cost (₹) |
|---|---|---|---|
| `RETRY_NOW` | Immediate smart retry on restored network | `BANK_DOWNTIME` | ₹2.50 |
| `RETRY_LATER` | Scheduled retry after 24–48h cooldown | `INSUFFICIENT_FUNDS` (Payday alignment) | ₹2.50 |
| `NOTIFY_CUSTOMER` | Multi-channel dunning alert with 1-click UPI link | `INSUFFICIENT_FUNDS`, `ISSUER_DECLINE` | ₹5.00 |
| `OFFER_ALTERNATE_PAYMENT_METHOD` | Send mandate switch link (UPI AutoPay / e-NACH) | `ISSUER_DECLINE` (RBI mandate limit) | ₹8.00 |
| `PROMPT_CARD_UPDATE` | RBI tokenization renewal session | `CARD_EXPIRED` | ₹6.00 |

---

## 5. Dual-Use Reusability Demonstration

Because The Sentinel was engineered to evaluate generic `PolicyRequest` payloads without hardcoding recovery-specific concepts, **it is reused 100% unmodified in the closing demo beat**:
- An **Autonomous AI Buyer Agent** attempts to purchase cloud infrastructure and SaaS licenses from a merchant catalog.
- The same Sentinel instance enforces monthly budget limits and permission scopes, instantly approving compliant requests and blocking over-budget or out-of-scope requests.
- **Architectural Takeaway**: A single, battle-hardened governance gate can protect an organization's money on both sides of the balance sheet—inflow (revenue recovery) and outflow (autonomous agent procurement).

---

## 6. Honest Counterfactual Modeling

In revenue recovery systems, it is easy to mislead stakeholders by framing unexercised strategy projections as "revenue that could have been made." 

Rebound strictly prohibits this:
- Every candidate scored by the AI ranking engine that is not executed is classified as an **"Expected Value of Paths Not Taken"**.
- Counterfactual cards clearly show the projected EV and success probability alongside their exact terminal status (`executed`, `gated_by_sentinel`, `rejected_by_gateway`, or `unreached_fallback`).
- Only actual settlement transactions captured by the Razorpay gateway are tallied as recovered revenue.
