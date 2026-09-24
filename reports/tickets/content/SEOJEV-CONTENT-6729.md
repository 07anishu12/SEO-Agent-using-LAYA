# [SEOJEV-CONTENT-6729] [SEOJEV-CONTENT-6729] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/bikes/yamaha is 35.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/yamaha

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/bikes/yamaha
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/bikes/yamaha`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/bikes/yamaha') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/yamaha.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/bikes/yamaha') == True
```
