# TidyCSV

Clean messy CSV files **in your browser**. Duplicates, whitespace, empty rows,
broken headers, suspicious emails and mixed date formats - fixed locally.
Your file never leaves your device.

## Why it exists

CSV exports from Shopify, Airtable, HubSpot, Salesforce and Google Sheets often
arrive broken (bad emails, duplicates, mixed dates, lost headers) and cleaning
them by hand costs 60+ minutes per file. Six paid products charge $9-29/month or
$8.99-49.99 per job for exactly this. TidyCSV does the common fixes client-side
for free and sells a **$9 one-time unlock** for the full clean export.

## Use it

Open `index.html` in any browser (double-click, or serve statically):

```
python -m http.server 8000
# then visit http://localhost:8000/
```

1. Drop a `.csv` file (parsing happens in this tab - no upload).
2. Review the issue report (rule-by-rule counts + details).
3. Check the cleaned preview and clean-up notes.
4. Click **Unlock clean export - $9 one-time**, then **Download cleaned CSV**.

### Pricing honesty

Checkout activates as soon as payments are connected (first demand signal).
Until then the download stays open during launch - the $9 unlock is how you pay
if the tool saved you time. No account, no subscription, no dark patterns.

## Run the core locally

The same rules ship as a Python standard-library CLI:

```
python tidycsv.py input.csv                 # print issue report + clean-up steps
python tidycsv.py input.csv -o clean.csv    # also write the cleaned file
python tidycsv.py input.csv --report-only   # report only
```

## Rules implemented

| Rule | Detects | Auto-fix |
| --- | --- | --- |
| `empty_rows` | entirely empty rows | drop |
| `duplicate_rows` | repeated rows (whitespace-insensitive) | keep first |
| `whitespace` | leading/trailing spaces in cells | strip |
| `header_noise` | blank or duplicate column names | name / suffix |
| `invalid_email` | bad addresses in `*email*` columns or cells with `@` | report only |
| `mixed_dates` | columns mixing `YYYY-MM-DD`, `DD/MM/YYYY`, `DD.MM.YYYY` | normalize to ISO **only when unambiguous** |

Ambiguous dates (`03/04/2024`) are **never** silently rewritten - we do not guess
whether you meant March 4 or April 3.

## Tests

```
python test_tidycsv.py     # 28 tests: parsing, detection, fixes, ISO dates, CLI
python test_site.py        # 22 tests: 9 pages, canonical/sitemap/robots,
                           #           local-only assets, event allowlist,
                           #           Node syntax + browser/Python core parity
```

## Pages in this site

| File | What it is |
| --- | --- |
| `index.html` | the full tool (drop a file, issue report, cleaned preview, unlock) |
| `LANDING.html` | pricing / launch page |
| `clean-csv-online.html` | primary free cleaner page (functional) |
| `remove-duplicate-csv-rows.html` | dedupe page (functional) |
| `fix-malformed-csv.html` | structure repair page (functional) |
| `csv-column-cleanup.html` | whitespace + header cleanup page (functional) |
| `csv-delimiter-conversion.html` | delimiter converter (functional, mode `delimiter`) |
| `csv-encoding-problems.html` | BOM / mojibake repair (functional, mode `encoding`) |
| `clean-csv-data.html`, `csv-formatting-tool.html`, `fix-broken-csv-file.html` | how-to guides (article + links into the tools) |
| `sitemap.xml`, `robots.txt` | crawl configuration for the 9 pages above |

Every functional page really runs: `tidycsv.js` (shared core) + `seo-tool.js`
(widget) + `site.css`. Guides are articles only.

## Measurement (no third-party analytics)

Static GitHub Pages have no access logs we can reach and no server to receive
events, and the product tests forbid remote resources. Measurement therefore is:

1. **GitHub traffic API** for the repository (views/clones, fetched with `gh`).
2. **`zf-track.js`** - a client-side session log in the visitor's browser
   (allowlisted funnel events only, no cookies, nothing sent anywhere). The
   visitor (or owner) exports the JSON from the badge at the bottom right and
   imports it with:
   ```
   python -m zeroforge track-session --experiment exp_006 --file session.json
   ```
   Imported numbers are labelled *client-side session log*, never server-measured.

## Design notes

- Zero dependencies: Python standard library + static HTML/JS/CSS files.
- Zero serving cost: static hosting only, no backend, no database.
- No tracking pixels, no CDNs, no third-party scripts (asserted by the tests).
- Honorable gating: the export button unlocks in the UI; there is no server to
  enforce payment yet (documented deliberately - enforcement comes with checkout).

Part of the ZeroForge zero-cash product factory. See `LANDING.html` for the
launch page and `../csv-fix-service/` for the done-for-you variant.
