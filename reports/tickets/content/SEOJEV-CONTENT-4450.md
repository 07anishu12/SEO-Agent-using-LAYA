# [SEOJEV-CONTENT-4450] [SEOJEV-CONTENT-4450] Author missing sections (['price', 'on_road_price', 'mileage', 'engine', 'p...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1 has content gaps: missing sections ['price', 'on_road_price', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'mileage', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/2023-royal-enfield-bullet-350-will-come-in-3-variants-launch-on-sept-1', ['price', 'on_road_price']) == True
```
