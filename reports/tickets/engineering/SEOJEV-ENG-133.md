# [SEOJEV-ENG-133] [SEOJEV-ENG-133] Routine hygiene cleanup: review uppercase in url on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (4 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 4 URLs in template 'tpl_article_featured-stories_2seg' with issue 'cluster_uppercase_in_url': Observed on 4 URLs across 3 templates. Primary concentration in 'tpl_article_featured-stories_2seg' (2 pages affected, 50.0% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_article_featured-stories_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/Hero Glamour
- https://www.drivio.in/featured-stories/Hero Splendor Plus
- https://www.drivio.in/Harley-Davidson-bikes
- https://www.drivio.in/Triumph-bikes

---

### Required Implementation
Action Required: Routine hygiene cleanup: review uppercase in url on affected pages.

Target Location: templates/tpl_article_featured-stories_2seg.html
Scope: Template (4 URLs affected)
Observed Hypothesis: Updating the template component for tpl_article_featured-stories_2seg systematically remedies all 4 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_article_featured-stories_2seg.html`.
- [ ] Verification spec evaluates to true: `status_code == 200`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/Hero Glamour, https://www.drivio.in/featured-stories/Hero Splendor Plus, https://www.drivio.in/Harley-Davidson-bikes.

**Automated Verification Spec:**
```
status_code == 200
```
