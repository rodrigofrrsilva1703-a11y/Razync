from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
marker = '/* Organizer directory vertical fix v3 */'
if marker in s:
    raise SystemExit('Ajuste do Organizador já aplicado')

needle = '''            st.markdown(
                '<div class="rz-directory-eyebrow">Empresas</div>',
                unsafe_allow_html=True,
            )
            st.title(titulo_pagina_organizador)
            st.caption(descricao_pagina_organizador)
'''
if needle not in s:
    raise SystemExit('Cabeçalho do diretório de empresas não encontrado')

replacement = '''            st.markdown(
                """
                <style>
                /* Organizer directory vertical fix v3 */
                main[data-testid="stMain"] .block-container {
                    padding-top: 0 !important;
                    margin-top: -5.25rem !important;
                }
                @media (max-width: 900px) {
                    main[data-testid="stMain"] .block-container {
                        margin-top: -2.25rem !important;
                    }
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="rz-directory-eyebrow">Empresas</div>',
                unsafe_allow_html=True,
            )
            st.title(titulo_pagina_organizador)
            st.caption(descricao_pagina_organizador)
'''

s = s.replace(needle, replacement, 1)
p.write_text(s, encoding='utf-8')
