"""
FacturaServiceMixin — Inyección de dependencias para Controladores (ViewSets).

Responsabilidad única: Proveer acceso estandarizado a la capa de servicios
desde el ViewSet, asegurando la inyección de empresa_id (Anti-IDOR).
"""

from apps.tenant.facturas.services.business_service import FacturaBusinessService
from apps.tenant.facturas.services.selectors import FacturaSelectors


class FacturaServiceMixin:
    """
    Mixin para FacturaViewSet que delega en la Service Layer modular.
    """

    # --- Acceso a Selectors (v3.5 Zero Waste) ---
    def get_qs_list(self, empresa_id=None, search=None, sede_ids=None):
        """Retorna QuerySet optimizado para listados (empresa_id aplicado en selector)."""
        return FacturaSelectors.qs_list(empresa_id=empresa_id, search=search, sede_ids=sede_ids)

    def get_qs_detail(self, empresa_id=None, sede_ids=None):
        """Retorna QuerySet optimizado para detalle (empresa_id aplicado en selector)."""
        return FacturaSelectors.qs_detail(empresa_id=empresa_id, sede_ids=sede_ids)

    def get_summary(self, empresa_id):
        """Retorna resumen financiero."""
        return FacturaSelectors.get_summary(empresa_id=empresa_id)

    # --- Acceso a CRUD Service ---
    def service_eliminar(self, instance):
        """
        Elimina una factura y sus relacionados -- solo si esta en BORRADOR
        (REM P0-01, docs/remediation/REM-P0-01.md). Delegado a
        FacturaBusinessService.eliminar_factura() para que la validacion de
        estado viva en la capa de negocio, no en el CRUD puro.
        """
        return FacturaBusinessService.eliminar_factura(instance)

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

    def service_obtener_retenciones_cliente(self, cliente_nit, empresa_id):
        """Obtiene retenciones desde Cliente."""
        return FacturaBusinessService.obtener_retenciones_desde_cliente(cliente_nit, empresa_id)

    def service_vincular_cliente(self, factura, cliente_uuid, empresa_id):
        """Vincula un cliente existente a una factura de venta."""
        return FacturaBusinessService.vincular_cliente(factura, cliente_uuid, empresa_id)

    def service_vincular_proveedor(self, factura, proveedor_uuid, empresa_id):
        """Vincula un proveedor existente a una factura de compra."""
        return FacturaBusinessService.vincular_proveedor(factura, proveedor_uuid, empresa_id)

    def service_obtener_retenciones_proveedor(self, proveedor_nit, empresa_id):
        """Obtiene retenciones desde Proveedor."""
        return FacturaBusinessService.obtener_retenciones_desde_proveedor(proveedor_nit, empresa_id)
