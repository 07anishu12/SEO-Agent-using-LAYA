# [SEOJEV-ENG-057] [SEOJEV-ENG-057] Routine hygiene cleanup: review template multiple h1 on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (3 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 3 URLs in template 'tpl_comparison_bikes_4seg' with issue 'cluster_template_multiple_h1': Observed on 24 URLs across 3 templates. Primary concentration in 'tpl_comparison_bikes_4seg' (8 pages affected, 33.3% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_comparison_bikes_4seg.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/tvs/raider/reviews
- https://www.drivio.in/bikes/hero/splendor-plus/reviews
- https://www.drivio.in/electric-vehicles/flyrides/eric/reviews

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template multiple h1 on affected pages.

Target Location: templates/tpl_comparison_bikes_4seg.html
Scope: Template (3 URLs affected)
Observed Hypothesis: Updating the template component for tpl_comparison_bikes_4seg systematically remedies all 3 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_comparison_bikes_4seg.html`.
- [ ] Verification spec evaluates to true: `selector_count("h1") == 1`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/tvs/raider/reviews, https://www.drivio.in/bikes/hero/splendor-plus/reviews, https://www.drivio.in/electric-vehicles/flyrides/eric/reviews.

**Automated Verification Spec:**
```
selector_count("h1") == 1
```
