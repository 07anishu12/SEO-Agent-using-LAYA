# [SEOJEV-ENG-002] [SEOJEV-ENG-002] Immediate engineering blocker: resolve missing title across 25 URLs.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_category_battre-electric-scooters-scooters_1seg' with issue 'cluster_missing_title': Observed on 25 URLs across 25 templates. Primary concentration in 'tpl_category_battre-electric-scooters-scooters_1seg' (1 pages affected, 4.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_category_battre-electric-scooters-scooters_1seg.

**Sample Affected URLs:**
- https://www.drivio.in/battre-electric-scooters-scooters
- https://www.drivio.in/bird-scooters
- https://www.drivio.in/bsa-scooters
- https://www.drivio.in/devot-scooters
- https://www.drivio.in/dispatch-ev-scooters

---

### Required Implementation
Action Required: Immediate engineering blocker: resolve missing title across 25 URLs.

Target Location: templates/tpl_category_battre-electric-scooters-scooters_1seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_category_battre-electric-scooters-scooters_1seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_category_battre-electric-scooters-scooters_1seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/battre-electric-scooters-scooters, https://www.drivio.in/bird-scooters, https://www.drivio.in/bsa-scooters.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
