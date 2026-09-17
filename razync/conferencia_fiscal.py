"""Conferência inteligente entre acumuladores fiscais e razão do Domínio."""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _texto(valor) -> str:
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    return re.sub(r"\s+", " ", str(valor)).strip()


def _numero(valor) -> float:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and not pd.isna(valor):
        return round(float(valor), 2)
    texto = _texto(valor).replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return 0.0


def _excel(conteudo: bytes, nome: str) -> pd.ExcelFile:
    try:
        return pd.ExcelFile(io.BytesIO(conteudo))
    except Exception as erro_original:
        if Path(nome).suffix.lower() != ".xls":
            raise ValueError(f"Não foi possível abrir {nome}: {erro_original}") from erro_original
        conversor = shutil.which("soffice") or shutil.which("libreoffice")
        if not conversor:
            raise ValueError(
                "O arquivo XLS veio com a estrutura interna danificada. Exporte novamente "
                "pelo Domínio em XLSX ou instale o LibreOffice no servidor."
            ) from erro_original
        pasta = tempfile.mkdtemp(prefix="razync_fiscal_")
        origem = Path(pasta) / "origem.xls"
        origem.write_bytes(conteudo)
        try:
            processo = subprocess.run(
                [conversor, "--headless", "--convert-to", "xlsx", "--outdir", pasta, str(origem)],
                capture_output=True, text=True, timeout=45, check=False,
                env={**os.environ, "HOME": pasta},
            )
            convertido = Path(pasta) / "origem.xlsx"
            if processo.returncode != 0 or not convertido.exists():
                raise ValueError("Não foi possível recuperar o XLS exportado pelo Domínio.")
            dados = convertido.read_bytes()
            return pd.ExcelFile(io.BytesIO(dados))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


def ler_acumuladores(conteudo: bytes, nome: str) -> tuple[pd.DataFrame, dict]:
    xls = _excel(conteudo, nome)
    bruto = pd.read_excel(xls, sheet_name=xls.sheet_names[0], header=None, dtype=object)
    periodo = {"inicio": None, "fim": None}
    tipo = ""
    registros = []
    for _, linha in bruto.iterrows():
        valores = linha.tolist()
        primeiro = _texto(valores[0] if valores else "").upper()
        if primeiro == "PERÍODO:":
            datas = [pd.to_datetime(v, errors="coerce") for v in valores]
            datas = [d for d in datas if pd.notna(d)]
            if datas:
                periodo = {"inicio": min(datas), "fim": max(datas)}
        if primeiro in {"ENTRADAS", "SAÍDAS", "SERVIÇOS"}:
            tipo = primeiro
            continue
        codigo = _texto(valores[0] if valores else "")
        conta = _texto(valores[49] if len(valores) > 49 else "")
        if not codigo.isdigit() or not conta or not re.fullmatch(r"\d+", conta):
            continue
        col_valor = 10 if tipo == "SERVIÇOS" else 13
        valor = _numero(valores[col_valor] if len(valores) > col_valor else 0)
        if abs(valor) < 0.005:
            continue
        descricao = next((_texto(v) for v in valores[1:12] if _texto(v)), "")
        registros.append({
            "TIPO": tipo, "ACUMULADOR": codigo, "DESCRIÇÃO": descricao,
            "CONTA": conta, "VALOR_FISCAL": valor,
        })
    if not registros:
        raise ValueError("Nenhum acumulador com conta contábil preenchida foi encontrado.")
    return pd.DataFrame(registros), periodo


def ler_razao(conteudo: bytes, nome: str) -> tuple[pd.DataFrame, dict]:
    xls = _excel(conteudo, nome)
    bruto = pd.read_excel(xls, sheet_name=xls.sheet_names[0], header=None, dtype=object)
    conta = ""
    descricao_conta = ""
    registros = []
    periodo = {"inicio": None, "fim": None}
    for _, linha in bruto.iterrows():
        valores = linha.tolist()
        primeiro = _texto(valores[0] if valores else "")
        if primeiro.upper() == "PERÍODO:":
            achado = re.findall(r"\d{2}/\d{2}/\d{4}", " ".join(_texto(v) for v in valores))
            if len(achado) >= 2:
                periodo = {
                    "inicio": pd.to_datetime(achado[0], dayfirst=True),
                    "fim": pd.to_datetime(achado[1], dayfirst=True),
                }
        if primeiro.upper() == "CONTA:":
            conta = re.sub(r"\D", "", _texto(valores[1] if len(valores) > 1 else ""))
            descricao_conta = _texto(valores[5] if len(valores) > 5 else "")
            continue
        data = pd.to_datetime(valores[0] if valores else None, dayfirst=True, errors="coerce")
        if not conta or pd.isna(data):
            continue
        debito = _numero(valores[8] if len(valores) > 8 else 0)
        credito = _numero(valores[9] if len(valores) > 9 else 0)
        if abs(debito) < 0.005 and abs(credito) < 0.005:
            continue
        registros.append({
            "CONTA": conta, "DESCRIÇÃO_CONTA": descricao_conta, "DATA": data.normalize(),
            "LOTE": _texto(valores[1] if len(valores) > 1 else ""),
            "HISTÓRICO": _texto(valores[2] if len(valores) > 2 else ""),
            "CONTRAPARTIDA": _texto(valores[7] if len(valores) > 7 else ""),
            "DÉBITO": debito, "CRÉDITO": credito,
        })
    if not registros:
        raise ValueError("Nenhum lançamento foi encontrado no razão.")
    return pd.DataFrame(registros), periodo


def _parece_fiscal(historico: str) -> bool:
    texto = _texto(historico).upper()
    if re.match(r"^(PAGO|PAGAMENTO|RECEBIDO|RECEBIMENTO|BAIXA)\b", texto):
        return False
    sinais = (" CF NF ", "COMPRA DE ", "VENDA DE ", "SERVIÇOS DE TERCEIROS", "SERVICOS DE TERCEIROS", "BENEFICIAMENTO")
    return any(sinal in f" {texto} " for sinal in sinais)


def conferir_fiscal_contabil(acumuladores: pd.DataFrame, razao: pd.DataFrame):
    resumos, detalhes = [], []
    agrupado = acumuladores.groupby(["CONTA", "TIPO"], as_index=False).agg(
        VALOR_FISCAL=("VALOR_FISCAL", "sum"),
        ACUMULADORES=("ACUMULADOR", lambda x: ", ".join(map(str, x))),
        DESCRIÇÕES=("DESCRIÇÃO", lambda x: " | ".join(map(str, x))),
    )
    for _, fiscal in agrupado.iterrows():
        conta = str(fiscal["CONTA"])
        lado = "CRÉDITO" if fiscal["TIPO"] == "SAÍDAS" else "DÉBITO"
        movimentos = razao[razao["CONTA"].astype(str).eq(conta)].copy()
        movimentos["VALOR_ANALISADO"] = pd.to_numeric(movimentos.get(lado), errors="coerce").fillna(0.0)
        movimentos = movimentos[movimentos["VALOR_ANALISADO"].abs() >= 0.005].copy()
        movimentos["COMPATÍVEL_FISCAL"] = movimentos["HISTÓRICO"].map(_parece_fiscal)
        valor_compativel = round(float(movimentos.loc[movimentos["COMPATÍVEL_FISCAL"], "VALOR_ANALISADO"].sum()), 2)
        valor_total = round(float(movimentos["VALOR_ANALISADO"].sum()), 2)
        valor_fiscal = round(float(fiscal["VALOR_FISCAL"]), 2)
        diferenca = round(valor_compativel - valor_fiscal, 2)
        extras = movimentos[~movimentos["COMPATÍVEL_FISCAL"]].copy()
        if abs(diferenca) <= 0.01:
            situacao = "CONFERE COM ALERTAS" if not extras.empty else "CONFERE"
        elif movimentos.empty:
            situacao = "AUSENTE NO CONTÁBIL"
        else:
            situacao = "REVISAR"
        resumos.append({
            "CONTA": conta, "TIPO": fiscal["TIPO"], "ACUMULADORES": fiscal["ACUMULADORES"],
            "VALOR FISCAL": valor_fiscal, "CONTÁBIL COMPATÍVEL": valor_compativel,
            "TOTAL DA CONTA": valor_total, "DIFERENÇA FISCAL": diferenca,
            "LANÇAMENTOS EXTRAS": len(extras), "SITUAÇÃO": situacao,
        })
        for _, mov in movimentos.iterrows():
            detalhes.append({
                "CONTA": conta, "DATA": mov["DATA"], "LOTE": mov["LOTE"],
                "HISTÓRICO": mov["HISTÓRICO"], "CONTRAPARTIDA": mov["CONTRAPARTIDA"],
                "VALOR": mov["VALOR_ANALISADO"],
                "CLASSIFICAÇÃO": "FISCAL COMPATÍVEL" if mov["COMPATÍVEL_FISCAL"] else "ALERTA - NÃO FISCAL",
            })
    return pd.DataFrame(resumos), pd.DataFrame(detalhes)


def processar_conferencia(acumuladores_bytes: bytes, acumuladores_nome: str, razao_bytes: bytes, razao_nome: str):
    acumuladores, periodo_fiscal = ler_acumuladores(acumuladores_bytes, acumuladores_nome)
    razao, periodo_razao = ler_razao(razao_bytes, razao_nome)
    resumo, detalhes = conferir_fiscal_contabil(acumuladores, razao)
    return {
        "resumo": resumo, "detalhes": detalhes, "acumuladores": acumuladores,
        "periodo_fiscal": periodo_fiscal, "periodo_razao": periodo_razao,
    }


def gerar_relatorio_excel(resultado: dict) -> bytes:
    """Gera o relatório da conferência em abas auditáveis."""
    wb = Workbook()
    wb.remove(wb.active)
    azul = PatternFill("solid", fgColor="123047")
    azul_claro = PatternFill("solid", fgColor="DCEAF4")
    amarelo = PatternFill("solid", fgColor="FFF1CC")
    vermelho = PatternFill("solid", fgColor="FADBD8")
    verde = PatternFill("solid", fgColor="DDF2E1")

    def adicionar_aba(nome: str, quadro: pd.DataFrame):
        ws = wb.create_sheet(nome)
        if quadro is None or quadro.empty:
            ws.append(["Nenhum registro encontrado"])
            return ws
        colunas = list(quadro.columns)
        ws.append(colunas)
        for celula in ws[1]:
            celula.fill = azul
            celula.font = Font(color="FFFFFF", bold=True)
            celula.alignment = Alignment(horizontal="center")
        for registro in quadro.itertuples(index=False, name=None):
            valores = []
            for valor in registro:
                if isinstance(valor, pd.Timestamp):
                    valor = valor.to_pydatetime()
                elif pd.isna(valor):
                    valor = ""
                valores.append(valor)
            ws.append(valores)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for indice, coluna in enumerate(colunas, start=1):
            valores = [str(ws.cell(linha, indice).value or "") for linha in range(1, ws.max_row + 1)]
            ws.column_dimensions[get_column_letter(indice)].width = min(max(len(v) for v in valores) + 2, 55)
            if any(chave in str(coluna).upper() for chave in ("VALOR", "TOTAL", "DIFERENÇA", "CONTÁBIL")):
                for linha in range(2, ws.max_row + 1):
                    ws.cell(linha, indice).number_format = 'R$ #,##0.00'
            if str(coluna).upper() == "DATA":
                for linha in range(2, ws.max_row + 1):
                    ws.cell(linha, indice).number_format = "dd/mm/yyyy"
        return ws

    resumo = resultado.get("resumo", pd.DataFrame()).copy()
    detalhes = resultado.get("detalhes", pd.DataFrame()).copy()
    acumuladores = resultado.get("acumuladores", pd.DataFrame()).copy()
    ws_resumo = adicionar_aba("Resumo por conta", resumo)
    if not resumo.empty and "SITUAÇÃO" in resumo.columns:
        coluna_situacao = list(resumo.columns).index("SITUAÇÃO") + 1
        for linha in range(2, ws_resumo.max_row + 1):
            situacao = str(ws_resumo.cell(linha, coluna_situacao).value or "")
            preenchimento = (
                verde if situacao == "CONFERE" else
                amarelo if situacao == "CONFERE COM ALERTAS" else vermelho
            )
            for celula in ws_resumo[linha]:
                celula.fill = preenchimento
    alertas = detalhes[
        detalhes.get("CLASSIFICAÇÃO", pd.Series(dtype=str)).eq("ALERTA - NÃO FISCAL")
    ].copy() if not detalhes.empty else pd.DataFrame()
    ws_alertas = adicionar_aba("Alertas", alertas)
    if ws_alertas.max_row > 1:
        for linha in range(2, ws_alertas.max_row + 1):
            for celula in ws_alertas[linha]:
                celula.fill = amarelo
    adicionar_aba("Todos os lançamentos", detalhes)
    adicionar_aba("Acumuladores considerados", acumuladores)
    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()
