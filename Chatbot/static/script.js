/**
 * lavangam.ai — Web Application Script
 * Pure web version: Firebase Auth (signInWithPopup), sessions, chat, file upload.
 * No desktop bridge / pywebview dependencies.
 */

import { initializeApp }            from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup,
         signInWithEmailAndPassword, createUserWithEmailAndPassword,
         onAuthStateChanged, signOut }
    from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

// ── Firebase Config ─────────────────────────────────────────────
const firebaseConfig = {
    apiKey:            "AIzaSyB_6wZtBzz3ZL43fy35ObzDw_N5ZN14i88",
    authDomain:        "chatbot-3816c.firebaseapp.com",
    projectId:         "chatbot-3816c",
    storageBucket:     "chatbot-3816c.firebasestorage.app",
    messagingSenderId: "198904505315",
    appId:             "1:198904505315:web:f0f6cfc220fc74817376d6",
};

const fbApp  = initializeApp(firebaseConfig);
const auth   = getAuth(fbApp);

// ── State ───────────────────────────────────────────────────────
let currentUser      = null;
let authToken        = null;
let currentSessionId = null;
let isTyping         = false;
let selectedFile     = null;

// ── DOM Refs ────────────────────────────────────────────────────
const authOverlay     = document.getElementById('authModal');
const appShell        = document.getElementById('appShell');
const googleLoginBtn  = document.getElementById('googleLoginBtn');
const emailAuthForm   = document.getElementById('emailAuthForm');
const emailBtnText    = document.getElementById('emailBtnText');
const emailBtnSpinner = document.getElementById('emailBtnSpinner');
const authError       = document.getElementById('authError');

const chatbox         = document.getElementById('chatbox');
const welcomeScreen   = document.getElementById('welcomeScreen');
const userInput       = document.getElementById('userInput');
const sendBtn         = document.getElementById('sendBtn');
const loader          = document.getElementById('loader');
const fileUpload      = document.getElementById('fileUpload');
const uploadBtn       = document.getElementById('uploadBtn');
const filePreview     = document.getElementById('filePreview');
const filePreviewName = document.getElementById('filePreviewName');
const historyList     = document.getElementById('historyList');
const newChatBtn      = document.getElementById('newChatBtn');
const logoutBtn       = document.getElementById('logoutBtn');
const userAvatarEl    = document.getElementById('userAvatar');
const userNameEl      = document.getElementById('userName');
const userEmailEl     = document.getElementById('userEmail');
const themeToggleBtn  = document.getElementById('themeToggleBtn');
const themeIcon       = document.getElementById('themeIcon');
const themeText       = document.getElementById('themeText');
const hamburger       = document.getElementById('hamburger');
const sidebar         = document.getElementById('sidebar');
const sidebarOverlay  = document.getElementById('sidebarOverlay');
const headerThemeBtn  = document.getElementById('headerThemeBtn');

// ── Auth Token Helper ───────────────────────────────────────────
async function getFreshToken() {
    if (!currentUser) return null;
    try {
        authToken = await currentUser.getIdToken(false);
        return authToken;
    } catch {
        return authToken;
    }
}

// ── Show / Hide Auth ─────────────────────────────────────────────
function showAuth() {
    authOverlay.classList.remove('hidden');
    appShell.style.display = 'none';
}

function showApp(user) {
    authOverlay.classList.add('hidden');
    appShell.style.display = 'flex';
    userNameEl.textContent  = user.displayName || user.email?.split('@')[0] || 'User';
    userEmailEl.textContent = user.email || '';
    userAvatarEl.textContent = (user.displayName || user.email || 'U')[0].toUpperCase();
}

function showAuthError(msg) {
    authError.textContent = msg;
    authError.classList.remove('hidden');
}

function clearAuthError() {
    authError.classList.add('hidden');
}

// ── Auth State ──────────────────────────────────────────────────
onAuthStateChanged(auth, async (user) => {
    if (user) {
        currentUser = user;
        authToken   = await user.getIdToken();
        showApp(user);
        loadSessions();
        if (!currentSessionId && chatbox.querySelector('.welcome-screen')) {
            // welcome screen already shown
        }
    } else {
        currentUser = null;
        authToken   = null;
        showAuth();
    }
});

// ── Google Sign-In (Popup — works in all browsers) ──────────────
googleLoginBtn.addEventListener('click', async () => {
    clearAuthError();
    googleLoginBtn.disabled    = true;
    googleLoginBtn.textContent = 'Opening sign-in...';
    try {
        const provider = new GoogleAuthProvider();
        await signInWithPopup(auth, provider);
        // onAuthStateChanged handles the rest
    } catch (err) {
        if (err.code !== 'auth/popup-closed-by-user' && err.code !== 'auth/cancelled-popup-request') {
            showAuthError('Google sign-in failed: ' + (err.message || 'Unknown error'));
        }
    } finally {
        googleLoginBtn.disabled = false;
        googleLoginBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg> Continue with Google`;
    }
});

// ── Email Auth ──────────────────────────────────────────────────
emailAuthForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAuthError();
    const email    = document.getElementById('authEmail').value.trim();
    const password = document.getElementById('authPassword').value;

    emailBtnText.textContent = 'Signing in...';
    emailBtnSpinner.classList.remove('hidden');
    document.getElementById('emailLoginBtn').disabled = true;

    try {
        await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
        if (['auth/user-not-found','auth/invalid-credential','auth/invalid-email'].includes(err.code)) {
            try {
                await createUserWithEmailAndPassword(auth, email, password);
            } catch (regErr) {
                const msgs = {
                    'auth/email-already-in-use': '⚠️ Account exists but password is wrong.',
                    'auth/weak-password':         '⚠️ Password must be at least 6 characters.',
                };
                showAuthError(msgs[regErr.code] || regErr.message);
            }
        } else if (err.code === 'auth/wrong-password') {
            showAuthError('⚠️ Incorrect password. Please try again.');
        } else if (err.code === 'auth/too-many-requests') {
            showAuthError('⚠️ Too many attempts. Please wait and try again.');
        } else {
            showAuthError(err.message);
        }
    } finally {
        emailBtnText.textContent = 'Sign In / Register';
        emailBtnSpinner.classList.add('hidden');
        document.getElementById('emailLoginBtn').disabled = false;
    }
});

// ── Logout ──────────────────────────────────────────────────────
logoutBtn.addEventListener('click', () => signOut(auth));

// ── Theme ───────────────────────────────────────────────────────
const sunSVG  = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const moonSVG = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('lavangam-theme', theme);
    if (theme === 'light') {
        themeIcon.innerHTML = sunSVG;
        themeText.textContent = 'Light Mode';
    } else {
        themeIcon.innerHTML = moonSVG;
        themeText.textContent = 'Dark Mode';
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(current === 'light' ? 'dark' : 'light');
}

applyTheme(localStorage.getItem('lavangam-theme') || 'dark');
themeToggleBtn.addEventListener('click', toggleTheme);
headerThemeBtn.addEventListener('click', toggleTheme);

// ── Mobile Sidebar ───────────────────────────────────────────────
function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('visible');
    hamburger.setAttribute('aria-expanded', 'true');
}

function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('visible');
    hamburger.setAttribute('aria-expanded', 'false');
}

hamburger.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
});

sidebarOverlay.addEventListener('click', closeSidebar);

// ── Session Management ──────────────────────────────────────────
async function loadSessions() {
    try {
        const token = await getFreshToken();
        if (!token) return;
        const res  = await fetch('/sessions', { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) return;
        const data = await res.json();
        renderSessions(data.sessions || []);
    } catch { /* silent */ }
}

function renderSessions(sessions) {
    historyList.innerHTML = '<p class="history-label">Chat History</p>';
    if (sessions.length === 0) {
        historyList.innerHTML += '<p class="history-empty">No chats yet. Start a conversation!</p>';
        return;
    }
    sessions.forEach(s => {
        const div       = document.createElement('div');
        div.className   = 'history-item' + (s.id === currentSessionId ? ' active' : '');
        div.setAttribute('role', 'listitem');
        div.setAttribute('tabindex', '0');

        const title     = document.createElement('span');
        title.className = 'history-title-text';
        title.textContent = s.title || 'Untitled Chat';

        const del       = document.createElement('span');
        del.className   = 'delete-chat-btn';
        del.innerHTML   = '🗑';
        del.title       = 'Delete chat';
        del.onclick     = (e) => { e.stopPropagation(); confirmDeleteSession(s.id); };

        div.appendChild(title);
        div.appendChild(del);
        div.onclick  = () => loadSession(s.id);
        div.onkeydown = (e) => e.key === 'Enter' && loadSession(s.id);
        historyList.appendChild(div);
    });
}

async function confirmDeleteSession(id) {
    if (!confirm('Delete this chat history?')) return;
    try {
        const token = await getFreshToken();
        const res   = await fetch(`/session/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
            if (currentSessionId === id) startNewChat();
            else loadSessions();
        }
    } catch { /* silent */ }
}

async function loadSession(id) {
    currentSessionId = id;
    chatbox.innerHTML = '';
    closeSidebar();
    loadSessions(); // refresh active state

    try {
        const token = await getFreshToken();
        const res   = await fetch(`/session/${id}`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) return;
        const data  = await res.json();
        if (data.history?.length) {
            data.history.forEach(m => {
                appendMessage(m.user, 'user');
                appendMessage(m.bot,  'bot');
            });
        }
    } catch { /* silent */ }
}

function startNewChat() {
    currentSessionId = null;
    chatbox.innerHTML = '';
    chatbox.appendChild(buildWelcomeScreen());
    loadSessions();
    closeSidebar();
}

newChatBtn.addEventListener('click', startNewChat);

// ── Welcome Screen Builder ──────────────────────────────────────
function buildWelcomeScreen() {
    const ws = document.createElement('div');
    ws.className = 'welcome-screen';
    ws.id = 'welcomeScreen';
    ws.innerHTML = welcomeScreen ? welcomeScreen.innerHTML : '';
    // Re-attach suggestion chip listeners
    ws.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            userInput.value = chip.dataset.prompt || chip.textContent.trim();
            userInput.dispatchEvent(new Event('input'));
            sendMessage();
        });
    });
    return ws;
}

// Attach suggestion chip listeners to initial welcome screen
document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        userInput.value = chip.dataset.prompt || chip.textContent.trim();
        userInput.dispatchEvent(new Event('input'));
        sendMessage();
    });
});

// ── Append Message ──────────────────────────────────────────────
function appendMessage(text, sender, typeEffect = false) {
    // Remove welcome screen on first message
    const ws = chatbox.querySelector('.welcome-screen');
    if (ws) ws.remove();

    const wrap   = document.createElement('div');
    wrap.className = `message ${sender}`;
    wrap.innerHTML = `
        <div class="message-inner">
            <div class="message-avatar" aria-hidden="true">${sender === 'bot' ? 'L' : 'U'}</div>
            <div class="message-content"></div>
        </div>`;

    chatbox.appendChild(wrap);
    const content = wrap.querySelector('.message-content');

    if (sender === 'bot') {
        if (typeEffect) {
            const tokens    = text.match(/[\s\n]+|\S+/g) || [];
            let rendered    = '';
            let idx         = 0;
            const tick = setInterval(() => {
                if (idx < tokens.length) {
                    rendered += tokens[idx++];
                    content.innerHTML = marked.parse(rendered);
                    chatbox.scrollTop = chatbox.scrollHeight;
                } else {
                    clearInterval(tick);
                    addCopyButtons(content);
                }
            }, 18);
        } else {
            content.innerHTML = marked.parse(text);
            addCopyButtons(content);
        }
    } else {
        const p = document.createElement('div');
        p.textContent     = text;
        p.style.whiteSpace = 'pre-wrap';
        content.appendChild(p);
    }

    chatbox.scrollTop = chatbox.scrollHeight;
    return wrap;
}

// ── Copy buttons for code blocks ────────────────────────────────
function addCopyButtons(container) {
    container.querySelectorAll('pre').forEach(pre => {
        if (pre.querySelector('.copy-btn')) return;
        const btn       = document.createElement('button');
        btn.className   = 'copy-btn';
        btn.textContent = 'Copy';
        btn.style.cssText = 'position:absolute;top:8px;right:8px;padding:3px 9px;font-size:0.72rem;border-radius:5px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.08);color:#94a3b8;cursor:pointer;transition:all 0.15s;';
        btn.onclick = async () => {
            const code = pre.querySelector('code')?.textContent || pre.textContent;
            await navigator.clipboard.writeText(code).catch(() => {});
            btn.textContent = 'Copied!';
            btn.style.color = '#4ade80';
            setTimeout(() => { btn.textContent = 'Copy'; btn.style.color = '#94a3b8'; }, 2000);
        };
        pre.style.position = 'relative';
        pre.appendChild(btn);
    });
}

// ── Loading State ───────────────────────────────────────────────
function setLoading(active) {
    isTyping = active;
    loader.classList.toggle('hidden', !active);
    sendBtn.disabled        = active;
    userInput.disabled      = active;
    uploadBtn.disabled      = active;
    if (active) chatbox.scrollTop = chatbox.scrollHeight;
    else userInput.focus();
}

// ── File Handling ───────────────────────────────────────────────
uploadBtn.addEventListener('click', () => fileUpload.click());

fileUpload.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile            = e.target.files[0];
        filePreviewName.textContent = selectedFile.name;
        filePreview.classList.remove('hidden');
        sendBtn.disabled        = false;
    }
});

window.clearFile = function() {
    selectedFile           = null;
    fileUpload.value       = '';
    filePreview.classList.add('hidden');
    if (!userInput.value.trim()) sendBtn.disabled = true;
};

// ── Textarea Auto-resize ─────────────────────────────────────────
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
    sendBtn.disabled  = !this.value.trim() && !selectedFile;
});

userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

// ── Send Message ─────────────────────────────────────────────────
async function sendMessage() {
    const text = userInput.value.trim();
    if ((!text && !selectedFile) || isTyping) return;

    let displayMsg = text;
    if (selectedFile && !text)   displayMsg = `[Shared: ${selectedFile.name}]`;
    else if (selectedFile)       displayMsg += `\n[Shared: ${selectedFile.name}]`;

    appendMessage(displayMsg, 'user');
    userInput.value       = '';
    userInput.style.height = 'auto';
    sendBtn.disabled      = true;
    setLoading(true);

    const form = new FormData();
    form.append('message', text);
    if (currentSessionId) form.append('session_id', currentSessionId);
    if (selectedFile)     form.append('file', selectedFile);

    try {
        const token = await getFreshToken();
        const res   = await fetch('/chat', {
            method:  'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body:    form,
        });
        const data  = await res.json();
        appendMessage(data.response || '⚠️ No response received.', 'bot', true);

        if (data.session_id) {
            const wasNew     = !currentSessionId;
            currentSessionId = data.session_id;
            if (wasNew) loadSessions();
        }
    } catch (err) {
        console.error('Chat error:', err);
        appendMessage('⚠️ Network error. Could not reach the server.', 'bot');
    } finally {
        setLoading(false);
        clearFile();
    }
}
