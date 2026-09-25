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
python test_tidycsv.py
```

28 tests cover parsing (BOM, quotes, ragged rows), every detection rule, every
clean-up fix, ISO conversion edge cases and the CLI.

## Design notes

- Zero dependencies: Python standard library + one static HTML file.
- Zero serving cost: static hosting only, no backend, no database.
- No tracking pixels, no CDNs, no third-party scripts.
- Honorable gating: the export button unlocks in the UI; there is no server to
  enforce payment yet (documented deliberately - enforcement comes with checkout).

Part of the ZeroForge zero-cash product factory. See `LANDING.html` for the
launch page and `../csv-fix-service/` for the done-for-you variant.
