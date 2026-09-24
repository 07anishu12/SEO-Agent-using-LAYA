# [SEOJEV-CONTENT-5611] [SEOJEV-CONTENT-5611] Author missing sections (['on_road_price', 'specifications', 'engine', 'pow...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more has content gaps: missing sections ['on_road_price', 'specifications', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/2025-suzuki-access-125-launched-in-india-with-tft-display-at-102-lakh-features-price-specs-and-more', ['on_road_price', 'specifications']) == True
```
