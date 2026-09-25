# TidyCSV - Zero-Cash Product Factory MVP

## Experiment design
- Hypothesis: organic visitors who scan their own CSV produce >=1 unlock/checkout CTA click within 72h.
- Target user: non-technical operators importing broken CSV exports (Shopify/Airtable/HubSpot/Sheets).
- Acquisition: organic zero-cost only (SEO landing, GitHub Pages, free directories, permitted communities, articles). No paid ads/marketplaces/DMs.
- Free MVP: browser-side CSV cleaner, nothing uploaded.
- Monetization: free issue preview + $9 one-time unlock (checkout activates only after payments connect; RED approval first).
- Success: >=1 checkout_start signal in 72h. Kill: 0 checkout clicks and 0 visitors at 72h.

## Build scope (MVP)
1. `tidycsv.py` - Python core (stdlib only): parse CSV, detect issues (duplicate rows,
   leading/trailing whitespace, empty rows, inconsistent date formats per column,
   invalid emails, blank/duplicate headers), apply fixes, emit issue report. CLI:
   `python tidycsv.py input.csv [-o clean.csv]`.
2. `test_tidycsv.py` - unittest covering every rule (must pass standalone).
3. `index.html` - single-file browser UI: file input, client-side parse + same rules,
   issue table preview, sample clean preview, "Unlock clean export - $9 one-time" CTA
   (honor-system gate: enables download button + shows checkout-activation notice).
   Privacy banner: files never leave the browser.
4. `README.md` - usage, pricing honesty (checkout activates when payments connected),
   test instructions, zero-infrastructure notes.

## Acceptance criteria
- `python test_tidycsv.py` passes from workspace root.
- `index.html` works offline as a static file (no network requests, no uploads).
- No secrets, no paid services, no third-party scripts/CDNs.
- Honest copy only: no fake testimonials, fake counts, or revenue claims.
