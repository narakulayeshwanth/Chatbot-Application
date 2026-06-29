import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")

print("=" * 60)
print("API KEY STATUS")
print("=" * 60)
print(f"OpenRouter Key : {'SET ✅' if OPENROUTER_KEY else 'MISSING ❌'}")
print(f"NVIDIA Key     : {'SET ✅' if NVIDIA_KEY else 'MISSING ❌'}")
print()

# --- Test OpenRouter ---
print("=" * 60)
print("TESTING OPENROUTER API")
print("=" * 60)

models_to_test = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-4-scout:free",
    "mistralai/mistral-7b-instruct:free",
]

openrouter_ok = False
for model in models_to_test:
    print(f"\n  Trying model: {model}")
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5050",
                "X-Title": "lavangam.ai"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "max_tokens": 10
            },
            timeout=20
        )
        if res.status_code == 200:
            content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  Status: {res.status_code} ✅  Response: {content.strip()!r}")
            openrouter_ok = True
            break
        else:
            print(f"  Status: {res.status_code} ❌  Body: {res.text[:200]}")
    except Exception as e:
        print(f"  Error: {e} ❌")

if not openrouter_ok:
    print("\n  ❌ ALL OpenRouter models FAILED")

# --- Test NVIDIA ---
print()
print("=" * 60)
print("TESTING NVIDIA NIM API")
print("=" * 60)

nvidia_ok = False
nvidia_models = [
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
]

for model in nvidia_models:
    print(f"\n  Trying model: {model}")
    try:
        res = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "max_tokens": 10,
                "stream": False
            },
            timeout=20
        )
        if res.status_code == 200:
            content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  Status: {res.status_code} ✅  Response: {content.strip()!r}")
            nvidia_ok = True
            break
        else:
            print(f"  Status: {res.status_code} ❌  Body: {res.text[:200]}")
    except Exception as e:
        print(f"  Error: {e} ❌")

if not nvidia_ok:
    print("\n  ❌ ALL NVIDIA models FAILED")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  OpenRouter : {'✅ WORKING' if openrouter_ok else '❌ NOT WORKING'}")
print(f"  NVIDIA NIM : {'✅ WORKING' if nvidia_ok else '❌ NOT WORKING'}")
if not openrouter_ok and not nvidia_ok:
    print("\n  ⚠️  BOTH APIs are down — the bot has no AI engine!")
    print("  Check your API keys or top up credits.")
print("=" * 60)
