import os
import re

filepath = 'c:/AI ChatBot/antigravity_ai_chatbot/static/script.js'

with open(filepath, 'r', encoding='utf-8') as f:
    js = f.read()

firebase_imports = """import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, signInWithPopup, GoogleAuthProvider, signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

// TODO: Replace with your actual Firebase config
const firebaseConfig = {
  apiKey: "REPLACE_API_KEY",
  authDomain: "REPLACE_AUTH_DOMAIN",
  projectId: "REPLACE_PROJECT_ID",
  storageBucket: "REPLACE_STORAGE_BUCKET",
  messagingSenderId: "REPLACE_MESSAGING_SENDER_ID",
  appId: "REPLACE_APP_ID"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

let authToken = null;
let currentUser = null;

const authModal = document.getElementById('authModal');
const appLayout = document.getElementById('appLayout');
const userNameEl = document.getElementById('userName');
const userAvatarEl = document.getElementById('userAvatar');
const googleLoginBtn = document.getElementById('googleLoginBtn');
const emailAuthForm = document.getElementById('emailAuthForm');
const authError = document.getElementById('authError');
const logoutBtn = document.getElementById('logoutBtn');

// Auth State Observer
onAuthStateChanged(auth, async (user) => {
    if (user) {
        currentUser = user;
        authToken = await user.getIdToken();
        authModal.classList.add('hidden');
        appLayout.style.display = 'flex';
        userNameEl.textContent = user.displayName || user.email.split('@')[0];
        userAvatarEl.textContent = (user.displayName || user.email)[0].toUpperCase();
        loadSessions(); // Load sessions now that we have a token
    } else {
        currentUser = null;
        authToken = null;
        authModal.classList.remove('hidden');
        appLayout.style.display = 'none';
    }
});

// Google Login
googleLoginBtn.addEventListener('click', async () => {
    try {
        await signInWithPopup(auth, provider);
        authError.classList.add('hidden');
    } catch (error) {
        authError.textContent = error.message;
        authError.classList.remove('hidden');
    }
});

// Email Login / Signup
emailAuthForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('authEmail').value;
    const password = document.getElementById('authPassword').value;
    try {
        await signInWithEmailAndPassword(auth, email, password);
        authError.classList.add('hidden');
    } catch (error) {
        if (error.code === 'auth/user-not-found' || error.code === 'auth/invalid-credential') {
            try {
                await createUserWithEmailAndPassword(auth, email, password);
                authError.classList.add('hidden');
            } catch (err) {
                authError.textContent = err.message;
                authError.classList.remove('hidden');
            }
        } else {
            authError.textContent = error.message;
            authError.classList.remove('hidden');
        }
    }
});

// Logout
logoutBtn.addEventListener('click', () => {
    signOut(auth);
});

"""

# Prefix firebase imports to js
js = firebase_imports + js

# Replace fetch calls
# loadSessions
js = js.replace("const res = await fetch('/sessions');", 
    "const res = await fetch('/sessions', { headers: { 'Authorization': `Bearer ${authToken}` } });")

# deleteSession
js = js.replace("const res = await fetch(`/session/${sessionId}`, { method: 'DELETE' });",
    "const res = await fetch(`/session/${sessionId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` } });")

# loadSession
js = js.replace("const res = await fetch(`/session/${sessionId}`);",
    "const res = await fetch(`/session/${sessionId}`, { headers: { 'Authorization': `Bearer ${authToken}` } });")

# sendMessage fetch
js = js.replace("const response = await fetch('/chat', {",
    "const response = await fetch('/chat', {\n            headers: { 'Authorization': `Bearer ${authToken}` },")

# Remove `loadSessions();` from DOMContentLoaded since it's now triggered onAuthStateChanged
js = js.replace("loadSessions();\n    // Default greeting if no session", "// Default greeting if no session")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(js)

print("Patched script.js successfully")
