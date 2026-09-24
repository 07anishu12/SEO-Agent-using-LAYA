# [SEOJEV-CONTENT-5619] [SEOJEV-CONTENT-5619] Author missing sections (['on_road_price', 'specifications', 'mileage', 'en...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes has content gaps: missing sections ['on_road_price', 'specifications', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'mileage', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/2026-royal-enfield-classic-350-launched-with-assist-and-slipper-clutch-price-specs-and-what-actually-changes', ['on_road_price', 'specifications']) == True
```
