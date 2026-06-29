import os

filepath = 'c:/AI ChatBot/antigravity_ai_chatbot/static/style.css'
with open(filepath, 'r') as f:
    css = f.read()

variables = """
:root {
  --c-0f172a: #0f172a;
  --c-020617: #020617;
  --c-f8fafc: #f8fafc;
  --c-94a3b8: #94a3b8;
  --c-1e293b: #1e293b;
  --c-1f2937: #1f2937;
  --c-334155: #334155;
  --c-64748b: #64748b;
  --c-3b82f6: #3b82f6;
  --c-2563eb: #2563eb;
  --c-f97316: #f97316;
  --c-rgba-255-005: rgba(255,255,255,0.05);
  --c-rgba-255-010: rgba(255,255,255,0.1);
  --c-rgba-000-020: rgba(0,0,0,0.2);
  --c-rgba-000-030: rgba(0,0,0,0.3);
  --c-rgba-000-040: rgba(0,0,0,0.4);
  --c-rgba-30-41-59-05: rgba(30, 41, 59, 0.5);
  --c-input-focus: rgba(59,130,246,0.5);
  --c-input-shadow: rgba(59,130,246,0.2);
  --c-btn-shadow: rgba(59,130,246,0.25);
}

[data-theme="light"] {
  --c-0f172a: #f8fafc;
  --c-020617: #ffffff;
  --c-f8fafc: #0f172a;
  --c-94a3b8: #64748b;
  --c-1e293b: #e2e8f0;
  --c-1f2937: #f1f5f9;
  --c-334155: #cbd5e1;
  --c-64748b: #94a3b8;
  --c-3b82f6: #3b82f6; 
  --c-2563eb: #2563eb;
  --c-f97316: #f97316;
  --c-rgba-255-005: rgba(0,0,0,0.05);
  --c-rgba-255-010: rgba(0,0,0,0.05);
  --c-rgba-000-020: rgba(0,0,0,0.1);
  --c-rgba-000-030: rgba(0,0,0,0.05);
  --c-rgba-000-040: rgba(0,0,0,0.1);
  --c-rgba-30-41-59-05: rgba(226, 232, 240, 0.8);
  --c-input-focus: rgba(59,130,246,0.5);
  --c-input-shadow: rgba(59,130,246,0.2);
  --c-btn-shadow: rgba(59,130,246,0.25);
}
"""

css = css.replace('#0f172a', 'var(--c-0f172a)')
css = css.replace('#020617', 'var(--c-020617)')
css = css.replace('#f8fafc', 'var(--c-f8fafc)')
css = css.replace('#94a3b8', 'var(--c-94a3b8)')
css = css.replace('#1e293b', 'var(--c-1e293b)')
css = css.replace('#1f2937', 'var(--c-1f2937)')
css = css.replace('#334155', 'var(--c-334155)')
css = css.replace('#64748b', 'var(--c-64748b)')
css = css.replace('#3b82f6', 'var(--c-3b82f6)')
css = css.replace('#2563eb', 'var(--c-2563eb)')
css = css.replace('#f97316', 'var(--c-f97316)')
css = css.replace('rgba(255,255,255,0.05)', 'var(--c-rgba-255-005)')
css = css.replace('rgba(255,255,255,0.1)', 'var(--c-rgba-255-010)')
css = css.replace('rgba(0,0,0,0.2)', 'var(--c-rgba-000-020)')
css = css.replace('rgba(0,0,0,0.3)', 'var(--c-rgba-000-030)')
css = css.replace('rgba(0,0,0,0.4)', 'var(--c-rgba-000-040)')
css = css.replace('rgba(30, 41, 59, 0.5)', 'var(--c-rgba-30-41-59-05)')
css = css.replace('rgba(59,130,246,0.5)', 'var(--c-input-focus)')
css = css.replace('rgba(59,130,246,0.2)', 'var(--c-input-shadow)')
css = css.replace('rgba(59,130,246,0.25)', 'var(--c-btn-shadow)')

fixes = """
.message.user .message-content {
    color: #ffffff;
}
.message.user .message-content code {
    color: #ffffff;
    background: rgba(0,0,0,0.2);
}
"""

with open(filepath, 'w') as f:
    f.write(variables + css + fixes)

print("Replaced colors successfully.")
