# [SEOJEV-CONTENT-4466] [SEOJEV-CONTENT-4466] Author missing sections (['on_road_price', 'mileage', 'torque', 'colors', '...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants has content gaps: missing sections ['on_road_price', 'mileage', 'torque'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'mileage', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants', ['on_road_price', 'mileage']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/bmw-m-1000-r-launched-at-rs-33-lakh-in-india-gets-two-variants', ['on_road_price', 'mileage']) == True
```
