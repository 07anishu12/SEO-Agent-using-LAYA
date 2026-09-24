# [SEOJEV-CONTENT-6171] [SEOJEV-CONTENT-6171] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol') == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol.

**Automated Verification Spec:**
```
has_qa_section('https://drivio.in/featured-stories/ev-scooter-catches-fire-what-actually-happens-and-is-it-more-dangerous-than-petrol') == True
```
