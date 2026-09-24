# [SEOJEV-CONTENT-1808] [SEOJEV-CONTENT-1808] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/yamaha-fz-blue-flex-launched-in-india-at-rs-124-lakh-first-flex-fuel-fz') >= 60
```
