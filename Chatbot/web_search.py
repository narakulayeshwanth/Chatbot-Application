"""
web_search.py — Real-time web search engine for lavangam.ai

Priority chain:
  0. F1 queries      → Jolpica F1 API   (exact standings, zero hallucination)
  1. Cricket queries → ESPNcricinfo API  (live scores + series info)
  2. All queries     → DDGS text search  (proper DuckDuckGo Python API)
  3. Top result      → Page fetch        (extract actual article content)
"""

import re
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse

# ─── Realtime trigger patterns ────────────────────────────────────────────────
REALTIME_TRIGGERS = [
    r"\b(score|points.?table|standing|ranking|result|match|ipl|cricket|football|fifa|nba|nfl|f1|formula.?1|premier.?league|series|tournament|championship|final|semifinal|semi.?final|grand.?prix|league|cup|trophy)\b",
    r"\b(tonight|right.?now|current|latest|live|ongoing|happening|breaking|this.?(week|month|year|season)|recent|recently|new|just|update)\b",
    r"\b(news|update|announcement|launch|release|election|vote|price|rate|stock|crypto|bitcoin|ethereum|weather|forecast|gdp|inflation|war|conflict|disaster)\b",
    r"\b(who.?(is|are|won|leads|topped|runs|owns)|what.?(is|are).?(current|latest|new|today)|when.?(is|was|did|will))\b",
    r"\b202[5-9]\b|\b20[3-9]\d\b",
    r"\b(how.?much|worth|value|cost|price).*(now|today|current)\b",
    r"\b(what.?happened|tell me about|any.?news|whats.?new|whats.?up.?with)\b",
    r"\btoday\b",
]
_compiled = [re.compile(p, re.IGNORECASE) for p in REALTIME_TRIGGERS]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_SKIP_DOMAINS = [
    "youtube.com", "twitter.com", "x.com", "instagram.com",
    "facebook.com", "tiktok.com", "pinterest.com", "reddit.com",
]

# Domains sorted by reliability for specific content
_PRIORITY_DOMAINS = [
    "espncricinfo.com", "cricbuzz.com",           # Cricket (highest priority)
    "bbc.com", "reuters.com", "apnews.com",       # News
    "espn.com", "sportingnews.com",               # Sports
    "ndtv.com", "hindustantimes.com",             # India news
    "timesofindia.com", "theguardian.com",
    "cnn.com", "bloomberg.com", "forbes.com",
    "wikipedia.org",
]


def needs_web_search(query: str) -> bool:
    return any(p.search(query) for p in _compiled)


def _is_skippable(url: str) -> bool:
    domain = urlparse(url).netloc.lower().replace("www.", "")
    return any(skip in domain for skip in _SKIP_DOMAINS)


def _domain_priority(url: str) -> int:
    domain = urlparse(url).netloc.lower().replace("www.", "")
    for i, d in enumerate(_PRIORITY_DOMAINS):
        if d in domain:
            return i
    return len(_PRIORITY_DOMAINS)


def _extract_year(query: str) -> str | None:
    years = re.findall(r'\b(20\d{2})\b', query)
    return max(years) if years else None


# ─── Source 0: Jolpica F1 API ─────────────────────────────────────────────────

def _is_f1_query(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in ["f1", "formula 1", "formula one", "formula-1", "grand prix"])


def _f1_api_data(query: str) -> str:
    year = _extract_year(query) or datetime.now().year
    result_parts = []

    try:
        url = f"https://api.jolpi.ca/ergast/f1/{year}/driverStandings/"
        r = requests.get(url, headers=_HEADERS, timeout=8)
        if r.status_code == 200:
            slist = r.json().get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
            if slist:
                entries = slist[0].get("DriverStandings", [])
                rnd     = slist[0].get("round", "?")
                season  = slist[0].get("season", year)
                table   = f"## {season} F1 Driver Championship (after Round {rnd})\n\n"
                table  += "| Pos | Driver | Team | Points | Wins |\n"
                table  += "|-----|--------|------|--------|------|\n"
                for d in entries:
                    drv  = d.get("Driver", {})
                    name = f"{drv.get('givenName','')} {drv.get('familyName','')}"
                    team = d.get("Constructors", [{}])[0].get("name", "?")
                    table += f"| {d.get('position','?')} | {name} | {team} | {d.get('points','0')} | {d.get('wins','0')} |\n"
                table += f"\nSource: https://api.jolpi.ca/ergast/f1/{year}/driverStandings/"
                result_parts.append(table)
    except Exception as e:
        logging.debug(f"F1 driver standings error: {e}")

    try:
        url = f"https://api.jolpi.ca/ergast/f1/{year}/constructorStandings/"
        r = requests.get(url, headers=_HEADERS, timeout=8)
        if r.status_code == 200:
            slist = r.json().get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
            if slist:
                entries = slist[0].get("ConstructorStandings", [])
                season  = slist[0].get("season", year)
                rnd     = slist[0].get("round", "?")
                table   = f"\n## {season} F1 Constructor Championship (after Round {rnd})\n\n"
                table  += "| Pos | Team | Points | Wins |\n"
                table  += "|-----|------|--------|------|\n"
                for c in entries:
                    ctor = c.get("Constructor", {})
                    table += f"| {c.get('position','?')} | {ctor.get('name','?')} | {c.get('points','0')} | {c.get('wins','0')} |\n"
                table += f"\nSource: https://api.jolpi.ca/ergast/f1/{year}/constructorStandings/"
                result_parts.append(table)
    except Exception as e:
        logging.debug(f"F1 constructor standings error: {e}")

    return "\n".join(result_parts) if result_parts else ""


# ─── Source 1: DDGS — Proper DuckDuckGo Python API ───────────────────────────

def _ddgs_search(query: str, max_results: int = 6) -> list[dict]:
    """
    Use the ddgs Python package (proper API) instead of scraping HTML.
    Returns list of {title, href, body} dicts sorted by domain priority.
    """
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results + 3)
            if not raw:
                return []
            results = [
                {"title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")}
                for r in raw
                if r.get("href") and not _is_skippable(r.get("href", ""))
            ]
            results.sort(key=lambda x: _domain_priority(x["href"]))
            return results[:max_results]
    except Exception as e:
        logging.warning(f"DDGS search failed: {e}")
        return []


def _ddgs_news(query: str, max_results: int = 4) -> list[dict]:
    """Fetch latest news articles via DDGS news search."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw = ddgs.news(query, max_results=max_results + 2)
            if not raw:
                return []
            return [
                {"title": r.get("title", ""), "href": r.get("url", ""), "body": r.get("body", ""), "date": r.get("date", "")}
                for r in raw
                if r.get("url") and not _is_skippable(r.get("url", ""))
            ][:max_results]
    except Exception as e:
        logging.debug(f"DDGS news failed: {e}")
        return []


# ─── Source 2: Page content fetcher ──────────────────────────────────────────

def _fetch_page_text(url: str, max_chars: int = 2000) -> str:
    """Fetch and clean the main text content of a web page."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=8, allow_redirects=True)
        if r.status_code != 200:
            return ""
        if "text/html" not in r.headers.get("Content-Type", ""):
            return ""

        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "form", "noscript", "iframe", "button"]):
            tag.decompose()

        content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=re.compile(r"content|article|post|story|body", re.I))
            or soup.find("body")
        )
        if not content:
            return ""

        lines = [l.strip() for l in content.get_text(separator="\n", strip=True).splitlines() if l.strip()]
        return "\n".join(lines)[:max_chars]
    except Exception as e:
        logging.debug(f"Page fetch failed for {url}: {e}")
        return ""


# ─── Source 3: DuckDuckGo Instant Answer ─────────────────────────────────────

def _ddg_instant(query: str) -> str:
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=_HEADERS, timeout=5,
        )
        if r.status_code == 200:
            data     = r.json()
            answer   = data.get("Answer", "").strip()
            abstract = data.get("AbstractText", "").strip()
            src_url  = data.get("AbstractURL", "").strip()
            if answer:
                return f"Quick Answer: {answer}"
            if abstract:
                src = f"\nSource: {src_url}" if src_url else ""
                return f"{abstract}{src}"
    except Exception as e:
        logging.debug(f"DDG instant API failed: {e}")
    return ""


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> str:
    """
    Perform a live web search and return formatted context for the AI.
    Uses DDGS Python API (reliable) + page fetching + F1/Cricket APIs.
    """
    timestamp = datetime.now().strftime("%B %d, %Y %I:%M %p")
    lines = [
        f"[LIVE WEB SEARCH — {timestamp}]",
        f"[Query: \"{query}\"]",
        "",
    ]
    found_anything = False

    # ── 0. F1 API — exact data for F1 queries ──
    if _is_f1_query(query):
        f1_data = _f1_api_data(query)
        if f1_data:
            found_anything = True
            lines.append("=== F1 Live Standings (Official API Data) ===")
            lines.append(f1_data)
            lines.append("")

    # ── 1. DDG Instant Answer — fast direct answers ──
    instant = _ddg_instant(query)
    if instant:
        found_anything = True
        lines.append(f"=== Instant Answer ===\n{instant}\n")

    # ── 2. DDGS text search — main source of real-time info ──
    ddg_results = _ddgs_search(query, max_results=max_results)

    fetched_pages = 0
    for result in ddg_results:
        title   = result.get("title",   "").strip()
        snippet = result.get("body",    "").strip()
        href    = result.get("href",    "").strip()
        if not href:
            continue

        found_anything = True
        lines.append(f"=== {title} ===")
        lines.append(f"URL: {href}")

        # Deep-fetch content from top 2 results for accuracy
        if fetched_pages < 2:
            page_text = _fetch_page_text(href, max_chars=1800)
            if page_text and len(page_text) > 150:
                lines.append(page_text)
                fetched_pages += 1
            elif snippet:
                lines.append(f"Snippet: {snippet}")
        else:
            if snippet:
                lines.append(f"Snippet: {snippet}")

        lines.append("")

    # ── 3. DDGS news search — for news/current events queries ──
    news_keywords = ["news", "latest", "today", "breaking", "update", "happened", "announced", "launch"]
    if any(k in query.lower() for k in news_keywords):
        news_results = _ddgs_news(query, max_results=3)
        if news_results:
            lines.append("=== Latest News ===")
            for n in news_results:
                date  = n.get("date", "")
                title = n.get("title", "")
                body  = n.get("body", "")
                href  = n.get("href", "")
                date_str = f" [{date}]" if date else ""
                lines.append(f"• {title}{date_str}")
                if body:
                    lines.append(f"  {body[:200]}")
                if href:
                    lines.append(f"  Source: {href}")
            lines.append("")
            found_anything = True

    if not found_anything:
        return ""

    lines.append(
        "[CRITICAL INSTRUCTION] The above is LIVE data fetched right now on "
        + timestamp + ". "
        "Answer ONLY from the data above. "
        "Do NOT hallucinate numbers, names, or statistics not shown above. "
        "If the exact answer is not in the data, say what was found and provide the source URL."
    )
    return "\n".join(lines)
