# 🚀 Inicio Rápido - Email Marketing

## Pasos para empezar a captar emails HOY

### 1️⃣ Instalar dependencias (2 minutos)

```bash
cd /mnt/data/autocm
pip install flask flask-cors jinja2
```

### 2️⃣ Configurar Gmail para SMTP (5 minutos)

1. Ve a tu cuenta de Google → **Seguridad**
2. Activa **Verificación en 2 pasos** (si no está activada)
3. Ve a **Contraseñas de aplicaciones**: https://myaccount.google.com/apppasswords
4. Crea una contraseña para "Correo"
5. Copia la contraseña de 16 caracteres

### 3️⃣ Actualizar tu .env (2 minutos)

Añade estas líneas a tu archivo `.env`:

```bash
# Email Marketing
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # La contraseña de app de Google
FROM_EMAIL=noreply@xiliux.com
FROM_NAME=Xiliux
BASE_URL=https://www.xiliux.com
PREVIEW_EMAIL=tu-email@gmail.com  # Para pruebas
```

### 4️⃣ Probar el sistema (5 minutos)

**A) Añadir tu primer suscriptor**:

```bash
python -c "
from email_marketing import EmailMarketingAgent
agent = EmailMarketingAgent()
agent.add_subscriber('tu-email@gmail.com', 'Tu Nombre', 'prueba_inicial')
print('✅ Suscriptor añadido')
"
```

**B) Enviar email de prueba**:

```bash
python -c "
from email_marketing import EmailMarketingAgent
agent = EmailMarketingAgent()
agent.send_campaign(
    asunto='🚀 Prueba de Email Marketing Xiliux',
    copy='Este es un email de prueba del nuevo sistema de email marketing. Si recibes esto, ¡todo funciona correctamente! #Python #Rust',
    preview_mode=True
)
print('✅ Email enviado')
"
```

**C) Verificar que llegó** a tu bandeja de entrada.

### 5️⃣ Iniciar el sistema completo (1 minuto)

```bash
python main.py
```

Ahora el agente:
- Publicará en redes sociales 3 veces al día (09:15, 13:30, 19:45)
- Enviará email marketing los LUNES a todos tus suscriptores

---

## 📝 Cómo captar tus primeros 10-100 emails

### Opción A: Manual (Para comenzar)

1. **Contactos existentes**: ¿Tienes clientes/colegas que podrían estar interesados?

```python
from email_marketing import EmailMarketingAgent
agent = EmailMarketingAgent()

# Añadir uno por uno
agent.add_subscriber('cliente1@empresa.com', 'Cliente Uno', 'contactos_existentes')
agent.add_subscriber('colega@bufete.com', 'Colega Abogado', 'contactos_existentes')
```

2. **Desde CSV**: Si tienes una hoja de Excel/CSV con contactos:

```python
import csv
from email_marketing import EmailMarketingAgent

agent = EmailMarketingAgent()

# Crear CSV: contactos.csv
# email,nombre
# user1@example.com,Usuario 1
# user2@example.com,Usuario 2

with open('contactos.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Saltar encabezado
    for row in reader:
        agent.add_subscriber(row[0], row[1], 'importacion_inicial')
```

### Opción B: Formulario Web (Automático)

1. **Iniciar la API de captura**:

```bash
python lead_capture_api.py
```

2. **Probar el formulario**: Ve a http://localhost:5000 y suscríbete

3. **Integrar en xiliux.com**: Añade este código a tu web:

```html
<form id="subscribeForm" style="padding: 20px; background: #f0f0f0; border-radius: 8px;">
    <h3>📧 Suscríbete a Xiliux</h3>
    <input type="email" id="email" placeholder="tu@email.com" required
           style="padding: 10px; margin: 5px; width: 250px;">
    <input type="text" id="nombre" placeholder="Tu nombre (opcional)"
           style="padding: 10px; margin: 5px; width: 250px;">
    <button type="submit" style="padding: 10px 20px; background: #667eea; color: white; border: none; cursor: pointer;">
        Suscribirse 🚀
    </button>
    <div id="message" style="margin-top: 10px; font-weight: bold;"></div>
</form>

<script>
document.getElementById('subscribeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const nombre = document.getElementById('nombre').value;

    try {
        const res = await fetch('http://TU-SERVIDOR-IP:5000/api/subscribe', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email, nombre })
        });
        const data = await res.json();
        document.getElementById('message').textContent = data.success ?
            '✅ ' + data.message : '❌ ' + data.message;
        if(data.success) document.getElementById('subscribeForm').reset();
    } catch (error) {
        document.getElementById('message').textContent = '❌ Error al conectar';
    }
});
</script>
```

---

## 🎯 Estrategias para conseguir emails LEGALMENTE

### Inmediatas (Esta semana)

1. **Firma de email personal**: Añade en tu firma:
   ```
   ---
   📧 ¿Te interesa LegalTech y desarrollo Python?
   Suscríbete: https://www.xiliux.com/newsletter
   ```

2. **Posts en redes**: Menciona en Twitter/Mastodon:
   ```
   "Acabo de lanzar mi newsletter semanal sobre LegalTech y Python.
   Suscríbete aquí: [link] 🚀"
   ```

3. **LinkedIn**: Publica un artículo sobre un tema y al final:
   ```
   "¿Quieres recibir más contenido como este?
   Suscríbete a mi newsletter semanal en [link]"
   ```

### Corto plazo (Este mes)

4. **Lead Magnet**: Crea un PDF simple (5-10 páginas):
   - "5 Automatizaciones Python para Abogados"
   - "Checklist: Cumplimiento RGPD en tu despacho"
   - "Guía: Tu primera app con NiceGUI"

   Ofrécelo a cambio del email.

5. **Popup en xiliux.com**: Implementa popup de salida (exit-intent):
   ```
   "¡Espera! 🎁
   Descarga GRATIS: Guía de Python para Abogados
   [Tu email] [Descargar]"
   ```

6. **Banner superior**: Banner fijo arriba de xiliux.com:
   ```
   "📬 Newsletter semanal: LegalTech + Python → [Email] [Suscribir]"
   ```

### Medio plazo (Próximos 3 meses)

7. **Blog con SEO**: Escribe artículos útiles:
   - "Cómo automatizar contratos con Python"
   - "NiceGUI vs Streamlit: Comparativa"
   - "RGPD: Guía técnica para desarrolladores"

   Al final: botón de suscripción.

8. **Webinar gratuito**: Organiza un webinar:
   - "Automatiza tu despacho legal con Python (Gratis)"
   - Registro requiere email
   - Post-webinar: "Recibe próximos webinars por email"

9. **YouTube**: Crea tutoriales:
   - En descripción: "Suscríbete a la newsletter: [link]"
   - Mención en video: "Link en descripción"

---

## 📊 Monitoreo y Crecimiento

### Ver estadísticas

```bash
# Opción 1: Python
python -c "from email_marketing import EmailMarketingAgent; print(EmailMarketingAgent().get_stats())"

# Opción 2: API (si está corriendo)
curl http://localhost:5000/api/stats
```

### Exportar contactos

```bash
python -c "
from email_marketing import EmailMarketingAgent
agent = EmailMarketingAgent()
agent.export_contacts('backup_contactos.csv')
print('✅ Exportado')
"
```

### Objetivos realistas

| Plazo | Meta | Estrategia |
|-------|------|------------|
| Semana 1 | 10 emails | Contactos directos + firma email |
| Mes 1 | 50 emails | + Popup web + posts en redes |
| Mes 3 | 200 emails | + Blog SEO + Lead magnet |
| Mes 6 | 500 emails | + Webinars + YouTube |
| Año 1 | 1000+ emails | + Ads pagados + Referidos |

---

## ⚠️ IMPORTANTE: Cumplimiento Legal

### Checklist RGPD

- [ ] Solo añadir emails con consentimiento explícito
- [ ] Tener política de privacidad en xiliux.com
- [ ] Link de "unsubscribe" en todos los emails (✅ ya incluido)
- [ ] Procesar bajas inmediatamente (✅ automatizado)
- [ ] NO comprar listas de emails
- [ ] Guardar evidencia de consentimiento

### En tus formularios web

Siempre incluir:
```html
<label>
  <input type="checkbox" required>
  Acepto recibir emails de Xiliux según la
  <a href="/privacidad">Política de Privacidad</a>
</label>
```

---

## 🔧 Troubleshooting Rápido

**"Gmail rechaza el envío"**
→ Verifica que usas contraseña de aplicación, NO tu contraseña normal

**"Emails van a spam"**
→ Normal al principio. Pide a suscriptores añadir a contactos.
→ Considera SendGrid (100 emails/día gratis) para mejor deliverability

**"Error al conectar a base de datos"**
→ `rm subscribers.db` y ejecuta de nuevo (crea nueva DB)

**"No recibo el email de prueba"**
→ Revisa carpeta de spam
→ Verifica SMTP_USER y SMTP_PASSWORD en .env

---

## 📚 Documentación Completa

- `EMAIL_MARKETING_README.md` - Guía técnica completa
- `ESTRATEGIAS_CAPTACION_EMAILS.md` - Estrategias avanzadas (100+ ideas)
- `.env.example` - Template de configuración
- `add_subscribers_example.py` - Scripts de ejemplo

---

## ✅ Resumen: 3 Acciones AHORA

1. **Configura SMTP** (copia credenciales a .env)
2. **Añade tus primeros 5 emails** (amigos, colegas, tú mismo)
3. **Envía tu primera campaña de prueba** (preview_mode=True)

**¡Listo! Ya tienes email marketing funcionando.** 🎉

El siguiente paso es añadir el formulario a xiliux.com y empezar a crecer tu lista orgánicamente.
