import os
import time
import random
import logging
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from openai import OpenAI
from mastodon import Mastodon
import tweepy
from atproto import Client as BlueskyClient
import schedule
from email_marketing import EmailMarketingAgent
import praw

# --- CONFIGURACIÓN ---
load_dotenv()

# LinkedIn versiona su API por mes y exige la cabecera en cada llamada. Las
# versiones se retiran a los ~12 meses, así que esto caduca: si LinkedIn empieza
# a devolver 426, sube el valor.
LINKEDIN_VERSION = os.getenv("LINKEDIN_VERSION", "202606")

logging.basicConfig(
    filename='autocm.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- DEFINICIÓN DE ZONAS ---
ZONES = {
    "SERVICES": {
        "name": "Servicios de desarrollo en Python",
        "url": os.getenv("TARGET_URL", "https://www.xiliux.com"),
        "scroll_y": 2600,
        "focus": "dev"
    },
    "PROJECTS": {
        "name": "Escaparate de Productos (Dinámico)",
        "url": os.getenv("TARGET_URL", "https://www.xiliux.com"),
        "scroll_y": 1200,
        "focus": "products"
    }
}

class XiliuxAgent:
    def __init__(self):
        self.extracted_text = ""
        # Sin `www`: el canónico es xiliux.com y www devuelve 301 (medido el
        # 2026-08-02). Publicar el que redirige gasta un salto en cada enlace y
        # reparte la señal entre dos direcciones.
        self.main_link = "https://xiliux.com"

        self.clients = {
            "openai": None,
            "mastodon": None,
            "twitter_api": None,
            "twitter_client": None,
            "bluesky": None,
            "email": None,
            "reddit": None
        }

        # Contador para ciclos (para enviar emails periódicamente)
        self.cycle_count = 0

        # Credenciales API puras
        self.tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.li_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.li_org_id = os.getenv("LINKEDIN_ORG_ID")
        # Autor de las publicaciones de LinkedIn. "organization" publica como la
        # página Xillux (exige la Community Management API, hoy denegada);
        # "person" publica como el perfil de Juan Carlos Isaza (scope
        # w_member_social, disponible sin aprobación). El perfil es DUAL a
        # propósito (Rust Engineer + Lawyer), así que sale contenido de Xiliux
        # desde él sin cruzar identidades; el contenido sigue siendo solo de
        # software, nunca jurídico. Se vuelve a "organization" cambiando esta
        # variable cuando LinkedIn apruebe la API de página.
        self.li_author_mode = os.getenv("LINKEDIN_AUTHOR_MODE", "organization").strip().lower()
        self.li_person_sub = os.getenv("LINKEDIN_PERSON_SUB")  # 'sub' de OpenID (modo person)
        self.discord_url = os.getenv("DISCORD_WEBHOOK_URL")

        # Facebook configuration
        self.fb_page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.fb_page_id = os.getenv("FACEBOOK_PAGE_ID")

        # --- CANALES HABILITADOS (fuente única) ------------------------------
        # Antes cada canal publicaba con solo encontrar credenciales, sin que
        # nadie lo decidiera. Ahora todo canal tiene interruptor explícito.
        #
        #   twitter / bluesky  -> cuentas PERSONALES (@isazajuancarlos). AutoCM
        #       es el altavoz de Xiliux, no de Juan Carlos. Publicar marketing
        #       de marca desde su handle funde las dos identidades. OFF.
        #   facebook           -> público equivocado para herramientas de dev. OFF.
        #   reddit             -> la autopromoción automatizada acaba en baneo. OFF.
        #   telegram / discord -> canales propios: son notificación, no difusión.
        #   linkedin           -> autor según LINKEDIN_AUTHOR_MODE: "organization"
        #       (página Xillux, Community Management API) o "person" (perfil DUAL
        #       de JC Isaza, w_member_social). Publica contenido de software; el
        #       perfil ya integra Rust+Lawyer, y el contenido nunca es jurídico.
        def _switch(name, default):
            return os.getenv(f"{name}_ENABLED", default).lower() == "true"

        self.enabled = {
            "mastodon": _switch("MASTODON", "true"),
            "twitter":  _switch("TWITTER",  "false"),
            "bluesky":  _switch("BLUESKY",  "false"),
            "telegram": _switch("TELEGRAM", "true"),
            "discord":  _switch("DISCORD",  "true"),
            "linkedin": _switch("LINKEDIN", "true"),
            "reddit":   _switch("REDDIT",   "false"),
            "facebook": _switch("FACEBOOK", "false"),
            "email":    _switch("EMAIL",    "true"),
        }

        # Reddit configuration
        self.reddit_subreddit = os.getenv("REDDIT_SUBREDDIT", "test")  # Subreddit donde publicar
        self.reddit_enabled = self.enabled["reddit"]
        
        # AutoCM habla por XILIUX (software), nunca por la práctica jurídica de
        # Juan Carlos Isaza. Nada de "abogado", "legaltech" ni cumplimiento aquí:
        # mezclar las dos identidades es justo lo que hay que evitar.
        self.backup_copies = [
            f"🔐 Quipu: criptografía post-cuántica de código abierto en Rust — ML-KEM-1024 y ML-DSA-87.\n\n🔗 {self.main_link} #Rust #Cryptography",
            f"🚀 Desarrollo en Python: MVPs, integración de LLMs y automatización a medida.\n\n🔗 {self.main_link} #Python #Dev",
            f"⚡ Automatización con NiceGUI e IA. Mira los desarrollos.\n\n🔗 {self.main_link} #Python #NiceGUI"
        ]
        
        # --- INICIALIZACIÓN TOLERANTE A FALLOS ---
        try:
            self.clients["openai"] = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            logging.error(f"⚠️ OpenAI Error: {e}")

        # Mastodon configuration
        self.mastodon_enabled = self.enabled["mastodon"]

        # El interruptor decide si se PUBLICA, no si se comprueba. Antes el
        # cliente solo se creaba con la bandera en true, así que un canal apagado
        # no se podía verificar: no había forma de saber si una credencial nueva
        # servía sin encender la publicación primero. Bluesky, Facebook y Discord
        # ya se verificaban apagados; Mastodon y Reddit eran la excepción.
        # Publicar sigue cerrado: lo cierran `publish_mastodon` y `run_cycle`.
        try:
            token = os.getenv("MASTODON_ACCESS_TOKEN")
            url = os.getenv("MASTODON_API_URL")
            if token and not url:
                # Nada de caer a mastodon.social: un token de otra instancia
                # contra el servidor equivocado falla sin decir por qué, y con
                # suerte publica donde nadie quería (directiva 20).
                raise ValueError("hay MASTODON_ACCESS_TOKEN pero falta MASTODON_API_URL")
            if token:
                self.clients["mastodon"] = Mastodon(access_token=token, api_base_url=url)
            else:
                logging.warning("⚠️ Mastodon omitido (Faltan credenciales)")
        except Exception as e:
            logging.error(f"⚠️ Mastodon Error: {e}")

        try:
            self.clients["twitter_client"] = tweepy.Client(
                consumer_key=os.getenv("TWITTER_API_KEY"),
                consumer_secret=os.getenv("TWITTER_API_SECRET"),
                access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
            )
            auth = tweepy.OAuth1UserHandler(
                os.getenv("TWITTER_API_KEY"),
                os.getenv("TWITTER_API_SECRET"),
                os.getenv("TWITTER_ACCESS_TOKEN"),
                os.getenv("TWITTER_ACCESS_SECRET")
            )
            self.clients["twitter_api"] = tweepy.API(auth)
        except Exception as e:
            logging.error(f"⚠️ Twitter Error: {e}")

        try:
            bs_handle = os.getenv("BLUESKY_HANDLE")
            bs_password = os.getenv("BLUESKY_PASSWORD")
            if bs_handle and bs_password:
                bs = BlueskyClient()
                bs.login(bs_handle, bs_password)
                self.clients["bluesky"] = bs
                logging.info("🔹 Bluesky Conectado.")
            else:
                logging.warning("⚠️ Bluesky omitido (Faltan credenciales).")
        except Exception as e:
            logging.error(f"⚠️ Bluesky Error: {e}")
            self.clients["bluesky"] = None

        try:
            if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
                self.clients["email"] = EmailMarketingAgent()
                logging.info("📧 Email Marketing Activado.")
            else:
                logging.warning("⚠️ Email Marketing omitido (Faltan credenciales SMTP).")
        except Exception as e:
            logging.error(f"⚠️ Email Marketing Error: {e}")
            self.clients["email"] = None

        try:
            reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
            reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            reddit_username = os.getenv("REDDIT_USERNAME")
            reddit_password = os.getenv("REDDIT_PASSWORD")

            # Sin `and self.reddit_enabled`, por la misma razón que en Mastodon:
            # crear el cliente es poder comprobarlo, no poder publicar. Lo que
            # impide publicar es `publish_reddit` y la puerta de `run_cycle`.
            if all([reddit_client_id, reddit_client_secret, reddit_username, reddit_password]):
                self.clients["reddit"] = praw.Reddit(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    username=reddit_username,
                    password=reddit_password,
                    user_agent=f"python:xiliux-autocm:v1.0 (by /u/{reddit_username})"
                )
                logging.info(f"🔴 Reddit Conectado (publicará en r/{self.reddit_subreddit}).")
            else:
                if not self.reddit_enabled:
                    logging.info("ℹ️ Reddit desactivado (REDDIT_ENABLED=false)")
                else:
                    logging.warning("⚠️ Reddit omitido (Faltan credenciales o REDDIT_ENABLED).")
        except Exception as e:
            logging.error(f"⚠️ Reddit Error: {e}")
            self.clients["reddit"] = None

        logging.info("✅ Agente Xiliux Inicializado (Discord + Email + Reddit).")

    def verify_accounts(self) -> dict:
        """
        Verifica el estado de todas las cuentas antes de publicar.
        Retorna un diccionario con el estado de cada plataforma.
        """
        logging.info("=" * 60)
        logging.info("🔍 VERIFICACIÓN DE CUENTAS - Inicio")
        logging.info("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "platforms": {}
        }

        # --- FACEBOOK ---
        fb_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.fb_page_token and self.fb_page_id:
            fb_status["configured"] = True
            try:
                url = f"https://graph.facebook.com/v18.0/me?fields=id,name,access_token&access_token={self.fb_page_token}"
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    fb_status["valid"] = True
                    fb_status["details"] = {"page_name": data.get("name"), "page_id": data.get("id")}
                    fb_status["message"] = f"Token válido - Página: {data.get('name')}"
                    logging.info(f"✅ [Facebook] Token válido - Página: {data.get('name')} (ID: {data.get('id')})")
                else:
                    error_data = res.json().get("error", {})
                    fb_status["message"] = f"Token inválido: {error_data.get('message', res.text)}"
                    fb_status["details"] = {"error_code": error_data.get("code"), "error_type": error_data.get("type")}
                    logging.error(f"❌ [Facebook] Token inválido: {error_data.get('message', res.text)}")
            except Exception as e:
                fb_status["message"] = f"Error de conexión: {str(e)}"
                logging.error(f"❌ [Facebook] Error verificando: {e}")
        else:
            fb_status["message"] = "No configurado (faltan FACEBOOK_PAGE_ACCESS_TOKEN o FACEBOOK_PAGE_ID)"
            logging.warning("⚠️ [Facebook] No configurado")
        results["platforms"]["facebook"] = fb_status

        # --- TWITTER/X ---
        tw_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.clients["twitter_client"]:
            tw_status["configured"] = True
            try:
                user = self.clients["twitter_client"].get_me()
                if user and user.data:
                    tw_status["valid"] = True
                    tw_status["details"] = {"username": user.data.username, "id": user.data.id}
                    tw_status["message"] = f"Conectado como @{user.data.username}"
                    logging.info(f"✅ [Twitter/X] Conectado como @{user.data.username}")
                else:
                    tw_status["message"] = "No se pudo obtener información del usuario"
                    logging.error("❌ [Twitter/X] No se pudo verificar usuario")
            except Exception as e:
                tw_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [Twitter/X] Error verificando: {e}")
        else:
            tw_status["message"] = "No configurado"
            logging.warning("⚠️ [Twitter/X] No configurado")
        results["platforms"]["twitter"] = tw_status

        # --- MASTODON ---
        mast_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.clients["mastodon"]:
            mast_status["configured"] = True
            try:
                account = self.clients["mastodon"].account_verify_credentials()
                if account:
                    mast_status["valid"] = True
                    mast_status["details"] = {"username": account.username, "display_name": account.display_name}
                    mast_status["message"] = f"Conectado como @{account.username}"
                    logging.info(f"✅ [Mastodon] Conectado como @{account.username}")
                else:
                    mast_status["message"] = "No se pudo verificar cuenta"
                    logging.error("❌ [Mastodon] No se pudo verificar")
            except Exception as e:
                mast_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [Mastodon] Error verificando: {e}")
        else:
            mast_status["message"] = "Desactivado (MASTODON_ENABLED=false)" if not self.mastodon_enabled else "No configurado"
            logging.warning(f"⚠️ [Mastodon] {'Desactivado' if not self.mastodon_enabled else 'No configurado'}")
        results["platforms"]["mastodon"] = mast_status

        # --- TELEGRAM ---
        tg_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.tg_token:
            tg_status["configured"] = True
            try:
                url = f"https://api.telegram.org/bot{self.tg_token}/getMe"
                res = requests.get(url, timeout=10)
                if res.status_code == 200 and res.json().get("ok"):
                    bot_info = res.json().get("result", {})
                    tg_status["valid"] = True
                    tg_status["details"] = {"bot_name": bot_info.get("first_name"), "username": bot_info.get("username")}
                    tg_status["message"] = f"Bot válido: @{bot_info.get('username')}"
                    logging.info(f"✅ [Telegram] Bot válido: @{bot_info.get('username')}")
                else:
                    tg_status["message"] = "Token de bot inválido"
                    logging.error("❌ [Telegram] Token inválido")
            except Exception as e:
                tg_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [Telegram] Error verificando: {e}")
        else:
            tg_status["message"] = "No configurado"
            logging.warning("⚠️ [Telegram] No configurado")
        results["platforms"]["telegram"] = tg_status

        # --- BLUESKY ---
        bs_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.clients["bluesky"]:
            bs_status["configured"] = True
            bs_status["valid"] = True  # Ya se verificó durante login en __init__
            try:
                profile = self.clients["bluesky"].me
                bs_status["details"] = {"handle": profile.handle if profile else "unknown"}
                bs_status["message"] = f"Conectado como @{profile.handle}" if profile else "Conectado"
                logging.info(f"✅ [Bluesky] Conectado como @{profile.handle if profile else 'unknown'}")
            except Exception:
                bs_status["message"] = "Conectado (login exitoso)"
                logging.info("✅ [Bluesky] Conectado")
        else:
            bs_status["message"] = "No configurado"
            logging.warning("⚠️ [Bluesky] No configurado")
        results["platforms"]["bluesky"] = bs_status

        # --- DISCORD ---
        dc_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.discord_url:
            dc_status["configured"] = True
            try:
                # Discord webhooks no tienen endpoint de verificación, pero podemos validar el formato
                if "discord.com/api/webhooks/" in self.discord_url:
                    # Intentar obtener info del webhook (GET request)
                    res = requests.get(self.discord_url, timeout=10)
                    if res.status_code == 200:
                        webhook_info = res.json()
                        dc_status["valid"] = True
                        dc_status["details"] = {"name": webhook_info.get("name"), "channel_id": webhook_info.get("channel_id")}
                        dc_status["message"] = f"Webhook válido: {webhook_info.get('name')}"
                        logging.info(f"✅ [Discord] Webhook válido: {webhook_info.get('name')}")
                    else:
                        dc_status["message"] = "Webhook inválido o eliminado"
                        logging.error("❌ [Discord] Webhook inválido")
                else:
                    dc_status["message"] = "URL de webhook con formato incorrecto"
                    logging.error("❌ [Discord] Formato de URL incorrecto")
            except Exception as e:
                dc_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [Discord] Error verificando: {e}")
        else:
            dc_status["message"] = "No configurado"
            logging.warning("⚠️ [Discord] No configurado")
        results["platforms"]["discord"] = dc_status

        # --- LINKEDIN ---
        # Se verifica lo que se va a PUBLICAR (directiva 16): en modo person que
        # el token tenga identidad OpenID y sea ESTE perfil; en modo organization
        # que administre ESTA página. Cada modo comprueba su propio permiso.
        li_status = {"configured": False, "valid": False, "message": "", "details": {}}
        li_author = self._linkedin_author()
        if self.li_token and li_author:
            li_status["configured"] = True
            li_status["details"]["modo"] = self.li_author_mode
            try:
                if self.li_author_mode == "person":
                    # /v2/userinfo (OpenID) devuelve el 'sub'; que coincida con
                    # LINKEDIN_PERSON_SUB confirma que el token es de este perfil.
                    # No prueba w_member_social —ese scope no tiene endpoint de
                    # solo lectura—, pero sí que el autor con el que publicaremos
                    # es el correcto; el 403 al publicar delataría el scope.
                    res = requests.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {self.li_token}"},
                        timeout=10)
                    if res.status_code == 200:
                        sub = res.json().get("sub", "")
                        li_status["details"]["sub"] = sub
                        if sub and sub == self.li_person_sub:
                            li_status["valid"] = True
                            li_status["message"] = f"Token publica como la persona {sub}"
                            logging.info(f"✅ [LinkedIn] Token válido para la persona {sub}")
                        else:
                            li_status["message"] = (
                                f"Token válido pero su 'sub' ({sub or 'ninguno'}) no "
                                f"coincide con LINKEDIN_PERSON_SUB ({self.li_person_sub}).")
                            logging.error(f"❌ [LinkedIn] {li_status['message']}")
                    elif res.status_code == 401:
                        li_status["message"] = "Token expirado o inválido"
                        logging.error("❌ [LinkedIn] Token expirado o inválido")
                    elif res.status_code == 403:
                        li_status["message"] = ("Token sin scope openid/profile "
                                                "(¿la app tiene 'Sign In with LinkedIn using OpenID Connect'?)")
                        logging.error(f"❌ [LinkedIn] {li_status['message']}")
                    else:
                        li_status["message"] = f"Error: {res.status_code} {res.text[:200]}"
                        logging.error(f"❌ [LinkedIn] {li_status['message']}")
                else:
                    # organization: publicamos como urn:li:organization, así que lo
                    # que hay que comprobar es que el token administre ESTA página.
                    # /v2/me da 200 con solo identidad personal y no dice nada de
                    # permisos en la empresa.
                    headers = {"Authorization": f"Bearer {self.li_token}",
                               "X-Restli-Protocol-Version": "2.0.0"}
                    res = requests.get(
                        "https://api.linkedin.com/v2/organizationAcls",
                        params={"q": "roleAssignee", "role": "ADMINISTRATOR",
                                "state": "APPROVED"},
                        headers=headers, timeout=10)
                    if res.status_code == 200:
                        orgs = [e.get("organization", "").rsplit(":", 1)[-1]
                                for e in res.json().get("elements", [])]
                        li_status["details"]["orgs_administradas"] = orgs
                        if self.li_org_id in orgs:
                            li_status["valid"] = True
                            li_status["message"] = f"Token administra la organización {self.li_org_id}"
                            logging.info(f"✅ [LinkedIn] Token administra la organización {self.li_org_id}")
                        else:
                            li_status["message"] = (
                                f"El token es válido pero NO administra {self.li_org_id} "
                                f"(administra: {orgs or 'ninguna'}). No podrá publicar.")
                            logging.error(f"❌ [LinkedIn] {li_status['message']}")
                    elif res.status_code == 401:
                        li_status["message"] = "Token expirado o inválido"
                        logging.error("❌ [LinkedIn] Token expirado o inválido")
                    elif res.status_code == 403:
                        li_status["message"] = ("Token sin permiso rw_organization_admin "
                                                "(¿la app tiene aprobada la Community Management API?)")
                        logging.error(f"❌ [LinkedIn] {li_status['message']}")
                    else:
                        li_status["message"] = f"Error: {res.status_code} {res.text[:200]}"
                        logging.error(f"❌ [LinkedIn] {li_status['message']}")
            except Exception as e:
                li_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [LinkedIn] Error verificando: {e}")
        else:
            li_status["message"] = "No configurado (en período de verificación)"
            logging.warning("⚠️ [LinkedIn] No configurado")
        results["platforms"]["linkedin"] = li_status

        # --- REDDIT ---
        rd_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.clients["reddit"]:
            rd_status["configured"] = True
            try:
                user = self.clients["reddit"].user.me()
                if user:
                    rd_status["valid"] = True
                    rd_status["details"] = {"username": user.name, "karma": user.link_karma + user.comment_karma}
                    rd_status["message"] = f"Conectado como u/{user.name} (karma: {user.link_karma + user.comment_karma})"
                    logging.info(f"✅ [Reddit] Conectado como u/{user.name} (karma: {user.link_karma + user.comment_karma})")
            except Exception as e:
                rd_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [Reddit] Error verificando: {e}")
        else:
            rd_status["message"] = "Desactivado (REDDIT_ENABLED=false)" if not self.reddit_enabled else "No configurado"
            logging.warning(f"⚠️ [Reddit] {'Desactivado' if not self.reddit_enabled else 'No configurado'}")
        results["platforms"]["reddit"] = rd_status

        # --- EMAIL ---
        email_status = {"configured": False, "valid": False, "message": "", "details": {}}
        if self.clients["email"]:
            email_status["configured"] = True
            try:
                stats = self.clients["email"].get_stats()
                email_status["valid"] = True
                email_status["details"] = {"subscribers": stats.get("activos", 0), "campaigns": stats.get("total_campañas", 0)}
                email_status["message"] = f"Activo - {stats.get('activos', 0)} suscriptores"
                logging.info(f"✅ [Email] Activo - {stats.get('activos', 0)} suscriptores, {stats.get('total_campañas', 0)} campañas")
            except Exception as e:
                email_status["message"] = f"Error: {str(e)}"
                logging.error(f"❌ [Email] Error verificando: {e}")
        else:
            email_status["message"] = "No configurado"
            logging.warning("⚠️ [Email] No configurado")
        results["platforms"]["email"] = email_status

        # --- RESUMEN ---
        # El interruptor se anota en cada plataforma ANTES de contar. Sin esto el
        # informe dice "✅ válida" de un canal apagado y remata con "listas para
        # publicar: Sí", que es mentira: el bucle de publicación salta lo que
        # tenga enabled=False por muy buenas que sean sus credenciales.
        for nombre, estado in results["platforms"].items():
            estado["enabled"] = self.enabled.get(nombre, False)
            # "Publicará" exige las dos cosas: interruptor Y credenciales.
            estado["will_publish"] = estado["enabled"] and estado["valid"]

        valid_count = sum(1 for p in results["platforms"].values() if p["valid"])
        configured_count = sum(1 for p in results["platforms"].values() if p["configured"])
        publishing = [n for n, p in results["platforms"].items() if p["will_publish"]]
        total_platforms = len(results["platforms"])

        results["summary"] = {
            "total_platforms": total_platforms,
            "configured": configured_count,
            "valid": valid_count,
            "publishing": publishing,
            # Lo único que importa: ¿hay algún canal que de verdad vaya a publicar?
            "ready_to_publish": len(publishing) > 0
        }

        logging.info("=" * 60)
        logging.info(f"📊 RESUMEN: {valid_count}/{configured_count} plataformas verificadas correctamente")
        logging.info(f"   Configuradas: {configured_count}/{total_platforms}")
        logging.info(f"   Válidas: {valid_count}/{configured_count}")
        logging.info("=" * 60)

        return results

    def observe_and_read(self, zone_config):
        logging.info(f"👁️ Analizando zona: {zone_config['name']}...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True
                )
                page = context.new_page()
                page.goto(zone_config['url'], wait_until="networkidle")
                time.sleep(15) 
                
                target_y = zone_config['scroll_y']
                page.evaluate(f"window.scrollTo({{ top: {target_y}, behavior: 'smooth' }});")
                time.sleep(3)
                
                visible_text = page.evaluate("() => document.body.innerText")
                self.extracted_text = visible_text[:2500] 
                browser.close()
                
            return True
        except Exception as e:
            logging.error(f"❌ Error al observar: {e}")
            return False

    def think(self, zone_config):
        logging.info("🧠 Generando estrategia de contenido...")
        if not self.clients["openai"]:
            return random.choice(self.backup_copies)

        try:
            # Escribe sobre lo que el pantallazo leyó de verdad. Antes este prompt
            # describía un ERP con módulos de funeraria e inmobiliaria —resto de
            # otro proyecto— e ignoraba tanto la zona como el texto capturado.
            system_prompt = (
                "Eres el responsable de comunicación de Xiliux, un estudio de software: "
                "desarrollo en Python (MVPs, integración de LLMs, automatización) y Quipu, "
                "una biblioteca de criptografía post-cuántica de código abierto en Rust.\n"
                "Escribe UNA publicación para redes sociales a partir del contenido real de "
                "la sección que se te entrega. Reglas:\n"
                "- Máximo 230 caracteres.\n"
                "- Habla SOLO de Xiliux: software, desarrollo, criptografía. NUNCA de "
                "servicios jurídicos, abogacía, cumplimiento normativo ni protección de "
                "datos: esa es otra identidad y no se mezcla con esta.\n"
                "- Cíñete a lo que dice el contenido: no inventes productos ni módulos.\n"
                "- Tono profesional y directo. Sin superlativos ni promesas vacías.\n"
                "- Máximo 2 hashtags al final. NO pongas el link, yo lo pondré después."
            )

            user_prompt = (
                f"Sección de la web: {zone_config['name']}\n\n"
                f"Contenido leído de esa sección:\n"
                f"{self.extracted_text or '(no se pudo leer texto; usa solo la sección)'}"
            )
            
            response = self.clients["openai"].chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content.strip('"')
            
            link_suffix = f"\n\n🔗 {self.main_link}"
            max_content_len = 280 - len(link_suffix) - 5 
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."
            
            final_content = content + link_suffix
            logging.info(f"📝 Copy Final: {final_content}")
            return final_content
            
        except Exception as e:
            logging.warning(f"⚠️ IA falló ({e}). Usando respaldo.")
            return random.choice(self.backup_copies)

    # --- PUBLICADORES ---

    def publish_mastodon(self, text):
        if not self.clients["mastodon"] or not self.mastodon_enabled: return
        try:
            self.clients["mastodon"].status_post(status=text)
            logging.info("✅ [Mastodon] Publicado.")
        except Exception as e:
            logging.error(f"❌ [Mastodon] Falló: {e}")

    def publish_twitter(self, text):
        if not self.clients["twitter_client"]: return
        try:
            self.clients["twitter_client"].create_tweet(text=text)
            logging.info("✅ [Twitter/X] Publicado.")
        except Exception as e:
            logging.error(f"❌ [Twitter/X] Falló: {e}")

    def publish_telegram(self, text):
        if not self.tg_token: return
        try:
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            reply_markup = {"inline_keyboard": [[{"text": "🚀 Ver en Xiliux.com", "url": self.main_link}]]}
            data = {'chat_id': self.tg_chat_id, 'text': text, 'reply_markup': json.dumps(reply_markup)}
            requests.post(url, data=data)
            logging.info("✅ [Telegram] Publicado.")
        except Exception as e:
            logging.error(f"❌ [Telegram] Falló: {e}")

    def publish_bluesky(self, text):
        if not self.clients["bluesky"]: return
        try:
            # El enlace va como *facet* o no se puede pinchar. `send_post` solo
            # construye facets si recibe un TextBuilder: con una cadena normal
            # manda facets=None y la URL sale como texto muerto. Se veía bien en
            # el log y no convertía nada.
            from atproto import client_utils
            if text.rstrip().endswith(self.main_link):
                previo = text[:text.rstrip().rfind(self.main_link)]
                post = (client_utils.TextBuilder().text(previo)
                        .link(self.main_link, self.main_link))
            else:
                post = text
            self.clients["bluesky"].send_post(post)
            logging.info("✅ [Bluesky] Publicado.")
        except Exception as e:
            logging.error(f"❌ [Bluesky] Falló envío: {e}")

    def publish_discord(self, text):
        """NUEVO: Publicación en Discord mediante Webhooks"""
        if not self.discord_url: return
        try:
            payload = {
                "content": text,
                "username": "Xiliux Intelligence",
            }
            res = requests.post(self.discord_url, json=payload)
                
            if res.status_code in [200, 204]:
                logging.info("✅ [Discord] Publicado.")
            else:
                logging.error(f"❌ [Discord] Error API: {res.status_code} - {res.text}")
        except Exception as e:
            logging.error(f"❌ [Discord] Falló: {e}")

    def _linkedin_author(self):
        """URN del autor según LINKEDIN_AUTHOR_MODE. None si falta su id.

        person       -> urn:li:person:{LINKEDIN_PERSON_SUB}   (scope w_member_social)
        organization -> urn:li:organization:{LINKEDIN_ORG_ID} (Community Management API)

        Devolver None (no un valor de relleno) hace que el canal se salte en vez
        de publicar contra un URN a medias (directiva 20).
        """
        if self.li_author_mode == "person":
            return f"urn:li:person:{self.li_person_sub}" if self.li_person_sub else None
        return f"urn:li:organization:{self.li_org_id}" if self.li_org_id else None

    def publish_linkedin(self, text):
        try:
            author = self._linkedin_author()
            if not self.li_token or not author:
                logging.warning("⚠️ [LinkedIn] Saltado (Esperando verificación).")
                return

            headers = {'Authorization': f'Bearer {self.li_token}',
                       'Content-Type': 'application/json',
                       'X-Restli-Protocol-Version': '2.0.0',
                       'LinkedIn-Version': LINKEDIN_VERSION}

            post_body = {
                "author": author,
                "commentary": text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": []
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False
            }
            final_res = requests.post("https://api.linkedin.com/rest/posts",
                                      headers=headers, json=post_body, timeout=15)
            if final_res.status_code == 201:
                logging.info(f"✅ [LinkedIn] Publicado. urn={final_res.headers.get('x-restli-id', '?')}")
            else:
                # Un 403 aquí (app sin permiso sobre la página) es el fallo esperable,
                # y antes se descartaba en silencio: parecía publicado sin estarlo.
                logging.error(f"❌ [LinkedIn] No publicado: HTTP {final_res.status_code} "
                              f"{final_res.text[:300]}")
        except Exception as e:
            logging.error(f"❌ [LinkedIn] Error: {e}")

    def publish_email(self, copy):
        """
        Envía campaña de email marketing.
        Solo se ejecuta en ciclos específicos (ej: cada 7 días o cada X ciclos)
        """
        if not self.clients["email"]:
            return

        try:
            # Verificar si hay suscriptores
            stats = self.clients["email"].get_stats()
            if stats['activos'] == 0:
                logging.info("⚠️ [Email] No hay suscriptores activos aún.")
                return

            # Determinar si enviar email este ciclo
            # Opción 1: Solo lunes (día 0)
            if datetime.now().weekday() == 0:
                asunto = "🚀 Novedades Semanales de Xiliux"
                result = self.clients["email"].send_campaign(
                    asunto=asunto,
                    copy=copy,
                    preview_mode=False  # Cambiar a True para testing
                )
                logging.info(f"✅ [Email] Campaña enviada: {result['enviados']} emails")
            else:
                logging.info("📧 [Email] Saltado (Solo se envía los lunes)")

        except Exception as e:
            logging.error(f"❌ [Email] Error: {e}")

    def publish_reddit(self, text):
        """
        Publica en Reddit.

        IMPORTANTE: Reddit tiene reglas estrictas contra self-promotion.
        - Solo se publica si REDDIT_ENABLED=true
        - Adapta el copy para ser más conversacional
        - Algunos subreddits requieren contribuir antes de promocionar (ratio 9:1)
        """
        if not self.clients["reddit"] or not self.reddit_enabled:
            return

        try:
            subreddit = self.clients["reddit"].subreddit(self.reddit_subreddit)

            # Adaptar copy para Reddit (más conversacional, menos promocional)
            # Eliminar emojis excesivos y hashtags que no funcionan en Reddit
            reddit_text = text.replace("#LegalTech", "LegalTech")
            reddit_text = reddit_text.replace("#Python", "Python")
            reddit_text = reddit_text.replace("#Dev", "")
            reddit_text = reddit_text.replace("#Xiliux", "")

            # Crear título (primeras palabras del copy, max 300 chars)
            title = reddit_text.split('\n')[0][:280]
            if len(title) == 280:
                title += "..."

            submission = subreddit.submit(
                title=title,
                selftext=reddit_text,
                url=None
            )
            logging.info(f"✅ [Reddit] Publicado como texto en r/{self.reddit_subreddit}")

            logging.info(f"   URL: https://reddit.com{submission.permalink}")

        except praw.exceptions.RedditAPIException as e:
            # Errores específicos de Reddit API
            if "RATELIMIT" in str(e):
                logging.warning(f"⚠️ [Reddit] Rate limit alcanzado. Espera antes de volver a publicar.")
            elif "SUBREDDIT_NOEXIST" in str(e):
                logging.error(f"❌ [Reddit] El subreddit r/{self.reddit_subreddit} no existe.")
            else:
                logging.error(f"❌ [Reddit] Error API: {e}")
        except Exception as e:
            logging.error(f"❌ [Reddit] Error: {e}")

    def publish_facebook(self, text):
        """Publica en Facebook Page usando Graph API"""
        if not self.fb_page_token or not self.fb_page_id:
            return
        try:
            url_feed = f"https://graph.facebook.com/v18.0/{self.fb_page_id}/feed"
            data = {
                'message': text,
                'access_token': self.fb_page_token
            }
            res = requests.post(url_feed, data=data)

            if res.status_code == 200:
                logging.info("✅ [Facebook] Publicado.")
            else:
                logging.error(f"❌ [Facebook] Error: {res.status_code} - {res.text}")
        except Exception as e:
            logging.error(f"❌ [Facebook] Falló: {e}")

    def run_cycle(self, verify_first: bool = False, skip_invalid: bool = True):
        """
        Ejecuta un ciclo de publicación.

        Args:
            verify_first: Si True, verifica todas las cuentas antes de publicar
            skip_invalid: Si True, omite plataformas con credenciales inválidas
        """
        logging.info("--- Iniciando Ciclo OMNICANAL (Mastodon + X + TG + Bsky + Discord + Facebook + Email + Reddit) ---")

        # Verificación previa si se solicita
        valid_platforms = None
        if verify_first:
            verification = self.verify_accounts()
            valid_platforms = {k: v["valid"] for k, v in verification["platforms"].items()}

            if skip_invalid and verification["summary"]["valid"] == 0:
                logging.error("❌ No hay plataformas válidas. Abortando ciclo.")
                return

        self.cycle_count += 1
        zone_key = random.choice(list(ZONES.keys()))
        zone = ZONES[zone_key]
        logging.info(f"🎯 Objetivo: {zone['name']} (Ciclo #{self.cycle_count})")

        if self.observe_and_read(zone):
            copy = self.think(zone)
            if copy:
                # Publicar solo donde el canal esté habilitado Y validado.
                # El interruptor manda: sin él, un canal no publica aunque tenga
                # credenciales buenas.
                canales = [
                    ("mastodon", self.publish_mastodon),
                    ("twitter",  self.publish_twitter),
                    ("telegram", self.publish_telegram),
                    ("bluesky",  self.publish_bluesky),
                    ("discord",  self.publish_discord),
                    ("linkedin", self.publish_linkedin),
                    ("reddit",   self.publish_reddit),
                    ("facebook", self.publish_facebook),
                    ("email",    self.publish_email),   # solo lunes, según su propia lógica
                ]
                for nombre, publicar in canales:
                    if not self.enabled[nombre]:
                        continue
                    if valid_platforms and not valid_platforms.get(nombre, True):
                        continue
                    publicar(copy)

        logging.info(f"--- Fin del Ciclo #{self.cycle_count} ---")

def job():
    delay = random.randint(60, 900)
    logging.info(f"⏳ Esperando {delay}s...")
    time.sleep(delay)
    agent = XiliuxAgent()
    agent.run_cycle(verify_first=True)  # Verifica antes de publicar


def print_verification_results(results: dict):
    """Imprime los resultados de verificación en consola de forma legible."""
    print("\n" + "=" * 60)
    print("🔍 VERIFICACIÓN DE CUENTAS")
    print("=" * 60)

    for platform, status in results["platforms"].items():
        # Un canal apagado NO lleva ✅ aunque sus credenciales sirvan: el ✅ se
        # reserva para lo que realmente va a publicar.
        if status.get("will_publish"):
            icon = "✅"
        elif not status.get("enabled", True):
            icon = "🚫"
        elif status["valid"]:
            icon = "✅"
        elif status["configured"]:
            icon = "⚠️"
        else:
            icon = "❌"
        nota = "" if status.get("enabled", True) else "  [APAGADO]"
        print(f"{icon} {platform.upper():12} | {status['message']}{nota}")
        if status.get("details"):
            for key, value in status["details"].items():
                print(f"   └─ {key}: {value}")

    print("-" * 60)
    summary = results["summary"]
    canales = summary.get("publishing", [])
    print(f"📊 RESUMEN: {summary['valid']}/{summary['configured']} con credenciales válidas")
    print(f"   Total configuradas: {summary['configured']}/{summary['total_platforms']}")
    print(f"   PUBLICARÁ EN: {', '.join(canales) if canales else 'NINGUNA'}")
    print(f"   Listas para publicar: {'Sí' if summary['ready_to_publish'] else 'No'}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys

    # Modo solo verificación: python main.py --verify
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        print("🔍 Ejecutando verificación de cuentas...")
        agent = XiliuxAgent()
        results = agent.verify_accounts()
        print_verification_results(results)

        # Guardar resultados en JSON
        with open("verification_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("📄 Resultados guardados en verification_results.json")
        sys.exit(0)

    print("🤖 Xiliux AutoCM: Operativo (Discord Incluido).")

    # Verificación inicial al arrancar
    print("\n🔍 Verificación inicial de cuentas...")
    agent = XiliuxAgent()
    results = agent.verify_accounts()
    print_verification_results(results)

    if not results["summary"]["ready_to_publish"]:
        print("⚠️ ADVERTENCIA: No hay plataformas válidas configuradas.")
        print("   El agente continuará pero no podrá publicar.")

    schedule.every().day.at("09:15").do(job)
    schedule.every().day.at("13:30").do(job)
    schedule.every().day.at("19:45").do(job)

    job()

    while True:
        schedule.run_pending()
        time.sleep(60)