"""Leitura do extrato Santander Empresarial no formato Data / Histórico / Valor."""

from __future__ import annotations

import re
from typing import List, Dict, Any

_LINHA = re.compile(
    r"^(?P<data>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<historico>.+?)\s+"
    r"(?P<negativo>-\s*)?R\$\s*"
    r"(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
    re.IGNORECASE,
)


def parece_extrato_santander_empresarial(texto: str) -> bool:
    bruto = (texto or "").upper()
    return (
        "INTERNET BANKING EMPRESARIAL" in bruto
        and "SANTANDER" in bruto
        and "SALDO DO DIA" in bruto
        and "R$" in bruto
    )


def _valor_br(valor: str) -> float:
    return float(valor.replace(".", "").replace(",", "."))


def processar_extrato_santander_empresarial_texto(
    texto: str,
    banco: str = "BANCO SANTANDER",
) -> List[Dict[str, Any]]:
    """Extrai somente movimentos do Santander, ignorando linhas de saldo.

    O sinal é obtido diretamente do PDF: linhas com ``- R$`` são saídas;
    linhas com ``R$`` sem hífen são entradas. Isso evita inferência incorreta
    baseada no texto do histórico.
    """
    lancamentos: List[Dict[str, Any]] = []
    for linha in (texto or "").splitlines():
        linha = re.sub(r"\s+", " ", linha).strip()
        match = _LINHA.match(linha)
        if not match:
            continue

        historico = match.group("historico").strip(" -")
        historico_upper = historico.upper()
        if "SALDO DO DIA" in historico_upper or "SALDO ANTERIOR" in historico_upper:
            continue

        valor = _valor_br(match.group("valor"))
        if match.group("negativo"):
            valor = -valor
        if abs(valor) < 0.005:
            continue

        lancamentos.append({
            "DESCRIÇÃO": banco,
            "DATA": match.group("data"),
            "VALOR": round(valor, 2),
            "DÉBITO": "",
            "CRÉDITO": "",
            "HISTÓRICO": historico,
        })

    return lancamentos
