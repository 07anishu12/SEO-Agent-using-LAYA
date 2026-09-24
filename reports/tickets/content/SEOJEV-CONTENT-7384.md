# [SEOJEV-CONTENT-7384] [SEOJEV-CONTENT-7384] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/news/2023-yamaha-r15-v4-mt-15-v2-and-r15s-launched-in-india') == True
```
