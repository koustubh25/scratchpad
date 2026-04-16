# NRMA — Gemini CX Agent Architecture

## Client Context

**Client:** Insurance Australia Group (IAG) — largest general insurer in Australia and New Zealand.
**Brand:** NRMA Insurance — IAG's primary consumer brand.
**Mission:** "Make the world a safer place through every policy, customer conversation and digital experience."
**Current focus:** Major digital transformation — Adobe Experience Cloud partnership, AI, cloud, personalisation at scale.

## Problem Statement

Real UX and interaction complaints from NRMA customers — the problems this architecture directly solves:

| Pain point | What customers say | What this solves |
|---|---|---|
| Broken digital forms | "Website refused to go past a certain point then automatically submitted" | Conversational — no forms, no submission errors |
| App/website failures | "Unable to access website or app — system error, instructions to ring support" | Always-on agent, no system errors |
| No proactive notifications | "Missed one payment which they never let us know" | Agent proactively alerts on payment, renewal, claim updates |
| Can't reach a case manager | "No means on their website of writing to a case manager" | Instant escalation with a name and a commitment |
| 1+ hour phone wait | "Waiting an hour on a queue with screechy, noisy muzac" | 3-minute resolution, no hold |
| Hidden policy details | "Hidden on page 43 of the policy document" | Plain-language answers grounded on actual PDS |

**Sources:** https://www.productreview.com.au/listings/nrma-home-insurance · https://www.productreview.com.au/listings/nrma-car-insurance · https://choice.community/t/nrma-motor-vehicle-insurance/24306

## Architecture Overview

```
Root Agent  (greets, detects intent, routes)
│
├── [ANONYMOUS — no login required]
│   ├── Acquisition Agent       needs assessment → recommendation → quote
│   └── Comparison Agent        upload competitor policy → gap analysis → quote
│
└── [AUTHENTICATED — session variables set on login]
    ├── Coverage Explainer Agent    "am I covered if X?" grounded on PDS
    ├── Claims Agent                FNOL + status + fraud scoring
    ├── Complaint Recovery Agent    frustrated customers → priority escalation
    ├── Home Policy Agent            update address, sum insured, cover options
    ├── Car Policy Agent             add driver, update vehicle, agreed value, add-ons
    ├── Billing Agent               balance, payments, receipts
    └── Renewal Agent               surfaces renewal on session start if expiry ≤ 30 days
```

**Authentication:** Passed via session variables. Root agent checks `is_authenticated` before routing to any authenticated sub-agent.

**Data:** All structured data (quotes, claims, policies, billing) via Python tools. All policy knowledge (coverage questions, exclusions, limits) via PDS data store.

## Knowledge Base — PDS Data Store

All downloaded NRMA policy documents are loaded into a Cloud Storage data store in CX Agent Studio. The Coverage Explainer Agent and Comparison Agent are grounded on this data store for all policy-related answers.

**Documents loaded (`nrma/pds/`):**

| Product | Documents |
|---|---|
| Car Insurance | PDS, PED |
| Home Insurance | PDS, Supplementary PDS (Nov 2025), PED, Buildings KFS, Contents KFS |
| Landlord Insurance | PDS, Supplementary PDS |
| Strata Insurance | PDS |
| Motorcycle Insurance | PDS, PED |
| Boat Insurance | PDS, PED |
| Caravan / Motorhome / Trailer | PDS, PED |
| Travel Insurance | PDS |
| Business Insurance | PDS, Farm PDS |
| NSW CTP | Driver Protection Cover Info Sheet |
| ACT CTP | CTP Policy |
| SA/WA/NT | State-specific Home PED, Strata PED |

**Why this matters:** Agent answers are grounded on actual policy text — not trained to guess. If the answer isn't in the PDS, the agent says so and offers to connect to a specialist. No hallucination.

## Session Variables & Mock Data

**All customer data in the demo is mocked.** There is no connection to NRMA's real systems. Session variables simulate a logged-in customer, and all Python tools return hardcoded demo data.

### Unauthenticated session
```
is_authenticated = false
```

### Authenticated session (demo simulation)
```
is_authenticated    = true
customer_id         = CUST-001
customer_name       = Sarah Johnson
policy_numbers      = [POL-HOME-4821, POL-CAR-9034]
home_postcode       = 2073
days_to_expiry      = 14        ← triggers renewal surfacing in root agent
```

### What each tool returns (mocked)

**Tool distinction:** `get_customer_profile` returns a summary of all active policies (used by Claims to check cross-policy coverage). `get_policy_details` returns the full details of a specific policy (used by Coverage Explainer, Home Policy, Car Policy for precise coverage and change operations). They are separate tools serving different purposes.

| Tool | Mocked data |
|---|---|
| `get_available_plans` | Returns full NRMA plan catalog: Home Buildings Plus, Home Contents, Comprehensive Car, Third Party Car, Combined Home+Car |
| `recommend_plan` | Returns ranked recommendation: Home Buildings Plus (score 92/100) — matches owner-occupier, flood-adjacent postcode, family profile |
| `get_quote` | Returns quote QT-XXXXXX, monthly premium based on profile inputs |
| `analyze_existing_policy` | Pinnacle Insurance, Home+Car bundle, $270/month, $420k building, $32k car, no flood, no hire car |
| `compare_and_recommend` | Gaps: no flood cover, no hire car, no roadside. Savings: $45/month switching to NRMA |
| `get_customer_profile` | Sarah Johnson, POL-HOME-4821 (Home Buildings Plus), POL-CAR-9034 (Comprehensive) |
| `get_policy_details` | Home: $500k building, $100k contents, $750 excess, no flood. Car: 2021 RAV4, $32k agreed value, $800 excess |
| `get_coverage_gaps` | Gaps: no flood cover (postcode 2073 is flood-adjacent), sum insured not reviewed since purchase |
| `score_claim_risk` | Risk: low. Reason: policy active 18 months, first claim, amount within normal range |
| `submit_fnol` | Returns claim reference CLM-2025-XXXX with next steps |
| `get_claim_status` | Claim CLM-2024-0041, lodged 3 months ago, status "Pending Assessment", no recent updates |
| `upload_claim_document` | Returns upload confirmation with document reference DOC-XXXX attached to claim CLM-2024-0041 |
| `escalate_complaint` | Returns case manager "James T.", direct line, commitment "call by 5pm today" |
| `update_home_policy` | Returns confirmation REF-HOM-XXXX with summary of change applied |
| `update_car_policy` | Returns confirmation REF-CAR-XXXX with summary of change applied |
| `get_billing_info` | Balance $185.00, due 1 May 2025, direct debit active |
| `process_payment` | Returns receipt REF-PAY-XXXX, simulates tokenised payment from saved direct debit |
| `get_renewal_details` | Home policy expires in 14 days, current $1,680/yr, renewal $1,764/yr (+5%) |
| `confirm_renewal` | Returns renewal confirmation REF-REN-XXXX, new policy period, updated premium |

In production, all tools would call NRMA's backend APIs. The agent layer is identical — only the data source changes.

## Root Agent

**Role:** Greeter and intelligent router. Does not answer questions itself.

**Instructions summary:**
- Greet warmly, detect intent from first message
- Check `is_authenticated` before routing to authenticated agents
- If unauthenticated and requesting account features → prompt to log in
- Route to the most specific sub-agent for the intent

**Routing table:**

| Intent | Auth | Sub-agent |
|---|---|---|
| New customer, needs insurance | No | Acquisition Agent |
| Has existing policy elsewhere | No | Comparison Agent |
| Coverage / policy question | Yes | Coverage Explainer Agent |
| File a claim | Yes | Claims Agent |
| Check claim status | Yes | Claims Agent |
| Frustrated / complaint | Yes | Complaint Recovery Agent |
| Update home policy | Yes | Home Policy Agent |
| Update car policy | Yes | Car Policy Agent |
| Billing / payment | Yes | Billing Agent |
| Policy renewal | Yes | Renewal Agent |

**Guardrails:**
- Out of scope requests (e.g. roadside membership, NRMA travel club) → clearly decline and redirect to correct contact
- Never guess or fabricate policy details

## Sub-Agents

### 1. Acquisition Agent *(Anonymous)*

**Goal:** Guide a new prospect through a needs assessment and deliver a personalised plan recommendation and quote in under 2 minutes.

**Key behaviours:**
- Ask one question at a time — never a list of questions
- Explain insurance terms in plain language when they arise
- Detect life events mentioned in passing (new home, new baby, new car) natively — Gemini picks these up from the conversation and factors them into the recommendation without a tool call
- Explain *why* the recommended plan fits this specific customer — not just what it is

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_available_plans` | Python | Returns full NRMA plan catalog with coverage amounts, benefits, exclusions, ideal customer profile |
| `recommend_plan` | Python | Scores plans against customer profile (type, family, assets, budget, concern), returns ranked recommendation with personalised reason |
| `get_quote` | Python | Generates quote with reference number, applies age and postcode loading |

**Conversation flow:**
1. What type of insurance? (home / car / combined)
2. For yourself or family?
3. Own your home? Own a car?
4. Any dependants?
5. Monthly budget?
6. Main concern?
7. → `get_available_plans` + `recommend_plan`
8. Present recommendation with personalised reasoning
9. Name, age, postcode → `get_quote`
10. Quote reference + human handoff offer

**Speed target:** Under 2 minutes from first message to quote reference.

### 2. Comparison Agent *(Anonymous)*

**Goal:** Help a prospect with existing insurance elsewhere understand how NRMA compares — and why they should switch.

**Key behaviours:**
- Accept uploaded policy document (PDF) — Gemini reads and extracts details via multimodal
- Present a clear gap analysis: what they're missing, what they're overpaying
- Never disparage the competitor — focus on what NRMA adds

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `analyze_existing_policy` | Python | Takes extracted policy details (from uploaded PDF), returns structured coverage summary |
| `compare_and_recommend` | Python | Compares existing coverage against NRMA plans, returns gaps, savings estimate, and recommendation |
| `get_quote` | Python | Generates quote for the recommended switch plan |
| PDS data store | Data store | Provides NRMA coverage details for accurate comparison — agent knows exactly what NRMA covers |

**Conversation flow:**
1. Ask customer to upload or describe their current policy
2. Gemini extracts: insurer, plan type, coverage limits, premium, exclusions
3. → `analyze_existing_policy`
4. → `compare_and_recommend`
5. Present gap analysis: "You're paying $X/month and not covered for Y"
6. Recommend switch plan with savings
7. → `get_quote`
8. Human handoff offer

**Demo asset:** `nrma/demo-assets/pinnacle-policy-sarah-johnson.pdf` — mock Pinnacle Insurance policy, $270/month, missing flood cover, hire car, and roadside assist.

### 3. Coverage Explainer Agent *(Authenticated)*

**Goal:** Answer "am I covered if X happens?" accurately, in plain language, grounded on the customer's actual policy documents.

**Why this matters:** The most common NRMA complaint is discovering exclusions only when claiming. This agent eliminates that surprise — customers can ask before they need to claim.

**Key behaviours:**
- Always ground answers on the PDS data store — never guess
- Cite the relevant policy section in the answer
- Proactively flag gaps: if the customer's postcode is flood-prone and they don't have flood cover, say so
- If the answer isn't in the policy, say so clearly and offer to connect to a specialist

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_policy_details` | Python | Returns customer's active policy — type, coverage limits, excess, inclusions, exclusions |
| `get_coverage_gaps` | Python | Analyses policy against customer profile and postcode, returns gaps and upgrade suggestions |

**Data store:** PDS data store is the primary source for all coverage answers. When the customer asks a coverage question, the agent retrieves the relevant PDS sections via vector search and answers from that text — with section citation.

**Example interaction:**
> Customer: "Am I covered if a storm knocks a tree onto my fence?"
> Agent: "Yes — storm damage to fences is covered under your Home Buildings Plus policy (Section 3.2 — Storm and Rainwater). Your excess would be $750. I also noticed your policy doesn't include flood cover. Given your postcode in Pymble, you may want to consider adding it."

### 4. Claims Agent *(Authenticated)*

**Goal:** Guide an existing customer through filing a new claim or checking the status of an existing one — conversationally, without forms.

**Key behaviours:**
- Greet by name from session
- Check all active policies when a claim is filed — customer may have multiple affected
- Proactively surface entitlements the customer may not know about (hire car, emergency accommodation)
- Score claim risk before lodging — route accordingly
- Never auto-reject — always escalate high-risk claims to a human

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_customer_profile` | Python | Returns customer name, all active policies and their cover details |
| `score_claim_risk` | Python | Scores claim risk (low/medium/high) based on policy age, claim type, amount, history |
| `submit_fnol` | Python | Registers new claim, returns claim reference number and next steps |
| `get_claim_status` | Python | Returns full claim history, current status, assigned assessor, next action, expected timeline |
| `upload_claim_document` | Python | Attaches document or photo to an existing claim |

**Fraud risk routing:**

| Risk level | Action |
|---|---|
| Low | Auto-proceed — lodge claim, return reference |
| Medium | Request supporting documents before lodging |
| High | Warm escalation to specialist — never auto-reject |

**Conversation flow (new claim):**
1. Greet by name
2. "What happened?" — natural language description
3. Check all active policies for relevance
4. Surface entitlements: "You have hire car cover — up to $80/day"
5. → `score_claim_risk`
6. Collect details one question at a time (date, location, description, parties)
7. → `submit_fnol`
8. Return reference number + timeline + next steps
9. Offer document upload
10. Offer human handoff if complex

**Speed target:** Under 3 minutes from incident description to claim reference.

### 5. Complaint Recovery Agent *(Authenticated)*

**Goal:** Handle customers who arrive frustrated or angry — turn a complaint into a recovery moment.

**Why this matters:** Customers waiting months on unresolved claims are a high-churn risk. Handling them well is a retention play.

**Key behaviours:**
- Acknowledge frustration immediately — no deflection, no boilerplate apology
- Pull up claim status instantly — no asking for information the agent already has
- If claim is stuck, escalate with a specific commitment (name, timeframe)
- Customer leaves with a reference number and a named case manager

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_claim_status` | Python | Returns full claim history, current status, assigned assessor, next action, expected timeline |
| `escalate_complaint` | Python | Flags claim for priority review, assigns senior case manager, returns commitment reference and timeframe |

**Conversation flow:**
1. Acknowledge frustration — "I can see why you're frustrated, let me look at this right now"
2. → `get_claim_status` — pull up everything immediately
3. Explain current status in plain language
4. If stuck → `escalate_complaint`
5. Return: case manager name, direct contact, commitment timeframe
6. "Someone will call you by [time] today"

### 6. Home Policy Agent *(Authenticated)*

**Goal:** Handle change requests specific to home insurance policies.

**Key behaviours:**
- Confirm the change before applying
- Proactively suggest related updates (e.g. "You have updated your address — do you want to review your sum insured for the new property?")
- Return a confirmation reference for every change

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_policy_details` | Python | Returns active home policy — address, sum insured, cover type, inclusions |
| `update_home_policy` | Python | Applies change — update address, adjust sum insured, add/remove flood cover, add/remove contents cover |

**Supported changes:**
- Update insured address
- Increase or decrease building sum insured
- Add or remove contents cover
- Add flood cover
- Add accidental damage cover

### 7. Car Policy Agent *(Authenticated)*

**Goal:** Handle change requests specific to car insurance policies.

**Key behaviours:**
- Confirm the change before applying
- Proactively suggest related updates (e.g. "You have added a new car — do you want to update the agreed value?")
- Return a confirmation reference for every change

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_policy_details` | Python | Returns active car policy — vehicle, agreed value, listed drivers, add-ons |
| `update_car_policy` | Python | Applies change — add/remove driver, update vehicle details, change agreed value, add hire car or roadside assist |

**Supported changes:**
- Add or remove a named driver
- Update vehicle (new car replacement)
- Change agreed value
- Add hire car cover
- Add roadside assistance
- Update usage type (personal / business / rideshare)


### 8. Billing Agent *(Authenticated)*

**Goal:** Answer billing questions and initiate payments conversationally — without ever handling sensitive payment details.

**PCI DSS compliance note:** The agent never collects, transmits, or stores card numbers, CVV, or expiry dates. All payment processing is delegated to NRMA's existing PCI-compliant payment backend. Two patterns are supported:

- **Tokenised payment (default):** Customer has a saved payment method on file (direct debit or saved card). Agent calls the backend to charge the existing method — no card details enter the conversation.
- **Payment link fallback:** If no saved method exists, agent generates a secure one-time payment URL. Customer completes payment on a PCI-compliant hosted page outside the chat. Agent confirms once payment is received.

**For the demo:** `process_payment` simulates the tokenised pattern — returns a mock receipt reference. Narration note: *"In production, this calls NRMA's existing payment system. The agent never touches card details."*

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_billing_info` | Python | Returns current balance, due date, payment history, saved payment method status |
| `process_payment` | Python | Initiates payment via saved method or returns a secure payment link — returns receipt reference |

### 9. Renewal Agent *(Authenticated)*

**Goal:** Surface renewal information when a customer is already in the chat — before they have to ask.

**Important clarification:** The agent does not initiate conversations. "Proactive" here means the root agent checks for upcoming renewals at the start of every authenticated session and surfaces them before routing to whatever the customer came for. This can also be triggered by the NRMA website/app passing a `renewal_due = true` session variable when a customer clicks a renewal banner.

**Key behaviours:**
- Root agent checks `days_to_expiry` on session start — if ≤ 30 days, surface renewal before routing
- Explain what has changed in the renewal (premium, coverage updates)
- Suggest upgrades based on detected life events or coverage gaps
- Confirm renewal in the conversation — no separate form

**Example trigger (root agent):**
> "Hi Sarah, welcome back. Your home insurance expires in 14 days. Would you like to renew now, or shall I help you with something else first?"

**Tools:**

| Tool | Type | What it does |
|---|---|---|
| `get_renewal_details` | Python | Returns expiry date, current premium, proposed renewal premium, changes |
| `get_coverage_gaps` | Python | Reused from Coverage Explainer — analyses policy against customer profile and postcode, returns gaps and upgrade suggestions |
| `confirm_renewal` | Python | Confirms renewal, returns confirmation reference |

## Complete Tool Reference

| Tool | Agent(s) | Description |
|---|---|---|
| `get_available_plans` | Acquisition | Full NRMA plan catalog |
| `recommend_plan` | Acquisition | Scored recommendation with personalised reason |
| `get_quote` | Acquisition, Comparison | Generates quote with reference number |
| `analyze_existing_policy` | Comparison | Structures competitor policy details from uploaded PDF |
| `compare_and_recommend` | Comparison | Gap analysis + switch recommendation |
| `get_policy_details` | Coverage Explainer, Home Policy, Car Policy | Customer's active policy details |
| `get_coverage_gaps` | Coverage Explainer, Renewal | Gap analysis against customer profile and postcode — shared tool |
| `get_customer_profile` | Claims | Customer name + all active policies |
| `score_claim_risk` | Claims | Risk scoring (low/medium/high) + recommended action |
| `submit_fnol` | Claims | Lodge new claim, return reference |
| `get_claim_status` | Claims, Complaint Recovery | Full claim history, current status, assigned assessor, next action, expected timeline — shared tool |
| `upload_claim_document` | Claims | Attach document/photo to claim |
| `escalate_complaint` | Complaint Recovery | Priority flag + case manager assignment + commitment |
| `update_home_policy` | Home Policy | Apply home policy changes — address, sum insured, cover options |
| `update_car_policy` | Car Policy | Apply car policy changes — drivers, vehicle, agreed value, add-ons |
| `get_billing_info` | Billing | Balance, due date, payment history, saved payment method status |
| `process_payment` | Billing | Initiate tokenised payment or return secure payment link |
| `get_renewal_details` | Renewal | Expiry, current vs renewal premium, changes |
| `confirm_renewal` | Renewal | Confirm renewal, return reference |

## Gemini Capabilities Used

| Capability | Where |
|---|---|
| **Multimodal (PDF/image)** | Comparison Agent — reads uploaded competitor policy PDF; Claims Agent — customer photographs damage |
| **Data store grounding** | Coverage Explainer — answers grounded on actual NRMA PDS documents, with section citations |
| **Tool / function calls** | All agents — structured data always via tools, never hallucinated |
| **Personalisation** | Acquisition — recommendation explains why it fits *this* customer specifically |
| **Cross-policy awareness** | Claims — checks all active policies when one claim is filed |
| **Proactive surfacing** | Claims — tells customer about entitlements they didn't know about |
| **Life event detection** | Acquisition, Comparison — picks up on life events mentioned in passing |
| **Session state** | Auth routing, customer name used throughout authenticated journey |
| **Human handoff with context** | Claims, Complaint Recovery — full conversation passed to human agent |
| **Guardrails** | Root Agent — out-of-scope requests declined cleanly with correct redirect |
| **Multilingual** | All agents — relevant for IAG's diverse Australian customer base |

## Demo Scenarios (aligned to demo script)

| Moment | Agent | Auth | Key capability shown |
|---|---|---|---|
| 0 — First-time buyer | Acquisition | No | Conversational quoting, plain-language explanation, life event detection |
| 1 — Competitor switch | Comparison | No | Multimodal PDF reading, gap analysis, personalised recommendation |
| 2 — Coverage question | Coverage Explainer | Yes | PDS grounding, accurate answer with citation, proactive gap flagging |
| 2b — Out of scope | Root Agent | Yes | Guardrails — clean decline + correct redirect |
| 3 — Frustrated claim | Claims + Complaint Recovery | Yes | Empathy, instant status, proactive entitlements, escalation with commitment |

## Speed Benchmarks

| Interaction | Target | Industry norm |
|---|---|---|
| Quote (new customer) | Under 2 minutes | 48-hour turnaround |
| Claim lodged | Under 3 minutes | Days to weeks |
| Policy change | Under 60 seconds | Phone call + hold time |
| Coverage question | Under 30 seconds | Page 43 of a PDF |

## Build Order

**Phase 1 — Demo core (build first)**
1. Root Agent — routing + auth check + guardrails
2. Acquisition Agent + tools (`get_available_plans`, `recommend_plan`, `get_quote`)
3. Comparison Agent + tools (`analyze_existing_policy`, `compare_and_recommend`, `get_quote`) + PDS data store
4. Coverage Explainer Agent + tools (`get_policy_details`, `get_coverage_gaps`) + PDS data store

**Phase 2 — Authenticated flows**
5. Claims Agent + tools (`get_customer_profile`, `score_claim_risk`, `submit_fnol`, `get_claim_status`, `upload_claim_document`)
6. Complaint Recovery Agent + tools (`get_claim_status`, `escalate_complaint`)

**Phase 3 — Self-service**
7. Home Policy Agent + tools (`get_policy_details`, `update_home_policy`)
8. Car Policy Agent + tools (`get_policy_details`, `update_car_policy`)
9. Billing Agent + tools (`get_billing_info`, `process_payment`)
10. Renewal Agent + tools (`get_renewal_details`, `get_coverage_gaps`, `confirm_renewal`) — reuses `get_coverage_gaps` from Coverage Explainer

> Voice, telephony, and sentiment: see `nrma/voice-sentiment-future-phase.md`

## Competitive Position

| Company | Benchmark | This demo |
|---|---|---|
| Lemonade (Maya) | Quote in 90 seconds | Quote in under 2 minutes |
| Lemonade (AI Jim) | Claim paid in 3 minutes | Claim lodged in under 3 minutes |
| USAA | Sentiment-based escalation | Complaint Recovery Agent |
| Any competitor | Generic FAQ bot | PDS-grounded accurate answers with citations |
| Any competitor | Single-product chatbot | Full lifecycle — acquisition to renewal |
