# [SEOJEV-CONTENT-5610] [SEOJEV-CONTENT-5610] Author missing sections (['on_road_price', 'variants', 'specifications', 'm...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings has content gaps: missing sections ['on_road_price', 'variants', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'specifications', 'mileage', 'engine', 'power', 'torque', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/2025-honda-rebel-500-launched-in-india-at-512-lakh-specs-features-and-bookings', ['on_road_price', 'variants']) == True
```
