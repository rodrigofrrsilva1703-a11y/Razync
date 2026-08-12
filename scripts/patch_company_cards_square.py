from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# 1) Cards principais: um pouco maiores e alinhados à esquerda.
old_css = '''        /* Cards de empresas: maiores, próximos e alinhados ao centro. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 210px !important;
            min-width: 210px !important;
            max-width: 210px !important;
            display: flex !important;
            justify-content: center !important;
        }
        .st-key-org_empresa_card_nova {
            margin-left: auto !important;
            margin-right: 24px !important;
        }
        .st-key-org_empresa_card_autokraft {
            margin-left: 24px !important;
            margin-right: auto !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 210px !important;
            min-width: 210px !important;
            max-width: 210px !important;
            height: 210px !important;
            min-height: 210px !important;
            max-height: 210px !important;
'''
new_css = '''        /* Cards de empresas: levemente maiores e alinhados à esquerda. */
        .st-key-org_empresa_card_nova,
        .st-key-org_empresa_card_autokraft {
            width: 224px !important;
            min-width: 224px !important;
            max-width: 224px !important;
            display: flex !important;
            justify-content: flex-start !important;
            margin: 0 !important;
        }
        .st-key-org_empresa_card_nova {
            margin-right: 10px !important;
        }
        .st-key-org_empresa_card_autokraft {
            margin-left: 0 !important;
        }
        .st-key-org_empresa_card_nova button,
        .st-key-org_empresa_card_autokraft button {
            width: 224px !important;
            min-width: 224px !important;
            max-width: 224px !important;
            height: 224px !important;
            min-height: 224px !important;
            max-height: 224px !important;
'''
if text.count(old_css) != 1:
    raise SystemExit(f'CSS principal encontrado {text.count(old_css)} vezes; alteração cancelada.')
text = text.replace(old_css, new_css, 1)
text = text.replace('max-width: 176px !important;', 'max-width: 188px !important;', 1)
text = text.replace('max-width: 172px !important;', 'max-width: 184px !important;', 1)

old_cols = '''        col_emp1, col_emp2 = st.columns(2)
'''
new_cols = '''        col_emp1, col_emp2, _espaco_empresas = st.columns([1, 1, 4])
'''
if text.count(old_cols) != 1:
    raise SystemExit(f'Layout dos cards encontrado {text.count(old_cols)} vezes; alteração cancelada.')
text = text.replace(old_cols, new_cols, 1)

# 2) Cache dos processamentos de Excel que são repetidos a cada interação do Streamlit.
old_nova = '''def processar_nova_geracao_banco(file_bytes, nome_aba, conta_esperada, descricao_banco):
'''
new_nova = '''@st.cache_data(show_spinner=False, max_entries=12)
def processar_nova_geracao_banco(file_bytes, nome_aba, conta_esperada, descricao_banco):
'''
if text.count(old_nova) != 1:
    raise SystemExit(f'Processador Nova Geração encontrado {text.count(old_nova)} vezes; alteração cancelada.')
text = text.replace(old_nova, new_nova, 1)

old_ak = '''def processar_mapa_autokraft(file_bytes, filename=''):
'''
new_ak = '''@st.cache_data(show_spinner=False, max_entries=12)
def processar_mapa_autokraft(file_bytes, filename=''):
'''
if text.count(old_ak) != 1:
    raise SystemExit(f'Processador Autokraft encontrado {text.count(old_ak)} vezes; alteração cancelada.')
text = text.replace(old_ak, new_ak, 1)

# 3) Reduz o custo visual da transição de página, evitando blur pesado no navegador.
text = text.replace('                filter: blur(2px);\n', '', 1)
text = text.replace('                filter: blur(0);\n', '', 2)
text = text.replace('            will-change: opacity, transform, filter;\n', '            will-change: opacity, transform;\n', 1)

path.write_text(text, encoding='utf-8')
print('Cards alinhados à esquerda, ampliados e processamentos pesados cacheados.')
