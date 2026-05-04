# Skill: DRF ViewSet — SINTEL v2.62

**Carga cuando:** Crear o editar un ViewSet, endpoint REST, acción HTMX.

---

## Plantilla Base Obligatoria

```python
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.api.utils import render_template_safe
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

class MiModeloViewSet(MiModeloServiceMixin, BaseTenantViewSet):
    queryset = MiModelo.objects.none()    # requerido por DRF router
    serializer_class = MiModeloDetailSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_object(self):
        """Double Semantic Verification (DSV)."""
        pk = self.kwargs.get(self.lookup_url_kwarg)
        empresa = self.get_empresa()
        obj = MiModelo.objects.filter(pk=pk, empresa_id=empresa.id).first()
        if not obj:
            raise NotFound(f'MiModelo {pk} no encontrado.')
        return obj

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return MiModelo.objects.none()
        return self.selector.get_list(empresa.id)

    def list(self, request):
        search = request.query_params.get('search', '').strip()
        qs = self.selector.get_list(self.get_empresa().id, search or None)
        page = self.paginate_queryset(qs)
        serializer = MiModeloListSerializer(page or qs, many=True)
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    def create(self, request, *args, **kwargs):
        empresa = self.get_empresa()
        serializer = MiModeloDetailSerializer(data=request.data, context={'empresa_id': empresa.id})
        serializer.is_valid(raise_exception=True)
        obj = self.service.registrar(empresa.id, serializer.validated_data)
        return Response(MiModeloDetailSerializer(obj).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        obj = self.get_object() # DSV
        serializer = MiModeloDetailSerializer(obj, data=request.data, partial=False, context={'empresa_id': self.get_empresa().id})
        serializer.is_valid(raise_exception=True)
        # [CRITICAL HOTFIX] Pasar obj a `registrar` para bypass del Upsert en DB
        obj = self.service.registrar(self.get_empresa().id, serializer.validated_data, instance=obj)
        return Response(MiModeloDetailSerializer(obj).data)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object() # DSV
        serializer = MiModeloDetailSerializer(obj, data=request.data, partial=True, context={'empresa_id': self.get_empresa().id})
        serializer.is_valid(raise_exception=True)
        # [CRITICAL HOTFIX] Pasar obj a `registrar` para evitar IntegrityError en PATCH con payload parcial
        obj = self.service.registrar(self.get_empresa().id, serializer.validated_data, instance=obj)
        return Response(MiModeloDetailSerializer(obj).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id  # Capturar ANTES de eliminar
        self.crud.eliminar(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
```

## Acción HTMX (render-offcanvas)

```python
@action(
    detail=False,
    methods=['get'],
    renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
    url_path='render-offcanvas/crear'
)
def render_offcanvas_crear(self, request):
    empresa = self.get_empresa()
    context = {'empresa': empresa, 'modo': 'crear'}
    return render_template_safe(context, 'tenant/<app>/offcanvas_crear_<modelo>.html', request=request)

@action(
    detail=True,
    methods=['get'],
    renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
    url_path='render-offcanvas/editar'
)
def render_offcanvas_editar(self, request, id=None):
    obj = self.get_object()
    context = {'obj': obj, 'modo': 'editar'}
    return render_template_safe(context, 'tenant/<app>/offcanvas_editar_<modelo>.html', request=request)
```

## URLs (api/urls.py)

```python
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'', MiModeloViewSet, basename='mimodelo')
urlpatterns = router.urls
```

## config/api_urls.py — Registro

```python
try:
    from apps.tenant.<app>.api.urls import urlpatterns as <app>_urls
    urlpatterns += [path('api/v1/<app>/', include(<app>_urls))]
except ImportError:
    pass
```

## Reglas Críticas
- `queryset = Modelo.objects.none()` a nivel de clase (nunca `.all()`)
- DSV **siempre** en `get_object()`: filtrar por `empresa_id`
- Capturar `obj.id`, `obj.numero`, etc. ANTES de llamar a `eliminar()`
- `render_template_safe()` para endpoints HTMX — nunca `Response(template_name=...)`
- `lookup_field = 'id'` (UUID en producción, pero 'id' en módulos existentes)
- **[CRITICAL HOTFIX]**: Si defines `lookup_url_kwarg = 'id'`, la firma de los métodos `@action(detail=True)` DEBE usar `id=None` (no `pk=None`), o DRF lanzará `TypeError: unexpected keyword argument 'id'`.
- **[CRITICAL HOTFIX]**: Si un ViewSet requiere acceder a datos/selectores de un modelo relacionado (ej. cargar detalles de una sub-entidad dentro del Offcanvas), el ViewSet **DEBE** heredar explícitamente el ServiceMixin correspondiente (ej. `<ModeloRelacionado>ServiceMixin`) para evitar `AttributeError`.
