# [SEOJEV-ENG-050] [SEOJEV-ENG-050] Routine hygiene cleanup: review template template long meta description on affec...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_comparison_compare_2seg' with issue 'cluster_template_template_long_meta_description': Observed on 58 URLs across 15 templates. Primary concentration in 'tpl_comparison_compare_2seg' (5 pages affected, 8.6% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_comparison_compare_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/reviews/bajaj-pulsar-125-review-2025-ultimate-buying-guide-for-the-best-125cc-bike-in-india
- https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110
- https://www.drivio.in/birla-e-bike/birla-a-1-4
- https://www.drivio.in/careers/201
- https://www.drivio.in/joy-e-bike/beast

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template long meta description on affected pages.

Target Location: templates/tpl_comparison_compare_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_comparison_compare_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_comparison_compare_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50`.
- [ ] Validated on sample URLs: https://www.drivio.in/reviews/bajaj-pulsar-125-review-2025-ultimate-buying-guide-for-the-best-125cc-bike-in-india, https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110, https://www.drivio.in/birla-e-bike/birla-a-1-4.

**Automated Verification Spec:**
```
has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50
```
