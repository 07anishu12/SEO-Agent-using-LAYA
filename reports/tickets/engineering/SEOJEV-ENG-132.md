# [SEOJEV-ENG-132] [SEOJEV-ENG-132] Routine hygiene cleanup: review short meta description on affected pages.

**Type:** Engineering  
**Priority:** P2  
**Scope:** Template (5 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Observed 5 URLs in template 'tpl_brand_news_2seg' with issue 'cluster_short_meta_description': Observed on 6 URLs across 4 templates. Primary concentration in 'tpl_brand_news_2seg' (2 pages affected, 33.3% of total occurrences)..

Diagnosis: Template-level omission or formatting defect in component rendering tpl_brand_news_2seg.

**Sample Affected URLs:**
- https://www.drivio.in/news/auto-expo-2023-some-exciting-scooters-bikes-to-watch-out
- https://drivio.in/news/auto-expo-2023-some-exciting-scooters-bikes-to-watch-out
- https://www.drivio.in/campaign-form
- https://www.drivio.in/thunderbolt-ev
- https://www.drivio.in/reviews/hero-passion-pro-vs-bajaj-ct-110x-battle-of-the-110cc-commuters

---

### Required Implementation
Action Required: Routine hygiene cleanup: review short meta description on affected pages.

Target Location: templates/tpl_brand_news_2seg.html
Scope: Template (5 URLs affected)
Observed Hypothesis: Updating the template component for tpl_brand_news_2seg systematically remedies all 5 affected URLs in a single engineering change.

---

### Acceptance Criteria
- [ ] Implementation updated in `templates/tpl_brand_news_2seg.html`.
- [ ] Verification spec evaluates to true: `has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/auto-expo-2023-some-exciting-scooters-bikes-to-watch-out, https://drivio.in/news/auto-expo-2023-some-exciting-scooters-bikes-to-watch-out, https://www.drivio.in/campaign-form.

**Automated Verification Spec:**
```
has_selector("meta[name='description']") and text_length("meta[name='description'][content]") >= 50
```
