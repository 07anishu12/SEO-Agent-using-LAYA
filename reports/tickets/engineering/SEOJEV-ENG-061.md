# [SEOJEV-ENG-061] [SEOJEV-ENG-061] Routine hygiene cleanup: review template template page has noindex on affected p...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (2 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 2 URLs in template 'tpl_comparison_compare_2seg' with issue 'cluster_template_template_page_has_noindex': Observed on 10 URLs across 2 templates. Primary concentration in 'tpl_comparison_compare_2seg' (5 pages affected, 50.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_comparison_compare_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110
- https://www.drivio.in/ather-energy/450-apex

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template page has noindex on affected pages.

Target Location: templates/tpl_comparison_compare_2seg.html
Scope: Template (2 URLs affected)
Observed Hypothesis: Updating the template component for tpl_comparison_compare_2seg systematically remedies all 2 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_comparison_compare_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110, https://www.drivio.in/ather-energy/450-apex.

**Automated Verification Spec:**
```
status_code == 200
```
