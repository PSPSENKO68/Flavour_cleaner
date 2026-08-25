"""Extract the English product name from Vietnamese customs goods descriptions.

    "CHẤT TẠO HƯƠNG MILK FLAVOUR PFE-10001, NSX: ABC TRADING, HÀNG MẪU MỚI 100%"
        -> "MILK FLAVOUR PFE-10001"

The vocabulary lives in patterns.txt so it can be extended without editing code.
Rows the rules cannot handle confidently are reported with a low confidence score;
the caller is expected to leave those rows alone rather than guess.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

PATTERNS_FILE = Path(__file__).with_name("patterns.txt")

_VI_EXTRA = frozenset("đĐ")


# --- Vietnamese detection -------------------------------------------------

def has_vietnamese(token: str) -> bool:
    """True when the token carries a Vietnamese diacritic or đ/Đ."""
    if any(ch in _VI_EXTRA for ch in token):
        return True
    return any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", token))


def strip_accents(text: str) -> str:
    """Fold 'HÀNG MẪU' down to 'HANG MAU' so patterns.txt needs no accents."""
    decomposed = unicodedata.normalize("NFD", text)
    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return folded.replace("đ", "d").replace("Đ", "D")


# --- patterns.txt loading -------------------------------------------------

def _compile_entry(entry: str) -> str:
    """Turn a vocabulary line into a regex fragment with flexible spacing."""
    if entry.startswith("re:"):
        return entry[3:]

    tokens = entry.split()
    body = r"\s*".join(re.escape(token) for token in tokens)
    prefix = r"\b" if tokens and tokens[0][:1].isalnum() else ""
    suffix = r"\b" if tokens and tokens[-1][-1:].isalnum() else ""
    return f"{prefix}{body}{suffix}"


def _load_sections(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1].strip(), [])
            continue
        if current is not None:
            current.append(line)

    return sections


@dataclass(frozen=True)
class Vocabulary:
    metadata: re.Pattern[str]
    descriptors: re.Pattern[str]
    plain_words: frozenset[str]
    product_keywords: frozenset[str]

    @classmethod
    def load(cls, path: Path = PATTERNS_FILE) -> "Vocabulary":
        sections = _load_sections(path)

        metadata = [_compile_entry(e) for e in sections.get("metadata", [])]
        descriptors = [_compile_entry(e) for e in sections.get("descriptors", [])]
        plain = {
            word.upper()
            for line in sections.get("vietnamese-words", [])
            for word in line.split()
        }
        keywords = {
            word.upper()
            for line in sections.get("product-keywords", [])
            for word in line.split()
        }

        never = r"(?!x)x"  # matches nothing, used when a section is empty
        return cls(
            metadata=re.compile("|".join(metadata) or never, re.IGNORECASE),
            descriptors=re.compile(
                r"^(?:%s)" % ("|".join(descriptors) or never), re.IGNORECASE
            ),
            plain_words=frozenset(plain),
            product_keywords=frozenset(keywords),
        )


# Split on punctuation that separates clauses. Hyphens are NOT split on: product
# codes contain them ("HFE - 14907"), and cutting there truncates the name.
# A full stop only splits when followed by a space, so "SDN.BHD" and decimals
# such as "0.53" stay intact while a trailing "... bánh. Mới 100%" is severed -
# otherwise that metadata poisons the clause holding the product name.
_SPLIT_RE = re.compile(r"[,;:]|\.\s")
_PAREN_RE = re.compile(r"\s*[（(]([^)）]*)[)）]")

# Product codes: "PFE-10001", "HFE - 14907", "TH4-657", "BT-9", or a bare "5567".
_CODE_RE = re.compile(r"\b[A-Za-z]{1,5}\s*-\s*\d{1,6}\b|\b[A-Za-z]{1,5}\d{2,6}\b|\b\d{4,6}\b")


# --- cleaning -------------------------------------------------------------

@dataclass(frozen=True)
class CleanResult:
    raw: str
    name: str
    confidence: float
    reasons: tuple[str, ...]

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.95


def _is_vietnamese_word(token: str, vocab: Vocabulary) -> bool:
    if has_vietnamese(token):
        return True
    return strip_accents(token).strip(":-.").upper() in vocab.plain_words


def _drop_lead_descriptor(segment: str, vocab: Vocabulary) -> str:
    """Remove leading Vietnamese category wording, keeping the English name."""
    working = segment
    for _ in range(3):  # descriptors stack: "PHU GIA THUC PHAM CHAT TAO HUONG X"
        match = vocab.descriptors.match(strip_accents(working))
        if not match:
            break
        working = working[match.end():].lstrip(" :-")

    tokens = working.split()
    index = 0
    while index < len(tokens) and _is_vietnamese_word(tokens[index], vocab):
        index += 1

    # Never strip the whole segment away - that means the guess went wrong.
    return " ".join(tokens[index:]) if index < len(tokens) else working


def _drop_trailing_vietnamese(segment: str) -> str:
    tokens = segment.split()
    end = len(tokens)
    while end > 0 and has_vietnamese(tokens[end - 1]):
        end -= 1
    return " ".join(tokens[:end])


def _english_runs(segment: str, vocab: Vocabulary) -> list[str]:
    """Split a segment into maximal runs of consecutive non-Vietnamese tokens.

    The English product name is often sandwiched between Vietnamese wording, so
    it has to be located rather than trimmed around:

        "Hương dầu hành, không chứa cồn - Fried Onion Oil FE-2002 dùng để..."
                                           ^^^^^^^^^^^^^^^^^^^^^^^ one run
    """
    runs: list[str] = []
    current: list[str] = []

    # Only accented words break a run. Accent-less Vietnamese words are NOT used
    # here - they also occur inside real names ("Tom Yum Flavour"), and trimming
    # them off the front of the winner is safe where splitting on them is not.
    for token in segment.split():
        if has_vietnamese(token):
            if current:
                runs.append(" ".join(current))
                current = []
        else:
            current.append(token)

    if current:
        runs.append(" ".join(current))

    return [cleaned for run in runs if (cleaned := run.strip(" -–—:.,"))]


def _prefer_after_dash(run: str, vocab: Vocabulary) -> str:
    """Handle the "<vietnamese name> - <ENGLISH NAME>" shape, the commonest here.

        "HƯƠNG LỰU PFE-30003 - POMEGRANATE FLAVOUR PFE-30003"
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ keep only this

    Cuts at the first " - " whose remainder still names a product, so a spaced
    code like "APPLE FLAVOUR PFE - 14248" is never truncated: "14248" carries no
    product keyword, so no cut is made.
    """
    for match in re.finditer(r"\s+-\s+|\(", run):
        remainder = run[match.end():].strip()
        words = re.findall(r"[A-Za-z]+", remainder)
        if any(word.upper() in vocab.product_keywords for word in words):
            return remainder
    return run


def _score_run(run: str, vocab: Vocabulary) -> int:
    """How strongly this span looks like a product name. Higher wins."""
    words = re.findall(r"[A-Za-z]+", run)
    if not words:
        return 0

    score = 0
    if any(word.upper() in vocab.product_keywords for word in words):
        score += 10                      # "FLAVOUR", "OIL", "POWDER"...
    if _CODE_RE.search(run):
        score += 5                       # "PFE-10001"
    score += min(len(words), 4)          # prefer a fuller name over a fragment
    return score


def clean_description(raw: object, vocab: Vocabulary | None = None) -> CleanResult:
    """Extract the English product name. Low confidence means 'do not trust this'."""
    vocab = vocab or Vocabulary.load()

    if raw is None:
        return CleanResult("", "", 0.0, ("empty_input",))

    text = re.sub(r"\s+", " ", str(raw)).strip()
    if not text:
        return CleanResult("", "", 0.0, ("empty_input",))

    def _prune_paren(match: re.Match[str]) -> str:
        inner = match.group(1)
        if vocab.metadata.search(strip_accents(inner)):
            return ""
        words = inner.split()
        if words and all(_is_vietnamese_word(w, vocab) for w in words):
            return ""
        return match.group(0)

    working = _PAREN_RE.sub(_prune_paren, text).strip()

    segments = [s.strip() for s in _SPLIT_RE.split(working) if s.strip()]
    candidates = [s for s in segments if not vocab.metadata.search(strip_accents(s))]

    reasons: list[str] = []
    if not candidates:
        candidates = segments
        reasons.append("all_segments_looked_like_metadata")

    # Locate the English product name rather than trimming around it: score every
    # run of non-Vietnamese words and keep the one that reads most like a product.
    scored = [
        (_score_run(run, vocab), index, run)
        for index, segment in enumerate(candidates)
        for run in _english_runs(segment, vocab)
        if not vocab.metadata.search(strip_accents(run))
    ]
    if not scored:
        return CleanResult(text, "", 0.0, tuple(reasons) + ("no_english_name_found",))

    # Best score wins; ties go to whichever appeared first.
    score, _, best = max(scored, key=lambda item: (item[0], -item[1]))
    best = _prefer_after_dash(best, vocab)
    name = _drop_trailing_vietnamese(_drop_lead_descriptor(best, vocab)).strip(" :-.")
    name = re.sub(r'(?i)\s*-?\s*KQGD\b.*$', '', name).strip(' -.,')

    if not name or not re.search(r"[A-Za-z]", name):
        return CleanResult(text, "", 0.0, tuple(reasons) + ("no_english_name_found",))

    if score >= 10:                      # a product keyword is present
        confidence = 1.0
    elif score >= 6:                     # a code, but nothing naming the product
        confidence = 0.7
        reasons.append("code_without_product_keyword")
    else:
        confidence = 0.4
        reasons.append("weak_product_name_signal")

    if has_vietnamese(name):
        reasons.append("vietnamese_left_in_result")
        confidence -= 0.5
    if len(name) < 4:
        reasons.append("result_too_short")
        confidence -= 0.3
    if len(name) > 120:
        reasons.append("result_too_long")
        confidence -= 0.2
    if not re.search(r"[A-Za-z]{3}", name):
        reasons.append("no_word_like_token")
        confidence -= 0.4

    return CleanResult(text, name, max(0.0, round(confidence, 2)), tuple(reasons))
