#!/usr/bin/env python3
"""
Pone nombre, biografía y avatar en las cuentas sociales de Xiliux.

Existe como script y no como una tanda de comandos porque el perfil se vuelve a
tocar: cambia la descripción de la empresa, se añade un enlace, se rehace el
logo. Un fichero se revisa en el diff; un `curl` de hace tres semanas, no.

    .venv/bin/python perfiles.py --simulacro
    .venv/bin/python perfiles.py --aplicar
    .venv/bin/python perfiles.py --aplicar --solo mastodon

**Nada jurídico aquí.** Estas cuentas hablan por Xiliux —software— y la práctica
jurídica de Juan Carlos Isaza va por separado: dominio distinto, estética
distinta y sin enlaces cruzados. Una biografía que mezcle las dos automatiza
justo la fusión de identidades que la regla existe para impedir.
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

NOMBRE = "Xiliux"

# Bluesky corta la descripción del perfil en 256 caracteres. La de Mastodon
# puede ser más larga, pero decir lo mismo en los dos sitios evita que dentro de
# un año nadie sepa cuál es la buena.
BIO = (
    "Estudio de software en Medellín. Python para MVPs, integración de LLMs y "
    "automatización. Y Quipu: criptografía post-cuántica libre en Rust "
    "(ML-KEM-1024, ML-DSA-87).\n"
    "xiliux.com"
)

# Solo Mastodon tiene campos de metadatos. El primero es el que Mastodon puede
# marcar como verificado si xiliux.com devuelve un <a rel="me"> a esta cuenta.
CAMPOS = [
    ("Web", "https://xiliux.com"),
    ("Blog", "https://xiliux.com/blog"),
    ("Quipu", "https://github.com/isazajuancarlos/quipu"),
    ("Código", "https://github.com/isazajuancarlos"),
]

# Las genera `imagenes_marca.py` a partir de la imagen canónica de Xiliux
# (/mnt/data/documentos/gato_xiliux.png). No se usa la del sitio: pesa 3,8 MB y
# la figura ocupa solo el 63 % del ancho, así que a 96 px no se distingue.
AVATAR = "marca/avatar.png"
BANNER = "marca/banner.png"
LIMITE_BLUESKY = 1_000_000  # Bluesky corta cualquier blob de imagen ahí


def leer(ruta):
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"falta {ruta}; genérala con: .venv/bin/python imagenes_marca.py")
    with open(ruta, "rb") as f:
        return f.read()


def aplicar_mastodon(avatar, banner):
    token = os.getenv("MASTODON_ACCESS_TOKEN")
    base = os.getenv("MASTODON_API_URL")
    if not token or not base:
        raise RuntimeError("faltan MASTODON_ACCESS_TOKEN/MASTODON_API_URL en .env")

    campos = {}
    for i, (nombre, valor) in enumerate(CAMPOS[:4]):   # Mastodon admite 4
        campos[f"fields_attributes[{i}][name]"] = nombre
        campos[f"fields_attributes[{i}][value]"] = valor

    r = requests.patch(
        f"{base.rstrip('/')}/api/v1/accounts/update_credentials",
        headers={"Authorization": f"Bearer {token}"},
        data={"display_name": NOMBRE, "note": BIO,
              # Aparecer en el directorio: sin esto la cuenta existe y nadie la
              # encuentra buscándola.
              "discoverable": "true",
              # `bot` se deja en false a conciencia: lo que se publica lo escribió
              # una persona y la cola solo lo entrega. El día que el texto lo
              # genere un modelo, esto pasa a true — marcarlo es lo honesto en el
              # fediverso, y allí se nota.
              "bot": "false", **campos},
        files={"avatar": ("avatar.png", avatar, "image/png"),
               "header": ("banner.png", banner, "image/png")},
        timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} {r.text[:250]}")
    d = r.json()
    return f"@{d['acct']} · {d['display_name']} · {len(d.get('fields', []))} campos"


def aplicar_bluesky(avatar, banner):
    from atproto import Client, models

    for nombre, datos in (("avatar", avatar), ("banner", banner)):
        if len(datos) > LIMITE_BLUESKY:
            raise ValueError(f"el {nombre} pesa {len(datos)} B y Bluesky corta "
                             f"en {LIMITE_BLUESKY} B")
    usuario = os.getenv("BLUESKY_HANDLE")
    clave = os.getenv("BLUESKY_PASSWORD")
    if not usuario or not clave:
        raise RuntimeError("faltan BLUESKY_HANDLE/BLUESKY_PASSWORD en .env")

    c = Client()
    c.login(usuario, clave)

    # El perfil es UN registro con rkey fijo 'self' y se escribe entero: lo que
    # no se mande aquí desaparece. Por eso avatar y banner van juntos y no en
    # dos llamadas — la segunda borraría lo que puso la primera.
    c.com.atproto.repo.put_record(models.ComAtprotoRepoPutRecord.Data(
        repo=c.me.did,
        collection="app.bsky.actor.profile",
        rkey="self",
        record=models.AppBskyActorProfile.Record(
            display_name=NOMBRE, description=BIO,
            avatar=c.upload_blob(avatar).blob,
            banner=c.upload_blob(banner).blob),
    ))
    return f"@{c.me.handle} · {NOMBRE} · avatar {len(avatar)//1000} kB + banner {len(banner)//1000} kB"


CANALES = {"mastodon": aplicar_mastodon, "bluesky": aplicar_bluesky}


def main():
    p = argparse.ArgumentParser()
    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument("--simulacro", action="store_true",
                      help="enseña qué pondría, sin tocar ninguna cuenta")
    modo.add_argument("--aplicar", action="store_true")
    p.add_argument("--solo", choices=sorted(CANALES))
    args = p.parse_args()

    print(f"nombre : {NOMBRE}")
    print(f"bio    : {len(BIO)} caracteres"
          f"{'  ⚠️ PASA DE 256, Bluesky la corta' if len(BIO) > 256 else '  (cabe en Bluesky)'}")
    for línea in BIO.splitlines():
        print(f"         {línea}")
    print("campos : " + "  ·  ".join(f"{n}={v}" for n, v in CAMPOS)
          + "   (solo Mastodon)")
    print(f"avatar : {AVATAR}")
    print(f"banner : {BANNER}")

    if args.simulacro:
        print("\nSIMULACRO: no se tocó ninguna cuenta.")
        return 0

    avatar, banner = leer(AVATAR), leer(BANNER)
    print(f"\navatar {len(avatar)//1000} kB · banner {len(banner)//1000} kB")

    fallos = 0
    for nombre, aplicar in CANALES.items():
        if args.solo and nombre != args.solo:
            continue
        try:
            print(f"  ✅ {nombre}: {aplicar(avatar, banner)}")
        except Exception as e:
            print(f"  ❌ {nombre}: {e}")
            fallos += 1
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
