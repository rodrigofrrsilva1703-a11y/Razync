"""Processamento específico da empresa 1211 - GZ Importadora e Exportadora.

Fonte principal: extrato Itaú (conta Domínio 508).
Fonte auxiliar: relatório 'Boletos baixados e liquidados'.
Os lançamentos agregados 'BOLETOS RECEBIDOS' são substituídos por boletos
individuais liquidados, com histórico 'Recebido: NOME DO PAGADOR'.
"""
from __future__ import annotations

import io
import re
from copy import copy
from dataclasses import dataclass
from typing import List

import pandas as pd
from pypdf import PdfReader


CONTA_ITAU_GZ = "508"
COLUNAS_MODELO = ["DESCRIÇÃO", "DATA", "VALOR", "DÉBITO", "CRÉDITO", "HISTÓRICO"]


@dataclass
class BoletoGZ:
    pagador: str
    vencimento: pd.Timestamp
    liquidacao: pd.Timestamp
    valor: float
    status: str
    usado: bool = False


def _normalizar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def _moeda_br(valor) -> float:
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


def _texto_pdf(conteudo: bytes) -> str:
    reader = PdfReader(io.BytesIO(conteudo), strict=False)
    return "\n".join((pagina.extract_text() or "") for pagina in reader.pages)


def _ocr_pdf(conteudo: bytes) -> str:
    import fitz
    import pytesseract
    from PIL import Image

    doc = fitz.open(stream=conteudo, filetype="pdf")
    textos = []
    for pagina in doc:
        pix = pagina.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), alpha=False)
        imagem = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        try:
            texto = pytesseract.image_to_string(imagem, lang="por")
        except Exception:
            texto = pytesseract.image_to_string(imagem)
        textos.append(texto)
    return "\n".join(textos)


def _limpar_historico_extrato(texto: str) -> str:
    texto = _normalizar_espacos(texto)
    texto = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", " ", texto)
    texto = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", " ", texto)
    return _normalizar_espacos(texto).strip(" -")


def ler_saldos_extrato_itau_gz(conteudo: bytes) -> dict:
    """Lê saldo inicial e saldo final impressos no extrato Itaú da GZ."""
    texto = _texto_pdf(conteudo)
    saldo_inicial = None
    saldo_final = None

    m_inicial = re.search(
        r"\b\d{2}/\d{2}/\d{4}\s+SALDO ANTERIOR\s+([\d.]+,\d{2})",
        texto, re.I
    )
    if m_inicial:
        saldo_inicial = _moeda_br(m_inicial.group(1))

    finais = re.findall(
        r"\b\d{2}/\d{2}/\d{4}\s+SALDO (?:EM CONTA CORRENTE|TOTAL DISPONÍVEL DIA)\s+([\d.]+,\d{2})",
        texto, re.I
    )
    if finais:
        saldo_final = _moeda_br(finais[-1])

    return {
        "saldo_inicial": round(float(saldo_inicial), 2) if saldo_inicial is not None else None,
        "saldo_final_informado": round(float(saldo_final), 2) if saldo_final is not None else None,
    }


def ler_extrato_itau_gz(conteudo: bytes) -> pd.DataFrame:
    """Extrai movimentos do extrato Itaú e ignora linhas de saldo."""
    texto = _texto_pdf(conteudo)
    if "GZ IMPORTADORA" not in texto.upper() and "0099343-5" not in texto:
        raise ValueError("O PDF enviado não parece ser o extrato Itaú da GZ.")

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
        if norm.startswith("SALDO ") or "SALDO TOTAL DISPONÍVEL" in norm or "SALDO EM CONTA" in norm:
            continue
        moedas = list(regex_moeda.finditer(conteudo_bloco))
        if not moedas:
            continue
        moeda = moedas[-1]
        valor = _moeda_br(moeda.group(1))
        historico = _limpar_historico_extrato(conteudo_bloco[:moeda.start()])
        if not historico or abs(valor) < 0.005:
            continue
        data = pd.to_datetime(bloco["data"], dayfirst=True, errors="coerce")
        if pd.isna(data):
            continue
        historico_sem_prefixo = re.sub(
            r"^(?:Pago|Recebido):\s*", "", historico, flags=re.I
        ).strip()
        prefixo = "Recebido: " if valor > 0 else "Pago: "
        registros.append({
            "DESCRIÇÃO": "BANCO ITAÚ",
            "DATA": data,
            "VALOR": round(valor, 2),
            "DÉBITO": CONTA_ITAU_GZ if valor > 0 else "",
            "CRÉDITO": CONTA_ITAU_GZ if valor < 0 else "",
            "HISTÓRICO": prefixo + historico_sem_prefixo,
        })
    if not registros:
        raise ValueError("Nenhum lançamento foi reconhecido no extrato Itaú da GZ.")
    return pd.DataFrame(registros, columns=COLUNAS_MODELO)


def _extrair_boletos_texto_gz(texto: str) -> List[BoletoGZ]:
    """Extrai boletos de layouts textuais do Itaú tolerando quebras de linha/colunas."""
    texto = (texto or "").replace("|", " ")
    linhas = [_normalizar_espacos(linha) for linha in texto.splitlines()]
    linhas = [linha for linha in linhas if linha]

    # Alguns PDFs quebram uma mesma linha da tabela em 2 ou 3 linhas. Criamos
    # janelas curtas para permitir a leitura sem depender de uma disposição fixa.
    candidatos = []
    vistos_candidatos = set()
    for i, linha in enumerate(linhas):
        for tamanho in (1, 2, 3):
            if i + tamanho > len(linhas):
                continue
            candidato = _normalizar_espacos(" ".join(linhas[i:i + tamanho]))
            chave = candidato.casefold()
            if chave not in vistos_candidatos:
                vistos_candidatos.add(chave)
                candidatos.append(candidato)

    boletos: List[BoletoGZ] = []
    vistos = set()
    regex_data = re.compile(r"\b\d{2}/\d{2}/(?:\d{2}|\d{4})\b")
    regex_moeda = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)")

    for candidato in candidatos:
        norm = candidato.upper()
        if not any(chave in norm for chave in ("LIQUIDAD", "LIQUIDAÇ", "LIQUIDAC", "BAIXAD")):
            continue

        datas = list(regex_data.finditer(candidato))
        if len(datas) < 2:
            continue

        # O relatório histórico usado pela GZ tem vencimento e liquidação.
        # Aceitamos ano com 2 ou 4 dígitos.
        vencimento_txt = datas[0].group(0)
        liquidacao_txt = datas[1].group(0)
        formato_ano_curto = len(liquidacao_txt.split("/")[-1]) == 2
        vencimento = pd.to_datetime(
            vencimento_txt, dayfirst=True, errors="coerce",
            format="%d/%m/%y" if len(vencimento_txt.split("/")[-1]) == 2 else None,
        )
        liquidacao = pd.to_datetime(
            liquidacao_txt, dayfirst=True, errors="coerce",
            format="%d/%m/%y" if formato_ano_curto else None,
        )
        if pd.isna(vencimento) or pd.isna(liquidacao):
            continue

        # Valor: preferimos o primeiro valor monetário entre as duas datas e o
        # status; se não houver, usamos o primeiro valor depois da 2ª data.
        inicio_valor = datas[0].end()
        fim_busca = len(candidato)
        status_match = re.search(
            r"\b(?:Liquidado|Liquida[cç][aã]o|Baixado)\b",
            candidato, flags=re.I,
        )
        if status_match:
            fim_busca = status_match.start()
        trecho_valor = candidato[inicio_valor:fim_busca]
        moedas = list(regex_moeda.finditer(trecho_valor))
        if not moedas:
            moedas = list(regex_moeda.finditer(candidato[datas[1].end():fim_busca]))
        if not moedas:
            continue
        valor = _moeda_br(moedas[0].group(1))
        if valor <= 0:
            continue

        # Nome do pagador normalmente vem antes do primeiro vencimento.
        pagador = candidato[:datas[0].start()].strip(" -")
        pagador = re.sub(
            r"^(?:\d+\s+){1,5}", "", pagador
        ).strip()
        pagador = re.sub(
            r"^(?:Pagador|Sacado|Cliente)\s*[:\-]\s*",
            "", pagador, flags=re.I,
        ).strip(" -")
        if not pagador:
            continue

        status = "Liquidado" if "LIQUID" in norm else "Baixado"
        chave = (
            _normalizar_espacos(pagador).casefold(),
            vencimento.normalize(),
            liquidacao.normalize(),
            round(valor, 2),
            status,
        )
        if chave in vistos:
            continue
        vistos.add(chave)
        boletos.append(BoletoGZ(
            _normalizar_espacos(pagador),
            vencimento,
            liquidacao,
            round(valor, 2),
            status,
        ))
    return boletos


def ler_boletos_liquidados_gz(conteudo: bytes) -> List[BoletoGZ]:
    """Lê o relatório de boletos em layouts Itaú diferentes, com OCR de fallback."""
    texto = _texto_pdf(conteudo)
    boletos = _extrair_boletos_texto_gz(texto)

    # Não usamos apenas o tamanho do texto como critério: existem PDFs com
    # bastante cabeçalho textual, mas a tabela principal vem como imagem.
    if not boletos:
        try:
            texto_ocr = _ocr_pdf(conteudo)
        except Exception:
            texto_ocr = ""
        if texto_ocr.strip():
            boletos = _extrair_boletos_texto_gz(texto_ocr)

    if not boletos:
        raise ValueError(
            "Nenhum boleto foi reconhecido no relatório auxiliar. "
            "O Modelo Domínio ainda pode ser gerado mantendo os totais "
            "'BOLETOS RECEBIDOS' do extrato."
        )
    return boletos

def _subset_exato(indices: list[int], boletos: List[BoletoGZ], alvo: float) -> list[int]:
    alvo_cent = int(round(alvo * 100))
    dp = {0: []}
    for indice in indices:
        valor = int(round(boletos[indice].valor * 100))
        for soma, escolhidos in list(dp.items())[::-1]:
            nova = soma + valor
            if nova > alvo_cent or nova in dp:
                continue
            dp[nova] = escolhidos + [indice]
            if nova == alvo_cent:
                return dp[nova]
    return []


def processar_gz(extrato_bytes: bytes, boletos_bytes: bytes | None = None):
    """Substitui agregados por boletos quando possível, sem bloquear a geração."""
    extrato = ler_extrato_itau_gz(extrato_bytes)
    saldos_extrato = ler_saldos_extrato_itau_gz(extrato_bytes)

    aviso_boletos = None
    boletos: List[BoletoGZ] = []
    if boletos_bytes:
        try:
            boletos = ler_boletos_liquidados_gz(boletos_bytes)
        except Exception as exc:
            aviso_boletos = str(exc)
    else:
        aviso_boletos = (
            "Relatório auxiliar de boletos não enviado. "
            "Os totais 'BOLETOS RECEBIDOS' foram preservados."
        )

    data_ini = extrato["DATA"].min().normalize()
    data_fim = extrato["DATA"].max().normalize()

    saida = []
    diagnosticos = []
    for _, linha in extrato.iterrows():
        historico = str(linha["HISTÓRICO"] or "")
        if "BOLETOS RECEBIDOS" not in historico.upper():
            saida.append(linha.to_dict())
            continue

        data_extrato = pd.to_datetime(linha["DATA"]).normalize()
        alvo = abs(float(linha["VALOR"]))

        if not boletos:
            diagnosticos.append({
                "DATA_EXTRATO": data_extrato,
                "TOTAL_EXTRATO": alvo,
                "TOTAL_BOLETOS": 0.0,
                "DIFERENÇA": 0.0,
                "QTD_BOLETOS": 0,
                "STATUS": "Sem detalhamento",
            })
            saida.append(linha.to_dict())
            continue

        elegiveis = [
            i for i, boleto in enumerate(boletos)
            if not boleto.usado
            and boleto.status.lower() == "liquidado"
            and data_ini <= boleto.liquidacao.normalize() <= data_extrato
        ]
        soma_elegivel = round(sum(boletos[i].valor for i in elegiveis), 2)
        escolhidos = (
            elegiveis
            if abs(soma_elegivel - alvo) <= 0.02
            else _subset_exato(elegiveis, boletos, alvo)
        )
        soma_escolhida = round(sum(boletos[i].valor for i in escolhidos), 2)
        bate = bool(escolhidos) and abs(soma_escolhida - alvo) <= 0.02

        diagnosticos.append({
            "DATA_EXTRATO": data_extrato,
            "TOTAL_EXTRATO": alvo,
            "TOTAL_BOLETOS": soma_escolhida if escolhidos else soma_elegivel,
            "DIFERENÇA": round(
                (soma_escolhida if escolhidos else soma_elegivel) - alvo, 2
            ),
            "QTD_BOLETOS": len(escolhidos),
            "STATUS": "Batendo" if bate else "Divergente",
        })

        if not bate:
            saida.append(linha.to_dict())
            continue

        for indice in escolhidos:
            boleto = boletos[indice]
            boleto.usado = True
            saida.append({
                "DESCRIÇÃO": "BANCO ITAÚ",
                "DATA": boleto.liquidacao,
                "VALOR": boleto.valor,
                "DÉBITO": CONTA_ITAU_GZ,
                "CRÉDITO": "",
                "HISTÓRICO": f"Recebido: {boleto.pagador}",
            })

    df_saida = pd.DataFrame(saida, columns=COLUNAS_MODELO)
    df_saida["DATA"] = pd.to_datetime(
        df_saida["DATA"], dayfirst=True, errors="coerce"
    )
    df_saida = (
        df_saida.dropna(subset=["DATA"])
        .sort_values("DATA", kind="stable")
        .reset_index(drop=True)
    )

    nao_usados = [
        boleto for boleto in boletos
        if not boleto.usado
        and boleto.status.lower() == "liquidado"
        and data_ini <= boleto.liquidacao.normalize() <= data_fim
    ]
    df_nao_usados = pd.DataFrame([
        {
            "DATA": b.liquidacao,
            "PAGADOR": b.pagador,
            "VALOR": b.valor,
            "STATUS": b.status,
        }
        for b in nao_usados
    ])
    df_diag = pd.DataFrame(diagnosticos)
    resumo = {
        "periodo_inicio": data_ini,
        "periodo_fim": data_fim,
        "agregados": len(diagnosticos),
        "agregados_batendo": (
            int((df_diag["STATUS"] == "Batendo").sum())
            if not df_diag.empty else 0
        ),
        "agregados_divergentes": (
            int((df_diag["STATUS"] == "Divergente").sum())
            if not df_diag.empty else 0
        ),
        "agregados_sem_detalhamento": (
            int((df_diag["STATUS"] == "Sem detalhamento").sum())
            if not df_diag.empty else 0
        ),
        "boletos_lidos": len(boletos),
        "boletos_liquidados": sum(
            1 for b in boletos if b.status.lower() == "liquidado"
        ),
        "boletos_nao_usados": len(nao_usados),
        "aviso_boletos": aviso_boletos,
        "total_extrato": round(float(extrato["VALOR"].sum()), 2),
        "total_modelo": round(float(df_saida["VALOR"].sum()), 2),
        "saldo_inicial": saldos_extrato.get("saldo_inicial"),
        "saldo_final_informado": saldos_extrato.get("saldo_final_informado"),
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
    return df_saida, df_diag, df_nao_usados, resumo

def gerar_modelo_dominio_gz(df: pd.DataFrame, modelo_bytes: bytes) -> bytes:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(modelo_bytes))
    template = None
    cabecalho = None
    mapa = None
    normalizar = lambda v: re.sub(r"[^A-Z0-9]", "", str(v or "").upper().translate(str.maketrans("ÁÀÃÂÉÊÍÓÔÕÚÇ", "AAAAEEIOOOUC")))
    esperadas = [normalizar(c) for c in COLUNAS_MODELO]
    for ws in wb.worksheets:
        for linha in range(1, min(ws.max_row, 25) + 1):
            mapa_temp = {normalizar(ws.cell(linha, c).value): c for c in range(1, ws.max_column + 1) if ws.cell(linha, c).value is not None}
            if all(nome in mapa_temp for nome in esperadas):
                template, cabecalho, mapa = ws, linha, mapa_temp
                break
        if template is not None:
            break
    if template is None:
        raise ValueError("Cabeçalho do Modelo Domínio não localizado.")

    linha_modelo = cabecalho + 1
    estilos = {}
    for c in range(1, template.max_column + 1):
        cel = template.cell(linha_modelo, c)
        estilos[c] = (copy(cel.font), copy(cel.fill), copy(cel.border), copy(cel.alignment), cel.number_format, copy(cel.protection))
    for r in range(cabecalho + 1, template.max_row + 1):
        for c in range(1, template.max_column + 1):
            template.cell(r, c).value = None

    for r, registro in enumerate(df[COLUNAS_MODELO].to_dict("records"), start=linha_modelo):
        for nome in COLUNAS_MODELO:
            c = mapa[normalizar(nome)]
            valor = registro.get(nome, "")
            if pd.isna(valor):
                valor = ""
            if nome == "DATA" and valor not in ("", None):
                valor = pd.to_datetime(valor).to_pydatetime()
            elif nome in {"DÉBITO", "CRÉDITO"} and str(valor).isdigit():
                valor = int(valor)
            elif nome == "VALOR":
                valor = float(valor)
            cel = template.cell(r, c)
            cel.value = valor
            fonte, fill, border, alinhamento, formato, protecao = estilos[c]
            cel.font, cel.fill, cel.border, cel.alignment = copy(fonte), copy(fill), copy(border), copy(alinhamento)
            cel.number_format, cel.protection = formato, copy(protecao)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
