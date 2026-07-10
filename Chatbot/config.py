import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Legacy — not used (NVIDIA NIM is active provider)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

INTENTS_FILE = os.path.join(os.path.dirname(__file__), "intents.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
