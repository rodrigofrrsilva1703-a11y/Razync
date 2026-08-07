import streamlit as st
import pandas as pd
import re
import io
import os
from pypdf import PdfReader

# Configuração da página
st.set_page_config(page_title="Importador Domínio Pro", page_icon="🤖", layout="wide")

# CSS para cards compactos
st.markdown("""
    <style>
        .card { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #dee2e6; text-align: center; }
        .label { font-size: 0.70rem; color: #6c757d; text-transform: uppercase; }
        .value { font-size: 0.95rem; font-weight: bold; color: #212529; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE LEITURA ---
def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val == '': return 0.0
    s = str(v_val).strip().replace('R$', '').replace('$', '').replace(' ', '')
    if '.' in s and ',' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def ler_pdf_bruto(file_bytes):
    """Leitura de PDF ultra tolerante: pega todo o texto da página."""
    pdf = PdfReader(io.BytesIO(file_bytes))
    texto_completo = ""
    for pag in pdf.pages:
        texto_completo += pag.extract_text() + "\n"
    
    # Tenta encontrar linhas com Data + Historico + Valor
    linhas = texto_completo.split('\n')
    dados = []
    # Regex para: Data (00/00/0000) + Historico + Valor (-00,00)
    regex = r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})"
    
    for linha in linhas:
        match = re.search(regex, linha)
        if match:
            dados.append({
                'DATA': match.group(1),
                'HISTÓRICO': match.group(2).strip(),
                'VALOR': limpar_valor_monetario(match.group(3))
            })
    return pd.DataFrame(dados)

# --- INTERFACE ---
st.sidebar.title("⚡ Painel de Controle")
arquivos = st.sidebar.file_uploader("Arraste os extratos", type=["pdf", "ofx", "csv", "xlsx", "xls"], accept_multiple_files=True)

st.title("🤖 Importador Inteligente Domínio")

if arquivos:
    for arquivo in arquivos:
        st.write(f"### Arquivo: {arquivo.name}")
        
        # Leitura Inteligente
        if arquivo.name.lower().endswith('.pdf'):
            df = ler_pdf_bruto(arquivo.getvalue())
        else:
            # Tente ler planilha/ofx conforme seu original
            df = pd.DataFrame() # Aqui entre com sua lógica de CSV/OFX
        
        if not df.empty:
            # LIMPEZA OBRIGATÓRIA
            df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL', case=False, na=False)]
            
            # EXIBIÇÃO
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="card"><div class="label">Registros</div><div class="value">{len(df)}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="card"><div class="label">Entradas</div><div class="value">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="card"><div class="label">Saídas</div><div class="value">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div></div>', unsafe_allow_html=True)
            
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Não conseguimos ler os dados deste PDF. Verifique se ele é uma imagem ou se o formato é muito específico.")
