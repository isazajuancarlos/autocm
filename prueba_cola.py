#!/usr/bin/env python3
"""
Simulación de la cola: 100+ operaciones, concurrencia con timeout, camino de
error inyectado, y comprobación de que las pruebas DISCRIMINAN (directiva 8).

    .venv/bin/python prueba_cola.py

No usa framework porque el repositorio no tiene ninguno; se ejecuta suelto y
termina con código 0 o 1. La base va a un fichero temporal: nunca toca la cola
real, que es historial.
"""
import os
import sqlite3
import sys
import tempfile
import threading

import cola

FALLOS = []


def comprobar(condición, qué):
    print(("  ✔ " if condición else "  ✘ ") + qué)
    if not condición:
        FALLOS.append(qué)
    return condición


def nueva_bd():
    ruta = os.path.join(tempfile.mkdtemp(prefix="cola-prueba-"), "cola.sqlite")
    return cola.conectar(ruta), ruta


def prueba_volumen():
    print("\n[1] 120 encolados y el reparto por estado")
    cx, _ = nueva_bd()
    for i in range(120):
        destino = "reddit" if i % 2 else "bluesky"
        cola.encolar(cx, destino, "NOTA", f"nota número {i}", f"https://xiliux.com/a/{i}")
    total = cx.execute("SELECT COUNT(*) c FROM cola").fetchone()["c"]
    comprobar(total == 120, f"120 filas encoladas (hay {total})")

    aprobadas = sum(cola.aprobar(cx, f["id"])
                    for f in cx.execute("SELECT id FROM cola WHERE destino='reddit'"))
    comprobar(aprobadas == 60, f"60 aprobadas de reddit (fueron {aprobadas})")

    publicadas = sum(cola.marcar_publicado(cx, f["id"], "https://rd/x")
                     for f in cola.reclamar(cx, "reddit", limite=1000))
    comprobar(publicadas == 60, f"60 publicadas (fueron {publicadas})")
    comprobar(len(cola.reclamar(cx, "reddit", limite=1000)) == 0,
              "no queda nada pendiente en reddit tras publicarlo todo")
    cx.close()


def prueba_discriminacion_por_canal():
    print("\n[2] un canal SENSIBLE no puede consumir borradores")
    cx, _ = nueva_bd()
    ln = cola.encolar(cx, "reddit", "NOTA", "texto para la comunidad", "https://x.com/1")
    bs = cola.encolar(cx, "bluesky", "NOTA", "texto para bluesky", "https://x.com/1")

    comprobar([f["id"] for f in cola.reclamar(cx, "reddit")] == [],
              "reddit (sensible) NO ve el borrador")
    comprobar([f["id"] for f in cola.reclamar(cx, "bluesky")] == [bs],
              "bluesky (barato) SÍ ve el borrador")

    # Y el salto directo a publicado también está cerrado para el sensible.
    comprobar(cola.marcar_publicado(cx, ln) is False,
              "reddit no salta de borrador a publicado sin aprobación")
    comprobar(cola.marcar_publicado(cx, bs) is True,
              "bluesky sí publica desde borrador")

    cola.aprobar(cx, ln)
    comprobar([f["id"] for f in cola.reclamar(cx, "reddit")] == [ln],
              "reddit ve la fila una vez aprobada")
    cx.close()


def prueba_duplicados():
    print("\n[3] el mismo enlace no se encola dos veces para el mismo destino")
    cx, _ = nueva_bd()
    a = cola.encolar(cx, "bluesky", "NOTA", "uno", "https://xiliux.com/p")
    b = cola.encolar(cx, "bluesky", "NOTA", "otro texto", "https://xiliux.com/p")
    c = cola.encolar(cx, "mastodon", "NOTA", "uno", "https://xiliux.com/p")
    comprobar(a is not None and b is None, "el duplicado devuelve None, no una fila nueva")
    comprobar(c is not None, "el mismo enlace en OTRO destino sí entra")
    # Sin enlace no hay unicidad que imponer: dos notas sueltas son legítimas.
    d = cola.encolar(cx, "bluesky", "NOTA", "suelta")
    e = cola.encolar(cx, "bluesky", "NOTA", "suelta")
    comprobar(d is not None and e is not None, "dos notas sin enlace conviven")
    cx.close()


def prueba_error_inyectado():
    print("\n[4] camino de error: un publicador que falla no pierde la fila")
    cx, _ = nueva_bd()
    i = cola.encolar(cx, "mastodon", "NOTA", "se va a caer", "https://xiliux.com/e")

    def publicador_roto(id_):
        try:
            raise ConnectionError("la instancia devolvió 503")
        except Exception as err:
            cola.marcar_fallido(cx, id_, err)

    publicador_roto(i)
    f = cx.execute("SELECT * FROM cola WHERE id=?", (i,)).fetchone()
    comprobar(f["estado"] == cola.FALLIDO, "queda en fallido, no desaparece")
    comprobar("503" in (f["error"] or ""), "el motivo queda escrito en la fila")
    comprobar(cola.reintentar(cx, i) is True, "reintentar la devuelve a borrador")
    comprobar(len(cola.reclamar(cx, "mastodon")) == 1, "y vuelve a estar pendiente")

    # Una fila ya publicada no se puede marcar fallida: el historial no se reescribe.
    j = cola.encolar(cx, "bluesky", "NOTA", "esta sí sale", "https://xiliux.com/ok")
    cola.marcar_publicado(cx, j, "https://bsky.app/x")
    comprobar(cola.marcar_fallido(cx, j, "tardío") is False,
              "lo publicado no se puede marcar fallido después")
    cx.close()


def prueba_concurrencia():
    print("\n[5] 40 hilos peleando por publicar la MISMA fila: gana uno solo")
    cx, ruta = nueva_bd()
    i = cola.encolar(cx, "reddit", "NOTA", "una sola vez", "https://xiliux.com/u")
    cola.aprobar(cx, i)
    cx.close()

    ganadores, errores = [], []
    barrera = threading.Barrier(40, timeout=15)

    def intentar():
        propia = cola.conectar(ruta)
        try:
            barrera.wait()
            if cola.marcar_publicado(propia, i, "https://ln/una"):
                ganadores.append(1)
        except Exception as e:          # incluye el timeout de la barrera
            errores.append(repr(e))
        finally:
            propia.close()

    hilos = [threading.Thread(target=intentar) for _ in range(40)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=20)

    comprobar(not any(h.is_alive() for h in hilos), "ningún hilo se quedó colgado")
    comprobar(not errores, f"sin excepciones en los hilos ({errores[:2]})")
    comprobar(len(ganadores) == 1, f"exactamente 1 publicación (hubo {len(ganadores)})")
    cx = cola.conectar(ruta)
    comprobar(cx.execute("SELECT COUNT(*) c FROM cola WHERE estado='publicado'"
                         ).fetchone()["c"] == 1, "y una sola fila publicada en la base")
    cx.close()


def prueba_alcance_del_borrado():
    print("\n[6] purgar borra SOLO el destino y estado pedidos (directiva 22)")
    cx, _ = nueva_bd()
    for n in range(10):
        cola.encolar(cx, "bluesky", "NOTA", f"b{n}", f"https://xiliux.com/b{n}")
    for n in range(10):
        cola.encolar(cx, "linkedin", "NOTA", f"l{n}", f"https://xiliux.com/l{n}")
    guardada = cola.encolar(cx, "bluesky", "NOTA", "ya salió", "https://xiliux.com/viva")
    cola.marcar_publicado(cx, guardada, "https://bsky.app/y")

    n = cola.purgar(cx, "bluesky", cola.BORRADOR)
    comprobar(n == 10, f"borra los 10 borradores de bluesky (borró {n})")
    comprobar(cx.execute("SELECT COUNT(*) c FROM cola WHERE destino='linkedin'"
                         ).fetchone()["c"] == 10, "no toca linkedin")
    comprobar(cx.execute("SELECT COUNT(*) c FROM cola WHERE estado='publicado'"
                         ).fetchone()["c"] == 1, "no toca lo publicado")
    try:
        cola.purgar(cx, "bluesky", cola.PUBLICADO)
        comprobar(False, "purgar lo publicado debe fallar")
    except ValueError:
        comprobar(True, "purgar lo publicado lanza ValueError")
    cx.close()


def prueba_entradas_invalidas():
    print("\n[7] falla ruidosamente ante lo que no existe (directiva 20)")
    cx, _ = nueva_bd()
    for destino, tipo, cuerpo, qué in [
            ("linkedln", "NOTA", "x", "destino mal escrito"),
            ("linkedin", "NOTITA", "x", "tipo inexistente"),
            ("linkedin", "NOTA", "   ", "cuerpo en blanco")]:
        try:
            cola.encolar(cx, destino, tipo, cuerpo)
            comprobar(False, f"{qué} debería lanzar excepción")
        except ValueError:
            comprobar(True, f"{qué} -> ValueError")
    try:
        cola.reclamar(cx, "linkedln")
        comprobar(False, "reclamar con destino mal escrito debería fallar")
    except ValueError:
        comprobar(True, "reclamar con destino mal escrito -> ValueError")
    try:
        cola.marcar_publicado(cx, 99999)
        comprobar(False, "marcar una fila inexistente debería fallar")
    except LookupError:
        comprobar(True, "marcar una fila inexistente -> LookupError")
    cx.close()


def prueba_que_las_pruebas_discriminan():
    """
    Rompe la regla a propósito y comprueba que la prueba [2] se cae. Una batería
    que sigue verde con el código roto no mide nada.
    """
    print("\n[8] con reddit declarado BARATO, la prueba [2] tiene que romperse")
    original = cola.SENSIBLES
    cola.SENSIBLES = original - {"reddit"}
    try:
        cx, _ = nueva_bd()
        i = cola.encolar(cx, "reddit", "NOTA", "sin aprobar", "https://xiliux.com/r")
        vería = [f["id"] for f in cola.reclamar(cx, "reddit")]
        publicaría = cola.marcar_publicado(cx, i)
        cx.close()
        comprobar(vería == [i] and publicaría is True,
                  "roto a propósito, reddit publica sin aprobación → la prueba [2] SÍ discrimina")
    finally:
        cola.SENSIBLES = original

    # Y queda como estaba.
    cx, _ = nueva_bd()
    i = cola.encolar(cx, "reddit", "NOTA", "sin aprobar", "https://xiliux.com/r")
    comprobar(cola.reclamar(cx, "reddit") == [] and cola.marcar_publicado(cx, i) is False,
              "restaurado: reddit vuelve a exigir aprobación")
    cx.close()



def prueba_encuadre_social():
    """La imagen alta se encuadra a tarjeta; la apaisada pasa intacta.

    Pareja obligatoria (directiva 33): con solo el caso rojo pasaría igual un
    encuadrador que reescale TODO; con solo el verde, uno que no toque nada. El
    mutante que este par mata es exactamente el bug que había — publicar la tira
    de página completa tal cual — y su inverso, recomprimir de más.
    """
    import io
    from PIL import Image
    import publicar_cola as pc

    def card(w, h, color):
        buf = io.BytesIO()
        Image.new("RGB", (w, h), color).save(buf, format="PNG")
        return buf.getvalue()

    # ROJO: 1440x16075, como la portada de xiliux. DEBE salir 1200x630.
    alto = pc._encuadrar_social(card(1440, 16075, (10, 20, 40)))
    aw, ah = Image.open(io.BytesIO(alto)).size
    comprobar((aw, ah) == (1200, 630),
              f"tira vertical 1440x16075 → tarjeta 1200x630 (salió {aw}x{ah})")

    # VERDE: 1440x900, como un pantallazo de app. DEBE quedar byte a byte igual.
    orig = card(1440, 900, (40, 20, 10))
    igual = pc._encuadrar_social(orig)
    comprobar(igual == orig,
              "apaisada 1440x900 pasa INTACTA (ni recorte ni recompresión)")

    # BORDE: cuadrada exacta pasa intacta (h == w no es 'más alta que ancha').
    cuad = card(1000, 1000, (20, 40, 20))
    comprobar(pc._encuadrar_social(cuad) == cuad,
              "cuadrada 1000x1000 pasa intacta (el umbral es h > w, no h >= w)")


def prueba_destinos_ui():
    """Instagram y Threads existen como destinos y son SENSIBLES: solo ven lo
    aprobado. La pareja (directiva 33): un borrador NO lo ve el canal; tras
    aprobarlo, SÍ. Con solo el rojo pasaría un canal que nunca ve nada; con solo
    el verde, uno que ve todo."""
    print("\n[9] instagram/threads SENSIBLES; x BARATO (siempre aprobado, 2026-11-07)")
    comprobar({"instagram", "threads"} <= cola.SENSIBLES,
              "instagram y threads están en SENSIBLES")
    comprobar(not ({"instagram", "threads"} & cola.BARATOS),
              "y NO están en BARATOS (no consumen borradores)")
    for red in ("instagram", "threads"):
        cx, _ = nueva_bd()
        i = cola.encolar(cx, red, "NOTA", f"nota {red}", f"https://xiliux.com/{red}")
        comprobar(cola.reclamar(cx, red) == [],
                  f"{red}: un borrador NO es reclamable (sensible)")
        cola.aprobar(cx, i)
        comprobar([f["id"] for f in cola.reclamar(cx, red)] == [i],
                  f"{red}: tras aprobar, SÍ es reclamable")
        cx.close()
    # x es BARATO pese a publicarse por UI: un borrador SÍ es reclamable sin aprobar
    # (como LinkedIn). El caso ROJO del sensible invertido: debe salir sin visto bueno.
    comprobar("x" in cola.BARATOS and "x" not in cola.SENSIBLES,
              "x está en BARATOS (siempre aprobado)")
    cx, _ = nueva_bd()
    ix = cola.encolar(cx, "x", "NOTA", "nota x", "https://xiliux.com/x")
    comprobar([f["id"] for f in cola.reclamar(cx, "x")] == [ix],
              "x: un borrador SÍ es reclamable sin aprobar (barato)")
    cx.close()


def prueba_publicar_ui():
    """La lógica de publicar_ui que NO necesita navegador: el texto con enlace y
    la invariante dura 'Instagram exige imagen'. El resto (conducir el DOM) es
    E2E y se verifica con --simulacro contra la cuenta real (directiva 28)."""
    print("\n[10] publicar_ui: texto con enlace e invariante de imagen de IG")
    import tempfile
    import publicar_ui as pu

    cx, _ = nueva_bd()
    # _texto añade el enlace si no está, y no lo duplica si ya está.
    i1 = cola.encolar(cx, "threads", "NOTA", "cuerpo sin enlace", "https://xiliux.com/a")
    f1 = cx.execute("SELECT * FROM cola WHERE id=?", (i1,)).fetchone()
    comprobar(pu._texto(f1).endswith("https://xiliux.com/a"),
              "_texto añade el enlace al final cuando no está en el cuerpo")
    i2 = cola.encolar(cx, "threads", "NOTA", "mira https://xiliux.com/b aquí",
                      "https://xiliux.com/b")
    f2 = cx.execute("SELECT * FROM cola WHERE id=?", (i2,)).fetchone()
    comprobar(pu._texto(f2).count("https://xiliux.com/b") == 1,
              "_texto NO duplica el enlace si ya aparece en el cuerpo")

    # Invariante: Instagram exige imagen. El guardián corre ANTES de tocar la
    # página, así que se prueba con page=None sin abrir navegador.
    i3 = cola.encolar(cx, "instagram", "NOTA", "sin imagen", "https://xiliux.com/c")
    f3 = cx.execute("SELECT * FROM cola WHERE id=?", (i3,)).fetchone()
    try:
        pu.publicar_instagram(None, f3, publicar=False)
        comprobar(False, "IG sin imagen debería exigir imagen")
    except ValueError as e:
        comprobar("imagen" in str(e), "IG sin imagen -> ValueError que exige imagen")

    # Control (directiva 33): CON imagen pasa el guardián y falla DESPUÉS por
    # page=None, no por imagen. Un mutante que siempre exigiera imagen caería aquí.
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(b"\x89PNG\r\n"); tmp.close()
    i4 = cola.encolar(cx, "instagram", "NOTA", "con imagen", "https://xiliux.com/d",
                      imagen=tmp.name, imagen_alt="una tarjeta")
    f4 = cx.execute("SELECT * FROM cola WHERE id=?", (i4,)).fetchone()
    try:
        pu.publicar_instagram(None, f4, publicar=False)
        comprobar(False, "no alcanzable: page=None debe romper al navegar")
    except ValueError as e:
        comprobar(False, f"IG CON imagen NO debe fallar por imagen: {e}")
    except Exception:
        comprobar(True, "IG con imagen pasa el guardián de imagen (rompe luego por page=None)")
    os.unlink(tmp.name)
    cx.close()


def prueba_trasplante_cookies():
    """El trasplante de sesión desde Firefox DISCRIMINA por dominio: un filtro
    ingenuo `LIKE '%x.com'` casaría okx.com/xiliux.com/hanerix.com y metería
    cookies ajenas en el perfil (bug medido 2026-11-07, directiva 23). El caso ROJO
    es justo esos dominios vecinos; el VERDE, x.com y twitter.com. Además la
    normalización de `expires` (sesión -> -1, enorme -> tope)."""
    print("\n[11] trasplante de cookies: filtro de dominio exacto-o-subdominio (D23)")
    import sqlite3
    import shutil
    import publicar_ui as pu

    d = tempfile.mkdtemp()
    db = os.path.join(d, "cookies.sqlite")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, "
                "path TEXT, expiry INTEGER, isSecure INTEGER, isHttpOnly INTEGER, "
                "sameSite INTEGER)")
    con.executemany("INSERT INTO moz_cookies VALUES (?,?,?,?,?,?,?,?)", [
        (".x.com", "auth_token", "SECRETO", "/", 0, 1, 1, 0),             # sesión
        ("x.com", "ct0", "TOK", "/", 9999999999, 1, 0, 1),               # normal
        (".twitter.com", "twid", "T", "/", 9999999999999, 1, 0, 0),  # expiry > tope año 9999
        (".upload.x.com", "up", "U", "/", 123, 1, 0, 1),
        ("okx.com", "ok_login_type", "AJENO", "/", 123, 1, 0, 1),        # ROJO: vecino
        ("www.okx.com", "ok", "AJENO", "/", 123, 1, 0, 1),               # ROJO
        ("xiliux.com", "_tk", "AJENO", "/", 123, 1, 0, 1),               # ROJO
        ("hanerix.com", "x", "AJENO", "/", 123, 1, 0, 1),                # ROJO
    ])
    con.commit(); con.close()

    cs = pu._cookies_firefox("x", d)
    doms = {c["domain"] for c in cs}
    names = {c["name"] for c in cs}
    comprobar(doms == {".x.com", "x.com", ".twitter.com", ".upload.x.com"},
              f"solo dominios de X (sin okx/xiliux/hanerix): {sorted(doms)}")
    comprobar(not any(c["value"] == "AJENO" for c in cs),
              "NINGUNA cookie de dominio vecino se cuela (caso rojo)")
    comprobar({"auth_token", "ct0", "twid"} <= names,
              "las cookies de sesión de X sí entran (caso verde)")
    # normalización de expires: sesión -> -1; enorme -> tope; normal intacto
    exp = {c["name"]: c["expires"] for c in cs}
    comprobar(exp["auth_token"] == -1, "expiry 0 (sesión) -> -1")
    comprobar(exp["twid"] == 253402300799.0, "expiry desbordado -> tope año 9999")
    comprobar(exp["ct0"] == 9999999999.0, "expiry normal intacto")
    shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    for prueba in (prueba_volumen, prueba_discriminacion_por_canal, prueba_duplicados,
                   prueba_error_inyectado, prueba_concurrencia, prueba_alcance_del_borrado,
                   prueba_entradas_invalidas, prueba_que_las_pruebas_discriminan,
                   prueba_encuadre_social, prueba_destinos_ui, prueba_publicar_ui,
                   prueba_trasplante_cookies):
        prueba()
    print("\n" + "=" * 60)
    if FALLOS:
        print(f"{len(FALLOS)} COMPROBACIONES FALLIDAS:")
        for f in FALLOS:
            print("   -", f)
        sys.exit(1)
    print("todas las comprobaciones pasan")
    sys.exit(0)
