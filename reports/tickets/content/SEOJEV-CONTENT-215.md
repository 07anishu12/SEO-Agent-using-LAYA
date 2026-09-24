# [SEOJEV-CONTENT-215] [SEOJEV-CONTENT-215] Add entity-clear product name in <title>/<h1>, structured specification summ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/ather-rizta-and-kawasaki-versys-650-launched-ktm-250-duke-updated-and-more-two-wheeler-news-from-last-week') >= 60
```
