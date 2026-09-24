# [SEOJEV-ENG-015] [SEOJEV-ENG-015] Routine hygiene cleanup: review entity conflict title h1 on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (4 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 4 URLs in template 'tpl_model_bikes_4seg' with issue 'cluster_entity_conflict_title_h1': Observed on 690 URLs across 1 templates. Primary concentration in 'None' (690 pages affected, 100.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_bikes_4seg.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/hero/splendor-plus/reviews
- https://www.drivio.in/bikes/hero/hf-deluxe/reviews
- https://www.drivio.in/bikes/hero/passion-pro/reviews
- https://www.drivio.in/bikes/honda/shine/reviews

---

### Required Implementation
Action Required: Routine hygiene cleanup: review entity conflict title h1 on affected pages.

Target Location: templates/tpl_model_bikes_4seg.html
Scope: Template (4 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_bikes_4seg systematically remedies all 4 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_bikes_4seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/hero/splendor-plus/reviews, https://www.drivio.in/bikes/hero/hf-deluxe/reviews, https://www.drivio.in/bikes/hero/passion-pro/reviews.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
