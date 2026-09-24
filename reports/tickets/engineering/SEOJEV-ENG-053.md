# [SEOJEV-ENG-053] [SEOJEV-ENG-053] Routine hygiene cleanup: review page has noindex on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_listing_hero_2seg' with issue 'cluster_page_has_noindex': Observed on 32 URLs across 16 templates. Primary concentration in 'tpl_listing_hero_2seg' (6 pages affected, 18.8% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_listing_hero_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110
- https://www.drivio.in/compare/royal-enfield-classic-350-vs-jawa-42-bobber
- https://www.drivio.in/compare/yamaha-fzs-fi-v3-vs-bajaj-pulsar-ns200
- https://www.drivio.in/compare/honda-shine-vs-hero-glamour
- https://www.drivio.in/compare/tvs-apache-rtr-160-4v-vs-bajaj-pulsar-150

---

### Required Implementation
Action Required: Routine hygiene cleanup: review page has noindex on affected pages.

Target Location: templates/tpl_listing_hero_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_listing_hero_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_listing_hero_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110, https://www.drivio.in/compare/royal-enfield-classic-350-vs-jawa-42-bobber, https://www.drivio.in/compare/yamaha-fzs-fi-v3-vs-bajaj-pulsar-ns200.

**Automated Verification Spec:**
```
status_code == 200
```
