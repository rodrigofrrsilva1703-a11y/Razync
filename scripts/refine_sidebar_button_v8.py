from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
start = s.index('        /* Botão lateral Razync v7')
end = s.index('        .stApp > header', start)
new = '''        /* Botão lateral Razync v8 — compacto, discreto e integrado */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            position: fixed !important;
            top: .62rem !important;
            left: .62rem !important;
            width: 2.10rem !important;
            height: 2.10rem !important;
            min-width: 2.10rem !important;
            min-height: 2.10rem !important;
            margin: 0 !important;
            padding: 0 !important;
            align-items: center !important;
            justify-content: center !important;
            border: 1px solid rgba(148, 164, 179, .18) !important;
            border-radius: 9px !important;
            background: rgba(13, 19, 25, .90) !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, .16) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            transition: border-color .16s ease, background .16s ease, transform .16s ease, box-shadow .16s ease !important;
            z-index: 1000001 !important;
        }
        [data-testid="stSidebarCollapsedControl"]:hover,
        [data-testid="stSidebarCollapseButton"]:hover {
            border-color: rgba(19, 185, 232, .58) !important;
            background: rgba(22, 33, 43, .98) !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, .22) !important;
            transform: translateY(-1px) !important;
        }
        [data-testid="stSidebarCollapsedControl"]:active,
        [data-testid="stSidebarCollapseButton"]:active {
            transform: translateY(0) scale(.97) !important;
        }
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button {
            width: 100% !important;
            height: 100% !important;
            min-height: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            border-radius: inherit !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stSidebarCollapseButton"] svg {
            width: 1.02rem !important;
            height: 1.02rem !important;
            opacity: .90 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
            position: absolute !important;
            top: .58rem !important;
            right: .62rem !important;
            left: auto !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]:hover {
            transform: none !important;
        }
        @media (max-width: 900px) {
            [data-testid="stSidebarCollapsedControl"] {
                top: .52rem !important;
                left: .52rem !important;
            }
            section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
                top: .52rem !important;
                right: .55rem !important;
            }
        }

'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding='utf-8')
# trigger
