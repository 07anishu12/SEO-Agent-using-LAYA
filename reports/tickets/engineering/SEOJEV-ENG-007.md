# [SEOJEV-ENG-007] [SEOJEV-ENG-007] Important architectural improvement: revise Individual page content / route hand...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_listing_hero_2seg' with issue 'cluster_empty_h1': Observed on 31 URLs across 17 templates. Primary concentration in 'tpl_listing_hero_2seg' (6 pages affected, 19.4% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_listing_hero_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/22motors/jawatest1
- https://www.drivio.in/ampere/magnus-ex
- https://www.drivio.in/aprilia/sxr-160
- https://www.drivio.in/aprilia/aprilia-rs-457
- https://www.drivio.in/aprilia/sr-160

---

### Required Implementation
Action Required: Important architectural improvement: revise Individual page content / route handlers to supply unique structured content.

Target Location: templates/tpl_listing_hero_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_listing_hero_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_listing_hero_2seg.html`.
- [ ] Verification spec evaluates to true: `selector_count("h1") == 1`.
- [ ] Validated on sample URLs: https://www.drivio.in/22motors/jawatest1, https://www.drivio.in/ampere/magnus-ex, https://www.drivio.in/aprilia/sxr-160.

**Automated Verification Spec:**
```
selector_count("h1") == 1
```
