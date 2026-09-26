# [SEOJEV-CONTENT-030] [SEOJEV-CONTENT-030] Add entity-clear product name in <title>/<h1>, structured specification summ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
GEO readiness score for http://127.0.0.1:8899/sitemap-dead-page is 25.0/100. Gaps: entity naming/disambiguation and citation-ready fact density.

Diagnosis: Page lacks the structured entity signals and factual density required for confident citation by generative AI engines (SGE, Perplexity, Bing Copilot).

**Sample Affected URLs:**
- http://127.0.0.1:8899/sitemap-dead-page

---

### Required Implementation
Action Required: Add entity-clear product name in <title>/<h1>, structured specification summary, and authoritative source references. Gaps: entity naming/disambiguation and citation-ready fact density.

Target Location: Page head + main content on http://127.0.0.1:8899/sitemap-dead-page
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding entity disambiguation markup, factual summaries, and authoritative citations increases probability of AI citation and generative-search visibility.

---

### Acceptance Criteria
- [ ] Implementation updated in `Page head + main content on http://127.0.0.1:8899/sitemap-dead-page`.
- [ ] Verification spec evaluates to true: `entity_clarity_score('http://127.0.0.1:8899/sitemap-dead-page') >= 60`.
- [ ] Validated on sample URLs: http://127.0.0.1:8899/sitemap-dead-page.

**Automated Verification Spec:**
```
entity_clarity_score('http://127.0.0.1:8899/sitemap-dead-page') >= 60
```
