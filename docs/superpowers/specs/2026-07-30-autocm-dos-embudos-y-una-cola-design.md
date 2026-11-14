<!-- SPDX-License-Identifier: LicenseRef-Propietario -->
<!-- Copyright (c) 2026 Juan Carlos Isaza -->

# autocm: dos embudos, tres contenidos y una cola

Diseño validado el 2026-07-30. Sustituye el enfoque de «un tubo a nueve
canales» por el que sigue. Todo lo que este documento afirma sobre el estado
actual está **medido** contra el repositorio y contra la red ese día, no citado
de memoria.

## 1. Diagnóstico

Lo que hay hoy, verificado:

- **No publica en ningún canal.** `verification_results.json` (2026-07-17)
  cierra con `"publishing": []` y `"ready_to_publish": false`. Todas las
  banderas `*_ENABLED` valen `false`; la única en `true` es `LINKEDIN_ENABLED`,
  y `LINKEDIN_ACCESS_TOKEN` está vacía. La nota que decía «LinkedIn es el único
  canal activo» describía una intención, no un estado.
- **Los nueve publicadores están escritos** (`main.py:558-741`). Añadir
  plataforma es credencial y bandera, no código.
- **Playwright no captura ninguna imagen.** `observe_and_read`
  (`main.py:477-501`) lanza Chromium, espera 18 s, hace scroll a un píxel fijo
  y extrae `document.body.innerText`. Los publicadores reciben solo `text`.
- **Hace falta hoy, y solo por el stack del portafolio.** El HTML crudo de
  `xiliux.com` da 177 caracteres de texto —dos de ellos errores de NiceGUI—
  porque NiceGUI renderiza en el cliente. En cambio `xiliux.com/blog` **es
  SSR**: 5 078 caracteres sin JS, y el sitemap lista 24 URLs.
- **La ficha miente.** `CLAUDE.md` describe capturas de 1920×1080 y publicación
  en 9 canales. Ni una cosa ni la otra. Se corrige en la misma pasada.

El error de fondo no es técnico: **trata canales con públicos, contenidos y
castigos distintos como si fueran el mismo destino.**

## 2. Dos embudos, porque son dos negocios con públicos disjuntos

**Embudo A — servicios de desarrollo.** El comprador es una empresa colombiana.
Está en LinkedIn y en el clúster de la Cámara. Lo que funciona ahí es el uno a
uno y la prueba de trabajo, no el volumen. La automatización aporta poco;
autocm aporta **redactando y encolando**.

**Embudo B — Quipu.** El público son desarrolladores de Rust, criptografía e
infosec, global. Lo que funciona es aparecer donde ellos leen, y eso se
consigue con artefactos técnicos. Aquí la automatización **sí compone**.

Un mismo texto no sirve a los dos. Por eso el contenido se tipifica.

## 3. Tres tipos de contenido

| Tipo | Qué es | Destinos |
|---|---|---|
| `NOTA` | ≤300 caracteres con enlace | Bluesky, Mastodon, LinkedIn |
| `ARTICULO` | markdown del blog, republicado con `canonical_url` | dev.to, Hashnode |
| `HITO` | release, versión, KAT, auditoría | This Week in Rust, r/rust, lobste.rs/HN |

`ARTICULO` es la pieza nueva y la que compone: `canonical_url` apuntando a
`xiliux.com` presta la autoridad del sitio grande sin penalización por
contenido duplicado. `HITO` **nunca** sale solo.

## 4. Una cola, y es lo que vuelve productivo LinkedIn hoy

`cola.sqlite` con una fila por publicación: destino, tipo, estado
(`borrador → aprobado → publicado`), cuerpo, enlace canónico, imagen, fecha.

- Canales **baratos** (Bluesky, Mastodon): consumen `borrador` directamente.
- Canales **sensibles** (LinkedIn, Reddit, HN, This Week in Rust): esperan el
  `aprobado` de Juan.

**El bloqueo de LinkedIn es de la API, no del canal.** La Community Management
API exige entidad legalmente registrada, página verificada, revisión de app en
dos niveles y un screencast; y hay permisos que no admiten solicitudes nuevas.
Xiliux no es persona jurídica, así que esa puerta puede no abrirse nunca.
Publicar a mano cuesta 30 segundos si el texto ya está escrito. La cola
convierte el bloqueo en fricción de medio minuto, y el día que llegue el token
la misma cola se publica sola sin cambiar nada más.

Decidido: en LinkedIn se publica **solo desde la página de Xiliux**, nunca
desde el perfil personal de Juan. El perfil es el del abogado, y amplificar
software desde ahí es la fusión de identidades que la regla evita, en la
dirección inversa.

## 5. Las plataformas, con el criterio explícito

«Altamente efectiva» = (a) el público contiene compradores o multiplicadores,
(b) no hay puerta de verificación de identidad, (c) el rastro es permanente y
compone, (d) el coste humano recurrente es bajo.

| Canal | Embudo | Puerta de entrada | Veredicto |
|---|---|---|---|
| LinkedIn (página) | A | API cerrada de facto | **Cola manual, desde ya** |
| dev.to (Forem v1) | B | `api-key` inmediata | **Sí — el que más compone** |
| Hashnode | B | token inmediato | Sí, la misma pieza |
| This Week in Rust | B | PR, o etiqueta en Bluesky/Mastodon | **Sí — máxima palanca por hito** |
| Mastodon (fosstodon / infosec.exchange) | B | token de la cuenta, sin revisión | Sí |
| Bluesky | B | app password | Sí, con el handle corregido |
| r/rust, r/crypto | B | karma y reglas de autopromoción | Cola, por hito |
| lobste.rs / HN | B | HN abierto; lobste.rs por invitación | Cola, una bala por producto |
| GitHub (topics, README, listas) | B | ninguna | Sí — es el escaparate real |
| X | — | 0,20 USD por post con enlace | **Descartado** |
| Telegram / Discord | — | token inválido / audiencia cero | Archivo, no promoción |
| Facebook | A | credencial válida | Apagado: público equivocado |
| Email (lista propia) | A+B | ninguna | Sí, más adelante: el activo más durable |

**This Week in Rust y Mastodon/Bluesky son el mismo movimiento**: la vía de
sugerencia del boletín es un PR o una mención en esas dos redes. Encender
Bluesky y Mastodon no es «estar en redes»; es tener por dónde llamar a la
puerta del canal de Rust.

**Antes de encender Bluesky**: el handle es `isazajuancarlos.bsky.social`, el
nombre legal de Juan. Pasarlo a `xiliux.com` con un TXT en `_atproto.xiliux.com`
es gratis, verifica el dominio y cierra la fusión de identidades.

## 6. Arquitectura

Cinco piezas, cada una con un propósito y un límite claro:

1. **`fuente`** — de dónde sale el contenido. Sitemap + blog SSR por HTTP. **Sin
   navegador.** Entra: URL del sitemap. Sale: lista de artículos con título,
   markdown/texto y URL canónica.
2. **`redactor`** — texto por tipo y por canal, con los límites de cada uno.
   Entra: artículo + tipo + canal. Sale: cuerpo listo. No inventa productos.
3. **`cola`** — el único estado del sistema. SQLite.
4. **`publicadores`** — uno por canal, sin lógica de negocio: toma de la cola lo
   que le toca y lo entrega. Falla ruidoso y deja la fila en `borrador`.
5. **`informe`** — qué se publicó, dónde y con qué enlace, para poder medirlo en
   Search Console y GA4 en vez de suponerlo.

## 7. Qué se borra

Directiva 1: si se añade un mecanismo para contener lo que creó otro, se quita
el primero.

- **Playwright** y las dos zonas con `scroll_y` en píxeles. El scroll a un píxel
  fijo es frágil por construcción: cualquier cambio de maquetación hace que la
  IA escriba sobre la sección equivocada sin que nada lo avise.
- **El publicador de X.** Cobra por publicación, y el enlace la encarece.
- **Los blurbs sobre «lo que caiga en y=2600».**
- **`TARGET_URL=https://www.xiliux.com`** → el canónico es sin `www` (hay 301).

## 8. Orden de ejecución

1. **Que publique algo.** Handle de Bluesky a `xiliux.com`; token de Mastodon;
   banderas de esos dos a `true`; re-verificar con `--verify`. Sin esto, todo lo
   demás es afinar una máquina desenchufada.
2. **Quitar el navegador.** `fuente` lee el sitemap y el blog SSR. Aquí muere la
   dependencia más difícil de portar, y el copy mejora: habla de un artículo con
   URL en vez de un recorte de píxeles.
3. **La cola y LinkedIn manual.** `cola.sqlite` + el listado de aprobación. Es
   el paso que produce valor en el canal que importa para el embudo A.
4. **`ARTICULO` a dev.to.** `POST https://dev.to/api/articles`, cabecera
   `api-key`, `accept: application/vnd.forem.api-v1+json`, cuerpo
   `{"article": {title, body_markdown, published, tags, canonical_url}}`.
   Después Hashnode con la misma pieza.
5. **`HITO` a This Week in Rust** en la próxima versión de Quipu.
6. **Port a Rust**, ya sin navegador: `megalodon` (Mastodon), `bsky-sdk`
   (Bluesky), `roux` (Reddit), `reqwest` (dev.to, Hashnode, LinkedIn, Discord),
   `axum` + SQLx para `lead_capture_api.py`, `minijinja` para las plantillas de
   correo. Primero `lead_capture_api.py`: son 407 líneas de Flask expuestas en
   el VPS y el estándar de Xiliux ya es axum.

El port va al final por una razón medida: no aporta ninguna función nueva. Lo
que compra es un binario único sin venv en el VPS —los 66 venvs que rompió
Python 3.14 ya costaron una sesión— y consistencia con el estándar.

## 9. Errores y pruebas

- **Fallar ruidosamente, nunca rellenar** (directiva 20). Si falta el token de un
  canal habilitado, la corrida falla con nombre y canal; no se «salta con
  gracia», que es lo que hoy esconde que no publica nada. El salto silencioso
  solo vale para canal `ENABLED=false`, que es una decisión explícita.
- **La cola es la prueba.** Un `borrador` que nadie consume es visible; un post
  perdido, no.
- **Simulación antes de dar por terminado** (directiva 8): 100+ ciclos con
  destino inyectado que falla, comprobando que la fila vuelve a `borrador` y no
  se publica dos veces; y que **discrimina** — un canal caído no arrastra a los
  demás.
- **Nada de contenido jurídico.** El prompt ya lo prohíbe
  (`main.py:519-521`); la prueba debe fijarlo, no el prompt solo.
