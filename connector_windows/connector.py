"""Conector local Razync para certificados do Windows.

Executa exclusivamente em 127.0.0.1 e nunca exporta chaves privadas.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP_VERSION = "0.1.0"
HOST = "127.0.0.1"
PORT = int(os.environ.get("RAZYNC_CONNECTOR_PORT", "17891"))
ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", ROOT)) / "Razync" / "Connector"
CONFIG_FILE = DATA_DIR / "config.json"
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


class Handler(BaseHTTPRequestHandler):
    server_version = "RazyncConnector/" + APP_VERSION

    def log_message(self, fmt: str, *args) -> None:
        print("[Razync]", fmt % args)

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

    def _json(self, data: object, status: int = 200) -> None:
        self._headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

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
        self.send_response(204)
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

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
            self._json({"error": "Rota não encontrada."}, 404)
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("O Conector Razync deve ser executado no Windows.")
    print("=" * 54)
    print("Conector Razync para Windows")
    print(f"Pareamento: {CONFIG['pairing_code']}")
    print(f"Endereço local: http://{HOST}:{PORT}")
    print("Mantenha esta janela aberta durante o uso.")
    print("=" * 54)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
