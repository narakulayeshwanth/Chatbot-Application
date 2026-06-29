import traceback
from ai_engine import get_ai_response
from ml_engine import load_ml_assets, predict_class
from memory import load_memory

user_id = "XcVNGWBTmgcJCcmICXDsD9t0utA2"
session_id = "acdef3cd-42e9-44e3-9c6a-366de686f806"

load_ml_assets()

history = load_memory(user_id, session_id)
msg = "hoi"
try:
    tag, confidence = predict_class(msg)
    print(f"Tag: {tag}, Confidence: {confidence}")
    if confidence > 0.7 and tag != "unknown":
        print("Using ML")
    else:
        print("Using AI")
        resp = get_ai_response(msg, history)
        print("AI Response:", resp)
except Exception as e:
    print("EXCEPTION:")
    traceback.print_exc()
