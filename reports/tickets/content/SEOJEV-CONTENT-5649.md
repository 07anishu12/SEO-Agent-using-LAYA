# [SEOJEV-CONTENT-5649] [SEOJEV-CONTENT-5649] Author missing sections (['on_road_price', 'variants', 'specifications', 'm...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'mileage', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/kawasaki-versys-x-300-re-launched-in-india-at-380-lakh-specs-features-rivals', ['on_road_price', 'variants']) == True
```
