#!/usr/bin/env python3
"""
Productor de capturas de las demos de Xiliux, para que las publicaciones lleven
la imagen de «míralo funcionando» en vez de texto pelado.

Estrategia, la misma para toda app (directiva 19): entra con las credenciales
DEMO —públicas, publicadas en la propia pantalla de acceso—, recorre los enlaces
del MENÚ que aparecen tras entrar, y captura cada sección a página completa. Así
salen los MAESTROS (catálogos, configuración) y las CARACTERÍSTICAS ESPECIALES
sin enumerar rutas a mano, que envejecería a la primera pantalla nueva.

    python capturas.py --app medico          # una
    python capturas.py                        # todas
    python capturas.py --app medico --limite 60

NO publica nada ni escribe en las demos: solo navega y hace screenshot. Las
imágenes van a `marca/capturas/<app>/<slug>.png`.
"""
import argparse
import json
import os
import re
import sys
from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(RAIZ, "marca", "capturas")

# Credenciales DEMO, públicas por diseño (cada login las publica). No son
# secretos: cualquiera puede entrar a la demostración y se reinicia sola.
APPS = {
    "xiliux": {
        "base": "https://xiliux.com",
        "login": None,  # landing pública; se capturan sus secciones por scroll
    },
    "informes": {
        "base": "https://informes.xiliux.com",
        "login": {"url": "/entrar", "usuario": "admin@co.co", "clave": "admin",
                  "sel_user": "input[type=email]", "sel_pass": "input[type=password]"},
    },
    "inventario": {
        "base": "https://inventario.xiliux.com",
        "login": {"url": "/", "usuario": "demo", "clave": "inventario2026",
                  "sel_user": "input[name=codigo]", "sel_pass": "input[type=password]"},
    },
    "medico": {
        "base": "https://medico.xiliux.com",
        "login": {"url": "/login", "usuario": "demo@xiliux.com", "clave": "demo-medico-2026",
                  "sel_user": "input[type=email]", "sel_pass": "input[type=password]"},
    },
    "chasqui": {
        "base": "https://chasqui.xiliux.com",
        # El despliegue no sembró credenciales demo; se intenta la de prueba y si
        # no entra, queda solo la portada. Se dice, no se adivina a ciegas.
        "login": {"url": "/entrar", "usuario": "ana@acme.com", "clave": "una-contraseña-larga",
                  "sel_user": "input[type=email]", "sel_pass": "input[type=password]",
                  "opcional": True},
    },
}

# Enlaces que NO se capturan: cerrar sesión rompe el recorrido, las acciones
# destructivas no se tocan aunque sea una demo, y las DESCARGAS (`/api/…`,
# `/archivo`, ficheros) no son pantallas —`goto` a una descarga aborta con
# «Download is starting», que ensuciaba informes con 14 fallos—.
EVITAR = re.compile(
    r"(salir|logout|cerrar|eliminar|borrar|delete|/api/|/archivo|descargar|download"
    r"|\.pdf|\.csv|\.xlsx?|\.zip|\.docx?)", re.I)


def _slug(ruta):
    s = re.sub(r"[^a-z0-9]+", "_", ruta.lower()).strip("_")
    return s or "inicio"


def _asentar(pg):
    """Espera a que el contenido htmx termine de cargar antes de capturar.

    `networkidle` no basta: los paneles piden sus datos con `hx-get` tras
    pintarse, así que la primera foto sale con «Cargando…». Se espera a que ese
    texto desaparezca (con techo, para no colgarse en una pantalla que siempre lo
    muestre) y se cierran los avisos de error que arrastra la pantalla anterior,
    que taparían la imagen.
    """
    try:
        pg.wait_for_function(
            "!/Cargando|Loading|Cargando…/i.test(document.body.innerText)", timeout=6000)
    except Exception:
        pass
    # Ocultar los avisos flotantes por JS, NO clicando su botón: un clic en un
    # «×» puede resultar ser «cerrar sesión» y tumbar el recorrido —le pasó a
    # medico, que perdía la sesión a mitad—. Ocultar por estilo no navega.
    try:
        pg.evaluate(
            "document.querySelectorAll('[role=alert],.toast,.notificacion,"
            ".aviso,.snackbar').forEach(e => e.style.display='none')")
    except Exception:
        pass
    pg.wait_for_timeout(900)


def _boton_enviar(pg):
    """El botón que INICIA sesión, no el de autorrelleno de demo.

    medico ofrece «Rellenar y entrar» (rellena las credenciales demo) junto a
    «Iniciar Sesión»; como aquí ya se rellenan los campos, se prefiere el de
    verdad. El orden de preferencia lo dice qué palabra lleva.
    """
    botones = pg.query_selector_all("button, input[type=submit]")
    def txt(b):
        return (b.inner_text() or b.get_attribute("value") or "").strip()
    for patron in (r"iniciar\s*sesi|acceder|ingresar", r"\bentrar\b"):
        for b in botones:
            if re.search(patron, txt(b), re.I) and not re.search(r"rellenar", txt(b), re.I):
                return b
    return None


def _entrar(pg, base, login):
    """Devuelve True si quedó dentro. Con `opcional`, un fallo no aborta la app."""
    pg.goto(base + login["url"], wait_until="networkidle", timeout=25000)
    pg.wait_for_timeout(1000)
    try:
        pg.fill(login["sel_user"], login["usuario"])
        pg.fill(login["sel_pass"], login["clave"])
        enviar = _boton_enviar(pg)
        if enviar:
            enviar.click()
        else:
            pg.press(login["sel_pass"], "Enter")
        pg.wait_for_load_state("networkidle", timeout=20000)
        pg.wait_for_timeout(1500)
        # Positivo de control: si sigue habiendo campo de contraseña, no entró.
        return not _en_login(pg, login)
    except Exception as e:
        if login.get("opcional"):
            print(f"    (login opcional falló: {str(e)[:60]})")
            return False
        raise


def _rutas_del_menu(pg, base):
    """
    Los enlaces internos del menú, como `(ruta, href_dom)`: `ruta` es el camino
    normalizado —para el nombre del archivo y para deduplicar—, y `href_dom` es
    el atributo tal como está escrito, que es por el que hay que CLICAR.

    Los dos hacen falta porque no todas las apps escriben el href igual: medico
    lo pone relativo (`/pacientes`) e inventario absoluto
    (`https://inventario.xiliux.com/articulos`). Normalizar para el nombre pero
    clicar por el literal es lo que hace universal el recorrido (directiva 19);
    buscar `a[href="/articulos"]` cuando el DOM dice la URL entera no encuentra
    nada, y eso dejó inventario en cero.
    """
    hrefs = pg.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.getAttribute('href'))")
    vistas, rutas = set(), []
    for h in hrefs:
        if not h:
            continue
        ruta = h[len(base):] if h.startswith(base) else h
        if not ruta.startswith("/") or ruta.startswith("//") or EVITAR.search(ruta):
            continue
        if ruta in vistas:
            continue
        vistas.add(ruta)
        rutas.append((ruta, h))
    return rutas


def _en_login(pg, login):
    """
    ¿La pantalla actual es el formulario de acceso? Se mira por la presencia del
    campo de CONTRASEÑA, no por la URL: inventario tiene su login en `/`, que con
    sesión redirige a `/articulos`, así que la ruta no lo distingue —y `"/"`.strip
    es `""`, que hace `endswith` siempre verdadero—. Una pantalla interna no
    tiene campo de contraseña; el login siempre.
    """
    if not login:
        return False
    try:
        return pg.query_selector("input[type=password]") is not None
    except Exception:
        return False


def _elegir_metodo(pg, base, login, rutas):
    """
    Sondea UNA vez qué navegación conserva la sesión `SameSite=Strict` de esta
    app, y usa esa para todas sus rutas.

    Las apps difieren y de forma OPUESTA, medido el 2026-08-09: medico conserva
    la sesión con navegación de cliente (`location.href`/clic) y la pierde con el
    `goto` de Playwright; inventario al revés. Adivinar por app envejece; probar
    con la primera ruta y quedarse con lo que funciona, no.

    El método CLIENTE es un CLIC en el enlace del menú, no `location.href`: el
    clic es la navegación same-site más estable —medico aguantó las 21 pantallas
    con clic, y con `location.href` perdía la sesión a mitad—. Se sondea con clic
    primero, que es no destructivo si funciona.
    """
    href0 = rutas[0][1]
    enlace = pg.query_selector(f'a[href="{href0}"]')
    if enlace:
        try:
            enlace.click()
            pg.wait_for_load_state("networkidle", timeout=20000)
            pg.wait_for_timeout(800)
            if not _en_login(pg, login):
                return "cliente"
        except Exception:
            pass
    # El clic no sirvió (o rebotó a login): asegurar la sesión y usar `goto`.
    if _en_login(pg, login):
        _entrar(pg, base, login)
    return "goto"


def capturar_app(b, nombre, cfg, limite):
    destino = os.path.join(SALIDA, nombre)
    os.makedirs(destino, exist_ok=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    base = cfg["base"]
    hechas, fallos = 0, 0

    dentro = True
    if cfg["login"]:
        dentro = _entrar(pg, base, cfg["login"])
        estado = "dentro" if dentro else "NO entró (queda la portada)"
        print(f"  [{nombre}] login: {estado}")

    if not cfg["login"] or not dentro:
        # Portada / login: al menos una captura, a página completa.
        pg.goto(base + "/", wait_until="networkidle", timeout=25000)
        pg.wait_for_timeout(1500)
        pg.screenshot(path=os.path.join(destino, "portada.png"), full_page=True)
        print(f"  [{nombre}] portada.png")
        hechas += 1
        if not dentro:
            pg.close()
            return hechas, fallos

    rutas = _rutas_del_menu(pg, base)[:limite]
    print(f"  [{nombre}] {len(rutas)} secciones en el menú")
    # Sin sesión (landing pública) `goto` basta; con sesión, el método que
    # conserva la cookie Strict se sondea (ver `_elegir_metodo`).
    metodo = "goto"
    if cfg["login"] and dentro and rutas:
        metodo = _elegir_metodo(pg, base, cfg["login"], rutas)
        print(f"  [{nombre}] navegación: {metodo}")
    inicio_href = rutas[0][1] if rutas else None
    for ruta, href_dom in rutas:
        try:
            if metodo == "cliente":
                sel = f'a[href="{href_dom}"]'
                if not pg.query_selector(sel) and inicio_href:
                    # El menú no está en esta pantalla: volver a la primera.
                    ini = pg.query_selector(f'a[href="{inicio_href}"]')
                    if ini:
                        ini.click()
                        pg.wait_for_load_state("networkidle", timeout=15000)
                        pg.wait_for_timeout(400)
                enlace = pg.query_selector(sel)
                if not enlace:
                    print(f"    ✗ {ruta}: sin enlace en el menú")
                    fallos += 1
                    continue
                enlace.click()
            else:
                pg.goto(base + ruta, wait_until="networkidle", timeout=20000)
            pg.wait_for_load_state("networkidle", timeout=20000)
            _asentar(pg)
            # Positivo de control: si acabó en la pantalla de acceso, no cuenta.
            if _en_login(pg, cfg["login"]):
                print(f"    ✗ {ruta}: rebotó a login (sesión perdida)")
                fallos += 1
                continue
            pg.screenshot(path=os.path.join(destino, f"{_slug(ruta)}.png"), full_page=True)
            hechas += 1
        except Exception as e:
            print(f"    ✗ {ruta}: {str(e)[:50]}")
            fallos += 1
    pg.close()
    return hechas, fallos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", choices=sorted(APPS), help="una sola; por defecto todas")
    ap.add_argument("--limite", type=int, default=50, help="máx. secciones por app")
    args = ap.parse_args()

    apps = {args.app: APPS[args.app]} if args.app else APPS
    os.makedirs(SALIDA, exist_ok=True)
    total_ok = total_fallo = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for nombre, cfg in apps.items():
            print(f"══ {nombre} ══")
            try:
                ok, fallo = capturar_app(b, nombre, cfg, args.limite)
                total_ok += ok
                total_fallo += fallo
            except Exception as e:
                print(f"  [{nombre}] ERROR de app: {str(e)[:80]}")
                total_fallo += 1
        b.close()
    print(f"\n{total_ok} capturas en {SALIDA}, {total_fallo} fallos")
    return 1 if total_fallo and not total_ok else 0


if __name__ == "__main__":
    sys.exit(main())
