# [SEOJEV-CONTENT-8425] [SEOJEV-CONTENT-8425] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch is 35.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/news/triumph-street-triple-1200-rs-unveiled-premium-naked-motorcycle-set-for-india-launch') == True
```
