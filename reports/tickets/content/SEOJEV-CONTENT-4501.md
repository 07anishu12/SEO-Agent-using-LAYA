# [SEOJEV-CONTENT-4501] [SEOJEV-CONTENT-4501] Author missing sections (['on_road_price', 'specifications', 'mileage', 'en...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier has content gaps: missing sections ['on_road_price', 'specifications', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'mileage', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/yamaha-mt-15-v2-price-hike-all-variants-now-costlier', ['on_road_price', 'specifications']) == True
```
