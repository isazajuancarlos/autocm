#!/usr/bin/env python3
"""
Prepara el avatar y el banner a partir de la imagen canónica de Xiliux.

La original (`/mnt/data/documentos/gato_xiliux.png`, 2048×2048, 3,8 MB) no sirve
tal cual por dos razones medidas:

- **Pesa demasiado.** Bluesky corta el blob del avatar en ~1 MB.
- **La figura ocupa el 63 % del ancho y está descentrada** (su centro está en
  950,1099 y el del lienzo en 1024,1024). A 96 px —el tamaño real de un avatar
  en una lista— el gato queda diminuto y rodeado de fondo vacío.

Así que se reencuadra: mismo dibujo, mismo fondo, mismo color; solo se recorta
el margen sobrante y se centra en la figura. No se retoca la marca.

    .venv/bin/python imagenes_marca.py
"""
import os
import sys

import numpy as np
from PIL import Image

CANÓNICA = os.getenv("XILIUX_LOGO", "/mnt/data/documentos/gato_xiliux.png")
SALIDA = "marca"

AVATAR = 1000          # Bluesky recomienda 1000×1000; Mastodon escala solo
BANNER = (3000, 1000)  # el de Bluesky; el de Mastodon (1500×500) es la mitad
TOPE_AVATAR = 1_000_000

# Cuánto respirar alrededor de la figura, en fracción de su lado mayor. 0.12
# deja el gato al ~84 % del cuadro: se reconoce a 96 px y no toca los bordes.
AIRE = 0.12


def caja_de_la_figura(im):
    """
    Dónde está el gato. Por color y no por diferencia con el fondo: el fondo es
    un degradado y además hay una sombra y un destello en la esquina, que una
    resta contra el color de esquina cuenta como figura. El cobre tiene R muy
    por encima de B; el fondo azul y el destello blanco, no.
    """
    a = np.asarray(im.convert("RGB")).astype(int)
    cálido = (a[:, :, 0] - a[:, :, 2]) > 30
    ys, xs = np.where(cálido)
    if not len(xs):
        raise ValueError("no se encontró la figura de cobre en la imagen")
    return xs.min(), ys.min(), xs.max(), ys.max()


def recorte_cuadrado(im, caja):
    x0, y0, x1, y1 = caja
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    lado = int(max(x1 - x0, y1 - y0) * (1 + 2 * AIRE))
    # Sin salirse del lienzo: si el cuadro ideal se sale, se desplaza en vez de
    # encogerse, para no perder aire de un lado y quedarse sin él del otro.
    lado = min(lado, im.width, im.height)
    izq = min(max(cx - lado // 2, 0), im.width - lado)
    arr = min(max(cy - lado // 2, 0), im.height - lado)
    return im.crop((izq, arr, izq + lado, arr + lado))


def guardar_bajo_tope(im, ruta, tope):
    """PNG optimizado; si no cabe, paleta; si tampoco, JPEG. Y se dice cuál salió."""
    im.save(ruta, "PNG", optimize=True)
    if os.path.getsize(ruta) <= tope:
        return "PNG", os.path.getsize(ruta)
    im.convert("P", palette=Image.ADAPTIVE, colors=256).save(ruta, "PNG", optimize=True)
    if os.path.getsize(ruta) <= tope:
        return "PNG (256 colores)", os.path.getsize(ruta)
    ruta_jpg = os.path.splitext(ruta)[0] + ".jpg"
    im.convert("RGB").save(ruta_jpg, "JPEG", quality=90, optimize=True)
    os.remove(ruta)
    return "JPEG q90", os.path.getsize(ruta_jpg)


def hacer_banner(im, caja):
    """
    El cuadro del avatar ocupando la derecha, y el resto del ancho relleno
    estirando su propia columna del borde.

    El primer intento pegaba el gato recortado sobre una franja del fondo, y se
    veía el rectángulo del parche: dos trozos del mismo degradado radial tomados
    de sitios distintos no casan. Estirando la columna de unión no hay dos
    fondos que casar — es literalmente el mismo píxel continuado, así que no
    puede haber costura.
    """
    ancho, alto = BANNER
    cuadro = recorte_cuadrado(im, caja).resize((alto, alto), Image.LANCZOS).convert("RGB")

    lienzo = Image.new("RGB", (ancho, alto))
    izquierda = ancho - alto
    # La columna 0 del cuadro es fondo puro (el aire del reencuadre), y conserva
    # su degradado vertical al estirarse a lo ancho.
    lienzo.paste(cuadro.crop((0, 0, 1, alto)).resize((izquierda, alto)), (0, 0))
    lienzo.paste(cuadro, (izquierda, 0))
    return lienzo


def main():
    if not os.path.exists(CANÓNICA):
        sys.exit(f"No está la imagen canónica: {CANÓNICA}")
    os.makedirs(SALIDA, exist_ok=True)

    im = Image.open(CANÓNICA)
    caja = caja_de_la_figura(im)
    x0, y0, x1, y1 = caja
    print(f"canónica : {im.size[0]}×{im.size[1]}, {os.path.getsize(CANÓNICA)/1e6:.1f} MB")
    print(f"figura   : {x1-x0}×{y1-y0} px, "
          f"{100*(x1-x0)/im.width:.0f}% del ancho, centro ({(x0+x1)//2},{(y0+y1)//2})")

    cuadro = recorte_cuadrado(im, caja).resize((AVATAR, AVATAR), Image.LANCZOS)
    ocupa = 100 * (x1 - x0) / (recorte_cuadrado(im, caja).width)
    ruta = os.path.join(SALIDA, "avatar.png")
    formato, peso = guardar_bajo_tope(cuadro, ruta, TOPE_AVATAR)
    print(f"avatar   : {AVATAR}×{AVATAR}, {formato}, {peso/1000:.0f} kB "
          f"→ la figura pasa a ocupar el {ocupa:.0f}% del cuadro")

    banner = hacer_banner(im, caja)
    ruta_b = os.path.join(SALIDA, "banner.png")
    # El mismo tope que el avatar: Bluesky corta cualquier blob de imagen ahí,
    # no solo el del avatar. Mastodon admite más, pero una sola imagen para los
    # dos evita mantener dos.
    formato_b, peso_b = guardar_bajo_tope(banner, ruta_b, TOPE_AVATAR)
    print(f"banner   : {BANNER[0]}×{BANNER[1]}, {formato_b}, {peso_b/1000:.0f} kB")
    print(f"\nen ./{SALIDA}/ — míralos antes de subirlos")


if __name__ == "__main__":
    main()
