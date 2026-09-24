# [SEOJEV-ENG-035] [SEOJEV-ENG-035] Routine hygiene cleanup: review template template duplicate title tag on affecte...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_husqvarna-motorcycles_2seg' with issue 'cluster_template_template_duplicate_title_tag': Observed on 412 URLs across 151 templates. Primary concentration in 'tpl_brand_husqvarna-motorcycles_2seg' (4 pages affected, 1.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_husqvarna-motorcycles_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250
- https://www.drivio.in/one-electric-motorcycles/kridn
- https://www.drivio.in/scooters/hero
- https://www.drivio.in/Harley-Davidson-bikes
- https://www.drivio.in/Triumph-bikes

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template duplicate title tag on affected pages.

Target Location: templates/tpl_brand_husqvarna-motorcycles_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_husqvarna-motorcycles_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_husqvarna-motorcycles_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250, https://www.drivio.in/one-electric-motorcycles/kridn, https://www.drivio.in/scooters/hero.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
