# [SEOJEV-ENG-028] [SEOJEV-ENG-028] Routine hygiene cleanup: review template duplicate meta description on affected ...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_article_featured-stories_2seg' with issue 'cluster_template_duplicate_meta_description': Observed on 1,131 URLs across 187 templates. Primary concentration in 'tpl_article_featured-stories_2seg' (7 pages affected, 0.6% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_article_featured-stories_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians
- https://www.drivio.in/news/2023-hero-xtreme-160r-incoming
- https://www.drivio.in/bikes/honda
- https://www.drivio.in/featured-stories/10-best-selling-bikes-in-2023
- https://www.drivio.in/husqvarna-motorcycles/husqvarna-svartpilen-250

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template duplicate meta description on affected pages.

Target Location: templates/tpl_article_featured-stories_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_article_featured-stories_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_article_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians, https://www.drivio.in/news/2023-hero-xtreme-160r-incoming, https://www.drivio.in/bikes/honda.

**Automated Verification Spec:**
```
has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50
```
