# CLAUDE.md — Xiliux AutoCM

> **Configuración general: `~/.claude/CLAUDE.md`** — reglas que no se rompen,
> las directivas numeradas y las máquinas montadas. Se carga en toda sesión y
> **no se copia aquí**; este archivo lleva SOLO lo propio de AutoCM.
>
> **Esta instancia se arranca desde esta carpeta**: `cd /mnt/data/autocm && claude`.
> Desde el 2026-08-01 no se trabajan varios proyectos desde una sola sesión.
>
> Lo propio de aquí que antes vivía en el archivo general: AutoCM es el altavoz
> **de Xiliux** y **nunca publica sobre la práctica jurídica** — automatizaría
> la fusión de las dos identidades, que es justo lo que se está evitando.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Xiliux AutoCM** es el agente de marketing de contenidos de Xiliux: lee texto de
la web con un navegador sin cabeza, redacta con OpenAI GPT-4o y entrega a canales
sociales.

**Estado real, medido con `--verify` el 2026-08-02 a las 23:47 — no lo que la
ficha decía antes:**

- **Publica en DOS canales: mastodon y bluesky** (`"publishing": ["mastodon",
  "bluesky"]`, `ready_to_publish: true`). Hasta esa noche no publicaba en
  ninguno; se encendieron al llenar la cola. Los demás siguen apagados por
  decisión, no por avería: **Facebook y Discord verifican bien** y no publican
  solo por el interruptor. `LINKEDIN_ENABLED` está en `true` pero
  `LINKEDIN_ACCESS_TOKEN` está vacía (bloqueada por la verificación de identidad
  de LinkedIn), así que `will_publish` es `false`. **ACTUALIZADO 2026-10-22: el
  token del modo `person` YA se obtuvo y es válido (`--verify` ✅ «publica como la
  persona»); `will_publish=true`, y LinkedIn pasó a canal BARATO (publica
  automático por timer, sin aprobación). Lo de abajo es historia.**
- **La cola se vacía sola desde el 2026-08-02**, una nota al día por canal, con
  dos temporizadores de systemd de usuario (ver «La cadencia» más abajo). Hasta
  esa noche no la vaciaba nadie: el `schedule` de `main.py` dispara el camino
  viejo, no la cola.
- **Hay publicadores escritos para 9 canales** (Mastodon, X, Telegram, Bluesky,
  Discord, LinkedIn, Reddit, Facebook, correo), así que activar uno es credencial
  y bandera, no código.
- **NO captura pantallazos.** La ficha anterior decía que capturaba imágenes de
  1920×1080; `observe_and_read` solo extrae `document.body.innerText`, y los
  publicadores reciben únicamente texto. El navegador está ahí como extractor de
  texto, porque la portada es NiceGUI y su HTML crudo da 177 caracteres.

El rediseño acordado —dos embudos, tres tipos de contenido y una cola con visto
bueno para los canales que castigan la automatización— está en
`docs/superpowers/specs/2026-07-30-autocm-dos-embudos-y-una-cola-design.md`.
Desde el 2026-08-02 sus dos primeras piezas existen: **la cola** (`cola.py`) y
**dev.to** (`publicar_devto.py`). Ver «La cola» más abajo.

**Lo que se midió el 2026-08-02 sobre la difusión, y conviene no olvidar:** el
repositorio público de Quipu tuvo **17 visitas únicas en 14 días y cero
referrers**, con 2 738 clones que son su propio CI (100 corridas × 11 trabajos).
Las 438 descargas de crates.io son infraestructura —docs.rs, espejos,
indexadores—, no personas: los picos coinciden uno a uno con las 11 fechas de
publicación y el suelo sin versión nueva es de 1 a 5 al día. **No hay demanda
que capturar todavía; hay que generarla.** Cualquier plan que dé por hecho que
llega gente al repositorio parte de un dato falso.

## Development Commands

**No hay `python` en el PATH, solo `python3`**, y las dependencias viven en el
`.venv` de la carpeta. Los comandos de abajo se escriben `python` por costumbre;
lo que de verdad se ejecuta es `.venv/bin/python`.

```bash
# Entorno (el .venv se rompe cuando el sistema sube de versión de Python:
# sus enlaces quedan colgando y NINGÚN comando arranca. Se rehace, no se repara)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium

# Verify all account credentials (without publishing) -> verification_results.json
.venv/bin/python main.py --verify

# Run the main agent. OJO: verifica, PUBLICA una vez de inmediato (tras 60-900 s
# de espera al azar) y solo entonces se queda en el horario 09:15/13:30/19:45
.venv/bin/python main.py

# Run email capture API (Flask server on port 5000)
.venv/bin/python lead_capture_api.py

# Test email marketing module (prints subscriber stats)
.venv/bin/python email_marketing.py
```

**No hay pruebas automatizadas**, ni framework, ni CI: cada módulo se ejecuta
suelto y `--verify` es lo más parecido a un banco. Lo que se afirme de este
repositorio hay que medirlo corriéndolo.

For code style guidelines, see `AGENTS.md`.

## Core Architecture

The system follows an **Observe → Think → Publish** pattern in `main.py`:

1. **`observe_and_read(zone_config)`**: abre la URL con Playwright (Chromium sin
   cabeza, viewport 1920×1080), espera, hace scroll a un píxel fijo y se queda con
   `document.body.innerText` recortado a 2500 caracteres. **No guarda ninguna
   imagen.**
2. **`think(zone_config)`**: manda ese texto a OpenAI con el prompt de la zona y
   devuelve el copy con el enlace añadido después (límites exactos en «Content
   Generation»).
3. **`publish_*`**: un publicador por canal, cada uno recibe solo `text`.

`run_cycle` los encadena: si `observe_and_read` devuelve `False` **no se llama ni
a `think` ni a ningún publicador** —el ciclo se salta entero y solo queda la
traza en el log—. Es la única condición de aborto que hay.

### Los dos interruptores: `enabled` × `valid`

Publicar exige DOS llaves, y confundirlas es el error que ya se cometió una vez
(el informe decía «listas para publicar: Sí» de canales apagados):

- **`self.enabled[canal]`** (`main.py:91`) — la bandera `<CANAL>_ENABLED` del
  `.env`. Es la **fuente única**: `run_cycle` la consulta con índice directo
  (`self.enabled[nombre]`, `main.py:785`) antes de llamar a nadie.
- **`valid`** — las credenciales responden, lo comprueba `verify_accounts`.

`will_publish = enabled and valid`, y `ready_to_publish` es «hay al menos un
canal con las dos». Un canal con credenciales perfectas y el interruptor en
`false` **no publica y no cuenta**.

Ojo: solo `publish_mastodon` y `publish_reddit` comprueban su propio interruptor
por dentro. Los otros siete confían en la puerta de `run_cycle`, así que
llamarlos a mano publica de verdad aunque su bandera esté en `false`.

### Zone-Based Targeting

El diccionario `ZONES` define qué parte de la web se promociona:
- `SERVICES`: `scroll_y=2600`, `focus="dev"`
- `PROJECTS`: `scroll_y=1200`, `focus="products"`

Cada ciclo elige una zona al azar. Las dos apuntan a la MISMA URL (`TARGET_URL`) y
se diferencian solo por el desplazamiento en píxeles.

**`focus` no lo lee nadie.** Está en el diccionario (`main.py:38` y `:44`) y no
aparece en ninguna otra línea del repositorio: `think` compone el prompt con
`zone_config['name']` y el texto extraído, nada más. Cambiarlo no cambia el
resultado — quien quiera que la zona influya en el prompt tiene que cablearlo.

**Esto es frágil por construcción y hay que saberlo**: cualquier cambio de
maquetación hace que se lea la sección equivocada y la IA escriba sobre otra cosa,
sin que nada avise. El spec del rediseño lo sustituye por leer el blog, que es SSR
(5 078 caracteres sin JS) y tiene sitemap.

Ojo: la ficha anterior decía que `SERVICES` usaba `focus="lawyer_dev"`. El código
dice `"dev"`, y así debe seguir — **autocm publica en nombre de Xiliux y nunca
sobre la práctica jurídica**; un foco llamado «lawyer» invita exactamente a la
fusión de identidades que la regla prohíbe.

### Multi-Platform Publishing

All publishers skip gracefully if credentials are missing:
- **Mastodon**: Mastodon.py library
- **Twitter/X**: tweepy. Se inicializan DOS clientes, `twitter_client` (v2) y
  `twitter_api` (OAuth1, v1.1), pero solo el primero se usa: el segundo estaba
  para subir imágenes y ya no hay imágenes que subir
- **Telegram**: Direct API with inline keyboard
- **Bluesky**: atproto Client
- **Discord**: Webhook-based
- **LinkedIn**: Posts API (`POST /rest/posts`, éxito = HTTP 201). El autor lo
  fija **`LINKEDIN_AUTHOR_MODE`** (`main.py`, `_linkedin_author()`):
  - `organization` → `urn:li:organization:{LINKEDIN_ORG_ID}`, la página Xillux.
    Exige la **Community Management API**, que LinkedIn **denegó** (medido en la
    consola el 2026-09-12): scopes `w_organization_social r_organization_social
    rw_organization_admin`, `--verify` contra `/v2/organizationAcls`.
  - `person` → `urn:li:person:{LINKEDIN_PERSON_SUB}`, el **perfil de JC Isaza**.
    Scope `w_member_social` (producto "Share on LinkedIn") + `openid profile`
    (producto "Sign In with LinkedIn using OpenID Connect") para el `sub`;
    `--verify` contra `/v2/userinfo`. **Es la vía viva** mientras la API de
    página siga denegada — auto-aprobada, sin espera.
  - **No funde identidades pese al perfil personal**: el perfil de LinkedIn es
    **dual a propósito** (headline "Senior Rust Engineer … · Lawyer (Data
    Protection)"), y autocm sigue publicando **solo contenido de software,
    nunca jurídico**. La regla dura ("autocm nunca publica sobre la práctica
    jurídica") es sobre el CONTENIDO, y se respeta.
  - Exige la cabecera `LinkedIn-Version` (`LINKEDIN_VERSION`, hoy `202606`):
    LinkedIn retira cada versión a los ~12 meses y responde 426 cuando caduca.
    `get_linkedin_token.py` (sin versionar) es el ayudante de OAuth y pide los
    scopes del modo elegido; en `person` imprime también `LINKEDIN_PERSON_SUB`.
- **Reddit**: PRAW (disabled by default - requires manual participation first)
- **Facebook**: Graph API v18.0. Con imagen, `POST /me/photos` (`source`
  multipart + `message` de pie); sin imagen, `POST /me/feed`. Publica contra
  **`/me`, no contra un `FACEBOOK_PAGE_ID`**: con un token de PÁGINA el nodo
  `me` ES la página, así que el token es la única fuente de identidad. El
  `page_id` suelto era una segunda fuente que se desincronizó (el `.env` del VPS
  apuntaba a otra página y el POST fallaba con 400 el 2026-08-11); se quitó del
  publicador (directiva 32). Está en la COLA como canal **SENSIBLE** (ver abajo)
  y su publicador vive en `publicar_cola.py`, no solo en `main.py`. El
  `publish_facebook` de `main.py` (camino viejo, run_cycle) sigue siendo
  solo-texto.
- **Email**: SQLite subscriber management, sends on Mondays only

### La cola (`cola.py`) — el único estado del rediseño

`cola.sqlite`, una fila por publicación: destino, tipo (`NOTA`/`ARTICULO`/
`HITO`), estado, cuerpo, enlace, **imagen + su texto alternativo**, y a dónde
salió. **La regla que la justifica**:

- **BARATOS** (bluesky, mastodon, devto, hashnode, telegram, discord, **linkedin**,
  **x**) consumen `borrador` directamente.
- **SENSIBLES** (reddit, hackernews, lobsters, thisweekinrust, **facebook**,
  **instagram**, **threads**) solo ven lo `aprobado`. Los cuatro primeros
  porque castigan que publique una máquina; **facebook** porque es una página de
  MARCA con público amplio y su línea es de producto/caso, que se cura y se
  aprueba; **instagram** y **threads** porque se publican conduciendo la UI
  con Playwright (`publicar_ui.py`, ver abajo) y automatizar la UI es lo que su
  ToS prohíbe y detecta: el visto bueno es la barandilla antes de que una máquina
  pulse "publicar" en una cuenta de marca irreemplazable.
- *(linkedin fue SENSIBLE hasta el 2026-10-22; hoy BARATO. **x** fue SENSIBLE hasta
  el 2026-11-07; hoy BARATO por decisión de Juan —«siempre aprobado»—: publica el
  mismo texto del pipeline sin visto bueno. x SIGUE publicándose por UI, pero la
  aprobación no reducía el baneo —la máquina pulsa "publicar" igual—, solo
  pre-revisaba; la mitigación es la CADENCIA baja, que se mantiene.)*

**La imagen** (`imagen` + `imagen_alt`, desde el 2026-08-09): ruta a un archivo
local, guardada ABSOLUTA porque el temporizador publica desde otro directorio.
Una imagen **exige** `alt` —lo obliga un `CHECK` de la tabla y `encolar()`—:
sin él es inaccesible y Bluesky/Mastodon penalizan el adjunto mudo (directiva
20). Cada publicador la adjunta si la fila la trae y **degrada a solo-texto** si
no: `_publicar_bluesky` con `send_image` (manteniendo el enlace pinchable como
facet), `_publicar_mastodon` con `media_post`+`media_ids`, `_publicar_facebook`
con `/photos`. Migración idempotente en `conectar()` para la `cola.sqlite` que ya
existía.

**Generación de la imagen (desde 2026-09-15, `docs/IMAGENES.md`):** las tarjetas se generan con `tarjeta.py` (texto del post sobre un FONDO de marca de `fondos/`, con Pillow) porque la cuenta de Canva es Educación y su Autofill API exige Enterprise (el cliente Canva, `canva.py`, queda para ese día). `imagen_para_post.imagen_para(titulo, cuerpo)` elige el fondo por TEMA (cripto→quipu, productos→productos, resto→neutro) y devuelve `(png, alt)`; `llenar_cola.py --imagen` lo encola. Config en el `.env`: `IMAGEN_BACKEND`, `TARJETA_FONDO` (carpeta = rotación), `TARJETA_CAJA=170,210,1340,510`, `IMAGEN_DIR`. Desplegado al VPS el 2026-09-15; bluesky/mastodon rellenados con imagen. Pruebas: `prueba_tarjeta.py`, `prueba_canva.py`.

Esa decisión vive en **`reclamar()`, no en cada publicador**: si cada uno
eligiera qué estado le sirve, un publicador nuevo mal escrito bastaría para que
LinkedIn publicara sin que nadie lo aprobara.

```bash
.venv/bin/python llenar_cola.py --destino linkedin   # una NOTA por artículo
.venv/bin/python cola.py listar --destino linkedin
.venv/bin/python cola.py ver 7
.venv/bin/python cola.py aprobar 7
.venv/bin/python cola.py pendientes linkedin         # lo que toca pegar a mano
.venv/bin/python cola.py publicado 7 --url https://…
```

**ACTUALIZADO 2026-10-22 — LinkedIn ya NO se pega a mano.** El token `person` se
obtuvo (válido) y LinkedIn pasó de SENSIBLE a BARATO (`cola.py`): el timer
`autocm-cola@linkedin` (Mar/Jue/Sáb) publica los borradores **sin aprobación**,
con el mismo texto del pipeline (la redacción ya es adecuada; lo que evita el
bloqueo es la CADENCIA, no curar cada texto). El flujo `aprobar`/`pendientes` de
arriba ya **no** aplica a LinkedIn —queda para los demás sensibles
(reddit/facebook/…)—. *(Histórico, hasta esa fecha: el token estaba bloqueado y
LinkedIn era sensible, así que se pegaba a mano; el bloqueo era de la API, no del
canal.)*

`llenar_cola.py` **no usa IA a propósito**: el título y la `og:description` de
cada artículo ya los escribió una persona y dicen lo que el artículo dice.
Pasarlos por un modelo solo añadiría el riesgo de inventar un producto que no
existe, que es un fallo que este proyecto ya cometió.

Pruebas: `.venv/bin/python prueba_cola.py` — 28 comprobaciones, 120 encolados,
40 hilos peleando por publicar la misma fila (gana uno), camino de error
inyectado, alcance del borrado, y una prueba que **rompe la regla a propósito**
para confirmar que la batería discrimina.

### Los perfiles (`perfiles.py` + `imagenes_marca.py`)

Nombre, biografía, avatar y banner de las cuentas sociales. **La biografía no
menciona nada jurídico**: estas cuentas hablan por Xiliux y la práctica jurídica
va por separado.

```bash
.venv/bin/python imagenes_marca.py            # avatar y banner -> ./marca/
.venv/bin/python perfiles.py --simulacro
.venv/bin/python perfiles.py --aplicar
```

La imagen canónica es **`/mnt/data/documentos/gato_xiliux.png`** (fuera del
repositorio; se puede cambiar con `XILIUX_LOGO`). No se usa la del sitio ni tal
cual: pesa 3,8 MB —Bluesky corta los blobs en ~1 MB— y la figura ocupa el 63 %
del ancho descentrada, así que a 96 px no se distingue. Se reencuadra sobre la
figura, que se localiza **por color** (R−B>30) porque el fondo es un degradado y
tiene una sombra y un destello de esquina que una resta contra el fondo confunde
con la figura.

En Bluesky el perfil es **un solo registro** con rkey `self` que se escribe
entero: avatar y banner van en la misma llamada o la segunda borra lo de la
primera.

### El productor de capturas (`capturas.py`)

Toma pantallazos de las demos en producción para que las publicaciones lleven la
imagen de «míralo funcionando» en vez de texto pelado. Entra con las credenciales
DEMO —públicas, publicadas en cada pantalla de acceso—, recorre los enlaces del
MENÚ que aparecen tras entrar y captura cada sección a página completa en
`marca/capturas/<app>/`. Así salen los maestros y las características especiales
sin enumerar rutas a mano (directiva 19). **No publica ni escribe en las demos**:
solo navega y hace screenshot.

```bash
.venv/bin/python capturas.py                 # las cinco demos
.venv/bin/python capturas.py --app medico    # una
```

Credenciales demo (públicas): informes `admin@co.co/admin`, inventario
`demo/inventario2026`, medico `demo@xiliux.com/demo-medico-2026`, xiliux sin
login. **chasqui no tiene credenciales demo sembradas** en el despliegue (su
login no las publica), así que queda solo la portada — se dice, no se adivina.

**Tres trampas medidas el 2026-08-09, y ninguna daba error —salían capturas
idénticas o vacías, un falso verde (directiva 30)—:**

- **La cookie de sesión es `SameSite=Strict`, y cada app la conserva con una
  navegación distinta y OPUESTA**: medico mantiene la sesión con navegación de
  cliente (`location.href`) y la pierde con el `goto` de Playwright; inventario al
  revés. No se adivina: `_elegir_metodo` sondea con la primera ruta cuál conserva
  la sesión y usa esa. Sin esto, medico daba **21 capturas idénticas** (todas la
  pantalla de login, 1 md5 de 21).
- **«Estoy en login» se detecta por el campo de CONTRASEÑA, no por la URL**:
  inventario tiene su login en `/`, que con sesión redirige a `/articulos`, y
  `"/".strip("/")` es `""`, que hace `endswith` siempre verdadero.
- **Hay que esperar a que htmx asiente** (`_asentar`): `networkidle` no basta
  —los paneles piden sus datos con `hx-get` tras pintarse—, así que la primera
  foto sale con «Cargando…». Se espera a que ese texto desaparezca y se cierran
  los avisos de error que arrastra la pantalla anterior.

**Lo que NO cubre, dicho para no confundir amplitud con datos**: la demo de
medico está **vacía** (se reinicia sola), así que sus listados salen sin datos;
inventario sí tiene datos sembrados. Y `/estadisticas` de medico no carga su
resumen en la demo. Las capturas prueban estructura y amplitud; para «con datos»
hay que sembrar la demo antes, que toca el VPS y se anuncia.

### El publicador de la cola (`publicar_cola.py`)

Consume la cola y entrega en los canales que sabe publicar por API —`bluesky`,
`mastodon`, `facebook`, `linkedin`, **`discord`** y **`nostr`** (`CANALES`)—. No
comprueba estados: eso lo decide `reclamar()`, así que un canal SENSIBLE como
facebook solo saca lo aprobado. Respeta `<CANAL>_ENABLED` y **se niega a publicar
con el canal apagado** en vez de vaciar la cola contra nadie. Adjunta la imagen de
la fila si la trae; ver «La imagen» arriba.

**Discord y Nostr (desde 2026-11-07) son canales PROPIOS** (webhook propio / clave
propia): sin riesgo de baneo, por eso BARATOS (publican borradores directo). Discord
va por webhook (`DISCORD_WEBHOOK_URL`); **Nostr** firma una nota kind-1 (schnorr) y la
difunde a `NOSTR_RELAYS` con la clave `NOSTR_NSEC` (pynostr). **Nostr OPERATIVO desde
2026-11-07** (`NOSTR_NSEC`/`NOSTR_RELAYS` en el `.env` del VPS, timer activo, diario);
primer post verificado VIVO en relay.damus.io (npub1we63yr…s2nz24). Publica solo-texto
(adjuntar imagen exige subirla antes a un host NIP-96/Blossom). **Fiabilidad a vigilar**:
`run_sync` no garantiza entrega a TODOS los relays por corrida (el primer post llegó a
damus pero no a nos.lol/snort); mejorable capturando los OK de cada relay y esperándolos.

**Threads sigue BLOQUEADO (2026-11-07):** su login deriva de Instagram por un handoff
("Continuar con Instagram") que pega con el checkpoint de Meta —medido: desde el perfil
de Instagram ya logueado, threads.com muestra muro, no compositor; la cookie de
Instagram NO transfiere (dominio distinto, Threads necesita su propio `sessionid`)—. No
es nuestro código; el timer `autocm-ui@threads` queda `disabled` hasta que Meta deje
completar el handoff.

```bash
.venv/bin/python publicar_cola.py --destino bluesky --simulacro
.venv/bin/python publicar_cola.py --destino bluesky --limite 1
```

**La trampa de Bluesky, medida el 2026-08-02**: `send_post` solo construye
*facets* si recibe un `TextBuilder` (`if isinstance(text, TextBuilder)` en el
SDK). Pasándole una cadena manda `facets=None` y **la URL sale como texto que no
se puede pinchar** — se ve bien en el log y convierte cero. Corregido aquí y en
`publish_bluesky` de `main.py`. Mastodon no lo necesita: enlaza por su cuenta.

`main_link` es `https://xiliux.com` **sin `www`**: `www` devuelve 301, así que
publicarlo gasta un salto en cada enlace y reparte la señal entre dos
direcciones.

### El publicador por UI (`publicar_ui.py`) — Instagram, Threads y X

La pieza gemela de `publicar_cola.py`: entrega conduciendo la **UI web logueada**
con Playwright, no por API, porque estas redes no tienen API orgánica asequible
(la de X es de pago, ~US$100+/mes). Consume la **misma cola** y respeta la misma
invariante (`reclamar()` de `cola.py`). Instagram y Threads son **SENSIBLES** (solo
lo `aprobado`); **X es BARATO desde 2026-11-07** (publica borradores directo, ver
«La cola») pese a publicarse también por UI. **X** (añadido 2026-11-07) reusa la bandera
canónica `TWITTER_ENABLED` —no inventa `X_ENABLED`— vía `_ENV_INTERRUPTOR`, para
no tener dos interruptores sobre la misma cuenta (directiva 32); la red se llama
`x` y acepta solo-texto (imagen opcional), como Threads.
Reusa el Playwright que ya está en `requirements.txt` (el mismo de
`capturas.py`/`main.py`), no añade stack.

**HILOS en X (desde 2026-11-11):** si el `cuerpo` de la fila trae varios tweets
separados por una línea de guiones (`---`), `publicar_x` los compone como un HILO
nativo con el botón `addButton` del compositor (`tweetTextarea_0..n`) y publica todo
con un solo `tweetButton`. Un cuerpo sin `---` se publica como un post suelto, igual
que antes (`_hilo()` devuelve una lista de 1). El enlace de la fila se añade al
ÚLTIMO tweet salvo que ya esté embebido. Cada tweet se valida ≤280 y falla ruidoso
si se pasa (D20). **Composición VERIFICADA por simulacro contra X vivo** (2026-11-11,
hilo de guecha de 5 tweets, `addButton` + 5 editores, sin excepción); el `Publicar
todo` reusa el mismo `tweetButton` ya verificado del post suelto.

Nació el 2026-11-06 adoptando el **catálogo de selectores+secuencia** de
`MultiPost-Extension` (Apache-2.0; atribución en `NOTICE`). **No se portó la
arquitectura** de la extensión (service worker MV3, `chrome.scripting`): eso no
encaja en autocm (headless, autónomo en el VPS, sin humano que haga clic). Se
portó solo lo valioso —los selectores del DOM y el orden de pasos de
`instagram.ts` y `threads.ts`— a Playwright Python.

**Dos diferencias deliberadas con MultiPost, que son el porqué de reescribirlo:**
- **Confirma la publicación.** MultiPost pulsa "publicar" y termina; si un selector
  no casa, imprime a la consola y sigue. Aquí cada envío se CONFIRMA (el
  compositor se cierra) y, si no, se levanta excepción → `marcar_fallido` con el
  motivo (directiva 30: un clic sin efecto no es una publicación).
- **Instagram EXIGE imagen** (no hay post de solo-texto): la fila sin imagen se
  rechaza ruidosamente antes de abrir el navegador. Threads acepta solo-texto.

```bash
# UNA vez por red y máquina: iniciar sesión a mano (abre navegador, lo hace Juan).
.venv/bin/python publicar_ui.py --login instagram
# Ensayo que rellena el formulario y NO publica — así se VERIFICAN los selectores
# contra el DOM vivo (hasta aquí son selectores portados, SIN verificar):
.venv/bin/python publicar_ui.py --destino threads --simulacro --headful
# Publicar de verdad (consume la cola; respeta <RED>_ENABLED):
.venv/bin/python publicar_ui.py --destino threads --limite 1
```

**ESTADO (directiva 28/30): es ANDAMIAJE verificado en lo que NO toca el DOM, no
un camino probado de extremo a extremo.** Verde: la cola, el cableado del CLI y
el guardián de canal-apagado. **Instagram y Threads están VERIFICADOS de punta a
punta** (2026-11-06, publicaron de verdad desde el VPS — ver los docstrings).
**X: VERIFICADO de punta a punta (2026-11-07)** — publicó de verdad desde el VPS
(xvfb, IP de Montréal) la nota #484, confirmada VISIBLE en la cuenta de marca
**@xiliuxDev**. Falta ejercitar solo la subida de imagen (el primer envío fue
solo-texto). **El login de X NO se hace con `--login`**: X bloquea el login dentro
del Chromium automatizado de Playwright (lo detecta como bot; Firefox normal pasa).
La sesión se TRASPLANTA del Firefox real (navegador seguro de chuspa) con
`--importar-sesion x` — ver «Trasplante de sesión» abajo. **Desplegado al VPS**:
código + perfil logueado (`/home/debian/.autocm/perfiles-ui/x`) + timer
`autocm-ui@x` activo + `TWITTER_ENABLED=true`. Cloudflare no estorbó desde Montréal.

**Secreto:** la sesión vive en un perfil persistente de Playwright por red, en
`PERFILES_UI_DIR` (por defecto `~/.autocm/perfiles-ui`, FUERA del repo). Una
cookie de sesión es acceso total a la cuenta saltándose el 2FA: jamás se
versiona (`.gitignore`).

**Trasplante de sesión (`--importar-sesion <red>`, desde 2026-11-07).** X y Meta
**bloquean el login dentro del Chromium automatizado** de Playwright (lo detectan
como bot: `navigator.webdriver`, `--enable-automation`…); el Firefox normal y el
celular pasan sin problema. En vez de pelear con la detección (frágil, D1), el
login se hace en el navegador que SÍ funciona —el **Firefox del navegador seguro
de chuspa**, `/mnt/data/navegador-seguro/clear/perfil` (configurable con
`FIREFOX_PERFIL`)— y se **trasplanta la cookie de sesión** a la perfil de
Playwright leyendo su `cookies.sqlite` (`immutable=1`, read-only, no copia el
secreto ni imprime valores). Esto **sirve para las tres redes UI** y rescata el
checkpoint de Meta en Threads/Instagram por la misma vía.

```bash
# 1) Juan inicia sesión en X en el Firefox de chuspa (una vez).
# 2) Trasplantar la sesión al perfil de Playwright (verifica que quedó logueado):
.venv/bin/python publicar_ui.py --importar-sesion x
# 3) (opcional) simulacro para ver el compositor sin publicar:
.venv/bin/python publicar_ui.py --destino x --simulacro --headful
```

**Trampa medida (D23):** el filtro de dominio NO puede ser `host LIKE '%x.com'` —
casa `okx.com`, `xiliux.com`, `hanerix.com` y mete cookies ajenas—. Es
exacto-o-subdominio (`host = 'x.com' OR host LIKE '%.x.com'`), en `COOKIES_DOMINIO`.
Las cookies `cf_clearance`/`__cf_bm` (Cloudflare, atadas a IP+UA) viajan en el
lote; no rompen el login, pero si al desplegar al VPS (otra IP) hay fricción de
Cloudflare, se excluyen —son efímeras y se regeneran—.

### La cadencia (`systemd/`)

Un canal encendido con la cola llena no publica nada si nadie llama al
publicador. Los llaman temporizadores systemd:
`autocm-cola@bluesky` (10:20), `autocm-devto` (13:15), `autocm-cola@mastodon`
(17:40), **`autocm-cola@facebook`** (12:30), **`autocm-cola@linkedin`** (Mar/Jue/Sáb),
y —desde el 2026-11-07— **`autocm-cola@discord`** (15:05, diario) y
**`autocm-cola@nostr`** (20:15, diario — ACTIVO desde 2026-11-07) y
**`autocm-cola@telegram`** (09:40, diario — ACTIVO desde 2026-11-07, bot
@XiliuxBot de BotFather al canal @xiliuxDev; `TELEGRAM_CHAT_ID` es el id `-100…`
REAL del canal, obtenido por getUpdates —el que se teclea a ojo suele estar mal—).
Los de la cola salen de la plantilla `autocm-cola@.service`, con el
destino tras la arroba; dev.to va aparte porque no consume la cola.

**Los canales por UI tienen su propia plantilla** (desde el 2026-11-06):
`autocm-ui@.service` corre `publicar_ui.py` con `xvfb-run` (ver «El publicador
por UI»), y sus timers van a **baja cadencia y en días/horas DISTINTOS entre sí**
para no publicar en lockstep ni parecer bot: **`autocm-ui@threads`** Lun/Mié/Vie
11:10 (3/sem), **`autocm-ui@instagram`** Mar/Sáb 16:40 (2/sem) y
**`autocm-ui@x`** Jue/Dom 09:25 (2/sem) —días PROPIOS, ninguna de las tres
publica el mismo día—, todos `America/Bogota` + `RandomizedDelaySec=1800` +
`--limite 1`. Instagram y Threads son SENSIBLES: su timer solo saca lo **aprobado**
(con la cola en borrador corre y sale limpio sin publicar). **X es BARATO** (siempre
aprobado, 2026-11-07): su timer saca borradores directo, 1 por corrida (jue/dom).

> **DESDE EL 2026-08-09 AUTOCM CORRE EN EL VPS, no en `hope`.** El equipo de Juan
> se apaga de noche (10pm–8am) y en tormentas, así que los timers locales
> publicaban a saltos y en ráfaga al volver —la huella de bot que esto existe
> para evitar—. En el VPS (`/home/debian/autocm`, siempre encendido) publican a
> la hora exacta. Cambia dónde se opera, no el diseño:
>
> - **Los timers son de SISTEMA** (`/etc/systemd/system/`, no `--user`), con
>   `User=debian` y **`OnCalendar=… America/Bogota`** —el VPS está en UTC, sin la
>   zona publicaría 5 h antes—. Se generaron de los `systemd/*.timer`/`.service`
>   del repo con un `sed` (rutas `/mnt/data`→`/home/debian`, `+User=debian`,
>   `+America/Bogota`); el procedimiento exacto está abajo.
> - **La cola del VPS (`/home/debian/autocm/cola.sqlite`) es la fuente de
>   verdad.** La de `hope` quedó obsoleta y sus timers, apagados
>   (`systemctl --user disable`). No correr `publicar_cola.py` en local: publicaría
>   de una cola vieja.
> - **Operar es por `ssh`**: `sudo systemctl {start,list-timers} autocm-*`,
>   `journalctl -u autocm-cola@* -o cat`. El `.venv` y el `chromium` de Playwright
>   viven en el VPS; `capturas.py` corre allá contra las demos (mismo servidor).
> - **Añadir contenido**: se hace en el VPS (o se sube), porque la cola vive
>   allá. Migrar código nuevo: repetir el `tar`-over-ssh + el `sed` de timers.
> - **El `.env` del VPS es suyo** (permisos 600); comparte los tokens con el
>   local pero es OTRO archivo. No se sobrescribe con el local.

**Facebook no va a diario: `OnCalendar=Mon,Wed,Fri,Sun` (cada dos días,
4/semana).** Es una página de MARCA nueva y sin seguidores; su algoritmo diluye
el alcance de quien publica de más con poco engagement, y el riesgo no es el
baneo por frecuencia —1/día no banea en ningún canal— sino parecer un bot y
quemar el inventario de contenido. La cadencia por canal, no uniforme: fediverse
(bluesky/mastodon/devto) toleran 1/día; Facebook cada dos días; LinkedIn 2–3 por
semana AUTOMÁTICO (barato desde 2026-10-22, timer Mar/Jue/Sáb, sin aprobación);
Reddit no por cadencia sino por la regla 9:1.

**Facebook es SENSIBLE, así que el timer solo saca lo APROBADO** (`reclamar()`).
Con la cola en borrador, el timer corre y sale limpio —«nada pendiente»— sin
publicar: no hace ruido esperando el visto bueno. Para que empiece a publicar
hacen falta **dos gestos que son de Juan**, por diseño: (1) `FACEBOOK_ENABLED=true`
en el `.env` —encender es publicar al mundo—, y (2) `cola.py aprobar <id>` de las
notas que quiera. Sin (1) el publicador se niega con el canal apagado; sin (2) no
hay nada que sacar. La primera tanda (4 notas de producto con captura) quedó
encolada el 2026-08-09.

**Cómo se desplegó al VPS (reproducible), 2026-08-09:**

```bash
# 1) código (sin .env/.venv/marca/git), por tar-over-ssh (el VPS no tiene rsync)
tar czf - --exclude-from=EXCLUDES . | ssh debian@192.99.42.108 \
    'mkdir -p /home/debian/autocm && tar xzf - -C /home/debian/autocm'
scp .env debian@192.99.42.108:/home/debian/autocm/.env   # y chmod 600
# 2) entorno en el VPS
ssh debian@192.99.42.108 'cd /home/debian/autocm && python3 -m venv .venv \
    && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install chromium'
# 3) timers de SISTEMA con rutas del VPS, User=debian y zona Colombia
#    (sed sobre systemd/*.service y *.timer → /etc/systemd/system/, ver arriba)
ssh debian@192.99.42.108 'sudo systemctl enable --now \
    autocm-cola@bluesky.timer autocm-cola@mastodon.timer \
    autocm-cola@facebook.timer autocm-devto.timer'
```

**Operación en el VPS (por `ssh`):**

```bash
ssh debian@192.99.42.108
systemctl list-timers 'autocm-*'                  # cuándo toca la próxima
sudo systemctl start autocm-cola@bluesky.service  # publicar una ya, a mano
journalctl -u 'autocm-cola@*' -o cat -n 50        # qué salió y con qué URL
sudo systemctl disable --now autocm-cola@bluesky.timer     # parar un canal
```

Las tres decisiones que llevan dentro:

- **`--limite 1`, no la cola entera.** Vaciar 16 notas de golpe desde una cuenta
  recién creada es spam; una al día agota la remesa del blog en dos semanas y
  media, que es justo lo que tarda en haber artículos nuevos.
- **Horas distintas y `RandomizedDelaySec=1800`.** Las dos cuentas publican lo
  mismo: hacerlo en el mismo minuto exacto todos los días las delata como un
  solo automatismo.
- **`Persistent=true`.** `Linger` está en `no` para este usuario, así que los
  temporizadores solo corren con la sesión abierta; con esto la corrida perdida
  se recupera al volver, en vez de saltarse el día en silencio. Si algún día se
  quiere publicar con la sesión cerrada: `sudo loginctl enable-linger juan`.

### dev.to (`publicar_devto.py`)

Republica el blog con `canonical_url` a xiliux.com: presta la audiencia de
dev.to sin que la copia compita con el original en Google. `--preparar` escribe
los markdown en `borradores_devto/` y no toca la red; `--publicar` necesita
`DEV_TO_API_KEY` y **falla si no está**, en vez de caer al modo local.

El ritmo va en dos tiempos: se suben los 17 **como borradores** de una vez
(`--publicar --borrador`, idempotente contra los `canonical_url` que ya existen
en la cuenta) y luego se sueltan de uno en uno. `--soltar SLUG` suelta el que se
diga; **`--soltar-siguiente` suelta el de `id` más bajo** —el primero que se
subió— y existe porque un temporizador no tiene de dónde sacar un slug. Con la
lista vacía devuelve `None` y sale en verde: quedarse sin borradores es un
estado legítimo, y si reventara, el temporizador saldría en rojo a diario a
partir del último artículo hasta que nadie mirara el journal.

Ojo con el idioma: el blog es 100 % español y el público de Quipu (Rust, cripto,
infosec) es global. Los 12 artículos de Python/IA/trading funcionan en español;
los 5 de criptografía piden versión en inglés.

### Email Marketing System

Three modules handle email:
- `email_marketing.py`: `EmailMarketingAgent` class - SQLite subscriber management, SMTP sending, statistics
- `lead_capture_api.py`: Flask API for web form subscriptions (`/api/subscribe`, `/api/unsubscribe`, `/api/stats`, `/api/bulk_import`)
- `email_templates.py`: Responsive HTML templates

**Database** (`subscribers.db`): `contacts` (subscribers), `campaigns` (sent history), `interactions` (event tracking)

## Modifying the Agent

### Adding a New Social Platform

1. Add credentials to `.env` (y a `.env.example`) and load in `__init__`
2. Add client initialization with try/except in the `XiliuxAgent.__init__` method
3. **Declarar el interruptor en `self.enabled`** con su valor por defecto. No es
   opcional: `run_cycle` hace `self.enabled[nombre]` con índice directo, así que
   un canal en la lista `canales` sin bandera lanza `KeyError` y **mata el ciclo
   entero**, no solo ese canal.
4. Create `publish_[platform](self, text)` method following existing pattern
5. Añadirlo a la lista `canales` de `run_cycle`
6. Añadir su bloque a `verify_accounts` — lo que no verifica sale con
   `enabled=False` por el `.get(nombre, False)` del resumen y nunca aparece en
   `publishing`

### Changing Publishing Schedule

Horario actual, al final de `main.py`: 09:15, 13:30 y 19:45 a diario, y cada
`job()` duerme entre 60 y 900 s al azar antes de arrancar.

```python
schedule.every().day.at("HH:MM").do(job)
```

**`python main.py` publica de inmediato**: tras la verificación inicial llama a
`job()` una vez antes de entrar en el bucle. Para mirar sin publicar,
`--verify`.

Cada `job()` **construye un `XiliuxAgent` nuevo**, así que `cycle_count` vuelve
a 1 en cada corrida y no sirve para cadencias («cada N ciclos»). Lo periódico se
decide por fecha: el correo mira `datetime.now().weekday() == 0`.

### Adding New Zones

Add to `ZONES` dict:
- `name`: descripción; **es lo único de la zona que llega al prompt**
- `url`: URL objetivo
- `scroll_y`: desplazamiento en píxeles
- `focus`: campo inerte, no lo lee nadie (ver «Zone-Based Targeting»)

### Adjusting AI Behavior

Edit `think` method:
- `system_prompt`: Tone, style, constraints
- `model`: Currently "gpt-4o"
- `temperature`: 0.7 (0.0-1.0)

### Email Configuration

- Change sending frequency: Edit weekday check in `publish_email` (`if datetime.now().weekday() == 0:` for Mondays only)
- Test mode: Set `preview_mode=True` in `publish_email` to send only to PREVIEW_EMAIL
- Add subscribers programmatically:
  ```python
  from email_marketing import EmailMarketingAgent
  agent = EmailMarketingAgent()
  agent.add_subscriber("user@example.com", "Name", fuente="manual")
  agent.bulk_add_subscribers([("email1", "Name1"), ("email2", "Name2")], fuente="import")
  ```

## Runtime Files

The following files are created at runtime (not in version control):
- `autocm.log`: Runtime logs
- `subscribers.db`: SQLite subscriber database
- `verification_results.json`: lo escribe `--verify` (ignorado por git)

No existe ningún `promo_dynamic.png`: es el fósil del pantallazo que el agente
nunca tomó. Si vuelve a aparecer citado en algún documento, sobra.

## Reddit Integration

Reddit is **disabled by default** (`REDDIT_ENABLED=false`) due to strict anti-spam rules:
- 9:1 rule: 9 contributions for every 1 promotional post
- Accounts need karma (>100) and age (>1 month)
- Read `REDDIT_SETUP.md` and `REDDIT_MEJORES_PRACTICAS.md` before enabling

## Content Generation

- **Límite pedido**: el prompt dice «máximo 230 caracteres», y es una
  instrucción al modelo, no una garantía.
- **Límite impuesto**: el recorte duro es `280 - len(link_suffix) - 5` ≈ **249**
  caracteres, y solo entonces se pega `\n\n🔗 https://www.xiliux.com`. O sea:
  entre 230 y 249 el modelo se pasa y nadie lo corta. Si algún canal exige 280
  de verdad, el número que hay que mirar es este, no el del prompt.
- **Fallback**: `backup_copies` si falta o falla OpenAI (`think` nunca propaga
  la excepción).
- **Link handling**: el enlace se añade DESPUÉS de generar; el prompt le prohíbe
  al modelo ponerlo.

## Account Verification

Run `.venv/bin/python main.py --verify` to check all platform credentials without publishing. Results are saved to `verification_results.json`.

The agent automatically verifies accounts at startup and can skip invalid platforms during publishing via `run_cycle(verify_first=True, skip_invalid=True)`.

## Fault Tolerance

- All API clients initialized with try/except (missing credentials = warning, not crash)
- Cada publicador se traga sus propios fallos: uno roto no detiene a los demás,
  y **nada le cuenta a `run_cycle` que falló** — el resultado solo vive en el log
- Si falla la lectura de la web, el ciclo se salta entero (no se llama a OpenAI
  ni a ningún canal)
- `observe_and_read` espera `networkidle` + 15 s fijos + 3 s tras el scroll: unos
  **18 s de reloj por ciclo**, pagados para que NiceGUI termine de renderizar
- Account verification before publishing prevents wasted API calls

## Environment Variables

Copy `.env.example` to `.env` and configure. Required credentials vary by platform - unconfigured platforms are simply skipped. Key variables:
- `<CANAL>_ENABLED`: el interruptor de cada canal. Por defecto en el código:
  `true` para mastodon, telegram, discord, linkedin y email; `false` para
  twitter, bluesky, facebook y reddit. Los cuatro apagados lo están por decisión
  de identidad o de castigo de plataforma, no por falta de credenciales — el
  porqué está comentado en `main.py:77-101` y en `.env.example`.
- `OPENAI_API_KEY`: Required for AI-generated copy (falls back to `backup_copies` if missing)
- `SMTP_*` y `PREVIEW_EMAIL`: Required for email marketing
- `TARGET_URL`: la web que se lee (por defecto `https://www.xiliux.com`)
- `LINKEDIN_VERSION`: cabecera de versión de la API; caduca (ver LinkedIn arriba)
