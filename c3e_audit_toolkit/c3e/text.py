from __future__ import annotations
import re
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
NEGATION_CUES = ("no ", "without ", "negative for ", "denies ", "absence of ", "free of ")
SPECULATION_CUES = (
    "rule out ", "r/o ", "evaluate for ", "concern for ", "possible ",
    "suspected ", "query ", "question of ", "check for ", "follow up "
)

def normalize(text: object) -> str:
    if text is None:
        return ""
    s = str(text).lower()
    s = re.sub(r"_+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def token_count(text: object) -> int:
    return len(TOKEN_RE.findall(normalize(text)))

def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase.lower())}\b", text) is not None

def classify_mentions(text: object, phrases: Iterable[str], window: int = 45) -> dict[str, bool]:
    s = normalize(text)
    affirmed = negated = speculative = any_mention = False
    for phrase in phrases:
        for m in re.finditer(rf"\b{re.escape(phrase.lower())}\b", s):
            any_mention = True
            left = s[max(0, m.start() - window):m.start()]
            if any(cue in left for cue in NEGATION_CUES):
                negated = True
            elif any(cue in left for cue in SPECULATION_CUES):
                speculative = True
            else:
                affirmed = True
    return {
        "mention_any": any_mention,
        "mention_affirmed": affirmed,
        "mention_negated": negated,
        "mention_speculative": speculative,
    }

def is_low_information(text: object, min_tokens: int, generic_phrases: list[str]) -> bool:
    s = normalize(text)
    if not s:
        return False
    if token_count(s) < min_tokens:
        return True
    stripped = s
    for phrase in generic_phrases:
        stripped = re.sub(rf"\b{re.escape(phrase.lower())}\b", " ", stripped)
    stripped = re.sub(r"[^a-z0-9]+", " ", stripped).strip()
    return len(TOKEN_RE.findall(stripped)) < min_tokens
