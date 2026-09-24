# [SEOJEV-CONTENT-4498] [SEOJEV-CONTENT-4498] Author missing sections (['price', 'on_road_price', 'specifications', 'mile...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant has content gaps: missing sections ['price', 'on_road_price', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'specifications', 'mileage', 'engine', 'power', 'torque', 'features', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant', ['price', 'on_road_price']) == True
```
