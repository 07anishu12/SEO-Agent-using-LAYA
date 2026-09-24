# [SEOJEV-CONTENT-2105] [SEOJEV-CONTENT-2105] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/news/tvs-ntorq-125-disc-launched-at-82-500-tvs-sweetens-the-125cc-scooter-deal') >= 60
```
