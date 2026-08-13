from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
anchor = "SEGURANCA_POR_SENHA_ATIVA = proteger_acesso_hub()\n"
if anchor not in s:
    raise SystemExit('anchor missing')
insert = '''\nif "tema_razync" not in st.session_state:\n    st.session_state["tema_razync"] = "Escuro"\nwith st.sidebar:\n    tema = st.radio("Aparência", ["Escuro", "Claro"], horizontal=True, key="tema_razync_radio")\nif tema != st.session_state["tema_razync"]:\n    st.session_state["tema_razync"] = tema\nif st.session_state["tema_razync"] == "Claro":\n    st.markdown("""<style>\n    :root{--hc-bg:#f5f7fa;--hc-surface:#ffffff;--hc-surface-hover:#eef4f8;--hc-border:#d6e0e8;--hc-border-strong:#bac8d3;--hc-text:#17212b;--hc-muted:#5f7180;--hc-accent:#0784b8;--hc-accent-soft:rgba(7,132,184,.10)}\n    .stApp,[data-testid=stAppViewContainer],[data-testid=stMain]{background:#f5f7fa!important;color:#17212b!important}\n    section[data-testid=stSidebar]{background:#fff!important;border-right:1px solid #d6e0e8!important}\n    h1,h2,h3,h4,h5,h6{color:#17212b!important}\n    .stButton>button,[data-testid=stFileUploaderDropzone],[data-testid=stMetric],.metric-card,.aviso-banner{background:#fff!important;border-color:#d6e0e8!important;color:#17212b!important}\n    [data-testid=stCaptionContainer]{background:rgba(7,132,184,.065)!important;border-left-color:#0784b8!important}\n    [data-testid=stCaptionContainer] p{color:#405766!important}\n    input,textarea{background:#fff!important;color:#17212b!important}\n    </style>""", unsafe_allow_html=True)\n'''
s = s.replace(anchor, anchor + insert, 1)
p.write_text(s, encoding='utf-8')
print('theme patched')
