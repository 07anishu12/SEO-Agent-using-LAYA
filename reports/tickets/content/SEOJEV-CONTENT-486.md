# [SEOJEV-CONTENT-486] [SEOJEV-CONTENT-486] Add entity-clear product name in <title>/<h1>, structured specification summ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know') >= 60`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know.

**Automated Verification Spec:**
```
entity_clarity_score('https://drivio.in/featured-stories/2025-yamaha-mt-15-top-5-highlights-that-every-rider-needs-to-know') >= 60
```
