# [SEOJEV-CONTENT-4861] [SEOJEV-CONTENT-4861] Author missing sections (['on_road_price', 'mileage', 'power', 'torque', 'p...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/royal-enfield/classic-350 has content gaps: missing sections ['on_road_price', 'mileage', 'power'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/royal-enfield/classic-350

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'mileage', 'power', 'torque', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/royal-enfield/classic-350
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/royal-enfield/classic-350`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/royal-enfield/classic-350', ['on_road_price', 'mileage']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/royal-enfield/classic-350.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/royal-enfield/classic-350', ['on_road_price', 'mileage']) == True
```
