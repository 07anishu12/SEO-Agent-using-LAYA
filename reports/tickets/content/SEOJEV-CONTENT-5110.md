# [SEOJEV-CONTENT-5110] [SEOJEV-CONTENT-5110] Author missing sections (['on_road_price', 'variants', 'specifications', 'm...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/electric-vehicles/vespa/electric-scooter has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/electric-vehicles/vespa/electric-scooter

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'mileage', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/electric-vehicles/vespa/electric-scooter
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/electric-vehicles/vespa/electric-scooter`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/electric-vehicles/vespa/electric-scooter', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/electric-vehicles/vespa/electric-scooter.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/electric-vehicles/vespa/electric-scooter', ['on_road_price', 'variants']) == True
```
