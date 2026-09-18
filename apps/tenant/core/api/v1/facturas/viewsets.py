"""Core API v1 - Facturas facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
- # WARNING: v2.61.1: Alineado con patrón de cotizaciones
"""

from apps.tenant.facturas.api.viewsets import (
    FacturaViewSet,
    ItemFacturaViewSet,
    NotaCreditoViewSet,
)

from . import serializers as ws_serializers


class FacturaCoreViewSet(FacturaViewSet):
    """
    # WARNING: v2.61.2: Facade ViewSet para Facturas en Core API.
    
    Hereda todas las acciones @action de FacturaViewSet:
    - summary: GET
    - upload-ubl: POST (con batch processing y pre-validación v2.61.2)
    - upload-document: POST
    - ingest/{task_id}/status: GET
    - create-from-dto: POST (NO usa serializer, recibe DTO directamente)
    - xml: GET (detail)
    - app-response: GET (detail)
    - update-inbox-state: POST
    - gestor-offcanvas: GET (TemplateHTMLRenderer)
    
    # WARNING: v2.61.2: OPTIMIZACIONES:
    - Batch processing: upload-ubl soporta files[] (múltiples archivos)
    - Pre-validación de idempotencia: extrae CUFE/CUDE con regex antes del parsing completo
    - Silent Success: actualiza FacturaAnexos si XML nuevo es más completo
    """
    def get_serializer_class(self):
        # # WARNING: v2.61.2: create-from-dto NO usa serializer, recibe DTO directamente en request.data
        # Las acciones @action que no usan serializer deben retornar None o no llamar a get_serializer_class
        if self.action == 'list':
            return ws_serializers.FacturaWorkspaceListSerializer
        elif self.action == 'retrieve':
            return ws_serializers.FacturaWorkspaceDetailSerializer
        elif self.action in ['create-from-dto', 'upload-ubl', 'upload-document']:
            # # WARNING: Estas acciones no usan serializer, trabajan directamente con request.data
            # Retornar None para que DRF no intente validar con serializer
            return None
        # Para otras acciones (create, update, partial_update), usar el serializer de escritura
        return ws_serializers.FacturaWorkspaceSerializer
    
    def get_serializer(self, *args, **kwargs):
        # # WARNING: v2.61.2: Si get_serializer_class retorna None, no crear serializer
        # Esto evita errores cuando las acciones @action no usan serializer
        serializer_class = self.get_serializer_class()
        if serializer_class is None:
            return None
        return super().get_serializer(*args, **kwargs)


class ItemFacturaCoreViewSet(ItemFacturaViewSet):
    """
    # WARNING: v2.61.1: Facade ViewSet para Items de Factura en Core API.
    """
    serializer_class = ws_serializers.ItemFacturaWorkspaceSerializer


class NotaCreditoCoreViewSet(NotaCreditoViewSet):
    """
    # WARNING: v2.61.1: Facade ViewSet para Notas Crédito en Core API.
    
    Hereda todas las acciones @action de NotaCreditoViewSet:
    - xml: GET (detail)
    """
    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.NotaCreditoWorkspaceListSerializer
        return ws_serializers.NotaCreditoWorkspaceDetailSerializer
