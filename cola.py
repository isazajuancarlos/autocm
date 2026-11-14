#!/usr/bin/env python3
"""
La cola de publicación de autocm: el único estado del sistema.

Existe porque los canales no son iguales. Bluesky y Mastodon aceptan que una
máquina publique; LinkedIn, Reddit y Hacker News castigan justo eso. En vez de
un tubo que trata a los nueve igual, cada destino declara si es BARATO —consume
borradores solo— o SENSIBLE —espera el visto bueno de una persona—.

Eso convierte el bloqueo de la API de LinkedIn en fricción de medio minuto:
autocm redacta y encola, Juan aprueba y pega. El día que llegue el token, el
publicador consume la misma cola sin que cambie nada más.

    python cola.py listar                  # qué hay, por estado
    python cola.py ver 7                   # el texto completo de una fila
    python cola.py aprobar 7               # borrador -> aprobado
    python cola.py publicado 7 --url ...   # aprobado -> publicado, con su enlace
    python cola.py pendientes linkedin     # lo que toca pegar a mano, listo
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone

BD = os.getenv("COLA_DB", "cola.sqlite")

BORRADOR, APROBADO, PUBLICADO, FALLIDO = "borrador", "aprobado", "publicado", "fallido"
ESTADOS = (BORRADOR, APROBADO, PUBLICADO, FALLIDO)

# Un destino BARATO puede consumir borradores; uno SENSIBLE exige `aprobado`.
# La clasificación es del canal, no del texto: no depende de lo que se publique
# sino de cómo castiga la plataforma que publique una máquina.
# Facebook es SENSIBLE no porque castigue la automatización —no lo hace como
# Reddit—, sino porque es una página de MARCA con público amplio: lo que sale ahí
# se cura, no se vacía a chorro. Su línea editorial es de producto/caso (comprador
# no técnico), distinta de la técnica que va a Mastodon/dev.to, así que pasa por
# el visto bueno.
# LinkedIn es BARATO desde 2026-10-22 (decisión de Juan): publica automático bajo
# el perfil `person` con el MISMO texto técnico que Mastodon/Bluesky —la redacción
# del pipeline ya es adecuada—. Lo que evita el bloqueo no es curar cada texto sino
# la CADENCIA: su timer es Mar/Jue/Sáb (3/sem) con retardo aleatorio, que LinkedIn
# tolera sin marcarlo como bot.
# instagram/threads se publican conduciendo la UI web logueada con Playwright
# (publicar_ui.py), no por API: ninguna tiene API orgánica asequible. Son SENSIBLES
# por DOS motivos: (1) son cuentas de MARCA, como facebook; (2) automatizar la UI es
# justo lo que su ToS prohíbe y detecta, y un baneo de la cuenta de Xiliux NO se
# deshace — el visto bueno es la barandilla antes de que una máquina publique en una
# cuenta irreemplazable.
# "x" (cuenta de MARCA Xiliux @xiliuxDev, NUNCA la personal @isazajuancarlos) es
# BARATO desde 2026-11-07 (decisión de Juan, «siempre aprobado»): publica automático
# el MISMO texto del pipeline, como LinkedIn. OJO: x SÍ se publica por UI (Playwright,
# en publicar_ui.py REDES_UI), así que SIGUE conduciendo la UI — lo que cambia es que
# no espera visto bueno. La aprobación NO reducía el riesgo de baneo (la máquina pulsa
# "publicar" igual); solo pre-revisaba el contenido. La mitigación del baneo es la
# CADENCIA baja (timer Jue/Dom 2/sem + retardo aleatorio), que se mantiene.
SENSIBLES = {"reddit", "hackernews", "lobsters", "thisweekinrust", "facebook",
             "instagram", "threads"}
# discord y nostr son canales PROPIOS (webhook propio / clave propia): no castigan
# que publique una máquina, así que son BARATOS. nostr publica por relays firmando
# la nota (schnorr); discord por webhook. Ambos por publicar_cola.py (API).
BARATOS = {"bluesky", "mastodon", "devto", "hashnode", "telegram", "discord",
           "linkedin", "x", "nostr"}
DESTINOS = SENSIBLES | BARATOS

TIPOS = {"NOTA", "ARTICULO", "HITO"}


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conectar(ruta=None):
    cx = sqlite3.connect(ruta or BD, isolation_level=None, timeout=30)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA foreign_keys=ON")
    cx.executescript("""
        CREATE TABLE IF NOT EXISTS cola (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            destino       TEXT NOT NULL,
            tipo          TEXT NOT NULL,
            estado        TEXT NOT NULL DEFAULT 'borrador',
            cuerpo        TEXT NOT NULL,
            enlace        TEXT,
            imagen        TEXT,
            imagen_alt    TEXT,
            creado        TEXT NOT NULL,
            modificado    TEXT NOT NULL,
            publicado_en  TEXT,
            url_publicada TEXT,
            error         TEXT,
            CHECK (estado IN ('borrador','aprobado','publicado','fallido')),
            CHECK (length(trim(cuerpo)) > 0),
            -- Una imagen SIN texto alternativo no se guarda: es inaccesible y
            -- Bluesky/Mastodon penalizan el adjunto sin `alt`. El `alt` sin
            -- imagen tampoco: sería un dato que no describe nada.
            CHECK ((imagen IS NULL AND imagen_alt IS NULL)
                   OR (imagen IS NOT NULL AND length(trim(imagen_alt)) > 0))
        );
        -- Un mismo enlace no se encola dos veces para el mismo destino. Sin esto
        -- una segunda corrida duplica la cola entera en silencio, y el duplicado
        -- solo se ve cuando ya salió publicado dos veces.
        CREATE UNIQUE INDEX IF NOT EXISTS cola_destino_enlace
            ON cola(destino, enlace) WHERE enlace IS NOT NULL;
        CREATE INDEX IF NOT EXISTS cola_estado ON cola(estado, destino);
    """)
    # Migración idempotente para la cola que ya existe: el CREATE de arriba solo
    # crea columnas en una BD nueva, así que una `cola.sqlite` anterior no tendría
    # `imagen`/`imagen_alt`. `ADD COLUMN` no admite `IF NOT EXISTS`, así que se
    # mira el esquema antes. El CHECK de coherencia no se puede añadir por ALTER a
    # una tabla que ya existe; lo cubre `encolar()`, que valida lo mismo en Python.
    columnas = {r["name"] for r in cx.execute("PRAGMA table_info(cola)")}
    for nueva in ("imagen", "imagen_alt"):
        if nueva not in columnas:
            cx.execute(f"ALTER TABLE cola ADD COLUMN {nueva} TEXT")
    return cx


def encolar(cx, destino, tipo, cuerpo, enlace=None, imagen=None, imagen_alt=None):
    """
    Devuelve el id, o None si ya estaba encolado ese enlace para ese destino.
    Falla ruidosamente ante un destino o tipo que no existe: un typo en el nombre
    del canal produciría una fila que ningún publicador reclama nunca, y una cola
    que calla es exactamente lo que esta pieza existe para impedir.

    `imagen` es una ruta a un archivo local; se guarda ABSOLUTA porque el
    temporizador publica desde otro directorio. Una imagen exige `imagen_alt`
    (texto alternativo): sin él es inaccesible y los canales lo penalizan, así que
    se rechaza aquí en vez de dejar salir un adjunto mudo (directiva 20).
    """
    if destino not in DESTINOS:
        raise ValueError(f"destino desconocido: {destino!r} (conocidos: {sorted(DESTINOS)})")
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconocido: {tipo!r} (conocidos: {sorted(TIPOS)})")
    if not cuerpo or not cuerpo.strip():
        raise ValueError("cuerpo vacío")

    if imagen is not None:
        if not imagen_alt or not imagen_alt.strip():
            raise ValueError("una imagen sin texto alternativo no se encola: sin `alt` "
                             "es inaccesible y Bluesky/Mastodon penalizan el adjunto mudo")
        if not os.path.isfile(imagen):
            raise ValueError(f"la imagen no existe: {imagen!r}")
        imagen = os.path.abspath(imagen)
        imagen_alt = imagen_alt.strip()
    elif imagen_alt is not None:
        raise ValueError("`imagen_alt` sin `imagen` no describe nada")

    t = _ahora()
    try:
        cur = cx.execute(
            "INSERT INTO cola (destino,tipo,estado,cuerpo,enlace,imagen,imagen_alt,creado,modificado)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (destino, tipo, BORRADOR, cuerpo.strip(), enlace, imagen, imagen_alt, t, t))
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def aprobar(cx, id_):
    """borrador -> aprobado. Atómico: el WHERE lleva el estado de partida."""
    cur = cx.execute(
        "UPDATE cola SET estado=?, modificado=? WHERE id=? AND estado=?",
        (APROBADO, _ahora(), id_, BORRADOR))
    return cur.rowcount == 1


def reclamar(cx, destino, limite=10):
    """
    Lo que ese destino puede publicar AHORA. Un canal sensible solo ve lo
    aprobado; uno barato ve también los borradores.

    La invariante vive aquí, fuera de cada publicador: si cada uno decidiera por
    su cuenta qué estado le vale, bastaría un publicador nuevo mal escrito para
    que LinkedIn publicara sin que nadie lo aprobara.
    """
    if destino not in DESTINOS:
        raise ValueError(f"destino desconocido: {destino!r}")
    estados = (APROBADO,) if destino in SENSIBLES else (APROBADO, BORRADOR)
    marcas = ",".join("?" * len(estados))
    return cx.execute(
        f"SELECT * FROM cola WHERE destino=? AND estado IN ({marcas})"
        f" ORDER BY id LIMIT ?", (destino, *estados, limite)).fetchall()


def marcar_publicado(cx, id_, url=None):
    """
    -> publicado. Solo desde `aprobado` para los sensibles; los baratos pueden
    saltar desde `borrador`. Devuelve False si la fila ya estaba publicada, que
    es lo que impide la doble publicación cuando dos corridas se solapan.
    """
    fila = cx.execute("SELECT destino,estado FROM cola WHERE id=?", (id_,)).fetchone()
    if fila is None:
        raise LookupError(f"no existe la fila {id_}")
    permitidos = (APROBADO,) if fila["destino"] in SENSIBLES else (APROBADO, BORRADOR)
    marcas = ",".join("?" * len(permitidos))
    t = _ahora()
    cur = cx.execute(
        f"UPDATE cola SET estado=?, modificado=?, publicado_en=?, url_publicada=?,"
        f" error=NULL WHERE id=? AND estado IN ({marcas})",
        (PUBLICADO, t, t, url, id_, *permitidos))
    return cur.rowcount == 1


def marcar_fallido(cx, id_, error):
    """
    El publicador que falla NO deja la fila en publicado ni la borra: la marca
    con el motivo. Una fila fallida es visible; un envío perdido, no.
    """
    cur = cx.execute(
        "UPDATE cola SET estado=?, modificado=?, error=? WHERE id=? AND estado!=?",
        (FALLIDO, _ahora(), str(error)[:500], id_, PUBLICADO))
    return cur.rowcount == 1


def reintentar(cx, id_):
    """fallido -> borrador, para que vuelva a entrar en el circuito normal."""
    cur = cx.execute(
        "UPDATE cola SET estado=?, modificado=?, error=NULL WHERE id=? AND estado=?",
        (BORRADOR, _ahora(), id_, FALLIDO))
    return cur.rowcount == 1


def resumen(cx):
    return cx.execute(
        "SELECT destino, estado, COUNT(*) n FROM cola GROUP BY destino, estado"
        " ORDER BY destino, estado").fetchall()


def purgar(cx, destino, estado=BORRADOR):
    """
    Borra SOLO lo que se va a regenerar: un destino y un estado concretos, nunca
    la tabla entera (directiva 22). El alcance va como parámetro; sin destino no
    se borra nada, y lo publicado no se toca nunca porque es el historial.
    """
    if destino not in DESTINOS:
        raise ValueError(f"destino desconocido: {destino!r}")
    if estado == PUBLICADO:
        raise ValueError("lo publicado es el historial: no se purga")
    cur = cx.execute("DELETE FROM cola WHERE destino=? AND estado=?", (destino, estado))
    return cur.rowcount


# --------------------------------------------------------------------------- CLI

def _pinta(fila, ancho=70):
    cuerpo = fila["cuerpo"].replace("\n", " ⏎ ")
    if len(cuerpo) > ancho:
        cuerpo = cuerpo[:ancho - 1] + "…"
    marca = {BORRADOR: "·", APROBADO: "✓", PUBLICADO: "✔", FALLIDO: "✗"}[fila["estado"]]
    return f"{marca} {fila['id']:>4}  {fila['destino']:<14} {fila['tipo']:<9} {cuerpo}"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="orden", required=True)

    q = sub.add_parser("listar", help="todo lo que hay en la cola")
    q.add_argument("--estado", choices=ESTADOS)
    q.add_argument("--destino", choices=sorted(DESTINOS))

    v = sub.add_parser("ver", help="el texto completo de una fila")
    v.add_argument("id", type=int)

    a = sub.add_parser("aprobar", help="borrador -> aprobado")
    a.add_argument("id", type=int, nargs="+")

    m = sub.add_parser("publicado", help="marcar como publicado")
    m.add_argument("id", type=int)
    m.add_argument("--url", help="enlace de la publicación ya hecha")

    r = sub.add_parser("pendientes", help="lo que ese destino puede publicar ya")
    r.add_argument("destino", choices=sorted(DESTINOS))

    e = sub.add_parser("encolar", help="añadir una fila a mano")
    e.add_argument("destino", choices=sorted(DESTINOS))
    e.add_argument("tipo", choices=sorted(TIPOS))
    e.add_argument("cuerpo")
    e.add_argument("--enlace")

    args = p.parse_args()
    cx = conectar()

    if args.orden == "listar":
        cond, params = [], []
        if args.estado:
            cond.append("estado=?"); params.append(args.estado)
        if args.destino:
            cond.append("destino=?"); params.append(args.destino)
        sql = "SELECT * FROM cola" + (" WHERE " + " AND ".join(cond) if cond else "") + " ORDER BY id"
        filas = cx.execute(sql, params).fetchall()
        for f in filas:
            print(_pinta(f))
        print(f"\n{len(filas)} filas")
        for r_ in resumen(cx):
            print(f"   {r_['destino']:<14} {r_['estado']:<10} {r_['n']}")

    elif args.orden == "ver":
        f = cx.execute("SELECT * FROM cola WHERE id=?", (args.id,)).fetchone()
        if not f:
            sys.exit(f"no existe la fila {args.id}")
        print(f"#{f['id']}  {f['destino']}  {f['tipo']}  [{f['estado']}]")
        print(f"enlace: {f['enlace'] or '—'}")
        if f["imagen"]:
            marca = "✓" if os.path.isfile(f["imagen"]) else "✗ NO EXISTE"
            print(f"imagen: {f['imagen']}  [{marca}]")
            print(f"alt:    {f['imagen_alt']}")
        if f["url_publicada"]:
            print(f"publicado en: {f['url_publicada']}  ({f['publicado_en']})")
        if f["error"]:
            print(f"error: {f['error']}")
        print("-" * 60)
        print(f["cuerpo"])

    elif args.orden == "aprobar":
        for i in args.id:
            print(f"#{i}: {'aprobado' if aprobar(cx, i) else 'NO (no existe o no estaba en borrador)'}")

    elif args.orden == "publicado":
        try:
            ok = marcar_publicado(cx, args.id, args.url)
        except LookupError as err:
            sys.exit(str(err))
        print(f"#{args.id}: {'publicado' if ok else 'NO (ya lo estaba, o falta aprobarlo)'}")

    elif args.orden == "pendientes":
        filas = reclamar(cx, args.destino, limite=100)
        if not filas:
            aviso = " (los sensibles solo ven lo aprobado)" if args.destino in SENSIBLES else ""
            print(f"nada pendiente para {args.destino}{aviso}")
        for f in filas:
            print("=" * 66)
            print(f"#{f['id']}  [{f['estado']}]  {f['enlace'] or ''}")
            print(f["cuerpo"])
        if filas:
            print("=" * 66)
            print(f"\n{len(filas)} listas. Al pegarlas: python cola.py publicado <id> --url <enlace>")

    elif args.orden == "encolar":
        i = encolar(cx, args.destino, args.tipo, args.cuerpo, args.enlace)
        print(f"encolada #{i}" if i else "ya estaba encolada (mismo destino y enlace)")

    cx.close()


if __name__ == "__main__":
    main()
