"""Padronização conservadora de históricos bancários para Modelo Domínio."""
from __future__ import annotations
import re


def limpar_historico_extrato(historico, valor, adicionar_natureza=True):
    texto = re.sub(r"\s+", " ", str(historico or "")).strip(" -")
    texto = re.sub(r"^(?:Pago|Recebido):\s*", "", texto, flags=re.I).strip()
    if re.search(r"\bRENDIMENTOS?\b|\bRENDIMENTO\b", texto, flags=re.I):
        base = "RENDIMENTOS"
    else:
        # Remove apenas rótulos operacionais; preserva a contraparte e referências úteis.
        padroes = [
            r"^PAGAMENTO\s+DE\s+BOLETO(?:\s+OUTROS\s+BANCOS)?\s+",
            r"^PAGAMENTO\s+BOLETO\s+",
            r"^BOLETO\s+PAGO\s+",
            r"^PIX\s+ENVIADO\s+",
            r"^PIX\s+RECEBIDO\s+",
            r"^TED\s+ENVIADA\s+",
            r"^TED\s+RECEBIDA\s+",
            r"^TRANSFER[EÊ]NCIA\s+ENVIADA\s+",
            r"^TRANSFER[EÊ]NCIA\s+RECEBIDA\s+",
            r"^TRANSF(?:ERENCIA)?\s+CC\s+ITAU\s+",
            r"^RECEBIMENTOS?\s+",
        ]
        base = texto
        for padrao in padroes:
            novo = re.sub(padrao, "", base, flags=re.I).strip(" -")
            if novo != base:
                base = novo
                break
        base = re.sub(r"\s+", " ", base).strip(" -") or texto
    if not adicionar_natureza:
        return base
    prefixo = "Recebido: " if float(valor) > 0 else "Pago: " if float(valor) < 0 else ""
    return prefixo + base
