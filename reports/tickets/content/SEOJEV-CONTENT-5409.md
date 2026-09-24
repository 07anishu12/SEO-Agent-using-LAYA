# [SEOJEV-CONTENT-5409] [SEOJEV-CONTENT-5409] Author missing sections (['on_road_price', 'engine', 'power', 'torque', 'pr...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/hero/splendor-plus-xtec has content gaps: missing sections ['on_road_price', 'engine', 'power'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/hero/splendor-plus-xtec

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'engine', 'power', 'torque', 'pros', 'cons', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/hero/splendor-plus-xtec
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/hero/splendor-plus-xtec`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/hero/splendor-plus-xtec', ['on_road_price', 'engine']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/hero/splendor-plus-xtec.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/hero/splendor-plus-xtec', ['on_road_price', 'engine']) == True
```
