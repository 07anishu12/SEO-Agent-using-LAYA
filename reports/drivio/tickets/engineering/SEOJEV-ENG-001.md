# [SEOJEV-ENG-001] [SEOJEV-ENG-001] Immediate engineering blocker: resolve sitemap url has noindex across 68 URLs.

**Type:** Engineering  
**Priority:** P1  
**Scope:** Site (69 URLs)  
**Effort:** S  

---

### Problem & Observed Evidence
Site-level issue detected: GENERIC affecting site-wide crawl/index configuration.

Diagnosis: Site-wide configuration or architecture issue limiting global accessibility or search discovery.

**Sample Affected URLs:**
- Site-wide

---

### Required Implementation
Action Required: Immediate engineering blocker: resolve sitemap url has noindex across 68 URLs.

Target Location: Server configuration / robots.txt / sitemap.xml
Scope: Site (69 URLs affected)
Observed Hypothesis: Remediating this site-level configuration ensures search engines can reliably crawl and index core pages without obstruction.

---

### Acceptance Criteria
- [ ] Implementation updated in `Server configuration / robots.txt / sitemap.xml`.
- [ ] Verification spec evaluates to true: `check_site_config('GENERIC') == True`.
- [ ] Validated on sample URLs: Site URL.

**Automated Verification Spec:**
```
check_site_config('GENERIC') == True
```
