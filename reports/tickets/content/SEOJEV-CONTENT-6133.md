# [SEOJEV-CONTENT-6133] [SEOJEV-CONTENT-6133] Add an explicit FAQ / summary section formatted with direct answers (under ...

**Type:** Content  
**Priority:** P2  
**Scope:** Page (1 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
AEO answer extractability score for https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category is 20.0/100. Missing concise definitions and Q&A formatting.

Diagnosis: Content lacks extractable single-sentence factual answers required by AI search assistants and featured snippets.

**Sample Affected URLs:**
- https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category

---

### Required Implementation
Action Required: Add an explicit FAQ / summary section formatted with direct answers (under 45 words) preceding detailed explanations.

Target Location: FAQ section on https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category
Scope: Page (1 URLs affected)
Observed Hypothesis: Structuring core product FAQs into clear Q&A pairs with direct answer sentences increases probability of snippet extraction.

---

### Acceptance Criteria
- [ ] Implementation updated in `FAQ section on https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category`.
- [ ] Verification spec evaluates to true: `has_qa_section('https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category') == True`.
- [ ] Validated on sample URLs: https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category.

**Automated Verification Spec:**
```
has_qa_section('https://drivio.in/featured-stories/2023-yamaha-ray-zr-125-yamahas-razor-sharp-take-on-the-125cc-scooter-category') == True
```
