# [SEOJEV-CONTENT-018] [SEOJEV-CONTENT-018] Author missing sections (['on_road_price', 'variants', 'mileage', 'power', '...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page http://127.0.0.1:8899/bikes/hidden-cruiser has content gaps: missing sections ['on_road_price', 'variants', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- http://127.0.0.1:8899/bikes/hidden-cruiser

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'mileage', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'images', 'reviews']) and add spec rows for [].

Target Location: Editorial content on http://127.0.0.1:8899/bikes/hidden-cruiser
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on http://127.0.0.1:8899/bikes/hidden-cruiser`.
- [ ] Verification spec evaluates to true: `content_sections_present('http://127.0.0.1:8899/bikes/hidden-cruiser', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: http://127.0.0.1:8899/bikes/hidden-cruiser.

**Automated Verification Spec:**
```
content_sections_present('http://127.0.0.1:8899/bikes/hidden-cruiser', ['on_road_price', 'variants']) == True
```
