#!/usr/bin/env python3
"""
Llena la cola con una NOTA por artículo del blog.

No usa IA a propósito. El título y la `og:description` de cada entrada ya están
escritos por una persona y dicen exactamente lo que el artículo dice; pasarlos
por un modelo solo añade el riesgo de que invente un producto que no existe, que
es el fallo que este proyecto ya cometió una vez. Si algún texto no convence, se
edita la fila —o el propio blog—, no el prompt.

    .venv/bin/python llenar_cola.py --destino linkedin
    .venv/bin/python llenar_cola.py --destino bluesky --limite 300

Todo entra como `borrador`. Para LinkedIn eso significa que espera tu visto
bueno; para Bluesky o Mastodon, que ya es publicable.
"""
import argparse
import re
import sys

import requests

import cola
from publicar_devto import _desescapar, _meta, urls_del_blog

# Lo que cabe de verdad en cada sitio. El enlace se cuenta aparte porque va al
# final y las plataformas lo acortan de forma distinta.
LIMITES = {"linkedin": 2900, "bluesky": 280, "mastodon": 480,
           "telegram": 3800, "discord": 1900, "nostr": 500,
           "threads": 500, "instagram": 2200, "x": 280}


def nota(url, tope):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    html = r.text

    título = _desescapar(_meta(html, "og:title")).replace(" | Blog de Xiliux", "").strip()
    gancho = _desescapar(_meta(html, "og:description")).strip()
    if not título or not gancho:
        raise ValueError(f"{url}: falta og:title u og:description")

    cuerpo = f"{título}\n\n{gancho}"
    sitio = tope - len(url) - 2
    if len(cuerpo) > sitio:
        # Recorta por frase, no a mitad de palabra: un texto cortado en seco se
        # nota más que uno más corto.
        recorte = cuerpo[:sitio]
        corte = max(recorte.rfind(". "), recorte.rfind("? "), recorte.rfind("! "))
        cuerpo = (recorte[:corte + 1] if corte > sitio * 0.5 else recorte.rstrip() + "…")
    return f"{cuerpo}\n\n{url}", título, gancho


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--destino", required=True, choices=sorted(cola.DESTINOS))
    p.add_argument("--limite", type=int, help="caracteres; por defecto, el del canal")
    p.add_argument("--imagen", action="store_true",
                   help="genera una tarjeta de marca por nota (necesita TARJETA_FONDO). "
                        "Si falla, se encola solo texto.")
    args = p.parse_args()

    tope = args.limite or LIMITES.get(args.destino)
    if tope is None:
        sys.exit(f"No sé el límite de {args.destino}: pásalo con --limite.")

    cx = cola.conectar()
    urls = urls_del_blog()
    print(f"{len(urls)} artículos, tope de {tope} caracteres para {args.destino}\n")

    nuevas = repetidas = fallos = 0
    for url in urls:
        try:
            texto, titulo, gancho = nota(url, tope)
        except Exception as e:
            print(f"  ❌ {e}")
            fallos += 1
            continue
        # Tarjeta de marca opcional. Si falla (sin fondo, Canva caído…), se degrada
        # a texto: una nota sin imagen es mejor que ninguna.
        imagen = alt = None
        if args.imagen:
            try:
                from imagen_para_post import imagen_para, ErrorImagen
                imagen, alt = imagen_para(titulo, cuerpo=gancho)
            except ErrorImagen as e:
                print(f"       (sin tarjeta, va como texto: {e})")
        i = cola.encolar(cx, args.destino, "NOTA", texto, url, imagen=imagen, imagen_alt=alt)
        if i:
            print(f"  #{i:<4} {len(texto):>4} car.  {url.rsplit('/', 1)[-1][:50]}")
            nuevas += 1
        else:
            repetidas += 1

    print(f"\n{nuevas} nuevas, {repetidas} ya estaban, {fallos} con fallo")
    if nuevas and args.destino in cola.SENSIBLES:
        print(f"\n{args.destino} es un canal sensible: nada sale sin tu visto bueno.")
        print(f"   python cola.py listar --destino {args.destino}")
        print(f"   python cola.py aprobar <id>")
        print(f"   python cola.py pendientes {args.destino}")
    cx.close()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
