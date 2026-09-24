# [SEOJEV-ENG-006] [SEOJEV-ENG-006] High-impact fix: update tpl_article_featured-stories_2seg layout to resolve http...

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_article_featured-stories_2seg' with issue 'cluster_http_404_error': Observed on 8 URLs across 5 templates. Primary concentration in 'tpl_article_featured-stories_2seg' (2 pages affected, 25.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_article_featured-stories_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/Hero Glamour
- https://www.drivio.in/featured-stories/Hero Splendor Plus
- https://www.drivio.in/featured-stories/drivio.in/jawa/perak
- https://www.drivio.in/featured-stories/drivio.in/yamaha/r15-v4
- https://www.drivio.in/news/drivio.in/bajaj/dominar-250

---

### Required Implementation
Action Required: High-impact fix: update tpl_article_featured-stories_2seg layout to resolve http 404 error across 8 pages.

Target Location: templates/tpl_article_featured-stories_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_article_featured-stories_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_article_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/Hero Glamour, https://www.drivio.in/featured-stories/Hero Splendor Plus, https://www.drivio.in/featured-stories/drivio.in/jawa/perak.

**Automated Verification Spec:**
```
status_code == 200
```
