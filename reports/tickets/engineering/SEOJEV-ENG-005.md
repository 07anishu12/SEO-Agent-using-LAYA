# [SEOJEV-ENG-005] [SEOJEV-ENG-005] High-impact fix: update tpl_brand_electric-vehicles_2seg layout to resolve missi...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_electric-vehicles_2seg' with issue 'cluster_missing_h1': Observed on 135 URLs across 10 templates. Primary concentration in 'tpl_brand_electric-vehicles_2seg' (88 pages affected, 65.2% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_electric-vehicles_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/honda
- https://www.drivio.in/bikes/hero
- https://www.drivio.in/bikes/royal-enfield
- https://www.drivio.in/bikes/bajaj
- https://www.drivio.in/bikes/yamaha

---

### Required Implementation
Action Required: High-impact fix: update tpl_brand_electric-vehicles_2seg layout to resolve missing h1 across 135 pages.

Target Location: templates/tpl_brand_electric-vehicles_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_electric-vehicles_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_electric-vehicles_2seg.html`.
- [ ] Verification spec evaluates to true: `selector_count("h1") == 1`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/honda, https://www.drivio.in/bikes/hero, https://www.drivio.in/bikes/royal-enfield.

**Automated Verification Spec:**
```
selector_count("h1") == 1
```
