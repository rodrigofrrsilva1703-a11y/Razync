from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

start_marker = "    # --- Ferramenta exclusiva 1529: Nibo -> Modelo Dominio ---\n"
tela4_marker = "# ==============================================================================\n# TELA 4: CONCILIAÇÃO COM O RAZÃO DA DOMÍNIO\n# ==============================================================================\n"

start = text.find(start_marker)
if start == -1:
    raise SystemExit('Bloco Nibo 1529 não encontrado')

# O bloco foi adicionado no fim do arquivo dentro da TELA 4. Captura até o EOF.
block = text[start:]
text_without = text[:start].rstrip() + "\n"

insert_at = text_without.find(tela4_marker)
if insert_at == -1:
    raise SystemExit('Marcador da TELA 4 não encontrado')

# O bloco já possui indentação de 4 espaços, adequada para a TELA 3 / organizador.
new_text = (
    text_without[:insert_at].rstrip()
    + "\n\n"
    + block.rstrip()
    + "\n\n"
    + text_without[insert_at:]
)

# Garantias simples de posição.
idx_block = new_text.find(start_marker)
idx_tela4 = new_text.find(tela4_marker)
if not (0 <= idx_block < idx_tela4):
    raise SystemExit('Bloco Nibo não ficou antes da TELA 4')
if new_text.count(start_marker) != 1:
    raise SystemExit('Bloco Nibo duplicado após patch')

path.write_text(new_text, encoding='utf-8')
print('Ferramenta Nibo 1529 movida para a TELA 3 com sucesso')
