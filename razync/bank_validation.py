"""Validações pequenas e reutilizáveis para parsers bancários do Razync."""

from __future__ import annotations

from typing import Iterable, Optional


def validar_fechamento_saldo(
    saldo_inicial: Optional[float],
    saldo_final: Optional[float],
    movimentos: Iterable[float],
    tolerancia: float = 0.05,
) -> dict:
    """Confere se saldo inicial + movimentos fecha com o saldo final informado."""
    if saldo_inicial is None or saldo_final is None:
        return {
            "disponivel": False,
            "ok": None,
            "saldo_calculado": None,
            "saldo_final": saldo_final,
            "diferenca": None,
        }

    saldo_calculado = round(float(saldo_inicial) + sum(float(v) for v in movimentos), 2)
    diferenca = round(saldo_calculado - float(saldo_final), 2)
    return {
        "disponivel": True,
        "ok": abs(diferenca) <= float(tolerancia),
        "saldo_calculado": saldo_calculado,
        "saldo_final": round(float(saldo_final), 2),
        "diferenca": diferenca,
    }


def diagnostico_pdf_sem_lancamentos(
    banco: str,
    sem_camada_texto: bool,
    ocr_executado: bool = False,
    erro_ocr: str = "",
) -> str:
    """Gera uma mensagem curta e útil sem expor traceback interno."""
    nome_banco = str(banco or "banco").replace("BANCO ", "").strip() or "banco"
    if sem_camada_texto and erro_ocr:
        return (
            f"O PDF do {nome_banco} não possui camada de texto e o OCR não pôde "
            f"ser concluído. Detalhe técnico: {erro_ocr}"
        )
    if sem_camada_texto and ocr_executado:
        return (
            f"O PDF do {nome_banco} foi processado por OCR, mas nenhum lançamento "
            "bancário válido foi reconhecido."
        )
    if sem_camada_texto:
        return (
            f"O PDF do {nome_banco} não possui camada de texto e precisa do OCR "
            "para ser interpretado."
        )
    return (
        f"Nenhum lançamento bancário válido foi reconhecido no arquivo do {nome_banco}."
    )
