from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response


class FacturaXMLMixin:
    """
    Mixin especializado para endpoints que exponen y entregan los artefactos pesados XML (UBL y ApplicationResponse).
    """

    @action(detail=True, methods=['get'], url_path='xml')
    def xml_ubl(self, request: Request, uuid=None) -> Response:
        """
        Retorna el UBL XML completo de la factura.
        
        # WARNING: FASE 6: Endpoint dedicado para artefactos pesados (XML).
        - Listas y detalle NO incluyen XML (solo metadatos)
        - Este endpoint retorna el XML completo con Content-Type: application/xml
        - Inline si <= 2MB, descarga forzada si mayor
        
        Returns:
            - 200 OK: XML completo con Content-Type: application/xml
            - 204 No Content: Si no hay XML disponible
            - 404 Not Found: Si la factura no existe
        """
        factura = self.get_object()
        payload, code = self.service_obtener_xml(factura, "ubl")
        if isinstance(payload, HttpResponse):
            return payload
        return Response(payload, status=code)
    
    @action(detail=True, methods=['get'], url_path='app-response')
    def xml_app_response(self, request: Request, uuid=None) -> Response:
        """
        Retorna el ApplicationResponse DIAN XML completo.
        
        # WARNING: FASE 6: Endpoint dedicado para artefactos pesados (ApplicationResponse XML).
        - Listas y detalle NO incluyen XML (solo metadatos)
        - Este endpoint retorna el XML completo con Content-Type: application/xml
        - Inline si <= 2MB, descarga forzada si mayor
        
        Returns:
            - 200 OK: XML completo con Content-Type: application/xml
            - 204 No Content: Si no hay ApplicationResponse disponible
            - 404 Not Found: Si la factura no existe
        """
        factura = self.get_object()
        payload, code = self.service_obtener_xml(factura, "app")
        if isinstance(payload, HttpResponse):
            return payload
        return Response(payload, status=code)
