# [SEOJEV-CONTENT-4503] [SEOJEV-CONTENT-4503] Author missing sections (['on_road_price', 'mileage', 'torque', 'colors', '...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals has content gaps: missing sections ['on_road_price', 'mileage', 'torque'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'mileage', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals', ['on_road_price', 'mileage']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/yamaha-r2-launched-at-230-lakh-in-india-price-specs-features-and-rivals', ['on_road_price', 'mileage']) == True
```
