"""
Gestión del estado del buzón IMAP para procesamiento incremental.

⚠️ MÓDULO PURO: Solo modelos Django, sin dependencias de Celery, core, o maildigester.
⚠️ SEGURO PARA URLS: Puede importarse desde cualquier lugar sin crear ciclos.

Este módulo gestiona el estado del procesamiento IMAP usando UIDs para evitar
reprocesar correos ya examinados.
"""
from __future__ import annotations
from typing import Optional
from django.db import transaction
from django.utils import timezone
from apps.tenant.facturas.models import MailInboxState


def get_or_create_inbox_state(config_id: int) -> MailInboxState:
    """
    Obtiene o crea el estado del buzón para una configuración.
    
    ⚠️ SSoT: Un estado por configuración (unique_together).
    
    Args:
        config_id: ID de MailInboxConfig
        
    Returns:
        MailInboxState existente o nuevo (con last_seen_uid=None)
        
    Raises:
        ValueError: Si la configuración no existe o no está activa
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    try:
        config = MailInboxConfig.objects.get(id=config_id, is_active=True)
    except MailInboxConfig.DoesNotExist:
        raise ValueError(f"Configuración {config_id} no existe o no está activa")
    
    state, created = MailInboxState.objects.get_or_create(
        mailbox_config=config,
        defaults={
            "last_seen_uid": None,  # Primera ejecución = histórico completo
            "total_processed": 0,
        }
    )
    
    return state


def update_inbox_state(config_id: int, last_uid: Optional[int], messages_processed: int) -> None:
    """
    Actualiza el estado del buzón después de procesar un lote.
    
    ⚠️ ATOMICIDAD: Usa transaction.atomic() para evitar condiciones de carrera.
    
    Args:
        config_id: ID de MailInboxConfig
        last_uid: Último UID procesado (None si no se procesó ningún mensaje)
        messages_processed: Número de mensajes procesados en este lote
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    try:
        config = MailInboxConfig.objects.get(id=config_id, is_active=True)
    except MailInboxConfig.DoesNotExist:
        return  # Config eliminada, no actualizar estado
    
    with transaction.atomic():
        state, _ = MailInboxState.objects.get_or_create(
            mailbox_config=config,
            defaults={"last_seen_uid": None, "total_processed": 0}
        )
        
        if last_uid is not None:
            # Actualizar solo si el nuevo UID es mayor
            if state.last_seen_uid is None or last_uid > state.last_seen_uid:
                state.last_seen_uid = last_uid
                state.total_processed += messages_processed
                state.last_run_at = timezone.now()
                state.save(update_fields=["last_seen_uid", "total_processed", "last_run_at", "updated_at"])


def get_inbox_state(config_id: int) -> Optional[MailInboxState]:
    """
    Obtiene el estado del buzón para una configuración.
    
    Args:
        config_id: ID de MailInboxConfig
        
    Returns:
        MailInboxState o None si no existe
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    try:
        config = MailInboxConfig.objects.get(id=config_id, is_active=True)
        return MailInboxState.objects.filter(mailbox_config=config).first()
    except MailInboxConfig.DoesNotExist:
        return None
