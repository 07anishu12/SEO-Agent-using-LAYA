# [SEOJEV-CONTENT-4499] [SEOJEV-CONTENT-4499] Author missing sections (['on_road_price', 'variants', 'specifications', 'e...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'engine', 'power', 'torque', 'features', 'pros', 'cons', 'comparison', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/yamaha-fascino-125-fi-hybrid-available-in-three-new-colours-price-specs-and-full-details', ['on_road_price', 'variants']) == True
```
