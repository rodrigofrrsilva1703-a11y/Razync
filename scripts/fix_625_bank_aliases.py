from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''    def _ler_planilha_conferencia_625(file_bytes, banco_slug, conta_alvo=None):\n        if banco_slug not in {"banco_brasil", "caixa", "sicredi"}:\n            return _ler_planilha_conf_legado_625(file_bytes, banco_slug, conta_alvo)\n        nomes = {\n'''
new = '''    def _ler_planilha_conferencia_625(file_bytes, banco_slug, conta_alvo=None):\n        banco_original = banco_slug\n        if isinstance(banco_slug, str) and banco_slug.endswith("_625"):\n            banco_slug = banco_slug.removesuffix("_625")\n        if banco_slug not in {"banco_brasil", "caixa", "sicredi"}:\n            return _ler_planilha_conf_legado_625(file_bytes, banco_original, conta_alvo)\n        nomes = {\n'''
if old not in s:
    raise SystemExit('bloco alvo da conferência 625 não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
assert 'banco_slug = banco_slug.removesuffix("_625")' in s
print('OK: aliases *_625 normalizados antes da leitura das abas')
