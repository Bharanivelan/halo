"""Web search adapter (optional). Implementation: Tavily, enabled when TAVILY_API_KEY is set."""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.providers.http import client, raise_for_status
from app.workflow.errors import TransientError

_settings = get_settings()

# Directory / social sites we never treat as a company's own website.
NOT_COMPANY_SITES = {
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "justdial.com",
    "indiamart.com", "glassdoor.com", "glassdoor.co.in", "ambitionbox.com", "naukri.com", "zaubacorp.com",
    "tofler.in", "crunchbase.com", "wikipedia.org", "google.com", "maps.google.com", "sulekha.com",
    "indeed.com", "indeed.co.in", "foundit.in", "tracxn.com", "zoominfo.com", "apollo.io", "bloomberg.com",
}


def available() -> bool:
    return _settings.search_configured


def search(query: str, max_results: int = 5) -> list[dict]:
    if not available():
        return []
    try:
        r = client.post("https://api.tavily.com/search", json={
            "api_key": _settings.tavily_api_key, "query": query[:300], "max_results": max_results,
            "search_depth": "basic", "include_answer": False}, timeout=25)
    except httpx.HTTPError as e:
        raise TransientError(f"Web search failed ({type(e).__name__})") from e
    raise_for_status(r, "Web search")
    return [{"title": it.get("title"), "url": it.get("url"), "snippet": (it.get("content") or "")[:500],
             "published_at": it.get("published_date")} for it in r.json().get("results", [])]
