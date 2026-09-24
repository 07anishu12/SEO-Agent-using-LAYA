# [SEOJEV-CONTENT-4093] [SEOJEV-CONTENT-4093] Author missing sections (['variants', 'engine', 'torque', 'features', 'pros...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/tvs/ntorq-125/reviews has content gaps: missing sections ['variants', 'engine', 'torque'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/tvs/ntorq-125/reviews

---

### Required Implementation
Action Required: Author missing sections (['variants', 'engine', 'torque', 'features', 'pros', 'cons', 'emi', 'faqs']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/tvs/ntorq-125/reviews
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/tvs/ntorq-125/reviews`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/tvs/ntorq-125/reviews', ['variants', 'engine']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/tvs/ntorq-125/reviews.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/tvs/ntorq-125/reviews', ['variants', 'engine']) == True
```
