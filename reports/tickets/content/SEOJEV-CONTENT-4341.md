# [SEOJEV-CONTENT-4341] [SEOJEV-CONTENT-4341] Author missing sections (['on_road_price', 'mileage', 'engine', 'torque', '...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/ola-electric/ola-roadster has content gaps: missing sections ['on_road_price', 'mileage', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/ola-electric/ola-roadster

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'mileage', 'engine', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/ola-electric/ola-roadster
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/ola-electric/ola-roadster`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/ola-electric/ola-roadster', ['on_road_price', 'mileage']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/ola-electric/ola-roadster.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/ola-electric/ola-roadster', ['on_road_price', 'mileage']) == True
```
