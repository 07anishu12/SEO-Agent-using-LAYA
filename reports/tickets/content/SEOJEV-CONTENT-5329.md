# [SEOJEV-CONTENT-5329] [SEOJEV-CONTENT-5329] Author missing sections (['on_road_price', 'mileage', 'power', 'torque', 'p...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** M  

---

### Problem & Observed Evidence
Page https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026 has content gaps: missing sections ['on_road_price', 'mileage', 'power'] and missing specifications [].

Diagnosis: Thin entity coverage compared to expected vertical baseline reduces topical completeness and satisfaction of search intent.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026

---

### Required Implementation
Action Required: Author missing sections (['on_road_price', 'mileage', 'power', 'torque', 'pros', 'cons', 'emi', 'faqs', 'reviews']) and add spec rows for [].

Target Location: Editorial content on https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026
Scope: Page (1 URLs affected)
Observed Hypothesis: Adding structured specification tables and required editorial sections provides comprehensive answers for user purchase queries.

---

### Acceptance Criteria
- [ ] Implementation updated in `Editorial content on https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026`.
- [ ] Verification spec evaluates to true: `content_sections_present('https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026', ['on_road_price', 'mileage']) == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026.

**Automated Verification Spec:**
```
content_sections_present('https://drivio.in/featured-stories/yamaha-aerox-155-colours-specs-and-version-s-guide-2026', ['on_road_price', 'mileage']) == True
```
