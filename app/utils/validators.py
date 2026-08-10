import re

# Djinni's primary_keyword values are latin ("Python", "C++", "Node.js", ".NET").
# An unknown keyword is not rejected — Djinni silently returns the full unfiltered
# feed — so junk has to be caught before it reaches the query string.
_LATIN = re.compile(r"[A-Za-z]")
_SEPARATORS = re.compile(r"[,\s/]+")


def is_searchable(word: str) -> bool:
    """True if the word can plausibly be a Djinni tech keyword."""
    return bool(_LATIN.search(word))


def split_keywords(stack: str | None, limit: int) -> list[str]:
    """Split a user's stack into deduplicated, searchable keywords."""
    if not stack:
        return []
    words = (w.strip() for w in _SEPARATORS.split(stack))
    searchable = [w for w in words if w and is_searchable(w)]
    return list(dict.fromkeys(searchable))[:limit]
