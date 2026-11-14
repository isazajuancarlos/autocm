#!/usr/bin/env python3
"""
Republica los artículos del blog de Xiliux en dev.to con `canonical_url`.

Por qué canonical_url: apunta a xiliux.com, así que dev.to presta su audiencia
sin que Google trate la copia como contenido duplicado. La autoridad se queda
en el sitio propio; el alcance se toma prestado.

Dos modos, y el que no publica es el que se usa para revisar:

    python publicar_devto.py --preparar            # escribe .md locales, NO toca dev.to
    python publicar_devto.py --publicar --borrador # sube a dev.to como borrador
    python publicar_devto.py --publicar            # sube publicado

Necesita DEV_TO_API_KEY (dev.to → Settings → Extensions → DEV Community API Keys).
Sin ella, --publicar falla ruidosamente: no cae a modo preparar (directiva 20).
"""
import argparse
import json
import os
import re
import sys
import time

# defusedxml y no la stdlib: el parser de serie expande entidades externas, así
# que un sitemap manipulado podría leer ficheros locales o colgar el proceso.
import defusedxml.ElementTree as ET
import requests
from dotenv import load_dotenv
from markdownify import markdownify

load_dotenv()  # la clave vive en .env, no en la línea de órdenes ni en el historial

SITEMAP = "https://xiliux.com/sitemap.xml"
API = "https://dev.to/api/articles"
SALIDA = "borradores_devto"

# dev.to acepta como máximo 4 etiquetas y SOLO alfanuméricas: nada de guiones ni
# acentos. `post-quantum` se rechaza; `postquantum` se acepta.
TAGS_POR_TEMA = {
    "criptografia": ["cryptography", "rust", "security", "postquantum"],
    "python": ["python", "programming", "tutorial"],
    "ia": ["ai", "python", "llm"],
    "trading": ["python", "trading", "algorithms"],
    "web": ["python", "webdev", "tutorial"],
}

# Clasificación por slug. Explícita y auditable: un artículo que no esté aquí
# sale con las etiquetas genéricas y se avisa, en vez de adivinar por keywords.
TEMA_POR_SLUG = {
    "sellar-evidencia-digital-firma-post-cuantica": "criptografia",
    "te-roban-la-base-de-datos-y-no-crackean-ni-una-contrasena": "criptografia",
    "que-es-criptografia-post-cuantica": "criptografia",
    "cifrado-hibrido-clasico-post-cuantico": "criptografia",
    "quipu-cifrado-multilenguaje-rust-python-node-go": "criptografia",
    "dimensionar-posicion-sin-pasarse-del-riesgo": "trading",
    "por-que-tu-bot-recibe-403-de-cloudflare-ccxt": "trading",
    "dos-formas-en-que-un-backtest-te-miente": "trading",
    "integrar-llm-ia-en-python": "ia",
    "rag-explicado-llm-con-tus-datos": "ia",
    "nicegui-web-app-python-sin-javascript": "web",
    "como-no-perder-un-reporte-obligaciones-recurrentes": "python",
    "anti-flapping-histeresis-clasificador-ruidoso": "python",
    "repartir-a-varios-canales-sin-que-uno-tumbe-al-resto": "python",
    "i18n-minima-sin-gettext-claves-de-punto-json": "python",
    "automatizar-tareas-con-bot-python": "python",
    "de-la-idea-al-mvp-python-2-semanas": "python",
}


def urls_del_blog():
    """Las URLs de artículo del sitemap. La portada /blog no es un artículo."""
    xml = requests.get(SITEMAP, timeout=20)
    xml.raise_for_status()
    raíz = ET.fromstring(xml.content)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text.strip() for loc in raíz.findall(".//s:loc", ns)]
    return [u for u in urls if "/blog/" in u]


def _meta(html, prop):
    m = re.search(rf'<meta (?:property|name)="{re.escape(prop)}" content="([^"]*)"', html)
    return m.group(1) if m else ""


def _desescapar(s):
    return (s.replace("&#x27;", "'").replace("&quot;", '"').replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))


def extraer(url):
    """
    Saca de un artículo lo que dev.to necesita. Falla ruidosamente si el HTML no
    trae <article>: significa que la plantilla del blog cambió, y publicar la
    página entera (menú, pie, CTA) sería peor que no publicar.
    """
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    html = r.text

    cuerpo = re.search(r"<article[^>]*>(.*?)</article>", html, re.S)
    if not cuerpo:
        raise ValueError(f"{url}: no hay <article>; la plantilla del blog cambió")

    interior = cuerpo.group(1)
    # El CTA y el bloque de etiquetas son navegación del sitio, no del texto.
    interior = re.sub(r'<div class="cta".*?</div>', "", interior, flags=re.S)
    interior = re.sub(r'<div class="tags".*?</div>', "", interior, flags=re.S)

    md = markdownify(interior, heading_style="ATX", code_language="")
    md = re.sub(r"\n{3,}", "\n\n", md).strip()

    título = _desescapar(_meta(html, "og:title")).replace(" | Blog de Xiliux", "").strip()
    if not título:
        raise ValueError(f"{url}: sin og:title")

    # El <h1> del cuerpo repite el título que dev.to ya pinta arriba.
    md = re.sub(rf"^#\s*{re.escape(título)}\s*\n+", "", md).strip()

    slug = url.rstrip("/").rsplit("/", 1)[-1]
    tema = TEMA_POR_SLUG.get(slug)
    if tema is None:
        print(f"  ⚠️  {slug}: sin tema declarado, va con etiquetas genéricas")
        tags = ["python", "programming"]
    else:
        tags = TAGS_POR_TEMA[tema]

    return {
        "slug": slug,
        "title": título,
        "body_markdown": md,
        "description": _desescapar(_meta(html, "og:description"))[:250],
        "canonical_url": url,
        "tags": tags[:4],
        "tema": tema or "(sin declarar)",
    }


def ya_subidos(api_key):
    """
    Los canonical_url que ya existen en la cuenta, publicados o en borrador.

    Sin esto, una segunda corrida sube los 17 otra vez y el duplicado no se ve
    hasta que está publicado dos veces — el mismo fallo que en la cola resuelve
    el índice único. Aquí no hay índice, así que se pregunta antes de escribir.
    """
    cab = {"api-key": api_key, "accept": "application/vnd.forem.api-v1+json"}
    vistos = set()
    for ruta in ("https://dev.to/api/articles/me/all?per_page=1000",
                 "https://dev.to/api/articles/me/unpublished?per_page=1000"):
        r = requests.get(ruta, headers=cab, timeout=30)
        r.raise_for_status()
        for a in r.json():
            if a.get("canonical_url"):
                vistos.add(a["canonical_url"].rstrip("/"))
    return vistos


def soltar(api_key, slug):
    """
    Pasa un borrador ya subido a publicado. Se hace de uno en uno a propósito:
    17 artículos el mismo día en una cuenta recién creada parecen spam, y además
    se entierran entre ellos — cada uno tiene su ventana en el feed o no la tiene.
    """
    cab = {"api-key": api_key, "accept": "application/vnd.forem.api-v1+json",
           "content-type": "application/json"}
    r = requests.get("https://dev.to/api/articles/me/unpublished?per_page=1000",
                     headers=cab, timeout=30)
    r.raise_for_status()
    # Por canónico para lo que viene del blog; por título para las traducciones,
    # que no llevan canónico y quedarían inalcanzables desde aquí.
    candidatos = [a for a in r.json()
                  if (a.get("canonical_url") or "").rstrip("/").endswith(slug)
                  or slug.casefold() in (a.get("title") or "").casefold()]
    if not candidatos:
        raise LookupError(
            f"ningún borrador con canónico terminado en «{slug}» "
            f"ni con «{slug}» en el título")
    if len(candidatos) > 1:
        raise ValueError(f"{len(candidatos)} borradores casan con «{slug}»: precisa más")

    return _marcar_publicado(api_key, candidatos[0])


def soltar_siguiente(api_key):
    """
    Suelta UN borrador sin que nadie elija cuál: el de `id` más bajo, que es el
    primero que se subió. Existe para que un temporizador pueda llamar a esto —
    `--soltar` pide un slug, y un temporizador no tiene de dónde sacarlo.

    Devuelve None cuando no queda nada. La cola vacía es un estado legítimo, no
    un fallo: si esto reventara, el temporizador saldría en rojo todos los días
    a partir del último artículo y nadie volvería a mirar el journal.
    """
    cab = {"api-key": api_key, "accept": "application/vnd.forem.api-v1+json",
           "content-type": "application/json"}
    r = requests.get("https://dev.to/api/articles/me/unpublished?per_page=1000",
                     headers=cab, timeout=30)
    r.raise_for_status()
    borradores = r.json()
    if not borradores:
        return None
    return _marcar_publicado(api_key, min(borradores, key=lambda a: a["id"]))


def _marcar_publicado(api_key, art):
    cab = {"api-key": api_key, "accept": "application/vnd.forem.api-v1+json",
           "content-type": "application/json"}
    p = requests.put(f"https://dev.to/api/articles/{art['id']}", headers=cab,
                     json={"article": {"published": True}}, timeout=30)
    if p.status_code == 200:
        return p.json().get("url", "?")
    raise RuntimeError(f"HTTP {p.status_code} {p.text[:200]}")


def leer_carpeta(carpeta):
    """
    Lee artículos ya escritos de una carpeta, en vez de extraerlos del blog.

    Es la vía para las TRADUCCIONES: no están en el sitemap —el blog es solo
    español— así que `urls_del_blog` no las ve. Cada archivo lleva su frontmatter
    y el resto es el cuerpo.

    Falla ruidosamente si falta el título o las etiquetas (directiva 20): un
    artículo sin título se subiría como «(sin título)» y nadie lo vería hasta
    tenerlo publicado.
    """
    if not os.path.isdir(carpeta):
        raise NotADirectoryError(f"no existe la carpeta «{carpeta}»")

    articulos = []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".md"):
            continue
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()

        m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
        if not m:
            raise ValueError(f"{ruta}: sin frontmatter delimitado por ---")
        cabecera, cuerpo = m.group(1), m.group(2).strip()

        campos = {}
        for linea in cabecera.split("\n"):
            if ":" not in linea:
                continue
            clave, _, valor = linea.partition(":")
            campos[clave.strip()] = valor.strip().strip('"').strip("'")

        titulo = campos.get("title", "").strip()
        if not titulo:
            raise ValueError(f"{ruta}: sin «title» en el frontmatter")
        etiquetas = [t.strip() for t in campos.get("tags", "").split(",") if t.strip()]
        if not etiquetas:
            raise ValueError(f"{ruta}: sin «tags» en el frontmatter")

        # dev.to compone la suya si no se manda; la primera frase es mejor que
        # el primer recorte a ciegas.
        primer_parrafo = next((p for p in cuerpo.split("\n\n")
                               if p.strip() and not p.startswith(("#", "`", ">"))), "")
        articulos.append({
            "slug": nombre[:-3],
            "title": titulo,
            "body_markdown": cuerpo,
            "description": re.sub(r"\s+", " ", re.sub(r"[*_`\[\]]", "", primer_parrafo))[:250],
            # Una traducción NO es contenido duplicado: apuntar el canónico a la
            # versión española declararía ésta como copia de una página en otro
            # idioma. Va como original de dev.to.
            "canonical_url": campos.get("canonical_url") or None,
            "tags": etiquetas[:4],
            "tema": campos.get("tema", "(sin declarar)"),
        })
    if not articulos:
        raise ValueError(f"{carpeta}: no hay ningún .md")
    return articulos


def titulos_subidos(api_key):
    """
    Los títulos que ya existen en la cuenta, publicados o en borrador.

    `ya_subidos` deduplica por `canonical_url`, y las traducciones no lo llevan:
    sin esta segunda llave, una corrida repetida las subiría otra vez y el
    duplicado no se vería hasta estar publicado dos veces.
    """
    cab = {"api-key": api_key, "accept": "application/vnd.forem.api-v1+json"}
    vistos = set()
    for ruta in ("https://dev.to/api/articles/me/all?per_page=1000",
                 "https://dev.to/api/articles/me/unpublished?per_page=1000"):
        r = requests.get(ruta, headers=cab, timeout=30)
        r.raise_for_status()
        for a in r.json():
            if a.get("title"):
                vistos.add(a["title"].strip().casefold())
    return vistos


def publicar(art, api_key, publicado):
    articulo = {"title": art["title"],
                "body_markdown": art["body_markdown"],
                "published": publicado,
                "tags": art["tags"],
                "description": art["description"]}
    # Mandarlo vacío borraría el canónico; se omite cuando no lo hay.
    if art.get("canonical_url"):
        articulo["canonical_url"] = art["canonical_url"]

    r = requests.post(
        API,
        headers={"api-key": api_key,
                 "accept": "application/vnd.forem.api-v1+json",
                 "content-type": "application/json"},
        json={"article": articulo},
        timeout=30,
    )
    if r.status_code == 201:
        return True, r.json().get("url", "?")
    return False, f"HTTP {r.status_code} {r.text[:200]}"


def main():
    p = argparse.ArgumentParser()
    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument("--preparar", action="store_true",
                      help="escribe los markdown en ./%s y no toca dev.to" % SALIDA)
    modo.add_argument("--publicar", action="store_true", help="sube a dev.to")
    modo.add_argument("--soltar", metavar="SLUG",
                      help="pasa a publicado un borrador que ya está en dev.to")
    modo.add_argument("--soltar-siguiente", action="store_true",
                      dest="soltar_siguiente",
                      help="suelta el borrador más antiguo (para el temporizador)")
    modo.add_argument("--borradores", action="store_true",
                      help="lista lo que sigue en borrador en dev.to")
    p.add_argument("--borrador", action="store_true",
                   help="con --publicar: sube como borrador (published=false)")
    p.add_argument("--solo", metavar="SLUG", help="un único artículo, por slug")
    p.add_argument("--desde-carpeta", metavar="DIR", dest="desde_carpeta",
                   help="con --publicar: sube los .md de DIR en vez de extraer "
                        "del blog (para las traducciones, que no están en el "
                        "sitemap). Deduplica por título, no por canónico.")
    args = p.parse_args()

    api_key = os.getenv("DEV_TO_API_KEY", "").strip()
    if (args.publicar or args.soltar or args.soltar_siguiente
            or args.borradores) and not api_key:
        sys.exit("Falta DEV_TO_API_KEY. dev.to → Settings → Extensions → API Keys.")

    if args.soltar:
        print(f"publicado: {soltar(api_key, args.soltar)}")
        return 0

    if args.soltar_siguiente:
        url = soltar_siguiente(api_key)
        print("no queda ningún borrador en dev.to" if url is None
              else f"publicado: {url}")
        return 0

    if args.borradores:
        cab = {"api-key": api_key, "accept": "application/vnd.forem.api-v1+json"}
        r = requests.get("https://dev.to/api/articles/me/unpublished?per_page=1000",
                         headers=cab, timeout=30)
        r.raise_for_status()
        for a in sorted(r.json(), key=lambda x: x["title"]):
            # Las traducciones no tienen canónico: sin esto salen con la columna
            # vacía y parece que les falta algo.
            slug = ((a.get("canonical_url") or "").rstrip("/").rsplit("/", 1)[-1]
                    or "(sin canónico — traducción)")
            print(f"  {slug:<55} {a['title'][:60]}")
        print(f"\n{len(r.json())} en borrador. Soltar uno:"
              f"\n   .venv/bin/python publicar_devto.py --soltar <slug>")
        return 0

    if args.desde_carpeta:
        if args.preparar:
            sys.exit("--desde-carpeta no se combina con --preparar: los .md ya existen")
        fuentes = leer_carpeta(args.desde_carpeta)
        if args.solo:
            fuentes = [a for a in fuentes if a["slug"].endswith(args.solo)]
            if not fuentes:
                sys.exit(f"Ningún .md de «{args.desde_carpeta}» termina en «{args.solo}»")
        print(f"{len(fuentes)} artículos en {args.desde_carpeta}\n")
    else:
        fuentes = urls_del_blog()
        if args.solo:
            fuentes = [u for u in fuentes if u.rstrip("/").endswith(args.solo)]
            if not fuentes:
                sys.exit(f"Ningún artículo del sitemap termina en «{args.solo}»")
        print(f"{len(fuentes)} artículos en el sitemap\n")

    if args.preparar:
        os.makedirs(SALIDA, exist_ok=True)

    # Dos llaves distintas porque son dos fuentes distintas: lo que viene del
    # blog tiene canónico y las traducciones no.
    if not args.publicar:
        subidos = set()
    elif args.desde_carpeta:
        subidos = titulos_subidos(api_key)
    else:
        subidos = ya_subidos(api_key)
    if subidos:
        print(f"{len(subidos)} ya están en dev.to y se saltan\n")

    ok = fallos = saltados = 0
    for i, fuente in enumerate(fuentes, 1):
        if isinstance(fuente, dict):
            art = fuente
        else:
            try:
                art = extraer(fuente)
            except Exception as e:
                print(f"[{i}/{len(fuentes)}] ❌ {e}")
                fallos += 1
                continue

        marca = f"[{i}/{len(fuentes)}] {art['slug'][:52]:<52}"
        clave = (art["title"].strip().casefold() if args.desde_carpeta
                 else (art["canonical_url"] or "").rstrip("/"))
        if clave in subidos:
            print(f"{marca} — ya estaba")
            saltados += 1
            continue

        if args.preparar:
            destino = os.path.join(SALIDA, art["slug"] + ".md")
            with open(destino, "w", encoding="utf-8") as f:
                f.write(f"---\ntitle: {art['title']}\n"
                        f"canonical_url: {art['canonical_url']}\n"
                        f"tags: {', '.join(art['tags'])}\n"
                        f"tema: {art['tema']}\n---\n\n{art['body_markdown']}\n")
            print(f"{marca} {len(art['body_markdown']):>6} car.  {', '.join(art['tags'])}")
            ok += 1
        else:
            bien, detalle = publicar(art, api_key, publicado=not args.borrador)
            print(f"{marca} {'✅ ' + detalle if bien else '❌ ' + detalle}")
            ok += bien
            fallos += not bien
            time.sleep(2)  # dev.to limita a ~10 artículos cada 30 s

    print(f"\n{ok} bien, {saltados} ya estaban, {fallos} con fallo"
          + (f" → ./{SALIDA}/" if args.preparar else ""))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
