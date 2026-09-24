# [SEOJEV-ENG-042] [SEOJEV-ENG-042] Routine hygiene cleanup: review template long meta description on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_article_featured-stories_2seg' with issue 'cluster_template_long_meta_description': Observed on 216 URLs across 27 templates. Primary concentration in 'tpl_article_featured-stories_2seg' (8 pages affected, 3.7% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_article_featured-stories_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians
- https://www.drivio.in/news/2023-hero-xtreme-160r-incoming
- https://www.drivio.in/featured-stories/10-best-selling-bikes-in-2023
- https://www.drivio.in/featured-stories/10-reasons-why-two-wheelers-are-so-popular-in-rural-india
- https://www.drivio.in/news/2023-honda-cb200x-launched-in-india-at-rs1-46-999

---

### Required Implementation
Action Required: Routine hygiene cleanup: review template long meta description on affected pages.

Target Location: templates/tpl_article_featured-stories_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_article_featured-stories_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_article_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/10-best-two-wheeler-apps-for-indians, https://www.drivio.in/news/2023-hero-xtreme-160r-incoming, https://www.drivio.in/featured-stories/10-best-selling-bikes-in-2023.

**Automated Verification Spec:**
```
has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50
```
