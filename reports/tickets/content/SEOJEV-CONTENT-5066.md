# [SEOJEV-CONTENT-5066] [SEOJEV-CONTENT-5066] Author missing sections (['on_road_price', 'variants', 'specifications', 'm...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/triumph/bonneville-t120/reviews has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/triumph/bonneville-t120/reviews

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'mileage', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/triumph/bonneville-t120/reviews
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/triumph/bonneville-t120/reviews`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/triumph/bonneville-t120/reviews', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/triumph/bonneville-t120/reviews.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/triumph/bonneville-t120/reviews', ['on_road_price', 'variants']) == True
```
