"""
API simple para capturar leads desde formularios web.
Usar con Flask o FastAPI para recibir suscripciones desde xiliux.com

INSTALACIÓN:
pip install flask flask-cors

USO:
python lead_capture_api.py

Luego en tu sitio web (xiliux.com), añade este código JavaScript:
<script>
    fetch('http://tu-servidor:5000/api/subscribe', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            email: 'usuario@ejemplo.com',
            nombre: 'Nombre Usuario'
        })
    })
    .then(res => res.json())
    .then(data => console.log(data));
</script>
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import hmac
import logging
import os
from email_marketing import EmailMarketingAgent
from email_templates import get_welcome_template

app = Flask(__name__)
CORS(app)  # Permite requests desde xiliux.com

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Inicializar agente de email
email_agent = EmailMarketingAgent()


@app.route('/')
def index():
    """Página de prueba del formulario"""
    return render_template_string(FORMULARIO_HTML)


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    """
    Endpoint para recibir nuevas suscripciones.

    Espera JSON:
    {
        "email": "usuario@ejemplo.com",
        "nombre": "Nombre Usuario" (opcional)
    }
    """
    try:
        data = request.get_json()

        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'message': 'Email es requerido'
            }), 400

        email = data.get('email', '').strip().lower()
        nombre = data.get('nombre', '').strip()

        # Validación básica de email
        if '@' not in email or '.' not in email.split('@')[1]:
            return jsonify({
                'success': False,
                'message': 'Email inválido'
            }), 400

        # Obtener IP del cliente
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        # Añadir suscriptor
        success, message = email_agent.add_subscriber(
            email=email,
            nombre=nombre or None,
            fuente='web_api',
            ip=ip,
            auto_confirm=True
        )

        if success:
            # Enviar email de bienvenida
            try:
                send_welcome_email(email, nombre or "Profesional")
            except Exception as e:
                logging.warning(f"⚠️ No se pudo enviar email de bienvenida: {e}")

            return jsonify({
                'success': True,
                'message': 'Suscripción exitosa. ¡Revisa tu email!'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 409

    except Exception as e:
        logging.error(f"Error en /api/subscribe: {e}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500


@app.route('/api/unsubscribe', methods=['GET'])
def unsubscribe():
    """
    Endpoint para dar de baja usando token.
    URL: /api/unsubscribe?token=xxxxx
    """
    token = request.args.get('token')

    if not token:
        return jsonify({
            'success': False,
            'message': 'Token no proporcionado'
        }), 400

    success = email_agent.unsubscribe(token)

    if success:
        return render_template_string(UNSUBSCRIBE_SUCCESS_HTML)
    else:
        return jsonify({
            'success': False,
            'message': 'Token inválido'
        }), 404


def _verificar_clave_admin(clave_recibida):
    """Verifica la clave de administración contra `BULK_IMPORT_KEY` del entorno.

    Fail loud (directiva 20): si la clave NO está configurada, el endpoint se
    DESHABILITA con 503 en vez de caer a una clave por defecto —que estaría en el
    código fuente y por tanto no protege nada—. Devuelve una respuesta de error
    (tupla Flask) si hay que rechazar, o None si la clave es válida.
    """
    esperada = os.getenv('BULK_IMPORT_KEY')
    if not esperada:
        return jsonify({
            'success': False,
            'message': 'servicio mal configurado: falta BULK_IMPORT_KEY en el entorno'
        }), 503
    # Comparación en TIEMPO CONSTANTE: un `!=` normal corta en el primer byte
    # distinto, y midiendo el tiempo de respuesta se adivina la clave byte a byte.
    if not hmac.compare_digest(clave_recibida or '', esperada):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    return None


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Estadísticas — requiere la clave admin en la cabecera `X-API-Key`."""
    err = _verificar_clave_admin(request.headers.get('X-API-Key'))
    if err:
        return err
    stats = email_agent.get_stats()
    return jsonify(stats)


@app.route('/api/bulk_import', methods=['POST'])
def bulk_import():
    """
    Endpoint para importar múltiples emails.
    Requiere autenticación (implementar según necesidad).

    Espera JSON:
    {
        "api_key": "tu_clave_secreta",
        "emails": [
            {"email": "user1@example.com", "nombre": "User 1"},
            {"email": "user2@example.com", "nombre": "User 2"}
        ],
        "fuente": "manual_import"
    }
    """
    try:
        data = request.get_json()

        # Verificar API key. Fail loud si no está configurada (ver helper).
        err = _verificar_clave_admin(data.get('api_key'))
        if err:
            return err

        emails = data.get('emails', [])
        fuente = data.get('fuente', 'bulk_import')

        # Convertir a formato esperado
        emails_list = [(e['email'], e.get('nombre')) for e in emails]

        stats = email_agent.bulk_add_subscribers(emails_list, fuente)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logging.error(f"Error en bulk_import: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


def send_welcome_email(email, nombre):
    """Envía email de bienvenida a nuevo suscriptor"""
    # Obtener token de unsubscribe
    import sqlite3
    db = sqlite3.connect(email_agent.db_path)
    cursor = db.cursor()
    token = cursor.execute(
        "SELECT token_unsub FROM contacts WHERE email=?",
        (email,)
    ).fetchone()[0]
    db.close()

    unsub_link = f"{email_agent.base_url}/api/unsubscribe?token={token}"
    html = get_welcome_template(nombre, unsub_link)

    # Enviar usando el agente
    email_agent._send_individual_email(
        email=email,
        nombre=nombre,
        asunto="¡Bienvenido a Xiliux! 🚀",
        copy=html,
        unsub_token=token,
        img_data=None
    )


# HTML del formulario de prueba
FORMULARIO_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Suscribirse a Xiliux</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            max-width: 450px;
            width: 100%;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
        p { color: #666; margin-bottom: 30px; line-height: 1.6; }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
            font-size: 14px;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 15px;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:active { transform: translateY(0); }
        .message {
            margin-top: 20px;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Suscríbete a Xiliux</h1>
        <p>Recibe novedades sobre LegalTech, desarrollo Python y nuestros productos.</p>

        <form id="subscribeForm">
            <div class="form-group">
                <label for="nombre">Nombre</label>
                <input type="text" id="nombre" name="nombre" placeholder="Tu nombre">
            </div>
            <div class="form-group">
                <label for="email">Email *</label>
                <input type="email" id="email" name="email" required placeholder="tu@email.com">
            </div>
            <button type="submit">Suscribirme 🚀</button>
        </form>

        <div id="message" class="message"></div>
    </div>

    <script>
        document.getElementById('subscribeForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const nombre = document.getElementById('nombre').value;
            const email = document.getElementById('email').value;
            const messageDiv = document.getElementById('message');

            try {
                const response = await fetch('/api/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, nombre })
                });

                const data = await response.json();

                messageDiv.style.display = 'block';
                if (data.success) {
                    messageDiv.className = 'message success';
                    messageDiv.textContent = '✅ ' + data.message;
                    document.getElementById('subscribeForm').reset();
                } else {
                    messageDiv.className = 'message error';
                    messageDiv.textContent = '❌ ' + data.message;
                }
            } catch (error) {
                messageDiv.style.display = 'block';
                messageDiv.className = 'message error';
                messageDiv.textContent = '❌ Error al conectar con el servidor';
            }
        });
    </script>
</body>
</html>
"""

UNSUBSCRIBE_SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baja exitosa - Xiliux</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f4f4;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .box {
            background: white;
            padding: 40px;
            border-radius: 8px;
            text-align: center;
            max-width: 500px;
        }
        h1 { color: #333; }
        p { color: #666; line-height: 1.6; }
        a { color: #667eea; text-decoration: none; }
    </style>
</head>
<body>
    <div class="box">
        <h1>✅ Baja exitosa</h1>
        <p>Has sido dado de baja de la lista de correo de Xiliux.</p>
        <p>Siempre puedes volver a suscribirte en <a href="https://www.xiliux.com">www.xiliux.com</a></p>
    </div>
</body>
</html>
"""


if __name__ == '__main__':
    print("🚀 API de captura de leads iniciada")
    print("📍 Formulario de prueba: http://localhost:5000")
    print("📡 Endpoint de suscripción: http://localhost:5000/api/subscribe")
    print("📊 Estadísticas: http://localhost:5000/api/stats")
    print()

    # Puerto configurable
    port = int(os.getenv('API_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
