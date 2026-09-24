# [SEOJEV-CONTENT-5308] [SEOJEV-CONTENT-5308] Author missing sections (['price', 'on_road_price', 'variants', 'specificat...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters has content gaps: missing sections ['price', 'on_road_price', 'variants'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'variants', 'specifications', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/featured-stories/royal-enfield-sherpa-450-engine-specs-performance-and-why-it-matters', ['price', 'on_road_price']) == True
```
