# [SEOJEV-CONTENT-5254] [SEOJEV-CONTENT-5254] Author missing sections (['on_road_price', 'variants', 'specifications', 'e...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/featured-stories/best-scooty-to-buy-in-july-2025-in-india-top-models-mileage-and-prices', ['on_road_price', 'variants']) == True
```
