# [SEOJEV-CONTENT-5644] [SEOJEV-CONTENT-5644] Author missing sections (['on_road_price', 'specifications', 'mileage', 'po...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals has content gaps: missing sections ['on_road_price', 'specifications', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'mileage', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/honda-cb350c-2026-launched-in-india-at-rs-2-lakh-price-specs-rivals', ['on_road_price', 'specifications']) == True
```
