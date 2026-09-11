from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
old = '''    configs = [
        {"nome": "Banco do Brasil · Conta 8", "slug": "banco_brasil", "banco": "banco_brasil_625", "conta": "8"},
        {"nome": "Caixa · Conta 504", "slug": "caixa", "banco": "caixa_625", "conta": "504"},
        {"nome": "Sicredi · Conta 3999", "slug": "sicredi", "banco": "sicredi_625", "conta": "3999"},
    ]'''
new = '''    # O motor genérico de conferência identifica/destina os arquivos pela chave
    # bancária normal (banco_brasil/caixa/sicredi). O sufixo _625 é interno ao
    # parser e impedia BB/Sicredi de serem associados quando os 3 bancos eram
    # enviados juntos. O wrapper abaixo roteia as chaves normais ao parser 625.
    configs = [
        {"nome": "Banco do Brasil · Conta 8", "slug": "banco_brasil", "banco": "banco_brasil", "conta": "8"},
        {"nome": "Caixa · Conta 504", "slug": "caixa", "banco": "caixa", "conta": "504"},
        {"nome": "Sicredi · Conta 3999", "slug": "sicredi", "banco": "sicredi", "conta": "3999"},
    ]'''
if old not in s:
    raise SystemExit('configs 625 não encontrados')
s = s.replace(old, new, 1)
old2 = '''        try:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conferencia_625
            renderizar_conferencia_autokraft(
                "valean_625", bancos_config=configs,
                rotulo_planilha="Planilha final organizada da empresa 625",
            )
        finally:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conf_original_625'''
new2 = '''        _processar_extrato_conf_original_625 = globals().get("processar_extrato_conferencia_empresa")

        def _processar_extrato_conferencia_625(file_bytes, filename, banco_forcado=None):
            # Quando apenas um banco está selecionado, o motor informa a chave
            # normal. Encaminha-a ao leitor dedicado da 625. Com vários bancos,
            # mantém a leitura genérica para identificar pelo próprio arquivo.
            if banco_forcado in {"banco_brasil", "caixa", "sicredi"}:
                return processar_extrato_625(file_bytes, banco_forcado).to_dict("records")
            return _processar_extrato_conf_original_625(file_bytes, filename, banco_forcado)

        try:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conferencia_625
            globals()["processar_extrato_conferencia_empresa"] = _processar_extrato_conferencia_625
            renderizar_conferencia_autokraft(
                "valean_625", bancos_config=configs,
                rotulo_planilha="Planilha final organizada da empresa 625",
            )
        finally:
            globals()["ler_planilha_organizada_conferencia"] = _ler_planilha_conf_original_625
            globals()["processar_extrato_conferencia_empresa"] = _processar_extrato_conf_original_625'''
if old2 not in s:
    raise SystemExit('bloco conferência 625 não encontrado')
s = s.replace(old2, new2, 1)
p.write_text(s, encoding='utf-8')
