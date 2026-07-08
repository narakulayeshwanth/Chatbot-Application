"""
web_search.py — Real-time web search with dedicated APIs.

Priority chain:
  0. F1 queries  → Jolpica F1 API (exact standings JSON, no hallucination possible)
  1. Wikipedia   → structured encyclopedia text (background info)
  2. DuckDuckGo  → instant answers + HTML snippets from real pages
"""

import re
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote

# ─── Realtime trigger patterns ─────────────────────────────────────────────────
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
    "facebook.com", "tiktok.com", "pinterest.com",
]

_PRIORITY_DOMAINS = [
    "bbc.com", "reuters.com", "apnews.com", "espn.com",
    "motorsport.com", "cricinfo.com", "sportingnews.com",
    "theguardian.com", "ndtv.com", "hindustantimes.com",
    "timesofindia.com", "cnn.com", "wikipedia.org",
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


# ─── Source 0: Jolpica F1 API (Ergast replacement — exact standings JSON) ──────

def _is_f1_query(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in ["f1", "formula 1", "formula one", "formula-1", "grand prix", "f1 standings", "f1 championship"])


def _f1_api_data(query: str) -> str:
    """
    Fetch F1 standings from the Jolpica API (open-source Ergast replacement).
    Returns current driver + constructor standings as formatted markdown tables.
    """
    year = _extract_year(query) or datetime.now().year
    q = query.lower()

    result_parts = []

    # ── Driver standings ──────────────────────────────────────────────────
    try:
        url = f"https://api.jolpi.ca/ergast/f1/{year}/driverStandings/"
        r = requests.get(url, headers=_HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            slist = (data.get("MRData", {})
                         .get("StandingsTable", {})
                         .get("StandingsLists", []))
            if slist:
                entries    = slist[0].get("DriverStandings", [])
                rnd        = slist[0].get("round", "?")
                season     = slist[0].get("season", year)

                table  = f"## {season} F1 Driver Championship (after Round {rnd})\n\n"
                table += "| Pos | Driver | Nationality | Team | Points | Wins |\n"
                table += "|-----|--------|-------------|------|--------|------|\n"
                for d in entries:
                    drv   = d.get("Driver", {})
                    name  = f"{drv.get('givenName','')} {drv.get('familyName','')}"
                    nat   = drv.get("nationality", "")
                    team  = d.get("Constructors", [{}])[0].get("name", "?")
                    pos   = d.get("position", "?")
                    pts   = d.get("points", "0")
                    wins  = d.get("wins", "0")
                    table += f"| {pos} | {name} | {nat} | {team} | {pts} | {wins} |\n"
                table += f"\nSource: https://api.jolpi.ca/ergast/f1/{year}/driverStandings/"
                result_parts.append(table)
    except Exception as e:
        logging.debug(f"F1 driver standings API error: {e}")

    # ── Constructor standings ─────────────────────────────────────────────
    try:
        url = f"https://api.jolpi.ca/ergast/f1/{year}/constructorStandings/"
        r = requests.get(url, headers=_HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            slist = (data.get("MRData", {})
                         .get("StandingsTable", {})
                         .get("StandingsLists", []))
            if slist:
                entries = slist[0].get("ConstructorStandings", [])
                season  = slist[0].get("season", year)
                rnd     = slist[0].get("round", "?")

                table  = f"\n## {season} F1 Constructor Championship (after Round {rnd})\n\n"
                table += "| Pos | Team | Nationality | Points | Wins |\n"
                table += "|-----|------|-------------|--------|------|\n"
                for c in entries:
                    ctor = c.get("Constructor", {})
                    name = ctor.get("name", "?")
                    nat  = ctor.get("nationality", "")
                    pos  = c.get("position", "?")
                    pts  = c.get("points", "0")
                    wins = c.get("wins", "0")
                    table += f"| {pos} | {name} | {nat} | {pts} | {wins} |\n"
                table += f"\nSource: https://api.jolpi.ca/ergast/f1/{year}/constructorStandings/"
                result_parts.append(table)
    except Exception as e:
        logging.debug(f"F1 constructor standings API error: {e}")

    # ── Last race result ──────────────────────────────────────────────────
    if "result" in query.lower() or "last race" in query.lower() or "latest race" in query.lower():
        try:
            url = f"https://api.jolpi.ca/ergast/f1/{year}/last/results/"
            r = requests.get(url, headers=_HEADERS, timeout=8)
            if r.status_code == 200:
                data   = r.json()
                races  = (data.get("MRData", {})
                              .get("RaceTable", {})
                              .get("Races", []))
                if races:
                    race  = races[0]
                    rname = race.get("raceName", "")
                    rnd   = race.get("round", "?")
                    date  = race.get("date", "")
                    results = race.get("Results", [])

                    table  = f"\n## Last Race: {rname} (Round {rnd}, {date})\n\n"
                    table += "| Pos | Driver | Team | Grid | Points |\n"
                    table += "|-----|--------|------|------|--------|\n"
                    for res in results[:10]:
                        drv  = res.get("Driver", {})
                        name = f"{drv.get('givenName','')} {drv.get('familyName','')}"
                        team = res.get("Constructor", {}).get("name", "?")
                        pos  = res.get("position", "?")
                        grid = res.get("grid", "?")
                        pts  = res.get("points", "0")
                        table += f"| {pos} | {name} | {team} | {grid} | {pts} |\n"
                    result_parts.append(table)
        except Exception as e:
            logging.debug(f"F1 last race API error: {e}")

    return "\n".join(result_parts) if result_parts else ""


# ─── Source 1: Wikipedia API ───────────────────────────────────────────────────

def _wikipedia_fetch_title(title: str, max_chars: int = 3500) -> str:
    """Fetch a Wikipedia article by exact title."""
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action":      "query",
                "prop":        "extracts",
                "explaintext": True,
                "exintro":     True,   # intro section only (has overview, no broken tables)
                "titles":      title,
                "format":      "json",
            },
            headers=_HEADERS,
            timeout=8,
        )
        if r.status_code != 200:
            return ""
        pages = r.json().get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1":
                return ""
            extract = page.get("extract", "").strip()
            if extract and len(extract) > 100:
                wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                return f"[Wikipedia: {title}]\n{extract[:max_chars]}\nSource: {wiki_url}"
    except Exception as e:
        logging.debug(f"Wikipedia fetch failed for '{title}': {e}")
    return ""


def _wikipedia_search(query: str) -> str:
    """
    Smart Wikipedia search:
    1. Direct title construction for known sport/event patterns.
    2. Fall back to Wikipedia search API with year-aware scoring.
    """
    year    = _extract_year(query)
    q_lower = query.lower()

    # Step 1: direct title construction
    candidate_titles = []
    if year:
        if any(k in q_lower for k in ["f1", "formula 1", "formula one", "grand prix", "formula-1"]):
            candidate_titles += [f"{year} Formula One World Championship"]
        if "ipl" in q_lower:
            candidate_titles.append(f"{year} Indian Premier League")
        if "cricket" in q_lower and "world cup" in q_lower:
            candidate_titles.append(f"{year} ICC Cricket World Cup")
        if "world cup" in q_lower and any(k in q_lower for k in ["football", "soccer", "fifa"]):
            candidate_titles.append(f"{year} FIFA World Cup")
        if "premier league" in q_lower:
            candidate_titles.append(f"{year}–{str(int(year)+1)[2:]} Premier League")
        if "nba" in q_lower:
            candidate_titles.append(f"{year}–{str(int(year)+1)[2:]} NBA season")
        if "champions league" in q_lower:
            candidate_titles.append(f"{year}–{str(int(year)+1)[2:]} UEFA Champions League")

    for title in candidate_titles:
        result = _wikipedia_fetch_title(title)
        if result:
            logging.info(f"Wikipedia direct hit: {title}")
            return result

    # Step 2: fallback to search API
    try:
        hits_r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search",
                    "srsearch": query, "srlimit": 5, "format": "json"},
            headers=_HEADERS, timeout=8,
        )
        if hits_r.status_code != 200:
            return ""
        hits = hits_r.json().get("query", {}).get("search", [])
        if not hits:
            return ""

        PREF = ["world championship", "season", "grand prix", "championship", "cup"]
        BAD  = ["academy", "f4", "f3", "f2", "junior", "support", "reserve", "list of"]

        def _score(title: str) -> int:
            t = title.lower()
            s = 0
            if year and year in t: s += 10
            for k in PREF: s += 2 if k in t else 0
            for k in BAD:  s -= 6 if k in t else 0
            return s

        best = max(hits, key=lambda h: _score(h["title"]))
        return _wikipedia_fetch_title(best["title"])
    except Exception as e:
        logging.debug(f"Wikipedia search API failed: {e}")
    return ""


# ─── Source 2: DuckDuckGo Instant Answer ──────────────────────────────────────

def _ddg_instant(query: str) -> str:
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=_HEADERS, timeout=6,
        )
        if r.status_code == 200:
            data     = r.json()
            answer   = data.get("Answer",       "").strip()
            abstract = data.get("AbstractText", "").strip()
            src_url  = data.get("AbstractURL",  "").strip()
            if answer:
                return f"Quick Answer: {answer}"
            if abstract:
                src = f"\nSource: {src_url}" if src_url else ""
                return f"{abstract}{src}"
    except Exception as e:
        logging.debug(f"DDG instant API failed: {e}")
    return ""


# ─── Source 3: DuckDuckGo HTML + Page Fetch ────────────────────────────────────

def _ddg_html_results(query: str, max_results: int = 5) -> list[dict]:
    results = []
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=_HEADERS,
            timeout=10,
        )
        if r.status_code != 200:
            return results

        soup = BeautifulSoup(r.text, "lxml")
        for item in soup.select(".result__body")[:max_results + 2]:
            title_tag   = item.select_one(".result__title a")
            snippet_tag = item.select_one(".result__snippet")
            title   = title_tag.get_text(strip=True)   if title_tag   else ""
            href    = title_tag.get("href", "")         if title_tag   else ""
            snippet = snippet_tag.get_text(strip=True)  if snippet_tag else ""

            if href and "uddg=" in href:
                qs   = parse_qs(urlparse(href).query)
                href = unquote(qs.get("uddg", [href])[0])

            if href and not _is_skippable(href):
                results.append({"title": title, "body": snippet, "href": href})
    except Exception as e:
        logging.debug(f"DDG HTML scrape failed: {e}")
    return results


def _fetch_page_text(url: str, max_chars: int = 2500) -> str:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=8, allow_redirects=True)
        if r.status_code != 200:
            return ""
        if "text/html" not in r.headers.get("Content-Type", ""):
            return ""

        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script","style","nav","footer","header","aside","form","noscript","iframe","button"]):
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


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 4) -> str:
    """
    Perform a live web search and return a formatted context string.
    Priority: F1 API → Wikipedia → DuckDuckGo → Page fetch.
    """
    timestamp = datetime.now().strftime("%B %d, %Y %I:%M %p")
    lines = [
        f"[LIVE WEB SEARCH — {timestamp}]",
        f"[Query: \"{query}\"]",
        "",
    ]
    found_anything = False

    # ── 0. F1 API — best for F1 standings (exact, no hallucination) ──
    if _is_f1_query(query):
        f1_data = _f1_api_data(query)
        if f1_data:
            found_anything = True
            lines.append("=== F1 Live Standings (Official API Data) ===")
            lines.append(f1_data)
            lines.append("")
            # For F1 queries we have exact data — don't need Wikipedia
            # But still add DuckDuckGo for latest news context
        else:
            logging.info("F1 API returned no data — falling back to Wikipedia/DDG")

    # ── 1. Wikipedia — background context ──
    if not _is_f1_query(query):   # Skip Wiki for F1 (standings aren't in plain text anyway)
        wiki_text = _wikipedia_search(query)
        if wiki_text:
            found_anything = True
            lines.append("=== Wikipedia ===")
            lines.append(wiki_text)
            lines.append("")

    # ── 2. DuckDuckGo Instant Answer ──
    instant = _ddg_instant(query)
    if instant:
        found_anything = True
        lines.append(f"=== Instant Answer ===\n{instant}\n")

    # ── 3. DuckDuckGo HTML + page fetch ──
    ddg_results = _ddg_html_results(query, max_results=max_results + 2)
    ddg_results.sort(key=lambda x: _domain_priority(x.get("href", "")))

    fetched = 0
    for result in ddg_results[:max_results]:
        title   = result.get("title",   "").strip()
        snippet = result.get("body",    "").strip()
        href    = result.get("href",    "").strip()
        if not href:
            continue

        found_anything = True
        lines.append(f"=== {title} ===")
        lines.append(f"URL: {href}")

        if fetched < 2:
            page_text = _fetch_page_text(href, max_chars=2000)
            if page_text and len(page_text) > 150:
                lines.append(page_text)
                fetched += 1
            elif snippet:
                lines.append(f"Snippet: {snippet}")
        else:
            if snippet:
                lines.append(f"Snippet: {snippet}")

        lines.append("")

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
