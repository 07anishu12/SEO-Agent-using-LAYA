# [SEOJEV-CONTENT-4489] [SEOJEV-CONTENT-4489] Author missing sections (['on_road_price', 'variants', 'mileage', 'power', ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs has content gaps: missing sections ['on_road_price', 'variants', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'mileage', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/royal-enfield-himalayan-750-spotted-testing-again-with-panniers-launch-date-expected-price-and-full-specs', ['on_road_price', 'variants']) == True
```
