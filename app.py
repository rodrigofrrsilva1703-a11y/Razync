import streamlit as st
import pandas as pd
import openpyxl
import re
import calendar
import io
import os
from datetime import datetime
from pypdf import PdfReader

# Configuração da página Web
st.set_page_config(
    page_title="Plataforma Contábil Pro", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILIZAÇÃO CSS DARK MODE
# ==============================================================================
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 100%; }
        .stButton>button { width: 100% !important; border-radius: 6px !important; font-weight: 500 !important; padding: 0.45rem 1rem !important; border: 1px solid #30363d !important; background-color: #21262d !important; color: #c9d1d9 !important; transition: all 0.2s ease; }
        .stButton>button:hover { background-color: #30363d !important; border-color: #8b949e !important; color: #ffffff !important; }
        .metric-card { background-color: #161b22; border: 1px solid #30363d; padding: 14px; border-radius: 8px; text-align: center; }
        .metric-title { font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }
        .metric-value { font-size: 18px; color: #f0f6fc; font-weight: 700; }
        section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
        .tool-card { background-color: #161b22; border: 1px solid #30363d; padding: 24px 20px; border-radius: 8px; text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES DE PROCESSAMENTO
# ==============================================================================
def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val is None: return 0.0
    s = str(v_val).strip().replace('R$', '').replace('$', '').replace(' ', '')
    if not s or s.lower() == 'nan': return 0.0
    if '.' in s and ',' in s:
        last_dot, last_comma = s.rfind('.'), s.rfind(',')
        s = s.replace('.', '').replace(',', '.') if last_comma > last_dot else s.replace(',', '')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def processar_razao_dominio(file_bytes, filename):
    """Leitor de Razão robusto para qualquer formato da Domínio"""
    try:
        # Tenta ler como Excel
        df = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
    except:
        # Fallback: Tenta ler como CSV/Texto
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python', header=None, dtype=str)
        except: return None
    
    # Localiza o cabeçalho
    header_row_idx = 0
    for idx, row in df.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).upper()
        if ('DATA' in row_str or 'DT' in row_str) and ('VALOR' in row_str or 'DEBITO' in row_str or 'CREDITO' in row_str):
            header_row_idx = idx
            break
            
    df.columns = [str(v).strip().upper() for v in df.iloc[header_row_idx].values]
    df = df.iloc[header_row_idx+1:].copy()
        
    cols = list(df.columns)
    col_data = next((c for c in cols if any(p in c for p in ['DATA', 'DT'])), None)
    col_deb = next((c for c in cols if any(p in c for p in ['DEBITO', 'DÉBITO', 'SAIDA', 'DÉB'])), None)
    col_cred = next((c for c in cols if any(p in c for p in ['CREDITO', 'CRÉDITO', 'ENTRADA', 'CRÉD'])), None)
    col_val = next((c for c in cols if any(p in c for p in ['VALOR', 'VL'])), None)
    
    if not col_data: return None
    
    dados = []
    for _, row in df.iterrows():
        dt_raw = str(row[col_data]).strip() if pd.notna(row[col_data]) else ''
        match_dt = re.search(r'(\d{2}/\d{2}/\d{2,4})', dt_raw)
        if not match_dt: continue
        dt_fmt = match_dt.group(1)
        if len(dt_fmt.split('/')[-1]) == 2: dt_fmt = dt_fmt[:-2] + "20" + dt_fmt[-2:]
        
        v = 0.0
        if col_deb and col_cred:
            v_deb = limpar_valor_monetario(row[col_deb]) if pd.notna(row[col_deb]) else 0.0
            v_cred = limpar_valor_monetario(row[col_cred]) if pd.notna(row[col_cred]) else 0.0
            v = v_cred - v_deb
        elif col_val and pd.notna(row[col_val]):
            v = limpar_valor_monetario(row[col_val])
            
        if v != 0: dados.append({'DATA': dt_fmt, 'VALOR_RAZAO': v})
            
    if not dados: return None
    df_res = pd.DataFrame(dados)
    df_agregado = df_res.groupby('DATA')['VALOR_RAZAO'].sum().reset_index()
    df_agregado['DATA_DT'] = pd.to_datetime(df_agregado['DATA'], format='%d/%m/%Y')
    return df_agregado

# ==============================================================================
# ESTRUTURA DE NAVEGAÇÃO E TELA PRINCIPAL (Resumo)
# ==============================================================================
if 'pagina_ativa' not in st.session_state: st.session_state['pagina_ativa'] = 'home'

def mudar_pagina(p): st.session_state['pagina_ativa'] = p

st.sidebar.markdown("### Hub Contábil")
st.sidebar.markdown("---")
if st.sidebar.button("Início", use_container_width=True): mudar_pagina('home')
if st.sidebar.button("Conciliação com Razão", use_container_width=True): mudar_pagina('razao')

if st.session_state['pagina_ativa'] == 'home':
    st.title("Início")
    st.markdown("Selecione uma ferramenta no menu lateral.")
    
elif st.session_state['pagina_ativa'] == 'razao':
    st.title("Conciliação: Extrato x Razão da Domínio")
    
    c1, c2 = st.columns(2)
    arq_extrato = c1.file_uploader("Extrato Bancário", type=["pdf", "ofx", "csv", "xlsx", "xls"])
    arq_razao = c2.file_uploader("Razão Domínio", type=["csv", "xlsx", "xls"])

    if arq_extrato and arq_razao:
        # (Lógica de processamento de extrato simplificada aqui para brevidade)
        # ... [coloque as funções processar_ofx, processar_pdf etc. aqui] ...
        
        raz_bytes = arq_razao.getvalue()
        df_raz = processar_razao_dominio(raz_bytes, arq_razao.name)
        
        if df_raz is not None:
            st.success("Razão processado com sucesso!")
            st.dataframe(df_raz, use_container_width=True)
        else:
            st.error("Erro ao ler Razão. Dica: Salve o arquivo como .xlsx ou .csv no Excel.")
