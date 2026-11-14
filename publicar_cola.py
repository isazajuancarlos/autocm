#!/usr/bin/env python3
"""
Consume la cola y publica en los canales baratos.

Es la pieza 4 del rediseño: un publicador sin lógica de negocio, que toma de la
cola lo que le toca y lo entrega. Quién puede consumir qué lo decide `cola.py`,
no este fichero — de ahí que aquí no haya ni una comprobación de estado.

    .venv/bin/python publicar_cola.py --destino bluesky --simulacro
    .venv/bin/python publicar_cola.py --destino bluesky --limite 1

En Bluesky el enlace va como *facet*. Sin eso el SDK publica `facets=None` y la
URL sale como texto muerto: se ve, no se pincha. Un enlace que no se pincha
convierte cero, que es justo lo que estas publicaciones existen para hacer.
"""
import argparse
import io
import os
import sys

from dotenv import load_dotenv

import cola

load_dotenv()

# Cabecera de versión de la Posts API (misma que main.py). LinkedIn retira cada
# versión a los ~12 meses y responde 426 cuando caduca.
LINKEDIN_VERSION = os.getenv("LINKEDIN_VERSION", "202606")


def _interruptor(destino):
    """
    Respeta la misma bandera que main.py. Un canal apagado NO publica y lo dice:
    si esto callara, la cola se vaciaría contra un canal que nadie encendió y
    las filas quedarían marcadas como publicadas sin haber salido.
    """
    return os.getenv(f"{destino.upper()}_ENABLED", "false").strip().lower() == "true"


# Facebook (y en menor medida Bluesky/Mastodon) meten la foto adjunta en un
# thumbnail apaisado del feed. Un pantallazo de PÁGINA COMPLETA —la portada de
# xiliux mide 1440x16075— entra ahí como una tira vertical aplastada e ilegible:
# el "mosaico" que se ve publicado. Las capturas se toman full_page a propósito
# (sirven de documentación), así que el encuadre social se hace AQUÍ, en la
# frontera de publicación, y una sola vez para los tres canales (directiva 19).
#
# La regla, en una frase para poder auditarla (directiva 23): una imagen APAISADA
# o CUADRADA se publica tal cual; una más ALTA que ANCHA se recorta por ARRIBA
# —donde está el encabezado/héroe de la página, que es lo legible y de marca— a
# una tarjeta 1200x630 (el ratio 1.91:1 que FB y Open Graph tratan bien). No se
# reescala una imagen ya apaisada: perdería nitidez sin ninguna ganancia.
TARJETA = (1200, 630)          # el estándar de Open Graph / enlace de FB
RATIO_TARJETA = TARJETA[0] / TARJETA[1]


def _encuadrar_social(data):
    """Bytes PNG encuadrados para redes. Idempotente y conservador: si la imagen
    no es más alta que ancha, devuelve los MISMOS bytes sin recomprimir."""
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    w, h = im.size
    if h <= w:                 # apaisada o cuadrada: FB la muestra bien
        return data
    # Recorte por arriba a 1.91:1, luego a 1200x630. El alto del recorte sale del
    # ancho para no dejar barras: para 1440 de ancho son los 754 px de arriba.
    alto_recorte = round(w / RATIO_TARJETA)
    caja = im.convert("RGB").crop((0, 0, w, min(alto_recorte, h)))
    tarjeta = caja.resize(TARJETA, Image.LANCZOS)
    buf = io.BytesIO()
    tarjeta.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _leer_imagen(fila):
    """
    `(bytes, alt)` de la imagen de la fila, o `None` si no lleva ninguna.

    Falla si la ruta ya no existe: la fila se encoló con la imagen presente y
    validada, así que perderla entre encolar y publicar es un fallo real — no un
    post que sale sin foto en silencio (directiva 20).
    """
    ruta = fila["imagen"]
    if not ruta:
        return None
    with open(ruta, "rb") as fh:
        return _encuadrar_social(fh.read()), fila["imagen_alt"]


def _cliente_bluesky():
    from atproto import Client
    usuario = os.getenv("BLUESKY_HANDLE") or os.getenv("BLUESKY_USERNAME")
    clave = os.getenv("BLUESKY_PASSWORD") or os.getenv("BLUESKY_APP_PASSWORD")
    if not usuario or not clave:
        raise RuntimeError("faltan BLUESKY_HANDLE/BLUESKY_PASSWORD en .env")
    c = Client()
    c.login(usuario, clave)
    return c


def _publicar_bluesky(cliente, fila):
    from atproto import client_utils

    cuerpo, enlace = fila["cuerpo"], fila["enlace"]
    if enlace and cuerpo.rstrip().endswith(enlace):
        texto = cuerpo[: cuerpo.rstrip().rfind(enlace)].rstrip()
        constructor = client_utils.TextBuilder().text(texto + "\n\n").link(enlace, enlace)
    else:
        # Sin enlace al final no hay facet que construir, y forzarlo marcaría
        # como enlace un trozo de texto que no lo es.
        constructor = client_utils.TextBuilder().text(cuerpo)

    img = _leer_imagen(fila)
    if img:
        data, alt = img
        # `send_image` acepta el MISMO `TextBuilder`, así que el enlace sigue
        # siendo un facet pinchable Y la imagen va adjunta con su `alt`.
        r = cliente.send_image(text=constructor, image=data, image_alt=alt)
    else:
        r = cliente.send_post(constructor)
    # at://did/app.bsky.feed.post/RKEY  ->  URL que una persona puede abrir
    rkey = r.uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{cliente.me.handle}/post/{rkey}"


def _cliente_mastodon():
    from mastodon import Mastodon
    # MASTODON_API_URL, que es el nombre que ya usan main.py y .env.example. El
    # valor lo fija quien primero lo lee: inventar aquí MASTODON_API_BASE_URL
    # habría dado dos vocabularios para el mismo dato y un fallo silencioso.
    token = os.getenv("MASTODON_ACCESS_TOKEN")
    base = os.getenv("MASTODON_API_URL")
    if not token or not base:
        raise RuntimeError("faltan MASTODON_ACCESS_TOKEN/MASTODON_API_URL en .env")
    return Mastodon(access_token=token, api_base_url=base)


def _publicar_mastodon(cliente, fila):
    # Mastodon convierte las URL en enlaces por su cuenta; no hay facets que armar.
    img = _leer_imagen(fila)
    if img:
        # `media_post` sube el archivo (acepta la ruta directa) con su `alt` como
        # descripción; el estado lo referencia por `media_ids`. Subir antes de
        # publicar es lo que exige la API: el `id` no existe hasta que la subida
        # termina.
        adjunto = cliente.media_post(fila["imagen"], description=fila["imagen_alt"])
        return cliente.status_post(status=fila["cuerpo"], media_ids=[adjunto])["url"]
    return cliente.status_post(status=fila["cuerpo"])["url"]


def _cliente_facebook():
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("falta FACEBOOK_PAGE_ACCESS_TOKEN en .env")
    # Con un token de PÁGINA, el nodo `me` ES la página, así que publicamos
    # contra `me` y NO contra un FACEBOOK_PAGE_ID aparte. Ese ID era una segunda
    # fuente de identidad que se desincronizó del token: el .env del VPS apuntaba
    # a una página distinta de la del token y el POST fallaba con 400. El token
    # ya dice a qué página pertenece; una sola fuente no puede contradecirse.
    return (token, "me")


def _publicar_facebook(cliente, fila):
    import requests
    token, page = cliente
    img = _leer_imagen(fila)
    if img:
        data, _alt = img
        # Foto CON texto: `/photos` publica la imagen y usa `message` de pie. Es
        # un solo POST, así que no queda una foto suelta si el texto fallara. FB
        # no expone `alt` por la API pública, así que el alt viaja igual en la
        # cola (accesibilidad y reuso) pero aquí solo puede ir el pie.
        endpoint = f"https://graph.facebook.com/v18.0/{page}/photos"
        r = requests.post(endpoint, data={"message": fila["cuerpo"], "access_token": token},
                          files={"source": ("imagen", data)}, timeout=60)
    else:
        # Solo texto: el feed hace pinchables las URL del cuerpo por su cuenta.
        endpoint = f"https://graph.facebook.com/v18.0/{page}/feed"
        r = requests.post(endpoint, data={"message": fila["cuerpo"], "access_token": token},
                          timeout=30)
    if r.status_code != 200:
        # Un 400 con `error` dentro es un rechazo de la publicación, no una avería
        # de red: se propaga con el motivo para que la cola lo marque fallido.
        raise RuntimeError(f"Graph API {r.status_code}: {r.text[:200]}")
    j = r.json()
    post_id = j.get("post_id") or j.get("id")
    return f"https://www.facebook.com/{post_id}"


def _cliente_linkedin():
    # El autor lo fija LINKEDIN_AUTHOR_MODE, igual que main._linkedin_author():
    # "person" -> el perfil (w_member_social); "organization" -> la página
    # (Community Management API). Se replica aquí en 4 líneas en vez de importar
    # main.py, que arrastra openai/tweepy/atproto/… al arranque del timer.
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    modo = os.getenv("LINKEDIN_AUTHOR_MODE", "organization").strip().lower()
    if modo == "person":
        sub = os.getenv("LINKEDIN_PERSON_SUB")
        author = f"urn:li:person:{sub}" if sub else None
    else:
        org = os.getenv("LINKEDIN_ORG_ID")
        author = f"urn:li:organization:{org}" if org else None
    if not token or not author:
        raise RuntimeError("faltan LINKEDIN_ACCESS_TOKEN y/o el id del autor "
                           "(LINKEDIN_PERSON_SUB en modo person, LINKEDIN_ORG_ID en organization)")
    return (token, author)


def _publicar_linkedin(cliente, fila):
    import requests
    token, author = cliente
    if fila["imagen"]:
        # LinkedIn-con-imagen (Posts API /images: initializeUpload + PUT) aún no
        # está soportado aquí. Fallar ruidoso es mejor que publicar la nota SIN
        # la imagen prometida (directiva 20); las NOTAS de linkedin se encolan
        # como texto. Cuando haga falta imagen, se implementa el flujo de assets.
        raise RuntimeError(f"linkedin en la cola es solo-texto por ahora; la fila "
                           f"#{fila['id']} trae imagen y no se publica a medias")
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json",
               "X-Restli-Protocol-Version": "2.0.0",
               "LinkedIn-Version": LINKEDIN_VERSION}
    # commentary = cuerpo tal cual, como facebook/mastodon: LinkedIn hace
    # pinchables las URL del texto por su cuenta, y el enlace ya viaja en el cuerpo.
    body = {
        "author": author,
        "commentary": fila["cuerpo"],
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED",
                         "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    r = requests.post("https://api.linkedin.com/rest/posts",
                      headers=headers, json=body, timeout=30)
    if r.status_code != 201:
        # 401=token, 403=scope/permiso, 422=cuerpo: todos son rechazo, no avería
        # de red. Se propaga con el motivo para que la cola marque la fila fallida.
        raise RuntimeError(f"Posts API {r.status_code}: {r.text[:200]}")
    post_urn = r.headers.get("x-restli-id", "")
    return (f"https://www.linkedin.com/feed/update/{post_urn}"
            if post_urn else "https://www.linkedin.com/feed/")


def _cliente_discord():
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        raise RuntimeError("falta DISCORD_WEBHOOK_URL en .env")
    return url


def _publicar_discord(cliente, fila):
    # Canal PROPIO de Xiliux (webhook): sin riesgo de baneo por automatizar. El
    # cuerpo ya trae el enlace al final y Discord lo enlaza solo; si la fila trae
    # imagen, va adjunta como archivo.
    import json as _json
    import requests
    payload = {"content": fila["cuerpo"], "username": "Xiliux"}
    img = _leer_imagen(fila)
    try:
        if img:
            data, _alt = img
            r = requests.post(cliente + "?wait=true",
                              data={"payload_json": _json.dumps(payload)},
                              files={"file": ("tarjeta.png", data, "image/png")}, timeout=30)
        else:
            r = requests.post(cliente + "?wait=true", json=payload, timeout=30)
    except requests.RequestException as e:
        # La excepción cruda de requests incluye la URL del webhook, y esa URL
        # LLEVA el token (secreto). El error sube a cola.marcar_fallido (se PERSISTE
        # en la BD) y a print (journal), así que se sanea: solo el tipo, nunca la URL.
        raise RuntimeError(f"webhook Discord: {type(e).__name__}") from None
    if r.status_code not in (200, 204):
        # status y, a lo sumo, el cuerpo de error de Discord (no contiene la URL);
        # NUNCA `cliente`.
        raise RuntimeError(f"webhook Discord HTTP {r.status_code}")
    try:
        mid = r.json().get("id")
    except Exception:
        mid = None
    return f"discord#{mid}" if mid else "discord:enviado"


def _cliente_nostr():
    # Clave y relays del .env (D20: sin ellos NO publica, no inventa). NOSTR_NSEC
    # acepta bech32 (nsec1…) o hex de 64; NOSTR_RELAYS son wss://… separados por coma.
    from pynostr.key import PrivateKey
    nsec = os.getenv("NOSTR_NSEC", "").strip()
    relays = [r.strip() for r in os.getenv("NOSTR_RELAYS", "").split(",") if r.strip()]
    if not nsec:
        raise RuntimeError("falta NOSTR_NSEC en .env (nsec1… o hex de 64)")
    if not relays:
        raise RuntimeError("falta NOSTR_RELAYS en .env (wss://… separados por coma)")
    pk = PrivateKey.from_nsec(nsec) if nsec.startswith("nsec") else PrivateKey(bytes.fromhex(nsec))
    return (pk, relays)


def _publicar_nostr(cliente, fila):
    # Nota kind-1 firmada (schnorr) y difundida a los relays. Sin imagen: adjuntar
    # media en Nostr exige subirla antes a un host NIP-96/Blossom; el cuerpo ya trae
    # el enlace a xiliux.com. Se verifica la firma ANTES de difundir (D33) y se
    # CONFIRMA la aceptación de CADA relay por su OK: `run_sync` solo NO garantiza
    # entrega (medido 2026-11-07: una nota llegó a damus/primal y no a nos.lol).
    # Reintenta una vez los que falten y falla si NINGUNO acepta (D30).
    from pynostr.event import Event
    from pynostr.relay_manager import RelayManager
    pk, relays = cliente
    ev = Event(content=fila["cuerpo"], pubkey=pk.public_key.hex())
    ev.sign(pk.hex())
    if not ev.verify():
        raise RuntimeError("la firma Nostr no valida; no se difunde")

    def difundir(destinos):
        rm = RelayManager(timeout=15)
        for r in destinos:
            rm.add_relay(r)
        rm.publish_event(ev)
        rm.run_sync()
        aceptados = set()
        while rm.message_pool.has_ok_notices():
            ok = rm.message_pool.get_ok_notice()
            if getattr(ok, "ok", False):
                aceptados.add((getattr(ok, "url", "") or "").rstrip("/"))
        rm.close_all_relay_connections()
        return aceptados

    objetivo = {r.rstrip("/") for r in relays}
    aceptados = difundir(relays)
    if aceptados != objetivo:
        # Reintento completo: reenviar el MISMO evento firmado es idempotente (los
        # relays deduplican por id), recupera los que faltaron sin duplicar.
        aceptados |= difundir(relays)
    if not aceptados:
        raise RuntimeError("Nostr: ningún relay aceptó la nota")
    print("    nostr: %d/%d relays aceptaron" % (len(aceptados), len(objetivo)))
    return f"https://njump.me/{ev.id}"


def _cliente_telegram():
    # Bot de BotFather: token del bot + chat/canal destino. Canal PROPIO.
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise RuntimeError("faltan TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID en .env")
    return (token, chat)


def _publicar_telegram(cliente, fila):
    # Bot API (sendMessage / sendPhoto con imagen). Botón en línea a xiliux.com.
    # La URL de la API LLEVA el token del bot: se sanea el error de red igual que
    # en Discord (D23), o el token acabaría en la cola y el journal.
    import json as _json
    import requests
    token, chat = cliente
    boton = {"inline_keyboard": [[{"text": "🚀 Ver en Xiliux.com",
                                   "url": "https://xiliux.com"}]]}
    img = _leer_imagen(fila)
    try:
        if img:
            data, _alt = img
            if len(fila["cuerpo"]) > 1024:
                raise RuntimeError("telegram con imagen: el pie supera 1024 "
                                   "caracteres; no se publica a medias")
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat, "caption": fila["cuerpo"],
                      "reply_markup": _json.dumps(boton)},
                files={"photo": ("tarjeta.png", data, "image/png")}, timeout=30)
        else:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": fila["cuerpo"],
                      "reply_markup": _json.dumps(boton)}, timeout=30)
    except requests.RequestException as e:
        raise RuntimeError(f"telegram: {type(e).__name__}") from None
    if r.status_code != 200:
        raise RuntimeError(f"telegram HTTP {r.status_code}")
    res = r.json()
    if not res.get("ok"):
        # description de Telegram no incluye el token; es seguro mostrarla.
        raise RuntimeError(f"telegram API: {str(res.get('description'))[:120]}")
    msg = res.get("result", {})
    mid = msg.get("message_id")
    uname = (msg.get("chat") or {}).get("username")
    if uname and mid:
        return f"https://t.me/{uname}/{mid}"
    return f"telegram#{mid}" if mid else "telegram:enviado"


CANALES = {
    "bluesky": (_cliente_bluesky, _publicar_bluesky),
    "mastodon": (_cliente_mastodon, _publicar_mastodon),
    "facebook": (_cliente_facebook, _publicar_facebook),
    "linkedin": (_cliente_linkedin, _publicar_linkedin),
    "discord": (_cliente_discord, _publicar_discord),
    "nostr": (_cliente_nostr, _publicar_nostr),
    "telegram": (_cliente_telegram, _publicar_telegram),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--destino", required=True, choices=sorted(CANALES))
    p.add_argument("--limite", type=int, default=1,
                   help="cuántas publicar en esta corrida (por defecto 1)")
    p.add_argument("--simulacro", action="store_true",
                   help="enseña qué publicaría sin tocar la red ni la cola")
    args = p.parse_args()

    cx = cola.conectar()
    filas = cola.reclamar(cx, args.destino, limite=args.limite)
    if not filas:
        print(f"nada pendiente para {args.destino}")
        return 0

    if args.simulacro:
        for f in filas:
            print("=" * 66)
            print(f"#{f['id']}  [{f['estado']}]  {len(f['cuerpo'])} car.")
            print(f["cuerpo"])
            print(f"  ↳ enlace como facet: {f['enlace'] or '(ninguno)'}")
            if f["imagen"]:
                marca = "✓" if os.path.isfile(f["imagen"]) else "✗ NO EXISTE"
                print(f"  ↳ imagen: {f['imagen']}  [{marca}]")
                print(f"  ↳ alt:    {f['imagen_alt']}")
        print("=" * 66)
        print(f"\n{len(filas)} listas. SIMULACRO: no se publicó nada.")
        return 0

    if not _interruptor(args.destino):
        sys.exit(f"{args.destino.upper()}_ENABLED no está en 'true': "
                 f"el canal está apagado y no se publica nada.")

    conectar_cliente, publicar = CANALES[args.destino]
    try:
        cliente = conectar_cliente()
    except Exception as e:
        sys.exit(f"no se pudo conectar a {args.destino}: {e}")

    ok = fallos = 0
    for f in filas:
        try:
            url = publicar(cliente, f)
        except Exception as e:
            cola.marcar_fallido(cx, f["id"], e)
            print(f"  ❌ #{f['id']}: {e}")
            fallos += 1
            continue
        if cola.marcar_publicado(cx, f["id"], url):
            print(f"  ✅ #{f['id']}: {url}")
            ok += 1
        else:
            # Salió de verdad pero la cola no lo registró: hay que decirlo, o la
            # siguiente corrida lo publica otra vez.
            print(f"  ⚠️  #{f['id']}: PUBLICADO en {url} pero la cola no lo marcó")
            fallos += 1

    print(f"\n{ok} publicadas, {fallos} con fallo")
    cx.close()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
