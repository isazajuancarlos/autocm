import sqlite3
import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from jinja2 import Template
from dotenv import load_dotenv

load_dotenv()

class EmailMarketingAgent:
    """
    Agente de Email Marketing que gestiona suscriptores y envía campañas.
    Incluye tracking de aperturas, gestión de bajas y cumplimiento legal.
    """

    def __init__(self, db_path='subscribers.db'):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.init_db()

        # Configuración SMTP
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "Xiliux")

        # URL base para links de unsubscribe
        self.base_url = os.getenv("BASE_URL", "https://www.xiliux.com")

        logging.info(f"📧 EmailMarketingAgent inicializado (DB: {db_path})")

    def init_db(self):
        """Crea las tablas necesarias si no existen"""
        cursor = self.db.cursor()

        # Tabla de contactos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nombre TEXT,
                fecha_suscripcion DATETIME DEFAULT CURRENT_TIMESTAMP,
                fuente TEXT,
                activo BOOLEAN DEFAULT 1,
                token_unsub TEXT UNIQUE,
                ip_suscripcion TEXT,
                confirmado BOOLEAN DEFAULT 0
            )
        ''')

        # Tabla de campañas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                asunto TEXT NOT NULL,
                copy TEXT,
                enviados INTEGER DEFAULT 0,
                errores INTEGER DEFAULT 0
            )
        ''')

        # Tabla de interacciones (para tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                campaign_id INTEGER,
                accion TEXT,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
            )
        ''')

        self.db.commit()
        logging.info("✅ Tablas de base de datos verificadas/creadas")

    def generate_unsub_token(self, email):
        """Genera un token único para unsubscribe"""
        import hashlib
        import time
        token = hashlib.sha256(f"{email}{time.time()}".encode()).hexdigest()[:32]
        return token

    def add_subscriber(self, email, nombre=None, fuente='web', ip=None, auto_confirm=True):
        """
        Añade un nuevo suscriptor a la base de datos.

        Args:
            email: Dirección de email
            nombre: Nombre del suscriptor (opcional)
            fuente: De dónde viene (web, manual, api, etc.)
            ip: IP desde donde se suscribió
            auto_confirm: Si True, marca como confirmado automáticamente

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            cursor = self.db.cursor()
            token = self.generate_unsub_token(email)

            cursor.execute('''
                INSERT INTO contacts (email, nombre, fuente, token_unsub, ip_suscripcion, confirmado)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, nombre, fuente, token, ip, 1 if auto_confirm else 0))

            self.db.commit()
            logging.info(f"✅ Nuevo suscriptor: {email} (fuente: {fuente})")
            return True, "Suscripción exitosa"

        except sqlite3.IntegrityError:
            logging.warning(f"⚠️ Email ya existe: {email}")
            return False, "Email ya registrado"
        except Exception as e:
            logging.error(f"❌ Error al añadir suscriptor {email}: {e}")
            return False, f"Error: {str(e)}"

    def bulk_add_subscribers(self, emails_list, fuente='bulk_import'):
        """
        Añade múltiples suscriptores de una vez.

        Args:
            emails_list: Lista de tuplas (email, nombre) o solo emails
            fuente: Origen de la lista

        Returns:
            dict: Estadísticas de importación
        """
        stats = {'added': 0, 'duplicates': 0, 'errors': 0}

        for item in emails_list:
            if isinstance(item, tuple):
                email, nombre = item
            else:
                email, nombre = item, None

            success, msg = self.add_subscriber(email, nombre, fuente)
            if success:
                stats['added'] += 1
            elif 'ya registrado' in msg:
                stats['duplicates'] += 1
            else:
                stats['errors'] += 1

        logging.info(f"📊 Importación: {stats['added']} añadidos, {stats['duplicates']} duplicados, {stats['errors']} errores")
        return stats

    def unsubscribe(self, token):
        """Dar de baja a un suscriptor usando su token"""
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE contacts SET activo=0 WHERE token_unsub=?",
            (token,)
        )
        self.db.commit()

        if cursor.rowcount > 0:
            logging.info(f"👋 Usuario dado de baja (token: {token[:8]}...)")
            return True
        return False

    def get_active_subscribers(self):
        """Obtiene lista de suscriptores activos y confirmados"""
        cursor = self.db.cursor()
        subscribers = cursor.execute('''
            SELECT id, email, nombre, token_unsub
            FROM contacts
            WHERE activo=1 AND confirmado=1
        ''').fetchall()
        return subscribers

    def get_stats(self):
        """Obtiene estadísticas de la base de datos"""
        cursor = self.db.cursor()

        total = cursor.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        activos = cursor.execute("SELECT COUNT(*) FROM contacts WHERE activo=1").fetchone()[0]
        confirmados = cursor.execute("SELECT COUNT(*) FROM contacts WHERE confirmado=1").fetchone()[0]
        campaigns = cursor.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]

        # Fuentes de suscriptores
        fuentes = cursor.execute('''
            SELECT fuente, COUNT(*) as count
            FROM contacts
            GROUP BY fuente
        ''').fetchall()

        return {
            'total_contactos': total,
            'activos': activos,
            'confirmados': confirmados,
            'total_campañas': campaigns,
            'fuentes': dict(fuentes)
        }

    def create_campaign(self, asunto, copy):
        """Crea un registro de campaña y devuelve su ID"""
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO campaigns (asunto, copy)
            VALUES (?, ?)
        ''', (asunto, copy))
        self.db.commit()
        return cursor.lastrowid

    def send_campaign(self, asunto, copy, preview_mode=False):
        """
        Envía una campaña de email a todos los suscriptores activos.

        Args:
            asunto: Asunto del email
            copy: Contenido del mensaje
            preview_mode: Si True, solo envía a un email de prueba

        Returns:
            dict: Estadísticas de envío
        """
        if not self.smtp_user or not self.smtp_password:
            logging.error("❌ Credenciales SMTP no configuradas")
            return {'enviados': 0, 'errores': 1, 'mensaje': 'Sin credenciales SMTP'}

        # Crear registro de campaña
        campaign_id = self.create_campaign(asunto, copy)

        # Obtener suscriptores
        if preview_mode:
            # En modo preview, solo envía al email configurado
            subscribers = [(0, os.getenv("PREVIEW_EMAIL", self.smtp_user), "Preview", "preview-token")]
            logging.info("📧 MODO PREVIEW: Enviando solo a email de prueba")
        else:
            subscribers = self.get_active_subscribers()

        stats = {'enviados': 0, 'errores': 0}

        # Enviar a cada suscriptor
        for sub_id, email, nombre, token in subscribers:
            success = self._send_individual_email(
                email=email,
                nombre=nombre or "Profesional",
                asunto=asunto,
                copy=copy,
                unsub_token=token,
                campaign_id=campaign_id
            )

            if success:
                stats['enviados'] += 1
            else:
                stats['errores'] += 1

        # Actualizar estadísticas de la campaña
        cursor = self.db.cursor()
        cursor.execute('''
            UPDATE campaigns
            SET enviados=?, errores=?
            WHERE id=?
        ''', (stats['enviados'], stats['errores'], campaign_id))
        self.db.commit()

        logging.info(f"📊 Campaña #{campaign_id}: {stats['enviados']} enviados, {stats['errores']} errores")
        return stats

    def _send_individual_email(self, email, nombre, asunto, copy, unsub_token, campaign_id=None):
        """Envía un email individual"""
        try:
            # Crear mensaje
            msg = MIMEMultipart('related')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = email
            msg['Subject'] = asunto

            # Link de baja
            unsub_link = f"{self.base_url}/unsubscribe?token={unsub_token}"

            # Template HTML (importado desde email_templates)
            from email_templates import get_campaign_template
            html_content = get_campaign_template(nombre, copy, unsub_link)

            # Adjuntar HTML
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)

            # Texto plano (fallback)
            text_part = MIMEText(f"{copy}\n\nBaja: {unsub_link}", 'plain', 'utf-8')
            msg_alternative.attach(text_part)

            # HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg_alternative.attach(html_part)

            # Enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            # Registrar interacción
            if campaign_id:
                cursor = self.db.cursor()
                cursor.execute('''
                    INSERT INTO interactions (email, campaign_id, accion)
                    VALUES (?, ?, 'sent')
                ''', (email, campaign_id))
                self.db.commit()

            return True

        except Exception as e:
            logging.error(f"❌ Error enviando a {email}: {e}")
            return False

    def export_contacts(self, filename='contacts_export.csv', only_active=True):
        """Exporta contactos a CSV"""
        import csv
        cursor = self.db.cursor()

        query = "SELECT email, nombre, fecha_suscripcion, fuente, activo FROM contacts"
        if only_active:
            query += " WHERE activo=1"

        contacts = cursor.execute(query).fetchall()

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Email', 'Nombre', 'Fecha Suscripción', 'Fuente', 'Activo'])
            writer.writerows(contacts)

        logging.info(f"📥 {len(contacts)} contactos exportados a {filename}")
        return filename

    def close(self):
        """Cierra la conexión a la base de datos"""
        self.db.close()


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)

    agent = EmailMarketingAgent()

    # Mostrar estadísticas
    stats = agent.get_stats()
    print("\n📊 Estadísticas de Email Marketing:")
    print(f"Total contactos: {stats['total_contactos']}")
    print(f"Activos: {stats['activos']}")
    print(f"Confirmados: {stats['confirmados']}")
    print(f"Campañas enviadas: {stats['total_campañas']}")
    print(f"Fuentes: {stats['fuentes']}")

    agent.close()
