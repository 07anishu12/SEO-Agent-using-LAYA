# [SEOJEV-CONTENT-2113] [SEOJEV-CONTENT-2113] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/tvs-ronin-agonda-edition-launched-at-131-lakh-beach-inspired-retro-roadster') >= 60
```
