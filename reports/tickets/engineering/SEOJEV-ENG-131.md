# [SEOJEV-ENG-131] [SEOJEV-ENG-131] Routine hygiene cleanup: review heading hierarchy skipped h2 on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_category_application_1seg' with issue 'cluster_heading_hierarchy_skipped_h2': Observed on 8 URLs across 8 templates. Primary concentration in 'tpl_category_application_1seg' (1 pages affected, 12.5% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_category_application_1seg.

**Sample Affected URLs:**
- https://www.drivio.in/application
- https://www.drivio.in/campaign-form
- https://www.drivio.in/expert-articles
- https://www.drivio.in/featured-stories
- https://www.drivio.in/fuel-prices

---

### Required Implementation
Action Required: Routine hygiene cleanup: review heading hierarchy skipped h2 on affected pages.

Target Location: templates/tpl_category_application_1seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_category_application_1seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_category_application_1seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/application, https://www.drivio.in/campaign-form, https://www.drivio.in/expert-articles.

**Automated Verification Spec:**
```
status_code == 200
```
