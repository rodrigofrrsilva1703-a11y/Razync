"""Conferência dos impostos da Receita/DCTFWeb com o balancete contábil."""

from __future__ import annotations

import io
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from pypdf import PdfReader


IMPOSTOS = {
    "INSS / Previdenciários": ("INSS", "PREVIDENCIARIA", "PREVIDENCIARIO", "CONTRIBUICAO PREVIDENCIARIA"),
    "IRRF": ("IRRF", "IMPOSTO DE RENDA RETIDO"),
    "PIS/PASEP": ("PIS", "PASEP"),
    "COFINS": ("COFINS",),
    "CSLL": ("CSLL", "CONTRIBUICAO SOCIAL SOBRE O LUCRO"),
    "IRPJ": ("IRPJ", "IMPOSTO DE RENDA PESSOA JURIDICA"),
    "CPRB": ("CPRB", "RECEITA BRUTA PREVIDENCIARIA"),
}


def _rotulo(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", texto.upper()).strip()


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and not pd.isna(valor):
        return round(float(valor), 2)
    texto = str(valor or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return None
    return round(-numero if negativo else numero, 2)


def _linhas_documento(conteudo: bytes, nome: str) -> list[list]:
    extensao = Path(nome).suffix.lower()
    if extensao == ".pdf":
        leitor = PdfReader(io.BytesIO(conteudo))
        return [[linha] for pagina in leitor.pages for linha in (pagina.extract_text() or "").splitlines()]
    if extensao == ".csv":
        quadro = pd.read_csv(io.BytesIO(conteudo), header=None, sep=None, engine="python", dtype=object)
        return quadro.fillna("").values.tolist()
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    linhas: list[list] = []
    for aba in xls.sheet_names:
        quadro = pd.read_excel(xls, sheet_name=aba, header=None, dtype=object)
        linhas.extend(quadro.fillna("").values.tolist())
    return linhas


def _valor_da_linha(linha: list) -> float | None:
    numeros = [_numero(valor) for valor in linha]
    numeros = [valor for valor in numeros if valor is not None]
    if numeros:
        return abs(numeros[-1])
    texto = " ".join(str(valor) for valor in linha)
    encontrados = re.findall(r"(?:R\$\s*)?-?\d{1,3}(?:\.\d{3})*,\d{2}", texto)
    return abs(_numero(encontrados[-1]) or 0) if encontrados else None


def extrair_impostos(conteudo: bytes, nome: str) -> dict[str, float]:
    totais = {imposto: 0.0 for imposto in IMPOSTOS}
    encontrados = {imposto: False for imposto in IMPOSTOS}
    for linha in _linhas_documento(conteudo, nome):
        texto = _rotulo(" ".join(str(valor) for valor in linha))
        valor = _valor_da_linha(linha)
        if valor is None:
            continue
        for imposto, aliases in IMPOSTOS.items():
            if any(alias in texto for alias in aliases):
                totais[imposto] += valor
                encontrados[imposto] = True
                break
    return {imposto: round(valor, 2) for imposto, valor in totais.items() if encontrados[imposto]}


def processar_conferencia_impostos(
    receita: bytes, nome_receita: str, balancete: bytes, nome_balancete: str,
) -> pd.DataFrame:
    valores_receita = extrair_impostos(receita, nome_receita)
    valores_contabeis = extrair_impostos(balancete, nome_balancete)
    impostos = sorted(set(valores_receita) | set(valores_contabeis))
    if not impostos:
        raise ValueError(
            "Não encontrei linhas de impostos nos arquivos. Envie o relatório detalhado "
            "da DCTFWeb/Receita e um balancete com as descrições das contas."
        )
    registros = []
    for imposto in impostos:
        receita_valor = valores_receita.get(imposto, 0.0)
        contabil_valor = valores_contabeis.get(imposto, 0.0)
        diferenca = round(contabil_valor - receita_valor, 2)
        registros.append({
            "IMPOSTO": imposto,
            "RECEITA / DCTFWEB": receita_valor,
            "BALANCETE": contabil_valor,
            "DIFERENÇA": diferenca,
            "SITUAÇÃO": "CONFERE" if abs(diferenca) <= 0.01 else "REVISAR",
        })
    return pd.DataFrame(registros)


def gerar_relatorio_impostos(resultado: pd.DataFrame, empresa: str, competencia: date) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Conferência de Impostos"
    ws.append(["EMPRESA", empresa])
    ws.append(["COMPETÊNCIA", competencia.strftime("%m/%Y")])
    ws.append([])
    ws.append(resultado.columns.tolist())
    for celula in ws[4]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor="147DA4")
    for linha in resultado.itertuples(index=False, name=None):
        ws.append(list(linha))
    for coluna in ("B", "C", "D"):
        for celula in ws[coluna][4:]:
            celula.number_format = 'R$ #,##0.00'
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 14
    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()


def renderizar_conferencia_impostos(prefixo: str, empresa: str) -> None:
    import streamlit as st
    from razync.certificado_digital import buscar_certificado, carregar_certificado

    chave = re.sub(r"[^a-z0-9_]+", "_", str(prefixo).lower()).strip("_")
    st.markdown("### Conferência de Impostos")
    st.caption(
        "Compare os débitos informados na Receita/DCTFWeb com os saldos do balancete "
        "da mesma competência."
    )
    try:
        certificado = buscar_certificado(prefixo)
    except Exception:
        certificado = None
    if certificado:
        st.success(
            f"Certificado A1 cadastrado e selecionado automaticamente · "
            f"CNPJ {certificado.get('cnpj') or 'não informado'} · "
            f"validade {pd.to_datetime(certificado.get('validade_fim')).strftime('%d/%m/%Y')}"
        )
        if st.button(
            "Validar certificado cadastrado",
            key=f"impostos_{chave}_validar_certificado",
            use_container_width=True,
        ):
            try:
                _, _, metadados = carregar_certificado(prefixo)
                st.success(
                    "Certificado validado com sucesso. Titular: "
                    + str(metadados.get("titular") or "não informado")
                )
            except Exception as erro:
                st.error(f"Não foi possível usar o certificado cadastrado: {erro}")

        serpro = st.secrets.get("serpro", {})
        chave_serpro = str(
            serpro.get("consumer_key", "")
            or st.secrets.get("SERPRO_CONSUMER_KEY", "")
        )
        segredo_serpro = str(
            serpro.get("consumer_secret", "")
            or st.secrets.get("SERPRO_CONSUMER_SECRET", "")
        )
        if chave_serpro and segredo_serpro:
            st.info(
                "Integra Contador configurado. O certificado A1 será usado nas "
                "consultas automáticas quando o serviço DCTFWeb for acionado."
            )
        else:
            st.warning(
                "O certificado está pronto, mas a consulta automática oficial ainda "
                "precisa das chaves do contrato Integra Contador/Serpro. Enquanto isso, "
                "envie abaixo o relatório exportado da DCTFWeb."
            )
            st.link_button(
                "Conhecer o Integra Contador",
                "https://loja.serpro.gov.br/integra-contador",
                use_container_width=True,
            )
    else:
        st.info(
            "Cadastre o certificado A1 no botão flutuante. Para a consulta automática "
            "também serão necessárias as chaves do Integra Contador/Serpro."
        )

    competencia = st.date_input(
        "Competência", value=date.today().replace(day=1),
        key=f"impostos_{chave}_competencia",
    )
    col_receita, col_balancete = st.columns(2)
    with col_receita:
        arquivo_receita = st.file_uploader(
            "Relatório da Receita / DCTFWeb", type=["pdf", "xls", "xlsx", "csv"],
            key=f"impostos_{chave}_receita",
        )
    with col_balancete:
        arquivo_balancete = st.file_uploader(
            "Balancete contábil", type=["xls", "xlsx", "csv"],
            key=f"impostos_{chave}_balancete",
        )
    if arquivo_receita is None or arquivo_balancete is None:
        st.info("Envie os dois arquivos para iniciar a conferência automática.")
        return
    try:
        resultado = processar_conferencia_impostos(
            arquivo_receita.getvalue(), arquivo_receita.name,
            arquivo_balancete.getvalue(), arquivo_balancete.name,
        )
    except Exception as erro:
        st.error(f"Não foi possível concluir a conferência: {erro}")
        return

    conferidos = int(resultado["SITUAÇÃO"].eq("CONFERE").sum())
    revisar = int(resultado["SITUAÇÃO"].eq("REVISAR").sum())
    total_diferenca = float(resultado["DIFERENÇA"].abs().sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Impostos analisados", len(resultado))
    m2.metric("Conferidos", conferidos)
    m3.metric("Diferença total", f"R$ {total_diferenca:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    if revisar:
        st.error(f"{revisar} imposto(s) precisam de revisão.")
    else:
        st.success("Os impostos encontrados conferem com o balancete.")
    st.dataframe(
        resultado, use_container_width=True, hide_index=True,
        column_config={
            "RECEITA / DCTFWEB": st.column_config.NumberColumn(format="R$ %.2f"),
            "BALANCETE": st.column_config.NumberColumn(format="R$ %.2f"),
            "DIFERENÇA": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )
    st.download_button(
        "Baixar relatório da conferência de impostos",
        data=gerar_relatorio_impostos(resultado, empresa, competencia),
        file_name=f"CONFERENCIA_IMPOSTOS_{competencia.strftime('%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True, key=f"impostos_{chave}_download",
    )
