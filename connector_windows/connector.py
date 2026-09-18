"""Conector local Razync para certificados do Windows.

Executa exclusivamente em 127.0.0.1 e nunca exporta chaves privadas.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP_VERSION = "0.6.2"
HOST = "127.0.0.1"
PORT = int(os.environ.get("RAZYNC_CONNECTOR_PORT", "17891"))
ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", ROOT)) / "Razync" / "Connector"
CONFIG_FILE = DATA_DIR / "config.json"
AUTOMATION_LOG = DATA_DIR / "automation.log"
DEFAULT_ORIGINS = {
    "https://razync-k9la2wnmiml5tm3edjvgur.streamlit.app",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
}


def _load_config() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if config.get("token") and config.get("pairing_code"):
                return config
        except (OSError, ValueError):
            pass
    config = {
        "token": secrets.token_urlsafe(32),
        "pairing_code": f"{secrets.randbelow(1_000_000):06d}",
        "origins": sorted(DEFAULT_ORIGINS),
    }
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


CONFIG = _load_config()


def _console(*values) -> None:
    """Escreve somente quando o conector está no modo visível."""
    if sys.stdout is not None:
        print(*values)


def _powershell(script: str, *args: str) -> object:
    command = [
        "powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(ROOT / script), *args,
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=45, creationflags=creationflags, check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "Falha ao acessar o repositório de certificados.")
    output = result.stdout.strip()
    return json.loads(output) if output else []


def list_certificates() -> list[dict]:
    result = _powershell("list_certificates.ps1")
    if isinstance(result, dict):
        return [result]
    return result


def sign_challenge(thumbprint: str, challenge_b64: str) -> dict:
    if len(challenge_b64) > 16_384:
        raise ValueError("Desafio excede o limite permitido.")
    try:
        base64.b64decode(challenge_b64, validate=True)
    except ValueError as exc:
        raise ValueError("Desafio inválido.") from exc
    result = _powershell("sign_challenge.ps1", thumbprint, challenge_b64)
    if not isinstance(result, dict):
        raise RuntimeError("Resposta de assinatura inválida.")
    return result


ECAC_LOGIN_URL = "https://cav.receita.fazenda.gov.br/autenticacao/login"


def _digits(value: str) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def _valid_cnpj(value: str) -> bool:
    cnpj = _digits(value)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    numbers = [int(char) for char in cnpj]
    for size in (12, 13):
        weights = ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if size == 12
                   else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        total = sum(number * weight for number, weight in zip(numbers[:size], weights))
        digit = 11 - (total % 11)
        expected = 0 if digit >= 10 else digit
        if numbers[size] != expected:
            return False
    return True


def open_dctfweb(cnpj: str, competencia: str, thumbprint: str) -> dict:
    """Prepara a consulta usando o certificado do escritorio como procurador."""
    target_cnpj = _digits(cnpj)
    if not _valid_cnpj(target_cnpj):
        raise ValueError("O CNPJ da empresa representada é inválido.")
    if not re.fullmatch(r"(0[1-9]|1[0-2])-\d{4}", str(competencia or "")):
        raise ValueError("A competência informada é inválida.")

    normalized_thumbprint = re.sub(r"[^0-9A-F]", "", str(thumbprint or "").upper())
    certificates = list_certificates()
    selected = next(
        (
            certificate for certificate in certificates
            if re.sub(r"[^0-9A-F]", "", str(certificate.get("thumbprint", "")).upper()) == normalized_thumbprint
        ),
        None,
    )
    if not selected:
        raise ValueError(
            "O certificado do escritório selecionado não está disponível no Windows."
        )

    # A chave privada permanece no repositório do Windows e nunca é exportada.
    subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-Command",
         "Set-Clipboard -Value $args[0]", target_cnpj],
        capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=15, check=False,
    )
    chrome_config = _powershell("configure_chrome.ps1", normalized_thumbprint)
    if not isinstance(chrome_config, dict) or not chrome_config.get("chrome"):
        raise RuntimeError("O Google Chrome não foi encontrado neste computador.")
    profile = DATA_DIR / "chrome_profile"
    profile.mkdir(parents=True, exist_ok=True)
    automation_url = ECAC_LOGIN_URL
    subprocess.Popen(
        [
            str(chrome_config["chrome"]),
            f"--user-data-dir={profile}",
            "--remote-debugging-port=17892",
            "--remote-debugging-address=127.0.0.1",
            "--remote-allow-origins=http://127.0.0.1:17892",
            "--no-first-run",
            "--no-default-browser-check",
            automation_url,
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    subprocess.Popen(
        [
            "powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(ROOT / "automate_ecac.ps1"), target_cnpj, str(AUTOMATION_LOG),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {
        "opened": True,
        "url": ECAC_LOGIN_URL,
        "automation": "chrome_cdp",
        "certificate_auto_select": bool(chrome_config.get("policy_applied")),
        "cnpj": target_cnpj,
        "competencia": competencia,
        "certificate": {
            "thumbprint": selected.get("thumbprint", ""),
            "subject": selected.get("subject", ""),
        },
        "profile": "procurador",
    }


def latest_dctf_report() -> dict:
    """Lê somente um relatório fiscal recente da pasta Downloads."""
    downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
    if not downloads.is_dir():
        raise ValueError("A pasta Downloads do Windows não foi encontrada.")
    allowed = {".pdf", ".xls", ".xlsx", ".csv"}
    hints = ("dctf", "darf", "debito", "debitos", "declaracao", "receita")
    limit_time = time.time() - 3600
    candidates = [
        item for item in downloads.iterdir()
        if item.is_file()
        and item.suffix.lower() in allowed
        and item.stat().st_mtime >= limit_time
        and any(hint in item.name.lower() for hint in hints)
    ]
    if not candidates:
        raise ValueError(
            "Nenhum relatório recente da DCTFWeb foi encontrado em Downloads. "
            "Baixe o relatório no e-CAC e tente novamente."
        )
    report = max(candidates, key=lambda item: item.stat().st_mtime)
    size = report.stat().st_size
    if size <= 0 or size > 25 * 1024 * 1024:
        raise ValueError("O relatório encontrado está vazio ou excede 25 MB.")
    return {
        "name": report.name,
        "modified_at": report.stat().st_mtime,
        "content": base64.b64encode(report.read_bytes()).decode("ascii"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "RazyncConnector/" + APP_VERSION

    def log_message(self, fmt: str, *args) -> None:
        _console("[Razync]", fmt % args)

    def _origin(self) -> str:
        return self.headers.get("Origin", "")

    def _origin_allowed(self) -> bool:
        origin = self._origin()
        return not origin or origin in set(CONFIG.get("origins", []))

    def _headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self._origin()
        if origin and self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def _json(self, data: object, status: int = 200) -> bool:
        """Envia JSON sem derrubar o conector se o navegador cancelar a chamada."""
        try:
            self._headers(status)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return True
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return False

    def _body(self) -> dict:
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 65536)
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Corpo JSON inválido.") from exc

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return bool(supplied) and hmac.compare_digest(supplied, CONFIG["token"])

    def do_OPTIONS(self) -> None:
        if not self._origin_allowed():
            self._json({"error": "Origem não autorizada."}, 403)
            return
        try:
            self.send_response(204)
            origin = self._origin()
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/v1/health":
            self._json({"ok": True, "name": "Razync Connector", "version": APP_VERSION})
            return
        if not self._origin_allowed():
            self._json({"error": "Origem não autorizada."}, 403)
            return
        if not self._authorized():
            self._json({"error": "Conector não pareado."}, 401)
            return
        if path == "/v1/certificates":
            try:
                self._json({"certificates": list_certificates()})
            except Exception as exc:
                self._json({"error": str(exc)}, 500)
            return
        if path == "/v1/dctf/latest":
            try:
                self._json(latest_dctf_report())
            except ValueError as exc:
                self._json({"error": str(exc)}, 404)
            except Exception as exc:
                self._json({"error": str(exc)}, 500)
            return
        self._json({"error": "Rota não encontrada."}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not self._origin_allowed():
            self._json({"error": "Origem não autorizada."}, 403)
            return
        try:
            body = self._body()
            if path == "/v1/pair":
                code = str(body.get("code", "")).strip()
                if not hmac.compare_digest(code, CONFIG["pairing_code"]):
                    self._json({"error": "Código de pareamento inválido."}, 401)
                    return
                self._json({"token": CONFIG["token"], "version": APP_VERSION})
                return
            if not self._authorized():
                self._json({"error": "Conector não pareado."}, 401)
                return
            if path == "/v1/sign":
                result = sign_challenge(
                    str(body.get("thumbprint", "")).strip(),
                    str(body.get("challenge", "")).strip(),
                )
                self._json(result)
                return
            if path == "/v1/dctf/open":
                self._json(open_dctfweb(
                    str(body.get("cnpj", "")),
                    str(body.get("competencia", "")),
                    str(body.get("thumbprint", "")),
                ))
                return
            self._json({"error": "Rota não encontrada."}, 404)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("O Conector Razync deve ser executado no Windows.")
    _console("=" * 54)
    _console("Conector Razync para Windows")
    _console(f"Pareamento: {CONFIG['pairing_code']}")
    _console(f"Endereço local: http://{HOST}:{PORT}")
    _console("Modo visível para pareamento e diagnóstico.")
    _console("=" * 54)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
