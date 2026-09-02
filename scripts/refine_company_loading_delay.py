from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_open = '''        def _abrir_empresa_catalogo(empresa_catalogo):
            chave_destino = empresa_catalogo.get(
                'chave_sistema', empresa_catalogo['chave']
            )
            if chave_destino == 'nova_geracao':
                st.session_state['org_estabelecimento_nova_geracao_card'] = (
                    empresa_catalogo.get('estabelecimento', 'matriz')
                )
            st.session_state['_rz_empresa_loading'] = {
                'codigo': str(empresa_catalogo.get('codigo', '')),
                'nome': str(empresa_catalogo.get('nome', 'Empresa')),
            }
            st.session_state['empresa_organizador'] = chave_destino
            st.rerun()
'''
new_open = '''        def _abrir_empresa_catalogo(empresa_catalogo):
            chave_destino = empresa_catalogo.get(
                'chave_sistema', empresa_catalogo['chave']
            )
            st.session_state['_rz_empresa_loading'] = {
                'codigo': str(empresa_catalogo.get('codigo', '')),
                'nome': str(empresa_catalogo.get('nome', 'Empresa')),
                'chave_destino': chave_destino,
                'estabelecimento': empresa_catalogo.get('estabelecimento', 'matriz'),
            }
            st.rerun()
'''
if old_open not in text:
    raise SystemExit('Função atual de abertura de empresa não encontrada')
text = text.replace(old_open, new_open, 1)

old_loading_start = "_empresa_loading = st.session_state.pop('_rz_empresa_loading', None)\nif _empresa_loading:\n"
new_loading_start = "_empresa_loading = st.session_state.get('_rz_empresa_loading')\nif _empresa_loading:\n"
if old_loading_start not in text:
    raise SystemExit('Início do loading não encontrado')
text = text.replace(old_loading_start, new_loading_start, 1)

old_finish = '''    # Janela mínima apenas para a transição chegar ao navegador antes do rerun final.
    time.sleep(0.16)
    st.rerun()
'''
new_finish = '''    # Mantém o diretório sob o overlay e só troca a empresa depois da transição.
    # Isso evita que a nova tela comece a renderizar por baixo do loading.
    time.sleep(0.55)
    _chave_destino_loading = _empresa_loading.get('chave_destino')
    if _chave_destino_loading == 'nova_geracao':
        st.session_state['org_estabelecimento_nova_geracao_card'] = (
            _empresa_loading.get('estabelecimento', 'matriz')
        )
    if _chave_destino_loading:
        st.session_state['empresa_organizador'] = _chave_destino_loading
    st.session_state.pop('_rz_empresa_loading', None)
    st.rerun()
'''
if old_finish not in text:
    raise SystemExit('Final atual do loading não encontrado')
text = text.replace(old_finish, new_finish, 1)

path.write_text(text, encoding='utf-8')
