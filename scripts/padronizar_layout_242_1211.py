from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# 1211: manter apenas as duas abas padrão; conferência fica dentro de Organizar arquivos.
s = s.replace("""        aba_operacoes_gz, aba_base_gz, aba_conferencia_gz = st.tabs([\n            'Organizar arquivos', 'Base Inteligente', 'Conferência com Extrato'\n        ])""", """        aba_operacoes_gz, aba_base_gz = st.tabs([\n            'Organizar arquivos', 'Base Inteligente'\n        ])""")
s = s.replace("        with aba_conferencia_gz:\n", "        with aba_operacoes_gz:\n", 1)

# 242: mesmo padrão das demais empresas; conferência passa para Organizar arquivos.
s = s.replace("""        aba_operacoes_ef, aba_base_ef, aba_conferencia_ef = st.tabs(['Organizar arquivos', 'Base Inteligente', 'Conferência com Extrato'])""", """        aba_operacoes_ef, aba_base_ef = st.tabs([\n            'Organizar arquivos', 'Base Inteligente'\n        ])""")
s = s.replace("        with aba_conferencia_ef:\n", "        with aba_operacoes_ef:\n", 1)

# Ajusta títulos para deixar claro que a conferência é uma seção da operação, como nas demais.
s = s.replace("            st.markdown('#### Conferência com Extrato')\n            st.caption(\n                'Confere cada total BOLETOS RECEBIDOS", "            st.markdown('#### Conferência com Extrato')\n            st.caption(\n                'Confere cada total BOLETOS RECEBIDOS", 1)

p.write_text(s, encoding='utf-8')

# Validações estruturais simples.
t = p.read_text(encoding='utf-8')
assert "aba_operacoes_gz, aba_base_gz = st.tabs" in t
assert "aba_operacoes_ef, aba_base_ef = st.tabs" in t
assert "aba_conferencia_gz" not in t
assert "aba_conferencia_ef" not in t
assert t.count("if st.session_state['empresa_organizador'] == 'gz_1211':") == 1
assert t.count("if st.session_state['empresa_organizador'] == 'eletro_forte':") == 1
print('layout 242/1211 padronizado')
