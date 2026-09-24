# [SEOJEV-CONTENT-6541] [SEOJEV-CONTENT-6541] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/featured-stories/delhi-ev-policy-2026-30-000-subsidy-on-electric-scooters-who-qualifies-and-how-to-claim-it') == True
```
