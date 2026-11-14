#!/usr/bin/env python3
"""
Prueba del generador híbrido `tarjeta.py`: superpone el texto del post sobre un
fondo de marca. Cruza la frontera del programa (directiva 28): genera un PNG de
verdad y lo RELEE para comprobar que el texto se dibujó DENTRO de la caja y NO
fuera (directiva 33), además de los casos rojos (sin fondo, sin título).

    .venv/bin/python prueba_tarjeta.py

Usa un fondo sintético (color sólido), así que no necesita el diseño real de
Canva. Sin framework; sale 0 o 1.
"""
import os
import sys
import tempfile

from PIL import Image

import tarjeta

FALLOS = []


def comprobar(cond, qué):
    print(("  ✔ " if cond else "  ✘ ") + qué)
    if not cond:
        FALLOS.append(qué)


def fondo_de_prueba(w=1200, h=630, color=(20, 30, 60)):
    fd, ruta = tempfile.mkstemp(prefix="fondo-", suffix=".png")
    os.close(fd)
    Image.new("RGB", (w, h), color).save(ruta, "PNG")
    return ruta


def pixeles_distintos(a, b, caja):
    """Cuántos píxeles difieren entre las imágenes `a` y `b` dentro de `caja`."""
    x, y, w, h = caja
    ia = Image.open(a).convert("RGB").crop((x, y, x + w, y + h))
    ib = Image.open(b).convert("RGB").crop((x, y, x + w, y + h))
    da, db = ia.getdata(), ib.getdata()
    return sum(1 for pa, pb in zip(da, db) if pa != pb)


def caso_dibuja_en_la_caja():
    fondo = fondo_de_prueba()
    # Caja explícita para poder mirar dentro y fuera de ella.
    os.environ["TARJETA_CAJA"] = "100,250,1000,150"
    try:
        fd, salida = tempfile.mkstemp(prefix="out-", suffix=".png"); os.close(fd)
        tarjeta.componer("Criptografía en Rust sin dependencias de C", fondo=fondo, destino=salida)
        comprobar(os.path.getsize(salida) > 0, "produce un PNG no vacío")
        w, h = Image.open(salida).size
        comprobar((w, h) == (1200, 630), "conserva el tamaño del fondo")
        # DENTRO de la caja: el texto cambió muchos píxeles.
        dentro = pixeles_distintos(fondo, salida, (100, 250, 1000, 150))
        comprobar(dentro > 500, f"el texto se dibuja DENTRO de la caja ({dentro} px cambiados)")
        # FUERA de la caja (esquina superior): NADA cambió → el texto no se desborda.
        fuera = pixeles_distintos(fondo, salida, (0, 0, 80, 80))
        comprobar(fuera == 0, "no se dibuja NADA fuera de la caja (esquina intacta)")
    finally:
        os.environ.pop("TARJETA_CAJA", None)


def caso_titulo_larguisimo_no_desborda():
    fondo = fondo_de_prueba()
    os.environ["TARJETA_CAJA"] = "100,250,1000,120"
    try:
        fd, salida = tempfile.mkstemp(prefix="out-", suffix=".png"); os.close(fd)
        largo = "palabra " * 80  # mucho más de lo que cabe: debe encoger/recortar
        tarjeta.componer(largo, fondo=fondo, destino=salida)
        comprobar(os.path.getsize(salida) > 0, "un título larguísimo no revienta, produce PNG")
        fuera = pixeles_distintos(fondo, salida, (0, 500, 1200, 130))  # debajo de la caja
        comprobar(fuera == 0, "aun con texto larguísimo, nada se sale por debajo de la caja")
    finally:
        os.environ.pop("TARJETA_CAJA", None)


def caso_rotacion():
    """Un directorio de fondos rota: componer elige uno de los que hay, y una
    carpeta sin fondos falla ruidoso."""
    import tempfile
    d = tempfile.mkdtemp(prefix="fondos-")
    # dos fondos de colores distintos
    Image.new("RGB", (1200, 630), (20, 30, 60)).save(os.path.join(d, "a.png"))
    Image.new("RGB", (1200, 630), (60, 30, 20)).save(os.path.join(d, "b.png"))
    os.environ["TARJETA_CAJA"] = "100,250,1000,150"
    try:
        todas_ok = True
        elegidos = set()
        for _ in range(12):
            fd, salida = tempfile.mkstemp(prefix="rot-", suffix=".png"); os.close(fd)
            tarjeta.componer("Título de prueba para rotación", fondo=d, destino=salida)
            todas_ok = todas_ok and os.path.getsize(salida) > 0
            elegidos.add(tarjeta._elegir_fondo(d))
        comprobar(todas_ok, "cada corrida sobre la carpeta produce un PNG")
        comprobar(all(os.path.isfile(x) for x in elegidos),
                  "la rotación resuelve SIEMPRE a un archivo existente de la carpeta")
        vacia = tempfile.mkdtemp(prefix="fondos-vac-")
        try:
            tarjeta.componer("X", fondo=vacia, destino="/tmp/x.png")
            comprobar(False, "una carpeta de fondos vacía debe fallar")
        except tarjeta.ErrorTarjeta:
            comprobar(True, "una carpeta de fondos vacía falla ruidoso")
    finally:
        os.environ.pop("TARJETA_CAJA", None)


def caso_rojo_sin_fondo():
    try:
        tarjeta.componer("Hola", fondo="/no/existe/fondo.png", destino="/tmp/x.png")
        comprobar(False, "un fondo inexistente debe fallar")
    except tarjeta.ErrorTarjeta:
        comprobar(True, "un fondo inexistente falla ruidoso (D20)")


def caso_rojo_sin_titulo():
    fondo = fondo_de_prueba()
    try:
        tarjeta.componer("   ", fondo=fondo, destino="/tmp/x.png")
        comprobar(False, "un título vacío debe fallar")
    except tarjeta.ErrorTarjeta:
        comprobar(True, "un título vacío falla ruidoso (no hace una tarjeta muda)")


def caso_rojo_caja_mal_formada():
    fondo = fondo_de_prueba()
    os.environ["TARJETA_CAJA"] = "esto,no,es,una-caja"
    try:
        tarjeta.componer("Hola", fondo=fondo, destino="/tmp/x.png")
        comprobar(False, "una TARJETA_CAJA mal formada debe fallar")
    except tarjeta.ErrorTarjeta:
        comprobar(True, "TARJETA_CAJA mal formada falla ruidoso, no la ignora")
    finally:
        os.environ.pop("TARJETA_CAJA", None)


if __name__ == "__main__":
    print("Prueba de tarjeta.py (híbrida, con Pillow):")
    caso_dibuja_en_la_caja()
    caso_titulo_larguisimo_no_desborda()
    caso_rotacion()
    caso_rojo_sin_fondo()
    caso_rojo_sin_titulo()
    caso_rojo_caja_mal_formada()
    if FALLOS:
        print(f"\n{len(FALLOS)} FALLARON")
        sys.exit(1)
    print("\nTodo verde.")
