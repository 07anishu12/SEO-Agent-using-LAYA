# [SEOJEV-CONTENT-5642] [SEOJEV-CONTENT-5642] Author missing sections (['on_road_price', 'specifications', 'mileage', 'en...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734 has content gaps: missing sections ['on_road_price', 'specifications', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'mileage', 'engine', 'power', 'torque', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/news/honda-activa-limited-edition-variant-launched-priced-between-rs-80-734-82-734', ['on_road_price', 'specifications']) == True
```
