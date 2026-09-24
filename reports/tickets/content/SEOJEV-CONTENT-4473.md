# [SEOJEV-CONTENT-4473] [SEOJEV-CONTENT-4473] Author missing sections (['on_road_price', 'mileage', 'power', 'torque', 'f...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh has content gaps: missing sections ['on_road_price', 'mileage', 'power'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'mileage', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh', ['on_road_price', 'mileage']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/hero-xtreme-160r-4v-cruise-control-variant-unveiled-at-134-lakh', ['on_road_price', 'mileage']) == True
```
