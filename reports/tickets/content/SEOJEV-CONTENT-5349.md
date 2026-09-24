# [SEOJEV-CONTENT-5349] [SEOJEV-CONTENT-5349] Author missing sections (['price', 'on_road_price', 'variants', 'specificat...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i has content gaps: missing sections ['price', 'on_road_price', 'variants'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'variants', 'specifications', 'mileage', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/electric-vehicles/greta-electric/greta-harper-zx-series-i', ['price', 'on_road_price']) == True
```
