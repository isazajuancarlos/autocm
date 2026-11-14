#!/usr/bin/env python3
"""
Prueba de `canva.py` SIN API viva: se sustituye `canva.requests` por un doble que
devuelve las respuestas que documenta la Canva Connect API (autofill job y export
job). Verifica el parseo, la forma del cuerpo que se envía, y —lo que de verdad
importa (directiva 33)— que discrimina: los casos rojos (job fallido, token
ausente, urls vacías, timeout) tienen que FALLAR.

    .venv/bin/python prueba_canva.py

No toca la red ni Canva. Sin framework, como el resto del repo; sale 0 o 1.
"""
import os
import sys
import canva

FALLOS = []


def comprobar(cond, qué):
    print(("  ✔ " if cond else "  ✘ ") + qué)
    if not cond:
        FALLOS.append(qué)


class Resp:
    def __init__(self, status, payload=None, content=b""):
        self.status_code = status
        self._payload = payload or {}
        self.content = content
        self.text = str(payload)

    def json(self):
        return self._payload


class RequestsFalso:
    """Cola de respuestas programada; registra los cuerpos POST para auditarlos."""

    def __init__(self):
        self.respuestas = []   # se van consumiendo en orden
        self.posts = []        # (url, json) de cada POST

    def encolar(self, *resps):
        self.respuestas.extend(resps)

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append((url, json))
        return self.respuestas.pop(0)

    def get(self, url, headers=None, timeout=None):
        return self.respuestas.pop(0)


def con_doble(fn):
    """Corre `fn(fake)` con `canva.requests` sustituido y sin esperas."""
    real, canva.requests = canva.requests, RequestsFalso()
    intervalo, canva.INTERVALO = canva.INTERVALO, 0
    try:
        fn(canva.requests)
    finally:
        canva.requests = real
        canva.INTERVALO = intervalo


# ── autorellenar: cuerpo correcto + design_id del job de éxito ──
def caso_autorellenar(fake):
    fake.encolar(
        Resp(200, {"job": {"id": "job-1", "status": "in_progress"}}),          # POST /autofills
        Resp(200, {"job": {"id": "job-1", "status": "in_progress"}}),          # GET (aún)
        Resp(200, {"job": {"id": "job-1", "status": "success",
                            "result": {"design": {"id": "DAF123"}}}}),         # GET (listo)
    )
    did = canva.autorellenar("tok", "BT9", {"titulo": "Hola", "cuerpo": "Mundo"}, titulo="t")
    comprobar(did == "DAF123", "autorellenar devuelve el design_id del job")
    url, cuerpo = fake.posts[0]
    comprobar(url.endswith("/autofills"), "autofill pega en /autofills")
    comprobar(cuerpo["brand_template_id"] == "BT9", "manda el brand_template_id")
    comprobar(cuerpo["type"] == "create_from_brand_template", "tipo create_from_brand_template")
    comprobar(cuerpo["data"]["titulo"] == {"type": "text", "text": "Hola"},
              "cada campo va como {type:text, text:...}")


# ── exportar_png: url de descarga del job de éxito ──
def caso_exportar(fake):
    fake.encolar(
        Resp(200, {"job": {"id": "ex-1", "status": "in_progress"}}),           # POST /exports
        Resp(200, {"job": {"id": "ex-1", "status": "success",
                           "urls": ["https://dl.canva/x.png", "https://dl.canva/y.png"]}}),
    )
    url = canva.exportar_png("tok", "DAF123")
    comprobar(url == "https://dl.canva/x.png", "exportar_png devuelve la PRIMERA url")
    u, cuerpo = fake.posts[0]
    comprobar(cuerpo == {"design_id": "DAF123", "format": {"type": "png"}},
              "el cuerpo de export pide PNG del design_id")


# ── ROJOS (D33): sin ellos, un instrumento que dice que sí a todo ──
def caso_rojo_job_fallido(fake):
    fake.encolar(
        Resp(200, {"job": {"id": "j", "status": "in_progress"}}),
        Resp(200, {"job": {"id": "j", "status": "failed", "error": {"code": "x"}}}),
    )
    try:
        canva.autorellenar("tok", "BT", {"a": "b"})
        comprobar(False, "un job FALLIDO debe lanzar ErrorCanva")
    except canva.ErrorCanva:
        comprobar(True, "un job FALLIDO lanza ErrorCanva (no devuelve basura)")


def caso_rojo_sin_token(_fake):
    try:
        canva.autorellenar("", "BT", {"a": "b"})
        comprobar(False, "sin token debe lanzar ErrorCanva")
    except canva.ErrorCanva:
        comprobar(True, "sin token lanza ErrorCanva")


def caso_rojo_export_sin_urls(fake):
    fake.encolar(
        Resp(200, {"job": {"id": "e", "status": "in_progress"}}),
        Resp(200, {"job": {"id": "e", "status": "success", "urls": []}}),
    )
    try:
        canva.exportar_png("tok", "D")
        comprobar(False, "un export sin urls debe lanzar ErrorCanva")
    except canva.ErrorCanva:
        comprobar(True, "un export con urls vacías lanza ErrorCanva")


def caso_rojo_timeout(fake):
    # Siempre in_progress: con TIMEOUT_JOB=0 tiene que rendirse ruidoso.
    fake.encolar(*[Resp(200, {"job": {"id": "t", "status": "in_progress"}}) for _ in range(3)])
    t, canva.TIMEOUT_JOB = canva.TIMEOUT_JOB, 0
    try:
        canva.autorellenar("tok", "BT", {"a": "b"})
        comprobar(False, "un job que nunca acaba debe rendirse por timeout")
    except canva.ErrorCanva:
        comprobar(True, "un job colgado se corta por timeout (directiva 39)")
    finally:
        canva.TIMEOUT_JOB = t


# ── el PUENTE imagen_para_post: mapeo de campos + alt + fallo ruidoso ──
def caso_puente():
    import imagen_para_post as ip
    capturado = {}

    def fake_plantilla(token, template_id, campos, destino, titulo=None):
        capturado.update(token=token, template_id=template_id, campos=campos, titulo=titulo)
        return destino

    real, canva.imagen_de_plantilla = canva.imagen_de_plantilla, fake_plantilla
    entorno = {
        "IMAGEN_BACKEND": "canva",
        "CANVA_ACCESS_TOKEN": "T",
        "CANVA_BRAND_TEMPLATE_ID": "BT",
        "CANVA_CAMPO_TITULO": "titular",
        "CANVA_CAMPO_CUERPO": "texto",
    }
    viejo = {k: os.environ.get(k) for k in entorno}
    os.environ.update(entorno)
    try:
        ruta, alt = ip.imagen_para("Cripto en Rust", cuerpo="Sin dependencias C", destino="/tmp/x.png")
        comprobar(ruta == "/tmp/x.png", "imagen_para devuelve la ruta del png")
        comprobar(capturado["campos"] == {"titular": "Cripto en Rust", "texto": "Sin dependencias C"},
                  "mapea título y cuerpo a las CLAVES de campo del entorno")
        comprobar(capturado["template_id"] == "BT", "usa el brand template del entorno")
        comprobar("Cripto en Rust" in alt and "Xiliux" in alt, "el alt describe la tarjeta y su texto")
        # Rojo: sin título no genera nada.
        try:
            ip.imagen_para("   ")
            comprobar(False, "un título vacío debe fallar")
        except ip.ErrorImagen:
            comprobar(True, "un título vacío falla ruidoso (no encola imagen fantasma)")
    finally:
        canva.imagen_de_plantilla = real
        for k, v in viejo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def caso_rojo_puente_sin_config():
    import imagen_para_post as ip
    os.environ["IMAGEN_BACKEND"] = "canva"
    for k in ("CANVA_ACCESS_TOKEN", "CANVA_BRAND_TEMPLATE_ID"):
        os.environ.pop(k, None)
    try:
        ip.imagen_para("Título", token=None, template_id=None)
        comprobar(False, "sin token/plantilla debe fallar")
    except ip.ErrorImagen:
        comprobar(True, "backend canva sin token/plantilla falla ruidoso (D20)")
    finally:
        os.environ.pop("IMAGEN_BACKEND", None)


def caso_tematico():
    import tempfile
    import imagen_para_post as ip
    d = tempfile.mkdtemp(prefix="fondos-tem-")
    for n in ("fondo-generico.png", "fondo-quipu.png", "fondo-productos.png", "fondo-clasico.png"):
        open(os.path.join(d, n), "wb").write(b"x")  # el contenido no importa aquí
    def nombre(titulo, cuerpo=None):
        return os.path.basename(ip._fondo_tematico(titulo, cuerpo, d) or "")
    comprobar(nombre("Criptografía post-cuántica en Rust") == "fondo-quipu.png",
              "un post de cripto/Rust elige el fondo quipu")
    comprobar(nombre("La demo de médico con historia clínica pericial") == "fondo-productos.png",
              "un post de producto elige el fondo productos")
    neutro = nombre("Un backtest de RSI en Python para trading de cripto")  # 'cripto' gana → quipu
    comprobar(neutro == "fondo-quipu.png", "si menciona cripto, aunque sea de Python, va a quipu")
    neutro2 = nombre("Tres trucos de pandas para limpiar datos en Python")
    comprobar(neutro2 in ("fondo-generico.png", "fondo-clasico.png"),
              "un post neutro (Python/datos) usa un fondo neutro, NO uno temático")


if __name__ == "__main__":
    print("Prueba de canva.py (sin red):")
    con_doble(caso_autorellenar)
    con_doble(caso_exportar)
    con_doble(caso_rojo_job_fallido)
    con_doble(caso_rojo_sin_token)
    con_doble(caso_rojo_export_sin_urls)
    con_doble(caso_rojo_timeout)
    caso_puente()
    caso_rojo_puente_sin_config()
    caso_tematico()
    if FALLOS:
        print(f"\n{len(FALLOS)} FALLARON")
        sys.exit(1)
    print("\nTodo verde.")
