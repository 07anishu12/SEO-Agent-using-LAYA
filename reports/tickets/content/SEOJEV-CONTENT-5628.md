# [SEOJEV-CONTENT-5628] [SEOJEV-CONTENT-5628] Author missing sections (['on_road_price', 'variants', 'specifications', 'm...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'mileage', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/ather-apex-450-goes-even-faster-new-model-unveiled-at-rs-189-lakh', ['on_road_price', 'variants']) == True
```
