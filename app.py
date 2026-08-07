import streamlit as st
import pandas as pd
import re
import io
import os
from datetime import datetime
from pypdf import PdfReader

# Configuração da página
st.set_page_config(page_title="Importador Domínio Pro", layout="wide", page_icon="🤖")

# --- CSS PARA DASHBOARD LIMPO ---
st.markdown("""
    <style>
        .metric-card { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #dee2e6; text-align: center; margin: 5px; }
        .label { font-size: 0.7rem; color: #6c757d; text-transform: uppercase; }
        .value { font-size: 0.95rem; font-weight: bold; color: #212529; }
    </style>
""", unsafe_allow_html=True)

def limpar_valor(v):
    if pd.isna(v) or v == '': return 0.0
    s = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except: return 0.0

def processar_planilha_universal(file_bytes, filename):
    # Tenta ler Excel ou CSV de forma inteligente
    try:
        if filename.endswith(('.xlsx', '.xls')): df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        else: df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python', dtype=str)
        
        # Procura colunas relevantes sem depender de índice fixo
        df.columns = [str(c).upper() for c in df.columns]
        c_dt = next((c for c in df.columns if 'DATA' in c or 'DT' in c), df.columns[0])
        c_vl = next((c for c in df.columns if 'VAL' in c or 'CRED' in c or 'DEB' in c), df.columns[-1])
        c_txt = [c for c in df.columns if c not in [c_dt, c_vl]]
        
        # Consolida histórico e converte
        df['HISTÓRICO'] = df[c_txt].astype(str).agg(' '.join, axis=1).str.replace('nan', '', regex=False).str.strip()
        df['DATA'] = pd.to_datetime(df[c_dt], errors='coerce').dt.strftime('%d/%m/%Y')
        df['VALOR'] = df[c_vl].apply(limpar_valor)
        
        return df[['DATA', 'HISTÓRICO', 'VALOR']]
    except: return pd.DataFrame()

# --- INTERFACE ---
st.title("🤖 Importador Inteligente")
arquivos = st.sidebar.file_uploader("Arraste extratos (XLSX, CSV, PDF)", accept_multiple_files=True)

if arquivos:
    for arquivo in arquivos:
        st.markdown(f"### 📑 {arquivo.name}")
        df = processar_planilha_universal(arquivo.getvalue(), arquivo.name)
        
        if not df.empty:
            # LIMPEZA UNIVERSAL: Remove linhas de saldo
            df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|DISPONÍVEL|SUBTOTAL', case=False, na=False)]
            df = df.dropna(subset=['DATA'])
            
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card"><div class="label">Registros</div><div class="value">{len(df)}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="label">Entradas</div><div class="value">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="label">Saídas</div><div class="value">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div></div>', unsafe_allow_html=True)
            
            st.dataframe(df, use_container_width=True)
            
            # Botão TXT (Domínio)
            txt = "\n".join([f"{r['DATA']};;{r['VALOR']:.2f};{str(r['HISTÓRICO']).replace(';', ' ')}" for _, r in df.iterrows()])
            st.download_button("🚀 Baixar .TXT p/ Domínio", txt, f"imp_{arquivo.name}.txt", use_container_width=True)
        else:
            st.warning("Não identifiquei colunas automáticas. O arquivo pode estar vazio ou com formato inválido.")
else:
    st.info("👈 Use a barra lateral para carregar seus arquivos.")
