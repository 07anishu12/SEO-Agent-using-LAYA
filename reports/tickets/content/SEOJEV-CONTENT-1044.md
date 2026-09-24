# [SEOJEV-CONTENT-1044] [SEOJEV-CONTENT-1044] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/royal-enfield-introduces-price-hike-across-its-range-of-motorcycles') >= 60
```
