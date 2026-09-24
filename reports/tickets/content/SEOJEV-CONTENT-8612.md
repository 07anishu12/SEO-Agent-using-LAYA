# [SEOJEV-CONTENT-8612] [SEOJEV-CONTENT-8612] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month') == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month.

**Automated Verification Spec:**
```
has_qa_section('https://drivio.in/news/kawasaki-z900-price-in-india-gets-sweeter-with-free-accessory-and-finance-offer-this-month') == True
```
