# [SEOJEV-CONTENT-2041] [SEOJEV-CONTENT-2041] Add entity-clear product name in <title>/<h1>, structured specification sum...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy') >= 60`.
- [ ] Validated on sample URLs: https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy.

**Automated Verification Spec:**
```
entity_clarity_score('https://www.drivio.in/featured-stories/aprilia-rs-457-vs-yamaha-r3-vs-kawasaki-ninja-500-which-twin-should-you-buy') >= 60
```
