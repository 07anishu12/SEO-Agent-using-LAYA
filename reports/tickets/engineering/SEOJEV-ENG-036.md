# [SEOJEV-ENG-036] [SEOJEV-ENG-036] Routine hygiene cleanup: review multiple h1 on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_model_bikes_4seg' with issue 'cluster_multiple_h1': Observed on 393 URLs across 21 templates. Primary concentration in 'tpl_model_bikes_4seg' (337 pages affected, 85.8% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_bikes_4seg.

**Sample Affected URLs:**
- https://www.drivio.in/news/ather-konarc-launched-at-99-999-can-it-be-the-best-electric-replacement-for-your-petrol-bike
- https://drivio.in/news/ather-konarc-launched-at-99-999-can-it-be-the-best-electric-replacement-for-your-petrol-bike
- https://www.drivio.in/bikes/best
- https://www.drivio.in/bikes/latest
- https://www.drivio.in/electric-vehicles/latest

---

### Required Implementation
Action Required: Routine hygiene cleanup: review multiple h1 on affected pages.

Target Location: templates/tpl_model_bikes_4seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_bikes_4seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_bikes_4seg.html`.
- [ ] Verification spec evaluates to true: `selector_count("h1") == 1`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/ather-konarc-launched-at-99-999-can-it-be-the-best-electric-replacement-for-your-petrol-bike, https://drivio.in/news/ather-konarc-launched-at-99-999-can-it-be-the-best-electric-replacement-for-your-petrol-bike, https://www.drivio.in/bikes/best.

**Automated Verification Spec:**
```
selector_count("h1") == 1
```
