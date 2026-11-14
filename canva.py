#!/usr/bin/env python3
"""
Cliente mínimo de la **Canva Connect API** para generar la imagen de un post a
partir de una PLANTILLA DE MARCA (Brand Template) con campos de autorrelleno.

El flujo, todo asíncrono por *jobs* que hay que sondear:

  1. Autofill  (`POST /v1/autofills`)  — rellena la plantilla con el texto del
     post → devuelve un job; al terminar da `job.result.design.id`.
  2. Export    (`POST /v1/exports`)    — exporta ese diseño a PNG → job; al
     terminar da `job.urls[0]` (un enlace de descarga que caduca a las 24 h).
  3. Se descarga el PNG a un archivo local, listo para `cola.encolar(...)`.

**Requisitos que NO están en el código** (los pone Juan, ver `docs/CANVA.md`):
  - Una organización **Canva Enterprise** (la Autofill API la exige; con un plan
    de pago hay acceso *trial* durante el desarrollo).
  - Una app de desarrollador (CANVA_CLIENT_ID / CANVA_CLIENT_SECRET) con la URL
    de redirección y los scopes `design:content:write` y `design:content:read`.
  - Una **Brand Template** con campos de texto, cuyas CLAVES (p. ej. `titulo`,
    `cuerpo`) se pasan en `campos`.
  - Un token, que obtiene y refresca `canva_oauth.py`.

Este módulo NO decide qué texto va en la imagen ni encola nada: solo habla con
Canva. La orquestación (mapear un post → campos → encolar) vive en
`imagen_para_post.py`.
"""
import os
import time
import requests

BASE = "https://api.canva.com/rest/v1"

# Sondeo de los jobs: Canva no promete un plazo, así que se acota (directiva 39:
# toda espera con tope). Un diseño de una tarjeta simple termina en segundos.
TIMEOUT_JOB = 90          # segundos como mucho por job
INTERVALO = 2.0           # segundos entre sondeos


class ErrorCanva(RuntimeError):
    """Algo salió mal hablando con Canva. El mensaje NO lleva el token."""


def _cabeceras(token):
    if not token:
        raise ErrorCanva("falta el token de Canva (corre canva_oauth.py)")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _sondear(url, token, extraer, que):
    """
    Sondea un endpoint de job hasta `status == success`, o falla ruidoso. Devuelve
    `extraer(job)` en el éxito. `que` es una etiqueta para los mensajes.
    """
    fin = time.monotonic() + TIMEOUT_JOB
    while True:
        r = requests.get(url, headers=_cabeceras(token), timeout=30)
        if r.status_code != 200:
            raise ErrorCanva(f"{que}: el sondeo devolvió HTTP {r.status_code}: {r.text[:200]}")
        job = r.json().get("job", {})
        estado = job.get("status")
        if estado == "success":
            return extraer(job)
        if estado == "failed":
            # Canva mete el motivo en job.error; no lleva secretos.
            raise ErrorCanva(f"{que}: Canva reportó el job como fallido: {job.get('error')}")
        if estado != "in_progress":
            raise ErrorCanva(f"{que}: estado de job inesperado: {estado!r}")
        if time.monotonic() > fin:
            raise ErrorCanva(f"{que}: el job no terminó en {TIMEOUT_JOB}s (sigue {estado})")
        time.sleep(INTERVALO)


def autorellenar(token, brand_template_id, campos, titulo=None):
    """
    Crea un diseño rellenando `brand_template_id` con `campos` (un dict
    `{clave_de_campo: texto}`; las claves las define la plantilla en Canva).
    Devuelve el `design_id`. Los campos que la plantilla no tenga se ignoran en
    silencio (comportamiento de Canva), así que las claves deben cuadrar.
    """
    if not brand_template_id:
        raise ErrorCanva("falta CANVA_BRAND_TEMPLATE_ID")
    data = {clave: {"type": "text", "text": str(valor)} for clave, valor in campos.items()}
    cuerpo = {
        "type": "create_from_brand_template",
        "brand_template_id": brand_template_id,
        "data": data,
    }
    if titulo:
        cuerpo["title"] = titulo[:255]
    r = requests.post(f"{BASE}/autofills", headers=_cabeceras(token), json=cuerpo, timeout=30)
    if r.status_code not in (200, 202):
        raise ErrorCanva(f"autofill: HTTP {r.status_code}: {r.text[:300]}")
    job_id = r.json().get("job", {}).get("id")
    if not job_id:
        raise ErrorCanva(f"autofill: la respuesta no trae job.id: {r.text[:200]}")
    return _sondear(
        f"{BASE}/autofills/{job_id}",
        token,
        extraer=lambda job: _design_id(job),
        que="autofill",
    )


def _design_id(job):
    dis = job.get("result", {}).get("design", {})
    did = dis.get("id")
    if not did:
        raise ErrorCanva(f"autofill: el job terminó sin design.id: {job}")
    return did


def exportar_png(token, design_id):
    """
    Exporta `design_id` a PNG y devuelve el ENLACE de descarga (caduca a las
    24 h). Se pide la primera página; una tarjeta de post es de una sola.
    """
    cuerpo = {"design_id": design_id, "format": {"type": "png"}}
    r = requests.post(f"{BASE}/exports", headers=_cabeceras(token), json=cuerpo, timeout=30)
    if r.status_code not in (200, 202):
        raise ErrorCanva(f"export: HTTP {r.status_code}: {r.text[:300]}")
    job_id = r.json().get("job", {}).get("id")
    if not job_id:
        raise ErrorCanva(f"export: la respuesta no trae job.id: {r.text[:200]}")
    return _sondear(
        f"{BASE}/exports/{job_id}",
        token,
        extraer=lambda job: _primer_url(job),
        que="export",
    )


def _primer_url(job):
    urls = job.get("urls") or []
    if not urls:
        raise ErrorCanva(f"export: el job terminó sin urls: {job}")
    return urls[0]


def descargar(url, destino):
    """Descarga `url` (el PNG exportado) a `destino`. Devuelve `destino`."""
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        raise ErrorCanva(f"descarga: HTTP {r.status_code}")
    tam = len(r.content)
    if tam == 0:
        raise ErrorCanva("descarga: el PNG vino vacío")
    with open(destino, "wb") as fh:
        fh.write(r.content)
    return destino


def imagen_de_plantilla(token, brand_template_id, campos, destino, titulo=None):
    """
    El flujo entero: autorrellena la plantilla, exporta a PNG y lo descarga a
    `destino`. Devuelve `destino`. Es lo que llama `imagen_para_post.py`.
    """
    design_id = autorellenar(token, brand_template_id, campos, titulo=titulo)
    url = exportar_png(token, design_id)
    return descargar(url, destino)
