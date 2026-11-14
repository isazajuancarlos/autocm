# 🔴 Reddit - Mejores Prácticas (Guía Rápida)

## ⚠️ Regla #1: NO HAGAS SPAM

Reddit **baneará** tu cuenta si detecta spam. Lee esto antes de publicar.

---

## 📜 Las 5 Reglas de Oro

### 1. Regla 9:1 (Self-Promotion)

**Por cada 1 post promocional, debes hacer 9 contribuciones genuinas.**

✅ **Correcto**:
- Comentar en 9 posts de otros (respondiendo preguntas, ayudando)
- Publicar 1 post sobre tu proyecto

❌ **Incorrecto**:
- Solo publicar sobre tu proyecto sin participar

### 2. Aporta Valor SIEMPRE

Reddit valora:
- ✅ Tutoriales detallados con código
- ✅ Casos de estudio con resultados
- ✅ Herramientas open source gratuitas
- ✅ Respuestas genuinas a preguntas

Reddit penaliza:
- ❌ "Visita mi web"
- ❌ "Ofrezco servicios de..."
- ❌ Marketing corporativo

### 3. Lee las Reglas de Cada Subreddit

Cada comunidad tiene reglas diferentes:
- r/python: Solo promoción en "Saturday Daily Thread"
- r/programming: Muy restrictivo con promoción
- r/SideProject: Más permisivo con proyectos

**Siempre lee**: https://www.reddit.com/r/nombredelsubreddit/about/rules

### 4. Participa ANTES de Promocionar

**Estrategia correcta**:

**Semana 1-2**: Solo participa
- Comenta en posts relevantes
- Responde preguntas
- Comparte conocimiento genuino

**Semana 3+**: Primera promoción
- Post educativo con mención sutil
- Ejemplo: "Tutorial: Cómo automaticé mi despacho legal con Python"

### 5. NO Spam Crossposting

❌ **NO hagas esto**:
- Publicar lo mismo en 5 subreddits en 10 minutos

✅ **Haz esto**:
- Publica en 1 subreddit
- Espera 24-48 horas
- Adapta el título/contenido para otro subreddit
- Publica en el segundo

---

## 🎯 Subreddits para Xiliux

### 🟢 VERDE (Relativamente seguros)

Puedes publicar con precaución:

- **r/Python_Projects** (12k) - Proyectos Python
- **r/SideProject** (235k) - Proyectos paralelos
- **r/coolgithubprojects** (53k) - Proyectos en GitHub
- **r/test** - Para probar (sandbox oficial)

**Frecuencia**: Máximo 1 post por semana

### 🟡 AMARILLO (Requieren más cuidado)

Lee reglas cuidadosamente:

- **r/python** (1.3M) - Solo sábados en thread específico
- **r/learnpython** (630k) - Solo si es tutorial educativo
- **r/legaltech** (2.5k) - Participar primero, promocionar después
- **r/WebDev** (1.8M) - Solo "Showoff Saturday"

**Frecuencia**: Máximo 1 post cada 2 semanas

### 🔴 ROJO (Evitar autopublicación)

**NUNCA** uses autopublicación automática aquí:

- **r/programming** (6.2M) - Extremadamente estricto
- **r/Entrepreneur** (2.8M) - Anti-spam muy activo
- **r/startups** (1.3M) - Restricciones muy fuertes

**Recomendación**: Solo publicar manualmente después de entender la comunidad

---

## 💡 Tipos de Contenido que Funcionan

### ✅ Tutorial con Código

```markdown
Título: "Cómo automatizar contratos legales con Python"

- Problema real
- Código completo (copy-paste funcional)
- Explicación paso a paso
- Screenshots de resultados
- Al final: "Construí una herramienta para esto: [link]"
```

**Upvotes esperados**: 50-200+

### ✅ "Show and Tell" de Proyecto

```markdown
Título: "Construí una herramienta LegalTech con NiceGUI"

- Qué hace (1 párrafo)
- Screenshot/demo
- Stack técnico
- Problemas interesantes que resolví
- Pedir feedback genuinamente
```

**Upvotes esperados**: 20-100+

### ✅ Caso de Estudio

```markdown
Título: "Reduje 15h/semana con automatización Python en mi despacho legal"

- Problema inicial (detallado)
- Solución técnica
- Resultados con números
- Lecciones aprendidas
- [Opcional] Link a herramienta
```

**Upvotes esperados**: 30-150+

### ❌ Lo que NO Funciona

- "Ofrezco servicios de LegalTech"
- "Visita mi web: xiliux.com"
- "Lanzamos [producto], mira las features"
- Solo un link sin contexto
- Marketing corporativo

**Upvotes esperados**: -5 a 0 (y posible ban)

---

## 🚦 Configuración para Autopublicación

### Opción 1: Conservadora (Recomendada)

```bash
# .env
REDDIT_ENABLED=false  # Publicar solo manualmente
```

Ventajas:
- Zero riesgo de ban
- Puedes adaptar contenido a cada subreddit
- Entiendes cada comunidad

### Opción 2: Semi-Automática

```bash
# .env
REDDIT_ENABLED=true
REDDIT_SUBREDDIT=test  # Solo en r/test
```

Prueba en r/test primero, luego cambia a:
- `Python_Projects` (si tu contenido es técnico)
- `SideProject` (si es un proyecto completo)

### Opción 3: Agresiva (Alto Riesgo)

```bash
REDDIT_ENABLED=true
REDDIT_SUBREDDIT=python  # Subreddit grande
```

⚠️ **Riesgos**:
- Probable ban si no sigues reglas exactas
- r/python solo permite promoción en sábados
- Necesitas karma alto y cuenta antigua

**Solo usa si**:
- Tu cuenta tiene >500 karma
- Tu cuenta tiene >6 meses
- Has participado activamente (ratio 9:1)

---

## 📊 Señales de Alerta

### 🔴 PARA inmediatamente si ves:

- Posts con -5 o más downvotes
- Comentarios "This is spam"
- Moderadores te envían warnings
- Posts removidos automáticamente
- "You're doing that too much" (rate limit constante)

### ✅ Señales de que lo haces bien:

- +10 upvotes en primeros 30 minutos
- Comentarios pidiendo más info
- Ratio upvote >0.7 (70% positivo)
- Preguntas técnicas genuinas

---

## 🛡️ Protección Anti-Ban

### Requisitos Mínimos

Antes de promocionar, asegúrate:

- [ ] **Karma >100** (combina post + comment karma)
- [ ] **Cuenta >1 mes** de antigüedad
- [ ] **Email verificado** en tu cuenta Reddit
- [ ] **Has comentado** en los subreddits donde publicarás
- [ ] **Entiendes las reglas** de cada subreddit
- [ ] **Tienes contenido valioso** (no solo promoción)

### Durante la Autopublicación

Si usas `REDDIT_ENABLED=true`:

- ✅ Empieza con 1 post/semana máximo
- ✅ Monitorea autocm.log para errores
- ✅ Revisa manualmente cada post publicado
- ✅ Responde a TODOS los comentarios
- ✅ Acepta críticas constructivamente
- ❌ NO publiques en múltiples subreddits el mismo día
- ❌ NO ignores comentarios negativos

---

## 🆘 Si Te Banean

### Shadowban (posts invisibles)

1. Verifica en: https://www.reddit.com/r/ShadowBan
2. Si estás shadowbanned:
   - Contacta admins de Reddit (no mods): https://www.reddit.com/appeals
   - Explica que no era spam intencional
   - Espera respuesta (puede tomar días)

### Ban de Subreddit

1. **NO** crear nueva cuenta (ban evasion = permanente)
2. Contacta moderadores educadamente
3. Admite error si lo cometiste
4. Pide disculpas genuinamente
5. Pregunta qué puedes hacer para ser desbaneado

### Ban de Subreddit vs Reddit

- **Subreddit ban**: Solo no puedes publicar en ese subreddit
- **Site-wide ban**: Toda tu cuenta suspendida (más grave)

---

## 📈 Mejores Horarios

Según estudios de engagement:

### Horarios Óptimos (Hora España)

- **14:00-16:00** (8-10 AM USA East Coast)
- **18:00-20:00** (12-2 PM USA East Coast)
- **00:00-02:00** (6-8 PM USA East Coast)

### Días Óptimos

- **Martes** (mejor día)
- **Miércoles** (segundo mejor)
- **Lunes** (bueno)
- Evitar: Viernes tarde, fines de semana (menos engagement B2B)

---

## ✅ Checklist Pre-Activación

Antes de cambiar `REDDIT_ENABLED=true`:

- [ ] He creado mi app de Reddit en https://www.reddit.com/prefs/apps
- [ ] He probado la conexión con script manual
- [ ] He publicado manualmente en r/test y funcionó
- [ ] He leído las reglas de mi subreddit objetivo
- [ ] Mi cuenta tiene >100 karma total
- [ ] Mi cuenta tiene >1 mes de antigüedad
- [ ] He participado en la comunidad (comentado en posts)
- [ ] Entiendo la regla 9:1
- [ ] Tengo contenido valioso preparado (no solo "visita mi web")
- [ ] Estoy preparado para responder comentarios
- [ ] Acepto el riesgo de posible ban

Si marcaste TODOS ✅, puedes activar con precaución.

Si alguno es ❌, **mejor publicar manualmente**.

---

## 🎓 Recursos de Aprendizaje

- **Guía completa**: Lee `REDDIT_SETUP.md` para detalles técnicos
- **Self-Promotion Rules**: https://www.reddit.com/wiki/selfpromotion
- **Reddiquette**: https://www.reddit.com/wiki/reddiquette
- **PRAW Docs**: https://praw.readthedocs.io/

---

## 💡 Consejo Final

> **Reddit valora autenticidad sobre todo.** Si realmente ayudas a la comunidad con contenido valioso, serás bienvenido. Si solo promocionas, serás baneado.

**Estrategia ganadora**:
1. Participa genuinamente (2 semanas)
2. Comparte tutorial/caso de estudio valioso
3. Menciona tu proyecto sutilmente
4. Responde a preguntas
5. Repite cada 1-2 semanas

**¡Éxito en Reddit!** 🚀
