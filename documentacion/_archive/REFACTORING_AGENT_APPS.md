---
name: refactoring_agent_apps
scope: SINTEL v2.61.4
version: 5.0
description: Guia de Refactorizacion de Apps - Alineada con AGENTS.md
---

# REFACTORING_AGENT_APPS.md (v5.0) -- Guia de Refactorizacion Alineada con AGENTS.md

Proceso estandar para refactorizar apps tenant existentes segun `AGENTS.md`. Referencia suprema: `AGENTS.md` > este documento.

## [CRITICAL] Regla 0: Cero Emojis en Python

Antes de cualquier modificacion, validar: `python -m py_compile archivo.py`. Cero caracteres Unicode/multibyte en archivos `.py` (ver AGENTS.md Seccion 0).

## [PHASE-0] Auditoria Pre-Refactorizacion

Ejecutar ANTES de modificar cualquier archivo:

1. **Modelos**: Herencia actual (`models.Model` vs `SintelTenantBaseModel`), ForeignKeys, constraints.
2. **Service Layer**: Logica dispersa en `save()`, `clean()`, ViewSets que debe migrar a `business_service.py`.
3. **Consultas**: Detectar `.all()`, `.filter()` sin `.only()` o `.defer()`.
4. **Seguridad**: Filtrado por `empresa_id`, puntos IDOR, resolucion de tenant.
5. **Lectura obligatoria**: `apps/tenant/<app_name>/AUDITORIA_FLUJO_COMPLETO.md` si existe.

## [PHASE-1] Estabilizacion del Backend

### 1.1. Modelos (CORE-DB)
```python
# ANTES (INCORRECTO)
class MiModelo(models.Model):
    nombre = models.CharField(max_length=100)

# DESPUES (CORRECTO) - empresa, created_at, updated_at se inyectan automaticamente
from apps.tenant.core.models import SintelTenantBaseModel

class MiModelo(SintelTenantBaseModel):
    nombre = models.CharField(max_length=100)
```

### 1.2. Service Layer Modular (OBLIGATORIO)

Estructura de archivos (2 niveles):
```
apps/tenant/<app_name>/
+-- services.py              # Fachada raiz legacy (reexporta para compatibilidad)
+-- services/
    +-- __init__.py           # Punto de entrada, exports limpios
    +-- selectors.py          # Consultas GET optimizadas (LIST_FIELDS/DETAIL_FIELDS)
    +-- crud_service.py       # Persistencia transaccional (@transaction.atomic)
    +-- business_service.py   # Logica de negocio, validaciones, orquestacion
    +-- api_mixins.py         # <Modelo>ServiceMixin para ViewSets
```

**NOTA:** `services.py` (fachada) esta en la RAIZ de la app, NO dentro del paquete `services/`. Coexisten.

#### `selectors.py` - Consultas read-only SSoT
```python
LIST_FIELDS = (
    "id", "empresa_id", "nombre", "activo", "created_at"
)
DETAIL_FIELDS = LIST_FIELDS + ("descripcion", "observaciones")

class MiModeloSelector:
    @staticmethod
    def get_list(empresa_id, search=None):
        qs = MiModelo.objects.filter(
            empresa_id=empresa_id
        ).only(*LIST_FIELDS).order_by("-created_at")
        if search:
            qs = qs.filter(nombre__icontains=search)
        return qs

    @staticmethod
    def get_detail(empresa_id, pk):
        return MiModelo.objects.filter(
            empresa_id=empresa_id, pk=pk
        ).only(*DETAIL_FIELDS).first()
```

#### `crud_service.py` - Persistencia pura
```python
from django.db import transaction

class MiModeloCRUDService:
    @staticmethod
    @transaction.atomic
    def crear(data: dict, empresa):
        return MiModelo.objects.create(empresa=empresa, **data)

    @staticmethod
    @transaction.atomic
    def actualizar(instance, data: dict):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save(update_fields=list(data.keys()))
        return instance
```

#### `business_service.py` - Logica de negocio
```python
from apps.tenant.<app_name>.services.crud_service import MiModeloCRUDService

class MiModeloBusinessService:
    @staticmethod
    def procesar(data: dict, empresa):
        # Validaciones semanticas, calculos, idempotencia
        # Delega persistencia a CRUDService
        return MiModeloCRUDService.crear(data, empresa)
```

#### `api_mixins.py` - Inyeccion de servicios en ViewSets
```python
from apps.tenant.<app_name>.services.selectors import MiModeloSelector
from apps.tenant.<app_name>.services.business_service import MiModeloBusinessService
from apps.tenant.<app_name>.services.crud_service import MiModeloCRUDService

class MiModeloServiceMixin:
    """Requiere que el ViewSet herede de SintelDSVMixin."""
    selector_class = MiModeloSelector
    business_service_class = MiModeloBusinessService
    crud_service_class = MiModeloCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search')
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))
```

#### `__init__.py` - Exports limpios
```python
from .selectors import MiModeloSelector
from .crud_service import MiModeloCRUDService
from .business_service import MiModeloBusinessService
from .api_mixins import MiModeloServiceMixin

__all__ = [
    'MiModeloSelector',
    'MiModeloCRUDService',
    'MiModeloBusinessService',
    'MiModeloServiceMixin',
]
```

### 1.3. ViewSets con Zero-Trust
```python
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin, SintelServiceMixin
from apps.tenant.api.permissions import IsTenantMember
from apps.tenant.<app_name>.models import MiModelo
from apps.tenant.<app_name>.services.api_mixins import MiModeloServiceMixin

class MiModeloViewSet(
    SintelDSVMixin,       # get_empresa_id()
    MiModeloServiceMixin, # get_qs_list(), get_qs_detail()
    BaseTenantViewSet     # lookup_field="uuid"
):
    queryset = MiModelo.objects.none()  # DRF route registration (OBLIGATORIO)
    permission_classes = [IsTenantMember]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Delega a ServiceMixin - ya filtra por empresa_id internamente."""
        if not hasattr(self, 'action') or self.action is None:
            return MiModelo.objects.none()
        if self.action == 'list':
            return self.get_qs_list()
        elif self.action == 'retrieve':
            return self.get_qs_detail()
        return MiModelo.objects.filter(
            empresa_id=self.get_empresa_id()
        )

    # --- HTMX Offcanvas Endpoints ---
    @action(detail=False, methods=['get'],
            renderer_classes=[TemplateHTMLRenderer],
            url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """Renderiza offcanvas via HTMX (crear/editar/detalle)."""
        context = {}
        return Response(context,
            template_name='tenant/<app_name>/offcanvas_crear_modelo.html')
```

**Patron clave:** Los endpoints HTMX usan `@action` con `TemplateHTMLRenderer` directamente en el ViewSet. NO usar `views.py` tradicionales (AGENTS.md Sec 4.3).

## [PHASE-2] Refactorizacion de UI

### 2.1. Templates (Feature-Sliced)

Ruta real: `apps/tenant/<app_name>/templates/tenant/<app_name>/`

```
templates/tenant/<app_name>/
+-- list.html                           # Lista principal
+-- offcanvas_crear_{modelo}.html       # Formulario creacion
+-- offcanvas_editar_{modelo}.html      # Formulario edicion
+-- offcanvas_detalle_{modelo}.html     # Vista detalle
+-- assets_{app_name}.html              # Carga de JS/CSS
+-- partials/
    +-- table.html                      # Tabla Tabulator parcial
    +-- offcanvas_factura.html           # Componentes reutilizables
```

**PROHIBIDO:** Templates monoliticos o modals compartidos entre modelos.

### 2.2. JavaScript Modular (Patron `features/`)

Ruta real: `apps/tenant/<app_name>/static/<app_name>/js/`

```
static/<app_name>/js/
+-- <app_name>.api.js              # SSoT de URLs y endpoints
+-- features/
    +-- {modelo}_list.js           # Tabla Tabulator
    +-- {modelo}_editor.js         # Formularios Offcanvas
```

Variante alternativa (apps simples con un solo modelo):
```
static/<app_name>/js/
+-- <app_name>.api.js
+-- <app_name>.main.js             # Orquestador central
+-- <app_name>.table.js
+-- <app_name>.ui.js
+-- <app_name>.utils.js
```

- **Namespace obligatorio:** `window.Sintel.<AppName>`
- **Helpers globales** en `apps/tenant/core/static/core/js/common/`: `ui-manager.js`, `tabulator.factory.js`, `notyf.init.js`
- **URLs en JS**: Usar Gateway Directo `/api/v1/<app_name>/`. PROHIBIDO `/api/v1/core/v1/` o `/api/v1/core/_apps/`.

### 2.3. DOM Shield Pattern
```javascript
// CORRECTO: Capturar valores crudos desde hidden inputs
const formData = {
    nombre: document.getElementById('nombre').value,
    cliente_id: document.getElementById('cliente_hidden').value
};
// INCORRECTO: Confiar en form.serialize() o atributos name visibles
```

## [PHASE-3] Alineacion con Gateway Directo

### 3.1. Registro de URLs

Cada app registra sus endpoints en `config/api_urls.py`:
```python
# config/api_urls.py
from apps.tenant.<app_name>.api.viewsets import MiModeloViewSet

router = DefaultRouter()
router.register(r'<app_name>', MiModeloViewSet, basename='<app_name>')
# Resultado: /api/v1/<app_name>/ (GET list, POST create, etc.)
```

- **PROHIBIDO:** Facades centralizadas que orquesten multiples apps.
- **Offcanvas HTMX:** Los endpoints `gestor-offcanvas` y `render-offcanvas/*` se definen como `@action` en el ViewSet (ver Phase 1.3).

## [PHASE-4] Validacion

```bash
# Compilacion Python (cero emojis, cero SyntaxError)
python -m py_compile apps/tenant/<app_name>/models.py
python -m py_compile apps/tenant/<app_name>/services/*.py
python -m py_compile apps/tenant/<app_name>/api/*.py

# Testing
python manage.py test apps.tenant.<app_name>
```

Verificaciones manuales:
- Queries: `.only()` o `.defer()` en todas las consultas
- Seguridad: Filtrado `empresa_id`, prevencion IDOR, DSV en mutaciones
- Tenant isolation: Datos solo del tenant autenticado

## [CHECKLIST] Conformidad Final

### Backend
- [ ] Modelos heredan de `SintelTenantBaseModel`
- [ ] Service Layer completo: `selectors.py`, `crud_service.py`, `business_service.py`, `api_mixins.py`, `__init__.py`
- [ ] `selectors.py` con `LIST_FIELDS`/`DETAIL_FIELDS` y `@staticmethod`
- [ ] `crud_service.py` con `@transaction.atomic` en mutaciones
- [ ] `api_mixins.py` con `get_qs_list()`/`get_qs_detail()`
- [ ] ViewSet: `BaseTenantViewSet` + `SintelDSVMixin` + `ServiceMixin`
- [ ] ViewSet: `queryset = Model.objects.none()` a nivel de clase
- [ ] ViewSet: `permission_classes = [IsTenantMember]`
- [ ] ViewSet: `pagination_class = StandardResultsSetPagination`
- [ ] HTMX offcanvas via `@action(renderer_classes=[TemplateHTMLRenderer])`
- [ ] `python -m py_compile` sin errores en todos los `.py`

### Frontend
- [ ] Templates en `templates/tenant/<app_name>/` (Feature-Sliced por modelo)
- [ ] JS bajo `window.Sintel.<AppName>` con `<app_name>.api.js` como SSoT de URLs
- [ ] URLs directas `/api/v1/<app_name>/` (cero refs a facade o gateway `_apps/`)
- [ ] DOM Shield en formularios (hidden inputs para FKs)

### Documentacion
- [ ] `AUDITORIA_FLUJO_COMPLETO.md` actualizado en la app

---

## [GOVERNANCE] Autorizacion Requerida

Para apps en `apps/tenant/`:
1. **Lectura obligatoria** de `apps/tenant/<app_name>/AUDITORIA_FLUJO_COMPLETO.md` (o `AUDITORIA_INVENTARIO.md` si existe)
2. **Autorizacion explicita** del usuario antes de modificaciones
3. **Alineacion estricta** con arquitectura documentada en AGENTS.md

---

*Referencia Suprema: AGENTS.md | SINTEL v2.61.4*
