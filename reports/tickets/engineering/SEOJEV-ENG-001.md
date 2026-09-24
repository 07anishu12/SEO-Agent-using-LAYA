# [SEOJEV-ENG-001] [SEOJEV-ENG-001] Immediate engineering blocker: resolve sitemap url has noindex across 68 URLs.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_model_Nmotors_2seg' with issue 'cluster_sitemap_url_has_noindex': Observed on 68 URLs across 67 templates. Primary concentration in 'tpl_model_Nmotors_2seg' (2 pages affected, 2.9% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_Nmotors_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/22motors-scooters
- https://www.drivio.in/avan-motors-scooters
- https://www.drivio.in/avera-scooters-scooters
- https://www.drivio.in/bajaj-urbanite-scooters
- https://www.drivio.in/battre-electric-scooters-scooters

---

### Required Implementation
Action Required: Immediate engineering blocker: resolve sitemap url has noindex across 68 URLs.

Target Location: templates/tpl_model_Nmotors_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_Nmotors_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_Nmotors_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/22motors-scooters, https://www.drivio.in/avan-motors-scooters, https://www.drivio.in/avera-scooters-scooters.

**Automated Verification Spec:**
```
status_code == 200
```
