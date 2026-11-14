#!/usr/bin/env python3
"""
El PUENTE entre un post y su imagen de Canva: dado el texto de una publicación,
genera la tarjeta de marca con `canva.py` y devuelve `(ruta_png, texto_alt)`,
listo para `cola.encolar(..., imagen=ruta, imagen_alt=alt)`.

Qué campos de la plantilla se rellenan lo decides tú al crear la Brand Template
en Canva; aquí se mapean por variables de entorno para no cablear nombres que la
plantilla podría no tener:

  CANVA_BRAND_TEMPLATE_ID   la plantilla (obligatoria)
  CANVA_CAMPO_TITULO        clave del campo de texto del título   (por defecto: titulo)
  CANVA_CAMPO_CUERPO        clave del campo de texto del cuerpo   (opcional)
  CANVA_ACCESS_TOKEN        el token de canva_oauth.py

El `alt` NO es decorativo: la cola RECHAZA una imagen sin texto alternativo
(accesibilidad). Se construye describiendo la tarjeta y su texto.
"""
import os
import tempfile

import canva


class ErrorImagen(RuntimeError):
    """Falló generar la imagen, con cualquier backend. El llamante captura ESTA
    y decide degradar a texto o abortar la nota."""


# Palabras clave por TEMA. La clave (p. ej. "quipu") tiene que aparecer también
# en el NOMBRE del fondo (fondo-quipu.jpg) para que se emparejen.
TEMAS = {
    "quipu": ["quipu", "cripto", "criptograf", "cifrad", "passkey", "post-cu",
              "chuspa", " rust", "seguridad", "kyber", "dilithium", "argon",
              "bóveda", "boveda", "contraseñ", "vulnerab"],
    "productos": ["medico", "médico", "informes", "inventario", "chasqui", "demo",
                  "historia clínica", "historia clinica", "dashboard", "factura",
                  "secop", "panel", "pericial"],
}


def _fondo_tematico(titulo, cuerpo, carpeta):
    """
    Elige el fondo de `carpeta` según el TEMA del post. Si el texto encaja en un
    tema y hay un fondo con ese nombre, lo usa; si no, uno NEUTRO (los que no son
    de ningún tema) al azar. Devuelve una ruta, o `None` si la carpeta no sirve
    (y entonces `tarjeta.componer` cae a TARJETA_FONDO / falla ruidoso).
    """
    import random

    try:
        fondos = [
            os.path.join(carpeta, n)
            for n in os.listdir(carpeta)
            if n.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
    except OSError:
        return None
    if not fondos:
        return None

    texto = f"{titulo} {cuerpo or ''}".lower()
    for tema, palabras in TEMAS.items():
        if any(p in texto for p in palabras):
            del_tema = [f for f in fondos if tema in os.path.basename(f).lower()]
            if del_tema:
                return random.choice(del_tema)
    # Neutro: los fondos cuyo nombre no menciona ningún tema.
    temas = tuple(TEMAS)
    neutros = [f for f in fondos if not any(t in os.path.basename(f).lower() for t in temas)]
    return random.choice(neutros or fondos)


def _destino_persistente(titulo):
    """
    Ruta ABSOLUTA en un directorio ESTABLE para la tarjeta (no `/tmp`): la cola
    la guardará y la publicará días después. `IMAGEN_DIR` la fija; por defecto un
    `tarjetas/` junto a este módulo (así viaja con el repo al VPS). Nombre único
    por fecha + hash del título, para no pisar ni acumular colisiones.
    """
    import time
    import hashlib

    base = os.getenv("IMAGEN_DIR", "").strip() or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "tarjetas"
    )
    os.makedirs(base, exist_ok=True)
    marca = time.strftime("%Y%m%d-%H%M%S")
    h = hashlib.sha1(titulo.encode("utf-8")).hexdigest()[:8]
    return os.path.abspath(os.path.join(base, f"tarjeta-{marca}-{h}.png"))


def _env(clave, defecto=None, obligatoria=False):
    v = os.getenv(clave, "").strip()
    if not v and obligatoria:
        raise canva.ErrorCanva(f"falta {clave} en el entorno")
    return v or defecto


def texto_alt(titulo, cuerpo=None):
    """
    Un `alt` que describe la IMAGEN (una tarjeta de marca con el texto), no que
    repite el post. Accesible y honesto: dice qué se ve.
    """
    base = f"Tarjeta de la marca Xiliux con el texto: «{titulo.strip()}»"
    if cuerpo and cuerpo.strip():
        base += f". {cuerpo.strip()}"
    # Los lectores de pantalla y algunas redes cortan el alt largo; se acota.
    return base[:420]


def imagen_para(titulo, cuerpo=None, destino=None, token=None, template_id=None):
    """
    Genera la tarjeta del post y devuelve `(ruta_png, alt)`. Dos backends, según
    `IMAGEN_BACKEND` (por defecto `tarjeta`):

      tarjeta  — HÍBRIDA (por defecto): texto sobre un fondo de marca de Canva con
                 Pillow, local y gratis. No necesita Canva Enterprise.
      canva    — Autofill de Canva (requiere organización Enterprise).

    Falla ruidoso si falta configuración (directiva 20): no encola una imagen que
    no existe.
    """
    if not titulo or not titulo.strip():
        raise ErrorImagen("un post sin título no puede generar tarjeta")

    # La tarjeta debe PERSISTIR: la cola guarda borradores días antes de que el
    # temporizador los publique, y guarda la ruta ABSOLUTA. Un `/tmp` mkstemp se
    # limpiaría y `publicar_cola._leer_imagen` fallaría al publicar. Por eso el
    # destino por defecto va a un directorio estable (IMAGEN_DIR, junto al repo).
    if destino is None:
        destino = _destino_persistente(titulo)

    backend = os.getenv("IMAGEN_BACKEND", "tarjeta").strip().lower()
    try:
        if backend == "canva":
            ruta = _con_canva(titulo, cuerpo, destino, token, template_id)
        else:
            import tarjeta
            # Si TARJETA_FONDO es una CARPETA, se elige el fondo por TEMA del post
            # (cripto→quipu, productos→productos, resto→neutro). Si es un archivo
            # suelto, se usa ese y ya.
            fondo_env = os.getenv("TARJETA_FONDO", "").strip()
            fondo = _fondo_tematico(titulo, cuerpo, fondo_env) if os.path.isdir(fondo_env) else None
            ruta = tarjeta.componer(titulo, fondo=fondo, destino=destino, cuerpo=cuerpo)
    except Exception as e:
        # Se unifica en ErrorImagen para que el llamante capture una sola clase
        # (ErrorCanva, ErrorTarjeta, un fallo de Pillow…) y decida degradar a texto.
        raise ErrorImagen(f"backend {backend}: {e}") from e

    return ruta, texto_alt(titulo, cuerpo)


def _con_canva(titulo, cuerpo, destino, token, template_id):
    token = token or _env("CANVA_ACCESS_TOKEN", obligatoria=True)
    template_id = template_id or _env("CANVA_BRAND_TEMPLATE_ID", obligatoria=True)
    campos = {_env("CANVA_CAMPO_TITULO", "titulo"): titulo.strip()}
    campo_cuerpo = _env("CANVA_CAMPO_CUERPO")
    if campo_cuerpo and cuerpo and cuerpo.strip():
        campos[campo_cuerpo] = cuerpo.strip()
    if destino is None:
        fd, destino = tempfile.mkstemp(prefix="autocm-canva-", suffix=".png")
        os.close(fd)
    return canva.imagen_de_plantilla(token, template_id, campos, destino, titulo=titulo)

