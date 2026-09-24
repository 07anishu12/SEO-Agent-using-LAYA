# [SEOJEV-CONTENT-5250] [SEOJEV-CONTENT-5250] Author missing sections (['on_road_price', 'variants', 'engine', 'power', '...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/hero/super-splendor-xtec has content gaps: missing sections ['on_road_price', 'variants', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/hero/super-splendor-xtec

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/hero/super-splendor-xtec
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/hero/super-splendor-xtec`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/hero/super-splendor-xtec', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/hero/super-splendor-xtec.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/hero/super-splendor-xtec', ['on_road_price', 'variants']) == True
```
