import json
import os
from config import MEMORY_FILE

MAX_HISTORY = 20

def load_memory_file():
    if not os.path.exists(MEMORY_FILE):
        return {"users": {}}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}

def save_memory_file(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_memory(user_id, session_id):
    data = load_memory_file()
    return data.get("users", {}).get(user_id, {}).get("sessions", {}).get(session_id, [])

def save_memory(user_id, session_id, user_msg, bot_msg):
    data = load_memory_file()
    
    if "users" not in data:
        data["users"] = {}
        
    if user_id not in data["users"]:
        data["users"][user_id] = {"sessions": {}}
        
    if session_id not in data["users"][user_id]["sessions"]:
        data["users"][user_id]["sessions"][session_id] = []
        
    session_history = data["users"][user_id]["sessions"][session_id]
    
    # Prevent duplicate memory writes if frontend retries
    if session_history and session_history[-1].get("user") == user_msg:
        # Just update the bot response if the user query was the same
        session_history[-1]["bot"] = bot_msg
    else:
        session_history.append({"user": user_msg, "bot": bot_msg})
        
    # Cap the history size
    data["users"][user_id]["sessions"][session_id] = session_history[-MAX_HISTORY:]
    
    save_memory_file(data)

def get_all_sessions(user_id):
    data = load_memory_file()
    sessions = []
    user_sessions = data.get("users", {}).get(user_id, {}).get("sessions", {})
    for sid, messages in user_sessions.items():
        if messages:
            first_msg = messages[0].get("user", "")
            title = first_msg[:30] + "..." if len(first_msg) > 30 else first_msg
            if not title.strip():
                title = "New Chat"
            sessions.append({"id": sid, "title": title})
    # Return reversed to show newest at the top
    return sessions[::-1]

def delete_session(user_id, session_id):
    data = load_memory_file()
    if "users" in data and user_id in data["users"]:
        user_sessions = data["users"][user_id].get("sessions", {})
        if session_id in user_sessions:
            del user_sessions[session_id]
            save_memory_file(data)
            return True
    return False
