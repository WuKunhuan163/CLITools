# GOOGLE.GS — Agent Quick Reference

## Status: RESTRICTED (ToS Violation)

**Google Scholar's Terms of Service explicitly prohibit automated access.**
The CDMCP browser automation implementation was removed on 2026-03-17.

## ToS Compliance

Google Scholar operates under Google's unified Terms of Service which states:
> "Don't misuse our Services. For example, don't interfere with our Services
> or try to access them using a method other than the interface and the
> instructions that we provide."

Specific prohibitions include:
- Automated queries of any kind
- Use of robots, spiders, scrapers, or other automated technology
- Bypassing CAPTCHA or rate-limiting mechanisms

**Enforcement**: Google actively blocks automated requests after ~100-200 queries.
Users face CAPTCHA challenges and IP bans.

**robots.txt**: `scholar.google.com/robots.txt` blocks most bot activity.

### Decision Matrix Result

| Factor | Value |
|--------|-------|
| ToS prohibits automation | **Yes** (explicit) |
| Official API exists | **No** (Search Researcher API is restricted to approved academics) |
| Decision | **Do NOT build CDMCP automation** |

## Alternatives

### Free / Open APIs (no ToS issues)

| API | URL | Notes |
|-----|-----|-------|
| Semantic Scholar | https://api.semanticscholar.org/ | Free, 100 req/sec, excellent coverage |
| OpenAlex | https://openalex.org/ | Free, open, 100k works/day |
| Crossref | https://api.crossref.org/ | Free with polite pool, DOI-based |
| CORE | https://core.ac.uk/services/api | Free for non-commercial, open access |

### Paid APIs (structured Google Scholar data)

| API | URL | Notes |
|-----|-----|-------|
| SerpAPI | https://serpapi.com/google-scholar-api | Paid, most complete GS mirror |
| ScrapingBee | https://www.scrapingbee.com/ | Paid, proxy rotation |

### Restricted Access

| API | URL | Notes |
|-----|-----|-------|
| Google Search Researcher API | https://support.google.com/websearch/answer/13856826 | Accredited academics only, 1000 queries/day |

## Recommendation

For academic paper search functionality, integrate **Semantic Scholar API** as
the primary provider (free, high-quality, ToS-compliant). Add **OpenAlex** as a
secondary source. If Google Scholar-specific data is required, use **SerpAPI**
(requires paid subscription).

## Preserved Exploration Data

The `data/exploration/scholar_elements.json` file documents the DOM structure
explored during the original CDMCP development. This is preserved as reference
material for understanding Google Scholar's UI, not for automation.

## Original CLI Commands (now disabled)

The following commands existed in the CDMCP implementation:

| Command | Description | Status |
|---------|-------------|--------|
| `GS search <query>` | Search papers | **Removed** |
| `GS results` | Re-read current results | **Removed** |
| `GS next` / `GS prev` | Navigate pages | **Removed** |
| `GS cite --index N` | Get citation formats | **Removed** |
| `GS cited-by --index N` | Find citing papers | **Removed** |
| `GS pdf --index N` | Get PDF URL | **Removed** |
| `GS profile` | View user's profile | **Removed** |
| `GS library` | View saved papers | **Removed** |
| `GS author <name>` | Search author profiles | **Removed** |
