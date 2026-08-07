import streamlit as st
import pandas as pd
import re
import io
import os
from pypdf import PdfReader

# Configuração da página
st.set_page_config(page_title="Importador Domínio Pro", layout="wide", page_icon="🤖")

# --- CSS PARA CARDS COMPACTOS E ESTILO LIMPO ---
st.markdown("""
    <style>
        .metric-card { background-color: #f0f2f6; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #d1d5db; }
        .metric-title { font-size: 0.8rem; color: #4b5563; }
        .metric-value { font-size: 1.1rem; font-weight: bold; color: #111827; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO ---
def limpar_valor(v):
    if pd.isna(v) or v == '': return 0.0
    s = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except: return 0.0

def processar_ofx(file_bytes):
    texto = file_bytes.decode('utf-8', errors='ignore')
    # Captura apenas transações <STMTTRN> ignorando blocos de balanço (LEDGERBAL)
    transacoes = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', texto, re.DOTALL)
    dados = []
    for t in transacoes:
        dt = re.search(r'<DTPOSTED>(\d{8})', t)
        val = re.search(r'<TRNAMT>([-+]?[\d.]+)', t)
        memo = re.search(r'<MEMO>(.*?)(?:<|$)', t)
        if dt and val:
            dados.append({
                'DATA': f"{dt.group(1)[6:8]}/{dt.group(1)[4:6]}/{dt.group(1)[:4]}",
                'VALOR': limpar_valor(val.group(1)),
                'HISTÓRICO': memo.group(1) if memo else "TRANSACAO BANCARIA"
            })
    return pd.DataFrame(dados)

def processar_tabela_geral(file_bytes, filename):
    try:
        if filename.endswith('.csv'): df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
        else: df = pd.read_excel(io.BytesIO(file_bytes))
        
        df.columns = [str(c).upper() for c in df.columns]
        
        # Identifica colunas de data, valor e as demais de texto
        col_data = next((c for c in df.columns if 'DATA' in c or 'DT' in c), df.columns[0])
        col_valor = next((c for c in df.columns if 'VALOR' in c or 'VAL' in c or 'IMPACTO' in c), df.columns[-1])
        col_texto = [c for c in df.columns if c not in [col_data, col_valor]]
        
        # Consolida histórico completo
        df['HISTÓRICO'] = df[col_texto].astype(str).agg(' '.join, axis=1).str.replace('nan', '', regex=False).str.strip()
        df['DATA'] = df[col_data]
        df['VALOR'] = df[col_valor].apply(limpar_valor)
        
        return df[['DATA', 'VALOR', 'HISTÓRICO']]
    except: return pd.DataFrame()

# --- INTERFACE ---
st.sidebar.title("📥 Importador")
arquivos = st.sidebar.file_uploader("Arraste seus extratos", accept_multiple_files=True)

st.title("🤖 Importador Inteligente Domínio")

if arquivos:
    for arquivo in arquivos:
        st.markdown(f"---")
        st.subheader(f"Arquivo: {arquivo.name}")
        
        if arquivo.name.endswith('.ofx'): df = processar_ofx(arquivo.getvalue())
        else: df = processar_tabela_geral(arquivo.getvalue(), arquivo.name)
        
        # FILTRO PODEROSO: Remove tudo que tem 'saldo' ou 'total' no histórico
        df = df[~df['HISTÓRICO'].str.contains('SALDO|TOTAL|INICIAL|FINAL|DISPONÍVEL|SUBTOTAL', case=False, na=False)]
        
        # Cards compactos
        qtd = len(df)
        entradas = df[df["VALOR"] > 0]["VALOR"].sum()
        saidas = abs(df[df["VALOR"] < 0]["VALOR"].sum())
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{qtd}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value">R$ {entradas:,.2f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value">R$ {saidas:,.2f}</div></div>', unsafe_allow_html=True)
        
        st.write("")
        st.dataframe(df, use_container_width=True, height=250)
        
        # Download
        txt_data = "\n".join([f"{r['DATA']};;{r['VALOR']};{r['HISTÓRICO']}" for _, r in df.iterrows()])
        st.download_button("🚀 Gerar .TXT p/ Domínio", txt_data, file_name=f"import_{arquivo.name}.txt")

else:
    st.info("Aguardando o envio de arquivos de extrato na barra lateral.")
