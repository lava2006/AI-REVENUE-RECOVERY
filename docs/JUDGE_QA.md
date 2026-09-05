# Rebound — FAQ (Frequently Asked Questions)
### Context: Track 3 — AI Revenue Recovery (Razorpay AI Buildathon)

This document contains written, structured answers to the five most critical questions asked about Rebound's architecture, scope, safety, and metrics.

---

### Question 1: "Why AI, why not rules?"

**Rehearsed Answer:**
"Rule trees break down in subscription recovery because decline telemetry is overloaded, noisy, and unstandardized across 100+ issuing banks. 

For instance, when an issuer returns `Decline 05: Do Not Honor` or `Decline 57: Transaction Not Permitted`, a static rule has no idea whether the problem is an RBI recurring e-mandate limit violation, an international transaction switch disabled by the user, or a temporary switch malfunction. A naive rule tree either blindly retries (burning decline fees) or immediately drops the customer.

AI excels at reading the multi-dimensional signal—combining the raw gateway switch string, customer tenure, past failed retries, and customer tier—to diagnose the root cause with a calibrated confidence score. It then ranks our fixed 5-action playbook by calculating Expected Value:
$$\text{EV} = (P_{\text{success}} \times \text{Amount}) - \text{Action Cost}$$

Crucially, **AI only selects and ranks—it is strictly prohibited from inventing novel actions or touching money directly.** Every top-ranked strategy must still clear our standalone deterministic gate: The Sentinel."

---

### Question 2: "Why not rules for the Sentinel too?"

**Rehearsed Answer:**
"The Sentinel **already IS 100% rules!** That is the entire architectural foundation of Rebound.

We deliberately do NOT put an LLM inside the Sentinel. There is zero prompt engineering, zero temperature, and zero model inference inside the governance gate. It is a standalone, deterministic Python policy engine that enforces hard mathematical constraints:
1. **Expected Value Cutoff**: Any action with non-positive EV is vetoed (`POLICY_EV_NEGATIVE`).
2. **Amount Bounds**: Minimum ₹1.00 and configurable ceilings (`POLICY_AMOUNT_EXCEEDS_LIMIT`).
3. **Retry Velocity Limits**: Hard stop at 3 attempts (`POLICY_MAX_RETRIES_EXCEEDED`).
4. **Mandatory Cooldowns**: Enforces 4 to 24-hour pauses between retry attempts (`POLICY_COOLDOWN_ACTIVE`).
5. **Dunning Throttling**: Limits customer notification frequency to prevent regulatory harassment (`POLICY_ESCALATION_THROTTLED`).
6. **Risk Shield**: Hard block on suspected stolen cards (`POLICY_RISK_THRESHOLD_EXCEEDED`).

By keeping the Sentinel completely free of AI, we guarantee that an LLM hallucination can never cause an unauthorized financial action."

---

### Question 3: "How do you measure improvement?"

**Rehearsed Answer:**
"We measure improvement against an exact, implemented baseline: the **Naive Blind-Retry Baseline**, which represents standard industry merchant behavior (blindly retrying failed cards up to 3 times without diagnosis or rail switching).

Across our calibrated 55-record benchmark dataset:
- **Total Revenue Recovered**: Rebound recovered **₹327,463.00** across 41 payments, compared to the baseline's **₹111,290.00** across 11 payments.
- **Net Uplift**: After deducting all gateway attempt fees, dunning costs, and chargeback penalties, Rebound delivered a **+₹221,701.50 Net Uplift (+210.1% increase)** over blind retry.
- **Recovery Precision**: Rebound achieved **35.04% precision** (recoveries per attempt) vs the baseline's **7.64%**—a **4.6x efficiency multiple**.
- **Fraud Penalty Avoidance**: The baseline incurred ₹1,800+ in acquirer chargeback penalties by repeatedly trying stolen cards, whereas Rebound's Sentinel vetoed 100% of risk-flagged accounts.

Every number on our dashboard is traceable to real pipeline runs across labeled ground-truth records."

---

### Question 4: "What happens when the model is wrong?"

**Rehearsed Answer:**
"Rebound provides two independent safety nets when the AI makes an inaccurate diagnosis or ranks a suboptimal action:

1. **Safety Net 1: The Deterministic Sentinel Veto**
   Even if the AI model hallucinates high confidence and ranks `RETRY_NOW` as its #1 strategy, the Sentinel inspects the customer's state. If the customer is within a mandatory 4-hour cooldown or has already been attempted 3 times, the Sentinel vetoes the action with an immutable policy code (e.g. `POLICY_COOLDOWN_ACTIVE`) and blocks money movement.

2. **Safety Net 2: The Graceful Fallback & Stopping Loop**
   If an approved action fails at the Razorpay gateway, Rebound does not loop blindly. It records the gateway decline, updates the customer's failure state, and steps down to the next-ranked strategy in the playbook. If all playbook candidates are exhausted or blocked by policy, Rebound executes an explicit, graceful termination (`STOP_POLICY_TERMINATION`), halting execution to protect customer goodwill and merchant capital."

---

### Question 5: "Why only subscription failures, not the other loss types the track mentions?"

**Rehearsed Answer:**
"**Depth over coverage.** 

The hackathon track description mentions checkout abandonment and B2B receivables as valid directions. However, attempting to build all three within buildathon constraints inevitably results in shallow prompt wrappers with superficial toy logic.

Subscription payment recovery is where the problem is technically richest and highest-stakes:
- It involves recurring mandates, token expiration lifecycles, RBI AFA limits, and payroll replenishment cycles.
- It requires an authentic AI/deterministic boundary because recurring debits touch cardholder accounts automatically without active human cart checkouts.

By focusing with ruthless discipline exclusively on recurring subscription failures, we built a complete, auditable 8-stage pipeline, a verified 55-record benchmark, and an action-agnostic Sentinel that can even gate autonomous buyer agents."
