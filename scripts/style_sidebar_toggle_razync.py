from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_toolbar = '''        /* Sidebar toolbar parent fix v6 */
        [data-testid="stToolbar"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            background: transparent !important;
            box-shadow: none !important;
            z-index: 1000000 !important;
        }
        [data-testid="stToolbar"] > div {
            pointer-events: auto !important;
        }
'''
new_toolbar = '''        /* Razync sidebar-only chrome v7 */
        [data-testid="stToolbar"] {
            display: none !important;
            visibility: hidden !important;
        }
'''
if old_toolbar not in s:
    raise SystemExit('Bloco toolbar v6 não encontrado')
s = s.replace(old_toolbar, new_toolbar, 1)

old_controls = '''        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 1000001 !important;
        }
'''
new_controls = '''        /* Botão lateral Razync v7 — usa o clique nativo do Streamlit */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            position: fixed !important;
            top: .72rem !important;
            left: .72rem !important;
            width: 2.35rem !important;
            height: 2.35rem !important;
            min-width: 2.35rem !important;
            min-height: 2.35rem !important;
            margin: 0 !important;
            padding: 0 !important;
            align-items: center !important;
            justify-content: center !important;
            border: 1px solid rgba(148, 164, 179, .28) !important;
            border-radius: 10px !important;
            background: rgba(17, 24, 32, .94) !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, .22) !important;
            backdrop-filter: blur(10px) !important;
            z-index: 1000001 !important;
        }
        [data-testid="stSidebarCollapsedControl"]:hover,
        [data-testid="stSidebarCollapseButton"]:hover {
            border-color: var(--hc-accent) !important;
            background: #16212b !important;
        }
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button {
            width: 100% !important;
            height: 100% !important;
            min-height: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stSidebarCollapseButton"] svg {
            width: 1.15rem !important;
            height: 1.15rem !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
            left: calc(21rem - 3.1rem) !important;
        }
        @media (max-width: 900px) {
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stSidebarCollapseButton"] {
                top: .55rem !important;
                left: .55rem !important;
            }
            section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
                left: auto !important;
                right: .65rem !important;
            }
        }
'''
if old_controls not in s:
    raise SystemExit('Bloco de controles laterais atual não encontrado')
s = s.replace(old_controls, new_controls, 1)

p.write_text(s, encoding='utf-8')
# trigger
