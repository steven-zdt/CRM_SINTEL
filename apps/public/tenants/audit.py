"""
Sistema de auditoría por tenant.

Este módulo proporciona funciones para registrar eventos de auditoría
específicos de cada tenant, con rotación automática de logs.
"""
import logging
import os
from datetime import datetime, timedelta
from django.conf import settings
from django_tenants.utils import get_tenant
from django.utils import timezone


class TenantAuditLogger:
    """
    Logger de auditoría específico por tenant.
    
    Crea logs separados por tenant con rotación automática.
    """
    
    def __init__(self, tenant_schema_name=None):
        """
        Inicializa el logger de auditoría para un tenant.
        
        Args:
            tenant_schema_name: Nombre del esquema del tenant (opcional, se detecta automáticamente)
        """
        if tenant_schema_name is None:
            try:
                tenant = get_tenant()
                tenant_schema_name = tenant.schema_name if tenant else 'public'
            except Exception:
                tenant_schema_name = 'public'
        
        self.tenant_schema_name = tenant_schema_name
        self.logger_name = f'audit_{tenant_schema_name}'
        self.logger = logging.getLogger(self.logger_name)
        
        # Configurar logger si no está configurado
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """Configura el logger con archivo por tenant."""
        # Directorio de logs de auditoría
        log_dir = getattr(settings, 'AUDIT_LOG_DIR', 'logs/audit')
        os.makedirs(log_dir, exist_ok=True)
        
        # Archivo de log por tenant
        log_file = os.path.join(log_dir, f'{self.tenant_schema_name}_audit.log')
        
        # Handler de archivo con rotación
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            log_file,
            maxBytes=getattr(settings, 'AUDIT_LOG_MAX_BYTES', 10 * 1024 * 1024),  # 10MB
            backupCount=getattr(settings, 'AUDIT_LOG_BACKUP_COUNT', 5),
            encoding='utf-8'
        )
        
        # Formato de log
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(tenant)s | %(user)s | %(action)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Nivel de log
        log_level = getattr(settings, 'AUDIT_LOG_LEVEL', logging.INFO)
        self.logger.setLevel(log_level)
        self.logger.addHandler(handler)
    
    def log_event(
        self,
        action: str,
        message: str,
        user=None,
        level=logging.INFO,
        extra_data=None
    ):
        """
        Registra un evento de auditoría.
        
        Args:
            action: Acción realizada (ej: 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', etc.)
            message: Mensaje descriptivo del evento
            user: Usuario que realizó la acción (opcional)
            level: Nivel de log (default: INFO)
            extra_data: Datos adicionales (opcional)
        """
        # Preparar contexto
        context = {
            'tenant': self.tenant_schema_name,
            'user': str(user) if user else 'system',
            'action': action,
        }
        
        # Agregar datos extra si existen
        if extra_data:
            message = f"{message} | Data: {extra_data}"
        
        # Registrar evento
        self.logger.log(level, message, extra=context)
    
    def log_create(self, model_name, instance_id, user=None, **kwargs):
        """Registra la creación de un objeto."""
        self.log_event(
            action='CREATE',
            message=f'Created {model_name} (id: {instance_id})',
            user=user,
            extra_data=kwargs
        )
    
    def log_update(self, model_name, instance_id, user=None, changes=None, **kwargs):
        """Registra la actualización de un objeto."""
        self.log_event(
            action='UPDATE',
            message=f'Updated {model_name} (id: {instance_id})',
            user=user,
            extra_data={'changes': changes, **kwargs}
        )
    
    def log_delete(self, model_name, instance_id, user=None, **kwargs):
        """Registra la eliminación de un objeto."""
        self.log_event(
            action='DELETE',
            message=f'Deleted {model_name} (id: {instance_id})',
            user=user,
            extra_data=kwargs
        )
    
    def log_login(self, user, ip_address=None, **kwargs):
        """Registra un inicio de sesión."""
        self.log_event(
            action='LOGIN',
            message=f'User login: {user}',
            user=user,
            extra_data={'ip_address': ip_address, **kwargs}
        )
    
    def log_logout(self, user, **kwargs):
        """Registra un cierre de sesión."""
        self.log_event(
            action='LOGOUT',
            message=f'User logout: {user}',
            user=user,
            extra_data=kwargs
        )
    
    def log_api_access(self, endpoint, method, user=None, status_code=None, **kwargs):
        """Registra acceso a una API."""
        self.log_event(
            action='API_ACCESS',
            message=f'{method} {endpoint}',
            user=user,
            extra_data={'status_code': status_code, **kwargs}
        )


def get_audit_logger(tenant_schema_name=None):
    """
    Obtiene un logger de auditoría para el tenant actual.
    
    Args:
        tenant_schema_name: Nombre del esquema del tenant (opcional)
        
    Returns:
        Instancia de TenantAuditLogger
    """
    return TenantAuditLogger(tenant_schema_name)
