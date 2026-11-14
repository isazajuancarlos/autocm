# HITO — Quipu 0.10.0

Borrador preparado el 2026-08-03. **Nada de esto se ha enviado.** Publicar o
abrir el PR sale al mundo → «pregunta antes» (regla general de `~/.claude/CLAUDE.md`).

- **Versión:** 0.10.0, publicada en crates.io el **2026-07-28** (comprobado
  contra la API de crates.io el 2026-08-03: `max_version` 0.10.0, 129 descargas).
- **Repo:** https://github.com/isazajuancarlos/quipu (público, AGPL-3.0, 0 estrellas)
- **Fuente de los datos:** `/mnt/data/decod/CHANGELOG.md`, sección `## [0.10.0]`.

## Aviso de exactitud — leer antes de publicar

Lo que sigue afirma **solo** lo que la sección 0.10.0 del CHANGELOG respalda.
Dos cosas que NO pueden atribuirse a este release porque están en
`[Unreleased]` y saldrán en la siguiente versión:

- `#![forbid(unsafe_code)]` en los **seis** paquetes del workspace (se cerró el
  2026-08-02, después de publicar 0.10.0).
- El arreglo de `negacion::crear` (comparaba contraseñas por bytes y el KDF las
  compara tras NFKC).

Lo que 0.10.0 **sí** puede afirmar sobre `unsafe`: **`unsafe` de primera parte
93 → 0**, consecuencia de retirar la C ABI. Es una afirmación sobre el código
propio del repositorio, **no** sobre el árbol de dependencias. Decirlo de otra
forma sería prometer de más — exactamente el fallo que este mismo release
corrige en `quipu-cnsa`.

## Recomendación: anunciar 0.11.0, no 0.10.0

0.10.0 tiene seis días. Un anuncio de release rinde el día que sale y se enfría
en una o dos semanas. Y `[Unreleased]` ya acumula material más fuerte que buena
parte de 0.10.0: el `forbid` en los seis paquetes y un arreglo de salvaguarda
real. **Cortar 0.11.0 y anunciarla el mismo día vale más que estirar 0.10.0.**

Si se prefiere no esperar, el texto de abajo sirve tal cual para 0.10.0.
Publicar en crates.io exige visto bueno aparte, cada vez (directiva 10).

---

## 1. This Week in Rust — máxima palanca

Dos vías de entrada, no excluyentes:

- **PR** al repositorio del boletín (`rust-lang/this-week-in-rust`), añadiendo
  una línea en la sección de *Crate updates / Project updates* de la semana.
- **Mención** etiquetando a `@thisweekinrust` desde Mastodon o Bluesky. Ésta es,
  según el spec §5, la razón real por la que esas dos cuentas están encendidas.

Línea propuesta (formato del boletín — una frase, enlace, sin adjetivos):

> [Quipu 0.10.0](https://github.com/isazajuancarlos/quipu) — post-quantum hybrid
> encryption for data at rest in pure Rust; this release drops the C ABI and the
> Node/Go bindings, taking first-party `unsafe` from 93 to 0, and adds a
> primitive-agnostic core plus a CNSA 2.0 profile.

## 2. r/rust — canal SENSIBLE (exige `aprobado` en la cola)

Reddit castiga la autopromoción: regla 9:1, karma >100 y cuenta con más de un
mes. **No publicar sin haber participado antes.** El texto, si se decide:

**Título:**
> Quipu 0.10.0 — post-quantum encryption at rest in Rust: we deleted the C ABI
> and went from 93 first-party `unsafe` to 0

**Cuerpo:**
> Quipu is a Rust library for encrypting data at rest with a hybrid
> classical/post-quantum design: XChaCha20-Poly1305 and Argon2id, with ML-KEM-1024
> and ML-DSA-87 for key establishment and signatures.
>
> 0.10.0 is mostly a subtraction release, and that is the interesting part.
>
> We removed the C ABI, the Node binding, the Go binding and the Express
> integration. Nobody was using them — measured against the registries, not
> guessed: npm showed 486 downloads in four months and crates.io 307 in its whole
> history, which at that scale is mirrors and crawlers rather than people. What
> they did generate was cost: a parity matrix across five surfaces that was wrong
> in four cells, and the 93 `unsafe` blocks of the C ABI, which were the only
> place in the repository where a memory bug could live.
>
> The numbers: first-party `unsafe` 93 → 0. Version sites 13 → 4. Package
> registries 4 → 2. CI jobs 14 → 11. Python stays as the single binding, built
> from the same code with maturin and PyO3 as one abi3 wheel.
>
> Also in this release: `quipu-nucleo`, a primitive-agnostic core (container
> format, no algorithms baked in), and `quipu-cnsa`, a sibling profile aligned
> with CNSA 2.0 — aligned, explicitly **not** FIPS 140-3 validated, and the
> README says so.
>
> On the testing side: known-answer tests against external standard vectors,
> a dudect-based timing harness over signature verification, and an
> indistinguishability bench.
>
> AGPL-3.0. Repo: https://github.com/isazajuancarlos/quipu

## 3. lobste.rs / Hacker News

**lobste.rs es por invitación** — no hay cuenta, así que hoy no es una vía.
Para HN, «una bala por producto» (spec §5): no gastarla en un release menor.
Si se usa, el título va sin superlativos:

> Quipu 0.10.0 – post-quantum encryption at rest in Rust, minus 93 unsafe blocks

## 4. NOTA para Bluesky y Mastodon (≤300 caracteres)

Va a la cola como tipo `HITO`. Recordar la trampa de Bluesky: el enlace necesita
`TextBuilder` o sale como texto no pinchable (ya corregido en `publicar_cola.py`).

> Quipu 0.10.0 is out: post-quantum encryption at rest, pure Rust.
> We deleted the C ABI and the Node/Go bindings — first-party `unsafe` went
> from 93 to zero. Plus a primitive-agnostic core and a CNSA 2.0 profile.
>
> https://github.com/isazajuancarlos/quipu

(288 caracteres con el enlace.)

## Antes de enviar nada

El escaparate tiene que aguantar la visita. Comprobado el 2026-08-03: los
**topics de GitHub ya están puestos** (13, correctos) y la descripción del repo
está en inglés y es precisa. Lo que queda por revisar es que la primera pantalla
del README diga qué es, por qué, y traiga un ejemplo ejecutable — porque el
README es la página de aterrizaje real, no xiliux.com.
