# [SEOJEV-ENG-017] [SEOJEV-ENG-017] Routine hygiene cleanup: review entity conflict title h1 on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
Observed 1 URLs in template 'tpl_model_news_2seg' with issue 'cluster_entity_conflict_title_h1': Observed on 690 URLs across 1 templates. Primary concentration in 'None' (690 pages affected, 100.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_model_news_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant

---

### Required Implementation
Action Required: Routine hygiene cleanup: review entity conflict title h1 on affected pages.

Target Location: templates/tpl_model_news_2seg.html
Scope: Template (1 URLs affected)
Observed Hypothesis: Updating the template component for tpl_model_news_2seg systematically remedies all 1 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_model_news_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("title") and text_length("title") >= 10`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/weekly-rewind-honda-cb350-launch-to-spying-of-bajaj-ct150x-and-trial-run-of-athers-new-variant.

**Automated Verification Spec:**
```
has_selector("title") and text_length("title") >= 10
```
