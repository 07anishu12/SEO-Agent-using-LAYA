# [SEOJEV-ENG-016] [SEOJEV-ENG-016] Routine hygiene cleanup: review template missing h1 on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (3 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 3 URLs in template 'tpl_brand_bikes_2seg' with issue 'cluster_template_missing_h1': Observed on 24 URLs across 3 templates. Primary concentration in 'tpl_brand_bikes_2seg' (8 pages affected, 33.3% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_bikes_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/honda
- https://www.drivio.in/electric-vehicles/hero
- https://www.drivio.in/scooters/hero

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template missing h1 on affected pages.

Target Location: templates/tpl_brand_bikes_2seg.html
Scope: Template (3 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_bikes_2seg systematically remedies all 3 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_bikes_2seg.html`.
- [ ] Verification spec evaluates to true: `selector_count("h1") == 1`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/honda, https://www.drivio.in/electric-vehicles/hero, https://www.drivio.in/scooters/hero.

**Automated Verification Spec:**
```
selector_count("h1") == 1
```
