# [SEOJEV-CONTENT-6542] [SEOJEV-CONTENT-6542] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/featured-stories/eicma-2023-all-bikes-and-scooters-that-will-come-to-india-before-long') == True
```
