import base64
import os
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from web_search import needs_web_search, web_search

# Use absolute path so .env is found regardless of working directory
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

def _get_system_prompt(has_web_results=False):
    now = datetime.now()
    today = now.strftime("%A, %B %d, %Y")  # e.g. "Wednesday, May 21, 2026"
    time_str = now.strftime("%I:%M %p")    # e.g. "04:08 PM"

    base = (
        f"You are lavangam.ai, an intelligent and friendly AI assistant. "
        f"The current date and time is {today} at {time_str}. "
        f"Your knowledge is current through May 2026 and updates automatically via live web search for real-time queries. "
        f"When a user greets you (e.g. 'hello', 'hi', 'hey', or any casual greeting), "
        f"simply greet them back warmly and ask how you can help — do NOT define or explain the greeting word. "
        f"Respond clearly and helpfully in markdown format."
    )

    if has_web_results:
        base += (
            f" IMPORTANT: Live web search results have been fetched and injected into this conversation for this query. "
            f"You MUST use these search results as your PRIMARY and ONLY source of truth for this answer. "
            f"Do NOT say you lack real-time data, do NOT say your knowledge is limited — the search results contain current data. "
            f"Present the information confidently, accurately, and cite the sources provided. "
            f"If the search results contain a table, points table, standings, or rankings, format them as a proper markdown table."
        )
    else:
        base += (
            f" For very recent events after May 2026, live web search will automatically retrieve current data. "
            f"Always answer based on the most current information available."
        )

    return base

def _build_messages(user_msg, history, file_text=None, image_path=None, has_web_results=False):
    """Build OpenAI-compatible messages array from history + current query."""
    messages = [{"role": "system", "content": _get_system_prompt(has_web_results=has_web_results)}]

    # Inject last 4 exchanges for context
    for past in history[-4:]:
        if past.get("user"): messages.append({"role": "user", "content": past["user"]})
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
            {"type": "text", "text": current_query},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type or 'image/jpeg'};base64,{enc}"}}
        ]})
    else:
        messages.append({"role": "user", "content": current_query})

    return messages


def _call_openrouter(messages):
    """DISABLED — OpenRouter API key was exposed and revoked. Do not use."""
    logging.warning("OpenRouter is disabled (API key was exposed). Skipping.")
    return None


def _call_nvidia(messages):
    """Primary: NVIDIA NIM API (LLaMA 3.3 70B)."""
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        logging.warning("NVIDIA_API_KEY not set.")
        return None

    # NVIDIA NIM models to try in order (updated working models)
    models = [
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.3-70b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
    ]

    for model in models:
        try:
            res = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={"model": model, "messages": messages, "max_tokens": 1500, "stream": False},
                timeout=60
            )
            if res.status_code == 200:
                content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    logging.info(f"NVIDIA model used: {model}")
                    return content.strip()
            else:
                logging.warning(f"NVIDIA {model} failed: {res.status_code} {res.text[:200]}")
        except Exception as e:
            logging.warning(f"NVIDIA {model} exception: {e}")
            continue

    return None


def _call_gemini(messages):
    """DISABLED — Gemini is not the active provider. NVIDIA NIM is the sole provider."""
    logging.warning("Gemini is disabled. NVIDIA NIM is the sole active provider.")
    return None


def get_ai_response(user_msg, history, image_path=None, file_text=None):
    """
    Main entry point. NVIDIA NIM is the ONLY active provider.
    Auto-injects live web search results for real-time queries (current through May 2026+).
    OpenRouter and Gemini are DISABLED (OpenRouter key was exposed and revoked).
    """

    # Auto web search: if query needs current data, fetch live results and inject
    enriched_msg = user_msg
    has_web_results = False

    if not image_path and not file_text and needs_web_search(user_msg):
        search_context = web_search(user_msg)
        if search_context:
            has_web_results = True
            enriched_msg = (
                f"{search_context}\n\n"
                f"REMINDER: You have been given live web search results above. "
                f"Use ONLY these results to answer. Do NOT say you lack current data.\n\n"
                f"User question: {user_msg}"
            )

    messages = _build_messages(enriched_msg, history, file_text, image_path, has_web_results=has_web_results)

    # NVIDIA NIM — sole active provider
    result = _call_nvidia(messages)
    if result:
        return result

    return "⚠️ **NVIDIA AI is temporarily unavailable.** Please check your API key or try again in a moment."
