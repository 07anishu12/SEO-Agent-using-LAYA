# [SEOJEV-ENG-040] [SEOJEV-ENG-040] Routine hygiene cleanup: review template template long title truncated on affect...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_husqvarna-motorcycles_2seg' with issue 'cluster_template_template_long_title_truncated': Observed on 245 URLs across 55 templates. Primary concentration in 'tpl_brand_husqvarna-motorcycles_2seg' (5 pages affected, 2.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_husqvarna-motorcycles_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250
- https://www.drivio.in/reviews/bajaj-pulsar-125-review-2025-ultimate-buying-guide-for-the-best-125cc-bike-in-india
- https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110
- https://www.drivio.in/reviews/ather-450-apex-vs-bajaj-chetak-premium-motors
- https://www.drivio.in/aeroride/e-spark

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template long title truncated on affected pages.

Target Location: templates/tpl_brand_husqvarna-motorcycles_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_husqvarna-motorcycles_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_husqvarna-motorcycles_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250, https://www.drivio.in/reviews/bajaj-pulsar-125-review-2025-ultimate-buying-guide-for-the-best-125cc-bike-in-india, https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
