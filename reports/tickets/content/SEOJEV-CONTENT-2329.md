# [SEOJEV-CONTENT-2329] [SEOJEV-CONTENT-2329] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/reviews/yamaha-mt-07-vs-triumph-trident-800-the-2026-middleweight-streetfighter-war') >= 60
```
