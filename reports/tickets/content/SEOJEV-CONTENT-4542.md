# [SEOJEV-CONTENT-4542] [SEOJEV-CONTENT-4542] Author missing sections (['on_road_price', 'specifications', 'mileage', 'en...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/electric-vehicles/ola-electric/s1-x has content gaps: missing sections ['on_road_price', 'specifications', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/electric-vehicles/ola-electric/s1-x

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'mileage', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/electric-vehicles/ola-electric/s1-x
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/electric-vehicles/ola-electric/s1-x`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/electric-vehicles/ola-electric/s1-x', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/electric-vehicles/ola-electric/s1-x.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/electric-vehicles/ola-electric/s1-x', ['on_road_price', 'specifications']) == True
```
