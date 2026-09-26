# [SEOJEV-CONTENT-014] [SEOJEV-CONTENT-014] Author missing sections (['on_road_price', 'variants', 'engine', 'power', 't...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page http://127.0.0.1:8899/bikes/blaze-125 has content gaps: missing sections ['on_road_price', 'variants', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- http://127.0.0.1:8899/bikes/blaze-125

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'engine', 'power', 'torque', 'features', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'images', 'reviews']) and add spec rows for [].

Target Location: Editorial content on http://127.0.0.1:8899/bikes/blaze-125
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on http://127.0.0.1:8899/bikes/blaze-125`.
- [ ] Verification spec evaluates to true: `content_sections_present('http://127.0.0.1:8899/bikes/blaze-125', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: http://127.0.0.1:8899/bikes/blaze-125.

**Automated Verification Spec:**
```
content_sections_present('http://127.0.0.1:8899/bikes/blaze-125', ['on_road_price', 'variants']) == True
```
