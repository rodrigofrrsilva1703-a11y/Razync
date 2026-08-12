from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''        if base_empresa:
            linhas = []
            for item in base_empresa:
                linhas.append({
                    'Banco': nome_banco_por_chave(item.get('banco', '')),
                    'Débito': item.get('debito', ''),
                    'Crédito': item.get('credito', ''),
                    'Ocorrências': item.get('ocorrencias', 0),
                    'Períodos': len(item.get('periodos') or []),
                    'Exemplo': item.get('exemplo_historico', '')
                })
            st.dataframe(pd.DataFrame(linhas), use_container_width=True, height=300)
        else:
            st.info("Esta empresa ainda não possui padrões aprendidos.")

'''
new = '''        if not base_empresa:
            st.info("Esta empresa ainda não possui padrões aprendidos.")

'''
if text.count(old) != 1:
    raise SystemExit(f'Relatório visual da Base Inteligente encontrado {text.count(old)} vezes.')
text = text.replace(old, new, 1)

# Garante que a listagem detalhada não volte a aparecer nessa área.
bloco_inicio = text.find('def renderizar_base_inteligente_empresa(')
bloco_fim = text.find('# ==============================================================================', bloco_inicio)
bloco = text[bloco_inicio:bloco_fim]
for trecho in ["'Ocorrências':", "'Períodos':", "'Exemplo':"]:
    if trecho in bloco:
        raise SystemExit(f'Coluna de relatório ainda presente na Base Inteligente: {trecho}')

path.write_text(text, encoding='utf-8')
print('Relatório detalhado da Base Inteligente removido; permanecem apenas status e ações.')
