import streamlit as st
import pandas as pd
import re
import io
import os
from datetime import datetime
from pypdf import PdfReader

st.set_page_config(page_title="Importador Domínio Pro", layout="wide", page_icon="🤖")

# --- CSS LIMPO ---
st.markdown("""
    <style>
        .metric-card { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #dee2e6; text-align: center; }
        .label { font-size: 0.7rem; color: #6c757d; text-transform: uppercase; }
        .value { font-size: 1.0rem; font-weight: bold; color: #111; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ORIGINAIS DE LEITURA (PRESERVADAS) ---
def limpar_valor(v):
    if pd.isna(v) or v == '': return 0.0
    s = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except: return 0.0

def processar_pdf_generico(caminho):
    reader = PdfReader(caminho, strict=False)
    lancamentos = []
    for pagina in reader.pages:
        texto = pagina.extract_text()
        if not texto: continue
        for linha in texto.split('\n'):
            # Regex que busca Data + Historico + Valor
            match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
            if match:
                lancamentos.append({
                    'DATA': match.group(1),
                    'HISTÓRICO': match.group(2).strip(),
                    'VALOR': limpar_valor(match.group(3))
                })
    return pd.DataFrame(lancamentos)

# --- INTERFACE ---
st.sidebar.title("📥 Importador")
arquivos = st.sidebar.file_uploader("Arraste extratos", accept_multiple_files=True)

st.title("🤖 Importador Inteligente")

if arquivos:
    for arquivo in arquivos:
        st.markdown("---")
        st.subheader(f"Arquivo: {arquivo.name}")
        
        # Leitura baseada no seu código original
        caminho_temp = f"temp_{arquivo.name}"
        with open(caminho_temp, "wb") as f: f.write(arquivo.getvalue())
        
        df = processar_pdf_generico(caminho_temp)
        if os.path.exists(caminho_temp): os.remove(caminho_temp)
        
        # --- LIMPEZA AGRESSIVA DE SALDOS ---
        if not df.empty:
            df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|DISPONÍVEL|SUBTOTAL', case=False, na=False)]
            df['HISTÓRICO'] = df['HISTÓRICO'].str.replace(r'\s+', ' ', regex=True).str.strip()
            
            # --- CARDS COMPACTOS ---
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card"><div class="label">Registros</div><div class="value">{len(df)}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="label">Entradas</div><div class="value">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="label">Saídas</div><div class="value">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card"><div class="label">Saldo Líquido</div><div class="value">R$ {df["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            
            st.write("")
            st.dataframe(df, use_container_width=True)
            
            # Botão TXT
            txt = "\n".join([f"{r['DATA']};;{r['VALOR']:.2f};{r['HISTÓRICO']}" for _, r in df.iterrows()])
            st.download_button("🚀 Gerar .TXT", txt, file_name=f"import_{arquivo.name}.txt")
        else:
            st.warning("Não foi possível extrair lançamentos. O layout deste extrato está muito diferente.")
