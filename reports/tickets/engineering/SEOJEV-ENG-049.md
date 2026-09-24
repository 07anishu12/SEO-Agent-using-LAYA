# [SEOJEV-ENG-049] [SEOJEV-ENG-049] Routine hygiene cleanup: review template template template long title truncated ...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_husqvarna-motorcycles_2seg' with issue 'cluster_template_template_template_long_title_truncated': Observed on 84 URLs across 42 templates. Primary concentration in 'tpl_brand_husqvarna-motorcycles_2seg' (2 pages affected, 2.4% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_husqvarna-motorcycles_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250
- https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110
- https://www.drivio.in/aeroride/e-spark
- https://www.drivio.in/amo-electric/inspirer
- https://www.drivio.in/avon/e-mate

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template template template long title truncated on affected pages.

Target Location: templates/tpl_brand_husqvarna-motorcycles_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_husqvarna-motorcycles_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_husqvarna-motorcycles_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250, https://www.drivio.in/compare/hero-splendor-plus-vs-bajaj-platina-110, https://www.drivio.in/aeroride/e-spark.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
