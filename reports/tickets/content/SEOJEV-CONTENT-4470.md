# [SEOJEV-CONTENT-4470] [SEOJEV-CONTENT-4470] Author missing sections (['price', 'on_road_price', 'variants', 'mileage', ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed has content gaps: missing sections ['price', 'on_road_price', 'variants'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'variants', 'mileage', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/hero-mavrick-440-discontinued-in-india-reasons-and-specs-revealed', ['price', 'on_road_price']) == True
```
