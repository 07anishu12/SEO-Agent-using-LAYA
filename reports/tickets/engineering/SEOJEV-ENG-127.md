# [SEOJEV-ENG-127] [SEOJEV-ENG-127] Routine hygiene cleanup: review long url on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_featured-stories_2seg' with issue 'cluster_long_url': Observed on 972 URLs across 18 templates. Primary concentration in 'tpl_brand_featured-stories_2seg' (180 pages affected, 18.5% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_featured-stories_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer
- https://www.drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category
- https://www.drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know
- https://www.drivio.in/featured-stories/2024-yezdi-roadking-500-launch-soon-exciting-must-know-aspects
- https://www.drivio.in/featured-stories/60-70km-daily-commute-we-help-you-choose-between-an-e-scooter-and-a-petrol-one

---

### Required Implementation
Action Required: Routine hygiene cleanup: review long url on affected pages.

Target Location: templates/tpl_brand_featured-stories_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_featured-stories_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer, https://www.drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category, https://www.drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know.

**Automated Verification Spec:**
```
status_code == 200
```
