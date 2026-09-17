"""Cadastro seguro de certificados digitais A1 por empresa."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier


OID_CNPJ = ObjectIdentifier("2.16.76.1.3.3")


def _configuracao():
    import streamlit as st

    secao = st.secrets.get("supabase", {})
    url = str(secao.get("url", "") or st.secrets.get("SUPABASE_URL", "")).rstrip("/")
    chave = str(
        secao.get("service_key", "") or st.secrets.get("SUPABASE_SERVICE_KEY", "")
    )
    chave_mestra = str(
        st.secrets.get("CERTIFICATES_MASTER_KEY", "")
        or secao.get("certificates_master_key", "")
        or chave
    )
    if "/rest/v1" in url:
        url = url.split("/rest/v1", 1)[0]
    return url, chave, chave_mestra


def _chave_aes(segredo: str) -> bytes:
    if not segredo:
        raise RuntimeError("A chave de criptografia dos certificados não foi configurada.")
    return hashlib.sha256(("razync-certificados-v1::" + segredo).encode()).digest()


def _cifrar(pfx: bytes, senha: str, segredo: str) -> str:
    nonce = os.urandom(12)
    payload = json.dumps({
        "pfx": base64.b64encode(pfx).decode("ascii"), "senha": senha,
    }, separators=(",", ":")).encode()
    cifrado = AESGCM(_chave_aes(segredo)).encrypt(nonce, payload, b"razync-certificado-a1")
    return base64.b64encode(nonce + cifrado).decode("ascii")


def decifrar_certificado(pacote: str, segredo: str) -> tuple[bytes, str]:
    bruto = base64.b64decode(pacote)
    payload = AESGCM(_chave_aes(segredo)).decrypt(
        bruto[:12], bruto[12:], b"razync-certificado-a1"
    )
    dados = json.loads(payload.decode())
    return base64.b64decode(dados["pfx"]), str(dados["senha"])


def validar_certificado(pfx: bytes, senha: str) -> dict:
    try:
        chave_privada, certificado, _ = pkcs12.load_key_and_certificates(
            pfx, senha.encode("utf-8")
        )
    except Exception as erro:
        raise ValueError("Não foi possível abrir o certificado. Confira o arquivo e a senha.") from erro
    if certificado is None or chave_privada is None:
        raise ValueError("O arquivo não contém um certificado A1 com chave privada.")

    def atributo(oid):
        encontrados = certificado.subject.get_attributes_for_oid(oid)
        return str(encontrados[0].value) if encontrados else ""

    cnpj = ""
    especificos = certificado.subject.get_attributes_for_oid(OID_CNPJ)
    if especificos:
        cnpj = re.sub(r"\D", "", str(especificos[0].value))
    if len(cnpj) != 14:
        for item in certificado.subject:
            candidato = re.sub(r"\D", "", str(item.value))
            if len(candidato) == 14:
                cnpj = candidato
                break
    titular = atributo(NameOID.COMMON_NAME)
    emissor_cn = certificado.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
    inicio = getattr(certificado, "not_valid_before_utc", None)
    fim = getattr(certificado, "not_valid_after_utc", None)
    if inicio is None:
        inicio = certificado.not_valid_before.replace(tzinfo=timezone.utc)
    if fim is None:
        fim = certificado.not_valid_after.replace(tzinfo=timezone.utc)
    return {
        "cnpj": cnpj,
        "titular": titular,
        "emissor": str(emissor_cn[0].value) if emissor_cn else certificado.issuer.rfc4514_string(),
        "numero_serie": format(certificado.serial_number, "X"),
        "validade_inicio": inicio.date().isoformat(),
        "validade_fim": fim.date().isoformat(),
        "fingerprint_sha256": certificado.fingerprint(hashes.SHA256()).hex().upper(),
    }


def _requisicao(caminho: str, metodo: str = "GET", dados=None, prefer: str = ""):
    url, chave, _ = _configuracao()
    if not url or not chave:
        raise RuntimeError("O armazenamento seguro ainda não foi configurado no servidor.")
    corpo = json.dumps(dados).encode() if dados is not None else None
    headers = {
        "apikey": chave, "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        f"{url}/rest/v1/{caminho}", data=corpo, headers=headers, method=metodo
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resposta:
            conteudo = resposta.read().decode()
            return json.loads(conteudo) if conteudo else []
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode(errors="ignore")
        raise RuntimeError(f"Falha no armazenamento seguro ({erro.code}): {detalhe[:180]}") from erro


def buscar_certificado(empresa: str) -> dict | None:
    consulta = (
        "certificados_digitais?empresa=eq." + urllib.parse.quote(empresa)
        + "&select=empresa,codigo_empresa,cnpj,titular,emissor,numero_serie,"
        "validade_inicio,validade_fim,fingerprint_sha256,atualizado_em&limit=1"
    )
    registros = _requisicao(consulta)
    return registros[0] if registros else None


def salvar_certificado(empresa: str, codigo: str, pfx: bytes, senha: str) -> dict:
    _, _, segredo = _configuracao()
    metadados = validar_certificado(pfx, senha)
    registro = {
        "empresa": empresa, "codigo_empresa": codigo,
        **metadados, "pacote_criptografado": _cifrar(pfx, senha, segredo),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }
    retorno = _requisicao(
        "certificados_digitais?on_conflict=empresa", "POST", registro,
        "resolution=merge-duplicates,return=representation",
    )
    return retorno[0] if retorno else metadados


def excluir_certificado(empresa: str) -> None:
    _requisicao(
        "certificados_digitais?empresa=eq." + urllib.parse.quote(empresa),
        "DELETE", prefer="return=minimal",
    )


def renderizar_certificado_digital(empresa: str, nome_empresa: str) -> None:
    import streamlit as st

    codigo = (re.match(r"\s*(\d+)", nome_empresa) or [None, empresa])[1]
    with st.popover("🔐 Certificado Digital", use_container_width=False):
        st.markdown("#### Certificado Digital A1")
        st.caption("O arquivo e a senha são criptografados antes de serem armazenados.")
        try:
            atual = buscar_certificado(empresa)
        except Exception as erro:
            st.error(str(erro))
            return
        if atual:
            validade = date.fromisoformat(atual["validade_fim"])
            dias = (validade - date.today()).days
            if dias < 0:
                st.error(f"Certificado vencido em {validade.strftime('%d/%m/%Y')}.")
            elif dias <= 30:
                st.warning(f"Certificado vence em {dias} dia(s): {validade.strftime('%d/%m/%Y')}.")
            else:
                st.success(f"Certificado válido até {validade.strftime('%d/%m/%Y')}.")
            st.write(f"**Titular:** {atual['titular']}")
            st.write(f"**CNPJ:** {atual['cnpj']}")
            st.caption(f"Série: {atual['numero_serie']} · Emissor: {atual['emissor']}")

        with st.form(f"form_certificado_{empresa}", clear_on_submit=True):
            arquivo = st.file_uploader("Certificado A1", type=["pfx", "p12"])
            senha = st.text_input("Senha do certificado", type="password")
            cnpj_esperado = st.text_input("CNPJ da empresa para validação")
            confirmar = st.form_submit_button(
                "Salvar ou substituir certificado", type="primary", use_container_width=True
            )
        if confirmar:
            if arquivo is None or not senha:
                st.error("Envie o certificado e informe a senha.")
            else:
                try:
                    metadados = validar_certificado(arquivo.getvalue(), senha)
                    esperado = re.sub(r"\D", "", cnpj_esperado)
                    if esperado and metadados["cnpj"] and esperado != metadados["cnpj"]:
                        raise ValueError("O CNPJ do certificado não corresponde ao CNPJ informado.")
                    salvar_certificado(empresa, str(codigo), arquivo.getvalue(), senha)
                    st.success("Certificado validado, criptografado e vinculado à empresa.")
                    st.rerun()
                except Exception as erro:
                    st.error(str(erro))

        if atual:
            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo remover o certificado", key=f"excluir_cert_{empresa}"
            )
            if st.button(
                "Remover certificado", disabled=not confirmar_exclusao,
                key=f"btn_excluir_cert_{empresa}", use_container_width=True,
            ):
                excluir_certificado(empresa)
                st.success("Certificado removido.")
                st.rerun()
