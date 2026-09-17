"""Integração visual entre o Streamlit e o Conector Razync local."""
from __future__ import annotations

from pathlib import Path
import re

import streamlit as st
import streamlit.components.v1 as components


_COMPONENT = components.declare_component(
    "razync_windows_connector",
    path=str(Path(__file__).with_name("connector_component")),
)


def render_connector_windows(empresa: str) -> dict | None:
    """Renderiza o cliente local e devolve o certificado escolhido."""
    safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", empresa)
    result = _COMPONENT(
        connector_url="http://127.0.0.1:17891",
        mode="certificate",
        key=f"windows_connector_{safe_key}",
        default=None,
    )
    if not isinstance(result, dict):
        return None

    status = result.get("status")
    if status == "selected" and isinstance(result.get("certificate"), dict):
        st.session_state[f"windows_certificate_{empresa}"] = result["certificate"]

    selected = st.session_state.get(f"windows_certificate_{empresa}")
    if selected:
        subject = str(selected.get("subject", "Certificado Windows"))
        valid_to = str(selected.get("valid_to", ""))[:10]
        st.success(f"Certificado do Windows selecionado: {subject}")
        if valid_to:
            st.caption(f"Validade: {valid_to}")
        return selected
    return None


def render_consulta_dctf(empresa: str, competencia: str) -> dict | None:
    """Abre a DCTFWeb e recebe do conector um relatório baixado no Windows."""
    safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", empresa)
    result = _COMPONENT(
        connector_url="http://127.0.0.1:17891",
        mode="dctf",
        competencia=str(competencia),
        key=f"dctf_connector_{safe_key}_{competencia}",
        default=None,
    )
    return result if isinstance(result, dict) else None
