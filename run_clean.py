"""Clean the goods-description column of a customs workbook into a new file.

The sheet, header row and description column are detected per file - nothing
about the layout is assumed - and printed before any work is done.

    python3 run_clean.py declarations.xlsx
    python3 run_clean.py declarations.xlsx out.xlsx --col D --header-row 3

Rows the rules handle confidently are replaced with the clean English name.
Rows they cannot are LEFT EXACTLY AS THEY WERE, highlighted amber, and listed on
a 'Review' sheet with an empty 'Final name' column.

Fill that column in - by hand, or by asking Claude to do it - then run:

    python3 apply_review.py out.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import column_index_from_string, get_column_letter

from clean_flavour import Vocabulary, clean_description, CleanResult
from detect import detect_layout
import re

def load_custom_rules(path: Path) -> list[dict]:
    import openpyxl
    try:
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = book.worksheets[0]
    except Exception as e:
        print(f"Warning: could not read custom rules file {path}: {e}")
        return []
        
    custom_patterns = []
    # Assumes row 1 is header (Input | Output), data starts from row 2
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if len(row) < 2: continue
        input_str, output_str = row[0], row[1]
        if not input_str or not output_str: continue
            
        input_str = str(input_str).strip()
        output_str = str(output_str).strip()
        
        if output_str not in input_str:
            custom_patterns.append({"type": "literal", "input": input_str, "output": output_str})
            continue
            
        parts = input_str.split(output_str, 1)
        prefix, suffix = parts[0], parts[1]
        
        # Ngăn chặn lỗi Catch-all (nếu input == output thì prefix và suffix đều rỗng)
        # Regex sinh ra sẽ là ^(.*?).*$ nuốt trọn mọi dòng và trả về kết quả ảo 1.0
        if not prefix.strip() and not suffix.strip():
            custom_patterns.append({"type": "literal", "input": input_str, "output": output_str})
            continue
            
        def generalize(text):
            escaped = re.escape(text)
            return re.sub(r'\d+', lambda m: r'\d+', escaped)
            
        prefix_pat = generalize(prefix)
        
        # Lấy phần hậu tố ngắn nhất đến dấu phẩy/chấm/chấm phẩy đầu tiên
        m = re.match(r'^([^,;.]+[,;.]?)', suffix)
        if m:
            first_part_of_suffix = m.group(1)
        else:
            first_part_of_suffix = suffix[:15]
            
        suffix_pat = generalize(first_part_of_suffix) + ".*"
        pattern = f"^{prefix_pat}(.*?){suffix_pat}$"
        
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            custom_patterns.append({"type": "regex", "pattern": compiled})
        except Exception:
            pass
            
    print(f"Loaded {len(custom_patterns)} custom rules from {path.name}")
    return custom_patterns

def apply_custom_rules(text, custom_patterns):
    text_clean = re.sub(r"\s+", " ", str(text)).strip()
    for rule in custom_patterns:
        if rule["type"] == "regex":
            match = rule["pattern"].match(text_clean)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return CleanResult(str(text), extracted, 1.0, ("custom_rule",))
        elif rule["type"] == "literal":
            if rule["input"].lower() == text_clean.lower():
                return CleanResult(str(text), rule["output"], 1.0, ("custom_rule_literal",))
    return None





AMBER = PatternFill("solid", start_color="FFF2CC", end_color="FFF2CC")
REVIEW_SHEET = "Review"
REVIEW_HEADERS = ["Row", "Why it was not cleaned", "Original text",
                  "Rules' best guess", "Final name", "Source"]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="source .xlsx")
    parser.add_argument("output", nargs="?", help="defaults to <input>_cleaned.xlsx")
    parser.add_argument("--sheet", default=None, help="sheet name (default: first)")
    parser.add_argument("--col", default="auto",
                        help="column letter to clean (default: detect it)")
    parser.add_argument("--header-row", default="auto",
                        help="row the headers sit on (default: detect it)")
    parser.add_argument("--threshold", type=float, default=0.95,
                        help="confidence below which a row is left for review")
    parser.add_argument("--custom-rules", default=None,
                        help="path to adding_rules.xlsx")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 1

    dest = Path(args.output) if args.output else src.with_name(f"{src.stem}_cleaned.xlsx")
    vocab = Vocabulary.load()
    
    custom_patterns = []
    if args.custom_rules:
        custom_rules_path = Path(args.custom_rules)
        if custom_rules_path.exists():
            custom_patterns = load_custom_rules(custom_rules_path)

    book = openpyxl.load_workbook(src)
    sheet = book[args.sheet] if args.sheet else book.worksheets[0]

    # Layout is measured, not assumed: another exporter's file will put the
    # description somewhere else, under a different header, on a different row.
    if args.col == "auto" or str(args.header_row) == "auto":
        layout = detect_layout(sheet, ai_tiebreak=None)
        col = (column_index_from_string(args.col) if args.col != "auto"
               else layout.column)
        header_row = (layout.header_row if str(args.header_row) == "auto"
                      else int(args.header_row))
        print(f"Sheet          : {sheet.title}")
        print(f"Header row     : {header_row}"
              + ("  (detected)" if str(args.header_row) == "auto" else ""))
        print(f"Description col: {get_column_letter(col)} "
              f"{'- ' + layout.header_name if layout.header_name else ''}")
        if args.col == "auto":
            print(f"                 {layout.reason}")
            if layout.runner_up:
                print(f"                 next best was {layout.runner_up!r}; "
                      f"pass --col to override")
        print()
    else:
        col = column_index_from_string(args.col)
        header_row = int(args.header_row)

    letter = get_column_letter(col)

    results = {}
    for row in range(header_row + 1, sheet.max_row + 1):
        value = sheet.cell(row, col).value
        if value is not None and str(value).strip():
            # Apply custom rules first
            res = apply_custom_rules(value, custom_patterns) if custom_patterns else None
            if not res:
                res = clean_description(value, vocab)
            results[row] = res

    # Audit columns so nothing is ever lost and every row is traceable.
    audit = sheet.max_column + 1
    for offset, suffix in enumerate(("original", "confidence", "status")):
        sheet.cell(header_row, audit + offset,
                   f"{letter}_{suffix}").font = Font(bold=True)

    if REVIEW_SHEET in book.sheetnames:
        del book[REVIEW_SHEET]
    review = book.create_sheet(REVIEW_SHEET)
    review.append(REVIEW_HEADERS)
    for cell in review[1]:
        cell.font = Font(bold=True)
    review.freeze_panes = "A2"

    # Record where the cleaned column lives, so apply_review.py needs no arguments.
    # Kept on row 1 so it does not push a blank row into the review list.
    review["G1"], review["H1"] = "target_column", letter
    review["I1"], review["J1"] = "target_sheet", sheet.title
    for ref in ("G1", "I1"):
        review[ref].font = Font(italic=True, color="808080")

    auto = flagged = 0

    for row, result in results.items():
        cell = sheet.cell(row, col)

        if result.confidence >= args.threshold:
            auto += 1
            cell.value = result.name
            status = "cleaned"
        else:
            flagged += 1
            status = "needs review"          # tier 3: cell content left untouched
            cell.fill = AMBER
            review.append([row, ", ".join(result.reasons) or "low_confidence",
                           result.raw, result.name, None])
            review.cell(review.max_row, 5).fill = AMBER

        sheet.cell(row, audit, result.raw)
        sheet.cell(row, audit + 1, result.confidence)
        sheet.cell(row, audit + 2, status)

    for column, width in (("A", 8), ("B", 34), ("C", 78), ("D", 40), ("E", 40), ("F", 10)):
        review.column_dimensions[column].width = width
    for column in ("C", "D", "E"):
        for cell in review[column]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for offset, width in ((0, 60), (1, 13), (2, 14)):
        sheet.column_dimensions[get_column_letter(audit + offset)].width = width

    if not flagged:
        review.append([])
        review.append([None, "Nothing needs review - every row was cleaned."])

    book.save(dest)

    total = len(results) or 1
    print(f"Rows processed : {len(results)}")
    print(f"  cleaned        : {auto:>6}  ({auto / total:.1%})")
    print(f"  needs review   : {flagged:>6}  ({flagged / total:.1%})  amber, left untouched")
    print(f"Written to     : {dest}")
    if flagged:
        print()
        print(f"Next: fill the 'Final name' column on the '{REVIEW_SHEET}' sheet,")
        print(f"      then run:  ./apply.sh {dest.name}          (Windows: apply.bat)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
