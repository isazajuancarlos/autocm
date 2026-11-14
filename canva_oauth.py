#!/usr/bin/env python3
"""
Obtiene (y explica cómo refrescar) un token de la **Canva Connect API** para
`canva.py`. Mismo patrón que `get_linkedin_token.py`: levanta un servidor local
en `/callback`, abre el navegador, y cambia el `code` por un token.

Canva exige **PKCE** (`code_challenge` S256), así que se genera un `code_verifier`
y su reto.

Uso:
  1. En el panel de desarrollador de Canva (https://www.canva.com/developers/):
     crea una integración, añade `http://127.0.0.1:8766/callback` como Redirect
     URL, y activa los scopes `design:content:write` y `design:content:read`.
  2. CANVA_CLIENT_ID=xxx CANVA_CLIENT_SECRET=yyy .venv/bin/python canva_oauth.py
  3. Inicia sesión en Canva (la cuenta de la organización Enterprise) y autoriza.
  4. Pega en `.env` el CANVA_ACCESS_TOKEN y el CANVA_REFRESH_TOKEN que imprime.

El access token de Canva dura ~4 h; el refresh token sirve para renovarlo sin
volver a abrir el navegador (grant_type=refresh_token). `canva.py` no refresca
solo todavía: cuando el temporizador falle con 401, se corre esto de nuevo o se
añade el refresco (ver `docs/CANVA.md`).
"""
import os
import sys
import base64
import hashlib
import secrets
import threading
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

CLIENT_ID = os.getenv("CANVA_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("CANVA_CLIENT_SECRET", "").strip()
PORT = int(os.getenv("CANVA_OAUTH_PORT", "8766"))
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"
SCOPES = "design:content:write design:content:read"

AUTORIZAR = "https://www.canva.com/api/oauth/authorize"
TOKEN = "https://api.canva.com/rest/v1/oauth/token"

_codigo = {}


def _pkce():
    """Devuelve (code_verifier, code_challenge S256) para PKCE."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    reto = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, reto


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        partes = urllib.parse.urlparse(self.path)
        if partes.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(partes.query)
        _codigo["code"] = q.get("code", [None])[0]
        _codigo["state"] = q.get("state", [None])[0]
        _codigo["error"] = q.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h1>Listo. Vuelve a la terminal.</h1>".encode())

    def log_message(self, *_):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit("Faltan CANVA_CLIENT_ID / CANVA_CLIENT_SECRET en el entorno.")

    verifier, reto = _pkce()
    estado = secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": reto,
        "code_challenge_method": "S256",
        "state": estado,
    }
    url = AUTORIZAR + "?" + urllib.parse.urlencode(params)

    servidor = HTTPServer(("127.0.0.1", PORT), Handler)
    hilo = threading.Thread(target=servidor.handle_request, daemon=True)
    hilo.start()
    print("Abriendo el navegador para autorizar en Canva…")
    print("Si no se abre, pega esta URL:\n", url)
    webbrowser.open(url)
    hilo.join(timeout=300)

    if _codigo.get("error"):
        sys.exit(f"Canva devolvió un error: {_codigo['error']}")
    if not _codigo.get("code"):
        sys.exit("No llegó el código de autorización (¿se agotó el tiempo?).")
    if _codigo.get("state") != estado:
        sys.exit("El `state` no coincide: posible CSRF, se aborta.")

    # Cambio del código por el token. Canva autentica la app con Basic (id:secret).
    r = requests.post(
        TOKEN,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": _codigo["code"],
            "code_verifier": verifier,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if r.status_code != 200:
        sys.exit(f"El intercambio de token falló: HTTP {r.status_code}: {r.text[:300]}")
    tok = r.json()
    print("\n=== Pega esto en tu .env ===")
    print(f"CANVA_ACCESS_TOKEN={tok.get('access_token','')}")
    print(f"CANVA_REFRESH_TOKEN={tok.get('refresh_token','')}")
    print(f"# expira en {tok.get('expires_in','?')} s; refresca con el refresh token")


if __name__ == "__main__":
    main()
