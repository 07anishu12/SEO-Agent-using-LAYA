# [SEOJEV-ENG-015] [SEOJEV-ENG-015] High-impact fix: update tpl_brand_bikes_2seg layout to resolve missing h1 across...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (2 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 2 URLs in template 'tpl_brand_bikes_2seg' with issue 'cluster_missing_h1': Observed on 2 URLs across 1 templates. Primary concentration in 'tpl_brand_bikes_2seg' (2 pages affected, 100.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_bikes_2seg.

**Sample Affected URLs:**
- http://127.0.0.1:8899/bikes/eco-scooter
- http://127.0.0.1:8899/bikes/js-only-model

---

### Required Implementation
Action Required: High-impact fix: update tpl_brand_bikes_2seg layout to resolve missing h1 across 2 pages.

Target Location: templates/tpl_brand_bikes_2seg.html
Scope: Template (2 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_bikes_2seg systematically remedies all 2 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_bikes_2seg.html`.
- [ ] Verification spec evaluates to true: `selector_count("h1") == 1`.
- [ ] Validated on sample URLs: http://127.0.0.1:8899/bikes/eco-scooter, http://127.0.0.1:8899/bikes/js-only-model.

**Automated Verification Spec:**
```
selector_count("h1") == 1
```
