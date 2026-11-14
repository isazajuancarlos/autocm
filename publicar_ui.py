#!/usr/bin/env python3
"""
Publicador por UI web: conduce la interfaz logueada de Instagram y Threads con
Playwright, para las redes que NO tienen API orgánica asequible.

Es la pieza gemela de `publicar_cola.py`. Aquel entrega por API (bluesky,
mastodon, facebook); éste entrega conduciendo el navegador, porque Instagram y
Threads no dan otra vía barata. Consume la MISMA cola y respeta la MISMA
invariante: quién puede sacar qué lo decide `cola.py` (`reclamar`), no este
fichero. Instagram y Threads son SENSIBLES, así que solo ven lo `aprobado`.

    # UNA vez por red y por máquina: iniciar sesión a mano (abre navegador).
    .venv/bin/python publicar_ui.py --login instagram
    .venv/bin/python publicar_ui.py --login threads

    # X (y cualquier red que bloquee el login en el Chromium automatizado):
    # NO se usa --login. Juan inicia sesión en el Firefox REAL (navegador seguro
    # de chuspa) y se TRASPLANTA esa sesión al perfil de Playwright:
    .venv/bin/python publicar_ui.py --importar-sesion x

    # Ensayo SIN publicar: rellena el formulario y se detiene antes de pulsar.
    # Es la forma de VERIFICAR los selectores contra el DOM vivo (ver abajo).
    .venv/bin/python publicar_ui.py --destino threads --simulacro
    .venv/bin/python publicar_ui.py --destino instagram --simulacro --headful

    # Publicar de verdad (consume la cola, marca publicado/fallido).
    .venv/bin/python publicar_ui.py --destino threads --limite 1

== POR QUÉ CONFIRMA, Y POR QUÉ FALLA RUIDOSO ==

La extensión MultiPost de la que se portan los selectores hace clic en "publicar"
y termina: no comprueba si publicó, y si un selector no casa imprime a la consola
y sigue. Eso es el falso-verde que la directiva 30 existe para impedir —una fila
quedaría marcada como enviada sin haber salido, y nadie lo vería—. Aquí cada
publicación se CONFIRMA (el compositor se cierra) y, si no se confirma, se levanta
una excepción que el bucle convierte en `marcar_fallido` con el motivo. Una fila
fallida es visible; un envío perdido, no.

== VERIFICACIÓN DE SELECTORES (directiva 30/28) ==

Los selectores de abajo están PORTADOS de MultiPost-Extension (Apache-2.0, ver
NOTICE) y NO se han verificado contra el DOM vivo de las cuentas de Xiliux —esas
cuentas aún se logean a mano con `--login`—. Hasta que `--simulacro` pase contra
la UI real, este publicador es ANDAMIAJE, no un camino probado: una pantalla hay
que DIBUJARLA (directiva 28), y estas redes ofuscan sus clases y cambian la
maquetación sin avisar. Cuando `--simulacro` pase, se anota la fecha en
`VERIFICADO` de cada red.

Las credenciales de sesión (cookies) viven en PERFILES_UI_DIR, FUERA del
repositorio: una cookie de sesión es acceso total a la cuenta, saltándose el 2FA.
"""
import argparse
import os
import sys
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

import cola

load_dotenv()

# Las redes que este publicador sabe conducir. El resto de destinos van por API
# (publicar_cola.py) o a mano; pedir uno de esos aquí es un error, no un no-op.
REDES_UI = {"instagram", "threads", "x"}

# La URL de cada red (una sola fuente, en vez de ternarios repartidos). X vive en
# x.com; threads.net redirige a threads.com.
_URL = {
    "instagram": "https://www.instagram.com/",
    "threads": "https://www.threads.com/",
    "x": "https://x.com/home",
}

# El interruptor de X reusa la MISMA bandera que el resto del sistema
# (TWITTER_ENABLED en main.py y .env), para no tener DOS banderas apuntando a la
# misma cuenta y que se desincronicen (directiva 32). La red se llama "x" (es la
# marca de hoy), el flag sigue siendo TWITTER_ENABLED.
_ENV_INTERRUPTOR = {"x": "TWITTER"}

# Perfiles persistentes de Playwright, uno por red (sesión logueada). FUERA de
# git: contienen cookies de sesión, que son secreto. Se puede mover con el env.
PERFILES_UI_DIR = os.path.expanduser(os.getenv("PERFILES_UI_DIR", "~/.autocm/perfiles-ui"))

# Perfil del Firefox REAL donde Juan inicia sesión a mano (el navegador seguro de
# chuspa, montado por gocryptfs). De ahí se TRASPLANTA la sesión al perfil de
# Playwright: X y Meta bloquean el login dentro del Chromium automatizado de
# Playwright (lo detectan como bot), pero Firefox normal pasa. En vez de pelear
# con la detección (frágil), se hace el login en el navegador que SÍ funciona y
# se copia solo la cookie de sesión (directiva 1: quitar la causa).
PERFIL_FIREFOX = os.path.expanduser(
    os.getenv("FIREFOX_PERFIL", "/mnt/data/navegador-seguro/clear/perfil"))

# Dominios de sesión por red. El sufijo se compara EXACTO o como subdominio
# (`x.com` y `*.x.com`), NUNCA con un LIKE '%x.com' ingenuo, que casaría
# `okx.com`, `xiliux.com` o `hanerix.com` y metería cookies ajenas en el perfil
# (medido el 2026-11-07 contra el cookies.sqlite real; directiva 23).
COOKIES_DOMINIO = {
    "x": ("x.com", "twitter.com"),
    "instagram": ("instagram.com",),
    "threads": ("threads.com", "threads.net", "instagram.com"),
}


def _perfil(red):
    # Las cookies de sesión son secreto: acceso total a la cuenta, saltándose el
    # 2FA. El árbol se crea restringido al dueño (0o700) y se FUERZA con chmod,
    # porque el `mode=` de makedirs lo recorta el umask (y una carpeta heredada
    # podría venir 0o755). Se restringen solo las carpetas que son nuestras
    # —PERFILES_UI_DIR y la de la red—; nunca el padre, que puede ser $HOME.
    d = os.path.join(PERFILES_UI_DIR, red)
    os.makedirs(d, mode=0o700, exist_ok=True)
    for ruta in (PERFILES_UI_DIR, d):
        try:
            os.chmod(ruta, 0o700)
        except OSError:
            pass
    return d


def _interruptor(red):
    """Misma bandera que main.py/publicar_cola.py. Un canal apagado NO publica y
    lo dice, en vez de vaciar la cola contra una cuenta que nadie encendió. X
    reusa TWITTER_ENABLED (ver _ENV_INTERRUPTOR), no inventa X_ENABLED."""
    clave = _ENV_INTERRUPTOR.get(red, red).upper()
    return os.getenv(f"{clave}_ENABLED", "false").strip().lower() == "true"


# --------------------------------------------------------------------------- UI
#
# Cada red es una función que recibe la `page` (ya logueada) y la `fila` de la
# cola, rellena el compositor y —si `publicar` es True— pulsa y CONFIRMA. Con
# `publicar` False (simulacro) deja el formulario listo y no toca el botón.
#
# Los nombres de botón se buscan por ROL con regex multi-idioma (es/en), porque
# la cuenta puede estar en español (Juan opera desde Colombia) o en inglés, y
# fijar un solo idioma es la fragilidad que ya rompió a MultiPost en LinkedIn.

# Texto a publicar: cuerpo + enlace (como el resto del pipeline). El enlace va en
# el cuerpo porque ni IG ni Threads hacen pinchable un enlace suelto de todos
# modos; va al final, separado.
def _texto(fila):
    cuerpo = fila["cuerpo"].strip()
    enlace = fila["enlace"]
    if enlace and enlace not in cuerpo:
        cuerpo = f"{cuerpo}\n\n{enlace}"
    return cuerpo


def _hilo(fila):
    """Divide el `cuerpo` de una fila en los tweets de un hilo de X. El separador
    es una línea con solo guiones (`---`). Con un único tweet el resultado es
    idéntico a `_texto`, así que una fila normal se publica igual que siempre.

    El `enlace` de la fila se añade al ÚLTIMO tweet (el CTA del hilo), salvo que ya
    esté embebido en el cuerpo —así no se duplica cuando el enlace va escrito dentro
    del último tweet—. Es la misma guarda `enlace not in cuerpo` de `_texto`."""
    import re
    cuerpo = fila["cuerpo"].strip()
    partes = [p.strip() for p in re.split(r"\n\s*-{3,}\s*\n", cuerpo) if p.strip()]
    if not partes:
        partes = [cuerpo]
    enlace = fila["enlace"]
    if enlace and enlace not in cuerpo:
        partes[-1] = f"{partes[-1]}\n\n{enlace}"
    return partes


def _escribir(page, locator, texto):
    """Escribe en un editor contenteditable (Lexical/Draft). `insert_text`
    despacha eventos de input como un pegado real, que es lo que estos editores
    esperan; `fill` no funciona en contenteditable."""
    locator.click()
    page.keyboard.insert_text(texto)


def publicar_instagram(page, fila, publicar):
    """
    VERIFICADO: 2026-11-06 de punta a punta — publicó de verdad desde el VPS
    (xvfb) dos posts de Quipu con tarjeta de marca (ES #480, EN #481),
    confirmados visibles en instagram.com. Flujo completo (Nueva publicación →
    subir imagen → Siguiente ×2 → pie de foto → Compartir) verificado. OJO: IG
    no CIERRA el compositor al compartir, lo REEMPLAZA por su pantalla de
    "compartido" — la confirmación vigila el EDITOR (que se desprende), no el
    diálogo, porque esto último daba un falso NEGATIVO (#480 publicó y se marcó
    fallido). Portado de MultiPost src/sync/dynamic/instagram.ts.

    Instagram EXIGE media: no hay post de solo-texto. La imagen la garantiza el
    llamante (una fila de IG sin imagen se rechaza antes de llegar aquí).
    """
    if not fila["imagen"]:
        raise ValueError("instagram exige imagen y la fila no la trae")

    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    # "Nueva publicación" → (submenú) "Publicación".
    page.locator(
        'svg[aria-label="New post"], svg[aria-label="Nueva publicación"], '
        'svg[aria-label="新帖子"], svg[aria-label="新貼文"]'
    ).first.click(timeout=15000)
    page.wait_for_timeout(1000)
    tipo = page.locator(
        'svg[aria-label="Post"], svg[aria-label="Publicación"], svg[aria-label="帖子"]'
    )
    if tipo.count():
        tipo.first.click()
        page.wait_for_timeout(1000)

    # Subir la imagen al <input type=file>. set_input_files evita el fetch+
    # DataTransfer de la extensión: Playwright tiene acceso al disco.
    page.locator('input[type="file"]').first.set_input_files(fila["imagen"], timeout=15000)
    page.wait_for_timeout(5000)  # IG procesa el recorte/filtros

    # Dos pantallas de "Siguiente" (recorte → filtros → pie de foto).
    import re
    siguiente = re.compile(r"^(Next|Siguiente|下一步|继续)$", re.I)
    for _ in range(2):
        page.get_by_role("button", name=siguiente).first.click(timeout=15000)
        page.wait_for_timeout(2500)

    # Pie de foto: editor Lexical.
    editor = page.locator(
        'div[contenteditable="true"][role="textbox"][data-lexical-editor="true"], '
        'div[contenteditable="true"][aria-label*="aption"], '
        'div[contenteditable="true"][aria-label*="pie de foto"]'
    ).first
    _escribir(page, editor, _texto(fila))
    page.wait_for_timeout(1500)

    if not publicar:
        return  # simulacro: formulario listo, no se comparte

    compartir = re.compile(r"^(Share|Compartir|分享)$", re.I)
    page.get_by_role("button", name=compartir).first.click(timeout=15000)
    # CONFIRMACIÓN: IG reemplaza el compositor por su pantalla de "compartido",
    # así que se vigila el EDITOR del pie (desaparece al compartir) y, como
    # respaldo, el texto de éxito. No el role=dialog, que puede persistir.
    _confirmar_publicado(page, editor, "instagram",
                         exito=re.compile(r"comparti|shared|se ha compartido", re.I))


def publicar_threads(page, fila, publicar):
    """
    VERIFICADO: 2026-11-06 de punta a punta — publicó de verdad desde el VPS
    (xvfb + perfil copiado, IP de Montréal, sin challenge) dos hilos de Quipu
    (ES #439 y EN #479), confirmados visibles en threads.com. Entrada, editor,
    diálogo y clic de "Publicar" verificados. Derivado de MultiPost
    src/sync/dynamic/threads.ts pero reescrito con los selectores REALES del DOM
    (ver NOTICE).

    Threads acepta solo-texto; la imagen es opcional (se adjunta si la fila la
    trae). threads.net redirige a threads.com.
    """
    import re
    page.goto("https://www.threads.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    # Abrir el compositor. El DOM real (2026-11-06) NO tiene svg[aria-label] de
    # "Crear": la entrada es un BOTÓN de texto "Nuevo hilo" (o el placeholder de
    # la portada "¿Qué novedades hay?"). Sin abrirlo no existe ningún
    # contenteditable — ése fue el fallo del primer intento.
    entrada = page.get_by_role("button", name=re.compile(r"Nuevo hilo|New thread", re.I))
    if not entrada.count():
        entrada = page.get_by_text(re.compile(r"¿Qué novedades hay\?|What's new", re.I))
    entrada.first.click(timeout=15000)

    # El editor aparece DENTRO del diálogo tras abrir el compositor.
    raiz = page.locator('div[role="dialog"]')
    raiz = raiz.first if raiz.count() else page.locator("body")
    editor = raiz.locator('div[contenteditable="true"]').first
    editor.wait_for(timeout=15000)
    _escribir(page, editor, _texto(fila))
    page.wait_for_timeout(1000)

    if fila["imagen"]:
        entrada_f = raiz.locator('input[type="file"]')
        if entrada_f.count():
            entrada_f.first.set_input_files(fila["imagen"], timeout=15000)
            page.wait_for_timeout(4000)

    if not publicar:
        return  # simulacro: hilo listo en el compositor, no se publica

    # "Publicar" ACOTADO al diálogo: el feed tiene "Republicar"/"Compartir", no
    # "Publicar", pero acotar evita cualquier colisión. Fallback: Ctrl/Cmd+Enter.
    boton = raiz.get_by_role("button", name=re.compile(r"^(Publicar|Post|發佈|发布)$", re.I))
    if boton.count():
        boton.first.click(timeout=15000)
    else:
        editor.click()
        page.keyboard.press("Control+Enter")
    _confirmar_publicado(page, raiz, "threads",
                         exito=re.compile(r"publicad|posted", re.I))


def publicar_x(page, fila, publicar):
    """
    VERIFICADO de punta a punta: 2026-11-07 publicó de verdad desde el VPS (xvfb,
    IP de Montréal, sin challenge de Cloudflare) la nota #484 (iraca/ML-KEM),
    confirmada VISIBLE en la cuenta de marca @xiliuxDev. Flujo completo: compositor
    (/compose/post) → editor `tweetTextarea_0` → escritura → clic "Publicar" →
    confirmación por desprendimiento del editor. SIN ejercitar aún: la subida de
    imagen (el primer envío fue solo-texto). Los selectores usan los `data-testid`
    de X, más estables que las clases ofuscadas de IG/Threads pero igual cambian sin
    avisar — una pantalla hay que DIBUJARLA (D28).

    El login NO se hace aquí: X bloquea el login en el Chromium automatizado, así
    que la sesión se trae del Firefox real con `--importar-sesion x` (ver abajo).

    X acepta solo-texto; la imagen es opcional (se adjunta si la fila la trae).
    El límite libre es 280 caracteres y el pipeline ya recorta a ~249 + enlace.

    Reglas de identidad: autocm publica SOLO por la cuenta de MARCA Xiliux, nunca
    por la personal (@isazajuancarlos). El canal es SENSIBLE: solo sale lo aprobado.
    """
    import re
    # /compose/post abre el compositor modal directo: más determinista que buscar
    # el botón "Publicar" en la portada (que cambia de sitio según el ancho).
    page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # El editor es un contenteditable DraftJS con testid estable. Si el modal no
    # cargó, caer a la caja en línea de la portada con el mismo testid.
    editor = page.locator('div[data-testid="tweetTextarea_0"]').first
    try:
        editor.wait_for(timeout=15000)
    except Exception:
        page.goto("https://x.com/home", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        editor = page.locator('div[data-testid="tweetTextarea_0"]').first
        editor.wait_for(timeout=15000)
    tweets = _hilo(fila)
    largos = [i + 1 for i, t in enumerate(tweets) if len(t) > 280]
    if largos:
        raise ValueError(f"x: hilo con tweet(s) >280 caracteres en posición {largos}")
    _escribir(page, editor, tweets[0])
    page.wait_for_timeout(1000)

    if fila["imagen"]:
        entrada_f = page.locator('input[data-testid="fileInput"], input[type="file"]')
        if entrada_f.count():
            entrada_f.first.set_input_files(fila["imagen"], timeout=15000)
            page.wait_for_timeout(4000)

    # Hilo (≥2 tweets): el botón "+" (addButton) añade otro editor al MISMO
    # compositor; al final un solo "Publicar todo" (tweetButton) los manda
    # encadenados. Más robusto que responder al propio post y capturar su URL.
    for i, t in enumerate(tweets[1:], start=1):
        add = page.locator('button[data-testid="addButton"]')
        if not add.count():
            add = page.get_by_role("button", name=re.compile(r"añad|agregar|add", re.I))
        add.first.click(timeout=15000)
        page.wait_for_timeout(1000)
        ed_i = page.locator(f'div[data-testid="tweetTextarea_{i}"]').first
        ed_i.wait_for(timeout=15000)
        _escribir(page, ed_i, t)
        page.wait_for_timeout(700)

    if not publicar:
        return  # simulacro: hilo compuesto en el compositor, no se publica

    # Botón de envío: `tweetButton` (modal) o `tweetButtonInline` (portada).
    # Fallback por rol multi-idioma, y último recurso Ctrl+Enter.
    boton = page.locator(
        'button[data-testid="tweetButton"], button[data-testid="tweetButtonInline"]')
    if boton.count():
        boton.first.click(timeout=15000)
    else:
        rol = page.get_by_role("button", name=re.compile(r"^(Post|Publicar|Postear)$", re.I))
        if rol.count():
            rol.first.click(timeout=15000)
        else:
            editor.click()
            page.keyboard.press("Control+Enter")
    # CONFIRMACIÓN: al enviar, el compositor (editor) se desprende, y X muestra un
    # toast "Se envió tu post" / "Your post was sent". Cualquiera de los dos vale.
    _confirmar_publicado(page, editor, "x",
                         exito=re.compile(r"se envió|was sent|posted|publicad", re.I))


def _confirmar_publicado(page, vigilado, red, exito=None, timeout_ms=25000):
    """
    Confirma que publicó de verdad. Es la diferencia con MultiPost (que no
    confirma) — pero la señal NO es la misma en cada red, y confundirlas da un
    falso NEGATIVO: Threads CIERRA el compositor; Instagram lo REEMPLAZA por su
    pantalla de "compartido" (el editor desaparece pero puede quedar un
    role=dialog). Así que se da por publicado si ocurre CUALQUIERA de dos cosas
    dentro del tope:
      - el elemento `vigilado` se desprende (compositor cerrado / editor ido), o
      - aparece un texto de éxito (`exito`, regex), p. ej. "compartido".
    Si no ocurre ninguna, se levanta: un clic sin efecto confirmado no es una
    publicación (directiva 30), y la fila queda visible para revisar a mano.
    """
    import time as _t
    fin = _t.time() + timeout_ms / 1000
    while _t.time() < fin:
        try:
            if vigilado.count() == 0:
                return
        except Exception:
            return
        if exito is not None:
            try:
                if page.get_by_text(exito).count() > 0:
                    return
            except Exception:
                pass
        page.wait_for_timeout(500)
    raise RuntimeError(
        f"{red}: no se pudo confirmar el envío (ni se cerró el compositor ni "
        f"apareció confirmación). Revísalo a mano antes de reintentar.")


PUBLICADORES = {"instagram": publicar_instagram, "threads": publicar_threads,
                "x": publicar_x}


def _png_placeholder():
    """Un PNG 1080x1080 en un temporal, para ensayar Instagram (exige imagen) en
    simulacro sin tener una tarjeta real a mano."""
    import tempfile
    from PIL import Image
    f = tempfile.NamedTemporaryFile(prefix="pui-prueba-", suffix=".png", delete=False)
    Image.new("RGB", (1080, 1080), (10, 20, 40)).save(f.name)
    f.close()
    return f.name


def _fila_de_prueba(red):
    """Un post SINTÉTICO para ejercitar el DOM en --simulacro cuando la cola no
    tiene nada aprobado. No es una fila de la BD (id='PRUEBA'): como simulacro
    nunca llama a marcar_publicado/marcar_fallido, jamás toca la cola ni se
    publica. Threads acepta solo-texto; Instagram lleva imagen placeholder."""
    return {
        "id": "PRUEBA", "destino": red, "tipo": "NOTA", "estado": "simulacro",
        "cuerpo": "Prueba de publicar_ui (simulacro, NO publicar). Xiliux: "
                  "criptografía post-cuántica y seguridad en Rust.",
        "enlace": "https://xiliux.com",
        "imagen": _png_placeholder() if red == "instagram" else None,
        "imagen_alt": "imagen de prueba" if red == "instagram" else None,
    }


# ------------------------------------------------------------------- orquestación

def _logueado(page, red):
    """Positivo de control antes de publicar: ¿hay sesión? Sin login la UI
    muestra el formulario de acceso y el compositor nunca aparece —publicar
    ciego dejaría filas 'fallidas' sin motivo claro, así que se dice—."""
    page.goto(_URL[red], wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    # Señal de NO-logueado: un campo de contraseña visible.
    return page.locator('input[type="password"]').count() == 0


def login(red, headful=True):
    """Abre el navegador para que Juan inicie sesión UNA vez; el perfil
    persistente guarda la cookie. No automatiza el login (2FA, captcha): lo hace
    la persona, y el proceso espera a que termine."""
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(_perfil(red), headless=not headful)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(_URL[red])
        print(f"\nInicia sesión en {red} en la ventana del navegador.")
        print("Cuando estés dentro (ves tu feed), vuelve aquí y pulsa Enter…")
        try:
            input()
        except EOFError:
            print("(sin terminal interactiva: cierra la ventana cuando termines)")
            time.sleep(120)
        ctx.close()
    print(f"perfil de {red} guardado en {_perfil(red)}")


def publicar(red, limite, simulacro, headful):
    if red not in REDES_UI:
        sys.exit(f"{red}: este publicador solo conduce {sorted(REDES_UI)}; "
                 f"el resto va por publicar_cola.py o a mano")
    if not simulacro and not _interruptor(red):
        sys.exit(f"{red} está apagado ({red.upper()}_ENABLED != true): "
                 f"no publico. Enciéndelo cuando quieras que salga al mundo.")

    cx = cola.conectar()
    filas = cola.reclamar(cx, red, limite=limite)
    if not filas:
        if simulacro:
            print(f"(simulacro sin cola aprobada para {red}: uso un post de PRUEBA "
                  f"sintético — ejercita el DOM, no se publica ni toca la cola)")
            filas = [_fila_de_prueba(red)]
        else:
            print(f"nada aprobado pendiente para {red} "
                  f"(es SENSIBLE: solo ve lo aprobado — usa `cola.py aprobar <id>`)")
            cx.close()
            return

    fn = PUBLICADORES[red]
    # Instagram exige imagen: filtra ruidosamente antes de abrir el navegador.
    if red == "instagram":
        sin_img = [f["id"] for f in filas if not f["imagen"]]
        if sin_img:
            print(f"AVISO: filas de instagram SIN imagen, no se pueden publicar: {sin_img}")
        filas = [f for f in filas if f["imagen"]]
        if not filas:
            cx.close()
            return

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            _perfil(red), headless=not (headful or simulacro))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not simulacro and not _logueado(page, red):
            ctx.close(); cx.close()
            sys.exit(f"{red}: no hay sesión iniciada. Corre: "
                     f"python publicar_ui.py --login {red}")
        for fila in filas:
            etiqueta = "SIMULACRO" if simulacro else "publicando"
            print(f"[{etiqueta}] {red} #{fila['id']}: {fila['cuerpo'][:50]}…")
            try:
                fn(page, fila, publicar=not simulacro)
                if simulacro:
                    print(f"  ✓ formulario listo (no se publicó: simulacro)")
                else:
                    cola.marcar_publicado(cx, fila["id"])
                    print(f"  ✔ publicado")
            except Exception as err:  # noqa: BLE001 — se registra, no se traga
                print(f"  ✘ {err}")
                if not simulacro:
                    cola.marcar_fallido(cx, fila["id"], err)
        ctx.close()
    cx.close()


def diagnosticar(red, headful=True):
    """Solo lectura: abre la sesión, va a la red y vuelca los candidatos reales
    del DOM para corregir los selectores con datos y no a ojo (directiva 20). No
    hace clic, no escribe, no publica."""
    url = _URL[red]
    js = r"""() => {
      const q = (s) => Array.from(document.querySelectorAll(s));
      const uniq = (a) => [...new Set(a.filter(Boolean))];
      return {
        url: location.href,
        title: document.title,
        login: !!document.querySelector('input[type="password"]'),
        svgLabels: uniq(q('svg[aria-label]').map(e => e.getAttribute('aria-label'))),
        contenteditables: q('[contenteditable="true"]').map(e => ({
          ph: e.getAttribute('aria-placeholder'),
          al: e.getAttribute('aria-label'),
          role: e.getAttribute('role'),
          lexical: e.getAttribute('data-lexical-editor'),
        })),
        botones: uniq(q('[role="button"], button, a[role="link"]')
          .map(b => (b.textContent || '').trim()).filter(t => t && t.length < 30)).slice(0, 80),
      };
    }"""
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(_perfil(red), headless=not headful)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        import json
        print(json.dumps(page.evaluate(js), ensure_ascii=False, indent=2))
        ctx.close()


def _cookies_firefox(red, perfil_firefox):
    """Lee del cookies.sqlite de Firefox SOLO las cookies de los dominios de la
    red y las devuelve en el formato de Playwright `add_cookies`. No imprime ni
    escribe NINGÚN valor: una cookie de sesión es acceso total a la cuenta.

    Firefox vivo mantiene el sqlite en WAL; se abre `immutable=1` (solo lectura,
    sin bloquear a Firefox ni copiar el secreto a otro archivo). El filtro de
    dominio es exacto-o-subdominio, nunca sufijo ingenuo (directiva 23)."""
    import sqlite3
    db = os.path.join(perfil_firefox, "cookies.sqlite")
    if not os.path.exists(db):
        sys.exit(f"no existe {db} — ¿está montado el navegador seguro de chuspa? "
                 f"(perfil Firefox; se puede cambiar con FIREFOX_PERFIL)")
    dominios = COOKIES_DOMINIO[red]
    # host = d  OR  host LIKE '%.d'  por cada dominio. El '.'+d evita que 'x.com'
    # case 'okx.com' (ese no termina en '.x.com').
    clausula = " OR ".join(["host = ? OR host LIKE ?"] * len(dominios))
    params = []
    for d in dominios:
        params += [d, f"%.{d}"]
    con = sqlite3.connect(f"file:{db}?immutable=1", uri=True)
    try:
        filas = con.execute(
            f"SELECT host,name,value,path,expiry,isSecure,isHttpOnly,sameSite "
            f"FROM moz_cookies WHERE {clausula}", params).fetchall()
    finally:
        con.close()

    _ss = {0: "None", 1: "Lax", 2: "Strict"}
    _MAX_EXP = 253402300799.0  # año 9999: tope que acepta Playwright/Chromium
    cookies = []
    for host, name, value, path, expiry, secure, httponly, samesite in filas:
        # Playwright solo admite expires == -1 (sesión) o un epoch positivo. Firefox
        # guarda 0 para las de sesión y, para algunas, un expiry enorme que desborda
        # el tope de Chromium: ambos van a -1 / al tope (directiva 20: nada de valor
        # inválido silencioso, se normaliza explícito).
        try:
            exp = float(expiry)
        except (TypeError, ValueError):
            exp = -1.0
        if exp <= 0:
            exp = -1.0
        elif exp > _MAX_EXP:
            exp = _MAX_EXP
        c = {
            "name": name, "value": value,
            "domain": host, "path": path or "/",
            "secure": bool(secure), "httpOnly": bool(httponly),
            "expires": exp,
        }
        ss = _ss.get(samesite, "Lax")
        # Playwright exige secure=True para SameSite=None; si no, degradar a Lax
        # en vez de que add_cookies lance.
        if ss == "None" and not c["secure"]:
            ss = "Lax"
        c["sameSite"] = ss
        cookies.append(c)
    return cookies


def importar_sesion(red, perfil_firefox=None, headful=False):
    """Trasplanta la sesión de `red` desde el Firefox real al perfil de Playwright,
    para no tener que autenticar dentro del Chromium automatizado (que X/Meta
    bloquean). Tras esto, `--destino <red>` publica reusando esa sesión, igual que
    si se hubiera hecho `--login`. Verifica que quedó logueado (directiva 30)."""
    if red not in REDES_UI:
        sys.exit(f"{red}: solo {sorted(REDES_UI)}")
    perfil_firefox = perfil_firefox or PERFIL_FIREFOX
    cookies = _cookies_firefox(red, perfil_firefox)
    nombres = sorted({c["name"] for c in cookies})
    # Positivo de control: sin cookie de sesión no hay nada que trasplantar y hay
    # que loguear en Firefox PRIMERO. Las de sesión difieren por red.
    sesion = {"x": {"auth_token", "ct0"},
              "instagram": {"sessionid"}, "threads": {"sessionid"}}.get(red, set())
    if sesion and not (sesion & set(nombres)):
        sys.exit(f"{red}: el perfil Firefox NO tiene sesión iniciada "
                 f"(faltan {sorted(sesion)}). Inicia sesión en {red} en ese "
                 f"Firefox y vuelve a correr esto.")
    print(f"{red}: {len(cookies)} cookies de {COOKIES_DOMINIO[red]} leídas "
          f"(nombres, SIN valores): {nombres}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(_perfil(red), headless=not headful)
        ctx.add_cookies(cookies)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(_URL[red], wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        ok = page.locator('input[type="password"]').count() == 0
        ctx.close()
    if ok:
        print(f"✔ sesión de {red} trasplantada al perfil de Playwright "
              f"({_perfil(red)}). Ya puedes publicar con --destino {red}.")
    else:
        sys.exit(f"✘ {red}: tras trasplantar sigue pidiendo contraseña. La sesión "
                 f"del Firefox pudo expirar, o faltan cookies. Reinicia sesión ahí.")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--login", choices=sorted(REDES_UI),
                    help="iniciar sesión a mano en esta red (abre navegador)")
    ap.add_argument("--importar-sesion", choices=sorted(REDES_UI), dest="importar",
                    help="trasplantar la sesión desde el Firefox real (navegador "
                         "seguro de chuspa) al perfil de Playwright — para redes "
                         "que bloquean el login en el Chromium automatizado (X, Meta)")
    ap.add_argument("--perfil-firefox", dest="perfil_firefox",
                    help=f"perfil Firefox de origen (def. {PERFIL_FIREFOX})")
    ap.add_argument("--destino", choices=sorted(REDES_UI), help="red a publicar")
    ap.add_argument("--diagnostico", choices=sorted(REDES_UI),
                    help="volcar los candidatos del DOM (solo lectura, no publica)")
    ap.add_argument("--limite", type=int, default=1, help="máximo de filas (def. 1)")
    ap.add_argument("--simulacro", action="store_true",
                    help="rellena el formulario pero NO publica (verifica selectores)")
    ap.add_argument("--headful", action="store_true",
                    help="navegador visible (útil para ver qué pasa)")
    args = ap.parse_args()

    if args.login:
        login(args.login, headful=True)
    elif args.importar:
        importar_sesion(args.importar, args.perfil_firefox, headful=args.headful)
    elif args.diagnostico:
        diagnosticar(args.diagnostico, headful=args.headful)
    elif args.destino:
        publicar(args.destino, args.limite, args.simulacro, args.headful)
    else:
        ap.error("elige --login <red>, --importar-sesion <red>, "
                 "--diagnostico <red> o --destino <red>")


if __name__ == "__main__":
    main()
