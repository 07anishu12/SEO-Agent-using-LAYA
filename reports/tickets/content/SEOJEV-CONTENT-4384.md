# [SEOJEV-CONTENT-4384] [SEOJEV-CONTENT-4384] Author missing sections (['variants', 'engine', 'power', 'torque', 'pros', ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/vespa/zx has content gaps: missing sections ['variants', 'engine', 'power'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/vespa/zx

---

### Required Implementation
Action Required: Author missing sections (['variants', 'engine', 'power', 'torque', 'pros', 'cons', 'comparison', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/vespa/zx
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/vespa/zx`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/vespa/zx', ['variants', 'engine']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/vespa/zx.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/vespa/zx', ['variants', 'engine']) == True
```
