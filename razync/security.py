"""Controle de acesso do Razync."""
import hmac
import time

import streamlit as st

MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 300
SESSAO_SEGUNDOS = 8 * 60 * 60


def _obter_senha():
    try:
        secao = st.secrets.get("security", {})
        return str(secao.get("app_password", "") or st.secrets.get("APP_PASSWORD", ""))
    except Exception:
        return ""


def _limpar_autorizacao():
    st.session_state.pop("_hc_acesso_autorizado", None)
    st.session_state.pop("_hc_ultima_atividade", None)


def proteger_acesso():
    """Protege o app quando há senha configurada e preserva o acesso legado sem senha."""
    senha_configurada = _obter_senha()
    if not senha_configurada:
        _limpar_autorizacao()
        return False

    agora = time.time()
    if st.session_state.get("_hc_acesso_autorizado", False):
        ultima_atividade = float(st.session_state.get("_hc_ultima_atividade", agora))
        if agora - ultima_atividade <= SESSAO_SEGUNDOS:
            st.session_state["_hc_ultima_atividade"] = agora
            return True
        _limpar_autorizacao()
        st.warning("Sua sessão expirou. Entre novamente.")

    bloqueado_ate = float(st.session_state.get("_hc_bloqueado_ate", 0))
    if bloqueado_ate > agora:
        minutos = max(1, int((bloqueado_ate - agora + 59) // 60))
        st.error(f"Muitas tentativas incorretas. Aguarde {minutos} minuto(s).")
        st.stop()
    if bloqueado_ate:
        st.session_state["_hc_bloqueado_ate"] = 0
        st.session_state["_hc_tentativas"] = 0

    st.markdown("<div style='height: 12vh;'></div>", unsafe_allow_html=True)
    _, coluna_login, _ = st.columns([1.25, 1, 1.25])
    with coluna_login:
        st.image("assets/razync-icon.png", width=66)
        st.markdown("## Razync")
        st.caption("Acesso restrito. Informe a senha para continuar.")
        with st.form("hc_formulario_acesso", clear_on_submit=True):
            senha_informada = st.text_input(
                "Senha de acesso", type="password", autocomplete="current-password"
            )
            entrar = st.form_submit_button("Entrar no sistema", use_container_width=True)
        if entrar:
            if hmac.compare_digest(str(senha_informada), senha_configurada):
                st.session_state["_hc_acesso_autorizado"] = True
                st.session_state["_hc_ultima_atividade"] = agora
                st.session_state["_hc_tentativas"] = 0
                st.session_state["_hc_bloqueado_ate"] = 0
                st.rerun()

            tentativas = int(st.session_state.get("_hc_tentativas", 0)) + 1
            st.session_state["_hc_tentativas"] = tentativas
            if tentativas >= MAX_TENTATIVAS:
                st.session_state["_hc_bloqueado_ate"] = agora + BLOQUEIO_SEGUNDOS
                st.session_state["_hc_tentativas"] = 0
                st.error("Acesso bloqueado por 5 minutos.")
            else:
                restantes = MAX_TENTATIVAS - tentativas
                st.error(f"Senha incorreta. Restam {restantes} tentativa(s).")
    st.stop()
