# -*- coding: utf-8 -*-
"""
Servicio de notificaciones por correo electrónico del Sistema de Denuncias MMQEP.

Cada llamada abre su propia conexión SMTP, envía el correo y la cierra
(compatible con entornos serverless como Vercel).
"""
import logging
import smtplib
import ssl
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_USE_SSL,
    SMTP_FROM_NAME,
    SMTP_FROM_EMAIL,
    PORTAL_URL,
)

logger = logging.getLogger("mmqep.mail")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.DEBUG)
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s — %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# Función principal de envío
# ---------------------------------------------------------------------------

def enviar_correo(destinatario_email, destinatario_nombre, asunto, cuerpo_html, timeout=10):
    """
    Abre una conexión SMTP, envía un correo HTML y cierra la conexión.

    Retorna True si el envío fue exitoso, False en cualquier caso de error.
    Nunca lanza excepciones hacia el llamador.
    """
    logger.debug("Iniciando envío a '%s', asunto='%s'", destinatario_email, asunto)

    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL]):
        logger.warning(
            "Configuración SMTP incompleta (SERVER=%r USER=%r FROM=%r). No se envió notificación a %s.",
            SMTP_SERVER, SMTP_USERNAME, SMTP_FROM_EMAIL, destinatario_email,
        )
        return False

    logger.debug(
        "Config SMTP: servidor=%s puerto=%s ssl=%s usuario=%s",
        SMTP_SERVER, SMTP_PORT, SMTP_USE_SSL, SMTP_USERNAME,
    )

    try:
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        if destinatario_nombre:
            mensaje["To"] = f"{destinatario_nombre} <{destinatario_email}>"
        else:
            mensaje["To"] = destinatario_email

        mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        if SMTP_USE_SSL:
            logger.debug("Abriendo SMTP_SSL a %s:%s (timeout=%ss)", SMTP_SERVER, SMTP_PORT, timeout)
            contexto = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                SMTP_SERVER, SMTP_PORT, context=contexto, timeout=timeout
            ) as servidor:
                logger.debug("Conexión SMTP_SSL establecida; autenticando como %s", SMTP_USERNAME)
                servidor.login(SMTP_USERNAME, SMTP_PASSWORD)
                logger.debug("Autenticación exitosa; enviando mensaje")
                servidor.sendmail(
                    SMTP_FROM_EMAIL, [destinatario_email], mensaje.as_bytes()
                )
        else:
            logger.debug("Abriendo SMTP a %s:%s STARTTLS (timeout=%ss)", SMTP_SERVER, SMTP_PORT, timeout)
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=timeout) as servidor:
                servidor.ehlo()
                servidor.starttls(context=ssl.create_default_context())
                logger.debug("STARTTLS establecido; autenticando")
                servidor.login(SMTP_USERNAME, SMTP_PASSWORD)
                logger.debug("Autenticación exitosa; enviando mensaje")
                servidor.sendmail(
                    SMTP_FROM_EMAIL, [destinatario_email], mensaje.as_bytes()
                )

        logger.info("Notificación enviada correctamente a %s.", destinatario_email)
        return True

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "Error de autenticación SMTP al notificar a %s: %s",
            destinatario_email, exc, exc_info=True,
        )
    except smtplib.SMTPConnectError as exc:
        logger.error(
            "No se pudo conectar al servidor SMTP (%s:%s): %s",
            SMTP_SERVER, SMTP_PORT, exc, exc_info=True,
        )
    except (TimeoutError, OSError) as exc:
        logger.error(
            "Timeout/error de red al conectar con SMTP %s:%s para notificar a %s: %s",
            SMTP_SERVER, SMTP_PORT, destinatario_email, exc, exc_info=True,
        )
    except smtplib.SMTPException as exc:
        logger.error(
            "Error SMTP al enviar notificación a %s: %s",
            destinatario_email, exc, exc_info=True,
        )
    except Exception as exc:
        logger.error(
            "Error inesperado al enviar notificación a %s: %s\n%s",
            destinatario_email, exc, traceback.format_exc(),
        )

    return False


# ---------------------------------------------------------------------------
# Construcción del HTML del correo de nueva denuncia
# ---------------------------------------------------------------------------

def _construir_html_nueva_denuncia(responsable_nombre, datos):
    """Genera el cuerpo HTML institucional para la notificación de nueva denuncia."""

    def _e(val):
        if val is None:
            return "&mdash;"
        return (
            str(val)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _fmt_fecha(dt):
        if dt is None:
            return "&mdash;"
        if hasattr(dt, "strftime"):
            return dt.strftime("%d/%m/%Y %H:%M")
        return str(dt)

    codigo     = _e(datos.get("codigo"))
    categoria  = _e(datos.get("categoria"))
    subcat     = _e(datos.get("subcategoria"))
    fecha      = _fmt_fecha(datos.get("fecha_creacion"))
    estado     = _e(datos.get("estado"))
    area       = _e(datos.get("area_nombre"))
    ubicacion  = _e(datos.get("ubicacion")) if datos.get("ubicacion") else "&mdash;"
    denunciante = (
        "An&oacute;nimo"
        if datos.get("es_anonima")
        else (_e(datos.get("nombres_denunciante")) or "&mdash;")
    )
    resp_nombre = _e(responsable_nombre)
    url_portal  = _e(PORTAL_URL)

    filas = [
        ("C&oacute;digo de denuncia",  f"<strong style='color:#003366;'>{codigo}</strong>"),
        ("Categor&iacute;a",           categoria),
        ("Subcategor&iacute;a",        subcat),
        ("Fecha y hora de registro",   fecha),
        ("Estado inicial",             estado),
        ("&Aacute;rea responsable",    area),
        ("Ubicaci&oacute;n del hecho", ubicacion),
        ("Denunciante",                denunciante),
    ]

    filas_html = ""
    for i, (etiqueta, valor) in enumerate(filas):
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        filas_html += (
            f'<tr>'
            f'<td style="background:{bg};padding:10px 14px;border-bottom:1px solid #e2e8f0;'
            f'width:42%;font-weight:600;color:#4a5568;font-size:13px;">{etiqueta}</td>'
            f'<td style="background:{bg};padding:10px 14px;border-bottom:1px solid #e2e8f0;'
            f'color:#2d3748;font-size:13px;">{valor}</td>'
            f'</tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Nueva denuncia asignada &mdash; MMQEP</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:30px 0;">
  <tr>
    <td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background-color:#ffffff;border-radius:8px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Cabecera institucional -->
        <tr>
          <td style="background-color:#003366;padding:28px 32px;">
            <p style="margin:0 0 5px 0;color:#a8c4e0;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;">
              Empresa P&uacute;blica Metropolitana
            </p>
            <p style="margin:0 0 4px 0;color:#ffffff;font-size:20px;font-weight:700;">
              Mercado Mayorista de Quito
            </p>
            <p style="margin:0;color:#ccdff0;font-size:13px;">
              Sistema de Quejas y Denuncias Ciudadanas
            </p>
          </td>
        </tr>

        <!-- Franja de t&iacute;tulo -->
        <tr>
          <td style="background-color:#0a4878;padding:13px 32px;">
            <p style="margin:0;color:#ffffff;font-size:15px;font-weight:600;">
              Nueva denuncia asignada
            </p>
          </td>
        </tr>

        <!-- Cuerpo -->
        <tr>
          <td style="padding:28px 32px;">
            <p style="margin:0 0 16px 0;color:#2d3748;font-size:14px;line-height:1.7;">
              Estimado(a) <strong>{resp_nombre}</strong>:
            </p>
            <p style="margin:0 0 24px 0;color:#4a5568;font-size:14px;line-height:1.7;">
              Se le informa que el <strong>Sistema de Quejas</strong> de la Empresa
              P&uacute;blica Metropolitana Mercado Mayorista de Quito (MMQEP) ha registrado
              una nueva denuncia que ha sido asignada autom&aacute;ticamente a su &aacute;rea
              para la gesti&oacute;n correspondiente.
            </p>

            <!-- T&iacute;tulo de la tabla -->
            <p style="margin:0 0 10px 0;color:#003366;font-size:14px;font-weight:700;
                      border-left:4px solid #003366;padding-left:10px;">
              Informaci&oacute;n de la denuncia
            </p>

            <!-- Tabla de datos -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:28px;">
              {filas_html}
            </table>

            <!-- Bot&oacute;n de acceso -->
            <table cellpadding="0" cellspacing="0" style="margin:0 0 8px 0;">
              <tr>
                <td style="background-color:#003366;border-radius:6px;">
                  <a href="{url_portal}" target="_blank"
                     style="display:inline-block;padding:13px 32px;color:#ffffff;
                            font-size:14px;font-weight:700;text-decoration:none;
                            letter-spacing:0.3px;">
                    Acceder al Sistema
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Pie de p&aacute;gina -->
        <tr>
          <td style="background-color:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;">
            <p style="margin:0;color:#718096;font-size:12px;line-height:1.6;">
              Este es un mensaje generado autom&aacute;ticamente por el
              <strong>Sistema de Quejas</strong> de la Empresa P&uacute;blica
              Metropolitana Mercado Mayorista de Quito (MMQEP).<br>
              Por favor no responder este correo.
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Notificación de nueva denuncia asignada
# ---------------------------------------------------------------------------

def enviar_notificacion_nueva_denuncia(responsable_correo, responsable_nombre, datos_denuncia):
    """
    Envía al Responsable la notificación de una nueva denuncia asignada.

    datos_denuncia debe contener:
        codigo, categoria, subcategoria, fecha_creacion, estado, prioridad,
        area_nombre, ubicacion, es_anonima, nombres_denunciante

    Retorna True si el envío fue exitoso, False en caso contrario.
    """
    asunto = "Nueva denuncia asignada - Sistema de Denuncias MMQEP"
    cuerpo_html = _construir_html_nueva_denuncia(responsable_nombre, datos_denuncia)
    return enviar_correo(responsable_correo, responsable_nombre, asunto, cuerpo_html)
