#!/usr/bin/env python3
"""
Obtiene un LINKEDIN_ACCESS_TOKEN para publicar en LinkedIn. Dos modos, según
LINKEDIN_AUTHOR_MODE (debe cuadrar con el de main.py):

  person       (disponible YA) -> publica como el perfil de Juan Carlos Isaza.
      Pide w_member_social + openid + profile. Productos de la app:
      "Share on LinkedIn" y "Sign In with LinkedIn using OpenID Connect", ambos
      de auto-aprobación. Además del access token, imprime LINKEDIN_PERSON_SUB.

  organization (requiere aprobación) -> publica como la página Xillux. Pide
      w_organization_social + r_organization_social + rw_organization_admin, que
      SOLO otorga la "Community Management API" tras revisión humana de LinkedIn
      (hoy DENEGADA). Sin ella, pedir esos scopes da unauthorized_scope_error.

Uso:
  1. En el panel de tu app añade http://localhost:8765/callback como
     "Authorized redirect URL", y añade los productos del modo elegido.
  2. LINKEDIN_AUTHOR_MODE=person LINKEDIN_CLIENT_ID=xxx LINKEDIN_CLIENT_SECRET=yyy \
         python get_linkedin_token.py
  3. Se abre el navegador. Inicia sesión con la cuenta de Juan Carlos Isaza (que
     en modo organization debe además ADMINISTRAR la página) y autoriza.
  4. Pega en .env el access token (LINKEDIN_ACCESS_TOKEN), el refresh token y —en
     modo person— el LINKEDIN_PERSON_SUB que imprime.
"""
import os
import sys
import secrets
import threading
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
PORT = int(os.getenv("LINKEDIN_OAUTH_PORT", "8765"))
REDIRECT_URI = f"http://localhost:{PORT}/callback"
AUTHOR_MODE = os.getenv("LINKEDIN_AUTHOR_MODE", "organization").strip().lower()
# Scopes por modo (deben cuadrar con LINKEDIN_AUTHOR_MODE de main.py):
#   organization: los tres los otorga la Community Management API al aprobarse, y
#     los tres hacen falta (verificado el 2026-08-02 contra learn.microsoft.com):
#       w_organization_social  -> POST /rest/posts como urn:li:organization
#       r_organization_social  -> leer los posts de la página
#       rw_organization_admin  -> GET /organizationAcls, con lo que main.py
#                                 comprueba que el token administre ESTA página.
#     Sin el tercero la publicación funciona pero --verify devuelve 403.
#   person: publicar como el perfil, sin aprobación humana:
#       w_member_social  -> POST /rest/posts como urn:li:person
#       openid, profile  -> GET /v2/userinfo, de donde sale el 'sub' del autor.
if AUTHOR_MODE == "person":
    SCOPES = "w_member_social openid profile"
else:
    SCOPES = "w_organization_social r_organization_social rw_organization_admin"

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

_result = {}
_expected_state = secrets.token_urlsafe(24)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(parsed.query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if "error" in q:
            _result["error"] = f"{q.get('error')} — {q.get('error_description')}"
            self.wfile.write("<h1>Error. Vuelve a la terminal.</h1>".encode())
        elif q.get("state", [""])[0] != _expected_state:
            _result["error"] = "state no coincide (posible CSRF); abortado"
            self.wfile.write("<h1>state invalido. Vuelve a la terminal.</h1>".encode())
        else:
            _result["code"] = q.get("code", [""])[0]
            self.wfile.write("<h1>Listo. Puedes cerrar esta pestana.</h1>".encode())

    def log_message(self, *a):  # silenciar el log del servidor
        pass


def main():
    if not (CLIENT_ID and CLIENT_SECRET):
        sys.exit("Faltan LINKEDIN_CLIENT_ID y/o LINKEDIN_CLIENT_SECRET en el entorno.")

    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": _expected_state,
        "scope": SCOPES,
    })
    url = f"{AUTH_URL}?{params}"

    server = HTTPServer(("localhost", PORT), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print(f"Abriendo el navegador. Si no se abre, pega esta URL:\n\n{url}\n")
    webbrowser.open(url)
    print(f"Esperando la redirección en {REDIRECT_URI} ...")

    while not _result:
        pass
    server.shutdown()

    if "error" in _result:
        sys.exit(f"\nLinkedIn devolvió: {_result['error']}")

    print("\nCódigo recibido. Intercambiando por el token...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": _result["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)

    if resp.status_code != 200:
        sys.exit(f"Intercambio falló: HTTP {resp.status_code}\n{resp.text}")

    tok = resp.json()
    access_token = tok.get("access_token")
    print("\n" + "=" * 60)
    print("ACCESS TOKEN (vale ~60 días) — pégalo en .env:\n")
    print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    print(f"\nExpira en {tok.get('expires_in')} s")
    if tok.get("refresh_token"):
        print(f"\nREFRESH TOKEN (vale ~365 días) — guárdalo para renovar sin repetir esto:")
        print(f"LINKEDIN_REFRESH_TOKEN={tok.get('refresh_token')}")
        print(f"Refresh expira en {tok.get('refresh_token_expires_in')} s")
    if AUTHOR_MODE == "person":
        # El 'sub' de OpenID es el id del perfil; main.py lo necesita para armar
        # urn:li:person:{sub}. Se lee aquí para no pedir un GET extra por ciclo.
        ui = requests.get("https://api.linkedin.com/v2/userinfo",
                          headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        if ui.status_code == 200:
            print(f"\nLINKEDIN_PERSON_SUB={ui.json().get('sub')}   # pégalo también en .env")
        else:
            print(f"\n⚠️ No se pudo leer /v2/userinfo (HTTP {ui.status_code}). "
                  f"¿La app tiene el producto 'Sign In with LinkedIn using OpenID Connect'?")
    print("=" * 60)
    print("\nVerifica con:  python main.py --verify")


if __name__ == "__main__":
    main()
