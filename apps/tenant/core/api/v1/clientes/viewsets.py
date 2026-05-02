"""Core API v1 - Clientes facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
- # WARNING: v2.61: Alineado con patrón de cotizaciones y contabilidad.
"""

from apps.tenant.clientes.api.viewsets import ClienteViewSet, ContactoClienteViewSet

from . import serializers as ws_serializers


class ClienteCoreViewSet(ClienteViewSet):
    """
    Facade ViewSet para Clientes en Core API v1.
    
    Hereda toda la funcionalidad de ClienteViewSet:
    - CRUD completo (list, retrieve, create, update, partial_update, destroy)
    - @action endpoints HTMX para renderizado de offcanvas (heredados)
    - Validaciones de negocio (inactivar antes de borrar)
    - Zero Trust (filtrado por empresa del tenant)
    
    Endpoints REST:
    - GET /api/v1/clientes/ - Lista paginada
    - POST /api/v1/clientes/ - Crear
    - GET /api/v1/clientes/{id}/ - Detalle
    - PUT/PATCH /api/v1/clientes/{id}/ - Actualizar
    - DELETE /api/v1/clientes/{id}/ - Eliminar
    
    Endpoints HTMX (heredados de ClienteViewSet):
    - GET /api/v1/clientes/render-offcanvas/crear/ - Renderizar offcanvas crear
    - GET /api/v1/clientes/{id}/render-offcanvas/editar/ - Renderizar offcanvas editar
    - GET /api/v1/clientes/render-offcanvas/detalle/?id={id} - Renderizar offcanvas detalle
    - GET /api/v1/clientes/offcanvas/?id={id} - Renderizar offcanvas legacy (compatibilidad)
    """
    def get_serializer_class(self):
        """
        Selecciona el serializer según la acción.
        
        - list: ClienteWorkspaceListSerializer (optimizado para Tabulator)
        - retrieve/create/update: ClienteWorkspaceDetailSerializer (completo)
        """
        if self.action == 'list':
            return ws_serializers.ClienteWorkspaceListSerializer
        return ws_serializers.ClienteWorkspaceDetailSerializer


class ContactoClienteCoreViewSet(ContactoClienteViewSet):
    """
    Facade ViewSet para Contactos de Cliente en Core API v1.
    
    Hereda toda la funcionalidad de ContactoClienteViewSet:
    - CRUD completo (list, retrieve, create, update, partial_update, destroy)
    - @action gestor_offcanvas para renderizado HTML (HTMX)
    - Zero Trust (filtrado por empresa del tenant)
    - Grid global (Directorio de Contactos)
    
    Endpoints:
    - GET /api/v1/core/v1/clientes/contactos/ - Lista paginada
    - POST /api/v1/core/v1/clientes/contactos/ - Crear
    - GET /api/v1/core/v1/clientes/contactos/{id}/ - Detalle
    - PUT/PATCH /api/v1/core/v1/clientes/contactos/{id}/ - Actualizar
    - DELETE /api/v1/core/v1/clientes/contactos/{id}/ - Eliminar
    - GET /api/v1/core/v1/clientes/contactos/gestor-offcanvas/ - Renderizar HTML (HTMX)
    """
    serializer_class = ws_serializers.ContactoClienteWorkspaceSerializer
