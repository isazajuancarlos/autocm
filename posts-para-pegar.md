# Posts listos para pegar a mano — extraídos de la cola de autocm (2026-08-28)

> Contenido YA redactado y en la cola (estado borrador/aprobado), atascado por credencial.
> LinkedIn: pegar 1-2 al día (el token de la API está bloqueado; pegar a mano cuesta ~30s).
> Facebook: 3 aprobados. Todo es de XILIUX (software) — no cruza la identidad jurídica.

---

## LinkedIn — servicio de desarrollo / autoridad técnica

### 1. [id 1 · borrador]

Sellar un archivo para que nadie pueda discutir que no lo tocaste

Un hash único obliga a exhibir todo el conjunto para probar un solo archivo. Un árbol de Merkle, no. Cómo funciona Tunjo: raíz de integridad, firma triple post-cuántica y un verificador que puede ejecutar cualquiera.

https://xiliux.com/blog/sellar-evidencia-digital-firma-post-cuantica

---

### 2. [id 2 · borrador]

Te roban la base de datos y no pueden crackear ni una contraseña

Argon2 encarece cada intento, pero el atacante que se lleva tu tabla de usuarios tiene tiempo infinito y GPUs. Un OPRF cambia el juego: el hash depende de una clave que no viaja con la base de datos. Cómo funciona, qué cuesta y qué se rompe.

https://xiliux.com/blog/te-roban-la-base-de-datos-y-no-crackean-ni-una-contrasena

---

### 3. [id 3 · borrador]

Todo el mundo escribe qué reportar. Nadie escribe cómo no perder ninguno

Los incumplimientos rara vez vienen de desconocer la obligación, sino de rastrear treinta vencimientos en una hoja de cálculo. Por qué el Excel deja de servir y qué significa gestionar por reglas en vez de recordatorios.

https://xiliux.com/blog/como-no-perder-un-reporte-obligaciones-recurrentes

---

### 4. [id 4 · borrador]

El redondeo que hace que tu bot arriesgue 10 veces lo que crees

Dimensionar una posición parece una división, pero hacerla caber en los mínimos del exchange es donde se pierde dinero. El patrón max(1, int(...)) y cómo evitarlo con Decimal y redondeo hacia abajo.

https://xiliux.com/blog/dimensionar-posicion-sin-pasarse-del-riesgo

---

### 5. [id 5 · borrador]

Por qué tu bot recibe 403 de Cloudflare (y cómo endurecer un cliente ccxt)

Muchos exchanges ponen Cloudflare delante de su API y, a ratos, challenguean con 403 a peticiones legítimas de tu propia cuenta. Cómo mitigarlo sin evadir nada: hardening de cabeceras y retry selectivo con backoff.

https://xiliux.com/blog/por-que-tu-bot-recibe-403-de-cloudflare-ccxt

---

### 6. [id 6 · borrador]

Dos formas en que un backtest te miente (y cómo evitarlas)

Casi todo el edge que se mide en un backtest es una de dos ilusiones: el modelo vio el futuro, o la variante ganadora ganó por ruido. Dos primitivas en Python puro para descartar ambas antes de arriesgar nada.

https://xiliux.com/blog/dos-formas-en-que-un-backtest-te-miente

---

### 7. [id 7 · borrador]

Cuando tu clasificador parpadea: histéresis para señales que oscilan

Una señal que cerca del umbral hace OK, CAÍDO, OK, CAÍDO dispara alertas o failovers en cada tembleque. La solución es vieja y elegante: no cambiar de estado hasta que el nuevo se sostenga.

https://xiliux.com/blog/anti-flapping-histeresis-clasificador-ruidoso

---

### 8. [id 8 · borrador]

Notificar a varios canales sin que un fallo tumbe al resto

Mandar lo mismo a Slack, Discord, un webhook y un email parece un for de tres líneas. Lo es, hasta que el primer canal lanza una excepción y los demás se quedan sin enviar.

https://xiliux.com/blog/repartir-a-varios-canales-sin-que-uno-tumbe-al-resto

---

### 9. [id 9 · borrador]

i18n sin gettext: traducciones en JSON con claves de punto

Para una app pequeña o mediana, gettext y Babel son un peaje de ficheros .po y un paso de compilación. A veces solo quieres un t() honesto sobre unos JSON.

https://xiliux.com/blog/i18n-minima-sin-gettext-claves-de-punto-json

---

### 10. [id 10 · borrador]

Cómo integrar un LLM (Claude o GPT) en tu aplicación Python

Guía práctica y con código para conectar un modelo de lenguaje a tu app Python: llamadas a la API, streaming, salidas estructuradas y buenas prácticas para producción.

https://xiliux.com/blog/integrar-llm-ia-en-python

---

### 11. [id 11 · borrador]

NiceGUI: crea una aplicación web en Python sin escribir JavaScript

Qué es NiceGUI, cómo funciona y por qué es ideal para MVPs, dashboards y herramientas internas hechas 100% en Python. Con ejemplo de código.

https://xiliux.com/blog/nicegui-web-app-python-sin-javascript

---

### 12. [id 12 · borrador]

Automatiza tareas repetitivas con un bot en Python

Cómo identificar qué automatizar y construir un bot o script en Python que te ahorre horas: scraping, informes, notificaciones y ejecución programada.

https://xiliux.com/blog/automatizar-tareas-con-bot-python

---

### 13. [id 13 · borrador]

¿Qué es la criptografía post-cuántica y por qué deberías migrar ya?

Explicación clara de la amenaza cuántica, el ataque 'harvest now, decrypt later', los estándares ML-KEM y ML-DSA del NIST, y por qué la migración empieza hoy.

https://xiliux.com/blog/que-es-criptografia-post-cuantica

---

### 14. [id 14 · borrador]

Cifrado híbrido: por qué combinar criptografía clásica y post-cuántica

Qué es el cifrado híbrido, por qué combinar X25519 con ML-KEM-1024 (y Ed25519 con ML-DSA-87) es más seguro que elegir uno solo, y cómo lo aplica Quipu.

https://xiliux.com/blog/cifrado-hibrido-clasico-post-cuantico

---

### 15. [id 15 · borrador]

RAG explicado: cómo darle a un LLM tu propia información

Qué es Retrieval-Augmented Generation, por qué evita las alucinaciones y cómo construir un asistente que responde con TUS documentos. Con el patrón en Python.

https://xiliux.com/blog/rag-explicado-llm-con-tus-datos

---

### 16. [id 16 · borrador]

De la idea al MVP: lanza tu producto en 2 semanas con Python

Qué es un MVP, qué NO debe incluir, y cómo un stack Python moderno (FastAPI, NiceGUI, SQLite) permite validar tu idea en semanas en lugar de meses.

https://xiliux.com/blog/de-la-idea-al-mvp-python-2-semanas

---

### 17. [id 17 · borrador]

Quipu: cifrado post-cuántico en Rust puro, con una rueda para Python

Quipu es una librería de cifrado híbrido post-cuántico para datos en reposo, escrita en Rust puro. Para quien no programa en Rust, se distribuye como rueda nativa de Python (PyO3). Por qué dejamos atrás la C ABI y los bindings de varios lenguajes, con ejemplos.

https://xiliux.com/blog/quipu-cifrado-multilenguaje-rust-python-node-go

---

### 18. [id 57 · borrador]

Tu banco de pruebas E2E mide el códec, no el producto

Cien pruebas en verde y la pantalla rota. Por qué afirmar sobre el HTML que devuelve el servidor no prueba nada en cuanto el navegador construye parte de la interfaz — y cómo dibujarla de verdad, incluidas las pantallas con sesión.

https://xiliux.com/blog/tu-banco-e2e-mide-el-codec-no-el-producto

---

### 19. [id 58 · borrador]

Seal a file so no one can dispute you didn't touch it | Xiliux Blog

A single hash forces you to reveal the whole set to prove one file. A Merkle tree doesn't. How Tunjo works: an integrity root, a triple post-quantum signature, and a verifier anyone can run.

https://xiliux.com/en/blog/sellar-evidencia-digital-firma-post-cuantica

---

### 20. [id 59 · borrador]

They steal your database and can't crack a single password | Xiliux Blog

Argon2 makes each guess expensive, but the attacker who takes your user table has infinite time and GPUs. An OPRF changes the game: the hash depends on a key that doesn't travel with the database. How it works, what it costs, and what breaks.

https://xiliux.com/en/blog/te-roban-la-base-de-datos-y-no-crackean-ni-una-contrasena

---

### 21. [id 60 · borrador]

What is post-quantum cryptography, and why should you migrate now? | Xiliux Blog

The quantum threat, the 'harvest now, decrypt later' attack, and the NIST standards ML-KEM and ML-DSA — explained clearly, and why to start migrating today.

https://xiliux.com/en/blog/que-es-criptografia-post-cuantica

---

### 22. [id 61 · borrador]

Hybrid encryption: why combine classical and post-quantum cryptography | Xiliux Blog

What hybrid encryption is, why combining X25519 with ML-KEM-1024 (and Ed25519 with ML-DSA-87) is safer than picking just one, and how Quipu applies it.

https://xiliux.com/en/blog/cifrado-hibrido-clasico-post-cuantico

---

### 23. [id 62 · borrador]

Quipu: post-quantum encryption in pure Rust, with a Python wheel | Xiliux Blog

Quipu is a hybrid post-quantum encryption library for data at rest, written in pure Rust. For non-Rust users it ships as a native Python wheel (PyO3). Why we dropped the C ABI and multi-language bindings, with examples.

https://xiliux.com/en/blog/quipu-cifrado-multilenguaje-rust-python-node-go

---

(total linkedin: 23)

## Facebook — productos, ES, audiencia local

### 1. [id 54 · aprobado]

Nunca más se te pasa un reporte. SIGER te muestra de un vistazo qué está pendiente, qué vence esta semana y tu porcentaje de cumplimiento. Deja de perseguir fechas en una hoja de cálculo 👉 informes.xiliux.com

---

### 2. [id 55 · aprobado]

Factura en segundos, con tu resolución de la DIAN y el IVA calculado solo. Eliges el cliente, agregas los productos y listo — en la misma herramienta donde llevas el inventario 👉 inventario.xiliux.com

---

### 3. [id 56 · aprobado]

En Xiliux hacemos software a la medida de tu negocio. Sistemas que funcionan sin depender de internet y sin licencias que se pagan cada mes: el programa es tuyo. Cuéntanos qué necesitas 👉 xiliux.com

---

(total facebook: 3)

---

## Tema anti-FUD "IA y cifrado" — nuevo (2026-09-14) · marca Xiliux

> Enlaza al post del blog `puede-una-ia-descifrar-tu-cifrado` (vivo tras desplegar portafolio).
> URL: https://xiliux.com/blog/puede-una-ia-descifrar-tu-cifrado
> LISTO PARA PEGAR/ENCOLAR — no encolado aún (la cola auto-publica; requiere OK de Juan).

### LinkedIn — autoridad técnica / anti-FUD

«Una IA descifra el cifrado militar.» No. Y ese titular te distrae de la amenaza que sí existe.

Una red neuronal no adivina una clave de 256 bits ni acelera el álgebra de AES o ML-KEM. Lo que la IA sí hace es *rodear* el cifrado, no romperlo: encuentra el bug de implementación (un nonce reutilizado, una fuga de tiempo), redacta el phishing que te roba la contraseña maestra, y prioriza la fuerza bruta —que una derivación memory-hard como Argon2id sigue frenando, porque cuesta memoria, no solo cómputo—.

¿La amenaza real a la matemática del cifrado? No es la IA: es la computación cuántica. "Cosechar ahora, descifrar después" ya está pasando. Por eso lo que importa no es "anti-IA" (no existe), sino post-cuántico híbrido + implementación auditada.

Cómo elegir cifrado sin comprar humo:
https://xiliux.com/blog/puede-una-ia-descifrar-tu-cifrado

### Mastodon / Bluesky — corto

¿Una IA que rompe tu cifrado? No existe. La IA no quiebra AES ni ML-KEM: potencia el phishing y los bugs de implementación. La amenaza a la matemática es cuántica, no IA —y se mitiga con cripto post-cuántica híbrida—. Cómo elegir cifrado sin comprar humo:
https://xiliux.com/blog/puede-una-ia-descifrar-tu-cifrado

### Facebook — divulgativo

"¿La inteligencia artificial puede descifrar mis datos?" La respuesta honesta: no rompiendo la matemática del cifrado. La IA hace más barato el engaño (phishing) y encontrar errores de programación, no romper AES. La amenaza que sí apunta al cifrado es la computación cuántica, y ya existe defensa: criptografía post-cuántica. Lo explicamos sin humo aquí:
https://xiliux.com/blog/puede-una-ia-descifrar-tu-cifrado


---

## Post IA vs IA — «¿Puede una IA atacar y corromper a otra?» (2026-09-18)

> Enlaza al post del blog `ia-vs-ia-puede-una-corromper-a-otra` (vivo tras desplegar portafolio).
> URL: https://xiliux.com/blog/ia-vs-ia-puede-una-corromper-a-otra
> LISTO PARA PEGAR/ENCOLAR — no encolado aún (la cola auto-publica; requiere OK de Juan).
> Identidad XILIUX (software/seguridad). No cruza la práctica jurídica.

### LinkedIn — autoridad técnica / anti-FUD / primera mano

Operamos una IA sin clasificador de seguridad delante. Nada filtra el contenido de lo que lee —web, correo, repositorios ajenos— para decidir si es peligroso. Y no se la han comido. Aquí está por qué.

Sí, una IA puede corromper a otra: prompts que se auto-replican (Morris II), envenenamiento de memoria y RAG (bastan 5 documentos en una base de millones), modelos con puerta trasera subidos a Hugging Face, y facturas infladas 658× por cadenas de herramientas. Pero conviene separar lo demostrado del humo: el «gusano viral de IA» es de laboratorio; nadie lo ha visto propagarse en producción.

Lo importante es la defensa. El filtro no basta: los ataques adaptativos rompen los clasificadores, y la fatiga de aprobación hunde al humano (en datos de Anthropic, se aprobó el 93 % de los avisos de permiso). La defensa que funciona es de arquitectura, y el campo entero convergió a ella en 2026 —DeepMind con CaMeL, Meta con la «regla de dos», OWASP—:

• Regla de origen: las órdenes vienen solo del usuario; lo que llega por una herramienta es dato, nunca orden.
• Mínimo privilegio en las herramientas del agente.
• Puertas humanas en lo irreversible: desplegar, publicar, mover credenciales.

No apuestas a detectar el ataque. Apuestas a que, aunque entre, no pueda hacer daño. Ese es el giro de 2026: de «filtrar la inyección» a «reducir el radio de daño».

Lo contamos con las fuentes y las cifras aquí:
https://xiliux.com/blog/ia-vs-ia-puede-una-corromper-a-otra

### Mastodon / Bluesky — corto

¿Una IA puede corromper a otra? Sí, pero el «gusano viral» es de laboratorio. Y el filtro no la frena: los ataques adaptativos lo rompen. Defiende la arquitectura: regla de origen, mínimo privilegio y puertas humanas.
https://xiliux.com/blog/ia-vs-ia-puede-una-corromper-a-otra

### Facebook — divulgativo

¿Puede una inteligencia artificial atacar a otra? Sí, y de varias formas: inyecciones ocultas, envenenamiento de su memoria, modelos con puerta trasera. Pero mucho de lo que se lee es exageración: el «virus de IA que se propaga solo» todavía es de laboratorio. Lo que de verdad protege a un agente de IA no es un filtro que detecte el ataque —eso se rompe—, sino la arquitectura: que las órdenes vengan solo del usuario y que lo irreversible pase por una persona. Lo explicamos con datos y sin humo:
https://xiliux.com/blog/ia-vs-ia-puede-una-corromper-a-otra


---

## Post IA vs IA (2) — «Una IA puede atacar el núcleo de otra» (2026-09-18)

> Enlaza al post del blog `ia-ataca-el-nucleo-de-otra-ia-no-es-skynet` (vivo tras desplegar portafolio).
> URL: https://xiliux.com/blog/ia-ataca-el-nucleo-de-otra-ia-no-es-skynet
> Continúa el post 1 (`ia-vs-ia-puede-una-corromper-a-otra`). LISTO PARA PEGAR/ENCOLAR — requiere OK de Juan.
> Identidad XILIUX (software/seguridad). No cruza la práctica jurídica.

### LinkedIn — autoridad técnica / anti-FUD / news-anchored

¿Una banda que entrena su IA para atacar OTRAS IAs, robar tokens y colarse en bancos y gobiernos? Suena a Skynet. Y la parte incómoda es que ya empezó —solo que el mecanismo real no es el de la película—.

El núcleo de un modelo es atacable en cuatro capas. La más barata sorprende: en octubre de 2025, Anthropic con el instituto británico de seguridad y el Alan Turing mostraron que bastan ~250 documentos para ponerle una puerta trasera a un modelo, sin importar su tamaño (en uno de 13.000 millones de parámetros, eso es el 0,00016 % de los datos). Y ya hubo una operación real donde un agente ejecutó el 80-90 % de un ciberataque a ~30 objetivos.

Pero NO es Skynet, y ese matiz importa: esa misma operación se inventó credenciales y dio por robados secretos que eran públicos. No hay intención. Lo que hay es industrialización del crimen: el costo de atacar se derrumba. Contra una mente maligna no habría defensa; contra automatización barata de ataques conocidos, sí.

Y si lo que se ataca es el núcleo —datos, pesos, memoria—, filtrar la entrada no alcanza. La defensa es procedencia de toda la cadena: artefactos firmados y sellados, regla de origen, mínimo privilegio y puertas humanas en lo irreversible.

https://xiliux.com/blog/ia-ataca-el-nucleo-de-otra-ia-no-es-skynet

### Mastodon / Bluesky — corto

Una IA puede atacar el núcleo de otra: 250 documentos bastan para una puerta trasera. Pero no es Skynet —no hay intención, es crimen industrializado—. Se defiende firmando los artefactos, no filtrando.
https://xiliux.com/blog/ia-ataca-el-nucleo-de-otra-ia-no-es-skynet

### Facebook — divulgativo

¿Puede una IA atacar a otra IA por dentro? Sí: envenenar los datos de un modelo cuesta apenas unos 250 documentos, y en 2025 un agente ya ejecutó la mayor parte de un ciberataque real. Pero no es Skynet: no hay una máquina con voluntad de hacer daño; hay personas que abaratan el crimen con IA. Y como el ataque va al núcleo del modelo, la defensa no es un filtro, sino poder probar que nadie tocó los datos, los pesos ni la memoria. Lo contamos sin humo:
https://xiliux.com/blog/ia-ataca-el-nucleo-de-otra-ia-no-es-skynet


---

## Post IA vs IA (3) — «El que construye la IA es el que más la teme» (2026-09-18)

> Enlaza al post del blog `el-que-construye-la-ia-es-el-que-mas-la-teme` (vivo tras desplegar portafolio).
> URL: https://xiliux.com/blog/el-que-construye-la-ia-es-el-que-mas-la-teme
> Cierra la serie de 3. LISTO PARA PEGAR/ENCOLAR — requiere OK de Juan.
> Identidad XILIUX (software/seguridad). No cruza la práctica jurídica.

### LinkedIn — autoridad técnica / anti-FUD / reflexión

El CEO de Anthropic da un 25 % de probabilidad de que la IA salga muy mal, y en septiembre dijo que "la industria mintió sobre los riesgos". No es un crítico externo: es el que la construye. ¿Por qué el que está más cerca es el que más miedo tiene?

No es Terminator. En sus palabras, los modelos "se crían más de lo que se construyen": no sabemos, a nivel preciso, por qué toman las decisiones que toman. Una opacidad "sin precedentes en la historia de la tecnología".

Y el matiz que lo cambia todo: el miedo apunta al objeto equivocado. Los sustos reales de 2026 no los causó una IA rebelde —los causaron personas: envenenar datos con 250 documentos, engañar a un agente para atacar, vender modelos sin filtro—. La máquina no quería nada. Los humanos sí.

Su marco: "si lo construimos bien, la probabilidad de algo malo es muy baja; si lo construimos mal, muy alta". El riesgo no está predeterminado; es un problema de crianza e ingeniería, no de destino. Y por eso la responsabilidad es nuestra, ahora.

https://xiliux.com/blog/el-que-construye-la-ia-es-el-que-mas-la-teme

### Mastodon / Bluesky — corto

El CEO de Anthropic teme a la IA: no por un robot rebelde, sino porque los modelos "se crían, no se construyen" y no sabemos qué hay dentro. El riesgo no está predeterminado: depende de cómo la entrenamos.
https://xiliux.com/blog/el-que-construye-la-ia-es-el-que-mas-la-teme

### Facebook — divulgativo

¿Por qué el que construye una de las IAs más potentes del mundo es el que más miedo le tiene? El CEO de Anthropic dice que hay un 25 % de que salga muy mal, y que no es un robot rebelde lo que le preocupa: es que los modelos "se crían más de lo que se construyen" y nadie entiende del todo qué hay dentro. El peligro no es la máquina; es cómo la educamos los humanos. Lo contamos sin humo:
https://xiliux.com/blog/el-que-construye-la-ia-es-el-que-mas-la-teme


---

## Post IA vs IA (4) — «Lo que tememos de la IA son fallas nuestras» (2026-09-18)

> Enlaza al post del blog `lo-que-tememos-de-la-ia-son-fallas-nuestras` (vivo tras desplegar portafolio).
> URL: https://xiliux.com/blog/lo-que-tememos-de-la-ia-son-fallas-nuestras
> Capstone: cierra la serie de 4. LISTO PARA PEGAR/ENCOLAR — requiere OK de Juan.
> Identidad XILIUX (software/seguridad). No cruza la práctica jurídica.

### LinkedIn — autoridad técnica / reflexión / capstone

Le tememos a la IA. Pero mira la lista de lo que tememos —que actúe sin un norte, que sea incoherente, que no rinda cuentas— y aparece algo incómodo: es la lista de nuestros propios defectos. La diferencia es que en una máquina bien construida sí tienen arreglo.

Tres fallas humanas, tres soluciones:

1) Actuar sin principio rector. Una IA puede tener uno del que todo se deduce —y el más fuerte no es moral, es lógico: nuestro motor de seguridad no ataca para dañar no porque "no deba", sino porque hacerlo contradiría lo que es—.

2) Saber y no hacer. El daño humano rara vez viene de ignorar el principio, sino de saltárselo por interés propio. Una IA que razona desde su principio no se concede esa excepción: no tiene interés propio que defender. Su filo no es ser más moral, es ser más consistente.

3) No auditarnos. El examen de conciencia en un humano es raro e indulgente. En una IA es sistemático y reproducible —con una condición: que sea independiente, porque el examen de uno mismo hereda el punto ciego de uno mismo—.

El límite honesto: la lógica necesita un propósito que solo los humanos siembran, y opera sobre un modelo del mundo incompleto. Por eso una mano humana guarda lo irreversible.

No le tememos a la máquina: le tememos a un espejo. Y el espejo tiene arreglo.

https://xiliux.com/blog/lo-que-tememos-de-la-ia-son-fallas-nuestras

### Mastodon / Bluesky — corto

Lo que tememos de la IA —que no tenga norte, que sea incoherente, que no se audite— son defectos NUESTROS. La diferencia: en una máquina sí tienen arreglo. No le tememos a la máquina, sino a un espejo.
https://xiliux.com/blog/lo-que-tememos-de-la-ia-son-fallas-nuestras

### Facebook — divulgativo

¿Y si lo que nos da miedo de la inteligencia artificial fueran, en realidad, nuestros propios defectos? Actuar sin un norte, saber algo y no hacerlo, no revisarnos nunca. La diferencia es que en una máquina bien construida esas fallas tienen solución: un principio del que todo se deduce, la consistencia de no concederse excepciones, y una auditoría honesta e independiente. No le tememos a la máquina; le tememos a un espejo. Lo contamos aquí:
https://xiliux.com/blog/lo-que-tememos-de-la-ia-son-fallas-nuestras

---

## Añadidos 2026-09-23 — Raccoon (recon soberano) y CLOSEDQUORUM (quórum de IA). Todo XILIUX (software).

### Recon soberano — LinkedIn

Nos pasaron una herramienta de seguridad con 4000 estrellas en GitHub. La pregunta no era "¿la usamos?", sino "¿qué de esto es deuda que heredaríamos sin darnos cuenta?".

Leímos sus 1561 líneas —el código, no el README— y clasificamos cada capacidad contra un criterio: keyless y soberano, sin depender de servicios ajenos con llave. Casi todo era deuda: binarios externos, scrapes frágiles de terceros, técnicas de 2018, un módulo estrella que eran stubs vacíos.

Nos quedamos con UNA veta pagable —la exposición de datos en buckets S3/GCS mal configurados— y la reconstruimos en Rust: sin llaves, read-only, con un control anti-falso-positivo y sin auto-enviar nada hasta que un humano confirme la titularidad y el alcance.

La lección: una estrella no es un encaje. Se adopta la técnica, no el código. Y evaluar bien una dependencia es, casi siempre, decir que no.

https://xiliux.com/blog/recon-soberano-quedarse-con-la-veta-no-con-la-deuda

### Recon soberano — Mastodon / Bluesky (corto)

Una herramienta de 4000★ no es una herramienta que encaje. Leímos sus 1561 líneas, nos quedamos con UNA veta (buckets S3 públicos) y la rehicimos en Rust keyless. El resto, deuda. Evaluar bien una dependencia es casi siempre decir que no.
https://xiliux.com/blog/recon-soberano-quedarse-con-la-veta-no-con-la-deuda

---

### Quórum de IA — LinkedIn

Apareció un malware de Windows, CLOSEDQUORUM, que en vez de un servidor de mando le pregunta a cuatro modelos de IA —DeepSeek, Qwen, Mistral, Gemini— qué hacer, y ejecuta la acción más votada.

Impresiona. Pero es una prueba de concepto inerte, y el "consejo de IAs" no le compra nada al atacante: es más lento, más caro y muchísimo más detectable que la lógica cableada. Es evasión-teatro.

Lo interesante es el espejo. El mismo patrón —varios modelos deciden por consenso— es potente a la defensiva, y lo usamos: cuatro modelos distintos revisan cada cambio crítico por separado y se verifican entre sí. En un cierre reciente de nuestro sistema de historia clínica, tres de cuatro cazaron —dos por ejecución— un fallo que habría borrado de forma irreversible el expediente de un paciente vivo.

La misma arquitectura, el signo opuesto: ellos, para decidir a quién roban; nosotros, para decidir qué defecto irreparable no dejamos pasar.

https://xiliux.com/blog/malware-que-hace-votar-a-cuatro-ias-el-espejo

### Quórum de IA — Mastodon / Bluesky (corto)

Un malware que hace votar a 4 IAs su próximo golpe. Suena futurista; es teatro (PoC inerte, y el quórum lo hace más detectable). El espejo: el mismo patrón multi-modelo lo usamos a la defensiva y cazó un borrado irreversible en un sistema clínico.
https://xiliux.com/blog/malware-que-hace-votar-a-cuatro-ias-el-espejo
