# [SEOJEV-CONTENT-4428] [SEOJEV-CONTENT-4428] Author missing sections (['on_road_price', 'specifications', 'engine', 'pow...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/ktm/125-duke has content gaps: missing sections ['on_road_price', 'specifications', 'engine'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/ktm/125-duke

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'specifications', 'engine', 'power', 'torque', 'features', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/ktm/125-duke
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/ktm/125-duke`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/ktm/125-duke', ['on_road_price', 'specifications']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/ktm/125-duke.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/ktm/125-duke', ['on_road_price', 'specifications']) == True
```
