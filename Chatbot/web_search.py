"""
web_search.py — Real-time web search using DuckDuckGo (no API key required).
Automatically detects queries that need current data and fetches live results.
"""

import re
from ddgs import DDGS

# Keywords that indicate the query needs real-time/current data
REALTIME_TRIGGERS = [
    # Sports
    r"\b(score|points table|standing|ranking|result|match|ipl|cricket|football|fifa|nba|nfl|premier league|series|tournament|championship|final|semifinal|semi.final)\b",
    # Time-sensitive
    r"\b(today|tonight|right now|current|latest|live|now|ongoing|happening|breaking|this (week|month|year|season))\b",
    # News & events
    r"\b(news|update|announcement|launch|release|election|vote|price|rate|stock|crypto|bitcoin|weather|forecast)\b",
    # Year references for recent events
    r"\b202[5-9]\b|\b20[3-9]\d\b",  # 2025-2029, 2030+ for future-proof coverage
    # Questions about recent status
    r"\b(who (is|are|won|leads|topped)|what (is|are) the (current|latest|new))\b",
]

_compiled = [re.compile(p, re.IGNORECASE) for p in REALTIME_TRIGGERS]

def needs_web_search(query: str) -> bool:
    """Returns True if the query likely needs real-time web data."""
    return any(p.search(query) for p in _compiled)

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return a formatted context string
    to inject into the AI prompt.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return ""

        lines = [f"[Web Search Results for: \"{query}\"]"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "").strip()
            body  = r.get("body", "").strip()
            href  = r.get("href", "").strip()
            if title or body:
                lines.append(f"\n[{i}] {title}")
                if body:
                    lines.append(f"    {body[:300]}")
                if href:
                    lines.append(f"    Source: {href}")

        lines.append("\n[Use the above search results to answer accurately. Cite the source if relevant.]")
        return "\n".join(lines)

    except Exception as e:
        return ""  # Silently fail — AI will answer from its own knowledge
