from pathlib import Path
import ast
import textwrap

APP = Path('app.py')
texto = APP.read_text(encoding='utf-8')
original = texto

# 1) Santander passa a ser um banco reconhecido pelo motor central.
alvo = """    if 'sicredi' in texto:\n        return 'sicredi'\n    if 'banco do brasil' in texto:\n"""
novo = """    if 'sicredi' in texto:\n        return 'sicredi'\n    if 'santander' in texto:\n        return 'santander'\n    if 'banco do brasil' in texto:\n"""
if alvo not in texto:
    raise RuntimeError('Não foi localizado o ponto de identificação dos bancos.')
texto = texto.replace(alvo, novo, 1)

alvo = """        'daycoval': 'Daycoval', 'sicredi': 'Sicredi',\n        'banco_brasil': 'Banco do Brasil'\n"""
novo = """        'daycoval': 'Daycoval', 'sicredi': 'Sicredi',\n        'santander': 'Santander', 'banco_brasil': 'Banco do Brasil'\n"""
if alvo not in texto:
    raise RuntimeError('Não foi localizado o mapa de nomes de bancos.')
texto = texto.replace(alvo, novo, 1)

# 2) Santander também pode ensinar a Base Inteligente.
alvo = "{'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi'}"
novo = "{'itau', 'bradesco', 'fibra', 'daycoval', 'sicredi', 'santander'}"
if alvo not in texto:
    raise RuntimeError('Não foi localizado o conjunto de bancos da Base Inteligente.')
texto = texto.replace(alvo, novo, 1)

# 3) Conferência reconhece Santander ao ler o Modelo Domínio.
alvo = """                    'fibra': 'BANCO FIBRA', 'daycoval': 'BANCO DAYCOVAL',\n                    'sicredi': 'SICREDI', 'banco_brasil': 'BANCO DO BRASIL'\n"""
novo = """                    'fibra': 'BANCO FIBRA', 'daycoval': 'BANCO DAYCOVAL',\n                    'sicredi': 'SICREDI', 'santander': 'BANCO SANTANDER',\n                    'banco_brasil': 'BANCO DO BRASIL'\n"""
if alvo not in texto:
    raise RuntimeError('Não foi localizado o mapa de descrições bancárias da conferência.')
texto = texto.replace(alvo, novo, 1)

# 4) Para apenas um banco, a conferência não mostra seleção desnecessária.
alvo = '''    conferir_todos = st.checkbox(\n        "Conferir os dois bancos",\n        value=False,\n        key=f"{prefixo_chaves}_conferir_todos"\n    )\n    if conferir_todos:\n        bancos_escolhidos = nomes_bancos\n        st.caption("Serão apresentados relatórios separados para os bancos selecionados.")\n    else:\n        bancos_escolhidos = st.multiselect(\n            "Bancos que serão conferidos",\n            nomes_bancos,\n            default=[nomes_bancos[0]],\n            key=f"{prefixo_chaves}_bancos_conferencia"\n        )\n'''
novo = '''    if len(configs) == 1:\n        bancos_escolhidos = nomes_bancos\n        st.caption(f"Banco da conferência: {nomes_bancos[0]}.")\n    else:\n        conferir_todos = st.checkbox(\n            "Conferir todos os bancos",\n            value=False,\n            key=f"{prefixo_chaves}_conferir_todos"\n        )\n        if conferir_todos:\n            bancos_escolhidos = nomes_bancos\n            st.caption("Serão apresentados relatórios separados para os bancos selecionados.")\n        else:\n            bancos_escolhidos = st.multiselect(\n                "Bancos que serão conferidos",\n                nomes_bancos,\n                default=[nomes_bancos[0]],\n                key=f"{prefixo_chaves}_bancos_conferencia"\n            )\n'''
if alvo not in texto:
    raise RuntimeError('Não foi localizado o seletor atual da conferência.')
texto = texto.replace(alvo, novo, 1)

# 5) A área 285 passa a ter Organizar arquivos + Base Inteligente e conferência Santander.
inicio = "    if st.session_state['empresa_organizador'] == 'lcarlos':\n"
fim = "    if st.session_state['empresa_organizador'] in {\n        'autokraft_industrial', 'autokraft_projetos', 'isa'\n    }:\n"
pos_inicio = texto.find(inicio)
pos_fim = texto.find(fim, pos_inicio)
if pos_inicio < 0 or pos_fim < 0:
    raise RuntimeError('Não foi possível localizar o bloco da empresa 285.')

bloco_atual = texto[pos_inicio:pos_fim]
corpo_atual = bloco_atual[len(inicio):]
corpo_indented = textwrap.indent(corpo_atual, '    ')

cabecalho = """    if st.session_state['empresa_organizador'] == 'lcarlos':\n        contas_lcarlos = {'santander': '513'}\n        aba_operacoes_lcarlos, aba_base_lcarlos = st.tabs([\n            'Organizar arquivos',\n            'Base Inteligente',\n        ])\n\n        with aba_base_lcarlos:\n            renderizar_base_inteligente_empresa(\n                'lcarlos',\n                '285 - L. Carlos Gomes',\n                {'santander'},\n                contas_lcarlos,\n            )\n\n        with aba_operacoes_lcarlos:\n"""
rodape = """\n            st.markdown('#### Conferência — 285 - L. Carlos Gomes')\n            renderizar_conferencia_autokraft(\n                'lcarlos',\n                bancos_config=[{'nome': 'Santander', 'slug': 'santander'}],\n            )\n\n"""
texto = texto[:pos_inicio] + cabecalho + corpo_indented + rodape + texto[pos_fim:]

if texto == original:
    raise RuntimeError('Nenhuma alteração foi aplicada.')

ast.parse(texto)
APP.write_text(texto, encoding='utf-8')
print('Patch da empresa 285 aplicado com sucesso.')
