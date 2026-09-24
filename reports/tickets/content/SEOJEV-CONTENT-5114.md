# [SEOJEV-CONTENT-5114] [SEOJEV-CONTENT-5114] Author missing sections (['on_road_price', 'specifications', 'engine', 'pow...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews has content gaps: missing sections ['on_road_price', 'specifications', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/electric-vehicles/piaggio/vespa-150/reviews', ['on_road_price', 'specifications']) == True
```
