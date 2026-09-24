# [SEOJEV-ENG-038] [SEOJEV-ENG-038] Routine hygiene cleanup: review template template missing image alt on affected ...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_husqvarna-motorcycles_2seg' with issue 'cluster_template_template_missing_image_alt': Observed on 373 URLs across 83 templates. Primary concentration in 'tpl_brand_husqvarna-motorcycles_2seg' (5 pages affected, 1.3% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_husqvarna-motorcycles_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250
- https://www.drivio.in/reviews/10-most-popular-sub-200cc-naked-bikes-in-india
- https://www.drivio.in/scooters/hero
- https://www.drivio.in/indian/chieftain-elite
- https://www.drivio.in/reviews/bajaj-pulsar-125-review-2025-ultimate-buying-guide-for-the-best-125cc-bike-in-india

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template missing image alt on affected pages.

Target Location: templates/tpl_brand_husqvarna-motorcycles_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_husqvarna-motorcycles_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_husqvarna-motorcycles_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250, https://www.drivio.in/reviews/10-most-popular-sub-200cc-naked-bikes-in-india, https://www.drivio.in/scooters/hero.

**Automated Verification Spec:**
```
status_code == 200
```
