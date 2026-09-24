# [SEOJEV-ENG-124] [SEOJEV-ENG-124] Routine hygiene cleanup: review missing image dimensions on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_article_news_2seg' with issue 'cluster_missing_image_dimensions': Observed on 5,001 URLs across 411 templates. Primary concentration in 'tpl_article_news_2seg' (494 pages affected, 9.9% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_article_news_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians
- https://www.drivio.in/featured-stories/10-reasons-why-a-two-wheeler-training-course-will-help-you
- https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer
- https://www.drivio.in/featured-stories/2023-honda-dio-is-it-still-relevant-as-a-modern-moto-scooter
- https://www.drivio.in/featured-stories/2023-royal-enfield-bullet-350-whats-new

---

### Required Implementation
Action Required: Routine hygiene cleanup: review missing image dimensions on affected pages.

Target Location: templates/tpl_article_news_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_article_news_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_article_news_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians, https://www.drivio.in/featured-stories/10-reasons-why-a-two-wheeler-training-course-will-help-you, https://www.drivio.in/featured-stories/2023-hero-maestro-edge-know-what-hero-motocorps-best-selling-scooter-has-to-offer.

**Automated Verification Spec:**
```
status_code == 200
```
