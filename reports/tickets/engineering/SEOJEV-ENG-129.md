# [SEOJEV-ENG-129] [SEOJEV-ENG-129] Routine hygiene cleanup: review page has nofollow on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_listing_hero_2seg' with issue 'cluster_page_has_nofollow': Observed on 95 URLs across 81 templates. Primary concentration in 'tpl_listing_hero_2seg' (6 pages affected, 6.3% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_listing_hero_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/22motors-scooters
- https://www.drivio.in/avan-motors-scooters
- https://www.drivio.in/avera-scooters-scooters
- https://www.drivio.in/bajaj-urbanite-scooters
- https://www.drivio.in/battre-electric-scooters-scooters

---

### Required Implementation
Action Required: Routine hygiene cleanup: review page has nofollow on affected pages.

Target Location: templates/tpl_listing_hero_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_listing_hero_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_listing_hero_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/22motors-scooters, https://www.drivio.in/avan-motors-scooters, https://www.drivio.in/avera-scooters-scooters.

**Automated Verification Spec:**
```
status_code == 200
```
