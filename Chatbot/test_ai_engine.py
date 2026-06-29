import os
from ai_engine import get_ai_response
history = [{"user": "hello", "bot": "hi"}, {"user": "tell me what was ipl", "bot": "\u26a0\ufe0f **AI Unavailable**"}]
result = get_ai_response("what is it", history)
with open("output.txt", "w", encoding="utf-8") as f: f.write(result)
