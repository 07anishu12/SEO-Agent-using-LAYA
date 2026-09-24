# [SEOJEV-ENG-010] [SEOJEV-ENG-010] Routine hygiene cleanup: review template template orphan page on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_city_indian_2seg' with issue 'cluster_template_template_orphan_page': Observed on 689 URLs across 193 templates. Primary concentration in 'tpl_city_indian_2seg' (5 pages affected, 0.7% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_city_indian_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/one-electric-motorcycles/kridn
- https://www.drivio.in/reviews/10-most-popular-sub-200cc-naked-bikes-in-india
- https://www.drivio.in/adventure
- https://www.drivio.in/aftek-motors-scooters
- https://www.drivio.in/avan-motors-scooters

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template orphan page on affected pages.

Target Location: templates/tpl_city_indian_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_city_indian_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_city_indian_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/one-electric-motorcycles/kridn, https://www.drivio.in/reviews/10-most-popular-sub-200cc-naked-bikes-in-india, https://www.drivio.in/adventure.

**Automated Verification Spec:**
```
status_code == 200
```
