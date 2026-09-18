"""DEPRECADO v2.61.8: Wrapper de compatibilidad.

La SSoT de permisos basados en rol es `apps.tenant.api.permissions`.
Este modulo reexporta IsTenantAdmin desde la fuente central.
Todo nuevo codigo DEBE importar desde `apps.tenant.api.permissions`.
"""
import logging
import warnings

from apps.tenant.api.permissions import IsTenantAdmin  # noqa: F401  SSoT

_log = logging.getLogger("empresa.permissions")

warnings.warn(
    "apps.tenant.empresa.permissions.IsTenantAdmin esta deprecado. "
    "Importar desde apps.tenant.api.permissions en su lugar.",
    DeprecationWarning,
    stacklevel=2,
)
_log.info("DEPRECATION: empresa.permissions importado — migrar a api.permissions")
