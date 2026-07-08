import base64
import os
import re
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from web_search import needs_web_search, web_search

# Use absolute path so .env is found regardless of working directory
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

# ── Simple queries that don't need a web search ──────────────────────────────
# These are things the AI already knows from its system prompt (date/time)
# or things that don't need real-time data (greetings, basic math, etc.)
_SKIP_SEARCH_PATTERNS = [
    r"^(what('?s| is)( today'?s?| the current| the)? (date|day|time|year|month))[?!.]?$",
    r"^(today'?s? date|current date|what day is (it|today))[?!.]?$",
    r"^(hello|hi+|hey+|good (morning|afternoon|evening|night)|how are you|thanks?|thank you|bye|goodbye)[!?., ]*$",
    r"^(who are you|what are you|what can you do|help me|what is your name)[?!.]?$",
]
_SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SKIP_SEARCH_PATTERNS]

def _is_simple_query(q: str) -> bool:
    """Returns True if the query can be answered from system prompt alone — skip web search."""
    q = q.strip()
    return any(p.match(q) for p in _SKIP_COMPILED)


def _get_system_prompt(has_web_results=False):
    now = datetime.now()
    today = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    base = (
        f"You are lavangam.ai, an intelligent and friendly AI assistant. "
        f"Today's date and time is {today} at {time_str}. "
        f"You have access to live web search, so you can answer questions about current events, "
        f"real-time scores, prices, news, and anything happening right now. "
        f"NEVER say you have a knowledge cutoff or cannot access real-time information — you CAN via web search. "
        f"When a user greets you (e.g. 'hello', 'hi', 'hey', or any casual greeting), "
        f"simply greet them back warmly and ask how you can help — do NOT define or explain the greeting word. "
        f"Respond clearly and helpfully in markdown format."
    )

    if has_web_results:
        base += (
            f" IMPORTANT: Live web search results have been fetched and are shown above. "
            f"You MUST use ONLY these results as your source of truth. "
            f"Do NOT hallucinate or invent specific numbers, names, or facts not in the search results. "
            f"Do NOT say you lack real-time data — the search results contain current, live information. "
            f"Present facts confidently. Format standings/rankings/scores as clean markdown tables. "
            f"Cite the source URL where relevant."
        )
    else:
        base += (
            f" For questions about current events or real-time data, "
            f"answer directly using your knowledge. Do not hedge unnecessarily."
        )

    return base


def _build_messages(user_msg, history, file_text=None, image_path=None, has_web_results=False):
    """Build OpenAI-compatible messages array from history + current query."""
    messages = [{"role": "system", "content": _get_system_prompt(has_web_results=has_web_results)}]

    # Inject last 4 exchanges for context
    for past in history[-4:]:
        if past.get("user"): messages.append({"role": "user",      "content": past["user"]})
        if past.get("bot"):  messages.append({"role": "assistant", "content": past["bot"]})

    # Build current user content
    current_query = user_msg
    if file_text:
        current_query = f"[UPLOADED FILE DATA]\n{file_text}\n\n{current_query}"

    if image_path and os.path.exists(image_path):
        import mimetypes
        mime_type, _ = mimetypes.guess_type(image_path)
        with open(image_path, "rb") as f:
            enc = base64.b64encode(f.read()).decode("utf-8")
        messages.append({"role": "user", "content": [
            {"type": "text",      "text": current_query},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type or 'image/jpeg'};base64,{enc}"}}
        ]})
    else:
        messages.append({"role": "user", "content": current_query})

    return messages


def _call_nvidia(messages, is_search_query=False):
    """
    NVIDIA NIM API.
    - Simple/fast queries  → 8B (fast, 15s timeout)
    - Search-augmented queries → try 70B (25s timeout) then fall back to 8B
    """
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        logging.warning("NVIDIA_API_KEY not set.")
        return None

    # For search-augmented responses we want the smarter model;
    # for everything else 8B is fast and perfectly capable.
    if is_search_query:
        model_plan = [
            ("meta/llama-3.3-70b-instruct", 25),   # smarter, but cap at 25s
            ("meta/llama-3.1-8b-instruct",  20),   # reliable fallback
        ]
    else:
        model_plan = [
            ("meta/llama-3.1-8b-instruct", 15),    # fast for simple queries
        ]

    for model, timeout in model_plan:
        try:
            res = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":      model,
                    "messages":   messages,
                    "max_tokens": 1024 if not is_search_query else 2048,
                    "stream":     False,
                    "temperature": 0.3,
                },
                timeout=timeout,
            )
            if res.status_code == 200:
                content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    logging.info(f"NVIDIA model used: {model}")
                    return content.strip()
            else:
                logging.warning(f"NVIDIA {model} failed: {res.status_code} {res.text[:200]}")
        except requests.exceptions.Timeout:
            logging.warning(f"NVIDIA {model} timed out after {timeout}s — trying next model")
        except Exception as e:
            logging.warning(f"NVIDIA {model} exception: {e}")

    return None


def get_ai_response(user_msg, history, image_path=None, file_text=None):
    """
    Main entry point.
    - Skips web search for simple/greeting queries (fast path)
    - For real-time queries: searches web, injects results, uses smarter model
    """

    enriched_msg     = user_msg
    has_web_results  = False
    is_search_query  = False

    # Decide whether web search is needed
    needs_search = (
        not image_path
        and not file_text
        and needs_web_search(user_msg)
        and not _is_simple_query(user_msg)
    )

    if needs_search:
        logging.info(f"Web search triggered for: {user_msg[:80]}")
        search_context = web_search(user_msg)
        if search_context:
            has_web_results = True
            is_search_query = True
            enriched_msg = (
                f"{search_context}\n\n"
                f"CRITICAL: The above are LIVE web search results fetched right now. "
                f"Answer the user's question ONLY from the above content. "
                f"Do NOT invent data not present above. "
                f"If the content doesn't have the exact answer, say what was found "
                f"and provide the source URL.\n\n"
                f"User question: {user_msg}"
            )
        else:
            logging.info("Web search returned no results — answering from model knowledge.")

    messages = _build_messages(enriched_msg, history, file_text, image_path, has_web_results=has_web_results)

    result = _call_nvidia(messages, is_search_query=is_search_query)
    if result:
        return result

    return "⚠️ **AI is temporarily unavailable.** Please try again in a moment."
