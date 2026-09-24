# [SEOJEV-ENG-120] [SEOJEV-ENG-120] High-impact fix: update tpl_brand_featured-stories_2seg layout to resolve canoni...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_featured-stories_2seg' with issue 'cluster_canonical_mismatch': Observed on 1,146 URLs across 24 templates. Primary concentration in 'tpl_brand_featured-stories_2seg' (183 pages affected, 16.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_featured-stories_2seg.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians
- https://drivio.in/featured-stories/2023-honda-dio-is-it-still-relevant-as-a-modern-moto-scooter
- https://drivio.in/featured-stories/10-reasons-why-a-two-wheeler-training-course-will-help-you
- https://drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer
- https://drivio.in/featured-stories/2023-royal-enfield-bullet-350-whats-new

---

### Required Implementation
Action Required: High-impact fix: update tpl_brand_featured-stories_2seg layout to resolve canonical mismatch across 1146 pages.

Target Location: templates/tpl_brand_featured-stories_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_featured-stories_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `canonical_matches_url == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians, https://drivio.in/featured-stories/2023-honda-dio-is-it-still-relevant-as-a-modern-moto-scooter, https://drivio.in/featured-stories/10-reasons-why-a-two-wheeler-training-course-will-help-you.

**Automated Verification Spec:**
```
canonical_matches_url == True
```
