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

from flask import Flask, request, jsonify, render_template
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
import webbrowser
import threading

login_tokens = {}

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

firebase_initialized = False
try:
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

# === DESKTOP AUTH BRIDGE ROUTES ===

@app.route('/login')
@app.route('/desktop-login')
@app.route('/desktop login')
@app.route('/desktop%20login')
def desktop_login():
    session_id = request.args.get('session_id')
    return render_template('desktop_login.html', session_id=session_id)

@app.route('/api/open-browser')
def open_browser():
    url = request.args.get('url')
    if url:
        import platform
        import subprocess
        def open_url():
            try:
                if platform.system() == 'Windows':
                    # Use cmd /c start for most reliable browser opening on Windows
                    subprocess.run(['cmd', '/c', 'start', '', url], shell=False, check=False)
                else:
                    webbrowser.open_new(url)
            except Exception as e:
                logging.error(f"Error opening browser: {e}")
                try:
                    webbrowser.open_new(url)  # fallback
                except Exception as e2:
                    logging.error(f"Fallback browser open also failed: {e2}")
                
        threading.Thread(target=open_url, daemon=True).start()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/api/exchange-token', methods=['POST'])
def exchange_token():
    data = request.json
    id_token = data.get('idToken')
    session_id = data.get('session_id')
    
    if not id_token or not session_id:
        return jsonify({"status": "error", "message": "Missing token"}), 400

    if firebase_initialized:
        try:
            # Verify the Firebase ID token from the browser
            decoded = auth.verify_id_token(id_token, clock_skew_seconds=60)
            uid = decoded['uid']
            # Store the token + user info so desktop can use it directly
            login_tokens[session_id] = {
                'token': id_token,
                'uid': uid,
                'email': decoded.get('email', ''),
                'name': decoded.get('name', decoded.get('email', 'User'))
            }
            logging.info(f"Token verified for uid: {uid}")
        except Exception as e:
            logging.error(f"Token exchange error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 400
    else:
        # Mock mode fallback
        login_tokens[session_id] = {
            'token': id_token,
            'uid': 'mock_user_123',
            'email': 'mock@user.com',
            'name': 'Mock User'
        }

    return jsonify({"status": "success"})

@app.route('/api/poll-token')
def poll_token():
    session_id = request.args.get('session_id')
    if session_id in login_tokens:
        data = login_tokens.pop(session_id)
        return jsonify({
            "status": "success",
            "token": data['token'],
            "user": {
                "uid": data['uid'],
                "email": data['email'],
                "name": data['name']
            }
        })
    return jsonify({"status": "pending"})

# === END DESKTOP AUTH BRIDGE ===

@app.route('/')
def index():
    response = render_template('index.html')
    # Use make_response to add headers to avoid caching issues in Pywebview
    from flask import make_response
    r = make_response(response)
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
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
    import webview
    import threading
    import time as time_mod
    import urllib.request

    def start_server():
        import logging as _log
        _log.getLogger('werkzeug').setLevel(_log.ERROR)  # suppress Flask noise
        app.run(port=5050, use_reloader=False, threaded=True)

    def wait_for_server(url, timeout=15):
        """Poll until Flask server is up, then open WebView."""
        deadline = time_mod.time() + timeout
        while time_mod.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=1)
                return True
            except Exception:
                time_mod.sleep(0.2)
        return False

    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    base_url = 'http://localhost:5050'
    if wait_for_server(base_url, timeout=60):
        window = webview.create_window(
            'lavangam.ai',
            base_url,
            width=1200,
            height=800,
            resizable=True,
            min_size=(800, 600)
        )
        webview.start(debug=False)
    else:
        print("[ERROR] Flask server did not start in time. Try running again.")
