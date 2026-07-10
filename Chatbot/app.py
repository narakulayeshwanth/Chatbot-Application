import sys
import io

# SafeStdout: prevents Keras/TF from crashing Flask threads on Windows
# with OSError [Errno 22] when it tries to flush stdout to an invalid handle.
class _SafeStdout:
    def __init__(self, wrapped):
        self._wrapped = wrapped
    def write(self, msg):
        try:
            self._wrapped.write(msg)
        except OSError:
            pass
    def flush(self):
        try:
            self._wrapped.flush()
        except OSError:
            pass
    def __getattr__(self, name):
        return getattr(self._wrapped, name)

if not isinstance(sys.stdout, _SafeStdout):
    sys.stdout = _SafeStdout(sys.stdout)
if not isinstance(sys.stderr, _SafeStdout):
    sys.stderr = _SafeStdout(sys.stderr)

from flask import Flask, request, jsonify, render_template, make_response
import logging
import re
import traceback
import os
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from time import time
from ml_engine import predict_class, get_ml_response, load_ml_assets
from ai_engine import get_ai_response
from memory import load_memory, save_memory, get_all_sessions, delete_session
import uuid
import firebase_admin
from firebase_admin import credentials, auth


app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

firebase_initialized = False
try:
    cred_path = os.environ.get(
        "FIREBASE_CRED_PATH",
        "/etc/secrets/firebase-adminsdk.json"
    )
    if not os.path.exists(cred_path):
        cred_path = os.path.join(os.path.dirname(__file__), "firebase-adminsdk.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        logging.info("Firebase Admin SDK initialized successfully.")
    else:
        logging.warning("firebase-adminsdk.json not found! Auth will fallback to mock_user_123.")
except Exception as e:
    logging.error(f"Firebase init error: {e}")

def get_user_id():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split("Bearer ")[1]
    
    if not firebase_initialized:
        return "mock_user_123"
        
    try:
        decoded = auth.verify_id_token(token, clock_skew_seconds=60)
        return decoded['uid']
    except Exception as e:
        logging.error(f"Auth error: {e}")
        return None

CONFIDENCE_THRESHOLD = 0.7
last_request = {}

load_ml_assets()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def is_rate_limited(user_ip):
    now = time()
    if user_ip in last_request and now - last_request[user_ip] < 1:
        return True
    last_request[user_ip] = now
    return False

def normalize_input(text):
    """Collapse 3+ repeated characters to 2 so 'hellooo' → 'helloo' → matched as 'hello'.
    Also handles common elongated greetings like 'heyyyy', 'hiii', etc."""
    # Collapse 3+ repeated chars to 1 (e.g. hellooo → hello, heyyyy → hey)
    normalized = re.sub(r'(.)\1{2,}', r'\1', text)
    return normalized.strip()

def rule_based(msg):
    if msg.lower().strip() == "ping":
        return "pong"
    return None

def extract_text_from_file(filepath):
    text = ""
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ""
    if ext == 'pdf':
        try:
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()
        except:
            pass
    elif ext in ['txt', 'csv', 'md', 'py', 'js', 'json', 'html']:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except:
            pass
    return text

# === END DESKTOP AUTH BRIDGE (removed — web version uses Firebase signInWithPopup) ===



@app.route('/')
def index():
    r = make_response(render_template('index.html'))
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r


@app.route('/sessions', methods=['GET'])
def get_sessions():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"sessions": get_all_sessions(user_id)})

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"history": load_memory(user_id, session_id)})

@app.route('/session/<session_id>', methods=['DELETE'])
def remove_session(session_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    if delete_session(user_id, session_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/chat', methods=['POST'])
def chat():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"response": "Please log in to continue.", "confidence": 0.0}), 401

    # Handle both JSON and Data-Form (for files)
    msg = ""
    file_path = None
    image_path = None
    file_text = None
    session_id = None
    
    if request.is_json:
        data = request.get_json()
        msg = data.get("message", "")
        session_id = data.get("session_id")
    else:
        msg = request.form.get("message", "")
        session_id = request.form.get("session_id")
        file = request.files.get("file")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Identify multimodal payload type
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                image_path = file_path
            else:
                file_text = extract_text_from_file(file_path)

    msg = msg.lower().strip()
    
    if not msg and not file_path:
        return jsonify({"response": "Say something 🚀 or upload a file!"})
        
    if not session_id:
        session_id = str(uuid.uuid4())
        
    if is_rate_limited(session_id):
        return jsonify({"response": "⏳ Slow down, human 🚀"})
        
    response = ""
    history = load_memory(user_id, session_id)
    confidence = 0.0

    try:
        response = rule_based(msg)

        if not response:
            try:
                # Bypass ML Engine if Multimodal input is provided
                if not file_path:
                    ml_input = normalize_input(msg)  # collapse hellooo → hello, heyyyy → hey
                    try:
                        tag, confidence = predict_class(ml_input)
                    except Exception as ml_err:
                        logging.warning(f"ML engine failed, falling back to AI: {ml_err}")
                        tag, confidence = "unknown", 0.0

                    if confidence > CONFIDENCE_THRESHOLD and tag != "unknown":
                        response = get_ml_response(tag)
                    else:
                        response = get_ai_response(msg, history)
                else:
                    response = get_ai_response(msg, history, image_path, file_text)
            except Exception as e:
                with open("error_log.txt", "w") as f:
                    f.write(traceback.format_exc())
                logging.error(f"Engine error: {traceback.format_exc()}")
                # Fall back to AI engine instead of showing raw error
                try:
                    response = get_ai_response(msg, history)
                except Exception:
                    response = "⚠️ I'm having trouble right now. Please try again."
                confidence = 0.0
                
        # Clean up temp file footprint
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
                
        save_memory(user_id, session_id, msg or "[File Uploaded]", response)
        logging.info(f"[USER]: {msg} [FILE]: {file_path}")
        logging.info(f"[BOT]: {response}")
        logging.info(f"[CONFIDENCE]: {confidence:.2f}" if confidence else f"[CONFIDENCE]: N/A")
        
        return jsonify({"response": response, "confidence": float(confidence), "session_id": session_id})
    except Exception as e:
        print(e)
        return jsonify({"response": "Server error", "confidence": 0.0}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logging.info(f"Starting lavangam.ai web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)

