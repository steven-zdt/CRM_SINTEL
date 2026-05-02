"""
FacturaServiceMixin — Inyección de dependencias para Controladores (ViewSets).

Responsabilidad única: Proveer acceso estandarizado a la capa de servicios
desde el ViewSet, asegurando la inyección de empresa_id (Anti-IDOR).
"""

from apps.tenant.facturas.services.business_service import FacturaBusinessService
from apps.tenant.facturas.services.crud_service import FacturaCRUDService
from apps.tenant.facturas.services.selectors import FacturaSelectors


class FacturaServiceMixin:
    """
    Mixin para FacturaViewSet que delega en la Service Layer modular.
    """

    # --- Acceso a Selectors (v3.5 Zero Waste) ---
    def get_qs_list(self, search=None):
        """Retorna QuerySet optimizado para listados."""
        return FacturaSelectors.qs_list(search=search)

    def get_qs_detail(self):
        """Retorna QuerySet optimizado para detalle."""
        return FacturaSelectors.qs_detail()

    def get_summary(self, empresa_id):
        """Retorna resumen financiero."""
        return FacturaSelectors.get_summary(empresa_id=empresa_id)

    # --- Acceso a CRUD Service ---
    def service_eliminar(self, instance):
        """Elimina una factura y sus relacionados."""
        return FacturaCRUDService.eliminar(instance)

    # --- Acceso a Business Service ---
    def service_importar_documento(self, file_bytes, **kwargs):
        """Orquesta la importación de un documento UBL/PDF."""
        return FacturaBusinessService.importar_documento(file_bytes, **kwargs)

    def service_materializar(self, result, empresa_id):
        """Materializa una factura desde un resultado previo del pipeline."""
        return FacturaBusinessService.materializar_desde_result(result, empresa_id=empresa_id)

    def service_obtener_xml(self, factura, tipo):
        """Retorna el XML de un anexo."""
        return FacturaBusinessService.obtener_xml(factura, tipo)
