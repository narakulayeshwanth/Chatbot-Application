#  (lavangam.ai)

A hybrid AI-powered chatbot with a sleek desktop GUI and web interface, featuring Firebase authentication, multi-modal file support, and a custom ML engine.

---

## ✨ Features

- 💬 **Conversational AI** — Powered by a hybrid engine (ML + Gemini/OpenRouter LLM)
- 🖥️ **Desktop App** — Native window via PyWebView (no browser needed)
- 🌐 **Web Interface** — Accessible at `http://localhost:5000`
- 🔐 **Firebase Authentication** — Google login support
- 📄 **Multi-modal Support** — Upload PDFs, images, and text files
- 🧠 **Persistent Memory** — Chat history saved in `memory.json`
- ⌨️ **CLI Mode** — Text-based interaction with typing effect

---

## 📁 Project Structure

```
Chatbot/
├── app.py                  # Main Flask + PyWebView application
├── ai_engine.py            # Hybrid AI response engine
├── ml_engine.py            # TensorFlow/scikit-learn ML model
├── train.py                # Model training script
├── cli.py                  # Command-line interface
├── memory.py               # Chat history persistence
├── config.py               # App configuration
├── tools.py                # Utility tools
├── intents.json            # ML training intents/responses
├── memory.json             # Persisted chat history
├── models.json             # AI model configuration
├── requirements.txt        # Python dependencies
├── firebase-adminsdk.json  # Firebase service account key
├── .env                    # Environment variables (API keys)
├── model/                  # Trained ML model files
├── static/                 # CSS, JavaScript assets
├── templates/              # HTML templates (index, login)
└── uploads/                # User-uploaded files
```

---

## ⚙️ Prerequisites

- **Python 3.8+**
- A `.env` file with your API keys (see [Configuration](#️-configuration))
- A `firebase-adminsdk.json` file for authentication

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies:**
| Package | Purpose |
|---|---|
| Flask | Backend web server |
| pywebview | Desktop GUI window |
| firebase-admin | Authentication |
| PyMuPDF (fitz) | PDF processing |
| tensorflow | ML engine |
| scikit-learn | ML utilities |
| google-generativeai | Gemini AI integration |

---

### 2. Train the ML Model

> **Required on first run or after editing `intents.json`**

```bash
python train.py
```

This generates model files (`model.h5`, `tokenizer.pkl`, etc.) in the `model/` directory.

---

### 3. Run the Application

#### 🖥️ Desktop / Web App (Recommended)

```bash
python app.py
```

- Opens a **PyWebView desktop window** automatically
- Flask server runs at **`http://localhost:5000`**
- Supports file uploads, Firebase login, and full chat features

#### ⌨️ Command Line Interface (CLI)

```bash
python cli.py
```

- Text-only mode, no GUI
- Uses the AI engine directly with a simulated typing effect

---

## 🛠️ Configuration

### `.env` File

Create a `.env` file in the `Chatbot/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
SECRET_KEY=your_flask_secret_key_here
```

### Firebase Setup

Place your Firebase service account JSON file at:
```
Chatbot/firebase-adminsdk.json
```

> Download this from: **Firebase Console → Project Settings → Service Accounts → Generate new private key**

---

## 🧪 Testing

Run the individual test scripts to verify components:

```bash
python test_ai.py          # Test AI engine responses
python test_ai_engine.py   # Test AI engine module
python test_gemini.py      # Test Gemini API connection
python test_endpoint.py    # Test Flask API endpoints
```

---

## 🔧 Troubleshooting

### Port 5000 already in use
Find and kill the process using port 5000:
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```
Then restart the app:
```bash
python app.py
```

### TensorFlow warnings on startup
These are non-critical warnings about GPU/CUDA drivers. The model runs on CPU and works correctly — you can safely ignore them.

### Login not working (Desktop)
Ensure `firebase-adminsdk.json` exists and your `.env` has the correct `SECRET_KEY`. The desktop app uses a browser-bridge for Google OAuth.

### ML Model not found
Run `python train.py` first to generate the required model files before launching `app.py`.

---

## 📜 License

This project is for personal/educational use. All rights reserved.

---

> Built with ❤️ using Flask, PyWebView, Firebase, and Google Gemini.
