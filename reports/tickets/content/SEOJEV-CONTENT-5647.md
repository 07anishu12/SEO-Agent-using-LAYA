# [SEOJEV-CONTENT-5647] [SEOJEV-CONTENT-5647] Author missing sections (['price', 'on_road_price', 'variants', 'mileage', ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights has content gaps: missing sections ['price', 'on_road_price', 'variants'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'variants', 'mileage', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/honda-transalp-xl750-sp-unveiled-overseas-specs-and-highlights', ['price', 'on_road_price']) == True
```
