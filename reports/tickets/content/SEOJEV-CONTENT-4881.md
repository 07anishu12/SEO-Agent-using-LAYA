# [SEOJEV-CONTENT-4881] [SEOJEV-CONTENT-4881] Author missing sections (['on_road_price', 'variants', 'mileage', 'torque',...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://www.drivio.in/bikes/bajaj/pulsar-ns400z has content gaps: missing sections ['on_road_price', 'variants', 'mileage'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://www.drivio.in/bikes/bajaj/pulsar-ns400z

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'variants', 'mileage', 'torque', 'colors', 'pros', 'cons', 'comparison', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://www.drivio.in/bikes/bajaj/pulsar-ns400z
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://www.drivio.in/bikes/bajaj/pulsar-ns400z`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://www.drivio.in/bikes/bajaj/pulsar-ns400z', ['on_road_price', 'variants']) == True`.
- [ ] Validated on sample URLs: https://www.drivio.in/bikes/bajaj/pulsar-ns400z.

**Automated Verification Spec:**
```
content_sections_present('https://www.drivio.in/bikes/bajaj/pulsar-ns400z', ['on_road_price', 'variants']) == True
```
