# [SEOJEV-CONTENT-6204] [SEOJEV-CONTENT-6204] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter') == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter.

**Automated Verification Spec:**
```
has_qa_section('https://drivio.in/featured-stories/is-a-15-lakh-motorcycle-worth-it-over-a-90k-scooter') == True
```
