import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

INTENTS_FILE = os.path.join(os.path.dirname(__file__), "intents.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
