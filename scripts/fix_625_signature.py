from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '    def _ler_planilha_conferencia_625(file_bytes, banco_slug):\n'
new = '    def _ler_planilha_conferencia_625(file_bytes, banco_slug, conta_alvo=None):\n'
if old not in s:
    raise SystemExit('assinatura antiga da 625 não encontrada')
s = s.replace(old, new, 1)

old2 = '            return _ler_planilha_conf_legado_625(file_bytes, banco_slug)\n'
new2 = '            return _ler_planilha_conf_legado_625(file_bytes, banco_slug, conta_alvo)\n'
if old2 not in s:
    raise SystemExit('fallback antigo da 625 não encontrado')
s = s.replace(old2, new2, 1)

p.write_text(s, encoding='utf-8')
print('OK: leitor da conferência 625 aceita arquivo, banco e conta')
