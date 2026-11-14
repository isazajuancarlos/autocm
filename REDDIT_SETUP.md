# 🔴 Reddit Integration - Guía Completa

## 🚀 Inicio Rápido

### 1. Instalar PRAW (Python Reddit API Wrapper)

```bash
pip install praw
```

### 2. Crear una Aplicación en Reddit

Reddit requiere que crees una "app" para acceder a su API.

#### Paso a paso:

1. **Inicia sesión en Reddit** con tu cuenta
   - Si no tienes cuenta, créala en https://www.reddit.com

2. **Ve a Reddit Apps**
   - URL: https://www.reddit.com/prefs/apps
   - O: Preferencias → Apps

3. **Crea una nueva app**
   - Click en "create app" o "create another app..." (al final de la página)

4. **Completa el formulario**:
   ```
   name: Xiliux AutoCM
   App type: ⚫ script (selecciona esta opción)
   description: Automated content marketing for Xiliux
   about url: https://www.xiliux.com (opcional)
   redirect uri: http://localhost:8080
   ```

5. **Click en "create app"**

6. **Obtén tus credenciales**:
   ```
   client_id: El código debajo de "personal use script" (14 caracteres)
   client_secret: El código junto a "secret" (27 caracteres)
   ```

### 3. Configurar .env

Añade estas líneas a tu archivo `.env`:

```bash
# === REDDIT ===
REDDIT_CLIENT_ID=tu_client_id_de_14_caracteres
REDDIT_CLIENT_SECRET=tu_client_secret_de_27_caracteres
REDDIT_USERNAME=tu_usuario_reddit
REDDIT_PASSWORD=tu_contraseña_reddit
REDDIT_SUBREDDIT=test  # Empieza con r/test para probar
REDDIT_ENABLED=false   # Cambia a true cuando estés listo
```

**IMPORTANTE**: Empieza con `REDDIT_ENABLED=false` y primero prueba manualmente en r/test.

### 4. Probar la Conexión

```python
import praw
import os
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent="python:xiliux-autocm:v1.0 (by /u/tu_usuario)"
)

print(f"Autenticado como: {reddit.user.me()}")
print("✅ Conexión exitosa a Reddit API")
```

### 5. Primera Publicación de Prueba

```python
# Publicar en r/test (subreddit de pruebas)
subreddit = reddit.subreddit("test")
submission = subreddit.submit(
    title="Probando la API de Reddit",
    selftext="Este es un post de prueba desde Python con PRAW"
)
print(f"Publicado: https://reddit.com{submission.permalink}")
```

### 6. Activar en el Agente Principal

Una vez que confirmes que funciona:

1. Cambia en `.env`: `REDDIT_ENABLED=true`
2. Cambia `REDDIT_SUBREDDIT=nombre_del_subreddit` (sin el r/)
3. Reinicia: `python main.py`

---

## 📋 Subreddits Recomendados para Xiliux

### Para LegalTech

| Subreddit | Miembros | Permite Promoción | Notas |
|-----------|----------|-------------------|-------|
| **r/legaltech** | ~2.5k | ⚠️ Limitada | Enfoque en discusiones, no solo promoción |
| **r/LawFirm** | ~24k | ⚠️ Limitada | Solo si aporta valor a abogados |
| **r/LawSchool** | ~194k | ❌ Restrictivo | Mejor solo participar sin promoción |
| **r/law** | ~536k | ❌ Muy restrictivo | Solo noticias legales |

### Para Python y Desarrollo

| Subreddit | Miembros | Permite Promoción | Notas |
|-----------|----------|-------------------|-------|
| **r/Python** | ~1.3M | ⚠️ Solo sábados | "Saturday Daily Thread" para proyectos |
| **r/learnpython** | ~630k | ✅ Si es educativo | Posts tipo tutorial/guía |
| **r/programming** | ~6.2M | ⚠️ Limitada | Contenido técnico de calidad |
| **r/coolgithubprojects** | ~53k | ✅ Sí | Ideal para proyectos open source |
| **r/Python_Projects** | ~12k | ✅ Sí | Específico para mostrar proyectos |
| **r/WebDev** | ~1.8M | ⚠️ Solo "Showoff Saturday" | Un día específico |

### Para Emprendimiento/Startups

| Subreddit | Miembros | Permite Promoción | Notas |
|-----------|----------|-------------------|-------|
| **r/SideProject** | ~235k | ✅ Sí | Perfecto para proyectos paralelos |
| **r/Entrepreneur** | ~2.8M | ⚠️ Limitada | Aportar valor primero |
| **r/startups** | ~1.3M | ⚠️ Limitada | Restricciones estrictas |
| **r/SaaS** | ~78k | ✅ Moderada | Si es contenido útil sobre SaaS |

### Para Testing

| Subreddit | Permite TODO | Notas |
|-----------|--------------|-------|
| **r/test** | ✅ | Sandbox oficial de Reddit |
| **tu propio subreddit** | ✅ | Crea uno para probar: r/XiliuxTest |

---

## ⚠️ Reglas CRÍTICAS de Reddit

### 1. La Regla 9:1 (Self-Promotion)

**Por cada 1 post promocional, debes tener 9 posts/comentarios aportando valor.**

Ejemplo correcto:
- ✅ Comentar en 9 posts de otros usuarios (respondiendo preguntas, dando consejos)
- ✅ Publicar 1 post sobre tu proyecto

Ejemplo incorrecto:
- ❌ Publicar solo sobre tu proyecto sin participar en la comunidad

### 2. Lee las Reglas de Cada Subreddit

```python
# Ver reglas programáticamente
subreddit = reddit.subreddit("python")
for rule in subreddit.rules:
    print(f"- {rule.short_name}: {rule.description}")
```

O visita: https://www.reddit.com/r/nombredelsubreddit/about/rules

### 3. No Spam

- ❌ NO publicar el mismo contenido en múltiples subreddits seguidos
- ❌ NO publicar más de 1 vez al día en el mismo subreddit
- ✅ Espera al menos 24-48 horas entre posts promocionales

### 4. Aporta Valor

Reddit valora:
- ✅ Tutoriales detallados
- ✅ Casos de estudio
- ✅ Herramientas gratuitas y útiles
- ✅ Código open source
- ✅ Respuestas genuinas a preguntas

Reddit penaliza:
- ❌ "Mira mi producto"
- ❌ Links sin contexto
- ❌ Pure marketing speak

### 5. Participa Antes de Promocionar

**Estrategia recomendada**:

1. **Semana 1-2**: Solo participa
   - Comenta en posts relevantes
   - Responde preguntas
   - Comparte conocimiento

2. **Semana 3**: Primera promoción suave
   - Post educativo con mención sutil a tu proyecto
   - Ej: "Cómo automaticé mi despacho legal con Python"

3. **Continúa el ratio 9:1**
   - Por cada post sobre Xiliux, 9 contribuciones genuinas

---

## 🎯 Estrategia de Contenido para Reddit

### Tipos de Posts que Funcionan

#### 1. Tutorial/Guía (⭐⭐⭐⭐⭐)

```markdown
Título: "Cómo automatizar contratos legales con Python: Tutorial paso a paso"

Contenido:
- Problema que resuelve
- Código completo (con explicación)
- Screenshots/resultados
- Al final: "Construí una herramienta completa para esto: [link a xiliux.com]"
```

#### 2. Show and Tell (⭐⭐⭐⭐⭐)

```markdown
Título: "Construí una herramienta de compliance legal con NiceGUI"

Contenido:
- Qué hace
- Screenshot/demo
- Stack técnico
- Problemas que tuve y cómo los resolví
- Link al proyecto (si es open source, mejor)
```

#### 3. Ask for Feedback (⭐⭐⭐⭐)

```markdown
Título: "¿Qué opináis de esta interfaz para gestión legal? (NiceGUI)"

Contenido:
- Screenshot
- Contexto del proyecto
- Preguntas específicas
- Estar genuinamente abierto al feedback
```

#### 4. Caso de Estudio (⭐⭐⭐⭐)

```markdown
Título: "Reduje 15 horas/semana de trabajo manual con automatización Python"

Contenido:
- Problema inicial
- Solución implementada (con detalles técnicos)
- Resultados cuantificables
- Lecciones aprendidas
- Opcional: Link a herramienta
```

### Tipos de Posts que NO Funcionan

❌ "Visita mi web de servicios legal tech"
❌ "Ofrezco consultoría [lista de precios]"
❌ "Lanzamos [producto], mira las features"
❌ Solo un link sin contexto

---

## 🛡️ Evitar Ser Baneado

### Señales de Alerta

Si ves estos signos, PARA inmediatamente:

- 🔴 Tus posts reciben muchos downvotes (-5 o más)
- 🔴 Comentarios tipo "This is spam"
- 🔴 Moderadores te envían warnings
- 🔴 Tus posts son removidos automáticamente

### Qué Hacer Si Te Banean

1. **No crear nuevas cuentas** (ban evasion = permanente)
2. **Contactar a moderadores** educadamente
3. **Explicar tu intención** (genuino valor vs spam)
4. **Pedir perdón** y comprometerte a seguir reglas
5. **Esperar** (algunos bans son temporales)

### Mejores Prácticas

✅ **Cuenta con karma positivo** (>100 antes de promocionar)
✅ **Cuenta antigua** (>1 mes antes de promocionar)
✅ **Verificar email** de tu cuenta Reddit
✅ **Comentar más que publicar** (ratio 10:1)
✅ **Usar lenguaje natural** (no corporativo)
✅ **Responder a comentarios** en tus posts
✅ **Admitir cuando es tu proyecto** (transparencia)

---

## 🔧 Configuración Avanzada

### Publicar en Múltiples Subreddits (Cuidado)

Si quieres publicar en varios subreddits, hazlo con cautela:

```python
# En .env, usar lista separada por comas
REDDIT_SUBREDDIT=Python_Projects,SideProject,coolgithubprojects

# En main.py, modificar publish_reddit para iterar
```

**IMPORTANTE**:
- Espera 1-2 horas entre posts en diferentes subreddits
- Adapta el título a cada comunidad
- NO hagas crosspost inmediato (es spam)

### Programar Posts para Horarios Óptimos

Mejores horarios para Reddit (hora USA):
- **8-10 AM EST** (2-4 PM España)
- **12-2 PM EST** (6-8 PM España)
- **6-8 PM EST** (12-2 AM España)

Evitar:
- Madrugada USA (menos visibilidad)
- Fines de semana (depende del subreddit)

### Usar Flairs Correctamente

Muchos subreddits requieren flairs (etiquetas):

```python
submission = subreddit.submit(
    title="Mi título",
    selftext="Contenido",
    flair_id="id_del_flair"  # Obtener IDs con: subreddit.flair.link_templates
)
```

O seleccionar después de publicar en la web de Reddit.

---

## 📊 Métricas y Análisis

### Ver Rendimiento de tus Posts

```python
submission = reddit.submission(id="post_id")
print(f"Upvotes: {submission.score}")
print(f"Ratio: {submission.upvote_ratio}")
print(f"Comentarios: {submission.num_comments}")
print(f"Vistas: {submission.view_count}")  # Solo en tus propios posts
```

### Indicadores de Éxito

| Métrica | Malo | Regular | Bueno | Excelente |
|---------|------|---------|-------|-----------|
| Upvotes | <5 | 5-20 | 20-100 | >100 |
| Ratio | <0.5 | 0.5-0.7 | 0.7-0.9 | >0.9 |
| Comentarios | 0-2 | 2-5 | 5-20 | >20 |

### Responder a Comentarios

✅ **Siempre responde** a comentarios en tus posts
- Agradecer feedback positivo
- Responder preguntas técnicas
- Aceptar críticas constructivas
- NO ser defensivo

---

## 🚦 Sistema de Semáforo para Autopublicación

Para tu agente automático, usa este sistema:

### 🟢 VERDE (Autopublicar seguro)
- r/test
- r/Python_Projects (si es contenido genuino)
- r/SideProject (máx 1x/semana)
- Tu propio subreddit

### 🟡 AMARILLO (Manual mejor)
- r/python (solo sábados)
- r/learnpython (si es tutorial real)
- r/coolgithubprojects
- r/WebDev (solo sábados)

### 🔴 ROJO (NUNCA autopublicar)
- r/programming (muy estricto)
- r/legaltech (mejor participar primero)
- r/Entrepreneur
- r/startups

**Recomendación**: Empieza con `REDDIT_ENABLED=false` y publica manualmente hasta entender cada comunidad.

---

## 📝 Template de Posts para Reddit

### Template: Tutorial

```markdown
# Título del Tutorial

## El Problema
[Describe un problema real que muchos tienen]

## La Solución
[Explica tu solución paso a paso]

```python
# Código completo y funcional
```

## Resultados
[Screenshots, métricas, antes/después]

## Conclusión
[Resumen y próximos pasos]

[Opcional] Construí una herramienta completa basada en esto: [link]
```

### Template: Proyecto

```markdown
# Título del Proyecto

## Qué hace
[Descripción clara en 1-2 líneas]

## Por qué lo construí
[Historia personal/problema que resuelve]

## Stack técnico
- Python 3.x
- NiceGUI
- [otras tecnologías]

## Features principales
- Feature 1
- Feature 2
- Feature 3

## Lo que aprendí
[Retos técnicos interesantes]

## Feedback bienvenido
[Preguntas específicas para la comunidad]

Demo/Repo: [link si aplica]
```

---

## 🆘 Troubleshooting

### "Insufficient OAuth scope"
- Verifica que tu app sea tipo "script" (no "web app")
- Regenera client_secret

### "User doesn't have access to this resource"
- Algunos subreddits son privados/restringidos
- Necesitas ser miembro aprobado primero

### "You're doing that too much. Try again in X minutes"
- Rate limit de Reddit
- Espera el tiempo indicado
- Si es frecuente, tu cuenta necesita más karma

### "Post removed by moderators"
- Leíste las reglas del subreddit?
- Tu cuenta cumple requisitos mínimos?
- El contenido aporta valor?

### "Shadowban" (posts invisibles)
- Verifica en https://www.reddit.com/r/ShadowBan
- Contacta a admins de Reddit (no mods de subreddit)

---

## ✅ Checklist Pre-Publicación

Antes de activar `REDDIT_ENABLED=true`:

- [ ] He creado mi app de Reddit
- [ ] He configurado credenciales en .env
- [ ] He probado la conexión con script de prueba
- [ ] He publicado manualmente en r/test
- [ ] He leído las reglas de los subreddits objetivo
- [ ] Mi cuenta Reddit tiene >100 karma
- [ ] Mi cuenta tiene >1 mes de antigüedad
- [ ] He participado en comunidades primero (regla 9:1)
- [ ] Tengo preparado contenido valioso (no solo promoción)
- [ ] He configurado REDDIT_SUBREDDIT correctamente
- [ ] Entiendo que puedo ser baneado si hago spam

---

## 📚 Recursos Adicionales

- **PRAW Documentation**: https://praw.readthedocs.io/
- **Reddit API Rules**: https://www.reddit.com/wiki/api
- **Reddit Self-Promotion**: https://www.reddit.com/wiki/selfpromotion
- **Reddiquette**: https://www.reddit.com/wiki/reddiquette

---

**🎯 Próximos Pasos**:

1. Crea tu app de Reddit (5 minutos)
2. Configura .env con credenciales
3. Prueba en r/test
4. Participa en comunidades relevantes (1-2 semanas)
5. Publica tu primer post valioso
6. Si funciona bien, activa `REDDIT_ENABLED=true`

**Recuerda**: Reddit valora la autenticidad sobre todo. Si tu contenido genuinamente ayuda a la comunidad, serás bien recibido.
