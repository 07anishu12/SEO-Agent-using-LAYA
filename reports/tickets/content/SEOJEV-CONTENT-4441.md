# [SEOJEV-CONTENT-4441] [SEOJEV-CONTENT-4441] Author missing sections (['price', 'on_road_price', 'specifications', 'mile...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options has content gaps: missing sections ['price', 'on_road_price', 'specifications'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options

---

### Required Implementation
Action Required: Author missing sections (['price', 'on_road_price', 'specifications', 'mileage', 'power', 'torque', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options', ['price', 'on_road_price']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/featured-stories/all-new-royal-enfield-himalayan-452-details-out-check-complete-specs-variants-and-colour-options', ['price', 'on_road_price']) == True
```
