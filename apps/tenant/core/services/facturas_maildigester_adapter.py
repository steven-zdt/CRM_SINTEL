"""
Adaptador de Core API para ingesta de facturas desde correo.

⚠️ FASE 4/5: Service Layer Adapter - Core API consume servicios de facturas sin HTTP interno.
- Core API sigue siendo orquestador de UI
- Internamente delega en facturas (dueño del dominio)
- Expone datos uniformes al workspace
- SSoT: Las configuraciones se obtienen desde empresa
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
# ⚠️ IMPORT LAZY: enqueue_mail_ingestion se importa dentro de las funciones (evita ciclos)
# from apps.tenant.facturas.services_mail_ingestion import enqueue_mail_ingestion
from apps.tenant.facturas.models import MailIngestionRun
from apps.tenant.empresa.models import MailInboxConfig
from apps.services.maildigester.inbox_client import RealIMAPClient
from apps.services.maildigester.exceptions import MailboxConnectionError

log = logging.getLogger(__name__)


def core_run_mail_ingestion(
    *,
    user,
    config_id: int,
    limit_messages: int = 50
) -> Dict[str, Any]:
    """
    Encola una ejecución de ingesta de facturas desde correo.
    
    ⚠️ SSoT: Delega en apps.tenant.facturas.services_mail_ingestion.
    ⚠️ NATURALEZA: No se especifica; se determina automáticamente desde el XML UBL.
    
    Args:
        user: Usuario que inicia la ingesta
        config_id: ID de MailIngestionConfig
        limit_messages: Número máximo de mensajes a procesar
        
    Returns:
        Dict con run_id, task_id y redirect_url
    """
    # ⚠️ IMPORT LAZY: Evita ciclos de importación
    from apps.tenant.facturas.services_mail_ingestion import enqueue_mail_ingestion
    
    run = enqueue_mail_ingestion(
        config_id=config_id,
        limit_messages=limit_messages,
        started_by=user,
    )
    return {
        "run_id": run.id,
        "task_id": run.task_id,
        "status": run.status,
        "redirect_url": "/workspace/#facturas",
    }


def core_list_mail_runs() -> List[Dict[str, Any]]:
    """
    Lista ejecuciones recientes de ingesta por correo.
    
    ⚠️ OPTIMIZACIÓN: Usa only() para limitar columnas.
    
    Returns:
        Lista de dicts con datos de ejecuciones
    """
    qs = MailIngestionRun.objects.all().only(
        "id",
        "started_at",
        "finished_at",
        "status",
        "task_id",
        "naturaleza",
        "counts"
    )
    return [
        {
            "id": r.id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "task_id": r.task_id,
            "naturaleza": r.naturaleza,
            "counts": r.counts,
        }
        for r in qs
    ]


def core_list_mail_configs() -> List[Dict[str, Any]]:
    """
    Lista configuraciones activas de buzones de correo.
    
    ⚠️ SSoT: Obtiene configuraciones desde empresa (MailInboxConfig).
    ⚠️ OPTIMIZACIÓN: Usa only() para limitar columnas.
    ⚠️ SEGURIDAD: No expone password.
    
    Returns:
        Lista de dicts con datos de configuraciones
    """
    qs = MailInboxConfig.objects.filter(is_active=True).only(
        "id",
        "nombre",
        "host",
        "port",
        "protocol",
        "ssl",
        "username",
        "mailbox",
        "mark_as_seen",
        "move_processed_to",
        "max_attachment_mb"
    )
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "host": c.host,
            "port": c.port,
            "protocol": c.protocol,
            "ssl": c.ssl,
            "username": c.username,
            "mailbox": c.mailbox,
            "mark_as_seen": c.mark_as_seen,
            "move_processed_to": c.move_processed_to,
            "max_attachment_mb": c.max_attachment_mb,
        }
        for c in qs
    ]


def core_test_mailbox_connection(
    *,
    provider: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    protocol: str = "imap",
    ssl: Optional[bool] = None,
    starttls: Optional[bool] = None,
    username: str = "",
    password: str = "",
    mailbox: str = "INBOX",
    email_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prueba conexión a un buzón de correo sin persistir configuración.
    
    ⚠️ DIAGNÓSTICO: Solo prueba conexión, no persiste nada.
    ⚠️ SEGURIDAD: No expone password en respuestas.
    ⚠️ GMAIL: Si provider == "gmail", fuerza presets de Gmail (ignora host/port/ssl enviados).
    
    Args:
        provider: "gmail" o "custom" (opcional)
        host: Servidor IMAP/POP3 (ignorado si provider == "gmail")
        port: Puerto (ignorado si provider == "gmail")
        protocol: "imap" o "pop3" (siempre "imap" para Gmail)
        ssl: Si usar SSL/TLS (ignorado si provider == "gmail")
        starttls: Si usar STARTTLS (ignorado si provider == "gmail")
        username: Usuario
        password: Contraseña o App Password
        mailbox: Carpeta a seleccionar (default: INBOX)
        email_address: Email principal (usado como username por defecto)
        
    Returns:
        Dict con ok, banner, capabilities, message
    """
    try:
        if protocol != "imap":
            return {
                "ok": False,
                "banner": None,
                "capabilities": [],
                "message": f"Protocolo {protocol} no soportado. Solo IMAP está implementado."
            }
        
        # Si provider == "gmail", forzar presets de Gmail (defensa en profundidad)
        # Ignorar cualquier override del cliente para garantizar seguridad
        if provider == "gmail":
            host = "imap.gmail.com"  # Gmail IMAP hostname [community.pmail.com]
            port = 993  # IMAPS 993 SSL/TLS (recomendado) [community.pmail.com]
            ssl = True
            starttls = False  # STARTTLS no aplica en 993 (solo en 143)
            # Username por defecto: email_address si está disponible
            if not username and email_address:
                username = email_address
        
        # Validar parámetros requeridos
        if not host:
            return {
                "ok": False,
                "banner": None,
                "capabilities": [],
                "message": "El host es obligatorio."
            }
        if not username:
            return {
                "ok": False,
                "banner": None,
                "capabilities": [],
                "message": "El usuario es obligatorio."
            }
        if not password:
            return {
                "ok": False,
                "banner": None,
                "capabilities": [],
                "message": "La contraseña es obligatoria."
            }
        
        # Valores por defecto si no se especifican
        port = port or 993
        ssl = ssl if ssl is not None else True
        starttls = starttls if starttls is not None else False
        
        client = RealIMAPClient()
        config: Dict[str, Any] = {
            "host": host,
            "port": port,
            "protocol": protocol,
            "ssl": ssl,
            "starttls": starttls,
            "username": username,
            "password": password,
            "mailbox": mailbox,
        }
        
        # Logging seguro (sin contraseña)
        log.debug(
            '[mail test] host=%s port=%s ssl=%s starttls=%s username=%s provider=%s',
            host, port, ssl, starttls, username, provider
        )
        
        client.connect(config)
        
        # Obtener banner y capabilities desde la conexión
        connection = client._connection
        banner = getattr(connection, 'welcome', None) if connection else None
        
        capabilities = []
        if connection:
            try:
                typ, data = connection.capability()
                if typ == "OK" and data:
                    capabilities = data[0].decode("utf-8").split() if isinstance(data[0], bytes) else str(data[0]).split()
            except Exception:
                pass
        
        client.disconnect()
        
        return {
            "ok": True,
            "banner": banner.decode("utf-8") if isinstance(banner, bytes) else str(banner) if banner else None,
            "capabilities": capabilities,
            "message": "Conexión exitosa"
        }
        
    except MailboxConnectionError as e:
        error_msg = str(e)
        error_code = "UNKNOWN"
        
        # Mapeo de errores específicos de Gmail con detección robusta
        if provider == "gmail":
            error_upper = error_msg.upper()
            # Detectar AUTHENTICATIONFAILED (varios formatos posibles)
            if ("AUTHENTICATIONFAILED" in error_upper or 
                "AUTHENTICATE" in error_upper or 
                "LOGIN" in error_upper or
                "INVALID CREDENTIALS" in error_upper or
                "BAD CREDENTIALS" in error_upper):
                error_code = "AUTHENTICATIONFAILED"
                error_msg = "Credenciales inválidas. En Gmail activa IMAP y, si tienes 2FA, usa Contraseña de App (no tu contraseña normal)."
            # Detectar IMAP deshabilitado (varios formatos)
            elif ("NOT ENABLED" in error_upper or 
                  ("IMAP" in error_upper and ("DISABLED" in error_upper or "ENABLE" in error_upper or "NOT AVAILABLE" in error_upper)) or
                  "NOT ALLOWED" in error_upper):
                error_code = "IMAP_DISABLED"
                error_msg = "IMAP deshabilitado en Gmail. Actívalo en Settings → Forwarding and POP/IMAP → Enable IMAP."
            # Detectar errores TLS/SSL/EOF
            elif ("EOF" in error_msg or 
                  "TLS" in error_msg or 
                  "SSL" in error_msg or 
                  "handshake" in error_msg.lower() or 
                  "CERTIFICATE" in error_upper or
                  "CONNECTION" in error_upper and ("REFUSED" in error_upper or "TIMEOUT" in error_upper)):
                error_code = "TLS_ERROR"
                error_msg = "Fallo de conexión segura (IMAPS 993). Verifica puerto/SSL y firewall; prueba con: openssl s_client -connect imap.gmail.com:993 -crlf -quiet"
        
        # Logging seguro del error (sin contraseña)
        log.warning(
            '[mail test] Error de conexión: code=%s provider=%s host=%s port=%s',
            error_code, provider or 'custom', host, port
        )
        
        return {
            "ok": False,
            "code": error_code,
            "banner": None,
            "capabilities": [],
            "message": error_msg
        }
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        error_code = "UNKNOWN"
        
        # Mapeo de errores específicos de Gmail (fallback para excepciones no capturadas)
        if provider == "gmail":
            error_str = str(e).upper()
            if ("AUTHENTICATIONFAILED" in error_str or 
                "AUTHENTICATE" in error_str or 
                "LOGIN" in error_str or
                "INVALID CREDENTIALS" in error_str):
                error_code = "AUTHENTICATIONFAILED"
                error_msg = "Credenciales inválidas. En Gmail activa IMAP y, si tienes 2FA, usa Contraseña de App (no tu contraseña normal)."
            elif ("NOT ENABLED" in error_str or 
                  ("IMAP" in error_str and ("DISABLED" in error_str or "ENABLE" in error_str))):
                error_code = "IMAP_DISABLED"
                error_msg = "IMAP deshabilitado en Gmail. Actívalo en Settings → Forwarding and POP/IMAP → Enable IMAP."
            elif ("EOF" in str(e) or 
                  "TLS" in str(e) or 
                  "SSL" in str(e) or 
                  "handshake" in str(e).lower() or 
                  "CERTIFICATE" in error_str):
                error_code = "TLS_ERROR"
                error_msg = "Fallo de conexión segura (IMAPS 993). Verifica puerto/SSL y firewall; prueba con: openssl s_client -connect imap.gmail.com:993 -crlf -quiet"
        
        # Logging seguro del error (sin contraseña, con traceback solo en desarrollo)
        log.error(
            '[mail test] Error inesperado: code=%s provider=%s host=%s',
            error_code, provider or 'custom', host,
            exc_info=True
        )
        
        return {
            "ok": False,
            "code": error_code,
            "banner": None,
            "capabilities": [],
            "message": error_msg
        }


def core_stop_mail_ingestion_run(run_id: int, *, force: bool = False) -> Dict[str, Any]:
    """
    Cancela una ejecución de ingesta de correo (cancelación cooperativa).
    
    ⚠️ CANCELACIÓN COOPERATIVA:
    a) Marca el run en BD como CANCEL_REQUESTED (la tarea lo detecta periódicamente)
    b) Opcional: app.control.revoke(task_id, terminate=False) para evitar nuevos slots
    
    Args:
        run_id: ID de MailIngestionRun
        force: Si True, termina la tarea forzosamente (SIGTERM) - solo en emergencia
        
    Returns:
        Dict con ok, message, status
    """
    try:
        run = MailIngestionRun.objects.get(id=run_id)
        
        # Verificar si ya terminó
        if run.status in ("SUCCESS", "FAILED", "CANCELED", "ABORTED"):
            return {
                "ok": False,
                "message": f"La ejecución ya terminó con estado {run.status}",
                "status": run.status
            }
        
        # a) Marcar CANCEL_REQUESTED en BD (cancelación cooperativa)
        run.status = "CANCEL_REQUESTED"
        run.save(update_fields=["status"])
        
        # b) Opcional: revoke suave (no termina, solo evita nuevos slots)
        if force:
            # Solo en emergencia: terminar forzosamente
            from celery import current_app
            current_app.control.revoke(
                run.task_id,
                terminate=True,
                signal="SIGTERM"
            )
            run.status = "ABORTED"
            run.save(update_fields=["status"])
        else:
            # Revoke suave (cooperativo)
            from celery import current_app
            current_app.control.revoke(
                run.task_id,
                terminate=False  # No termina, solo marca para que no arranque de nuevo
            )
        
        return {
            "ok": True,
            "message": "Cancelación solicitada. La tarea se detendrá en el siguiente checkpoint.",
            "status": run.status
        }
        
    except MailIngestionRun.DoesNotExist:
        return {
            "ok": False,
            "message": f"Ejecución {run_id} no encontrada",
            "status": None
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Error al cancelar: {str(e)}",
            "status": None
        }


def core_delete_mail_ingestion_run(run_id: int) -> Dict[str, Any]:
    """
    Elimina una ejecución de ingesta de correo.
    
    ⚠️ SEGURIDAD: Solo permite eliminar ejecuciones terminadas (SUCCESS, FAILED, CANCELED, ABORTED).
    No permite eliminar ejecuciones en curso (PENDING, RUNNING) para evitar inconsistencias.
    
    Args:
        run_id: ID de MailIngestionRun
        
    Returns:
        Dict con ok, message
    """
    try:
        run = MailIngestionRun.objects.get(id=run_id)
        
        # Verificar que la ejecución haya terminado
        if run.status in ("PENDING", "RUNNING", "CANCEL_REQUESTED"):
            return {
                "ok": False,
                "message": f"No se puede eliminar una ejecución en estado {run.status}. Detén la ejecución primero."
            }
        
        # Eliminar el run
        run.delete()
        
        return {
            "ok": True,
            "message": f"Ejecución {run_id} eliminada correctamente."
        }
        
    except MailIngestionRun.DoesNotExist:
        return {
            "ok": False,
            "message": f"Ejecución {run_id} no encontrada"
        }
    except Exception as e:
        log.error("Error eliminando ejecución %s: %s", run_id, str(e), exc_info=True)
        return {
            "ok": False,
            "message": f"Error al eliminar: {str(e)}"
        }


def core_get_mail_ingestion_run_details(run_id: int) -> Dict[str, Any]:
    """
    Obtiene detalles de una ejecución de ingesta, incluyendo lista de XMLs detectados.
    
    Args:
        run_id: ID de MailIngestionRun
        
    Returns:
        Dict con run_id, status, xml_items
    """
    try:
        run = MailIngestionRun.objects.get(id=run_id)
        
        # Extraer items XML desde summary/details
        xml_items = []
        details = run.summary.get("details", []) if isinstance(run.summary, dict) else []
        
        for detail in details:
            if isinstance(detail, dict):
                xml_items.append({
                    "filename": detail.get("source_filename", detail.get("numero", "unknown")),
                    "size": detail.get("size_bytes", 0),
                    "source_email_id": detail.get("source_email_id", ""),
                    "status": detail.get("status", "unknown"),
                    "message": detail.get("message", "")
                })
        
        return {
            "run_id": run.id,
            "status": run.status,
            "xml_items": xml_items
        }
        
    except MailIngestionRun.DoesNotExist:
        return {
            "run_id": run_id,
            "status": None,
            "xml_items": []
        }
