# [SEOJEV-ENG-069] [SEOJEV-ENG-069] Routine hygiene cleanup: review template template page has nofollow on affected ...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
Observed 1 URLs in template 'tpl_listing_ather-energy_2seg' with issue 'cluster_template_template_page_has_nofollow': Observed on 5 URLs across 1 templates. Primary concentration in 'tpl_listing_ather-energy_2seg' (5 pages affected, 100.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_listing_ather-energy_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/ather-energy/450-apex

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template page has nofollow on affected pages.

Target Location: templates/tpl_listing_ather-energy_2seg.html
Scope: Template (1 URLs affected)
Observed Hypothesis: Updating the template component for tpl_listing_ather-energy_2seg systematically remedies all 1 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_listing_ather-energy_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/ather-energy/450-apex.

**Automated Verification Spec:**
```
status_code == 200
```
