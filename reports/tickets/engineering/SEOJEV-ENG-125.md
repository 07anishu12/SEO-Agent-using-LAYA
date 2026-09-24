# [SEOJEV-ENG-125] [SEOJEV-ENG-125] Routine hygiene cleanup: review long title truncated on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_model_bikes_3seg' with issue 'cluster_long_title_truncated': Observed on 2,035 URLs across 278 templates. Primary concentration in 'tpl_model_bikes_3seg' (281 pages affected, 13.8% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_bikes_3seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer
- https://www.drivio.in/featured-stories/2023-royal-enfield-bullet-350-whats-new
- https://www.drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category
- https://www.drivio.in/featured-stories/60-70km-daily-commute-we-help-you-choose-between-an-e-scooter-and-a-petrol-one
- https://www.drivio.in/featured-stories/accessorize-and-upgrade-12-must-have-add-ons-for-the-royal-enfield-meteor-350

---

### Required Implementation
Action Required: Routine hygiene cleanup: review long title truncated on affected pages.

Target Location: templates/tpl_model_bikes_3seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_bikes_3seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_bikes_3seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer, https://www.drivio.in/featured-stories/2023-royal-enfield-bullet-350-whats-new, https://www.drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
