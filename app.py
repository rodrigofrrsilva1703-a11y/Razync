import streamlit as st
import pandas as pd
import re
import io
import os
from datetime import datetime
from pypdf import PdfReader

# Configuração da página
st.set_page_config(page_title="Importador Domínio Pro", page_icon="🤖", layout="wide")

# --- CSS PARA CARDS COMPACTOS ---
st.markdown("""
    <style>
        .card { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #dee2e6; text-align: center; }
        .label { font-size: 0.75rem; color: #6c757d; text-transform: uppercase; margin-bottom: 5px; }
        .value { font-size: 1.0rem; font-weight: bold; color: #212529; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO (MANTIDAS DO SEU ORIGINAL) ---
def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val is None: return 0.0
    if isinstance(v_val, (int, float)): return float(v_val)
    s = str(v_val).strip().replace('R$', '').replace('$', '').replace(' ', '')
    if not s or s.lower() == 'nan': return 0.0
    if '.' in s and ',' in s:
        last_dot = s.rfind('.'); last_comma = s.rfind(',')
        s = s.replace('.', '').replace(',', '.') if last_comma > last_dot else s.replace(',', '')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def processar_ofx(file_bytes, filename):
    texto = file_bytes.decode('utf-8', errors='ignore')
    transacoes = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', texto, re.DOTALL)
    lancamentos = []
    for t in transacoes:
        dt = re.search(r'<DTPOSTED>(\d{8})', t)
        val = re.search(r'<TRNAMT>([-+]?[\d.]+)', t)
        memo = re.search(r'<MEMO>(.*?)(?:<|$)', t)
        if dt and val:
            lancamentos.append({
                'DATA': f"{dt.group(1)[6:8]}/{dt.group(1)[4:6]}/{dt.group(1)[:4]}",
                'VALOR': limpar_valor_monetario(val.group(1)),
                'HISTÓRICO': memo.group(1).strip() if memo else "TRANSACAO OFX"
            })
    return lancamentos

# (Demais funções de PDF e Planilha permanecem conforme sua lógica original, apenas retornando o dict padrão)
# ... [Inclua aqui suas funções processar_planilha_universal, processar_arquivo_pdf, etc] ...

def gerar_txt_dominio(df):
    return "\n".join([f"{r['DATA']};;{r['VALOR']:.2f};{str(r['HISTÓRICO']).replace(';', ' ')}" for _, r in df.iterrows()])

# --- INTERFACE CORRIGIDA E COMPACTA ---
st.sidebar.title("⚡ Painel de Controle")
arquivos = st.sidebar.file_uploader("Arraste os extratos", accept_multiple_files=True)

st.title("🤖 Importador Inteligente Domínio")

if arquivos:
    abas = st.tabs([a.name for a in arquivos])
    for idx, arquivo in enumerate(arquivos):
        with abas[idx]:
            # [AQUI VOCÊ CHAMA SEUS PROCESSADORES DE ARQUIVO]
            # lancamentos = processar_arquivo(...)
            
            df = pd.DataFrame(lancamentos)
            
            # --- LIMPEZA UNIVERSAL E AGRESSIVA ---
            # 1. Remove saldos e linhas irrelevantes
            df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|DISPONÍVEL|SUBTOTAL', case=False, na=False)]
            # 2. Consolida histórico (remove quebras de linha e espaços extras)
            df['HISTÓRICO'] = df['HISTÓRICO'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            
            # --- CARDS COMPACTOS ---
            saldo_liquido = df['VALOR'].sum()
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="card"><div class="label">Registros</div><div class="value">{len(df)}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="card"><div class="label">Entradas</div><div class="value">R$ {df[df["VALOR"]>0]["VALOR"].sum():,.2f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="card"><div class="label">Saídas</div><div class="value">R$ {abs(df[df["VALOR"]<0]["VALOR"].sum()):,.2f}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="card"><div class="label">Saldo Líquido</div><div class="value">R$ {saldo_liquido:,.2f}</div></div>', unsafe_allow_html=True)
            
            st.write("")
            st.dataframe(df, use_container_width=True)
            
            txt = gerar_txt_dominio(df)
            st.download_button("🚀 Gerar .TXT p/ Domínio", txt, file_name=f"import_{arquivo.name}.txt", use_container_width=True)
else:
    st.info("Utilize a barra lateral para carregar seus extratos.")
