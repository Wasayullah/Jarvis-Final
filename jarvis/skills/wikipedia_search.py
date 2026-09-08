"""Wikipedia lookup using Wikipedia's HTTPS REST + MediaWiki APIs.

We deliberately avoid the `wikipedia` PyPI package: it is unmaintained and
hardcodes plain-HTTP endpoints, which Wikipedia now blocks.
"""

import requests

WIKI_SEARCH_API = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_HEADERS = {"User-Agent": "Jarvis-549-desktop-assistant/1.0"}


def _wiki_search_titles(query: str, limit: int = 5) -> list:
    params = {
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": limit, "format": "json",
    }
    r = requests.get(WIKI_SEARCH_API, params=params, headers=WIKI_HEADERS, timeout=10)
    r.raise_for_status()
    return [item["title"] for item in r.json().get("query", {}).get("search", [])]


def _wiki_summary(title: str):
    url = WIKI_SUMMARY_API.format(requests.utils.quote(title.replace(" ", "_")))
    r = requests.get(url, headers=WIKI_HEADERS, timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if data.get("type") == "disambiguation":
        return "DISAMBIGUATION"
    return (data.get("extract") or "").strip() or None


def _first_two_sentences(text: str) -> str:
    parts = text.replace("\n", " ").split(". ")
    trimmed = ". ".join(parts[:2]).strip()
    if trimmed and not trimmed.endswith((".", "!", "?")):
        trimmed += "."
    return trimmed


def search_wikipedia(query: str) -> str:
    if not query.strip():
        return "Please tell me what to search on Wikipedia."
    try:
        summary = _wiki_summary(query)
        if summary == "DISAMBIGUATION":
            summary = None
        if not summary:
            titles = _wiki_search_titles(query)
            if not titles:
                return "I couldn't find a Wikipedia page for that."
            for title in titles:
                candidate = _wiki_summary(title)
                if candidate and candidate != "DISAMBIGUATION":
                    summary = candidate
                    break
            if not summary:
                return "That's ambiguous -- could you be more specific?"
        return _first_two_sentences(summary)
    except requests.exceptions.RequestException:
        return "I'm having trouble reaching the internet right now."
    except Exception as e:
        return f"Wikipedia error: {e}"
