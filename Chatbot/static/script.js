import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, signInWithCustomToken, signInWithCredential, GoogleAuthProvider, signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyB_6wZtBzz3ZL43fy35ObzDw_N5ZN14i88",
  authDomain: "chatbot-3816c.firebaseapp.com",
  projectId: "chatbot-3816c",
  storageBucket: "chatbot-3816c.firebasestorage.app",
  messagingSenderId: "198904505315",
  appId: "1:198904505315:web:f0f6cfc220fc74817376d6",
  measurementId: "G-DM3NFY8SX9"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

let authToken = null;
let currentUser = null;

// Always get a fresh (non-expired) token before API calls
async function getFreshToken() {
    if (!currentUser) return null;
    try {
        authToken = await currentUser.getIdToken(false); // use cached if still valid
        return authToken;
    } catch (e) {
        console.error('Token refresh error:', e);
        return authToken;
    }
}

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
        if (!currentSessionId && chatbox.children.length === 0) {
            setTimeout(() => {
                appendMessage("Hi, I'm lavangam.ai. I can help visualize data, parse files, or answer questions. How can I help you today?", "bot");
            }, 300);
        }
    } else {
        currentUser = null;
        authToken = null;
        authModal.classList.remove('hidden');
        appLayout.style.display = 'none';
    }
});

// Google Login (Desktop Bridge Flow)
googleLoginBtn.addEventListener('click', async () => {
    try {
        const sessionId = Math.random().toString(36).substring(2, 15);
        const loginUrl = `http://localhost:5050/login?session_id=${sessionId}`;
        
        // Use the backend bridge to reliably open the OS default browser
        await fetch(`/api/open-browser?url=${encodeURIComponent(loginUrl)}`);
        
        googleLoginBtn.disabled = true;
        googleLoginBtn.textContent = 'Waiting for browser login...';
        
        // Poll for the token
        const pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/poll-token?session_id=${sessionId}`);
                const data = await res.json();
                
                if (data.status === 'success') {
                    clearInterval(pollInterval);

                    // Store the Firebase ID token directly — no client re-auth needed
                    authToken = data.token;
                    const user = data.user;

                    // Create a mock currentUser so getFreshToken() works
                    currentUser = {
                        uid: user.uid,
                        email: user.email,
                        displayName: user.name,
                        getIdToken: async () => authToken
                    };

                    // Manually update UI (onAuthStateChanged won't fire for this path)
                    authModal.classList.add('hidden');
                    appLayout.style.display = 'flex';
                    userNameEl.textContent = user.name || user.email?.split('@')[0] || 'User';
                    userAvatarEl.textContent = (user.name || user.email || 'U')[0].toUpperCase();

                    loadSessions();
                    if (!currentSessionId && chatbox.children.length === 0) {
                        setTimeout(() => {
                            appendMessage("Hi, I'm lavangam.ai. I can help visualize data, parse files, or answer questions. How can I help you today?", "bot");
                        }, 300);
                    }

                    authError.classList.add('hidden');
                    googleLoginBtn.disabled = false;
                    googleLoginBtn.innerHTML = 'Continue with Google';
                }
            } catch (err) {
                clearInterval(pollInterval);
                googleLoginBtn.disabled = false;
                googleLoginBtn.innerHTML = 'Continue with Google';
                authError.textContent = "Sign in error: " + err.message;
                authError.classList.remove('hidden');
            }
        }, 2000);
        
    } catch (error) {
        googleLoginBtn.disabled = false;
        googleLoginBtn.innerHTML = 'Continue with Google';
        authError.textContent = "Failed to open browser or authenticate.";
        authError.classList.remove('hidden');
    }
});

// Email Login / Signup
emailAuthForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('authEmail').value;
    const password = document.getElementById('authPassword').value;
    authError.classList.add('hidden');
    const btn = document.getElementById('emailLoginBtn');
    btn.textContent = 'Signing in...';
    btn.disabled = true;
    try {
        // Always try sign-in first
        await signInWithEmailAndPassword(auth, email, password);
        authError.classList.add('hidden');
    } catch (error) {
        if (error.code === 'auth/user-not-found' || error.code === 'auth/invalid-credential' || error.code === 'auth/invalid-email') {
            // Account doesn't exist — try to register
            try {
                await createUserWithEmailAndPassword(auth, email, password);
                authError.classList.add('hidden');
            } catch (err) {
                if (err.code === 'auth/email-already-in-use') {
                    authError.textContent = '⚠️ Account exists but password is wrong. Please check your password.';
                } else if (err.code === 'auth/weak-password') {
                    authError.textContent = '⚠️ Password must be at least 6 characters.';
                } else {
                    authError.textContent = err.message;
                }
                authError.classList.remove('hidden');
            }
        } else if (error.code === 'auth/wrong-password') {
            authError.textContent = '⚠️ Incorrect password. Please try again.';
            authError.classList.remove('hidden');
        } else if (error.code === 'auth/too-many-requests') {
            authError.textContent = '⚠️ Too many failed attempts. Please wait and try again.';
            authError.classList.remove('hidden');
        } else {
            authError.textContent = error.message;
            authError.classList.remove('hidden');
        }
    } finally {
        btn.textContent = 'Sign In / Register';
        btn.disabled = false;
    }
});

// Logout
logoutBtn.addEventListener('click', () => {
    signOut(auth);
});

const chatbox = document.getElementById('chatbox');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const loader = document.getElementById('loader');

// Sidebar and tool elements
const fileUpload = document.getElementById('fileUpload');
const uploadBtn = document.getElementById('uploadBtn');
const filePreview = document.getElementById('filePreview');
const newChatBtn = document.querySelector('.new-chat-btn');
const historyListContainer = document.querySelector('.history-list');

let isTyping = false;
let selectedFile = null;
let currentSessionId = null;

// Auto-expand textarea
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    
    if (this.value.trim() !== '' || selectedFile) {
        sendBtn.removeAttribute('disabled');
    } else {
        sendBtn.setAttribute('disabled', 'true');
    }
});

// File Handling
uploadBtn.addEventListener('click', () => fileUpload.click());

fileUpload.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        filePreview.innerHTML = `<span>📎 ${selectedFile.name}</span> <div class="clear-btn" onclick="clearFile()">✖</div>`;
        filePreview.classList.remove('hidden');
        sendBtn.removeAttribute('disabled');
    }
});

window.clearFile = function() {
    selectedFile = null;
    fileUpload.value = '';
    filePreview.classList.add('hidden');
    if(userInput.value.trim() === '') {
        sendBtn.setAttribute('disabled', 'true');
    }
};

userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

function toggleLoading(state) {
    isTyping = state;
    if (state) {
        sendBtn.setAttribute('disabled', 'true');
        userInput.setAttribute('disabled', 'true');
        uploadBtn.setAttribute('disabled', 'true');
        loader.classList.remove('hidden');
        chatbox.scrollTop = chatbox.scrollHeight;
    } else {
        userInput.removeAttribute('disabled');
        uploadBtn.removeAttribute('disabled');
        loader.classList.add('hidden');
        userInput.focus();
    }
}

function appendMessage(text, sender, typeEffect = false) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    
    msgDiv.innerHTML = `
        <div class="message-inner">
            <div class="message-avatar">${sender === 'bot' ? 'L' : 'U'}</div>
            <div class="message-content"></div>
        </div>`;
    
    chatbox.appendChild(msgDiv);
    const contentDiv = msgDiv.querySelector('.message-content');

    if (sender === 'bot') {
        if (typeEffect) {
            const tokens = text.match(/[\s\n]+|\S+/g) || [];
            let currentText = '';
            let tokenIndex = 0;
            const typingInterval = setInterval(() => {
                if (tokenIndex < tokens.length) {
                    currentText += tokens[tokenIndex];
                    contentDiv.innerHTML = marked.parse(currentText);
                    chatbox.scrollTop = chatbox.scrollHeight;
                    tokenIndex++;
                } else {
                    clearInterval(typingInterval);
                }
            }, 20);
        } else {
            contentDiv.innerHTML = marked.parse(text);
        }
    } else {
        const p = document.createElement('div');
        p.textContent = text;
        p.style.fontFamily = "inherit";
        p.style.whiteSpace = "pre-wrap";
        p.style.margin = "0";
        contentDiv.appendChild(p);
    }
    
    chatbox.scrollTop = chatbox.scrollHeight;
}

// ==== SESSION MANAGEMENT ====

async function loadSessions() {
    try {
        const token = await getFreshToken();
        if (!token) return;
        
        const res = await fetch('/sessions', { headers: { 'Authorization': `Bearer ${token}` } });
        if (!res.ok) {
            console.error('Sessions fetch failed:', res.status);
            return;
        }
        const data = await res.json();
        const sessions = data.sessions || [];
        
        historyListContainer.innerHTML = '<p class="history-title">Chat History</p>';
        
        if (sessions.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'history-empty';
            empty.textContent = 'No previous chats';
            historyListContainer.appendChild(empty);
            return;
        }
        
        sessions.forEach(session => {
            const div = document.createElement('div');
            div.className = 'history-item';
            
            const titleSpan = document.createElement('span');
            titleSpan.className = 'history-title-text';
            titleSpan.textContent = session.title;
            div.appendChild(titleSpan);
            
            const deleteBtn = document.createElement('span');
            deleteBtn.className = 'delete-chat-btn';
            deleteBtn.innerHTML = '🗑️';
            deleteBtn.title = 'Delete Chat';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                deleteSession(session.id);
            };
            div.appendChild(deleteBtn);
            
            if (session.id === currentSessionId) {
                div.classList.add('active');
            }
            div.onclick = () => loadSession(session.id);
            historyListContainer.appendChild(div);
        });
    } catch (e) {
        console.error("Failed to load sessions", e);
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Are you sure you want to delete this chat history?")) return;
    try {
        const token = await getFreshToken();
        const res = await fetch(`/session/${sessionId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
            if (currentSessionId === sessionId) {
                newChatBtn.click();
            } else {
                loadSessions();
            }
        }
    } catch (e) {
        console.error("Failed to delete session", e);
    }
}

async function loadSession(sessionId) {
    currentSessionId = sessionId;
    chatbox.innerHTML = '';
    
    // Highlight correct item
    loadSessions();

    try {
        const token = await getFreshToken();
        const res = await fetch(`/session/${sessionId}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!res.ok) {
            console.error('Load session failed:', res.status);
            return;
        }
        const data = await res.json();
        
        if (data.history && data.history.length > 0) {
            data.history.forEach(msg => {
                appendMessage(msg.user, 'user');
                appendMessage(msg.bot, 'bot');
            });
        } else {
            appendMessage("No messages found in this chat.", 'bot');
        }
    } catch (e) {
        console.error("Failed to load session", e);
    }
}

newChatBtn.addEventListener('click', () => {
    currentSessionId = null;
    chatbox.innerHTML = '';
    loadSessions();
    setTimeout(() => {
        appendMessage("Hi, I'm lavangam.ai. I can help visualize data, parse files, or answer questions. How can I help you today?", "bot");
    }, 300);
});

async function sendMessage() {
    const text = userInput.value;
    if ((!text.trim() && !selectedFile) || isTyping) return;

    let displayMsg = text;
    if (selectedFile && !text.trim()) {
        displayMsg = `[Shared a file: ${selectedFile.name}]`;
    } else if (selectedFile) {
        displayMsg += `\n\n[Shared a file: ${selectedFile.name}]`;
    }

    appendMessage(displayMsg, 'user');
    userInput.value = '';
    userInput.style.height = 'auto';
    
    sendBtn.setAttribute('disabled', 'true');
    
    toggleLoading(true);
    
    const formData = new FormData();
    formData.append('message', text.trim());
    if (currentSessionId) {
        formData.append('session_id', currentSessionId);
    }
    if (selectedFile) {
        formData.append('file', selectedFile);
    }

    try {
        const token = await getFreshToken();
        const response = await fetch('/chat', {
            headers: { 'Authorization': `Bearer ${token}` },
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        appendMessage(data.response, 'bot', true);
        
        if (data.session_id) {
            const wasNew = !currentSessionId;
            currentSessionId = data.session_id;
            if (wasNew) {
                // Reload session list to show new chat
                loadSessions();
            }
        }
    } catch (error) {
        console.error('Error fetching chat:', error);
        appendMessage("Network error. Could not reach the server.", 'bot');
    } finally {
        toggleLoading(false);
        clearFile();
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Default greeting if no session
    setTimeout(() => {
        if (!currentSessionId && chatbox.children.length === 0) {
            appendMessage("Hi, I'm lavangam.ai. I can help visualize data, parse files, or answer questions. How can I help you today?", "bot");
        }
    }, 300);
});

// Theme Management
const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeIcon = document.getElementById('themeIcon');
const themeText = document.getElementById('themeText');

const sunIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
const moonIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    if (theme === 'light') {
        themeIcon.innerHTML = sunIcon;
        themeText.textContent = 'Light Mode';
    } else {
        themeIcon.innerHTML = moonIcon;
        themeText.textContent = 'Dark Mode';
    }
}

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'dark';
setTheme(savedTheme);

themeToggleBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
});
