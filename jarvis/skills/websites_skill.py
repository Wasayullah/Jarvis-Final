"""Website opening with fuzzy matching, plus list helper for the UI browser."""

import difflib
import webbrowser

from config import config
from websites import websites, WEBSITE_CATEGORIES


def _fuzzy_find_site(query: str):
    """Return (url, matched_key) or (None, suggestions_list)."""
    q = query.strip().lower()
    if q in websites:
        return websites[q], q

    substring_hits = [k for k in websites if q in k]
    if len(substring_hits) == 1:
        return websites[substring_hits[0]], substring_hits[0]
    if len(substring_hits) > 1:
        best = min(substring_hits, key=lambda k: abs(len(k) - len(q)))
        return websites[best], best

    close = difflib.get_close_matches(q, list(websites.keys()), n=3, cutoff=0.45)
    if close:
        return websites[close[0]], close[0]

    for w in q.split():
        if w in websites:
            return websites[w], w

    return None, [k for k in difflib.get_close_matches(q, list(websites.keys()), n=5, cutoff=0.3)]


def open_website(site_name: str) -> str:
    """Open a website. Returns None if the name is a reserved app name."""
    site_name = site_name.strip().lower()
    if site_name in config.RESERVED_APP_NAMES:
        return None

    url, matched = _fuzzy_find_site(site_name)
    if url:
        webbrowser.open(url)
        return f"Opening {matched}..."
    return None


def categories_text() -> str:
    lines = []
    for name, sites in WEBSITE_CATEGORIES.items():
        lines.append(f"  {name}: {', '.join(sites[:5])}...")
    return "\n".join(lines)


def categories() -> dict:
    return WEBSITE_CATEGORIES
