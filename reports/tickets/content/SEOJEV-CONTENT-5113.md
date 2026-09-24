# [SEOJEV-CONTENT-5113] [SEOJEV-CONTENT-5113] Author missing sections (['variants', 'specifications', 'engine', 'power', ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews has content gaps: missing sections ['variants', 'specifications', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews

---

### Required Implementation
Action Required: Author missing sections (['variants', 'specifications', 'engine', 'power', 'torque', 'colors', 'pros', 'cons', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews', ['variants', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/electric-vehicles/yamaha/yamaha-ec-06-e/reviews', ['variants', 'specifications']) == True
```
