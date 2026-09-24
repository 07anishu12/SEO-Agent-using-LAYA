# [SEOJEV-CONTENT-5624] [SEOJEV-CONTENT-5624] Author missing sections (['on_road_price', 'variants', 'engine', 'power', '...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/vespa/125 has content gaps: missing sections ['on_road_price', 'variants', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/vespa/125

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/vespa/125
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/vespa/125`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/vespa/125', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/vespa/125.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/vespa/125', ['on_road_price', 'variants']) == True
```
