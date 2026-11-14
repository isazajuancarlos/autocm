#!/usr/bin/env python3
"""
La vía HÍBRIDA para la imagen de un post: tú diseñas el FONDO de marca en Canva
(gratis en tu plan Educación) y lo exportas a PNG; esto **superpone el texto del
post encima** con Pillow, local y gratis. No necesita la Autofill API de Canva
(que exige Enterprise).

El fondo y la CAJA de texto donde va el título los defines por entorno, porque
dependen de tu diseño (dónde dejaste el hueco):

  TARJETA_FONDO      ruta al PNG del fondo de marca (obligatoria)
  TARJETA_CAJA       "x,y,ancho,alto" de la caja de texto, en píxeles del fondo.
                     Por defecto: una franja centrada al 80 % del ancho.
  TARJETA_FUENTE     ruta a un .ttf (por defecto DejaVu Sans Bold del sistema)
  TARJETA_COLOR      color del texto en hex (por defecto "#FFFFFF")
  TARJETA_SOMBRA     "1" para sombra suave (legibilidad sobre fondos claros); por
                     defecto "1"
  TARJETA_ALINEAR    left|center  (por defecto center)

El texto se ENVUELVE en líneas y el tamaño de fuente se AJUSTA solo hasta caber
en la caja; si aun al mínimo no cabe, se recorta con «…» (no se desborda ni se
sale del diseño).
"""
import os

from PIL import Image, ImageDraw, ImageFont

FUENTE_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MAX_PT = 96
MIN_PT = 18


class ErrorTarjeta(RuntimeError):
    pass


def _cargar_fuente(ruta, pt):
    try:
        return ImageFont.truetype(ruta, pt)
    except OSError as e:
        raise ErrorTarjeta(f"no se pudo abrir la fuente {ruta!r}: {e}") from e


def _envolver(texto, fuente, ancho_max, draw):
    """Envuelve `texto` en líneas que no pasen de `ancho_max` px. Una palabra más
    ancha que la caja se deja en su línea (se encogerá la fuente en otra pasada)."""
    palabras = texto.split()
    lineas, actual = [], ""
    for p in palabras:
        tent = (actual + " " + p).strip()
        if draw.textlength(tent, font=fuente) <= ancho_max or not actual:
            actual = tent
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def _ajustar(texto, ruta_fuente, caja, draw):
    """
    Encuentra el mayor tamaño de fuente cuyo texto envuelto quepa en `caja`
    (w,h). Devuelve (fuente, lineas, alto_linea). Si ni al mínimo cabe, recorta.
    """
    _x, _y, w, h = caja
    for pt in range(MAX_PT, MIN_PT - 1, -2):
        fuente = _cargar_fuente(ruta_fuente, pt)
        lineas = _envolver(texto, fuente, w, draw)
        subida = fuente.getbbox("Ag")
        alto_linea = int((subida[3] - subida[1]) * 1.35)
        cabe_ancho = all(draw.textlength(l, font=fuente) <= w for l in lineas)
        if cabe_ancho and alto_linea * len(lineas) <= h:
            return fuente, lineas, alto_linea
    # Ni al mínimo: recortar por altura y marcar con «…».
    fuente = _cargar_fuente(ruta_fuente, MIN_PT)
    lineas = _envolver(texto, fuente, w, draw)
    subida = fuente.getbbox("Ag")
    alto_linea = int((subida[3] - subida[1]) * 1.35)
    caben = max(1, h // alto_linea)
    if len(lineas) > caben:
        lineas = lineas[:caben]
        lineas[-1] = (lineas[-1][:-1].rstrip() + "…") if lineas[-1] else "…"
    return fuente, lineas, alto_linea


EXTS = (".png", ".jpg", ".jpeg")


def _elegir_fondo(fondo):
    """
    Resuelve `fondo` a un archivo concreto. Si es una CARPETA, elige uno de sus
    fondos AL AZAR (rotación: cada post sale con un fondo distinto, para no
    parecer un bot repitiendo la misma imagen). Si es un archivo, lo usa. Falla
    ruidoso si no hay ninguno (directiva 20).
    """
    import random

    if os.path.isdir(fondo):
        candidatos = sorted(
            os.path.join(fondo, n)
            for n in os.listdir(fondo)
            if n.lower().endswith(EXTS)
        )
        if not candidatos:
            raise ErrorTarjeta(f"la carpeta de fondos no tiene ningún PNG/JPG: {fondo!r}")
        return random.choice(candidatos)
    if not os.path.isfile(fondo):
        raise ErrorTarjeta(f"el fondo no existe: {fondo!r}")
    return fondo


def _caja_por_defecto(im):
    """Una franja centrada al 80 % del ancho y el 40 % central del alto."""
    w, h = im.size
    cw = int(w * 0.8)
    ch = int(h * 0.4)
    return ((w - cw) // 2, (h - ch) // 2, cw, ch)


def _leer_caja(im):
    v = os.getenv("TARJETA_CAJA", "").strip()
    if not v:
        return _caja_por_defecto(im)
    try:
        x, y, w, h = (int(n) for n in v.split(","))
        if w <= 0 or h <= 0:
            raise ValueError
        return (x, y, w, h)
    except ValueError as e:
        raise ErrorTarjeta(f"TARJETA_CAJA mal formada: {v!r} (se espera 'x,y,ancho,alto')") from e


def componer(titulo, fondo=None, destino=None, cuerpo=None):
    """
    Superpone `titulo` (y opcionalmente `cuerpo`) sobre el fondo de marca y
    guarda el PNG en `destino`. Devuelve `destino`. Falla ruidoso si falta el
    fondo o el título (directiva 20): no produce una tarjeta muda.
    """
    if not titulo or not titulo.strip():
        raise ErrorTarjeta("un post sin título no puede rotularse")
    fondo = fondo or os.getenv("TARJETA_FONDO", "").strip()
    if not fondo:
        raise ErrorTarjeta("falta TARJETA_FONDO (el fondo de marca, o la carpeta con varios)")
    fondo = _elegir_fondo(fondo)
    if destino is None:
        import tempfile
        fd, destino = tempfile.mkstemp(prefix="autocm-tarjeta-", suffix=".png")
        os.close(fd)

    fuente_ruta = os.getenv("TARJETA_FUENTE", "").strip() or FUENTE_FALLBACK
    color = os.getenv("TARJETA_COLOR", "#FFFFFF").strip()
    sombra = os.getenv("TARJETA_SOMBRA", "1").strip() != "0"
    alinear = os.getenv("TARJETA_ALINEAR", "center").strip().lower()

    im = Image.open(fondo).convert("RGBA")
    draw = ImageDraw.Draw(im)
    x, y, w, h = _leer_caja(im)

    texto = titulo.strip()
    if cuerpo and cuerpo.strip():
        texto = f"{texto}\n{cuerpo.strip()}"
    # El ajuste trabaja sobre una sola cadena; los saltos explícitos se respetan
    # tratando cada párrafo por separado sería más fino, pero para un título basta
    # con envolver todo junto.
    fuente, lineas, alto_linea = _ajustar(texto.replace("\n", " "), fuente_ruta, (x, y, w, h), draw)

    total = alto_linea * len(lineas)
    cy = y + max(0, (h - total) // 2)   # centrado vertical en la caja
    for linea in lineas:
        lw = draw.textlength(linea, font=fuente)
        lx = x + (w - lw) // 2 if alinear == "center" else x
        if sombra:
            draw.text((lx + 2, cy + 2), linea, font=fuente, fill=(0, 0, 0, 160))
        draw.text((lx, cy), linea, font=fuente, fill=color)
        cy += alto_linea

    im.convert("RGB").save(destino, "PNG")
    return destino
