"""
Templates HTML para campañas de email marketing.
Diseñados para ser responsive y compatibles con la mayoría de clientes de email.
"""

def get_campaign_template(nombre, copy, unsub_link):
    """
    Template principal para campañas de marketing.

    Args:
        nombre: Nombre del suscriptor
        copy: Contenido del mensaje
        unsub_link: URL para darse de baja

    Returns:
        str: HTML del email
    """
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xiliux - Novedades</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <!-- Container principal -->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 600px;">

                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: bold;">
                                Xiliux
                            </h1>
                            <p style="margin: 10px 0 0 0; color: #e0e7ff; font-size: 14px;">
                                LegalTech & Desarrollo
                            </p>
                        </td>
                    </tr>

                    <!-- Saludo -->
                    <tr>
                        <td style="padding: 30px 30px 20px 30px;">
                            <p style="margin: 0; color: #333333; font-size: 16px;">
                                Hola <strong>{nombre}</strong>,
                            </p>
                        </td>
                    </tr>

                    <!-- Contenido principal -->
                    <tr>
                        <td style="padding: 0 30px 20px 30px;">
                            <p style="margin: 0; color: #555555; font-size: 15px; line-height: 1.6;">
                                {copy}
                            </p>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 20px 30px 30px 30px; text-align: center;">
                            <a href="https://www.xiliux.com" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">
                                🚀 Visitar Xiliux.com
                            </a>
                        </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                        <td style="padding: 0 30px;">
                            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 0;">
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0 0 10px 0; color: #666666; font-size: 13px; text-align: center;">
                                Te enviamos este email porque te suscribiste a novedades de Xiliux.
                            </p>
                            <p style="margin: 0; color: #999999; font-size: 12px; text-align: center;">
                                <a href="{unsub_link}" style="color: #667eea; text-decoration: none;">
                                    Cancelar suscripción
                                </a> |
                                <a href="https://www.xiliux.com" style="color: #667eea; text-decoration: none;">
                                    Sitio web
                                </a>
                            </p>
                            <p style="margin: 10px 0 0 0; color: #999999; font-size: 11px; text-align: center;">
                                © 2026 Xiliux - LegalTech & Desarrollo
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_welcome_template(nombre, unsub_link):
    """Template de bienvenida para nuevos suscriptores"""
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="background-color: #ffffff; border-radius: 8px; max-width: 600px;">

                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px;">¡Bienvenido a Xiliux! 🎉</h1>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 16px;">
                                Hola <strong>{nombre}</strong>,
                            </p>
                            <p style="margin: 0 0 20px 0; color: #555555; font-size: 15px; line-height: 1.6;">
                                Gracias por suscribirte a Xiliux. Ahora recibirás actualizaciones sobre:
                            </p>
                            <ul style="color: #555555; font-size: 15px; line-height: 1.8;">
                                <li>🔧 Nuevas herramientas y productos LegalTech</li>
                                <li>💻 Desarrollos en Python y NiceGUI</li>
                                <li>⚖️ Consultoría especializada en tecnología legal</li>
                                <li>🚀 Proyectos y casos de éxito</li>
                            </ul>
                            <p style="margin: 20px 0 0 0; color: #555555; font-size: 15px; line-height: 1.6;">
                                Mantente atento a tu inbox para contenido exclusivo y novedades.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 30px 40px 30px; text-align: center;">
                            <a href="https://www.xiliux.com" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">
                                Explorar Xiliux.com
                            </a>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 20px 30px; background-color: #f9fafb; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0; color: #999999; font-size: 12px; text-align: center;">
                                <a href="{unsub_link}" style="color: #667eea; text-decoration: none;">
                                    Cancelar suscripción
                                </a>
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_unsubscribe_confirmation_template(nombre="Usuario"):
    """Template de confirmación de baja"""
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td align="center" style="padding: 40px 0;">
                <table role="presentation" width="500" cellspacing="0" cellpadding="0" border="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px;">
                    <tr>
                        <td style="text-align: center;">
                            <h2 style="color: #333333; margin: 0 0 20px 0;">Suscripción cancelada</h2>
                            <p style="color: #666666; font-size: 15px; line-height: 1.6;">
                                Lamentamos verte partir, <strong>{nombre}</strong>.
                                Has sido dado de baja exitosamente de nuestra lista de correo.
                            </p>
                            <p style="color: #666666; font-size: 14px; margin-top: 20px;">
                                Siempre puedes volver a suscribirte en
                                <a href="https://www.xiliux.com" style="color: #667eea;">www.xiliux.com</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
