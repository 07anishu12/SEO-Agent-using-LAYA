# [SEOJEV-CONTENT-5614] [SEOJEV-CONTENT-5614] Author missing sections (['on_road_price', 'variants', 'specifications', 'm...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'mileage', 'power', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/2025-suzuki-gsx-8r-obd-2b-launched-at-925-lakh-in-india-full-specs-and-features-revealed', ['on_road_price', 'variants']) == True
```
