"""Work out the layout of an unfamiliar workbook: sheet, header row, and which
column holds the goods descriptions.

Nothing about the layout is assumed. Files from different exporters put the
description in different columns, with the headers on different rows, under
different names - so it is measured per file rather than configured.

    from detect import detect_layout
    layout = detect_layout(sheet)      # -> Layout(header_row=2, column=10, ...)

The heuristic alone is usually right. When the top two candidates are close,
and an AI backend is available, the model is asked to break the tie - it sees
only the header names and a couple of sample values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from clean_flavour import has_vietnamese

MAX_HEADER_SCAN = 15         # headers are never further down than this
SAMPLE_ROWS = 40             # rows sampled per column when scoring
_CODE_RE = re.compile(r"\b[A-Za-z]{1,5}\s*-\s*\d{1,6}\b|\b[A-Za-z]{1,5}\d{2,6}\b")


@dataclass(frozen=True)
class Layout:
    header_row: int
    column: int
    header_name: str
    confidence: float
    runner_up: str | None
    reason: str


def _cells(sheet, column: int, start: int, limit: int = SAMPLE_ROWS) -> list[str]:
    values = []
    for row in range(start, min(sheet.max_row, start + limit * 3) + 1):
        value = sheet.cell(row, column).value
        if value is not None and str(value).strip():
            values.append(str(value).strip())
        if len(values) >= limit:
            break
    return values


def find_header_row(sheet) -> int:
    """The header row is the last mostly-text row before the data starts."""
    best, best_score = 1, -1.0

    for row in range(1, min(MAX_HEADER_SCAN, sheet.max_row) + 1):
        labels = [
            sheet.cell(row, c).value for c in range(1, sheet.max_column + 1)]
        text = [v for v in labels
                if isinstance(v, str) and v.strip() and len(v.strip()) < 60]
        if len(text) < 2:
            continue

        # A header row is followed by rows that are at least as populated.
        below = 0
        for probe in range(row + 1, min(row + 6, sheet.max_row) + 1):
            below += sum(
                1 for c in range(1, sheet.max_column + 1)
                if sheet.cell(probe, c).value not in (None, ""))
        if below < len(text):
            continue

        # Prefer the lowest qualifying row: a title above real headers
        # scores worse because it has fewer filled cells.
        score = len(text) + row * 0.01
        if score > best_score:
            best, best_score = row, score

    return best


def score_column(values: list[str]) -> tuple[float, str]:
    """How much this column looks like free-text goods descriptions."""
    if not values:
        return 0.0, "empty"

    lengths = sorted(len(v) for v in values)
    median = lengths[len(lengths) // 2]
    if median < 12:
        return 0.0, "values too short to be descriptions"

    vietnamese = sum(1 for v in values if has_vietnamese(v)) / len(values)
    coded = sum(1 for v in values if _CODE_RE.search(v)) / len(values)
    wordy = sum(1 for v in values if len(v.split()) >= 4) / len(values)
    distinct = len(set(values)) / len(values)

    score = (min(median / 60, 1.0) * 3.0     # long text
             + vietnamese * 3.0              # Vietnamese prose
             + wordy * 2.0                   # several words, not a label
             + coded * 1.5                   # product codes present
             + distinct * 1.0)               # varies row to row

    reason = (f"median {median} chars, {vietnamese:.0%} Vietnamese, "
              f"{coded:.0%} with codes")
    return score, reason


def detect_layout(sheet, ai_tiebreak=None) -> Layout:
    """Locate the description column. ai_tiebreak(candidates) -> column or None."""
    header_row = find_header_row(sheet)

    ranked = []
    for column in range(1, sheet.max_column + 1):
        values = _cells(sheet, column, header_row + 1)
        score, reason = score_column(values)
        if score <= 0:
            continue
        header = sheet.cell(header_row, column).value
        ranked.append((score, column, str(header or f"column {column}"),
                       reason, values[:2]))

    if not ranked:
        raise ValueError(
            "could not find a text column that looks like goods descriptions - "
            "pass --col explicitly")

    ranked.sort(key=lambda item: -item[0])
    top = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None

    # Close call: let the model look at the headers and sample values.
    margin = (top[0] - runner[0]) / top[0] if runner else 1.0
    if runner and margin < 0.15 and ai_tiebreak is not None:
        chosen = ai_tiebreak([
            {"column": c, "header": h, "samples": s} for _, c, h, _, s in ranked[:3]])
        if chosen:
            for score, column, header, reason, _ in ranked:
                if column == chosen:
                    return Layout(header_row, column, header, 1.0,
                                  runner[2], f"{reason} (confirmed by AI)")

    return Layout(header_row, top[1], top[2], min(margin + 0.5, 1.0),
                  runner[2] if runner else None, top[3])
