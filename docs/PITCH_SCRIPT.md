# Rebound: 5-Minute Pitch Script & Storyboard
### Submission for Track 3: AI Revenue Recovery — Razorpay AI Buildathon

**Speaker Timing**: Total duration 5:00 (300 seconds)  
**Tone**: Technical, institutional, measured, zero buzzwords. Speak like a principal payments engineer presenting to an executive risk committee.

---

### Minute 0:00 – 0:45: The Problem & The Non-Negotiable Boundary
**Visual**: Screen recording opens directly on the Rebound Operations Console. Metrics strip visible: ₹327,463 recovered across 55 batch payments.
**Audio**:
> "Most failed payment recovery tools make one of two mistakes. Either they rely on naive blind retry scripts that blast card networks, burning gateway fees and churning customers—or they hand the steering wheel over to an LLM that invents arbitrary actions and calls financial APIs directly.
>
> In financial infrastructure, you cannot let an AI model touch money.
>
> That is why we built **Rebound**. Rebound is an autonomous revenue recovery agent designed exclusively for failed recurring subscription payments. Its architectural prime directive is simple: AI does diagnosis and expected-value ranking across a fixed playbook, while a completely deterministic, zero-AI rules engine—**The Sentinel**—is the only component that ever authorizes capital movement."

---

### Minute 0:45 – 1:45: The 8-Stage Pipeline & The Decision Card
**Visual**: Click into `pay_rec_dt_003` (₹14,999 Enterprise debit) to display the **Recovery Decision Card**.
**Audio**:
> "Let's inspect how this works under the hood through the Recovery Decision Card—the atomic governance unit of Rebound.
>
> When an auto-debit fails, Stage 1 captures the raw telemetry: the bank decline code, the switch latency, customer tier, and retry history.
>
> In Stage 2, our AI Diagnosis Engine parses the error signals. Here, it diagnoses a transient **Bank Downtime** with 94% confidence—specifically an ICICI CBS maintenance outage, not customer insolvency.
>
> In Stage 3, our Playbook Ranking Engine evaluates our fixed 5-action playbook: Immediate Smart Retry, Scheduled Retry, Customer Dunning, Alternate Rail, or Card Token Renewal. Each strategy is scored by Expected Value in Rupees: Probability of Success times the Amount minus execution cost.
>
> The AI ranks 'Immediate Smart Retry' #1 with an expected value of ₹13,196.
>
> But look at Stage 4: **The Sentinel vetoes the AI's top choice.** Why? Because the customer was already attempted 2 hours ago, violating our mandatory 4-hour cooldown policy: `POLICY_COOLDOWN_ACTIVE`.
>
> No LLM was asked for permission. The deterministic rules engine stepped in, blocked the money movement, and safely routed execution to the next viable strategy."

---

### Minute 1:45 – 2:45: Measured Batch Uplift vs Naive Baseline
**Visual**: Switch to Batch Console and show side-by-side comparison tables with Naive Blind Retry.
**Audio**:
> "Track 3 demands measured recovery across a batch, not cherry-picked anecdotes. We benchmarked Rebound over a calibrated 55-record dataset spanning all 5 core failure modes: insufficient funds, expired cards, issuer mandate caps, transient downtime, and risk blocks.
>
> Compared against the industry-standard **Naive Blind-Retry Baseline**:
> - Rebound recovered **₹327,463** across 41 payments, vs the baseline's **₹111,290** across 11 payments.
> - After accounting for gateway fees and communications, Rebound delivered **+₹221,701 in Net Uplift—a 210% increase** in recovered cash.
> - Our recovery precision is **35.04% vs 7.64%**—delivering over 4.5 times more recovered revenue per attempt while eliminating 48 futile retry charges.
>
> Notice also our risk blocks: 12 fraudulent cards were flagged. The naive baseline retried them all, incurring ₹1,800 in acquirer chargeback fines. Rebound's Sentinel vetoed 100% of them at zero penalty."

---

### Minute 2:45 – 3:30: Auditability & Honest Counterfactual EV
**Visual**: Switch to Audit Trail tab. Filter by `SENTINEL_GATE` and expand JSON payloads. Highlight the Counterfactual EV section on the Decision Card.
**Audio**:
> "Governance requires complete observability. Rebound logs an immutable, timestamped audit entry for every single diagnostic inference, candidate scored, policy gate check, and gateway settlement. A compliance officer can trace any Rupee from the bank ledger back to the exact code constraint that authorized it.
>
> Furthermore, notice our counterfactual modeling: all unexecuted alternative paths are strictly labeled as 'expected value of paths not taken.' We never deceptively claim unexercised model predictions as realized recovered revenue. Evaluability and intellectual honesty are built into the data schema."

---

### Minute 3:30 – 4:45: THE UNANNOUNCED CLOSING REVEAL — Sentinel Reusability
**Visual**: Click on the 'Sentinel Gate Demo' tab. The UI reveals the Autonomous AI Buyer Agent Procurement Console.
**Audio**:
> "Now, for the closing beat—something we haven't foreshadowed anywhere in this presentation.
>
> If you look closely at the architecture of the Sentinel, you'll notice something unusual: its input schema doesn't say 'payment recovery.' It accepts an action-agnostic request: a subject, an action type, an amount, permissions, and context.
>
> To prove the architectural integrity of our AI/deterministic split, watch this:
>
> Here we have an **Autonomous AI Buyer Agent** attempting to procure cloud compute and SaaS licenses from a merchant catalog.
>
> Agent Apollo—a junior DevOps agent with a ₹25,000 monthly budget—is attempting to purchase a dedicated H100 GPU cluster for ₹48,000.
>
> We hit 'Evaluate'.
>
> Instantly: **BLOCKED.** Policy code: `POLICY_BUDGET_EXCEEDED` and `POLICY_PERMISSION_DENIED`.
>
> Next, Agent Titan—an authorized platform agent with a ₹150,000 budget and high-value compute permissions—requests the same purchase.
>
> We hit 'Evaluate'.
>
> Instantly: **APPROVED.** Policy code: `SENTINEL_OK`.
>
> Here is the reveal: **We never built a second safety system.**
>
> This is literally the exact same Sentinel module, running the exact same pure-rules Python code, gating money movement for an autonomous buyer agent without a single line of modification.
>
> Whether it's an AI agent attempting to recover subscription revenue or an AI agent attempting to spend company money, the rule of financial AI is universal:
> **Models may recommend. Only deterministic policy may execute.**"

---

### Minute 4:45 – 5:00: Conclusion & Submission Wrap
**Visual**: Return to Executive Metrics Header.
**Audio**:
> "Rebound proves that revenue recovery does not require black-box risk. By pairing deep AI diagnosis with an unbypassable deterministic Sentinel, we recover 210% more revenue with mathematical safety.
>
> Thank you."
