"""Tokenizing helpers shared by retrieval and comment attribution."""
import re
from typing import List

STOPWORDS = set("""
a an the and or but if then so of to in on at by for with from into over under about as is are was were be been
being it its this that these those there here i you he she we they me him her us them my your his our their
what which who whom whose when where why how all any both each few more most other some such no nor not only own
same than too very can will just do does did doing have has had having would should could may might must shall
also get got gonna like really just even still yet ever one two dont don't im i'm its it's thats that's youre
you're theyre they're isnt isn't arent aren't wasnt wasn't cant can't wont won't lol yeah ok okay
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9$][a-z0-9$.%'-]*")


def stem(token: str) -> str:
    """Very light suffix stripping so 'discs'/'disc' and 'subscriptions'/'subscription' match."""
    for suffix in ("ations", "ation", "ings", "ing", "ies", "es", "s", "ed"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return token


def tokens(text: str) -> List[str]:
    words = _TOKEN_RE.findall((text or "").lower())
    return [stem(w.strip(".'-")) for w in words if w.strip(".'-") and w not in STOPWORDS and len(w) > 1]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 0]


def format_timestamp(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
