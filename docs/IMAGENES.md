# Imágenes de post (vía HÍBRIDA: fondo de Canva + texto con Pillow)

La cuenta de Canva es **Educación**, no Enterprise, así que la Autofill API por
código no está disponible (ver `CANVA.md`). La vía elegida es híbrida y gratis:

1. **Tú** diseñas 1-2 **fondos de marca** en Canva (Educación te deja) y los
   exportas a PNG. Dejas un HUECO donde irá el texto del post.
2. **`tarjeta.py`** superpone el título del post en ese hueco con Pillow, local.
3. Se encola con su `alt` y los publicadores de `publicar_cola.py` lo suben.

## Config (`.env`)

```
IMAGEN_BACKEND=tarjeta            # 'tarjeta' (híbrida, por defecto) | 'canva' (Enterprise)
TARJETA_FONDO=fondos              # un archivo, o una CARPETA: rota al azar entre sus fondos
TARJETA_CAJA=100,250,1000,150     # x,y,ancho,alto del hueco de texto, en px del fondo
TARJETA_FUENTE=                    # .ttf opcional; por defecto DejaVu Sans Bold
TARJETA_COLOR=#FFFFFF
TARJETA_ALINEAR=center            # center | left
TARJETA_SOMBRA=1                   # 1 sombra suave (legibilidad); 0 no
```

Con `TARJETA_FONDO` apuntando a la CARPETA `fondos/`, cada post elige su fondo por
TEMA: cripto/Rust/seguridad → `fondo-quipu`, productos/demos → `fondo-productos`,
el resto → un fondo neutro (`fondo-generico`/`fondo-clasico`) al azar. Las palabras
clave están en `imagen_para_post.TEMAS`; el nombre del fondo debe contener el tema
(`fondo-quipu.jpg`).

El tamaño de fuente se **ajusta solo** hasta caber en la caja; un título largo se
envuelve en líneas y, si aun al mínimo no cabe, se recorta con «…». Nunca se sale
del hueco (probado).

## Enchufe a la cola

En `llenar_cola.py`, antes del `encolar`:

```python
from imagen_para_post import imagen_para, ErrorImagen
try:
    ruta, alt = imagen_para(titulo, cuerpo=descripcion)
    cola.encolar(cx, destino, tipo, cuerpo, enlace=enlace, imagen=ruta, imagen_alt=alt)
except ErrorImagen as e:
    log.warning("sin tarjeta (%s); encolo solo texto", e)
    cola.encolar(cx, destino, tipo, cuerpo, enlace=enlace)   # degrada a texto
```

## Pruebas

```
.venv/bin/python prueba_tarjeta.py    # el generador híbrido (dibuja dentro de la caja, no fuera)
.venv/bin/python prueba_canva.py      # el cliente Canva (para el día de Enterprise)
```
