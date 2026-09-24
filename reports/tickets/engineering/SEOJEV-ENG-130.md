# [SEOJEV-ENG-130] [SEOJEV-ENG-130] Routine hygiene cleanup: review short title on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_category_about-us_1seg' with issue 'cluster_short_title': Observed on 8 URLs across 8 templates. Primary concentration in 'tpl_category_about-us_1seg' (1 pages affected, 12.5% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_category_about-us_1seg.

**Sample Affected URLs:**
- https://www.drivio.in/about-us
- https://www.drivio.in/application
- https://www.drivio.in/banking-partners
- https://www.drivio.in/campaign-form
- https://www.drivio.in/privacy-policy

---

### Required Implementation
Action Required: Routine hygiene cleanup: review short title on affected pages.

Target Location: templates/tpl_category_about-us_1seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_category_about-us_1seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_category_about-us_1seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/about-us, https://www.drivio.in/application, https://www.drivio.in/banking-partners.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
