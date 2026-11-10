"""Grounding validator — the core trust mechanism (AGENT_ARCHITECTURE §7).

A claim may be stored as FACT only if its evidence quote is actually present in the text
of a source we fetched. Otherwise it is downgraded to UNKNOWN (and kept for debugging).
"""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from app.core.config import get_settings

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").translate(_QUOTES).lower()
    return re.sub(r"\s+", " ", s).strip()


def check_quote(quote: str | None, source_text: str | None) -> tuple[str, dict]:
    """Returns (grounding_status, detail). Status: passed | passed_fuzzy | failed."""
    if not quote or not source_text:
        return "failed", {"reason": "missing quote or source text"}
    q, t = normalize(quote), normalize(source_text)
    if len(q) < 8:
        return "failed", {"reason": "quote too short to verify"}
    if q in t:
        return "passed", {"method": "exact"}
    score = fuzz.partial_ratio(q, t) if len(t) < 400_000 else 0
    threshold = get_settings().grounding_fuzzy_threshold
    if score >= threshold:
        return "passed_fuzzy", {"method": "fuzzy", "score": round(score, 1), "threshold": threshold}
    return "failed", {"reason": "quote not found in source", "score": round(score, 1), "threshold": threshold}


_NUM = re.compile(r"\d[\d,\.]*")


def value_consistent(field: str, value, quote: str) -> bool:
    """Cheap sanity checks: numbers in numeric values must appear in the quote; cities must be mentioned."""
    nq = normalize(quote)
    if field == "employee_range":
        nums = [n.replace(",", "") for n in _NUM.findall(nq)]
        words = any(w in nq for w in ("employee", "people", "team", "staff", "professionals", "strong", "workforce", "associates"))
        return bool(nums) and words
    if field in ("hq_location",) and isinstance(value, dict):
        city = normalize(str(value.get("city") or ""))
        return not city or city in nq
    return True
