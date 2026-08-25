# Flavour name cleaner

Takes a Vietnamese customs import declaration and pulls the English product name
out of the goods-description column.

```
IN   CHẤT TẠO HƯƠNG MILK FLAVOUR PFE-10001, NSX: ABC TRADING, HÀNG MẪU MỚI 100%
OUT  MILK FLAVOUR PFE-10001
```

One command: unprocessed `.xlsx` in, processed `.xlsx` out.

**Your source file is never modified.** Everything is written to a new workbook.

---

# ⚠️ WINDOWS USERS — DO THIS FIRST

**Three files arrive with a `.txt` on the end and will not work until you remove
it.** Email providers block `.bat` attachments, so they were renamed to get
through. Rename them back before anything else:

| arrives as | rename it to |
|---|---|
| `run.bat.txt` | `run.bat` |
| `apply.bat.txt` | `apply.bat` |
| `make-tests.bat.txt` | `make-tests.bat` |

### The trap: Windows hides file extensions

By default, File Explorer **hides** the `.txt`, so `run.bat.txt` is displayed to
you as `run.bat` — it already looks correct, and renaming appears to do nothing.
You must turn extensions on first or you cannot fix this:

1. Open the unzipped folder in File Explorer
2. Click the **View** tab → tick **File name extensions**
   *(Windows 11: **View** → **Show** → **File name extensions**)*
3. The names now read `run.bat.txt`. Right-click each → **Rename** → delete the
   trailing `.txt` → Enter. Accept the "file might become unusable" warning.

### Or do it in one line

Open Command Prompt in the unzipped folder and paste:

```
ren run.bat.txt run.bat & ren apply.bat.txt apply.bat & ren make-tests.bat.txt make-tests.bat
```

Then check it worked:

```
dir *.bat
```

You should see exactly three files: `run.bat`, `apply.bat`, `make-tests.bat`.
If you see `run.bat.txt` in that list, the rename did not take — go back and turn
on file name extensions.

**macOS and Linux: ignore all of the above.** You use `run.sh`, which is
unaffected. You can delete the three `.bat.txt` files.

---

---

## Prerequisites

**1. Python 3.9 or newer** — [python.org](https://python.org). On Windows, tick
*"Add Python to PATH"* during install.

**2. An AI backend.** Rules alone get about 77% of the rows; the model handles a
good part of the rest. You need **one** of these:

| option | how | cost |
|---|---|---|
| **Claude Code** (easiest) | install from [claude.com/claude-code](https://claude.com/claude-code) and sign in | uses your existing plan |
| **Anthropic API key** | set `ANTHROPIC_API_KEY` in your environment | a few cents per run |

The tool detects whichever you have. Claude Code is used first if both are present.

Setting an API key, if you go that route:

```bash
export ANTHROPIC_API_KEY="your-key-here"        # macOS / Linux
setx ANTHROPIC_API_KEY "your-key-here"          # Windows, then reopen the terminal
```

> **No credential is stored in this package.** The key is read from your
> environment at the moment of the call and never written to any file here. Use
> your own key; get one at [console.anthropic.com](https://console.anthropic.com).

If you have neither, `--no-ai` still works — you get the 77% and review the rest
by hand.

---

## Quick start — from zero on a fresh machine

Open a terminal: **Terminal** on macOS (Cmd+Space, type "terminal"), or
**Command Prompt** on Windows (Start, type "cmd").

**Step 1 — check you have Python.**

```bash
python3 --version        # macOS / Linux
python --version         # Windows
```

Anything `3.9` or higher is fine. If it says "command not found", install from
[python.org](https://python.org) — on Windows tick *"Add Python to PATH"* — then
close the terminal, open a new one, and try again.

**Step 2 — check you have an AI backend.**

```bash
claude --version
```

If that prints a version, you are done. If not, either install Claude Code from
[claude.com/claude-code](https://claude.com/claude-code) and sign in, or set an
`ANTHROPIC_API_KEY` (see Prerequisites above). Skip this step entirely if you
intend to use `--no-ai`.

**Step 3 — unzip and go into the folder.**

```bash
unzip flavour-cleaner.zip
cd flavour-cleaner
```

Double-clicking the zip works just as well; then `cd` into the folder it creates.

**Step 4 — run it on your spreadsheet.**

```bash
./run.sh declarations.xlsx                      # macOS / Linux
run.bat declarations.xlsx                       # Windows (rename .bat.txt first)
```

If your file is somewhere else, give the full path — or on macOS just type
`./run.sh ` and **drag the file into the terminal window**, which pastes its path
for you:

```bash
./run.sh ~/Downloads/declarations.xlsx
run.bat C:\Users\you\Downloads\declarations.xlsx
```

The first run installs one dependency into a local `.venv` folder — about 20
seconds, once only. After that stage 1 takes seconds and the AI stage a few
minutes.

**Step 5 — collect the result.** It lands next to your input as
`declarations_cleaned.xlsx`. To choose the name yourself:

```bash
./run.sh declarations.xlsx cleaned.xlsx
```

> **"permission denied" on macOS or Linux?** Some unzip tools drop the
> executable flag. Fix it once:
> ```bash
> chmod +x run.sh apply.sh
> ```

---

## What it does

Three stages, run automatically in order.

**Stage 1 — rules.** Deterministic pattern matching. Fast, free, no network.
Handles the bulk.

**Stage 2 — AI.** The model reads *every* row: it fills the gaps the rules
refused, **and re-checks the rows the rules were confident about.** That second
half matters — rules can be confidently wrong, and nothing else in the system
would ever catch it.

**Stage 3 — merge.** Accepted names are written into the sheet.

Measured on a real 831-row declaration file:

```
rules, confirmed by AI   592  (71.2%)
rules corrected by AI     49  ( 5.9%)
gaps filled by AI         52  ( 6.3%)
---------------------------------------
resolved                 693  (83.4%)
left for a human         138  (16.6%)
```

Note the middle line. The rules were confident about 641 rows — and **49 of them
(7.6%) were wrong.** Codes truncated (`SAMPLE FLAVOUR PFE` instead of
`SAMPLE FLAVOUR PFE- 20001`), codes duplicated onto the front
(`PFE-20002-SAMPLE FLAVOUR PFE-20002`), a lost closing bracket, and in three
rows an ingredient lifted out of a composition list instead of the product —
`REFINED PALM OIL` picked out of `Hương X (TP gồm: REFINED PALM OIL, ...) -
Sample Flavour PFE-20003`. All of them scored ≥0.95 confidence. Without the
audit they ship silently wrong.

The AI stage takes 10–20 minutes on a file this size; the rest is seconds. Use
`--scope refused` to skip the audit and only fill gaps — faster, and what you
want for a quick look, but it will not catch any of the above.

---

## The part that matters: the AI cannot invent a name

**Every answer the model gives is verified against the original text before it is
accepted.** A name is only written if it actually appears in that row's
description — ignoring case and spacing. Anything else is thrown away and the row
is left blank for a human.

That means a translation cannot get through. Given
`CHẤT TẠO HƯƠNG THƠM VỊ DÂU TÂY SỐ 7788`, if the model answered
"Strawberry Flavour 7788" the verifier would reject it, because those letters are
nowhere in the source. In the measured run above, **136 rows came back as "no
English name here"** and 2 more were rejected by the verifier.

This is deliberate. It is customs data: a name that was never on the declaration
corrupts the record, and a wrong product name is far worse than an unconverted
one. The tool is built to stop rather than guess, and the AI is held to the same
rule as the rules engine.

Rows left blank are genuinely unresolvable — things like `Hương Bò PFE-30001` or
`Hương tỏi PFE-30002`, which name the product only in Vietnamese. Turning those
into "BEEF FLAVOUR" or "GARLIC FLAVOUR" is exactly what must not happen.

The one edit the model is allowed is inserting spaces where the source runs words
together: `RoastedMeatSeasoningPowderFE-10005` →
`Roasted Meat Seasoning Powder FE-10005`. The letters stay identical.

---

## What you get back

Two sheets.

**Sheet 1** — your original data, all columns intact, the description column
cleaned, and three columns appended on the right:

| column | meaning |
|---|---|
| `<col>_original` | the untouched original text, always |
| `<col>_confidence` | 0.0–1.0, how sure the rules were |
| `<col>_status` | where the final name came from — see below |

`<col>` is the letter of the column that was cleaned, so for a file whose
descriptions are in column J these read `J_original`, `J_confidence`, `J_status`.

`<col>_status` values:

| value | meaning |
|---|---|
| `cleaned` | the rules, and the model independently agreed |
| `cleaned (AI)` | a row the rules refused; the model found the name |
| `cleaned (AI corrected)` | the rules were wrong here and the model overrode them |
| `cleaned (reviewed)` | a person |
| `needs review` | still amber; nobody could extract a name |

You can always tell which names came from a machine and which from a person.

**`Review` sheet** — only the unresolved rows:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Row | Why it was not cleaned | Original text | Rules' best guess | **Final name** | Source |

AI answers are highlighted blue. Rows still blank are for you.

---

## Finishing the last rows by hand

1. Open the output, go to the **`Review`** sheet.
2. Type the English name into column **E, `Final name`**.
3. Save, close the workbook, then:

```bash
./apply.sh cleaned.xlsx        # macOS / Linux
apply.bat cleaned.xlsx         # Windows
```

Re-runnable as often as you like — rows you leave blank stay amber.

**The rule for filling it in:** if you cannot see an English name in the original
text, leave it blank. Copy words exactly as they appear; never translate. A blank
is a correct answer.

---

## Options

```bash
./run.sh input.xlsx output.xlsx --review
```

| flag | default | |
|---|---|---|
| `--col` | detected | column holding the descriptions |
| `--header-row` | detected | row the headers are on; data starts below |
| `--sheet` | first sheet | sheet name |
| `--threshold` | `0.95` | confidence the rules need to accept a name |
| `--scope` | `all` | `all` audits the confident rows too; `refused` only fills gaps |
| `--review` | off | stop before merging, so you can skim the AI's answers |
| `--no-ai` | off | rules only; no model, no network |
| `--backend` | `auto` | force `cli` or `api` |
| `--model` | Sonnet | model name, API backend only |
| `--batch` | `20` | rows per request |

You should not normally need `--col`, `--header-row` or `--sheet` — see below.

Lowering `--threshold` makes the rules clean more rows and get more of them
wrong. 0.95 was tuned on real data.

---

## Files from a different exporter

Nothing about the layout is hardcoded. Every file is measured on opening:

```
Sheet          : Sheet1
Header row     : 1  (detected)
Description col: J - Chung loai hang hoa xuat nhap
                 median 115 chars, 100% Vietnamese, 100% with codes
                 next best was 'Doanh nghiep xuat nhap'; pass --col to override
```

Each column is scored on how much it looks like free-text goods descriptions —
length, Vietnamese content, product codes, how many words, how much it varies row
to row. The header row is found as the last mostly-text row before the data
starts. When the top two columns score within 15% of each other, the model is
shown the header names and a couple of sample values and asked to pick; with no
AI backend the heuristic decides alone.

It prints what it found before doing anything. If it picked wrong, override it:

```bash
./run.sh declarations.xlsx --col D --header-row 3 --sheet "Import Data"
```

Different exporters also word things differently, so the rules' share will drop
on an unfamiliar file until you add that wording to `patterns.txt`.

---

## Tests for your own file

The shipped tests cover generic shapes only. To build a set specific to your
data:

```bash
./make-tests.sh declarations.xlsx        # macOS / Linux
make-tests.bat declarations.xlsx         # Windows
```

This samples rows from your file and asks the rules engine and the model the same
question about each. Where they **agree**, the answer becomes a fixture. Where
they **disagree**, it is written out as `UNCONFIRMED` with both answers, and you
decide who was right.

That disagreement list is the useful part — it is where either the rules have a
gap or the model is wrong, and both are worth knowing.

The result is `fixtures.py`, picked up automatically by `test_clean.py`.
`test_clean.py` will not report a pass while any `UNCONFIRMED` entry remains, so
an unreviewed baseline cannot look like a green suite.

> **`fixtures.py` holds rows from your data.** It is generated locally and is not
> part of this package. Do not pass it on with the tool.

Why not just record whatever the rules currently output? Because that tests
nothing — the baseline would move along with any bug, and the suite would stay
green through a change that broke every row. A fixture is only worth having when
something independent asserts the expected value.

---

## Teaching it new patterns

If several review rows share a shape, add the wording to `patterns.txt` and the
rules will catch it next time, no model needed:

- `[metadata]` — clauses to delete outright
- `[descriptors]` — Vietnamese category wording to strip off the front
- `[vietnamese-words]` — Vietnamese words written without accents
- `[product-keywords]` — words marking a real product name (`FLAVOUR`, `OIL`)

Entries match **without accents and case-insensitively** — write `HANG MAU` and
it matches `HÀNG MẪU`. Prefix a line with `re:` for a raw regular expression.

After any edit, run the tests:

```bash
./.venv/bin/python test_clean.py        # macOS / Linux
.venv\Scripts\python test_clean.py      # Windows
```

29 checks covering the known-good cases. If one fails, the edit broke something
that used to work — fix it before running on real data.

---

## Troubleshooting

**"The row count didn't change / my edits vanished."**
Excel was holding the file open and wrote its stale copy over the output.
**Close the workbook in Excel before re-running.** This is the most common
problem and it looks exactly like the tool failing.

**"no AI backend available"**
Neither Claude Code nor `ANTHROPIC_API_KEY` was found. Set one up per
Prerequisites, or run with `--no-ai`.

**A batch says FAILED.** Usually a network blip or a rate limit. The other
batches still land; re-run and it only retries what is still blank.

**"It cleaned the wrong column"** or **"it skipped a row of data."** Check the
layout it printed at the top of the run — sheet, header row, column. Override
whichever it got wrong with `--col`, `--header-row` or `--sheet`.

**Starting over.** Delete the `.venv` folder and run again; it rebuilds.

---

## Limitations

- Numeric cells can shift by about 1 part in 10^16 when the workbook is rewritten
  (`3200368.6259999997` may be stored as `3200368.626`). Floating-point
  round-tripping, far below any currency or weight unit, invisible in Excel. Your
  source file is untouched, so it stays the authority.
- Charts, images, pivot tables and macros are **not** carried into the output. If
  your file has any, clean a data-only copy.
- The AI stage sends the goods-description text of the unresolved rows to
  Anthropic. Nothing else from the workbook leaves your machine. If that is not
  acceptable for your data, use `--no-ai`.
- Tuned on one exporter's declarations. Other exporters word things differently,
  so expect the rules' share to drop until you add their phrasing to
  `patterns.txt`.

---

## Files

| | |
|---|---|
| `run.sh` / `run.bat.txt` | the entry point — runs all three stages |
| `apply.sh` / `apply.bat.txt` | merge hand-written names in later |
| `make-tests.sh` / `.bat.txt` | build fixtures from your own file |

Windows: the three `.bat.txt` files must be renamed to `.bat` before use — see
the warning at the top of this file.
| `pipeline.py` | stage orchestration |
| `detect.py` | works out sheet, header row and description column |
| `make_tests.py` | fixture generation and the rules-vs-model cross-check |
| `run_clean.py` | stage 1, the rules |
| `clean_flavour.py` | the extraction engine |
| `patterns.txt` | the vocabulary; edit this, not the code |
| `ai_fill.py` | stage 2, the model + the verifier |
| `apply_review.py` | stage 3, the merge |
| `test_clean.py` | 29 checks |
| `SKILL.md` | notes for use inside Claude Code |
