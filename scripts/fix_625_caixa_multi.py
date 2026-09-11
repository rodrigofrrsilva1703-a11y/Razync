from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''        def _processar_extrato_conferencia_625(file_bytes, filename, banco_forcado=None):
            # Quando apenas um banco está selecionado, o motor informa a chave
            # normal. Encaminha-a ao leitor dedicado da 625. Com vários bancos,
            # mantém a leitura genérica para identificar pelo próprio arquivo.
            if banco_forcado in {"banco_brasil", "caixa", "sicredi"}:
                return processar_extrato_625(file_bytes, banco_forcado).to_dict("records")
            return _processar_extrato_conf_original_625(file_bytes, filename, banco_forcado)
'''
new = '''        def _processar_extrato_conferencia_625(file_bytes, filename, banco_forcado=None):
            # Usa sempre o parser dedicado da 625 quando o banco puder ser
            # determinado. Isso é essencial quando os 3 PDFs são enviados juntos,
            # pois nesse caso o motor genérico chama com banco_forcado=None.
            banco_625 = banco_forcado if banco_forcado in {"banco_brasil", "caixa", "sicredi"} else None
            if banco_625 is None:
                nome_arquivo = normalizar_texto(texto_celula_seguro(filename))
                if "caixa" in nome_arquivo or "cef" in nome_arquivo:
                    banco_625 = "caixa"
                elif "sicredi" in nome_arquivo:
                    banco_625 = "sicredi"
                elif "banco do brasil" in nome_arquivo or re.search(r"(^|[^a-z])bb([^a-z]|$)", nome_arquivo):
                    banco_625 = "banco_brasil"
            if banco_625:
                return processar_extrato_625(file_bytes, banco_625).to_dict("records")
            return _processar_extrato_conf_original_625(file_bytes, filename, banco_forcado)
'''
if old not in s:
    raise SystemExit('wrapper de conferência 625 não encontrado')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
