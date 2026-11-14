# Fondos de marca para las tarjetas de post

Aquí van los PNG que exportas de Canva (el DISEÑO de marca, con un hueco para el
texto). Se **versionan** (viajan con el deploy al VPS). `TARJETA_FONDO` del `.env`
apunta a uno de estos por ruta absoluta, p. ej.
`/home/debian/autocm/fondos/fondo-quipu.png`.

Las tarjetas GENERADAS por post (fondo + texto) NO van aquí: van a `tarjetas/`
(gitignorado, runtime).
