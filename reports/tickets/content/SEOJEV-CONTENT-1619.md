# [SEOJEV-CONTENT-1619] [SEOJEV-CONTENT-1619] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/2026-kawasaki-ninja-250-launched-in-japan-what-it-means-for-ninja-300-buyers-in-india') >= 60
```
