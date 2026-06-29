import os

filepath = 'c:/AI ChatBot/antigravity_ai_chatbot/static/style.css'

css_to_append = """

/* Auth Modal Styles */
.auth-modal {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(5px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.auth-modal.hidden {
    display: none;
}

.auth-modal-content {
    background: var(--c-020617);
    padding: 32px;
    border-radius: 16px;
    width: 100%;
    max-width: 400px;
    border: 1px solid var(--c-rgba-255-005);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    text-align: center;
}

.auth-modal-content h2 {
    color: var(--c-f8fafc);
    margin-bottom: 8px;
}

.auth-modal-content p {
    color: var(--c-94a3b8);
    font-size: 0.9em;
    margin-bottom: 24px;
}

.google-btn {
    width: 100%;
    padding: 12px;
    background: #ffffff;
    color: #3c4043;
    border: 1px solid #dadce0;
    border-radius: 8px;
    font-size: 1em;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    transition: background 0.2s;
}

.google-btn:hover {
    background: #f8f9fa;
}

.divider {
    display: flex;
    align-items: center;
    margin: 24px 0;
    color: var(--c-64748b);
    font-size: 0.85em;
}

.divider::before, .divider::after {
    content: "";
    flex: 1;
    border-bottom: 1px solid var(--c-rgba-255-005);
}

.divider span {
    padding: 0 12px;
}

#emailAuthForm {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

#emailAuthForm input {
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--c-rgba-255-005);
    background: var(--c-1e293b);
    color: var(--c-f8fafc);
    outline: none;
}

#emailAuthForm input:focus {
    border-color: var(--c-input-focus);
}

.primary-btn {
    padding: 12px;
    border-radius: 8px;
    border: none;
    background: var(--c-3b82f6);
    color: #ffffff;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}

.primary-btn:hover {
    background: var(--c-2563eb);
}

.auth-error {
    color: #ef4444 !important;
    margin-top: 12px;
    font-size: 0.85em;
}
"""

with open(filepath, 'a') as f:
    f.write(css_to_append)
