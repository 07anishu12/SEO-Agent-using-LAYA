# [SEOJEV-CONTENT-7548] [SEOJEV-CONTENT-7548] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/news/royal-enfield-shotgun-650-x-rough-crafts-launched-in-india-at-rs-575-lakh') == True
```
