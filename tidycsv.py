"""TidyCSV - CSV cleaning core (Python reference implementation).

Client-side friendly rules shared with index.html:
duplicate rows, whitespace, empty rows, header noise, invalid emails and
mixed date formats. Nothing here uploads or transmits anything.

Usage:
    python tidycsv.py input.csv [-o cleaned.csv] [--report-only]
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from dataclasses import dataclass

RULES = (
    "empty_rows",
    "duplicate_rows",
    "whitespace",
    "header_noise",
    "invalid_email",
    "mixed_dates",
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

DATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("iso", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("slash", re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")),
    ("dot", re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")),
)

DATE_LIKE_MIN_SHARE = 0.6


@dataclass
class Issue:
    rule: str
    row: int  # 1-based data row number; 0 for header issues
    column: str
    detail: str
    original: str = ""
    suggestion: str = ""


def parse(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV text into (headers, rows). Tolerates BOM and ragged rows."""
    if text.startswith("﻿"):
        text = text[1:]
    reader = csv.reader(io.StringIO(text))
    records = [list(r) for r in reader]
    while records and not any(cell.strip() for cell in records[0]):
        records.pop(0)  # skip blank lines before the header row
    if not records:
        return [], []
    headers = [cell.strip() for cell in records[0]]
    width = max(len(headers), 1)
    rows: list[list[str]] = []
    for record in records[1:]:
        fixed = list(record[:width]) + [""] * max(0, width - len(record))
        rows.append(fixed)
    return headers, rows


def _date_kind(cell: str) -> str | None:
    value = cell.strip()
    for name, pattern in DATE_PATTERNS:
        if pattern.match(value):
            return name
    return None


def _date_columns(headers: list[str], rows: list[list[str]]) -> dict[int, str]:
    """Map column index -> dominant date pattern name for date-like columns."""
    columns: dict[int, str] = {}
    for index in range(len(headers)):
        cells = [rows[r][index] for r in range(len(rows)) if index < len(rows[r])]
        non_empty = [c for c in cells if c.strip()]
        if len(non_empty) < 2:
            continue
        kinds = [k for k in (_date_kind(c) for c in non_empty) if k]
        if len(kinds) / len(non_empty) >= DATE_LIKE_MIN_SHARE and kinds:
            dominant = max(set(kinds), key=kinds.count)
            columns[index] = dominant
    return columns


def _mixes_patterns(values: list[str]) -> bool:
    kinds = {k for k in (_date_kind(v) for v in values) if k}
    return len(kinds) >= 2


def detect(headers: list[str], rows: list[list[str]]) -> list[Issue]:
    issues: list[Issue] = []
    seen_headers: dict[str, int] = {}
    for index, raw in enumerate(headers):
        name = raw.strip()
        column = f"col{index + 1}"
        if not name:
            issues.append(Issue("header_noise", 0, column, "blank header", "", f"name it column_{index + 1}"))
        elif name.lower() in seen_headers:
            issues.append(Issue("header_noise", 0, column, f"duplicate header '{name}'", name, f"'{name}_2'"))
        if name:
            seen_headers.setdefault(name.lower(), index)

    seen_rows: dict[tuple[str, ...], int] = {}
    for r, row in enumerate(rows, start=1):
        number = r
        if all(not cell.strip() for cell in row):
            issues.append(Issue("empty_rows", number, "-", "entirely empty row", "", "drop row"))
            continue
        key = tuple(cell.strip() for cell in row)
        if key in seen_rows:
            issues.append(Issue(
                "duplicate_rows", number, "-", f"row duplicates line {seen_rows[key]}", "", "keep first copy"
            ))
        else:
            seen_rows[key] = number
        for index, cell in enumerate(row):
            column = headers[index] if index < len(headers) and headers[index] else f"col{index + 1}"
            if cell != cell.strip() and cell.strip():
                issues.append(Issue(
                    "whitespace", number, column, "leading/trailing whitespace", cell, cell.strip()
                ))
            value = cell.strip()
            if not value:
                continue
            emailish = "email" in column.lower() or column.lower().endswith("mail")
            has_at = "@" in value
            if (emailish and not has_at) or (has_at and not EMAIL_RE.match(value)):
                issues.append(Issue(
                    "invalid_email", number, column, "does not look like a valid email", value, "fix manually"
                ))

    date_columns = _date_columns(headers, rows)
    for index, _kind in date_columns.items():
        column = headers[index] if index < len(headers) and headers[index] else f"col{index + 1}"
        values = [rows[r][index].strip() for r in range(len(rows))
                  if index < len(rows[r]) and rows[r][index].strip()]
        if _mixes_patterns(values):
            issues.append(Issue(
                "mixed_dates", 0, column,
                f"{len(values)} date cells use mixed formats (e.g. {', '.join(values[:3])})",
                "", "normalize to YYYY-MM-DD where unambiguous",
            ))
    return issues


def to_iso(cell: str) -> str | None:
    """Convert a date cell to ISO when the order is unambiguous; else None."""
    value = cell.strip()
    for name, pattern in DATE_PATTERNS:
        match = pattern.match(value)
        if not match:
            continue
        if name == "iso":
            return value
        if name == "slash":
            first, second, year = int(match.group(1)), int(match.group(2)), match.group(3)
        else:
            first, second, year = int(match.group(1)), int(match.group(2)), match.group(3)
        if first > 12:            # day must come first -> D/M/Y
            day, month = first, second
        elif second > 12:         # only month can come first -> M/D/Y
            month, day = first, second
        else:                     # ambiguous (both <= 12): leave untouched
            return None
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return None
        return f"{year}-{month:02d}-{day:02d}"
    return None


def clean(headers: list[str], rows: list[list[str]]) -> tuple[list[str], list[list[str]], list[str]]:
    """Apply fixes. Returns (headers, rows, notes). Invalid emails are only
    reported (never silently rewritten). Ambiguous dates are left as-is."""
    notes: list[str] = []
    new_headers: list[str] = []
    used: set[str] = set()
    for index, raw in enumerate(headers):
        name = raw.strip() or f"column_{index + 1}"
        base = name
        suffix = 2
        while name.lower() in used:
            name = f"{base}_{suffix}"
            suffix += 1
        if name != raw:
            notes.append(f"header col{index + 1}: {raw.strip() or '(blank)'} -> {name}")
        used.add(name.lower())
        new_headers.append(name)

    cleaned: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    dropped_empty = dropped_dupes = stripped = 0
    date_columns = _date_columns(headers, rows)
    converted = 0
    for row in rows:
        cells = [cell.strip() for cell in row]
        if all(not cell for cell in cells):
            dropped_empty += 1
            continue
        key = tuple(cells)
        if key in seen:
            dropped_dupes += 1
            continue
        seen.add(key)
        stripped += sum(1 for cell in row if cell != cell.strip())
        out: list[str] = []
        for index, value in enumerate(cells):
            if index in date_columns:
                iso = to_iso(value)
                if iso and iso != value:
                    value = iso
                    converted += 1
            out.append(value)
        cleaned.append(out)

    if stripped:
        notes.append(f"stripped whitespace from {stripped} cell(s)")
    if dropped_empty:
        notes.append(f"dropped {dropped_empty} empty row(s)")
    if dropped_dupes:
        notes.append(f"dropped {dropped_dupes} duplicate row(s)")
    if converted:
        notes.append(f"normalized {converted} unambiguous date cell(s) to YYYY-MM-DD")
    if not notes:
        notes.append("no changes needed")
    return new_headers, cleaned, notes


def render(headers: list[str], rows: list[list[str]], issues: list[Issue]) -> str:
    lines = ["TidyCSV report", "=" * 40, f"columns: {len(headers)}   rows: {len(rows)}", ""]
    if not issues:
        lines.append("No issues found.")
        return "\n".join(lines)
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.rule] = counts.get(issue.rule, 0) + 1
    lines.append("Issues by rule:")
    for rule in RULES:
        if rule in counts:
            lines.append(f"  {rule:<16} {counts[rule]}")
    lines.append("")
    lines.append("Details (first 50):")
    for issue in issues[:50]:
        where = f"row {issue.row} {issue.column}".strip()
        lines.append(f"  [{issue.rule}] {where}: {issue.detail}")
    if len(issues) > 50:
        lines.append(f"  ... {len(issues) - 50} more")
    return "\n".join(lines)


def to_csv(headers: list[str], rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect and clean issues in a CSV file.")
    parser.add_argument("input", help="path to the CSV file")
    parser.add_argument("-o", "--output", help="write cleaned CSV here")
    parser.add_argument("--report-only", action="store_true", help="print the issue report only")
    args = parser.parse_args(argv)
    try:
        with open(args.input, encoding="utf-8-sig", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"error: cannot read {args.input}: {exc}", file=sys.stderr)
        return 2
    headers, rows = parse(text)
    if not headers:
        print("error: no header row found", file=sys.stderr)
        return 2
    issues = detect(headers, rows)
    print(render(headers, rows, issues))
    if args.report_only:
        return 0
    clean_headers, clean_rows, notes = clean(headers, rows)
    print("\nClean-up steps:")
    for note in notes:
        print(f"  - {note}")
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as handle:
            handle.write(to_csv(clean_headers, clean_rows))
        print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
