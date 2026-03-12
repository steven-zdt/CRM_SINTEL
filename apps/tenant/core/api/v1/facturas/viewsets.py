"""Core API v1 - Facturas facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
- ⚠️ v2.61.1: Alineado con patrón de cotizaciones
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.facturas.api.viewsets import (
    FacturaViewSet,
    ItemFacturaViewSet,
    NotaCreditoViewSet,
)

from . import serializers as ws_serializers


class FacturaCoreViewSet(FacturaViewSet):
    """
    ⚠️ v2.61.2: Facade ViewSet para Facturas en Core API.
    
    Hereda todas las acciones @action de FacturaViewSet:
    - importar-ubl: POST
    - summary: GET
    - upload-ubl: POST (con batch processing y pre-validación v2.61.2)
    - upload-document: POST
    - ingest/{task_id}/status: GET
    - create-from-dto: POST (NO usa serializer, recibe DTO directamente)
    - materialize: POST
    - xml: GET (detail)
    - app-response: GET (detail)
    - update-inbox-state: POST
    - gestor-offcanvas: GET (TemplateHTMLRenderer)
    
    ⚠️ v2.61.2: OPTIMIZACIONES:
    - Batch processing: upload-ubl soporta files[] (múltiples archivos)
    - Pre-validación de idempotencia: extrae CUFE/CUDE con regex antes del parsing completo
    - Silent Success: actualiza FacturaAnexos si XML nuevo es más completo
    """
    authentication_classes = [SessionAuthentication]
    
    def get_serializer_class(self):
        # ⚠️ v2.61.2: create-from-dto NO usa serializer, recibe DTO directamente en request.data
        # Las acciones @action que no usan serializer deben retornar None o no llamar a get_serializer_class
        if self.action == 'list':
            return ws_serializers.FacturaWorkspaceListSerializer
        elif self.action == 'retrieve':
            return ws_serializers.FacturaWorkspaceDetailSerializer
        elif self.action in ['create-from-dto', 'materialize', 'importar-ubl', 'upload-ubl', 'upload-document']:
            # ⚠️ Estas acciones no usan serializer, trabajan directamente con request.data
            # Retornar None para que DRF no intente validar con serializer
            return None
        # Para otras acciones (create, update, partial_update), usar el serializer de escritura
        return ws_serializers.FacturaWorkspaceSerializer
    
    def get_serializer(self, *args, **kwargs):
        # ⚠️ v2.61.2: Si get_serializer_class retorna None, no crear serializer
        # Esto evita errores cuando las acciones @action no usan serializer
        serializer_class = self.get_serializer_class()
        if serializer_class is None:
            return None
        return super().get_serializer(*args, **kwargs)


class ItemFacturaCoreViewSet(ItemFacturaViewSet):
    """
    ⚠️ v2.61.1: Facade ViewSet para Items de Factura en Core API.
    """
    authentication_classes = [SessionAuthentication]
    serializer_class = ws_serializers.ItemFacturaWorkspaceSerializer


class NotaCreditoCoreViewSet(NotaCreditoViewSet):
    """
    ⚠️ v2.61.1: Facade ViewSet para Notas Crédito en Core API.
    
    Hereda todas las acciones @action de NotaCreditoViewSet:
    - xml: GET (detail)
    """
    authentication_classes = [SessionAuthentication]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.NotaCreditoWorkspaceListSerializer
        return ws_serializers.NotaCreditoWorkspaceDetailSerializer
