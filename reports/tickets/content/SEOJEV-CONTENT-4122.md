# [SEOJEV-CONTENT-4122] [SEOJEV-CONTENT-4122] Author missing sections (['price', 'on_road_price', 'variants', 'specificat...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/tvs/scooty-zest/reviews has content gaps: missing sections ['price', 'on_road_price', 'variants'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/tvs/scooty-zest/reviews

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'variants', 'specifications', 'engine', 'torque', 'colors', 'pros', 'cons', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/tvs/scooty-zest/reviews
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/tvs/scooty-zest/reviews`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/tvs/scooty-zest/reviews', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/tvs/scooty-zest/reviews.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/tvs/scooty-zest/reviews', ['price', 'on_road_price']) == True
```
