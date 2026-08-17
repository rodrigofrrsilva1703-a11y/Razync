from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

# Remove apenas caches potencialmente pesados de arquivos grandes.
s = s.replace('@st.cache_data(show_spinner=False, max_entries=12)\ndef processar_extrato_unificado', 'def processar_extrato_unificado', 1)
s = s.replace('@st.cache_data(show_spinner=False, max_entries=8)\ndef gerar_excel_modelo_dominio', 'def gerar_excel_modelo_dominio', 1)

# Mantém o cache curto do Supabase, que reduz chamadas de rede sem serializar arquivos pesados.
assert "@st.cache_data(show_spinner=False, ttl=120, max_entries=20)\ndef carregar_classificacoes_online" in s
assert '@st.cache_data(show_spinner=False, max_entries=12)\ndef processar_extrato_unificado' not in s
assert '@st.cache_data(show_spinner=False, max_entries=8)\ndef gerar_excel_modelo_dominio' not in s

p.write_text(s, encoding='utf-8')
print('Caches pesados removidos; cache curto do Supabase mantido.')
