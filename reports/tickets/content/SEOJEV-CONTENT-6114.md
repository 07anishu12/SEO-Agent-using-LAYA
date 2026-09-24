# [SEOJEV-CONTENT-6114] [SEOJEV-CONTENT-6114] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat') == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat.

**Automated Verification Spec:**
```
has_qa_section('https://www.drivio.in/news/yamaha-launches-motogp-edition-of-r15m-mt-15-and-ray-zr-125-ahead-of-motogp-bharat') == True
```
