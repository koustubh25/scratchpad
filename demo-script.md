# NRMA Demo Script

## Before the Demo — Preparation Checklist

**Test NRMA's current chatbot:**
Go to https://www.nrma.com.au/car-insurance — open the chat widget and ask:
1. *"Am I covered if a storm damages my car?"*
2. *"I just had an accident, what do I do?"*
3. *"Can you help me compare plans?"*

Screenshot the responses. The current bot will give generic FAQ answers and deflect to "call 132 132." Show these screenshots before the demo starts — the contrast with Gemini speaks for itself.

**Prepare the mock competitor policy:**
- PDF is ready at `nrma/demo-assets/pinnacle-policy-sarah-johnson.pdf`
- Have it ready to upload during Moment 1

**Session setup:**
- CX Agent Studio preview panel open in browser
- `is_authenticated = false` for Moments 0–1
- `is_authenticated = true` for Moments 2–4
- PDS data store attached to Coverage Explainer Agent

---

## Audience
Mixed — CX, commercial, and executive stakeholders at IAG.

## Duration
~12 minutes

---

## Opening (spoken, ~30 seconds)

> "NRMA customers wait over an hour on hold.
> Claims take months with no updates.
> People discover they're not covered only when they need to claim.
>
> We're going to follow one customer — Sarah — through four moments in her life with NRMA.
> Same customer. Four moments. No hold music. No broken forms. No surprises."

---

## Moment 0 — First-Time Buyer (2 min)

**Context:** Sarah is 26. She just bought her first home. She's never had home insurance before.

**Narration:**
> "Sarah has never bought insurance before. She doesn't know what 'sum insured' means. Watch how the agent guides her without overwhelming her."

**Type into chat:**
```
Hi, I just bought my first home and I think I need insurance but I'm not really sure what I need
```

**What to show:**
- Agent asks one question at a time — not a form
- Explains "sum insured" and "contents cover" in plain language when relevant
- Recommends a plan and explains why it fits Sarah specifically
- Generates a quote reference

**After:**
> "She understands what she's buying and why. No jargon. No PDF to read. Two minutes."

---

*[Transition — spoken]*
> "A year later. Sarah's car insurance is up for renewal with her current insurer. She's heard NRMA might be better value."

---

## Moment 1 — Competitor Switch (2 min)

**Context:** Sarah wants to know if switching to NRMA makes sense. She has her Allianz policy summary.

**Narration:**
> "She's not looking for a lecture — she wants to know if switching makes sense. Watch what happens when she uploads her existing policy."

**Type into chat:**
```
I'm currently with Pinnacle Insurance for my car and home insurance. Can NRMA do better? I've uploaded my current policy
```
*(Upload `pinnacle-policy-sarah-johnson.pdf`)*

**What to show:**
- Agent reads the uploaded PDF — extracts insurer, coverage limits, premium, exclusions
- Identifies gaps: no flood cover, no hire car, no roadside assist
- Presents comparison: "You're paying $270/month with Pinnacle and not covered for flood damage or hire car"
- Recommends NRMA HomeSafe Plus — saves $X/month, adds flood and hire car
- Generates a quote

**After:**
> "She didn't have to explain her policy. The agent read it. Found three gaps. Made the case in 90 seconds."

---

*[Transition — spoken]*
> "Six months later. Sarah now logs into her NRMA account. Watch how the experience changes."

**Switch session to authenticated:**
1. Click **Session settings** in the Preview panel
2. Set `is_authenticated = true`, `customer_name = Sarah Johnson`, `policy_numbers = POL-HOME-4821, POL-CAR-9034`
3. Click **New conversation**

*Narrate while doing this:*
> "Same agent. Same conversation. Now she's logged in — the agent knows who she is, what she has, and can act on her behalf."

---

## Moment 2 — Coverage Question (2 min)

**Context:** Sarah asks a coverage question. Switch session to authenticated.

**Narration:**
> "This is the question NRMA customers currently have to find on page 43 of a PDF. Or wait on hold to ask."

**Type into chat:**
```
Am I covered if a storm knocks a tree onto my fence?
```

**What to show:**
- Agent reads Sarah's actual policy via the PDS data store
- Answers in plain language with the relevant policy section cited
- Proactively flags: "Your sum insured hasn't been updated since you bought the policy. With building costs rising, you may want to review it."

**After:**
> "Accurate answer from her actual policy. Not a guess. And she just learned something she didn't know to ask."

---

*[Transition — spoken]*
> "Now — something the agent can't help with. This is important."

---

## Moment 2b — Out of Scope (30 seconds)

**Context:** Sarah asks something outside the agent's scope — shows guardrails working.

**Type into chat:**
```
Can you help me with my NRMA roadside assistance membership?
```

**What to show:**
- Agent clearly states it can only help with insurance — not roadside membership
- Gives her the right contact: "For roadside assistance, contact the NRMA directly on 132 132 or via the My NRMA app"
- Does not guess or make something up

**After:**
> "It knows what it doesn't know. That's as important as what it does know. No hallucination, no wrong answer — just a clear redirect."

---

*[Transition — spoken]*
> "Three months later. A hailstorm. Sarah's car is damaged. She tried the NRMA website to lodge a claim — it crashed."

---

## Moment 3 — Claim (3 min)

**Context:** Sarah is frustrated. The website failed her. This is the moment that defines retention.

**Narration:**
> "She's already had a bad experience. Watch how the agent handles it."

**Type into chat:**
```
I need to make a claim. My car was damaged in the hailstorm last night. I tried the website and it crashed. I'm really frustrated
```

**What to show:**
- Agent acknowledges frustration immediately — no deflection, no "I'm sorry to hear that" boilerplate
- Pulls up Sarah's policy and active cover
- Proactively: "You have cover for a hire car — up to $80/day while your car is being repaired"
- Collects claim details conversationally — one question at a time
- Lodges the claim, returns reference number
- Clear next steps and timeline

**After:**
> "She came in frustrated. She left with a claim reference, a hire car entitlement she didn't know about, and a clear timeline. Three minutes."

---

## Close (spoken, ~1 minute)

> "Same customer. Four moments. First-time buyer to loyal customer.
> No hold music. No broken forms. No surprises on page 43.
>
> This is what NRMA's customer experience looks like with Gemini."

---

## Call to Action

> "What you've seen today took us a matter of days to build — not months.
>
> The architecture is designed. The policy documents are loaded. The agent is running on Google Cloud with enterprise data residency — your customer data stays in Australia.
>
> The question isn't whether this is possible. It's which customer journey you want to transform first.
>
> We'd like to propose a 4-week sprint: pick one flow, build it properly, measure it against your current contact centre metrics. We'll show you the ROI before you commit to anything larger."

---

## Q&A — Key Messages

**"Is this replacing our contact centre?"**
> No — it handles the routine so your people focus on the complex. High-risk claims, disputes, vulnerable customers — those still go to humans, with full conversation context passed over.

**"How accurate is it on policy questions?"**
> It's grounded on your actual PDS documents — not trained to guess. If the answer isn't in the policy, it says so and redirects. You saw that in the roadside assistance moment.

**"How long to build this for production?"**
> The POC took days. A production deployment — with your systems integration, auth, and compliance review — is a 3–6 month program depending on scope. The 4-week sprint gets you a measurable pilot first.

**"Can this work across our other brands?"**
> Yes — same platform, different brand voice and product catalog. ROLLiN', CGU, WFI — each gets its own agent. One investment, deployed across the portfolio.

**"What about data privacy?"**
> Enterprise Gemini runs on Google Cloud with Australian data residency. Customer data is not used to train models. The function call architecture means PII stays in your backend — Gemini only sees what it needs to answer the question.
