# [SEOJEV-CONTENT-1650] [SEOJEV-CONTENT-1650] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/bajaj-chetak-3001-launched-in-india-price-features-and-competitors') >= 60
```
