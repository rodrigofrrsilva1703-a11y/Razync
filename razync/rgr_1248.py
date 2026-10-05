"""Processamento específico da empresa 1248 - RGR Importadora e Exportadora.

Fonte principal: extrato Itaú (conta Domínio 508).
Fonte auxiliar: planilha mensal de entradas e saídas.

Regras:
- "BOLETOS RECEBIDOS" do extrato são substituídos pelos boletos individuais
  da aba de entradas, usando a data de pagamento e validando o total do dia.
- Saídas são conferidas por data + valor contra a aba SAIDAS. Quando o extrato
  não traz identificação suficiente do favorecido, o nome da planilha completa
  o histórico.
"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from typing import List

import pandas as pd
from pypdf import PdfReader


CONTA_ITAU_RGR = "508"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


@dataclass
class BoletoRGR:
    pagador: str
    pagamento: pd.Timestamp
    valor: float
    nf: str = ""
    observacao: str = ""
    usado: bool = False


@dataclass
class SaidaRGR:
    data: pd.Timestamp
    valor: float
    razao_social: str
    lancamento: str = ""
    observacao: str = ""
    usado: bool = False


def _normalizar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def _normalizar_chave(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", texto).strip()


def _moeda_br(valor) -> float:
    if isinstance(valor, (int, float)) and not pd.isna(valor):
        return float(valor)
    texto = str(valor or "").replace("R$", "").replace("\xa0", " ").strip()
    texto = texto.replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _valor_planilha(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor or "").strip()
    if not texto or texto.startswith("="):
        return None
    try:
        return _moeda_br(texto)
    except Exception:
        return None


def _texto_pdf(conteudo: bytes) -> str:
    reader = PdfReader(io.BytesIO(conteudo), strict=False)
    return "\n".join((pagina.extract_text() or "") for pagina in reader.pages)


def _limpar_historico_extrato(texto: str) -> str:
    texto = _normalizar_espacos(texto)
    texto = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", " ", texto)
    texto = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", " ", texto)
    return _normalizar_espacos(texto).strip(" -")


def ler_saldos_extrato_itau_rgr(conteudo: bytes) -> dict:
    texto = _texto_pdf(conteudo)
    saldo_inicial = None
    saldo_final = None

    m_inicial = re.search(
        r"\b\d{2}/\d{2}/\d{4}\s+SALDO ANTERIOR\s+([\d.]+,\d{2})",
        texto,
        re.I,
    )
    if m_inicial:
        saldo_inicial = _moeda_br(m_inicial.group(1))

    finais = re.findall(
        r"\b\d{2}/\d{2}/\d{4}\s+SALDO (?:EM CONTA CORRENTE|TOTAL DISPONÍVEL DIA)\s+([\d.]+,\d{2})",
        texto,
        re.I,
    )
    if finais:
        saldo_final = _moeda_br(finais[-1])

    return {
        "saldo_inicial": round(float(saldo_inicial), 2) if saldo_inicial is not None else None,
        "saldo_final_informado": round(float(saldo_final), 2) if saldo_final is not None else None,
    }


def ler_extrato_itau_rgr(conteudo: bytes) -> pd.DataFrame:
    """Extrai os movimentos do extrato Itaú e ignora linhas de saldo."""
    texto = _texto_pdf(conteudo)
    if "RGR IMPORTADORA" not in texto.upper() and "0021550-8" not in texto:
        raise ValueError("O PDF enviado não parece ser o extrato Itaú da RGR.")

    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    blocos = []
    atual = None
    padrao_data = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.*)$")

    for linha in linhas:
        match = padrao_data.match(linha)
        if match:
            if atual:
                blocos.append(atual)
            atual = {"data": match.group(1), "partes": [match.group(2)]}
        elif atual:
            atual["partes"].append(linha)
    if atual:
        blocos.append(atual)

    registros = []
    regex_moeda = re.compile(r"(?<!\d)([-+]?\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)")
    for bloco in blocos:
        conteudo_bloco = _normalizar_espacos(" ".join(bloco["partes"]))
        norm = conteudo_bloco.upper()
        if (
            norm.startswith("SALDO ")
            or "SALDO TOTAL DISPONÍVEL" in norm
            or "SALDO EM CONTA" in norm
        ):
            continue

        moedas = list(regex_moeda.finditer(conteudo_bloco))
        if not moedas:
            continue

        moeda = moedas[-1]
        valor = _moeda_br(moeda.group(1))
        historico = _limpar_historico_extrato(conteudo_bloco[: moeda.start()])
        if not historico or abs(valor) < 0.005:
            continue

        data = pd.to_datetime(bloco["data"], dayfirst=True, errors="coerce")
        if pd.isna(data):
            continue

        historico = re.sub(
            r"^(?:Pago|Recebido):\s*", "", historico, flags=re.I
        ).strip()
        prefixo = "Recebido: " if valor > 0 else "Pago: "

        registros.append(
            {
                "DESCRIÇÃO": "BANCO ITAÚ",
                "DATA": data,
                "VALOR": round(float(valor), 2),
                "DÉBITO": CONTA_ITAU_RGR if valor > 0 else "",
                "CRÉDITO": CONTA_ITAU_RGR if valor < 0 else "",
                "HISTÓRICO": prefixo + historico,
            }
        )

    if not registros:
        raise ValueError("Nenhum lançamento foi reconhecido no extrato Itaú da RGR.")

    return pd.DataFrame(registros, columns=COLUNAS_MODELO)


def _achar_aba(xls: pd.ExcelFile, termos: list[str]):
    for nome in xls.sheet_names:
        chave = _normalizar_chave(nome)
        if all(termo in chave for termo in termos):
            return nome
    return None


def ler_boletos_planilha_rgr(conteudo: bytes) -> List[BoletoRGR]:
    """Lê o bloco esquerdo da aba de entradas, que detalha BOLETOS RECEBIDOS."""
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    aba = _achar_aba(xls, ["ENTRADAS"]) or xls.sheet_names[0]
    bruto = pd.read_excel(io.BytesIO(conteudo), sheet_name=aba, header=None)

    linha_cabecalho = None
    for indice in range(min(len(bruto), 20)):
        nomes = [_normalizar_chave(v) for v in bruto.iloc[indice, :6].tolist()]
        if (
            "PAGADOR" in nomes
            and "PAGAMENTO" in nomes
            and "VALOR" in nomes
        ):
            linha_cabecalho = indice
            break

    if linha_cabecalho is None:
        raise ValueError(
            "Não encontrei o cabeçalho PAGADOR / PAGAMENTO / VALOR na aba de entradas."
        )

    nomes = [_normalizar_chave(v) for v in bruto.iloc[linha_cabecalho, :6].tolist()]
    col_pagador = nomes.index("PAGADOR")
    col_pagamento = nomes.index("PAGAMENTO")
    col_valor = nomes.index("VALOR")
    col_nf = next(
        (i for i, nome in enumerate(nomes) if nome in {"NFS", "NF", "NOTA FISCAL"}),
        None,
    )
    col_obs = next((i for i, nome in enumerate(nomes) if "OBS" in nome), None)

    boletos: List[BoletoRGR] = []
    for indice in range(linha_cabecalho + 1, len(bruto)):
        pagador = _normalizar_espacos(bruto.iat[indice, col_pagador])
        pagamento = pd.to_datetime(
            bruto.iat[indice, col_pagamento], dayfirst=True, errors="coerce"
        )
        valor = _valor_planilha(bruto.iat[indice, col_valor])

        if (
            not pagador
            or _normalizar_chave(pagador).startswith("TOTAL")
            or pd.isna(pagamento)
            or valor is None
            or valor <= 0
        ):
            continue

        nf = _normalizar_espacos(bruto.iat[indice, col_nf]) if col_nf is not None else ""
        obs = _normalizar_espacos(bruto.iat[indice, col_obs]) if col_obs is not None else ""
        boletos.append(
            BoletoRGR(
                pagador=pagador,
                pagamento=pagamento.normalize(),
                valor=round(float(valor), 2),
                nf=nf,
                observacao=obs,
            )
        )

    if not boletos:
        raise ValueError("Nenhum boleto individual foi encontrado na aba de entradas.")

    return boletos


def ler_saidas_planilha_rgr(conteudo: bytes) -> List[SaidaRGR]:
    """Lê a aba SAIDAS para completar favorecidos ausentes no extrato."""
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    aba = _achar_aba(xls, ["SAIDAS"])
    if aba is None:
        raise ValueError("Não encontrei a aba SAIDAS na planilha da RGR.")

    bruto = pd.read_excel(io.BytesIO(conteudo), sheet_name=aba, header=None)
    linha_cabecalho = None
    for indice in range(min(len(bruto), 30)):
        nomes = [_normalizar_chave(v) for v in bruto.iloc[indice].tolist()]
        if (
            "DATA" in nomes
            and "RAZAO SOCIAL" in nomes
            and any(nome.startswith("VALOR") for nome in nomes)
        ):
            linha_cabecalho = indice
            break

    if linha_cabecalho is None:
        raise ValueError(
            "Não encontrei o cabeçalho Data / Razão Social / Valor na aba SAIDAS."
        )

    nomes = [_normalizar_chave(v) for v in bruto.iloc[linha_cabecalho].tolist()]
    col_data = nomes.index("DATA")
    col_razao = nomes.index("RAZAO SOCIAL")
    col_valor = next(i for i, nome in enumerate(nomes) if nome.startswith("VALOR"))
    col_lancamento = next(
        (i for i, nome in enumerate(nomes) if nome == "LANCAMENTO"), None
    )
    col_obs = next((i for i, nome in enumerate(nomes) if "OBS" in nome), None)

    saidas: List[SaidaRGR] = []
    for indice in range(linha_cabecalho + 1, len(bruto)):
        data = pd.to_datetime(
            bruto.iat[indice, col_data], dayfirst=True, errors="coerce"
        )
        razao = _normalizar_espacos(bruto.iat[indice, col_razao])
        valor = _valor_planilha(bruto.iat[indice, col_valor])

        if pd.isna(data) or not razao or valor is None or valor >= 0:
            continue

        lancamento = (
            _normalizar_espacos(bruto.iat[indice, col_lancamento])
            if col_lancamento is not None
            else ""
        )
        observacao = (
            _normalizar_espacos(bruto.iat[indice, col_obs])
            if col_obs is not None
            else ""
        )
        saidas.append(
            SaidaRGR(
                data=data.normalize(),
                valor=round(float(valor), 2),
                razao_social=razao,
                lancamento=lancamento,
                observacao=observacao,
            )
        )

    if not saidas:
        raise ValueError("Nenhuma saída válida foi encontrada na aba SAIDAS.")

    return saidas


def _nome_ja_identificado(razao_social: str, historico: str) -> bool:
    """Compara nomes tolerando abreviações e sufixos societários."""
    nome = _normalizar_chave(razao_social)
    hist = _normalizar_chave(historico)
    if not nome:
        return True
    if nome in hist:
        return True

    ignorar = {
        "LTDA", "ME", "EPP", "EIRELI", "SA", "S", "DE", "DO", "DA", "DOS", "DAS",
        "COMERCIO", "SERVICOS",
    }
    tokens = [t for t in nome.split() if len(t) >= 3 and t not in ignorar]
    if not tokens:
        return False

    tokens_hist = set(hist.split())
    presentes = sum(1 for token in tokens if token in tokens_hist)
    minimo = max(1, min(2, (len(tokens) + 1) // 2))
    return presentes >= minimo


def _achar_saida(
    saidas: List[SaidaRGR], data: pd.Timestamp, valor: float
) -> SaidaRGR | None:
    for item in saidas:
        if (
            not item.usado
            and item.data.normalize() == data.normalize()
            and abs(float(item.valor) - float(valor)) <= 0.02
        ):
            return item
    return None


def _historico_saida_planilha(item: SaidaRGR) -> str:
    historico = f"Pago: {item.razao_social}"
    nome_generico = _normalizar_chave(item.razao_social) in {
        "ITAU", "DARF", "RECEITA FEDERAL"
    }
    if nome_generico and item.lancamento:
        historico += f" - {item.lancamento}"
    return historico


def processar_rgr(extrato_bytes: bytes, planilha_bytes: bytes):
    """Monta o Modelo Domínio da RGR e devolve diagnósticos de conferência."""
    extrato = ler_extrato_itau_rgr(extrato_bytes)
    saldos = ler_saldos_extrato_itau_rgr(extrato_bytes)
    boletos = ler_boletos_planilha_rgr(planilha_bytes)
    saidas_planilha = ler_saidas_planilha_rgr(planilha_bytes)

    saida = []
    diagnosticos_boletos = []
    saidas_completadas = 0
    saidas_extrato_sem_planilha = 0

    for _, linha in extrato.iterrows():
        data = pd.to_datetime(linha["DATA"]).normalize()
        valor = round(float(linha["VALOR"]), 2)
        historico = str(linha["HISTÓRICO"] or "")

        if valor > 0 and "BOLETOS RECEBIDOS" in historico.upper():
            indices = [
                i for i, boleto in enumerate(boletos)
                if not boleto.usado and boleto.pagamento.normalize() == data
            ]
            total_planilha = round(sum(boletos[i].valor for i in indices), 2)
            total_extrato = round(abs(valor), 2)
            bate = bool(indices) and abs(total_planilha - total_extrato) <= 0.02

            diagnosticos_boletos.append(
                {
                    "DATA": data,
                    "TOTAL_EXTRATO": total_extrato,
                    "TOTAL_PLANILHA": total_planilha,
                    "DIFERENÇA": round(total_planilha - total_extrato, 2),
                    "QTD_BOLETOS": len(indices),
                    "STATUS": "Batendo" if bate else "Divergente",
                }
            )

            if bate:
                for indice in indices:
                    boleto = boletos[indice]
                    boleto.usado = True
                    saida.append(
                        {
                            "DESCRIÇÃO": "BANCO ITAÚ",
                            "DATA": data,
                            "VALOR": boleto.valor,
                            "DÉBITO": CONTA_ITAU_RGR,
                            "CRÉDITO": "",
                            "HISTÓRICO": f"Recebido: {boleto.pagador}",
                        }
                    )
                continue

        if valor < 0:
            saida_planilha = _achar_saida(saidas_planilha, data, valor)
            if saida_planilha is None:
                saidas_extrato_sem_planilha += 1
            else:
                saida_planilha.usado = True
                if not _nome_ja_identificado(saida_planilha.razao_social, historico):
                    linha = linha.copy()
                    linha["HISTÓRICO"] = _historico_saida_planilha(saida_planilha)
                    saidas_completadas += 1

        saida.append(linha.to_dict())

    modelo = pd.DataFrame(saida, columns=COLUNAS_MODELO)
    modelo["DATA"] = pd.to_datetime(modelo["DATA"], dayfirst=True, errors="coerce")
    modelo["VALOR"] = pd.to_numeric(modelo["VALOR"], errors="coerce")
    modelo = (
        modelo.dropna(subset=["DATA", "VALOR"])
        .sort_values("DATA", kind="stable")
        .reset_index(drop=True)
    )

    diag_boletos = pd.DataFrame(diagnosticos_boletos)
    boletos_nao_usados = [boleto for boleto in boletos if not boleto.usado]
    saidas_nao_usadas = [item for item in saidas_planilha if not item.usado]

    df_boletos_nao_usados = pd.DataFrame(
        [
            {
                "DATA": b.pagamento,
                "PAGADOR": b.pagador,
                "VALOR": b.valor,
                "NF": b.nf,
            }
            for b in boletos_nao_usados
        ]
    )
    df_saidas_nao_usadas = pd.DataFrame(
        [
            {
                "DATA": s.data,
                "RAZÃO SOCIAL": s.razao_social,
                "LANÇAMENTO": s.lancamento,
                "VALOR": s.valor,
            }
            for s in saidas_nao_usadas
        ]
    )

    resumo = {
        "agregados": len(diagnosticos_boletos),
        "agregados_batendo": (
            int((diag_boletos["STATUS"] == "Batendo").sum())
            if not diag_boletos.empty
            else 0
        ),
        "agregados_divergentes": (
            int((diag_boletos["STATUS"] == "Divergente").sum())
            if not diag_boletos.empty
            else 0
        ),
        "boletos_individuais": len(boletos),
        "boletos_nao_usados": len(boletos_nao_usados),
        "saidas_planilha": len(saidas_planilha),
        "saidas_completadas": saidas_completadas,
        "saidas_planilha_nao_usadas": len(saidas_nao_usadas),
        "saidas_extrato_sem_planilha": saidas_extrato_sem_planilha,
        "total_extrato": round(float(extrato["VALOR"].sum()), 2),
        "total_modelo": round(float(modelo["VALOR"].sum()), 2),
        "saldo_inicial": saldos.get("saldo_inicial"),
        "saldo_final_informado": saldos.get("saldo_final_informado"),
    }

    if resumo["saldo_inicial"] is not None:
        resumo["saldo_final_calculado"] = round(
            float(resumo["saldo_inicial"]) + float(resumo["total_extrato"]), 2
        )
    else:
        resumo["saldo_final_calculado"] = None

    if (
        resumo["saldo_final_calculado"] is not None
        and resumo["saldo_final_informado"] is not None
    ):
        resumo["diferenca_saldo_extrato"] = round(
            float(resumo["saldo_final_informado"])
            - float(resumo["saldo_final_calculado"]),
            2,
        )
    else:
        resumo["diferenca_saldo_extrato"] = None

    return (
        modelo,
        diag_boletos,
        df_boletos_nao_usados,
        df_saidas_nao_usadas,
        resumo,
    )
