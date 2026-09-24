# [SEOJEV-CONTENT-4090] [SEOJEV-CONTENT-4090] Author missing sections (['price', 'on_road_price', 'variants', 'mileage', ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/tvs/jupiter-125 has content gaps: missing sections ['price', 'on_road_price', 'variants'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/tvs/jupiter-125

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'variants', 'mileage', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/tvs/jupiter-125
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/tvs/jupiter-125`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/tvs/jupiter-125', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/tvs/jupiter-125.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/tvs/jupiter-125', ['price', 'on_road_price']) == True
```
