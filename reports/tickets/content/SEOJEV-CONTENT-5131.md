# [SEOJEV-CONTENT-5131] [SEOJEV-CONTENT-5131] Author missing sections (['on_road_price', 'specifications', 'mileage', 'en...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/simple-energy/one-s has content gaps: missing sections ['on_road_price', 'specifications', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/simple-energy/one-s

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'mileage', 'engine', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/simple-energy/one-s
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/simple-energy/one-s`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/simple-energy/one-s', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/simple-energy/one-s.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/simple-energy/one-s', ['on_road_price', 'specifications']) == True
```
