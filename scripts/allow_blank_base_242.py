from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

repls = {
    "('Despesa', 'debito', {'0'}, False),": "('Despesa', 'debito', {'0', ''}, False),",
    "('Fornecedor', 'debito', {'166', '0'}, False),": "('Fornecedor', 'debito', {'166', '0', ''}, False),",
    "('Recebido', 'credito', {'166', '0', '14', '16'}, False),": "('Recebido', 'credito', {'166', '0', '14', '16', ''}, False),",
    "'Fornecedor: somente DÉBITO 166 ou 0 é substituído. '": "'Fornecedor: DÉBITO 166, 0 ou vazio pode ser classificado. '",
    "'Recebido: somente CRÉDITO 166, 0, 14 ou 16 é substituído. '": "'Recebido: CRÉDITO 166, 0, 14, 16 ou vazio pode ser classificado. '",
    "st.caption('Somente as abas bancárias serão classificadas; na Despesa, apenas linhas com DÉBITO 0. A aba Principal é preservada.')": "st.caption('Somente as abas bancárias serão classificadas; na Despesa, linhas com DÉBITO 0 ou vazio. A aba Principal é preservada.')",
    "st.caption('Somente as abas bancárias serão classificadas; linhas com DÉBITO 166 ou 0. A aba Principal é preservada.')": "st.caption('Somente as abas bancárias serão classificadas; linhas com DÉBITO 166, 0 ou vazio. A aba Principal é preservada.')",
    "st.caption('Somente as abas bancárias serão classificadas; linhas com CRÉDITO 166, 0, 14 ou 16. A aba Principal é preservada.')": "st.caption('Somente as abas bancárias serão classificadas; linhas com CRÉDITO 166, 0, 14, 16 ou vazio. A aba Principal é preservada.')",
}

for old, new in repls.items():
    if old not in s:
        raise SystemExit(f'Padrão não encontrado: {old}')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
