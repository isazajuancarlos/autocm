# Imágenes de post con Canva (Connect API)

Genera la **tarjeta de marca** de cada publicación rellenando una *Brand
Template* de Canva con el texto del post, la exporta a PNG y la deja lista para
`cola.encolar(..., imagen=ruta, imagen_alt=alt)`. Los publicadores de
`publicar_cola.py` ya adjuntan esa imagen en Bluesky, Mastodon y Facebook.

## El gate que hay que saber antes de nada

**La Autofill API de Canva (rellenar plantillas por API) exige una organización
Canva Enterprise.** Con un plan de pago hay acceso *trial* durante el desarrollo,
pero para uso continuado es Enterprise. Si la cuenta no lo tiene, este camino no
funciona y hay que volver a la alternativa local con Pillow (que no se construyó
porque se eligió Canva). **Verifica esto primero**, o montarás la app y la
plantilla para chocar con un 403 al primer autofill.

## Lo que pones TÚ (no está en el código)

1. **Una app/integración** en https://www.canva.com/developers/ :
   - Redirect URL: `http://127.0.0.1:8766/callback`
   - Scopes: `design:content:write` y `design:content:read`
   - Copia el **Client ID** y el **Client Secret** al `.env`
     (`CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`). *El secret es una credencial: lo
     pegas tú, no se comparte por aquí.*
2. **Una Brand Template** con campos de texto de autorrelleno. Anota:
   - El **ID de la plantilla** (sale en la URL del diseño) → `CANVA_BRAND_TEMPLATE_ID`.
   - Las **claves** de sus campos de texto → `CANVA_CAMPO_TITULO` (y
     `CANVA_CAMPO_CUERPO` si tiene un campo para el cuerpo).
3. **El token**, una vez:
   ```bash
   CANVA_CLIENT_ID=… CANVA_CLIENT_SECRET=… .venv/bin/python canva_oauth.py
   ```
   Inicia sesión con la cuenta de la organización Enterprise, autoriza, y pega en
   `.env` el `CANVA_ACCESS_TOKEN` y el `CANVA_REFRESH_TOKEN` que imprime.

## Lo que ya está construido y probado (offline)

- `canva.py` — cliente: `autorellenar()` → `exportar_png()` → `descargar()`, y el
  atajo `imagen_de_plantilla()`. Sondea los jobs con tope de tiempo (directiva
  39) y falla ruidoso (directiva 20). No registra el token.
- `canva_oauth.py` — el OAuth con PKCE (patrón de `get_linkedin_token.py`).
- `imagen_para_post.py` — el puente: `imagen_para(titulo, cuerpo) -> (ruta, alt)`,
  mapeando a las claves de campo del `.env`. El `alt` NO es opcional: la cola
  rechaza una imagen sin texto alternativo.
- `prueba_canva.py` — 17 comprobaciones sin red (parseo, forma del cuerpo, y los
  casos ROJOS: job fallido, sin token, urls vacías, timeout, sin config).
  `.venv/bin/python prueba_canva.py`.

## Cómo se enchufa a la cola (cuando el token esté)

En el punto donde hoy se encola una nota (p. ej. `llenar_cola.py`), antes del
`encolar`:

```python
from imagen_para_post import imagen_para
ruta, alt = imagen_para(titulo, cuerpo=descripcion)   # genera la tarjeta en Canva
cola.encolar(cx, destino, tipo, cuerpo, enlace=enlace, imagen=ruta, imagen_alt=alt)
```

Si `imagen_para` falla (token caducado, plantilla mal, Canva caído), lanza
`ErrorCanva`: decide ahí si encolar SIN imagen (degradar a texto, que los
publicadores ya soportan) o abortar esa nota. Recomendado degradar a texto: una
nota sin tarjeta es mejor que ninguna.

## Pendiente / límites

- **Refresco automático del token**: hoy `canva.py` no refresca; cuando el token
  de ~4 h caduque, el temporizador fallará con 401. Falta añadir el
  `grant_type=refresh_token` (con el `CANVA_REFRESH_TOKEN`) en `canva.py` y
  reintentar una vez. Sencillo, se hace cuando el flujo esté vivo.
- **e2e real**: no se pudo correr sin la app + plantilla + plan Enterprise; el
  código está validado contra la forma DOCUMENTADA de la API (fixtures), no
  contra Canva vivo. El primer autofill real es la prueba que falta (directiva
  28).
- **Imágenes en los campos** (no solo texto): la plantilla puede tener campos de
  imagen (`type: image`, con `asset_id`); habría que subir el asset antes
  (`asset:write`). Hoy `canva.py` solo rellena texto, que es lo que pide una
  tarjeta con el copy del post.
