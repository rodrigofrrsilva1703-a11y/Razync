"""Marcador de deploy da empresa 626.

Força o Streamlit Cloud a carregar a versão que remove linhas de saldo final do
Banco do Brasil mesmo quando o OCR distorce o código 999 ou espaça S A L D O.
"""

DEPLOY_626_BB_SALDO = "2026-09-15T03:05-03:00-sicredi-auditoria-v5"
