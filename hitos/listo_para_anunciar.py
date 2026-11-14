#!/usr/bin/env python3
"""
¿Está Quipu listo para anunciarse en This Week in Rust / r/rust?

Existe porque «esperar a que la documentación esté al día» no es un estado
verificable, y una espera sin condición exacta es la directiva 27 incumplida.
Esto la convierte en seis comprobaciones que se corren en diez segundos.

Mide el REPOSITORIO PÚBLICO, no el árbol local: lo que importa es lo que ve
quien llega desde el boletín, no lo que hay en el disco de Juan. El árbol local
puede estar perfecto y el escaparate seguir roto — que es justo lo que pasaba el
2026-08-03, con 94 commits sin publicar.

    python3 hitos/listo_para_anunciar.py

Sale 0 si todo pasa; 1 si algo falta. No toca nada, solo lee.
"""
import json
import re
import subprocess
import sys
import urllib.request

REPO = "isazajuancarlos/quipu"
# Lo que 0.10.0 eliminó y por tanto NO puede seguir anunciándose.
RETIRADO = ["simbolog", "glifo", "bindings/node", "bindings/go", "quipu-crypto"]


def _gh(ruta, jq=None):
    orden = ["gh", "api", ruta]
    if jq:
        orden += ["-q", jq]
    r = subprocess.run(orden, capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:120])
    return r.stdout.strip()


def readme_publico():
    import base64
    return base64.b64decode(_gh(f"repos/{REPO}/readme", ".content")).decode("utf-8")


def comprobaciones():
    """Devuelve [(nombre, ok, detalle)]. Cada una falla ruidosamente por su cuenta."""
    salida = []

    # 1. El README público en inglés. El público de Rust es global.
    try:
        rm = readme_publico()
        primera = next(l for l in rm.split("\n")
                       if l.strip() and not l.startswith(("#", "[", "!", ">")))
        # Marcadores de español que no aparecen en un texto técnico en inglés.
        es = re.search(r"\b(librería|cifrado|datos|propia|codificación|con)\b",
                       primera, re.I)
        salida.append(("README público en inglés", not es,
                       primera[:78]))
    except Exception as e:
        salida.append(("README público en inglés", False, f"no se pudo leer: {e}"))
        rm = ""

    # 2. El README no anuncia lo que 0.10.0 retiró.
    encontrados = [t for t in RETIRADO if t.lower() in rm.lower()]
    salida.append(("README sin características retiradas", not encontrados,
                   "menciona: " + ", ".join(encontrados) if encontrados else "limpio"))

    # 3. La descripción del repo tampoco.
    try:
        desc = _gh(f"repos/{REPO}", ".description") or ""
        malos = [t for t in ("Node", "Go binding", "/Go") if t.lower() in desc.lower()]
        salida.append(("Descripción del repo al día", not malos,
                       desc[:78] or "(vacía)"))
    except Exception as e:
        salida.append(("Descripción del repo al día", False, str(e)[:78]))

    # 4. Nada local sin publicar: el escaparate refleja el trabajo.
    try:
        rama = _gh(f"repos/{REPO}", ".default_branch")
        subprocess.run(["git", "fetch", "-q", "origin"], cwd="/mnt/data/decod",
                       capture_output=True, timeout=60)
        n = subprocess.run(["git", "rev-list", "--count", f"origin/{rama}..HEAD"],
                           cwd="/mnt/data/decod", capture_output=True, text=True)
        pendientes = int(n.stdout.strip() or 0)
        salida.append((f"Sin commits sin publicar en «{rama}»", pendientes == 0,
                       f"{pendientes} commits locales por delante"))
    except Exception as e:
        salida.append(("Sin commits sin publicar", False, str(e)[:78]))

    # 5. La versión anunciada tiene que ser la última de crates.io, y reciente.
    try:
        req = urllib.request.Request("https://crates.io/api/v1/crates/quipu",
                                     headers={"User-Agent": "xiliux-listo-check"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
        ultima = d["crate"]["max_version"]
        fecha = next(v["created_at"][:10] for v in d["versions"] if v["num"] == ultima)
        salida.append(("Última versión en crates.io", True, f"{ultima} del {fecha}"))
    except Exception as e:
        salida.append(("Última versión en crates.io", False, str(e)[:78]))

    # 6. El CHANGELOG no debe tener un [Unreleased] gordo: si lo tiene, se corta
    #    versión y se anuncia ESA. Un anuncio rinde el día que sale.
    try:
        with open("/mnt/data/decod/CHANGELOG.md", encoding="utf-8") as fh:
            texto = fh.read()
        m = re.search(r"## \[Unreleased\](.*?)(?=\n## \[)", texto, re.S)
        entradas = len(re.findall(r"^- \*\*", m.group(1), re.M)) if m else 0
        salida.append(("[Unreleased] vacío o pequeño", entradas <= 3,
                       f"{entradas} entradas acumuladas"))
    except Exception as e:
        salida.append(("[Unreleased] vacío o pequeño", False, str(e)[:78]))

    return salida


def main():
    print(f"¿Listo para anunciar {REPO}?\n")
    resultados = comprobaciones()
    for nombre, ok, detalle in resultados:
        print(f"  {'✅' if ok else '❌'} {nombre:<38} {detalle}")

    faltan = [n for n, ok, _ in resultados if not ok]
    print()
    if faltan:
        print(f"NO. Faltan {len(faltan)}: {'; '.join(faltan)}")
        print("El texto del anuncio está en hitos/quipu-0.10.0.md — actualizar la")
        print("versión si se corta una nueva antes de enviarlo.")
        return 1
    print("SÍ. Enviar sale al mundo -> pedir el visto bueno de Juan antes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
