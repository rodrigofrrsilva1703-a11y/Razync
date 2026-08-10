import streamlit as st
import pandas as pd
import openpyxl
import re
import calendar
import io
import os
import tempfile
import unicodedata
import json
import hashlib
import hmac
import zipfile
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pypdf import PdfReader
import traceback

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
        .stButton>button { width: 100% !important; border-radius: 6px !important; font-weight: 500 !important; padding: 0.45rem 1rem !important; border: 1px solid #30363d !important; background-color: #21262d !important; color: #c9d1d9 !important; transition: all 0.2s ease; box-shadow: none !important; }
        .stButton>button:hover { background-color: #30363d !important; border-color: #8b949e !important; color: #ffffff !important; }
        .metric-card { background-color: #161b22; border: 1px solid #30363d; padding: 14px; border-radius: 8px; text-align: center; }
        .metric-title { font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.5px; }
        .metric-value { font-size: 18px; color: #f0f6fc; font-weight: 700; }
        section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
        .tool-card { background-color: #161b22; border: 1px solid #30363d; padding: 24px 20px; border-radius: 8px; text-align: center; height: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center; transition: border-color 0.2s ease; }
        .tool-card:hover { border-color: #8b949e; }
        .alerta-dominio { background-color: #3d1c1c; border-left: 5px solid #f85149; padding: 16px; border-radius: 4px; margin-bottom: 20px; }
        .alerta-dominio h4 { margin-top: 0; color: #f85149; font-size: 16px; }
        .alerta-dominio p { margin-bottom: 0; color: #c9d1d9; font-size: 14px; }
        .aviso-banner { background-color: #161b22; border: 1px solid #30363d; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; }
        .aviso-banner p { margin: 0; color: #c9d1d9; font-size: 14px; }
        
        /* Alinhamento perfeito entre date_input e text_input */
        .stTextInput { margin-top: -2px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES DE LIMPEZA E FORMATAÇÃO (MECÂNICAS)
# ==============================================================================
def limpar_caracteres_ilegais(val):
    if isinstance(val, str): return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', val)
    return val

def normalizar_texto(texto):
    if not isinstance(texto, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').lower()

def formatar_moeda(valor):
    try: return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def formatar_dataframe_moeda_br(df, colunas):
    """Formata apenas a cópia exibida; os dados originais continuam numéricos."""
    exibicao = df.copy()
    for coluna in colunas:
        if coluna in exibicao.columns:
            exibicao[coluna] = exibicao[coluna].apply(
                lambda valor: formatar_moeda(valor) if pd.notna(valor) and valor != '' else ''
            )
    return exibicao

def sanitizar_dataframe(df):
    for col in df.select_dtypes(include=['object', 'string']).columns: df[col] = df[col].apply(limpar_caracteres_ilegais)
    return df

def interpretar_sinal_inteligente(historico_str, valor_num, explicit_nature=""):
    """
    Motor Inteligente Universal:
    Avalia se o lançamento é Entrada (+) ou Saída (-) com base em indicadores
    explícitos e análise semântica avançada do histórico.
    """
    val = abs(float(valor_num))
    ind = normalizar_texto(str(explicit_nature)).strip()
    ind_tokens = set(re.findall(r'[a-z]+', ind))
    h_norm = normalizar_texto(historico_str)
    
    # 1. Indicador explícito de natureza (C/D, Crédito/Débito, Entrada/Saída)
    natureza_debito = (
        ind in {'d', 'deb', 'db', 'debito', 'saida'} or
        bool(ind_tokens.intersection({'debito', 'saida', 'pagamento', 'pagto', 'emitido'}))
    )
    natureza_credito = (
        ind in {'c', 'cred', 'cr', 'credito', 'entrada'} or
        bool(ind_tokens.intersection({'credito', 'entrada', 'recebimento', 'recebido'}))
    )
    if natureza_debito:
        return -val
    if natureza_credito:
        return val
        
    # 2. Se o valor já veio negativo do arquivo original
    if valor_num < 0:
        return -val

    # 3. Indicadores inequívocos de entrada têm prioridade sobre termos como
    # "aplic" que podem aparecer no complemento de um rendimento.
    termos_entrada = [
        'pix recebido', 'ted recebida', 'ted recebido', 'recebimento',
        'recebimentos', 'rendimento', 'rendimentos', 'deposito',
        'boleto recebido', 'boletos recebidos', 'estorno cred', 'credito'
    ]
    if any(termo in h_norm for termo in termos_entrada):
        return val
        
    # 4. Análise semântica inteligente por palavras-chave de saída no histórico
    termos_saida = [
        'ted emitido', 'ted emi do', 'pix env', 'pix enviado', 'ted env', 'doc env', 'pagto', 'pagamento', 
        'tarifa', 'manut', 'cobranca', 'debito', 'saque', 'compra', 'cartao', 
        'transferencia env', 'transf env', 'cpfl', 'darf', 'gps', 'iss', 'imposto',
        'aplicacao', 'aplic', 'investimento', 'estorno deb', 'saida', 'db', 'sispag',
        'concessionaria', 'tributo', 'boleto pago', 'tarifa emissao', 'tarifa emissao de ted', 'emitido'
    ]
    
    if any(termo in h_norm for termo in termos_saida):
        return -val
        
    # Padrão para recebimentos, pix recebido, ted recebida, rendimentos, etc.
    return val

def limpar_valor_monetario(v_val):
    if pd.isna(v_val) or v_val == '': return 0.0
    if isinstance(v_val, (int, float)): return float(v_val)
    
    s = str(v_val).strip().upper()
    is_negative = False
    if '-' in s or s.endswith('D') or s.endswith('SAÍDA') or s.endswith('SAIDA') or re.search(r'\(\s*[\d\.,]+\s*\)', s):
        is_negative = True
        
    s = re.sub(r'[^\d,\.]', '', s)
    if not s: return 0.0
    
    if ',' in s and '.' in s:
        last_dot, last_comma = s.rfind('.'), s.rfind(',')
        s = s.replace('.', '').replace(',', '.') if last_comma > last_dot else s.replace(',', '')
    elif ',' in s: 
        s = s.replace(',', '.')
        
    try: 
        val = float(s)
        return -abs(val) if is_negative else abs(val)
    except: 
        return 0.0

def identificar_banco_inteligente(texto_conteudo, filename_str=""):
    # O nome do arquivo tem prioridade para impedir que fornecedores citados no
    # histórico sejam confundidos com o banco emissor do extrato.
    nome = normalizar_texto(str(filename_str)).upper()
    cabecalho = normalizar_texto(str(texto_conteudo)[:6000]).upper()
    digitos_nome = re.sub(r'\D', '', str(filename_str))
    digitos_cabecalho = re.sub(r'\D', '', str(texto_conteudo)[:6000])

    # As empresas também nomeiam os extratos apenas com agência/conta. Essa
    # identificação não depende do mês ou do ano presentes no nome do arquivo.
    contas_nova_geracao = [
        ('995495', 'BANCO ITAU'),
        ('4519906', 'BANCO BRADESCO'),
        ('6739471', 'BANCO FIBRA'),
    ]
    for conta, banco in contas_nova_geracao:
        if conta in digitos_nome:
            return banco

    bancos = [
        (['ITAU'], 'BANCO ITAU'),
        (['BRADESCO'], 'BANCO BRADESCO'),
        (['FIBRA'], 'BANCO FIBRA'),
        (['SANTANDER'], 'BANCO SANTANDER'),
        (['SICOOB'], 'SICOOB'),
        (['SICREDI'], 'SICREDI'),
        (['NUBANK', 'NU PAGAMENTO'], 'NUBANK'),
        (['CAIXA ECONOMICA'], 'CAIXA ECONOMICA'),
        (['BANCO DO BRASIL'], 'BANCO DO BRASIL'),
        (['BANCO INTER'], 'BANCO INTER'),
    ]
    for termos, banco in bancos:
        if any(termo in nome for termo in termos):
            return banco
    for termos, banco in bancos:
        if any(termo in cabecalho for termo in termos):
            return banco
    for conta, banco in contas_nova_geracao:
        if conta in digitos_cabecalho:
            return banco
    if '58.616.418' in str(texto_conteudo)[:6000]: return 'BANCO FIBRA'
    if re.search(r'\b0?341\b', cabecalho): return 'BANCO ITAU'
    return "BANCO CONTA CORRENTE"

# ==============================================================================
# MOTORES DE EXTRAÇÃO UNIVERSAL
# ==============================================================================
def processar_ofx(file_bytes, filename):
    lancamentos = []
    texto = ""
    for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
        try: texto = file_bytes.decode(enc); break
        except: pass
    if not texto: texto = file_bytes.decode('latin1', errors='ignore')
    
    banco_detectado = identificar_banco_inteligente(texto, filename)
    raw_blocks = re.split(r'<STMTTRN>', texto, flags=re.IGNORECASE)
    
    for block in raw_blocks[1:]:
        block_clean = re.split(r'</STMTTRN>|</BANKTRANLIST>', block, flags=re.IGNORECASE)[0]
        match_date = re.search(r'<DTPOSTED>\s*(\d{4}[-/\.]?\d{2}[-/\.]?\d{2}|\d{8})', block_clean, re.IGNORECASE)
        match_amt = re.search(r'<TRNAMT>\s*([\+\-]?[\d\.\,]+)', block_clean, re.IGNORECASE)
        match_memo = re.search(r'<(?:MEMO|NAME|PAYEE)>\s*(.*?)(?:\r|\n|<|$)', block_clean, re.IGNORECASE)
        match_type = re.search(r'<TRNTYPE>\s*([A-Z]+)', block_clean, re.IGNORECASE)
        
        if match_date and match_amt:
            dt_s = match_date.group(1).replace('-', '').replace('/', '').replace('.', '')
            if len(dt_s) >= 8: data_fmt = f"{dt_s[6:8]}/{dt_s[4:6]}/{dt_s[:4]}"
            else: continue
            
            valor_bruto = limpar_valor_monetario(match_amt.group(1).strip())
            trntype = match_type.group(1).upper() if match_type else ""
            historico = limpar_caracteres_ilegais(match_memo.group(1).strip().replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')) if match_memo else "TRANSACAO OFX"
            
            if 'SALDO' in historico.upper(): continue
            
            if trntype in ['DEBIT', 'PAYMENT', 'FEE']:
                valor_float = -abs(valor_bruto)
            elif trntype in ['CREDIT', 'DEP', 'DIRECTDEP']:
                valor_float = abs(valor_bruto)
            else:
                valor_float = interpretar_sinal_inteligente(historico, valor_bruto)
                
            if valor_float != 0: 
                lancamentos.append({'DESCRIÇÃO': banco_detectado, 'DATA': data_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': historico})
    return lancamentos

def processar_planilha_universal(file_bytes, filename):
    lancamentos, df = [], None
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.xlsx', '.xls']:
        try:
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            for sheet in xls.sheet_names:
                df_temp = pd.read_excel(xls, sheet_name=sheet, dtype=str)
                if df_temp is not None and not df_temp.empty and df_temp.shape[1] > 1:
                    df = df_temp
                    break
        except Exception:
            try: dfs = pd.read_html(io.BytesIO(file_bytes))
            except Exception: pass
            if dfs: df = dfs[0]
    if df is None:
        for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']:
            for sep in [';', ',', '\t', '|']:
                try: df_temp = pd.read_csv(io.BytesIO(file_bytes), sep=sep, encoding=enc, dtype=str)
                except Exception: pass
                if df_temp is not None and df_temp.shape[1] > 1: df = df_temp; break
            if df is not None: break
    if df is None or df.empty: return []
    
    texto_amostra = " ".join([str(v) for row in df.head(10).values for v in row if pd.notna(v)])
    banco_detectado = identificar_banco_inteligente(texto_amostra, filename)
    
    header_idx = None
    for idx, row in df.iterrows():
        row_str = normalizar_texto(" ".join([str(v) for v in row.values if pd.notna(v)]))
        if ('data' in row_str or 'dt' in row_str) and ('valor' in row_str or 'credito' in row_str or 'debito' in row_str or 'lancamento' in row_str or 'historico' in row_str):
            header_idx = idx; break
            
    if header_idx is not None:
        df.columns = [str(v).strip() for v in df.iloc[header_idx].values]
        df = df.iloc[header_idx+1:].copy()
    
    cols_map = {c: normalizar_texto(c) for c in df.columns}
    col_data = next((c for c, nc in cols_map.items() if any(p in nc for p in ['data', 'dt', 'date', 'dia'])), None)
    col_hist = next((c for c, nc in cols_map.items() if any(p in nc for p in ['lancamento', 'historico', 'hist', 'razao social', 'descric', 'detalhe', 'memo'])), None)
    col_val = next((c for c, nc in cols_map.items() if any(p in nc for p in ['valor', 'val', 'monto', 'amount'])), None)
    col_cred = next((c for c, nc in cols_map.items() if any(p in nc for p in ['credito', 'credit', 'entrada', 'vlr_cred', 'crd'])), None)
    col_deb = next((c for c, nc in cols_map.items() if any(p in nc for p in ['debito', 'debit', 'saida', 'vlr_deb', 'deb'])), None)
    col_tipo = next((c for c, nc in cols_map.items() if any(p in nc for p in ['tipo', 'natureza', 'operacao', 'c/d'])), None)

    if not col_data: return []
    
    for _, row in df.iterrows():
        dt_raw = str(row[col_data]).strip() if pd.notna(row[col_data]) else ''
        if dt_raw.upper() in ['TOTAL', 'ÚLTIMOS LANÇAMENTOS', 'ULTIMOS LANCAMENTOS', 'SALDOS INVEST FÁCIL / PLUS', 'NAN', 'SALDO ANTERIOR']:
            if dt_raw.upper() == 'TOTAL': break
            continue
            
        match_dt = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', dt_raw)
        if not match_dt: continue
        dt_fmt = match_dt.group(1).replace('-', '/')
        
        hist_raw = limpar_caracteres_ilegais(str(row[col_hist]).strip()) if col_hist and pd.notna(row[col_hist]) else 'MOVIMENTO BANCARIO'
        hist_fmt = hist_raw if hist_raw.lower() != 'nan' else 'MOVIMENTO BANCARIO'
        if any(term in hist_fmt.upper() for term in ['SALDO', 'SUBTOTAL', 'TOTAL', 'TRANSPORTAR']): continue
        
        valor_float = 0.0
        
        if col_cred or col_deb:
            v_cred = limpar_valor_monetario(row[col_cred]) if col_cred and pd.notna(row[col_cred]) else 0.0
            v_deb = limpar_valor_monetario(row[col_deb]) if col_deb and pd.notna(row[col_deb]) else 0.0
            if v_cred != 0: valor_float = abs(v_cred)
            elif v_deb != 0: valor_float = -abs(v_deb)
        elif col_val and pd.notna(row[col_val]):
            val_cru = limpar_valor_monetario(row[col_val])
            tipo_str = str(row[col_tipo]).strip() if col_tipo and pd.notna(row[col_tipo]) else ""
            valor_float = interpretar_sinal_inteligente(hist_fmt, val_cru, tipo_str)

        if valor_float != 0:
            lancamentos.append({'DESCRIÇÃO': banco_detectado, 'DATA': dt_fmt, 'VALOR': valor_float, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': hist_fmt})
    return lancamentos

def extrair_periodo_extrato(caminho_pdf):
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto = "".join([p.extract_text() for p in reader.pages[:3]])
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if len(datas) >= 2: return datetime.strptime(datas[0], '%d/%m/%Y'), datetime.strptime(datas[1], '%d/%m/%Y')
    except: pass
    return None, None

def processar_pdf_layout_universal(reader, banco_identificado):
    """
    Analisa tabelas bancárias pela estrutura do próprio PDF, sem regras por banco.

    O motor combina: cabeçalhos detectados, posição das colunas, última data
    válida, sinais C/D, semântica do histórico e variação matemática do saldo.
    """
    lancamentos = []
    tabela_ativa = False
    encontrou_cabecalho = False
    data_atual = None
    saldo_anterior = None
    pos_credito = None
    pos_debito = None
    pos_valor = None
    pos_saldo = None
    historico_pendente = ""

    date_regex = re.compile(r'(?<!\d)(\d{2}/\d{2}/\d{4})(?!\d)')
    valor_regex = re.compile(
        r'(?<!\d)(?:R\$\s*)?(\(?\s*[+-]?\s*\d{1,3}(?:\.\d{3})*,\d{2}\s*\)?\s*[CD]?)(?!\d)',
        re.IGNORECASE
    )

    def limpar_historico_linha(linha, data_linha=None):
        hist = linha
        if data_linha:
            hist = hist.replace(data_linha, ' ', 1)
        hist = valor_regex.sub(' ', hist).replace('R$', ' ')
        hist = hist.replace('Emi\x00do', 'Emitido').replace('\x00', '')
        return re.sub(r'\s+', ' ', hist).strip(' -|')

    def linha_auxiliar_valida(linha):
        norm = normalizar_texto(linha)
        if re.match(r'^\s*\d+\s*/\s*\d+\s*$', linha):
            return False
        bloqueios = [
            'extrato mensal', 'nome do usuario', 'data da operacao', 'folha ',
            'pagina ', 'sujeito a alteracoes', 'fim de relatorio', 'cnpj:',
            'agencia | conta', 'total disponivel', 'extrato de:', 'lancamento dcto',
            'lembramos que', 'movimentacao de saldo', 'sua validade restrita'
        ]
        return bool(linha.strip()) and not any(item in norm for item in bloqueios)

    parar_processamento = False
    for pagina in reader.pages:
        try:
            texto_layout = pagina.extract_text(extraction_mode="layout") or ""
        except (TypeError, ValueError):
            texto_layout = pagina.extract_text() or ""

        linhas = texto_layout.splitlines()
        for indice_linha, linha in enumerate(linhas):
            norm = normalizar_texto(linha)

            # Encerra o extrato principal antes de avisos, projeções ou uma nova
            # tabela de lançamentos futuros existente no mesmo PDF.
            if lancamentos and (
                'lancamentos futuros do periodo' in norm or
                norm.startswith('aviso: os saldos acima') or
                (norm.startswith('saldo de ') and not date_regex.search(linha)) or
                norm.startswith('posicao em:')
            ):
                parar_processamento = True
                break

            # Detecta dinamicamente as colunas da tabela.
            tem_data = re.search(r'\bdata\b', norm) is not None
            tem_coluna_monetaria = any(k in norm for k in ['credito', 'debito', 'valor', 'saldo'])
            if tem_data and tem_coluna_monetaria:
                tabela_ativa = True
                encontrou_cabecalho = True
                if 'credito' in norm:
                    pos_credito = normalizar_texto(linha).find('credito')
                if 'debito' in norm:
                    pos_debito = normalizar_texto(linha).find('debito')
                if 'valor' in norm:
                    pos_valor = normalizar_texto(linha).find('valor')
                if 'saldo' in norm:
                    pos_saldo = normalizar_texto(linha).find('saldo')
                continue

            # Finaliza a primeira tabela principal antes de resumos ou outras seções.
            if tabela_ativa and lancamentos and re.match(r'^\s*total\b', norm):
                parar_processamento = True
                break

            ocorrencias = list(valor_regex.finditer(linha))
            match_data = date_regex.search(linha)
            datas_na_linha = date_regex.findall(linha)

            # PDFs sem cabeçalho ainda podem iniciar por uma linha transacional.
            if not tabela_ativa and not encontrou_cabecalho:
                if (match_data and len(datas_na_linha) == 1 and ocorrencias and
                        not any(k in norm for k in ['periodo', 'saldo', 'disponivel', 'limite'])):
                    tabela_ativa = True
                else:
                    continue

            if not tabela_ativa:
                continue

            # Saldo anterior/de abertura serve para validar matematicamente o sinal.
            if 'saldo anterior' in norm or 'saldo inicial' in norm:
                if match_data:
                    data_atual = match_data.group(1)
                if ocorrencias:
                    saldo_anterior = limpar_valor_monetario(ocorrencias[-1].group(1))
                continue

            # Linhas isoladas de saldo não são lançamentos.
            if ('saldo' in norm and not any(k in norm for k in ['rentab', 'rendimento'])):
                if ocorrencias:
                    saldo_anterior = limpar_valor_monetario(ocorrencias[-1].group(1))
                continue

            # Resumos financeiros e limites não representam movimentações.
            if any(k in norm for k in [
                'disponivel', 'limite adicional', 'bloqueado', 'c.p.m.f',
                'provisionado', 'lancamentos futuros', 'tarifas pendentes',
                'previsao encargos', 'posicao em:'
            ]):
                continue

            # Uma linha com movimento + saldo tem ao menos dois valores. Quando há
            # apenas um, o cabeçalho/posição e o histórico definem sua natureza.
            if not ocorrencias:
                # Alguns PDFs quebram um valor alto: a linha da transação termina
                # em "R$" e o número aparece sozinho na linha seguinte.
                if match_data and len(datas_na_linha) == 1 and 'R$' in linha:
                    data_atual = match_data.group(1)
                    historico_pendente = limpar_historico_linha(linha, data_atual)
                    continue
                if lancamentos and linha_auxiliar_valida(linha):
                    complemento = limpar_historico_linha(linha)
                    if complemento and not date_regex.search(complemento):
                        hist_atual = lancamentos[-1]['HISTÓRICO']
                        lancamentos[-1]['HISTÓRICO'] = re.sub(r'\s+', ' ', f"{hist_atual} {complemento}").strip()
                continue

            if match_data:
                data_atual = match_data.group(1)
            if not data_atual:
                continue

            # Valores anteriores ao último são movimento; o último é saldo quando
            # a tabela possui coluna Saldo e há mais de um valor na linha.
            tem_saldo_linha = pos_saldo is not None and len(ocorrencias) >= 2
            saldo_linha = limpar_valor_monetario(ocorrencias[-1].group(1)) if tem_saldo_linha else None
            candidatos = ocorrencias[:-1] if tem_saldo_linha else ocorrencias
            candidatos_validos = [m for m in candidatos if limpar_valor_monetario(m.group(1)) != 0]
            if not candidatos_validos:
                if saldo_linha is not None:
                    saldo_anterior = saldo_linha
                continue

            mov = candidatos_validos[0]
            token_mov = mov.group(1).strip()
            valor_bruto = limpar_valor_monetario(token_mov)
            valor_abs = abs(valor_bruto)
            natureza = ''
            if re.search(r'D\s*$', token_mov, re.IGNORECASE):
                natureza = 'D'
            elif re.search(r'C\s*$', token_mov, re.IGNORECASE):
                natureza = 'C'

            hist_linha = limpar_historico_linha(linha, match_data.group(1) if match_data else None)
            hist = re.sub(r'\s+', ' ', f"{historico_pendente} {hist_linha}").strip()
            historico_pendente = ""
            hist_norm = normalizar_texto(hist)
            if any(k in hist_norm for k in ['saldo invest', 'saldo anterior', 'saldo final', 'saldo do dia']):
                if saldo_linha is not None:
                    saldo_anterior = saldo_linha
                continue

            # Prioridade 1: sinal explícito no próprio valor.
            if valor_bruto < 0 or natureza == 'D':
                valor_final = -valor_abs
            elif natureza == 'C':
                valor_final = valor_abs
            else:
                valor_final = None

            # Prioridade 2: diferença exata entre saldo atual e saldo anterior.
            if valor_final is None and saldo_linha is not None and saldo_anterior is not None:
                diferenca = round(saldo_linha - saldo_anterior, 2)
                if abs(abs(diferenca) - valor_abs) <= 0.05:
                    valor_final = valor_abs if diferenca > 0 else -valor_abs

            # Prioridade 3: posição em colunas Débito/Crédito detectadas.
            if valor_final is None and pos_debito is not None and pos_credito is not None:
                pos_movimento = linha.find('R$', max(0, mov.start() - 4), mov.end())
                if pos_movimento < 0:
                    pos_movimento = mov.start(1)
                dist_debito = abs(pos_movimento - pos_debito)
                dist_credito = abs(pos_movimento - pos_credito)
                valor_final = -valor_abs if dist_debito < dist_credito else valor_abs

            # Prioridade 4: sinal semântico como último recurso.
            if valor_final is None:
                valor_final = interpretar_sinal_inteligente(hist, valor_bruto, natureza)

            if valor_abs != 0:
                lancamentos.append({
                    'DESCRIÇÃO': banco_identificado,
                    'DATA': data_atual,
                    'VALOR': valor_final,
                    'DÉBITO': '',
                    'CRÉDITO': '',
                    'HISTÓRICO': limpar_caracteres_ilegais(hist or 'MOVIMENTO BANCARIO')
                })

            if saldo_linha is not None:
                saldo_anterior = saldo_linha

        if parar_processamento:
            break

    return lancamentos

def extrair_valor_lancamento_pdf(texto_bloco):
    """
    Seleciona o valor da movimentação sem confundi-lo com o saldo.

    Extratos normalmente exibem o valor do lançamento antes do saldo. Esta
    função também descarta números ligados explicitamente a saldo anterior,
    saldo atual, disponível, limite e resumos semelhantes.
    """
    padrao_valor = re.compile(
        r'(?<!\d)(?:R\$\s*)?(\(?\s*[+-]?[\d\.]+,\d{2}\s*\)?\s*[CD]?)(?!\d)',
        re.IGNORECASE
    )
    ocorrencias = list(padrao_valor.finditer(texto_bloco))
    if not ocorrencias:
        return None, ""

    termos_resumo = [
        'saldo', 'disponivel', 'limite', 'bloqueado', 'provisionado',
        'saldo atual', 'saldo anterior', 'saldo final', 'saldo do dia'
    ]
    candidatos = []
    for ocorrencia in ocorrencias:
        contexto_antes = normalizar_texto(texto_bloco[max(0, ocorrencia.start() - 35):ocorrencia.start()])
        if any(termo in contexto_antes for termo in termos_resumo):
            continue
        candidatos.append(ocorrencia)

    # Se todos foram marcados como resumo, não cria um lançamento de saldo.
    if not candidatos:
        return None, ""

    # Nos formatos Valor + Saldo, Débito + Saldo ou Crédito + Saldo, o primeiro
    # valor monetário útil pertence ao lançamento e os seguintes são saldos.
    escolhido = candidatos[0]
    token = escolhido.group(1).strip()
    natureza = ""
    if re.search(r'D\s*$', token, re.IGNORECASE):
        natureza = "D"
    elif re.search(r'C\s*$', token, re.IGNORECASE):
        natureza = "C"

    return token, natureza

def processar_arquivo_pdf(caminho_pdf, filename_original=None):
    lancamentos = []
    try:
        reader = PdfReader(caminho_pdf, strict=False)
        texto_completo = ""
        for pagina in reader.pages:
            texto_completo += (pagina.extract_text() or "") + "\n"
            
        nome_para_identificacao = filename_original or os.path.basename(caminho_pdf)
        banco_identificado = identificar_banco_inteligente(texto_completo, nome_para_identificacao)

        # Primeiro tenta o analisador estrutural único, independente do banco.
        lancamentos_layout = processar_pdf_layout_universal(reader, banco_identificado)
        if lancamentos_layout:
            return lancamentos_layout

        linhas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        date_regex = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            match_date = date_regex.match(linha)
            if match_date:
                data_str = match_date.group(1)
                bloco_linhas = [linha]
                j = i + 1
                while j < len(linhas):
                    next_linha = linhas[j]
                    if date_regex.match(next_linha) or 'SALDO' in next_linha.upper() or 'Página' in next_linha:
                        break
                    bloco_linhas.append(next_linha)
                    j += 1
                
                texto_bloco = " ".join(bloco_linhas)
                val_str, natureza_valor = extrair_valor_lancamento_pdf(texto_bloco)

                if val_str is not None:
                    v_num = limpar_valor_monetario(val_str)

                    hist = texto_bloco.replace(data_str, '', 1)
                    hist = re.sub(
                        r'(?<!\d)(?:R\$\s*)?\(?\s*[+-]?[\d\.]+,\d{2}\s*\)?\s*[CD]?(?!\d)',
                        ' ', hist, flags=re.IGNORECASE
                    )
                    hist = re.sub(r'\s+', ' ', hist).strip()

                    if not any(termo in hist.upper() for termo in ['SALDO ANTERIOR', 'SALDO FINAL', 'SALDO DO DIA']) and v_num != 0:
                        v_final = interpretar_sinal_inteligente(hist, v_num, natureza_valor)
                        lancamentos.append({'DESCRIÇÃO': banco_identificado, 'DATA': data_str, 'VALOR': v_final, 'DÉBITO': '', 'CRÉDITO': '', 'HISTÓRICO': limpar_caracteres_ilegais(hist)})
                i = j - 1
            i += 1
    except Exception as e:
        print(f"Erro no processamento PDF universal: {e}")
    return lancamentos

def gerar_txt_dominio(df):
    linhas_txt = []
    for _, row in df.iterrows():
        hist_limpo = limpar_caracteres_ilegais(str(row['HISTÓRICO'])).replace(';', ' ')
        linhas_txt.append(f"{row['DATA']};{row['DÉBITO'] if pd.notna(row['DÉBITO']) else ''};{row['CRÉDITO'] if pd.notna(row['CRÉDITO']) else ''};{float(row['VALOR']):.2f};{hist_limpo}\n")
    return "".join(linhas_txt)

def processar_razao_dominio(file_bytes, filename):
    df = None
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        if ext == '.xlsx':
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            for sheet in xls.sheet_names:
                df_temp = pd.read_excel(xls, sheet_name=sheet, dtype=str, header=None)
                if df_temp is not None and not df_temp.empty and df_temp.shape[1] > 1:
                    df = df_temp
                    break
        elif ext == '.xls':
            try: df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, header=None, engine='xlrd')
            except Exception as e:
                if "Expected BOF record" in str(e) or "corrupt" in str(e).lower():
                    st.session_state['erro_bof_xls'] = True
                    return None
                try: df = pd.read_html(io.BytesIO(file_bytes), header=None)[0].astype(str)
                except Exception:
                    st.session_state['erro_bof_xls'] = True
                    return None
        else:
            for enc in ['utf-8', 'latin1', 'cp1252']:
                for sep in [';', '\t', '|', ',']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, encoding=enc, dtype=str, header=None, on_bad_lines='skip')
                        if df.shape[1] > 1: break
                    except: continue
                if df is not None and df.shape[1] > 1: break
    except Exception: return None
    
    if df is None or df.empty: return None
    
    header_row_idx = 0
    for idx, row in df.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)]).upper()
        if ('DATA' in row_str or 'DT' in row_str) and ('VALOR' in row_str or 'DEBITO' in row_str or 'DÉBITO' in row_str or 'CREDITO' in row_str or 'CRÉDITO' in row_str):
            header_row_idx = idx
            break
            
    if header_row_idx > 0:
        df.columns = [str(v).strip().upper() for v in df.iloc[header_row_idx].values]
        df = df.iloc[header_row_idx+1:].copy()
    else:
        df.columns = [str(v).strip().upper() for v in df.iloc[0].values]
        df = df.iloc[1:].copy()
        
    df.columns = [re.sub(r'[^\w\s]', '', c) for c in df.columns]
    cols = list(df.columns)
    
    col_data = next((c for c in cols if any(p in c for p in ['DATA', 'DT'])), None)
    col_deb = next((c for c in cols if any(p in c for p in ['DEBITO', 'DÉBITO', 'SAIDA', 'DEB'])), None)
    col_cred = next((c for c in cols if any(p in c for p in ['CREDITO', 'CRÉDITO', 'ENTRADA', 'CRE'])), None)
    col_val = next((c for c in cols if any(p in c for p in ['VALOR', 'VL'])), None)
    col_hist = next((c for c in cols if any(p in c for p in ['HISTORICO', 'HISTÓRICO', 'HIST', 'COMPLEMENTO', 'LANCAMENTO', 'DESCRI'])), None)
    
    if not col_data: return None
    
    dados = []
    for _, row in df.iterrows():
        dt_raw = str(row[col_data]).strip() if pd.notna(row[col_data]) else ''
        match_dt = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', dt_raw)
        if not match_dt: continue
        dt_fmt = match_dt.group(1).replace('-', '/')
        
        v_ent, v_sai = 0.0, 0.0
        
        if col_deb and col_cred:
            v_sai = abs(limpar_valor_monetario(row[col_deb])) if pd.notna(row[col_deb]) else 0.0
            v_ent = abs(limpar_valor_monetario(row[col_cred])) if pd.notna(row[col_cred]) else 0.0
        elif col_val and pd.notna(row[col_val]):
            val_num = limpar_valor_monetario(row[col_val])
            if val_num < 0: v_sai = abs(val_num)
            else: v_ent = val_num
                
        hist_str = limpar_caracteres_ilegais(str(row[col_hist]).strip()) if col_hist and pd.notna(row[col_hist]) else 'LANCAMENTO RAZAO'
                
        if v_ent != 0 or v_sai != 0:
            dados.append({'DATA': dt_fmt, 'ENTRADAS_RAZAO': v_ent, 'SAIDAS_RAZAO': v_sai, 'HISTÓRICO': hist_str})
            
    if not dados: return None
    df_res = pd.DataFrame(dados)
    df_res['DATA_DT'] = pd.to_datetime(df_res['DATA'], dayfirst=True, errors='coerce')
    return df_res.dropna(subset=['DATA_DT'])

# ==============================================================================
# ORGANIZADORES ESPECÍFICOS POR EMPRESA
# ==============================================================================
def texto_celula_seguro(valor):
    if valor is None or pd.isna(valor): return ""
    if isinstance(valor, float) and valor.is_integer(): return str(int(valor))
    return limpar_caracteres_ilegais(str(valor)).strip()

def identificar_estorno_de_baixa(*campos):
    """Reconhece apenas estornos ligados a baixa, preservando outros estornos."""
    texto = normalizar_texto(" ".join(texto_celula_seguro(c) for c in campos))
    tokens = re.findall(r'[a-z0-9]+', texto)
    pos_estorno = [i for i, token in enumerate(tokens) if token.startswith(('estorn', 'revers'))]
    pos_baixa = [i for i, token in enumerate(tokens) if token.startswith('baix')]
    return any(abs(i - j) <= 6 for i in pos_estorno for j in pos_baixa)

def criar_assinatura_classificacao(historico):
    """Remove documentos variáveis e preserva natureza, empresa e observação útil."""
    texto = normalizar_texto(texto_celula_seguro(historico))
    texto = re.sub(r'\b(?:pagar|pagamento)\b', 'pago', texto)
    texto = re.sub(r'\b(?:receber|recebimento)\b', 'recebido', texto)
    natureza = (
        'pago' if re.search(r'\bpago\b', texto)
        else 'recebido' if re.search(r'\brecebido\b', texto)
        else 'outro'
    )
    empresa_match = re.search(r'empresa\s*:\s*(.*?)(?:\s+obs\s*:|$)', texto)
    empresa = empresa_match.group(1) if empresa_match else texto
    empresa = re.sub(r'[^a-z0-9]+', ' ', empresa)
    tokens_empresa = [
        token for token in empresa.split()
        if not (any(c.isdigit() for c in token) and len(token) >= 3)
    ]
    empresa = ' '.join(tokens_empresa).strip()

    observacao = ''
    observacao_match = re.search(r'\s+obs\s*:\s*(.*)$', texto)
    if observacao_match:
        observacao_bruta = re.sub(r'[^a-z0-9]+', ' ', observacao_match.group(1))
        # Números, documentos, parcelas e datas mudam a cada mês. Palavras como
        # BANCO FIBRA, TRANSFERENCIA ou DEVOLUCAO alteram a classificação e ficam.
        tokens_observacao = [
            token for token in observacao_bruta.split()
            if token.isalpha() and token not in {'doc', 'documento'}
        ]
        observacao = ' '.join(tokens_observacao).strip()

    partes = [natureza, empresa]
    if observacao:
        partes.append(observacao)
    return '|'.join(partes) if empresa else ''

def obter_config_classificacao_online():
    """Obtém somente no servidor as credenciais guardadas em st.secrets."""
    try:
        secao = st.secrets.get('supabase', {})
        url = secao.get('url', '') or st.secrets.get('SUPABASE_URL', '')
        chave = secao.get('service_key', '') or st.secrets.get('SUPABASE_SERVICE_KEY', '')
        senha = secao.get('admin_password', '') or st.secrets.get(
            'CLASSIFICATION_ADMIN_PASSWORD', ''
        )
        url = str(url).strip()
        chave = str(chave).strip()
        senha = str(senha)
        placeholders_url = {'URL_DO_PROJETO_SUPABASE', 'SUA_URL_SUPABASE', 'SUPABASE_URL'}
        placeholders_chave = {
            'SERVICE_ROLE_KEY', 'SUA_SERVICE_ROLE_KEY', 'SUPABASE_SERVICE_KEY'
        }
        if url.upper() in placeholders_url or not url.startswith(('https://', 'http://')):
            url = ''
        elif url:
            partes_url = urllib.parse.urlsplit(url)
            caminho_url = partes_url.path or ''
            if '/rest/v1' in caminho_url:
                caminho_url = caminho_url.split('/rest/v1', 1)[0]
            url = urllib.parse.urlunsplit((
                partes_url.scheme,
                partes_url.netloc,
                caminho_url.rstrip('/'),
                '',
                ''
            )).rstrip('/')
        if chave.upper() in placeholders_chave:
            chave = ''
        return url, chave, senha
    except Exception:
        return '', '', ''

def requisicao_classificacao_online(caminho, metodo='GET', dados=None, prefer=''):
    url_base, chave, _ = obter_config_classificacao_online()
    if not url_base or not chave:
        raise RuntimeError(
            'A base online ainda não foi configurada com a URL e a chave reais do Supabase.'
        )
    corpo = json.dumps(dados, ensure_ascii=False).encode('utf-8') if dados is not None else None
    cabecalhos = {
        'apikey': chave,
        'Authorization': f'Bearer {chave}',
        'Content-Type': 'application/json',
    }
    if prefer:
        cabecalhos['Prefer'] = prefer
    requisicao = urllib.request.Request(
        f"{url_base.rstrip('/')}/rest/v1/{caminho}",
        data=corpo,
        headers=cabecalhos,
        method=metodo
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            conteudo = resposta.read().decode('utf-8')
            return json.loads(conteudo) if conteudo else []
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f"Falha na base online ({erro.code}): {detalhe[:300]}") from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"Não foi possível acessar a base online: {erro.reason}") from erro

def carregar_classificacoes_online(empresa='nova_geracao'):
    registros, deslocamento, limite = [], 0, 1000
    while True:
        consulta = (
            'classificacoes_bancarias?empresa=eq.'
            + urllib.parse.quote(empresa)
            + '&select=id,empresa,banco,assinatura,debito,credito,ocorrencias,periodos,exemplo_historico'
            + f'&limit={limite}&offset={deslocamento}'
        )
        lote = requisicao_classificacao_online(consulta)
        registros.extend(lote)
        if len(lote) < limite:
            break
        deslocamento += limite
    return registros

def salvar_classificacoes_online(registros):
    if not registros:
        return 0
    existentes = {item['id']: item for item in carregar_classificacoes_online()}
    for registro in registros:
        anterior = existentes.get(registro['id'], {})
        registro['ocorrencias'] = max(
            int(registro.get('ocorrencias') or 1), int(anterior.get('ocorrencias') or 0)
        )
        registro['periodos'] = sorted(set(
            (registro.get('periodos') or []) + (anterior.get('periodos') or [])
        ))
    for inicio in range(0, len(registros), 500):
        requisicao_classificacao_online(
            'classificacoes_bancarias?on_conflict=id',
            metodo='POST',
            dados=registros[inicio:inicio + 500],
            prefer='resolution=merge-duplicates,return=minimal'
        )
    return len(registros)

def ler_planilha_classificada(file_bytes, filename):
    """Lê planilha com um ou vários bancos e extrai Débito/Crédito já revisados."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    registros = []
    banco_arquivo = identificar_chave_banco_empresa(filename)
    for nome_aba in xls.sheet_names:
        bruto = pd.read_excel(xls, sheet_name=nome_aba, header=None, dtype=object)
        indice_cabecalho = None
        for indice in range(min(30, len(bruto))):
            nomes = [normalizar_texto(texto_celula_seguro(v)).strip() for v in bruto.iloc[indice]]
            if all(nome in nomes for nome in ['data', 'valor', 'debito', 'credito']) and (
                'historico' in nomes
            ):
                indice_cabecalho = indice
                break
        if indice_cabecalho is None:
            continue
        cabecalhos = [texto_celula_seguro(v) for v in bruto.iloc[indice_cabecalho]]
        df = bruto.iloc[indice_cabecalho + 1:].copy()
        df.columns = cabecalhos
        mapa = {normalizar_texto(str(c)).strip(): c for c in df.columns}
        col_hist = mapa.get('historico')
        col_data = mapa.get('data')
        col_debito = mapa.get('debito')
        col_credito = mapa.get('credito')
        col_descricao = mapa.get('descricao')
        if col_hist is None or col_debito is None or col_credito is None:
            continue
        banco_aba = identificar_chave_banco_empresa(nome_aba)
        for _, linha in df.iterrows():
            historico = texto_celula_seguro(linha[col_hist])
            debito = texto_celula_seguro(linha[col_debito])
            credito = texto_celula_seguro(linha[col_credito])
            if not historico or not debito or not credito:
                continue
            banco_linha = (
                identificar_chave_banco_empresa(linha[col_descricao])
                if col_descricao is not None else ''
            ) or banco_aba or banco_arquivo
            assinatura = criar_assinatura_classificacao(historico)
            if banco_linha not in {'itau', 'bradesco', 'fibra'} or not assinatura:
                continue
            data_lancamento = (
                pd.to_datetime(linha[col_data], dayfirst=True, errors='coerce')
                if col_data is not None else pd.NaT
            )
            periodo = (
                data_lancamento.strftime('%Y-%m') if not pd.isna(data_lancamento)
                else normalizar_texto(filename)
            )
            identificador = hashlib.sha256(
                f"nova_geracao|{banco_linha}|{assinatura}|{debito}|{credito}".encode('utf-8')
            ).hexdigest()
            registros.append({
                'id': identificador,
                'empresa': 'nova_geracao',
                'banco': banco_linha,
                'assinatura': assinatura,
                'debito': debito,
                'credito': credito,
                'ocorrencias': 1,
                'periodos': [periodo],
                'exemplo_historico': historico[:500]
            })
    return registros

def importar_arquivos_classificados(arquivos):
    """Aceita XLSX individual, vários XLSX ou ZIP contendo planilhas."""
    registros = []
    for arquivo in arquivos:
        conteudo = arquivo.getvalue()
        nome = arquivo.name
        if nome.lower().endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
                membros = [
                    membro for membro in pacote.infolist()
                    if not membro.is_dir() and membro.filename.lower().endswith(('.xlsx', '.xls'))
                ]
                if sum(membro.file_size for membro in membros) > 60 * 1024 * 1024:
                    raise ValueError('O conteúdo descompactado ultrapassa o limite de 60 MB.')
                for membro in membros:
                    if membro.file_size > 20 * 1024 * 1024:
                        raise ValueError(f'A planilha {membro.filename} ultrapassa 20 MB.')
                    registros.extend(ler_planilha_classificada(
                        pacote.read(membro), os.path.basename(membro.filename)
                    ))
        else:
            registros.extend(ler_planilha_classificada(conteudo, nome))

    agrupados = {}
    for registro in registros:
        chave = registro['id']
        if chave not in agrupados:
            agrupados[chave] = registro
        else:
            agrupados[chave]['ocorrencias'] += 1
            agrupados[chave]['periodos'] = sorted(set(
                agrupados[chave]['periodos'] + registro['periodos']
            ))
    return list(agrupados.values())

def aplicar_classificacoes_automaticas(df, banco, base_classificacoes):
    """Preenche apenas padrões repetidos e com uma única classificação conhecida."""
    resultado = df.copy()
    resultado['_CLASSIFICAÇÃO'] = 'Pendente'
    candidatos = {}
    periodos_por_assinatura = {}
    for item in base_classificacoes:
        if item.get('banco') != banco:
            continue
        assinatura = item.get('assinatura', '')
        par = (texto_celula_seguro(item.get('debito')), texto_celula_seguro(item.get('credito')))
        if assinatura and all(par):
            candidatos.setdefault(assinatura, set()).add(par)
            periodos_por_assinatura.setdefault(assinatura, set()).update(
                item.get('periodos') or []
            )
    mapa_seguro = {
        assinatura: next(iter(pares))
        for assinatura, pares in candidatos.items()
        if len(pares) == 1 and len(periodos_por_assinatura.get(assinatura, set())) >= 3
    }
    for indice, linha in resultado.iterrows():
        if texto_celula_seguro(linha.get('DÉBITO')) or texto_celula_seguro(linha.get('CRÉDITO')):
            resultado.at[indice, '_CLASSIFICAÇÃO'] = 'Já preenchido'
            continue
        assinatura = criar_assinatura_classificacao(linha.get('HISTÓRICO', ''))
        if assinatura in mapa_seguro:
            debito, credito = mapa_seguro[assinatura]
            resultado.at[indice, 'DÉBITO'] = debito
            resultado.at[indice, 'CRÉDITO'] = credito
            resultado.at[indice, '_CLASSIFICAÇÃO'] = 'Automática'
        elif assinatura in candidatos and len(candidatos[assinatura]) > 1:
            resultado.at[indice, '_CLASSIFICAÇÃO'] = 'Revisar conflito'
        elif assinatura in candidatos:
            resultado.at[indice, '_CLASSIFICAÇÃO'] = 'Revisar padrão novo'
    return resultado

def classificar_planilha_final(file_bytes, filename, base_classificacoes):
    """Preenche Débito/Crédito somente na planilha final já conciliada."""
    from openpyxl import load_workbook

    if not filename.lower().endswith('.xlsx'):
        raise ValueError('A planilha final deve estar no formato .xlsx.')

    candidatos_por_banco = {}
    periodos_por_banco = {}
    for item in base_classificacoes:
        banco = item.get('banco', '')
        assinatura = item.get('assinatura', '')
        par = (
            texto_celula_seguro(item.get('debito')),
            texto_celula_seguro(item.get('credito'))
        )
        if banco not in {'itau', 'bradesco', 'fibra'} or not assinatura or not all(par):
            continue
        candidatos_por_banco.setdefault(banco, {}).setdefault(assinatura, set()).add(par)
        periodos_por_banco.setdefault(banco, {}).setdefault(assinatura, set()).update(
            item.get('periodos') or []
        )

    mapas_seguros = {}
    for banco, candidatos in candidatos_por_banco.items():
        mapas_seguros[banco] = {
            assinatura: next(iter(pares))
            for assinatura, pares in candidatos.items()
            if len(pares) == 1 and len(
                periodos_por_banco.get(banco, {}).get(assinatura, set())
            ) >= 3
        }

    def valor_conta_excel(conta):
        texto = texto_celula_seguro(conta)
        if texto.isdigit() and (texto == '0' or not texto.startswith('0')):
            return int(texto)
        return texto

    wb = load_workbook(io.BytesIO(file_bytes))
    resumo = {
        'automaticos': 0,
        'ja_preenchidos': 0,
        'conflitos': 0,
        'padroes_novos': 0,
        'banco_nao_identificado': 0,
        'abas_processadas': 0,
    }
    banco_arquivo = identificar_chave_banco_empresa(filename)

    for ws in wb.worksheets:
        if 'retir' in normalizar_texto(ws.title):
            continue
        linha_cabecalho = None
        mapa_colunas = {}
        for numero_linha in range(1, min(ws.max_row, 30) + 1):
            mapa_teste = {
                normalizar_texto(texto_celula_seguro(ws.cell(numero_linha, coluna).value)).strip(): coluna
                for coluna in range(1, ws.max_column + 1)
            }
            if all(nome in mapa_teste for nome in ['historico', 'debito', 'credito']):
                linha_cabecalho = numero_linha
                mapa_colunas = mapa_teste
                break
        if linha_cabecalho is None:
            continue

        resumo['abas_processadas'] += 1
        col_hist = mapa_colunas['historico']
        col_debito = mapa_colunas['debito']
        col_credito = mapa_colunas['credito']
        col_descricao = mapa_colunas.get('descricao')
        banco_aba = identificar_chave_banco_empresa(ws.title) or banco_arquivo

        for numero_linha in range(linha_cabecalho + 1, ws.max_row + 1):
            historico = texto_celula_seguro(ws.cell(numero_linha, col_hist).value)
            if not historico:
                continue
            debito_atual = texto_celula_seguro(ws.cell(numero_linha, col_debito).value)
            credito_atual = texto_celula_seguro(ws.cell(numero_linha, col_credito).value)
            if debito_atual or credito_atual:
                resumo['ja_preenchidos'] += 1
                continue

            banco_linha = (
                identificar_chave_banco_empresa(ws.cell(numero_linha, col_descricao).value)
                if col_descricao is not None else ''
            ) or banco_aba
            if banco_linha not in {'itau', 'bradesco', 'fibra'}:
                resumo['banco_nao_identificado'] += 1
                continue

            assinatura = criar_assinatura_classificacao(historico)
            candidatos = candidatos_por_banco.get(banco_linha, {}).get(assinatura, set())
            par_seguro = mapas_seguros.get(banco_linha, {}).get(assinatura)
            if par_seguro:
                debito, credito = par_seguro
                ws.cell(numero_linha, col_debito).value = valor_conta_excel(debito)
                ws.cell(numero_linha, col_credito).value = valor_conta_excel(credito)
                resumo['automaticos'] += 1
            elif len(candidatos) > 1:
                resumo['conflitos'] += 1
            else:
                resumo['padroes_novos'] += 1

    if resumo['abas_processadas'] == 0:
        raise ValueError(
            'Nenhuma aba com as colunas HISTÓRICO, DÉBITO e CRÉDITO foi encontrada.'
        )

    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue(), resumo

def processar_nova_geracao_banco(file_bytes, nome_aba, conta_esperada, descricao_banco):
    """Localiza uma conta na planilha consolidada e transforma seus lançamentos."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    conta_normalizada = re.sub(r'\D', '', conta_esperada)

    df, colunas = None, None
    for aba_candidata in xls.sheet_names:
        df_candidata = pd.read_excel(xls, sheet_name=aba_candidata, dtype=object)
        mapa = {normalizar_texto(str(col)).strip(): col for col in df_candidata.columns}
        obrigatorias = ['conta', 'data', 'valor', 'lacto', 'historico', 'doc']
        if not all(nome in mapa for nome in obrigatorias):
            continue
        contas_aba = df_candidata[mapa['conta']].apply(
            lambda valor: re.sub(r'\D', '', texto_celula_seguro(valor))
        )
        if contas_aba.eq(conta_normalizada).any():
            df = df_candidata
            colunas = mapa
            break

    if df is None or colunas is None:
        raise ValueError(
            f"A conta {conta_esperada} ({nome_aba}) não foi encontrada em nenhuma aba "
            "válida da planilha consolidada."
        )

    col_conta = colunas['conta']
    col_data = colunas['data']
    col_valor = colunas['valor']
    col_lacto = colunas['lacto']
    col_hist = colunas['historico']
    col_doc = colunas['doc']
    col_tipo = colunas.get('tipo')

    colunas_saida = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
    principais, retirados = [], []

    for _, linha in df.iterrows():
        conta = re.sub(r'\D', '', texto_celula_seguro(linha[col_conta]))
        if conta != conta_normalizada:
            continue

        data_raw = linha[col_data]
        if isinstance(data_raw, (int, float)) and not pd.isna(data_raw):
            data = pd.to_datetime(data_raw, unit='D', origin='1899-12-30', errors='coerce')
        else:
            data = pd.to_datetime(data_raw, dayfirst=True, errors='coerce')
        if pd.isna(data):
            continue

        lacto_original = texto_celula_seguro(linha[col_lacto])
        lacto_normalizado = normalizar_texto(lacto_original).strip()
        lacto = re.sub(r'\bPAGAR\b', 'PAGO', lacto_original, flags=re.IGNORECASE)
        lacto = re.sub(
            r'\b(?:RECEBER|RECEBIMENTO)\b', 'RECEBIDO', lacto, flags=re.IGNORECASE
        )

        valor_raw = linha[col_valor]
        valor_original = (
            float(valor_raw)
            if isinstance(valor_raw, (int, float)) and not pd.isna(valor_raw)
            else limpar_valor_monetario(valor_raw)
        )
        if valor_original == 0:
            continue

        tipo_normalizado = normalizar_texto(texto_celula_seguro(linha[col_tipo])) if col_tipo else ''
        if lacto_normalizado.startswith(('pagar', 'pago')):
            valor = -abs(valor_original)
        elif lacto_normalizado.startswith(('receber', 'recebido', 'recebimento')):
            valor = abs(valor_original)
        elif 'debito' in tipo_normalizado:
            valor = -abs(valor_original)
        elif 'credito' in tipo_normalizado:
            valor = abs(valor_original)
        else:
            valor = valor_original

        historico_valor_original = linha[col_hist]
        historico_origem_exato = (
            '' if historico_valor_original is None or pd.isna(historico_valor_original)
            else limpar_caracteres_ilegais(str(historico_valor_original))
        )
        historico_origem = texto_celula_seguro(historico_valor_original)
        documento = texto_celula_seguro(linha[col_doc])
        historico_final = re.sub(r'\s+', ' ', " ".join(
            parte for parte in [lacto, historico_origem, documento] if parte
        )).strip()

        registro = {
            'DESCRIÇÃO': descricao_banco,
            'DATA': data.to_pydatetime(),
            'VALOR': valor,
            'DÉBITO': '',
            'CRÉDITO': '',
            'HISTÓRICO': historico_final
        }

        if identificar_estorno_de_baixa(lacto_original, historico_origem, documento):
            registro_retirado = dict(registro)
            registro_retirado['HISTÓRICO'] = historico_origem_exato
            registro_retirado['MOTIVO'] = 'Estorno de baixa identificado'
            retirados.append(registro_retirado)
        else:
            principais.append(registro)

    if not principais and not retirados:
        raise ValueError(f"Nenhum lançamento da conta {nome_aba} {conta_esperada} foi encontrado.")

    return pd.DataFrame(principais, columns=colunas_saida), pd.DataFrame(
        retirados, columns=colunas_saida + ['MOTIVO']
    )

def processar_nova_geracao_itau(file_bytes):
    return processar_nova_geracao_banco(
        file_bytes, 'Itaú', '99549-5', 'BANCO ITAÚ'
    )

def processar_nova_geracao_bradesco(file_bytes):
    return processar_nova_geracao_banco(
        file_bytes, 'Bradesco', '451990-6', 'BANCO BRADESCO'
    )

def processar_nova_geracao_fibra(file_bytes):
    return processar_nova_geracao_banco(
        file_bytes, 'Fibra', '673947-1', 'BANCO FIBRA'
    )

def filtrar_dataframe_periodo(df, data_inicial, data_final):
    """Mantém somente os lançamentos entre as datas informadas, inclusive."""
    if df is None or df.empty:
        return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    if 'DATA' not in df.columns:
        return df.iloc[0:0].copy()
    # Extratos brasileiros usam dia/mês/ano. Sem dayfirst=True, por exemplo,
    # 01/04/2026 seria interpretado como 4 de janeiro e sairia do filtro de abril.
    datas = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.date
    mascara = datas.between(data_inicial, data_final, inclusive='both')
    return df.loc[mascara].copy().reset_index(drop=True)

def identificar_chave_banco_empresa(valor):
    """Identifica os bancos da Nova Geração por descrição, aba ou conta."""
    texto = normalizar_texto(texto_celula_seguro(valor))
    digitos = re.sub(r'\D', '', texto_celula_seguro(valor))
    if 'itau' in texto or '995495' in digitos:
        return 'itau'
    if 'bradesco' in texto or '4519906' in digitos:
        return 'bradesco'
    if 'fibra' in texto or '6739471' in digitos:
        return 'fibra'
    return ''

def nome_banco_por_chave(chave):
    return {'itau': 'Itaú', 'bradesco': 'Bradesco', 'fibra': 'Fibra'}.get(chave, chave)

def ler_planilha_organizada_conferencia(file_bytes, banco_alvo):
    """Lê a planilha final e retorna somente o banco escolhido para conferência."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    colunas_base = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
    principais, retirados, bancos_encontrados = [], [], set()

    for nome_aba in xls.sheet_names:
        df_bruto = pd.read_excel(xls, sheet_name=nome_aba, header=None, dtype=object)
        if df_bruto.empty:
            continue

        indice_cabecalho = None
        for indice in range(min(len(df_bruto), 30)):
            nomes_linha = [
                normalizar_texto(texto_celula_seguro(valor)).strip()
                for valor in df_bruto.iloc[indice].tolist()
            ]
            if ('data' in nomes_linha and 'valor' in nomes_linha and
                    any(nome in nomes_linha for nome in ['historico', 'histórico'])):
                indice_cabecalho = indice
                break
        if indice_cabecalho is None:
            continue

        cabecalhos = [texto_celula_seguro(valor) for valor in df_bruto.iloc[indice_cabecalho]]
        df_aba = df_bruto.iloc[indice_cabecalho + 1:].copy()
        df_aba.columns = cabecalhos
        mapa = {normalizar_texto(str(coluna)).strip(): coluna for coluna in df_aba.columns}
        col_data = mapa.get('data')
        col_valor = mapa.get('valor')
        col_hist = mapa.get('historico')
        col_desc = mapa.get('descricao')
        col_motivo = mapa.get('motivo')
        if col_data is None or col_valor is None or col_hist is None:
            continue

        banco_aba = identificar_chave_banco_empresa(nome_aba)
        aba_retirados = 'retir' in normalizar_texto(nome_aba)
        for _, linha in df_aba.iterrows():
            banco_linha = (
                identificar_chave_banco_empresa(linha[col_desc]) if col_desc is not None else ''
            ) or banco_aba
            if banco_linha:
                bancos_encontrados.add(banco_linha)
            if banco_linha != banco_alvo:
                continue

            data_raw = linha[col_data]
            if isinstance(data_raw, (int, float)) and not pd.isna(data_raw):
                data = pd.to_datetime(data_raw, unit='D', origin='1899-12-30', errors='coerce')
            else:
                data = pd.to_datetime(data_raw, dayfirst=True, errors='coerce')
            valor = limpar_valor_monetario(linha[col_valor])
            if pd.isna(data) or valor == 0:
                continue

            descricao = texto_celula_seguro(linha[col_desc]) if col_desc is not None else ''
            if not descricao:
                descricao = {
                    'itau': 'BANCO ITAÚ', 'bradesco': 'BANCO BRADESCO', 'fibra': 'BANCO FIBRA'
                }[banco_alvo]
            historico_valor = linha[col_hist]
            historico = (
                '' if historico_valor is None or pd.isna(historico_valor)
                else limpar_caracteres_ilegais(str(historico_valor))
            )
            registro = {
                'DESCRIÇÃO': descricao,
                'DATA': data.to_pydatetime(),
                'VALOR': valor,
                'DÉBITO': '',
                'CRÉDITO': '',
                'HISTÓRICO': historico
            }
            if aba_retirados:
                registro['MOTIVO'] = (
                    texto_celula_seguro(linha[col_motivo]) if col_motivo is not None
                    else 'Estorno de baixa identificado'
                )
                retirados.append(registro)
            else:
                principais.append(registro)

    return (
        pd.DataFrame(principais, columns=colunas_base),
        pd.DataFrame(retirados, columns=colunas_base + ['MOTIVO']),
        [nome_banco_por_chave(chave) for chave in sorted(bancos_encontrados)]
    )

def gerar_excel_nova_geracao(dados_por_banco, modelo_bytes=None):
    """Gera um único arquivo com uma aba do Modelo Domínio para cada banco."""
    from openpyxl import Workbook, load_workbook

    if modelo_bytes:
        wb = load_workbook(io.BytesIO(modelo_bytes))
        ws_modelo = wb[wb.sheetnames[0]]
        if ws_modelo.max_row > 1:
            ws_modelo.delete_rows(2, ws_modelo.max_row - 1)
    else:
        wb = Workbook()
        ws_modelo = wb.active
        ws_modelo.title = 'Modelo temporário'
        ws_modelo.append(['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO'])

    cabecalhos = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
    for col, cabecalho in enumerate(cabecalhos, 1):
        ws_modelo.cell(1, col, cabecalho)

    def preparar_linha_modelo(registro, colunas):
        linha = []
        for coluna in colunas:
            valor = registro.get(coluna, '')
            if coluna == 'DATA':
                data = pd.to_datetime(valor, errors='coerce')
                valor = data.strftime('%d/%m/%Y') if not pd.isna(data) else ''
            elif pd.isna(valor):
                valor = ''
            linha.append(valor)
        return linha

    nomes_criados = []
    retirados_gerais = []
    for nome_banco, dados_banco in dados_por_banco.items():
        nome_aba = str(nome_banco)[:31]
        if nome_aba in nomes_criados:
            sufixo = 2
            while f"{nome_aba[:28]} {sufixo}" in nomes_criados:
                sufixo += 1
            nome_aba = f"{nome_aba[:28]} {sufixo}"

        ws_banco = wb.copy_worksheet(ws_modelo)
        ws_banco.title = nome_aba
        nomes_criados.append(nome_aba)

        df_principal = dados_banco.get('principal', pd.DataFrame())
        df_retirados = dados_banco.get('retirados', pd.DataFrame())
        for registro in df_principal.to_dict('records'):
            ws_banco.append(preparar_linha_modelo(registro, cabecalhos))
        if not df_retirados.empty:
            retirados_gerais.extend(df_retirados.to_dict('records'))

    wb.remove(ws_modelo)

    if retirados_gerais:
        nome_retirados = 'Lançamentos retirados'
        if nome_retirados in wb.sheetnames:
            del wb[nome_retirados]
        ws_ret = wb.create_sheet(nome_retirados)
        cabecalhos_ret = cabecalhos + ['MOTIVO']
        ws_ret.append(cabecalhos_ret)
        for registro in retirados_gerais:
            ws_ret.append(preparar_linha_modelo(registro, cabecalhos_ret))

    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()

def processar_extrato_conferencia_empresa(file_bytes, filename):
    """Lê o extrato usado na conferência com os mesmos motores do conversor."""
    extensao = os.path.splitext(filename)[1].lower()
    if extensao == '.ofx':
        return processar_ofx(file_bytes, filename)
    if extensao in ['.csv', '.xlsx', '.xls']:
        return processar_planilha_universal(file_bytes, filename)
    if extensao == '.pdf':
        caminho_temporario = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temporario:
                temporario.write(file_bytes)
                caminho_temporario = temporario.name
            return processar_arquivo_pdf(caminho_temporario, filename)
        finally:
            if caminho_temporario and os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)
    return []

def conciliar_empresa_com_extrato(df_planilha, lancamentos_extrato, df_retirados=None):
    """Compara movimentos por dia e faz pareamento individual por data e centavos."""
    colunas_base = ['DESCRIÇÃO', 'DATA', 'VALOR', 'HISTÓRICO']

    def preparar_dataframe(dados):
        if isinstance(dados, pd.DataFrame):
            df = dados.copy()
        else:
            df = pd.DataFrame(dados or [])
        for coluna in colunas_base:
            if coluna not in df.columns:
                df[coluna] = '' if coluna != 'VALOR' else 0.0
        df['DESCRIÇÃO'] = df['DESCRIÇÃO'].fillna('').astype(str)
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.normalize()
        df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0.0).round(2)
        df['HISTÓRICO'] = df['HISTÓRICO'].fillna('').astype(str)
        df = df.dropna(subset=['DATA'])
        df = df[df['VALOR'].abs() >= 0.005].copy()
        df['_CENTAVOS'] = (df['VALOR'] * 100).round().astype(int)
        df['_BANCO'] = df['DESCRIÇÃO'].apply(
            lambda valor: re.sub(r'\s+', ' ', normalizar_texto(valor).replace('banco', '')).strip()
        )
        return df.reset_index(drop=True)

    df_modelo = preparar_dataframe(df_planilha)
    df_extrato = preparar_dataframe(lancamentos_extrato)
    df_retirados_ok = preparar_dataframe(df_retirados if df_retirados is not None else [])

    usar_banco_na_chave = df_modelo.loc[df_modelo['_BANCO'] != '', '_BANCO'].nunique() > 1
    for dataframe in [df_modelo, df_extrato, df_retirados_ok]:
        if usar_banco_na_chave:
            dataframe['_CHAVE'] = list(zip(
                dataframe['_BANCO'], dataframe['DATA'], dataframe['_CENTAVOS']
            ))
        else:
            dataframe['_CHAVE'] = list(zip(dataframe['DATA'], dataframe['_CENTAVOS']))

    # Estornos de baixa retirados de propósito não devem gerar falso alerta.
    indices_ignorados = set()
    if not df_retirados_ok.empty and not df_extrato.empty:
        quantidades_retiradas = df_retirados_ok['_CHAVE'].value_counts().to_dict()
        for chave, quantidade in quantidades_retiradas.items():
            candidatos = df_extrato.index[
                (df_extrato['_CHAVE'] == chave) &
                df_extrato['HISTÓRICO'].apply(identificar_estorno_de_baixa)
            ].tolist()
            indices_ignorados.update(candidatos[:int(quantidade)])

    df_ignorados = df_extrato.loc[sorted(indices_ignorados)].copy() if indices_ignorados else df_extrato.iloc[0:0].copy()
    df_extrato_comparavel = df_extrato.drop(index=list(indices_ignorados)).reset_index(drop=True)

    # Pareamento um a um: lançamentos repetidos são tratados individualmente.
    disponiveis_modelo = {}
    for indice, chave in enumerate(df_modelo['_CHAVE']):
        disponiveis_modelo.setdefault(chave, []).append(indice)

    indices_modelo_pareados = set()
    indices_extrato_sem_par = []
    for indice_extrato, chave in enumerate(df_extrato_comparavel['_CHAVE']):
        candidatos = disponiveis_modelo.get(chave, [])
        if candidatos:
            indices_modelo_pareados.add(candidatos.pop(0))
        else:
            indices_extrato_sem_par.append(indice_extrato)

    indices_modelo_sem_par = [
        indice for indice in range(len(df_modelo))
        if indice not in indices_modelo_pareados
    ]

    faltando_planilha = df_extrato_comparavel.loc[indices_extrato_sem_par, colunas_base].copy()
    a_mais_planilha = df_modelo.loc[indices_modelo_sem_par, colunas_base].copy()
    ignorados = df_ignorados[colunas_base].copy()

    total_modelo = df_modelo.groupby('DATA')['VALOR'].sum().rename('TOTAL PLANILHA')
    total_extrato = df_extrato_comparavel.groupby('DATA')['VALOR'].sum().rename('TOTAL EXTRATO')
    diario = pd.concat([total_extrato, total_modelo], axis=1).fillna(0.0).sort_index().reset_index()
    diario['DIFERENÇA DO DIA'] = (diario['TOTAL PLANILHA'] - diario['TOTAL EXTRATO']).round(2)
    diario['ACUMULADO EXTRATO'] = diario['TOTAL EXTRATO'].cumsum().round(2)
    diario['ACUMULADO PLANILHA'] = diario['TOTAL PLANILHA'].cumsum().round(2)
    diario['DIFERENÇA ACUMULADA'] = (
        diario['ACUMULADO PLANILHA'] - diario['ACUMULADO EXTRATO']
    ).round(2)
    diario['STATUS'] = diario['DIFERENÇA DO DIA'].apply(
        lambda valor: '✅ Batendo' if abs(valor) < 0.01 else '❌ Divergente'
    )

    return diario, faltando_planilha, a_mais_planilha, ignorados

# ==============================================================================
# CONTROLE DE ESTADO DE NAVEGAÇÃO
# ==============================================================================
if 'pagina_ativa' not in st.session_state: st.session_state['pagina_ativa'] = 'home'
def mudar_pagina(nome_pagina): st.session_state['pagina_ativa'] = nome_pagina

# ==============================================================================
# BARRA LATERAL DARK MINIMALISTA
# ==============================================================================
st.sidebar.markdown("<p style='font-size: 14px; font-weight: 600; color: #f0f6fc; margin-bottom: 0px;'>Hub Contábil</p>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; color: #8b949e; margin-top: 2px;'>Domínio Systems</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.sidebar.button("Início", use_container_width=True, key="sb_home"): mudar_pagina('home')
if st.sidebar.button("Conversor de Extratos", use_container_width=True, key="sb_extratos"): mudar_pagina('extratos')
if st.sidebar.button("Conciliação com Razão", use_container_width=True, key="sb_razao"): mudar_pagina('razao')
if st.sidebar.button("Organizador de Planilhas", use_container_width=True, key="sb_organizador"): mudar_pagina('organizador')
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 10px; color: #8b949e; text-align: center;'>v11.7 · Clear View</p>", unsafe_allow_html=True)

# ==============================================================================
# TELA 1: MENU PRINCIPAL (HOME)
# ==============================================================================
if st.session_state['pagina_ativa'] == 'home':
    st.title("Início")
    st.caption("Selecione uma ferramenta abaixo para começar.")
    st.markdown("<br>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">📊</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Conversor de Extratos</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Converta extratos para o formato de importação da Domínio.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_extratos"):
            mudar_pagina('extratos')
            st.rerun()
            
    with col_t2:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">🔍</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Conciliação com Razão</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Análise automatizada, rolagem de saldos e auditoria de divergências.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_razao"):
            mudar_pagina('razao')
            st.rerun()
        
    with col_t3:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">🗂️</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Organizador de Planilhas</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Converta planilhas específicas de empresas para o Modelo Domínio.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Acessar", use_container_width=True, key="btn_abrir_organizador"):
            mudar_pagina('organizador')
            st.rerun()

# ==============================================================================
# TELA 2: FERRAMENTA DE CONVERSÃO DE EXTRATOS
# ==============================================================================
elif st.session_state['pagina_ativa'] == 'extratos':
    col_voltar, col_tit = st.columns([1.2, 8.8])
    with col_voltar:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True, key="btn_voltar_home"):
            mudar_pagina('home')
            st.rerun()
    with col_tit: st.title("Conversor de Extratos Bancários")
    st.caption("Faça o upload dos arquivos para gerar os layouts compatíveis com a Domínio.")
    st.markdown("---")

    arquivos = st.file_uploader("Selecione os extratos (PDF, OFX, CSV, Excel)", type=["pdf", "ofx", "csv", "xlsx", "xls"], accept_multiple_files=True)

    if arquivos:
        try:
            colunas_dominio = ['DESCRIÇÃO', 'DATA', 'VALOR', 'DÉBITO', 'CRÉDITO', 'HISTÓRICO']
            df_modelo = pd.read_excel("Modelo dominio.xlsx") if os.path.exists("Modelo dominio.xlsx") else pd.DataFrame(columns=colunas_dominio)
            if 'DESCRIÇÃO' not in df_modelo.columns: df_modelo = pd.DataFrame(columns=colunas_dominio)
            
            dados_por_arquivo, todos_lancamentos_brutos = {}, []
            for arquivo in arquivos:
                file_bytes, extensao = arquivo.getvalue(), os.path.splitext(arquivo.name)[1].lower()
                lancamentos, data_ini_doc, data_fim_doc = [], None, None
                
                if extensao == '.ofx': lancamentos = processar_ofx(file_bytes, arquivo.name)
                elif extensao in ['.csv', '.xlsx', '.xls']: lancamentos = processar_planilha_universal(file_bytes, arquivo.name)
                elif extensao == '.pdf':
                    caminho_temp = f"temp_{arquivo.name}"
                    with open(caminho_temp, "wb") as f: f.write(file_bytes)
                    data_ini_doc, data_fim_doc = extrair_periodo_extrato(caminho_temp)
                    lancamentos = processar_arquivo_pdf(caminho_temp)
                    if os.path.exists(caminho_temp): os.remove(caminho_temp)
                    
                if lancamentos:
                    df_temp = pd.DataFrame(lancamentos)
                    df_temp['ARQUIVO_ORIGEM'] = arquivo.name
                    dados_por_arquivo[arquivo.name] = {'lancamentos': lancamentos, 'data_ini': data_ini_doc, 'data_fim': data_fim_doc}
                    todos_lancamentos_brutos.extend(lancamentos)

            if todos_lancamentos_brutos:
                nomes_abas = ["Visão Consolidada"] + [arq.name for arq in arquivos if arq.name in dados_por_arquivo] if len(arquivos) > 1 else [arq.name for arq in arquivos if arq.name in dados_por_arquivo]
                abas = st.tabs(nomes_abas)
                
                if len(arquivos) > 1:
                    with abas[0]:
                        st.markdown("### Resumo Consolidado")
                        df_geral_bruto = pd.DataFrame(todos_lancamentos_brutos)
                        df_geral_bruto['DATA_DT'] = pd.to_datetime(df_geral_bruto['DATA'], dayfirst=True, errors='coerce')
                        df_geral_bruto = df_geral_bruto.dropna(subset=['DATA_DT'])
                        
                        if df_geral_bruto.empty:
                            st.warning("Nenhum lançamento válido encontrado.")
                        else:
                            dt_min_geral, dt_max_geral = df_geral_bruto['DATA_DT'].min().date(), df_geral_bruto['DATA_DT'].max().date()
                            col_g1, col_g2, col_g3 = st.columns([1, 1, 1.5])
                            with col_g1: data_geral_ini = st.date_input("Data Inicial", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_ini")
                            with col_g2: data_geral_fim = st.date_input("Data Final", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="gen_fim")
                            with col_g3: 
                                st.markdown("<label style='font-size:14px; font-weight:400; color:inherit;'>Busca rápida</label>", unsafe_allow_html=True)
                                termo_busca_geral = st.text_input("Busca rápida", placeholder="Filtrar histórico...", label_visibility="collapsed", key="gen_busca")
                            
                            df_geral_final = df_geral_bruto[(df_geral_bruto['DATA_DT'].dt.date >= data_geral_ini) & (df_geral_bruto['DATA_DT'].dt.date <= data_geral_fim)].copy()
                            if termo_busca_geral: df_geral_final = df_geral_final[df_geral_final['HISTÓRICO'].str.contains(termo_busca_geral, case=False, na=False)]
                            
                            df_geral_final = df_geral_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                            df_geral_final = sanitizar_dataframe(df_geral_final)
                            
                            tot_cred_g, tot_deb_g = df_geral_final[df_geral_final['VALOR'] > 0]['VALOR'].sum(), df_geral_final[df_geral_final['VALOR'] < 0]['VALOR'].sum()
                            saldo_liq_g = tot_cred_g + tot_deb_g
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            cg1, cg2, cg3, cg4 = st.columns(4)
                            with cg1: st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_geral_final)}</div></div>', unsafe_allow_html=True)
                            with cg2: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_cred_g)}</div></div>', unsafe_allow_html=True)
                            with cg3: st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_deb_g))}</div></div>', unsafe_allow_html=True)
                            with cg4:
                                color_g = "#3fb950" if saldo_liq_g >= 0 else "#f85149"
                                st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_g};">{formatar_moeda(saldo_liq_g)}</div></div>', unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True); st.markdown("##### Prévia Consolidada")
                            st.dataframe(formatar_dataframe_moeda_br(df_geral_final, ['VALOR']), use_container_width=True, height=280)
                            
                            st.markdown("##### Exportar")
                            cc_dl1, cc_dl2 = st.columns(2)
                            buf_excel_g = io.BytesIO()
                            with pd.ExcelWriter(buf_excel_g, engine='openpyxl') as writer: df_geral_final.to_excel(writer, index=False)
                            cc_dl1.download_button("Baixar Excel (.XLSX)", data=buf_excel_g.getvalue(), file_name=f"consolidado_geral_{data_geral_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_excel_geral", use_container_width=True)
                            cc_dl2.download_button("Baixar TXT para Domínio", data=gerar_txt_dominio(df_geral_final), file_name=f"importacao_dominio_consolidado_{data_geral_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key="dl_txt_geral", use_container_width=True)

                offset_abas = 1 if len(arquivos) > 1 else 0
                for idx_arq, arquivo in enumerate(arquivos):
                    if arquivo.name not in dados_por_arquivo: continue
                    with abas[idx_arq + offset_abas]:
                        info_arq = dados_por_arquivo[arquivo.name]
                        df_bruto = pd.DataFrame(info_arq['lancamentos'])
                        df_bruto['DATA_DT'] = pd.to_datetime(df_bruto['DATA'], dayfirst=True, errors='coerce')
                        df_bruto = df_bruto.dropna(subset=['DATA_DT'])
                        
                        if df_bruto.empty:
                            st.warning("Não há dados válidos neste arquivo.")
                            continue
                            
                        dt_min_dataset, dt_max_dataset = df_bruto['DATA_DT'].min().date(), df_bruto['DATA_DT'].max().date()
                        
                        data_ini_doc, data_fim_doc = info_arq['data_ini'], info_arq['data_fim']
                        val_ini_def = max(min(data_ini_doc.date(), dt_max_dataset), dt_min_dataset) if data_ini_doc and data_ini_doc.date() else dt_min_dataset
                        val_fim_def = max(min(data_fim_doc.date(), dt_max_dataset), dt_min_dataset) if data_fim_doc and data_fim_doc.date() else dt_max_dataset
                        if val_ini_def > val_fim_def: val_ini_def, val_fim_def = dt_min_dataset, dt_max_dataset
                        
                        with st.container():
                            col_f1, col_f2, col_f3 = st.columns([1, 1, 1.5])
                            with col_f1: data_sel_ini = st.date_input("Data Inicial", value=val_ini_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"ini_{idx_arq}")
                            with col_f2: data_sel_fim = st.date_input("Data Final", value=val_fim_def, min_value=dt_min_dataset, max_value=dt_max_dataset, format="DD/MM/YYYY", key=f"fim_{idx_arq}")
                            with col_f3: 
                                st.markdown("<label style='font-size:14px; font-weight:400; color:inherit;'>Busca rápida</label>", unsafe_allow_html=True)
                                termo_busca = st.text_input("Busca rápida", placeholder="Digite para filtrar...", label_visibility="collapsed", key=f"busca_{idx_arq}")

                        df_final = df_bruto[(df_bruto['DATA_DT'].dt.date >= data_sel_ini) & (df_bruto['DATA_DT'].dt.date <= data_sel_fim)].copy()
                        if termo_busca: df_final = df_final[df_final['HISTÓRICO'].str.contains(termo_busca, case=False, na=False)]
                        
                        df_final = df_final.drop(columns=['DATA_DT', 'ARQUIVO_ORIGEM'], errors='ignore')[df_modelo.columns]
                        df_final = sanitizar_dataframe(df_final)

                        total_creditos, total_debitos = df_final[df_final['VALOR'] > 0]['VALOR'].sum(), df_final[df_final['VALOR'] < 0]['VALOR'].sum()
                        saldo_liquido = total_creditos + total_debitos
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">Registros</div><div class="metric-value">{len(df_final)}</div></div>', unsafe_allow_html=True)
                        with c2: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(total_creditos)}</div></div>', unsafe_allow_html=True)
                        with c3: st.markdown(f'<div class="metric-card"><div class="metric-title">Saídas</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(total_debitos))}</div></div>', unsafe_allow_html=True)
                        with c4:
                            color_liq = "#3fb950" if saldo_liquido >= 0 else "#f85149"
                            st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo Líquido</div><div class="metric-value" style="color: {color_liq};">{formatar_moeda(saldo_liquido)}</div></div>', unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True); st.markdown("##### Prévia dos Lançamentos")
                        st.dataframe(formatar_dataframe_moeda_br(df_final, ['VALOR']), use_container_width=True, height=280)
                        
                        st.markdown("##### Exportar")
                        c_dl1, c_dl2 = st.columns(2)
                        buffer_excel = io.BytesIO()
                        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer: df_final.to_excel(writer, index=False)
                        c_dl1.download_button("Baixar Excel (.XLSX)", data=buffer_excel.getvalue(), file_name=f"lancamentos_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{idx_arq}", use_container_width=True)
                        c_dl2.download_button("Baixar TXT para Domínio", data=gerar_txt_dominio(df_final), file_name=f"importacao_dominio_{os.path.splitext(arquivo.name)[0]}_{data_sel_ini.strftime('%d%m%Y')}.txt", mime="text/plain", key=f"txt_{idx_arq}", use_container_width=True)
        except Exception as e:
            st.error(f"🛑 Ocorreu um erro na aba extratos. Detalhes: {e}")

# ==============================================================================
# TELA 3: ORGANIZADOR DE PLANILHAS POR EMPRESA
# ==============================================================================
elif st.session_state['pagina_ativa'] == 'organizador':
    col_voltar, col_tit = st.columns([1.2, 8.8])
    with col_voltar:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True, key="btn_voltar_home_org"):
            mudar_pagina('home')
            st.rerun()
    with col_tit: st.title("Organizador de Planilhas")
    st.caption("Selecione a empresa e aplique as regras específicas para gerar o Modelo Domínio.")
    st.markdown("---")

    if 'empresa_organizador' not in st.session_state:
        st.session_state['empresa_organizador'] = None

    st.markdown("##### Selecione a empresa")
    col_emp1, col_emp2 = st.columns(2)
    with col_emp1:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">🏢</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Nova Geração</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">Organização dos movimentos bancários da matriz.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("Selecionar Nova Geração", use_container_width=True, key="org_nova_geracao"):
            st.session_state['empresa_organizador'] = 'nova_geracao'
            st.rerun()
    with col_emp2:
        st.markdown("""<div class="tool-card"><p style="font-size: 20px; margin-bottom: 8px;">🏢</p><p style="font-weight: 600; color: #f0f6fc; margin-bottom: 4px; font-size: 15px;">Segunda Empresa</p><p style="font-size: 12px; color: #8b949e; line-height: 1.4;">As regras serão configuradas na próxima etapa.</p></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.button("Em breve", use_container_width=True, disabled=True, key="org_empresa_2")

    if st.session_state['empresa_organizador'] == 'nova_geracao':
        st.markdown("---")
        st.markdown("### Nova Geração")
        url_base_classificacao, chave_base_classificacao, senha_admin_classificacao = (
            obter_config_classificacao_online()
        )
        base_classificacoes = []
        erro_base_classificacoes = ''
        if url_base_classificacao and chave_base_classificacao:
            try:
                base_classificacoes = carregar_classificacoes_online()
            except Exception as erro_base:
                erro_base_classificacoes = str(erro_base)

        with st.expander("Base inteligente de Débito e Crédito"):
            if erro_base_classificacoes:
                st.error(erro_base_classificacoes)
            elif url_base_classificacao and chave_base_classificacao:
                st.success(
                    f"Base online conectada: {len(base_classificacoes)} padrões disponíveis."
                )
            else:
                st.warning(
                    "A base online ainda não foi configurada com os valores reais nos Secrets "
                    "do Streamlit. Substitua URL_DO_PROJETO_SUPABASE e SERVICE_ROLE_KEY pelos "
                    "dados do seu projeto Supabase. "
                    "A organização continuará funcionando, mas sem preencher Débito e Crédito."
                )
            st.caption(
                "Importe planilhas já classificadas. Pode enviar arquivos separados, uma planilha "
                "com vários bancos ou arquivos ZIP. Reimportar o mesmo conteúdo não cria duplicidades."
            )
            arquivos_aprendizado = st.file_uploader(
                "Planilhas classificadas para ensinar o sistema",
                type=['xlsx', 'xls', 'zip'],
                accept_multiple_files=True,
                key='org_base_classificada_nova'
            )
            senha_aprendizado = st.text_input(
                "Senha administrativa para atualizar a base",
                type='password',
                key='org_senha_base_classificada_nova'
            )
            if st.button(
                "Importar classificações",
                key='org_importar_base_classificada_nova',
                use_container_width=True
            ):
                if not url_base_classificacao or not chave_base_classificacao:
                    st.error("Configure primeiro a conexão da base online nos Secrets do Streamlit.")
                elif not senha_admin_classificacao:
                    st.error("Configure a senha administrativa nos Secrets do Streamlit.")
                elif not hmac.compare_digest(senha_aprendizado, senha_admin_classificacao):
                    st.error("Senha administrativa incorreta.")
                elif not arquivos_aprendizado:
                    st.warning("Envie pelo menos uma planilha classificada ou arquivo ZIP.")
                else:
                    try:
                        novos_registros = importar_arquivos_classificados(arquivos_aprendizado)
                        quantidade_salva = salvar_classificacoes_online(novos_registros)
                        st.success(
                            f"Base atualizada com {quantidade_salva} padrões de classificação."
                        )
                        st.rerun()
                    except Exception as erro_importacao:
                        st.error(f"Não foi possível atualizar a base: {erro_importacao}")

            st.markdown("---")
            st.markdown("#### Classificar planilha final conciliada")
            st.caption(
                "Anexe somente a planilha final, depois que a conferência bancária estiver "
                "concluída e os saldos estiverem batendo. O arquivo original não será alterado."
            )
            planilha_final_classificacao = st.file_uploader(
                "Planilha final com os saldos conferidos",
                type=['xlsx'],
                key='org_planilha_final_classificacao_nova'
            )
            if planilha_final_classificacao:
                if erro_base_classificacoes:
                    st.error("A base online precisa estar conectada antes da classificação.")
                elif not base_classificacoes:
                    st.warning(
                        "A base ainda não possui padrões. Importe primeiro as planilhas dos "
                        "meses já classificados."
                    )
                else:
                    try:
                        arquivo_classificado, resumo_classificacao = classificar_planilha_final(
                            planilha_final_classificacao.getvalue(),
                            planilha_final_classificacao.name,
                            base_classificacoes
                        )
                        c_auto, c_pendente, c_conflito = st.columns(3)
                        with c_auto:
                            st.metric(
                                "Classificados automaticamente",
                                resumo_classificacao['automaticos']
                            )
                        with c_pendente:
                            st.metric(
                                "Permaneceram em branco",
                                resumo_classificacao['padroes_novos']
                                + resumo_classificacao['banco_nao_identificado']
                            )
                        with c_conflito:
                            st.metric(
                                "Conflitos para revisão",
                                resumo_classificacao['conflitos']
                            )
                        if resumo_classificacao['automaticos']:
                            st.success(
                                "Classificação concluída. As abas, os valores e a formatação "
                                "da planilha final foram preservados."
                            )
                        else:
                            st.info(
                                "Nenhum padrão seguro foi encontrado para preenchimento automático."
                            )
                        nome_base_saida = os.path.splitext(
                            planilha_final_classificacao.name
                        )[0]
                        st.download_button(
                            "Baixar planilha final classificada",
                            data=arquivo_classificado,
                            file_name=f"{nome_base_saida}_Classificada.xlsx",
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            key='org_download_planilha_final_classificada_nova',
                            use_container_width=True
                        )
                    except Exception as erro_classificacao_final:
                        st.error(
                            "Não foi possível classificar a planilha final: "
                            f"{erro_classificacao_final}"
                        )

        configuracoes_bancos = {
            "Itaú - Conta 99549-5": {
                "nome": "Itaú", "conta": "99549-5", "slug": "itau",
                "processador": processar_nova_geracao_itau
            },
            "Bradesco - Conta 451990-6": {
                "nome": "Bradesco", "conta": "451990-6", "slug": "bradesco",
                "processador": processar_nova_geracao_bradesco
            },
            "Fibra - Conta 673947-1": {
                "nome": "Fibra", "conta": "673947-1", "slug": "fibra",
                "processador": processar_nova_geracao_fibra
            }
        }
        bancos_empresa = st.multiselect(
            "Bancos",
            list(configuracoes_bancos.keys()),
            default=["Itaú - Conta 99549-5"],
            key="org_banco_nova_geracao"
        )
        if not bancos_empresa:
            st.info("Selecione pelo menos um banco para continuar.")
            st.stop()

        configs_selecionadas = [configuracoes_bancos[banco] for banco in bancos_empresa]
        nomes_bancos = ", ".join(config['nome'] for config in configs_selecionadas)
        st.caption(
            f"O sistema localizará automaticamente as contas de {nomes_bancos} dentro da "
            "planilha consolidada pelas colunas CONTA, DATA, VALOR, LACTO, HISTORICO e DOC."
        )
        arquivo_empresa = st.file_uploader(
            "Envie a planilha bancária da Nova Geração",
            type=["xlsx", "xls"],
            key="org_upload_nova_geracao_multibanco"
        )

        if arquivo_empresa:
            try:
                bytes_empresa = arquivo_empresa.getvalue()
                dados_processados = []
                for config in configs_selecionadas:
                    df_banco, df_banco_retirados = config['processador'](bytes_empresa)
                    dados_processados.append((config, df_banco, df_banco_retirados))

                datas_disponiveis = pd.concat(
                    [dados[1][['DATA']] for dados in dados_processados if not dados[1].empty],
                    ignore_index=True
                )
                datas_disponiveis['DATA'] = pd.to_datetime(
                    datas_disponiveis['DATA'], errors='coerce'
                )
                datas_disponiveis = datas_disponiveis.dropna(subset=['DATA'])
                if datas_disponiveis.empty:
                    raise ValueError("Nenhuma data válida foi encontrada nos bancos selecionados.")

                data_minima = datas_disponiveis['DATA'].min().date()
                data_maxima = datas_disponiveis['DATA'].max().date()
                chave_periodo = (
                    f"org_periodo_nova_{data_minima.isoformat()}_{data_maxima.isoformat()}_"
                    + "_".join(config['slug'] for config in configs_selecionadas)
                )
                st.markdown("### Período dos lançamentos")
                periodo_selecionado = st.date_input(
                    "Selecione a data inicial e a data final",
                    value=(data_minima, data_maxima),
                    min_value=data_minima,
                    max_value=data_maxima,
                    format="DD/MM/YYYY",
                    key=chave_periodo
                )
                if not isinstance(periodo_selecionado, (tuple, list)) or len(periodo_selecionado) != 2:
                    st.info("Selecione também a data final para concluir o período.")
                    st.stop()
                data_inicial, data_final = periodo_selecionado
                if data_inicial > data_final:
                    st.error("A data inicial não pode ser maior que a data final.")
                    st.stop()

                st.caption(
                    f"Serão considerados os lançamentos de {data_inicial.strftime('%d/%m/%Y')} "
                    f"até {data_final.strftime('%d/%m/%Y')}."
                )

                modelos_por_banco, retirados_por_banco = [], []
                dados_exportacao_por_banco = {}
                for config, df_banco_completo, df_banco_retirados_completo in dados_processados:
                    df_banco = filtrar_dataframe_periodo(
                        df_banco_completo, data_inicial, data_final
                    )
                    df_banco_retirados = filtrar_dataframe_periodo(
                        df_banco_retirados_completo, data_inicial, data_final
                    )
                    modelos_por_banco.append(df_banco)
                    retirados_por_banco.append(df_banco_retirados)
                    dados_exportacao_por_banco[config['nome']] = {
                        'principal': df_banco.sort_values('DATA', kind='stable').reset_index(drop=True),
                        'retirados': df_banco_retirados.sort_values('DATA', kind='stable').reset_index(drop=True)
                        if not df_banco_retirados.empty else df_banco_retirados
                    }

                df_org = pd.concat(modelos_por_banco, ignore_index=True)
                if df_org.empty:
                    st.warning("Nenhum lançamento foi encontrado no período selecionado.")
                    st.stop()
                df_org = df_org.sort_values(
                    ['DATA', 'DESCRIÇÃO'], kind='stable'
                ).reset_index(drop=True)
                df_retirados = pd.concat(retirados_por_banco, ignore_index=True)
                if not df_retirados.empty:
                    df_retirados = df_retirados.sort_values(
                        ['DATA', 'DESCRIÇÃO'], kind='stable'
                    ).reset_index(drop=True)
                modelo_org_bytes = None
                for caminho_modelo in ['Modelo dominio.xlsx', 'Modelo dominio(6).xlsx']:
                    if os.path.exists(caminho_modelo):
                        with open(caminho_modelo, 'rb') as arquivo_modelo:
                            modelo_org_bytes = arquivo_modelo.read()
                        break
                arquivo_final = gerar_excel_nova_geracao(
                    dados_exportacao_por_banco, modelo_org_bytes
                )

                total_entradas = df_org.loc[df_org['VALOR'] > 0, 'VALOR'].sum()
                total_saidas = df_org.loc[df_org['VALOR'] < 0, 'VALOR'].sum()
                saldo_liquido = total_entradas + total_saidas

                st.markdown("<br>", unsafe_allow_html=True)
                m1, m2, m3, m4 = st.columns(4)
                with m1: st.markdown(f'<div class="metric-card"><div class="metric-title">Modelo principal</div><div class="metric-value">{len(df_org)}</div></div>', unsafe_allow_html=True)
                with m2: st.markdown(f'<div class="metric-card"><div class="metric-title">Retirados</div><div class="metric-value">{len(df_retirados)}</div></div>', unsafe_allow_html=True)
                with m3: st.markdown(f'<div class="metric-card"><div class="metric-title">Entradas</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(total_entradas)}</div></div>', unsafe_allow_html=True)
                with m4:
                    cor_saldo = "#3fb950" if saldo_liquido >= 0 else "#f85149"
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Saldo líquido</div><div class="metric-value" style="color: {cor_saldo};">{formatar_moeda(saldo_liquido)}</div></div>', unsafe_allow_html=True)

                tab_principal, tab_retirados = st.tabs(["Modelo principal", "Lançamentos retirados"])
                with tab_principal:
                    previa = df_org.copy()
                    previa['DATA'] = pd.to_datetime(previa['DATA']).dt.strftime('%d/%m/%Y')
                    st.dataframe(formatar_dataframe_moeda_br(previa, ['VALOR']), use_container_width=True, height=320)
                with tab_retirados:
                    if df_retirados.empty:
                        st.info("Nenhum estorno de baixa foi identificado neste arquivo.")
                    else:
                        previa_ret = df_retirados.copy()
                        previa_ret['DATA'] = pd.to_datetime(previa_ret['DATA']).dt.strftime('%d/%m/%Y')
                        st.dataframe(formatar_dataframe_moeda_br(previa_ret, ['VALOR']), use_container_width=True, height=280)

                nome_saida_banco = (
                    configs_selecionadas[0]['nome']
                    if len(configs_selecionadas) == 1
                    else f"Separado_{len(configs_selecionadas)}_Bancos"
                )
                st.download_button(
                    "Baixar Modelo Domínio com abas por banco (.XLSX)",
                    data=arquivo_final,
                    file_name=(
                        f"Nova_Geracao_{nome_saida_banco}_"
                        f"{data_inicial.strftime('%d%m%Y')}_a_{data_final.strftime('%d%m%Y')}_"
                        "Modelo_Dominio.xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_org_nova_multibanco",
                    use_container_width=True
                )

                st.markdown("---")
                st.markdown("### Conferência com o extrato bancário")
                nomes_disponiveis_conferencia = [
                    config['nome'] for config in configs_selecionadas
                ]
                chave_grupo_conferencia = "_".join(
                    config['slug'] for config in configs_selecionadas
                )
                conferir_todos_bancos = st.checkbox(
                    "Conferir todos os bancos disponíveis",
                    value=False,
                    key=f"org_conferir_todos_nova_{chave_grupo_conferencia}",
                    disabled=len(nomes_disponiveis_conferencia) == 1
                )
                if conferir_todos_bancos:
                    bancos_conferencia = nomes_disponiveis_conferencia
                    st.caption("Todos os bancos disponíveis serão analisados separadamente.")
                else:
                    bancos_conferencia = st.multiselect(
                        "Bancos que serão conferidos",
                        nomes_disponiveis_conferencia,
                        default=nomes_disponiveis_conferencia[:1],
                        key=f"org_bancos_conferencia_nova_{chave_grupo_conferencia}",
                        help="Selecione um ou vários bancos disponíveis."
                    )
                if not bancos_conferencia:
                    st.info("Selecione pelo menos um banco para realizar a conferência.")
                    st.stop()

                configs_conferencia = [
                    config for config in configs_selecionadas
                    if config['nome'] in bancos_conferencia
                ]
                dados_conferencia_por_banco = {}

                planilha_atualizada_conferencia = st.file_uploader(
                    "Planilha organizada atualizada para conferência (opcional)",
                    type=["xlsx", "xls"],
                    key="org_planilha_atualizada_conferencia_nova",
                    help=(
                        "Você pode anexar a planilha final com os três bancos. "
                        "O sistema separará somente os bancos escolhidos acima."
                    )
                )
                if planilha_atualizada_conferencia:
                    try:
                        bancos_detectados_geral = set()
                        for config in configs_conferencia:
                            df_atualizada, df_retirados_atualizada, bancos_detectados = (
                                ler_planilha_organizada_conferencia(
                                    planilha_atualizada_conferencia.getvalue(),
                                    config['slug']
                                )
                            )
                            bancos_detectados_geral.update(bancos_detectados)
                            dados_conferencia_por_banco[config['slug']] = {
                                'modelo': filtrar_dataframe_periodo(
                                    df_atualizada, data_inicial, data_final
                                ),
                                'retirados': filtrar_dataframe_periodo(
                                    df_retirados_atualizada, data_inicial, data_final
                                )
                            }
                        bancos_sem_dados = [
                            config['nome'] for config in configs_conferencia
                            if dados_conferencia_por_banco[config['slug']]['modelo'].empty
                        ]
                        if len(bancos_sem_dados) == len(configs_conferencia):
                            st.error("A planilha atualizada não possui lançamentos dos bancos selecionados no período.")
                            st.stop()
                        if bancos_sem_dados:
                            st.warning(
                                "Sem lançamentos na planilha atualizada para: "
                                + ", ".join(bancos_sem_dados)
                            )
                        bancos_texto = (
                            ", ".join(sorted(bancos_detectados_geral))
                            if bancos_detectados_geral else "não identificados"
                        )
                        st.success(
                            f"Planilha atualizada carregada. Bancos identificados: {bancos_texto}."
                        )
                    except Exception as erro_planilha_atualizada:
                        st.error(f"Não foi possível ler a planilha organizada atualizada: {erro_planilha_atualizada}")
                        st.stop()
                else:
                    for config in configs_conferencia:
                        chave = config['slug']
                        dados_conferencia_por_banco[chave] = {
                            'modelo': df_org[
                                df_org['DESCRIÇÃO'].apply(
                                    identificar_chave_banco_empresa
                                ).eq(chave)
                            ].copy().reset_index(drop=True),
                            'retirados': df_retirados[
                                df_retirados['DESCRIÇÃO'].apply(
                                    identificar_chave_banco_empresa
                                ).eq(chave)
                            ].copy().reset_index(drop=True)
                            if not df_retirados.empty else df_retirados.copy()
                        }

                st.caption(
                    "Anexe os extratos correspondentes aos bancos escolhidos. "
                    "Será criado um relatório diário separado para cada banco."
                )
                extratos_conferencia = st.file_uploader(
                    "Envie o(s) extrato(s) bancário(s) para conferência",
                    type=["pdf", "ofx", "csv", "xlsx", "xls"],
                    accept_multiple_files=True,
                    key=(
                        "org_extratos_conferencia_nova_"
                        + "_".join(config['slug'] for config in configs_conferencia)
                    )
                )

                if extratos_conferencia:
                    extratos_por_banco = {
                        config['slug']: [] for config in configs_conferencia
                    }
                    arquivos_nao_identificados = []
                    for extrato_conferencia in extratos_conferencia:
                        lancamentos_arquivo = processar_extrato_conferencia_empresa(
                            extrato_conferencia.getvalue(), extrato_conferencia.name
                        )
                        df_arquivo = filtrar_dataframe_periodo(
                            pd.DataFrame(lancamentos_arquivo), data_inicial, data_final
                        )
                        if df_arquivo.empty:
                            continue
                        # Prioriza banco/conta no nome do arquivo. Isso cobre
                        # extratos como Extrato_1514_995495_SP-05-2026.pdf,
                        # mesmo quando o PDF não imprime o nome do banco.
                        chave_pelo_nome = identificar_chave_banco_empresa(
                            extrato_conferencia.name
                        )
                        if chave_pelo_nome in extratos_por_banco:
                            extratos_por_banco[chave_pelo_nome].extend(
                                df_arquivo.to_dict('records')
                            )
                            continue
                        chaves_arquivo = df_arquivo['DESCRIÇÃO'].apply(
                            identificar_chave_banco_empresa
                        )
                        chaves_reconhecidas = set(
                            chave for chave in chaves_arquivo.unique().tolist() if chave
                        )
                        if not chaves_reconhecidas:
                            if len(configs_conferencia) == 1:
                                chave_unica = configs_conferencia[0]['slug']
                                extratos_por_banco[chave_unica].extend(df_arquivo.to_dict('records'))
                            else:
                                arquivos_nao_identificados.append(extrato_conferencia.name)
                            continue
                        for config in configs_conferencia:
                            chave = config['slug']
                            df_banco_extrato = df_arquivo[chaves_arquivo.eq(chave)]
                            if not df_banco_extrato.empty:
                                extratos_por_banco[chave].extend(
                                    df_banco_extrato.to_dict('records')
                                )

                    if arquivos_nao_identificados:
                        st.warning(
                            "Não foi possível identificar o banco destes arquivos: "
                            + ", ".join(arquivos_nao_identificados)
                        )
                    if not any(extratos_por_banco.values()):
                        st.warning(
                            "Não foi possível identificar lançamentos dos bancos selecionados "
                            "dentro do período."
                        )
                    else:
                        abas_bancos = st.tabs([
                            config['nome'] for config in configs_conferencia
                        ])
                        for aba_banco, config in zip(abas_bancos, configs_conferencia):
                            with aba_banco:
                                chave = config['slug']
                                nome_banco = config['nome']
                                df_modelo_banco = dados_conferencia_por_banco[chave]['modelo']
                                df_retirados_banco = dados_conferencia_por_banco[chave]['retirados']
                                df_extrato_banco = pd.DataFrame(extratos_por_banco[chave])
                                st.markdown(f"#### Relatório — {nome_banco}")
                                if df_modelo_banco.empty:
                                    st.warning(f"Não há lançamentos do {nome_banco} na planilha para o período.")
                                    continue
                                if df_extrato_banco.empty:
                                    st.warning(f"Nenhum extrato do {nome_banco} foi identificado para o período.")
                                    continue

                                diario, _, _, _ = conciliar_empresa_com_extrato(
                                    df_modelo_banco, df_extrato_banco, df_retirados_banco
                                )
                                if diario.empty:
                                    st.warning("Não existem datas válidas para realizar a conferência.")
                                    continue

                                periodo_inicial = diario['DATA'].min().strftime('%d/%m/%Y')
                                periodo_final = diario['DATA'].max().strftime('%d/%m/%Y')
                                dias_batendo = int((diario['STATUS'] == '✅ Batendo').sum())
                                dias_divergentes = int((diario['STATUS'] == '❌ Divergente').sum())
                                st.info(f"Período analisado: {periodo_inicial} até {periodo_final}")

                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown(f'<div class="metric-card"><div class="metric-title">Dias batendo</div><div class="metric-value" style="color: #3fb950;">{dias_batendo}</div></div>', unsafe_allow_html=True)
                                with c2:
                                    st.markdown(f'<div class="metric-card"><div class="metric-title">Dias divergentes</div><div class="metric-value" style="color: #f85149;">{dias_divergentes}</div></div>', unsafe_allow_html=True)

                                if dias_divergentes == 0:
                                    st.success("Conferência concluída: todos os dias estão batendo.")
                                else:
                                    st.warning("Foram encontradas diferenças nos totais diários.")

                                with st.expander("O que significam os valores acumulados?"):
                                    st.markdown(
                                        "O **acumulado** soma progressivamente os movimentos desde o primeiro "
                                        "dia do período analisado. Ele **não é o saldo bancário real**, pois não "
                                        "inclui o saldo inicial da conta. A diferença acumulada mostra quanto das "
                                        "divergências anteriores ainda permanece sem correção."
                                    )
                                exibicao_diaria = diario.copy()
                                exibicao_diaria['DATA'] = exibicao_diaria['DATA'].dt.strftime('%d/%m/%Y')
                                colunas_monetarias_diarias = [
                                    'TOTAL EXTRATO', 'TOTAL PLANILHA', 'DIFERENÇA DO DIA',
                                    'ACUMULADO EXTRATO', 'ACUMULADO PLANILHA', 'DIFERENÇA ACUMULADA'
                                ]
                                exibicao_diaria = formatar_dataframe_moeda_br(
                                    exibicao_diaria, colunas_monetarias_diarias
                                )
                                st.dataframe(
                                    exibicao_diaria,
                                    use_container_width=True,
                                    height=360
                                )
            except Exception as e:
                st.error(f"Não foi possível organizar a planilha: {e}")

# ==============================================================================
# TELA 4: CONCILIAÇÃO COM O RAZÃO DA DOMÍNIO
# ==============================================================================
elif st.session_state['pagina_ativa'] == 'razao':
    col_voltar, col_tit = st.columns([1.2, 8.8])
    with col_voltar:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True, key="btn_voltar_home_razao"): mudar_pagina('home'); st.rerun()
    with col_tit: st.title("Conciliação: Extrato x Razão da Domínio")
    
    st.caption("Acompanhe a conferência diária comparando diretamente as Entradas e Saídas do Extrato com o Razão da Domínio.")
    st.markdown("""<div class="aviso-banner"><p>⚠️ <strong>Dica para o Razão da Domínio:</strong> Para evitar erros de leitura, abra o relatório <code>.xls</code> antigo no Excel e salve-o como <strong>CSV (separado por vírgulas)</strong> antes de anexar abaixo.</p></div>""", unsafe_allow_html=True)

    st.markdown("##### 📁 Arquivos de Importação")
    col_up1, col_up2 = st.columns(2)
    with col_up1: arq_extrato = st.file_uploader("1º - Envie o Extrato (PDF, OFX, Excel, CSV)", type=["pdf", "ofx", "csv", "xlsx", "xls"], key="up_extrato")
    with col_up2: arq_razao = st.file_uploader("2º - Envie o Razão exportado (CSV ou XLSX)", type=["csv", "xlsx", "xls"], key="up_razao")

    if arq_extrato and arq_razao:
        try:
            ext_bytes, ext_ext = arq_extrato.getvalue(), os.path.splitext(arq_extrato.name)[1].lower()
            lancamentos_ext = []
            if ext_ext == '.ofx': lancamentos_ext = processar_ofx(ext_bytes, arq_extrato.name)
            elif ext_ext in ['.csv', '.xlsx', '.xls']: lancamentos_ext = processar_planilha_universal(ext_bytes, arq_extrato.name)
            elif ext_ext == '.pdf':
                tmp_ext = f"temp_ext_conc_{arq_extrato.name}"
                with open(tmp_ext, "wb") as f: f.write(ext_bytes)
                lancamentos_ext = processar_arquivo_pdf(tmp_ext)
                if os.path.exists(tmp_ext): os.remove(tmp_ext)
                
            raz_bytes, raz_name = arq_razao.getvalue(), arq_razao.name
            
            if 'erro_bof_xls' in st.session_state: del st.session_state['erro_bof_xls']
            df_razao_bruto = processar_razao_dominio(raz_bytes, raz_name)

            if st.session_state.get('erro_bof_xls', False):
                st.markdown("""<div class="alerta-dominio"><h4>🚨 Formato .XLS da Domínio Detectado!</h4><p>O sistema Domínio exporta relatórios em <code>.xls</code> usando um formato binário antigo da Microsoft que oculta os valores originais.</p><p style="margin-top: 10px;"><strong>💡 Como resolver agora:</strong><br>Abra o arquivo <code>.xls</code> no seu Excel e clique em <b>Salvar Como -> CSV (separado por vírgulas)</b> ou <b>Pasta de Trabalho do Excel (.xlsx)</b> e anexe novamente.</p></div>""", unsafe_allow_html=True)
                st.stop()

            if lancamentos_ext and df_razao_bruto is not None and not df_razao_bruto.empty:
                # ---------------- PREPARAÇÃO DOS DADOS ----------------
                df_ext = pd.DataFrame(lancamentos_ext)
                df_ext['DATA_DT'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
                df_ext = df_ext.dropna(subset=['DATA_DT'])
                
                df_ext['ENTRADAS_EXTRATO'] = df_ext['VALOR'].apply(lambda x: x if x > 0 else 0.0)
                df_ext['SAIDAS_EXTRATO'] = df_ext['VALOR'].apply(lambda x: abs(x) if x < 0 else 0.0)
                df_ext_agregado = df_ext.groupby('DATA_DT')[['ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO']].sum().reset_index()
                
                df_razao_bruto['DATA_DT'] = pd.to_datetime(df_razao_bruto['DATA'], dayfirst=True, errors='coerce')
                df_razao_bruto = df_razao_bruto.dropna(subset=['DATA_DT'])
                df_razao_agregado = df_razao_bruto.groupby('DATA_DT')[['ENTRADAS_RAZAO', 'SAIDAS_RAZAO']].sum().reset_index()

                for col in ['ENTRADAS_EXTRATO', 'SAIDAS_EXTRATO']:
                    if col not in df_ext_agregado.columns: df_ext_agregado[col] = 0.0
                for col in ['ENTRADAS_RAZAO', 'SAIDAS_RAZAO']:
                    if col not in df_razao_agregado.columns: df_razao_agregado[col] = 0.0

                df_conciliacao = pd.merge(df_ext_agregado, df_razao_agregado, on='DATA_DT', how='outer').fillna(0.0)
                df_conciliacao = df_conciliacao.sort_values('DATA_DT')
                df_conciliacao['DATA_EXIBICAO'] = df_conciliacao['DATA_DT'].dt.strftime('%d/%m/%Y')

                if df_conciliacao.empty:
                    st.warning("⚠️ Não conseguimos cruzar as datas. Verifique se os arquivos contêm datas válidas.")
                    st.stop()

                # ---------------- FILTRO DE PERÍODO ----------------
                st.markdown("---")
                st.markdown("##### 📅 Filtro de Período da Conciliação")
                
                dt_min_geral, dt_max_geral = df_conciliacao['DATA_DT'].min().date(), df_conciliacao['DATA_DT'].max().date()
                col_p1, col_p2 = st.columns(2)
                with col_p1: data_ini_filtro = st.date_input("Data Inicial", value=dt_min_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="raz_ini")
                with col_p2: data_fim_filtro = st.date_input("Data Final", value=dt_max_geral, min_value=dt_min_geral, max_value=dt_max_geral, format="DD/MM/YYYY", key="raz_fim")
                
                if data_ini_filtro > data_fim_filtro:
                    st.warning("⚠️ A data inicial não pode ser maior que a data final.")
                    data_ini_filtro, data_fim_filtro = dt_min_geral, dt_max_geral

                df_conciliacao = df_conciliacao[(df_conciliacao['DATA_DT'].dt.date >= data_ini_filtro) & (df_conciliacao['DATA_DT'].dt.date <= data_fim_filtro)].copy()

                if df_conciliacao.empty:
                    st.info("Nenhuma movimentação no período selecionado.")
                    st.stop()

                # ---------------- CÁLCULOS DE DIFERENÇAS ----------------
                df_conciliacao = df_conciliacao.sort_values('DATA_DT')
                df_conciliacao['DIF_ENTRADAS'] = df_conciliacao['ENTRADAS_EXTRATO'] - df_conciliacao['ENTRADAS_RAZAO']
                df_conciliacao['DIF_SAIDAS'] = df_conciliacao['SAIDAS_EXTRATO'] - df_conciliacao['SAIDAS_RAZAO']
                
                df_conciliacao['STATUS'] = df_conciliacao.apply(
                    lambda row: "✅ Batendo" if abs(row['DIF_ENTRADAS']) < 0.01 and abs(row['DIF_SAIDAS']) < 0.01 else "❌ Divergente", 
                    axis=1
                )
                
                # ---------------- 4 CARDS RESUMO ----------------
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📊 Resultado da Conferência Diária")
                
                tot_ent_ext = df_conciliacao['ENTRADAS_EXTRATO'].sum()
                tot_sai_ext = df_conciliacao['SAIDAS_EXTRATO'].sum()
                tot_ent_raz = df_conciliacao['ENTRADAS_RAZAO'].sum()
                tot_sai_raz = df_conciliacao['SAIDAS_RAZAO'].sum()
                
                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Entradas (Extrato)</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_ext)}</div></div>', unsafe_allow_html=True)
                with rc2: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Entradas (Razão)</div><div class="metric-value" style="color: #3fb950;">{formatar_moeda(tot_ent_raz)}</div></div>', unsafe_allow_html=True)
                with rc3: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Saídas (Extrato)</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_ext))}</div></div>', unsafe_allow_html=True)
                with rc4: st.markdown(f'<div class="metric-card"><div class="metric-title">Total Saídas (Razão)</div><div class="metric-value" style="color: #f85149;">{formatar_moeda(abs(tot_sai_raz))}</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # ---------------- TABELA DE EXIBIÇÃO ----------------
                df_exibicao = df_conciliacao[['DATA_EXIBICAO', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS', 'STATUS']].copy()
                df_exibicao.columns = ['Data', 'Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)', 'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)', 'Status']
                colunas_monetarias_conciliacao = [
                    'Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)',
                    'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)'
                ]
                
                st.dataframe(
                    formatar_dataframe_moeda_br(df_exibicao, colunas_monetarias_conciliacao),
                    use_container_width=True, 
                    height=380
                )

                # ---------------- EXPORTAÇÃO EXCEL BLINDADA ----------------
                st.markdown("---")
                st.markdown("##### 📥 Exportar Relatório de Conciliação")
                st.caption("Faça o download da conferência completa em formato Excel.")
                
                buf_audit = io.BytesIO()
                with pd.ExcelWriter(buf_audit, engine='openpyxl') as writer:
                    df_exib_excel = df_exibicao.copy()
                    for col in ['Entradas Ext. (R$)', 'Entradas Razão (R$)', 'Dif. Entradas (R$)', 'Saídas Ext. (R$)', 'Saídas Razão (R$)', 'Dif. Saídas (R$)']:
                        df_exib_excel[col] = df_exib_excel[col].apply(formatar_moeda)
                        
                    sanitizar_dataframe(df_exib_excel).to_excel(writer, sheet_name="Resumo Geral", index=False)
                    
                    df_divergencias = df_conciliacao[df_conciliacao['STATUS'] == '❌ Divergente'].copy()
                    if not df_divergencias.empty:
                        df_div_export = df_divergencias[['DATA_EXIBICAO', 'ENTRADAS_EXTRATO', 'ENTRADAS_RAZAO', 'DIF_ENTRADAS', 'SAIDAS_EXTRATO', 'SAIDAS_RAZAO', 'DIF_SAIDAS']].copy()
                        df_div_export.columns = ['Data', 'Entradas Extrato', 'Entradas Razao', 'Diferenca Entradas', 'Saidas Extrato', 'Saidas Razao', 'Diferenca Saidas']
                        for col in df_div_export.columns[1:]: df_div_export[col] = df_div_export[col].apply(formatar_moeda)
                        sanitizar_dataframe(df_div_export).to_excel(writer, sheet_name="Dias Divergentes", index=False)

                st.download_button(
                    label="Baixar Relatório em Excel (.XLSX)", 
                    data=buf_audit.getvalue(), 
                    file_name=f"Analise_Conciliacao_{data_ini_filtro.strftime('%d%m%Y')}_a_{data_fim_filtro.strftime('%d%m%Y')}.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    use_container_width=False
                )

            else:
                st.warning("⚠️ Não conseguimos extrair as linhas contábeis válidas. Verifique se os arquivos contêm Data e Valor.")
        
        except Exception as e:
            st.error(f"🛑 Ocorreu um erro no cruzamento dos dados. Tire um print e envie para análise: \n{traceback.format_exc()}")
