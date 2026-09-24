# [SEOJEV-ENG-128] [SEOJEV-ENG-128] Routine hygiene cleanup: review low text to html ratio on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_model_bikes_4seg' with issue 'cluster_low_text_to_html_ratio': Observed on 281 URLs across 147 templates. Primary concentration in 'tpl_model_bikes_4seg' (122 pages affected, 43.4% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_bikes_4seg.

**Sample Affected URLs:**
- https://www.drivio.in/22motors-scooters
- https://www.drivio.in/aeroride-ev
- https://www.drivio.in/aftek-motors-scooters
- https://www.drivio.in/amo-electric-ev
- https://www.drivio.in/ampere-ev

---

### Required Implementation
Action Required: Routine hygiene cleanup: review low text to html ratio on affected pages.

Target Location: templates/tpl_model_bikes_4seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_bikes_4seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_bikes_4seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/22motors-scooters, https://www.drivio.in/aeroride-ev, https://www.drivio.in/aftek-motors-scooters.

**Automated Verification Spec:**
```
status_code == 200
```
