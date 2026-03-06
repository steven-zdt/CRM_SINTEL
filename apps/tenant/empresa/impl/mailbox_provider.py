"""
Provider SSoT para configuraciones de buzones de correo.

⚠️ SSoT: Este es el único lugar desde donde maildigester toma credenciales.
⚠️ CERO SIGNALS: Toda la lógica es explícita.
"""
from typing import Dict
from apps.tenant.empresa.models import MailInboxConfig
from apps.services.maildigester.schemas import MailboxConfigDTO


def get_mailbox_config(config_id: int) -> MailboxConfigDTO:
    """
    Retorna un diccionario listo para el pipeline de maildigester.
    
    Valida is_active y normaliza campos según el contrato MailboxConfigDTO.
    Si provider == "gmail", aplica presets de Gmail (imap.gmail.com:993 SSL).
    
    ⚠️ SSoT: Este es el único lugar desde donde maildigester obtiene credenciales.
    ⚠️ GMAIL: Si provider == "gmail", fuerza presets seguros de Gmail.
    
    Args:
        config_id: ID de MailInboxConfig (debe estar activa)
        
    Returns:
        MailboxConfigDTO listo para usar en el pipeline
        
    Raises:
        MailInboxConfig.DoesNotExist: Si la config no existe o no está activa
        
    Ejemplo:
        config = get_mailbox_config(config_id=1)
        # Retorna: {
        #     "host": "imap.gmail.com",
        #     "port": 993,
        #     "protocol": "imap",
        #     "ssl": True,
        #     "starttls": False,
        #     "username": "facturas@empresa.com",
        #     "password": "secret",
        #     "mailbox": "INBOX",
        #     "mark_as_seen": True,
        #     "move_processed_to": "Procesados",
        #     "max_attachment_mb": 50
        # }
    """
    cfg = MailInboxConfig.objects.get(id=config_id, is_active=True)
    
    # Si provider == "gmail", aplicar presets de Gmail (SSoT)
    if cfg.provider == "gmail":
        # IMAP preset: imap.gmail.com:993 SSL (recomendado por Gmail) [community.pmail.com]
        imap_host = "imap.gmail.com"
        imap_port = 993  # IMAPS 993 SSL/TLS
        imap_ssl = True
        imap_starttls = False  # STARTTLS no aplica en 993 (solo en 143)
        # SMTP preset: smtp.gmail.com:587 TLS por defecto (o 465 SSL si se marca explícitamente) [docs.celeryq.dev]
        smtp_host = "smtp.gmail.com"
        # Por defecto usar 587 TLS; si UI marca SSL 465, ajustar:
        smtp_port = 587 if getattr(cfg, 'smtp_starttls', True) else (getattr(cfg, 'smtp_port', None) or 465)
        smtp_ssl = not getattr(cfg, 'smtp_starttls', True) if hasattr(cfg, 'smtp_starttls') and cfg.smtp_starttls is not None else False
        smtp_starttls = getattr(cfg, 'smtp_starttls', True) if hasattr(cfg, 'smtp_starttls') else True
    else:
        # Custom: usar valores de DB (preferir nuevos campos IMAP, fallback a legacy)
        imap_host = cfg.imap_host or cfg.host or ""
        imap_port = cfg.imap_port or cfg.port or 993
        # Verificar si el campo existe antes de acceder
        try:
            imap_ssl = cfg.imap_ssl
        except AttributeError:
            imap_ssl = cfg.ssl if cfg.ssl is not None else True
        try:
            imap_starttls = cfg.imap_starttls
        except AttributeError:
            imap_starttls = False
        smtp_host = cfg.smtp_host or ""
        smtp_port = cfg.smtp_port or 587
        try:
            smtp_ssl = cfg.smtp_ssl
        except AttributeError:
            smtp_ssl = False
        try:
            smtp_starttls = cfg.smtp_starttls
        except AttributeError:
            smtp_starttls = True
    
    # Username: preferir imap_username, luego email_address, luego legacy username
    # Para Gmail, username por defecto = email_address [community.pmail.com]
    if cfg.provider == "gmail":
        username = getattr(cfg, 'imap_username', None) or getattr(cfg, 'email_address', None) or getattr(cfg, 'username', None) or ""
    else:
        username = getattr(cfg, 'imap_username', None) or getattr(cfg, 'email_address', None) or getattr(cfg, 'username', None) or ""
    
    # Password: preferir imap_password, luego legacy password
    password = getattr(cfg, 'imap_password', None) or getattr(cfg, 'password', None) or ""
    
    # Mailbox: preferir imap_mailbox, luego legacy mailbox
    mailbox = getattr(cfg, 'imap_mailbox', None) or getattr(cfg, 'mailbox', None) or "INBOX"
    
    # SMTP username: preferir smtp_username, luego email_address, luego imap_username
    # Para Gmail, smtp_username por defecto = email_address [docs.celeryq.dev]
    smtp_user = getattr(cfg, 'smtp_username', None) or getattr(cfg, 'email_address', None) or username
    
    # SMTP password: preferir smtp_password, luego imap_password
    smtp_pass = getattr(cfg, 'smtp_password', None) or password
    
    return {
        "provider": cfg.provider,
        "host": imap_host,
        "port": imap_port,
        "protocol": "imap",  # Siempre IMAP
        "ssl": imap_ssl,
        "starttls": imap_starttls,
        "username": username,
        "password": password,
        "mailbox": mailbox,
        "mark_as_seen": getattr(cfg, 'imap_mark_as_seen', None) if hasattr(cfg, 'imap_mark_as_seen') else getattr(cfg, 'mark_as_seen', True),
        "move_processed_to": getattr(cfg, 'imap_move_processed_to', None) or getattr(cfg, 'move_processed_to', None),
        "max_attachment_mb": getattr(cfg, 'imap_max_attachment_mb', None) or getattr(cfg, 'max_attachment_mb', None) or 50,
        # SMTP opcional (para futuros usos)
        "smtp": {
            "host": smtp_host,
            "port": smtp_port,
            "ssl": smtp_ssl,
            "starttls": smtp_starttls,
            "username": smtp_user,
            "password": smtp_pass,
        }
    }
