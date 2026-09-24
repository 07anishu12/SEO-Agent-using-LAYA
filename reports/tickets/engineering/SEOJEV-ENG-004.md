# [SEOJEV-ENG-004] [SEOJEV-ENG-004] High-impact fix: update tpl_model_bikes_3seg layout to resolve weakly linked pro...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_model_bikes_3seg' with issue 'cluster_weakly_linked_product_page': Observed on 1,302 URLs across 8 templates. Primary concentration in 'tpl_model_bikes_3seg' (371 pages affected, 28.5% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_bikes_3seg.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/hero-electric/nyx
- https://www.drivio.in/bikes/joy-e-bike/monster
- https://www.drivio.in/bikes/earth-energy-ev/evolve-r
- https://www.drivio.in/bikes/dao/703
- https://www.drivio.in/bikes/ola-electric/ola-roadster

---

### Required Implementation
Action Required: High-impact fix: update tpl_model_bikes_3seg layout to resolve weakly linked product page across 1302 pages.

Target Location: templates/tpl_model_bikes_3seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_bikes_3seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_bikes_3seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/hero-electric/nyx, https://www.drivio.in/bikes/joy-e-bike/monster, https://www.drivio.in/bikes/earth-energy-ev/evolve-r.

**Automated Verification Spec:**
```
status_code == 200
```
