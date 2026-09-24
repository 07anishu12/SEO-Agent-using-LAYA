# [SEOJEV-ENG-126] [SEOJEV-ENG-126] Routine hygiene cleanup: review long meta description on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_featured-stories_2seg' with issue 'cluster_long_meta_description': Observed on 1,421 URLs across 152 templates. Primary concentration in 'tpl_brand_featured-stories_2seg' (172 pages affected, 12.1% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_featured-stories_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians
- https://www.drivio.in/featured-stories/10-reasons-why-a-two-wheeler-training-course-will-help-you
- https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer
- https://www.drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know
- https://www.drivio.in/featured-stories/ather-rizta-to-debut-on-april-6-check-how-to-book-the-family-electric-scooter

---

### Required Implementation
Action Required: Routine hygiene cleanup: review long meta description on affected pages.

Target Location: templates/tpl_brand_featured-stories_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_featured-stories_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians, https://www.drivio.in/featured-stories/10-reasons-why-a-two-wheeler-training-course-will-help-you, https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer.

**Automated Verification Spec:**
```
has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50
```
