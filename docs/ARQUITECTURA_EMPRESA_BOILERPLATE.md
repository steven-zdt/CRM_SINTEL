# Arquitectura de la App "Empresa" - Análisis y Guía de Replicación

**Versión:** 2.40  
**Fecha:** 2024  
**Objetivo:** Documentar el flujo de trabajo de la app "Empresa" y proporcionar un boilerplate para replicar esta arquitectura en futuras apps privadas.

---

## 1. Análisis de Flujo y Validación

### 1.1. Ciclo de Vida de una Solicitud: "Crear/Editar Empresa"

#### **Flujo Completo (End-to-End):**

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (JavaScript)                                            │
│ apps/tenant/core/static/core/js/empresa/empresa.page.js         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1. Usuario hace clic en "Crear Empresa"
                              │    → handleGuardarEmpresaUnified('create')
                              │
                              │ 2. collectEmpresaPayload() recolecta datos del formulario
                              │    → Retorna objeto plano: { razon_social, nit, ... }
                              │
                              │ 3. Validación: Verifica que payload NO sea FormData
                              │    → Convierte FormData a objeto plano si es necesario
                              │
                              │ 4. httpJSON('PATCH', '/api/v1/core/empresa/', payload)
                              │    → Headers: Accept, Content-Type: application/json, X-CSRFToken
                              │    → Body: JSON.stringify(payload)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CORE ORCHESTRATOR (API Gateway)                                 │
│ apps/tenant/core/api/views.py → MiEmpresaView.patch()           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 5. Validación temprana de payload
                              │    → Verifica que request.data sea dict y no esté vacío
                              │
                              │ 6. Determina si es creación o actualización
                              │    → Empresa.objects.first() → None = crear, existe = actualizar
                              │
                              │ 7. Si creación:
                              │    → core_empresa_get_or_create() (vía adapter)
                              │    → Retorna 201 Created
                              │
                              │ 8. Si actualización:
                              │    → core_empresa_update() (vía adapter)
                              │    → Retorna 200 OK
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CORE SERVICE ADAPTER (Orquestación)                              │
│ apps/tenant/core/services/empresa_adapter.py                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 9. core_empresa_update() / get_or_create_empresa()
                              │    → Llama a servicios de la app empresa
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SERVICE LAYER (Lógica de Negocio)                               │
│ apps/tenant/empresa/services.py                                  │
│ apps/tenant/empresa/impl/empresa_service.py                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 10. get_or_create_empresa() / update_empresa()
                              │     → Lógica de negocio pura (sin dependencias de DRF)
                              │     → Validaciones, cálculos (DV), normalización
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATA LAYER (Persistencia)                                        │
│ apps/tenant/empresa/models.py → Empresa.save()                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 11. Modelo ejecuta clean() y save()
                              │     → Normalización de campos (trim, lowercase)
                              │     → Validación de constraints (singleton_key)
                              │     → Persistencia en BD
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ RESPUESTA (JSON)                                                 │
│ → 201 Created / 200 OK con datos de empresa                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 12. Frontend recibe respuesta
                              │     → Actualiza state.singletonId
                              │     → Cierra modal
                              │     → Recarga tabla (refreshEmpresaPanel())
                              │     → Muestra mensaje de éxito
```

### 1.2. Validación de Desacoplamiento

#### ✅ **Desacoplamiento Correcto:**

1. **API Layer → Service Layer:**
   - `MiEmpresaView.patch()` NO contiene lógica de negocio
   - Delega completamente a `core_empresa_update()` / `get_or_create_empresa()`
   - El adapter (`empresa_adapter.py`) actúa como puente entre Core y la app Empresa

2. **Service Layer → Model Layer:**
   - `services.py` y `impl/empresa_service.py` contienen toda la lógica de negocio
   - El modelo (`Empresa`) solo tiene validaciones básicas (`clean()`) y persistencia
   - No hay lógica de negocio en `models.py`

3. **Frontend → API:**
   - El frontend NO conoce la estructura interna de la base de datos
   - Usa contratos JSON canónicos definidos por los serializers
   - La UI está completamente desacoplada del backend

#### ⚠️ **Puntos de Atención:**

1. **Core Orchestrator como Única Vía de Mutación:**
   - La UI está **forzada** a usar `PATCH /api/v1/core/empresa/` (ENFORCED MODE)
   - Los endpoints directos (`POST /api/v1/empresas/`) retornan 405 para no-staff
   - Esto garantiza que toda mutación pase por el orchestrator

2. **Manejo de Errores Consistente:**
   - Frontend: `httpJSON()` captura errores y los formatea para UI
   - API: DRF serializers validan y retornan errores estructurados
   - Service: Lanza excepciones específicas que el adapter convierte a respuestas HTTP

---

## 2. Documentación de Lógica

### 2.1. Estructura de Servicios

#### **Patrón Service Layer:**

```python
# apps/tenant/empresa/services.py
# ⚠️ PROVEEDOR PÚBLICO: Funciones exportadas para consumo externo

LIST_FIELDS = ("id", "razon_social", "nit", ...)  # Campos para listado
DETAIL_FIELDS = ("id", "razon_social", ..., "logo", "website")  # Campos para detalle

def qs_list():
    """QuerySet optimizado para listado (usa only() con LIST_FIELDS)"""
    return Empresa.objects.only(*LIST_FIELDS)

def qs_detail():
    """QuerySet optimizado para detalle (usa only() con DETAIL_FIELDS)"""
    return Empresa.objects.only(*DETAIL_FIELDS)

def get_empresa_data() -> Optional[Dict[str, Any]]:
    """Obtiene datos de empresa (SSoT para consumo interno)"""
    # Lógica de negocio pura
    # Retorna dict canónico o None

def get_empresa_emisor_data() -> Dict[str, Any]:
    """SSoT para datos del emisor (facturas)"""
    # Lanza EmpresaNotConfiguredError si no existe
```

#### **Implementación Interna:**

```python
# apps/tenant/empresa/impl/empresa_service.py
# ⚠️ IMPLEMENTACIÓN PRIVADA: Lógica de negocio detallada

def get_or_create_empresa(defaults: dict) -> Dict[str, Any]:
    """Crea empresa si no existe, retorna existente si ya existe"""
    # Lógica de singleton
    # Cálculo de DV
    # Normalización de datos
    # Retorna DTO (dict)

def update_empresa(data: dict) -> Dict[str, Any]:
    """Actualiza empresa existente"""
    # Validaciones
    # Actualización de campos
    # Retorna DTO actualizado
```

### 2.2. Convención de Nombres Frontend ↔ Backend

#### **Mapeo de Campos:**

| Frontend (JS) | Backend (Serializer) | Modelo (DB) |
|---------------|---------------------|-------------|
| `empresa-create-nit` | `nit` | `nit` |
| `empresa-create-razon_social` | `razon_social` | `razon_social` |
| `empresa-edit-direccion` | `direccion` | `direccion` |

**Regla:** Los IDs de los campos HTML siguen el patrón `{modalType}-{fieldName}`, donde `fieldName` coincide exactamente con el nombre del campo en el serializer.

#### **Funciones JavaScript:**

```javascript
// Recolectar datos del formulario
function collectEmpresaPayload(modalType) {
  // Prefijo: 'empresa-create' o 'empresa-edit'
  const prefix = modalType === 'create' ? 'empresa-create' : 'empresa-edit';
  
  // Mapeo directo: ID del input → clave del payload
  return {
    nit: d.getElementById(`${prefix}-nit`).value,
    razon_social: d.getElementById(`${prefix}-razon_social`).value,
    // ...
  };
}
```

### 2.3. Inyección de Templates Parciales

#### **Estructura de Templates:**

```
apps/tenant/core/templates/tenant/core/partials/empresa/
├── list.html          # Shell HTML para DataTables (tabla vacía)
├── modals.html        # Modales (crear, editar, ver)
├── mailinbox_list.html
└── mailinbox_modals.html
```

#### **Inclusión en Workspace:**

```django
{# apps/tenant/core/templates/tenant/core/workspace.html #}

<section id="tab-empresa" class="workspace-tab" style="display: none;">
  <!-- Módulo 1: Empresa -->
  {% include 'tenant/core/partials/empresa/list.html' %}
  {% include 'tenant/core/partials/empresa/modals.html' %}
  
  <!-- Módulo 2: MailInboxConfig -->
  {% include 'tenant/core/partials/empresa/mailinbox_list.html' %}
  {% include 'tenant/core/partials/empresa/mailinbox_modals.html' %}
</section>
```

#### **Inicialización JavaScript:**

```javascript
// empresa.page.js
// Lazy Loading: Solo se inicializa cuando el tab está visible
DOMUtils.onVisibleOnce(TAB_CONTAINER_ID, () => {
  initDataTableEmpresa();
  attachEventListeners();
});
```

---

## 3. Guía de Replicación (Boilerplate)

### 3.1. Estructura de Carpetas Requerida

```
apps/tenant/{app_name}/
├── __init__.py
├── apps.py                    # AppConfig con label explícito
├── models.py                  # Modelos de la app
├── services.py                # Service Provider (público)
├── impl/                      # Implementación privada
│   ├── __init__.py
│   └── {app_name}_service.py  # Lógica de negocio
├── api/
│   ├── __init__.py
│   ├── serializers.py         # Serializers DRF
│   ├── viewsets.py            # ViewSets DRF
│   ├── urls.py                # URLs de API
│   ├── permissions.py         # Permisos personalizados (opcional)
│   └── pagination.py          # Paginación (opcional)
├── migrations/
│   └── 0001_initial.py
└── templates/                   # Templates legacy (opcional)

apps/tenant/core/templates/tenant/core/partials/{app_name}/
├── list.html                  # Shell HTML para DataTables
└── modals.html                # Modales (crear, editar, ver)

apps/tenant/core/static/core/js/{app_name}/
├── {app_name}.page.js         # Módulo principal
├── {app_name}.api.js          # Helpers de API (opcional)
├── {app_name}.ui.js           # Helpers de UI (opcional)
└── {app_name}.modals.js       # Lógica de modales (opcional)
```

### 3.2. Plantilla Base: `models.py`

```python
"""
Modelos de {app_name} por tenant.

⚠️ IMPORTANTE: Estos modelos están en TENANT_APPS, por lo que:
- Cada tenant tiene sus propios datos
- NO usar foreign keys al esquema público (excepto User si es necesario)
- django-tenants maneja automáticamente el aislamiento por esquema
- No es necesario filtrar manualmente por tenant_id
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class {ModelName}(models.Model):
    """
    Descripción del modelo.
    
    ⚠️ PATRÓN: [Singleton | Collection]
    ⚠️ PRINCIPIOS:
    - Cero Signals: Toda la lógica está en la capa de servicios
    - Tenant Isolation: Cada tenant tiene sus propios datos
    - Service Layer: La lógica de negocio está en servicios
    """
    
    # Campos básicos
    nombre = models.CharField(
        max_length=255,
        verbose_name=_('Nombre'),
        help_text=_('Descripción del campo')
    )
    
    # Foreign Key a Empresa (requerido para ENFORCED MODE v2.40)
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='+',  # Evita reverse relation
        verbose_name=_('Empresa'),
        help_text=_('Empresa asociada')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('{ModelName}')
        verbose_name_plural = _('{ModelName}s')
        ordering = ['nombre']
        db_table = '{app_name}_{model_name}'
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["empresa"]),  # Para FK
        ]
    
    def __str__(self):
        return f"{self.nombre}"
    
    def clean(self):
        """Normaliza campos antes de guardar."""
        if self.nombre:
            self.nombre = self.nombre.strip()
        # Agregar más normalizaciones según necesidad
    
    def save(self, *args, **kwargs):
        """Asegura que clean() se ejecute antes de guardar."""
        self.full_clean()
        super().save(*args, **kwargs)
```

### 3.3. Plantilla Base: `services.py`

```python
"""
Servicio Provider para datos de {app_name} (consumo interno entre apps).

⚠️ POLÍTICA SSoT (Single Source of Truth):
- Este servicio es la ÚNICA fuente de datos de {app_name} para consumo interno
- Otras TENANT_APPS deben usar este servicio en lugar de duplicar campos
- NO hacer llamadas HTTP internas; usar ORM directo para evitar latencia

⚠️ v2.37: Service Layer Pattern - Toda la lógica de negocio está aquí.
Las vistas/serializers solo orquestan las llamadas a estos servicios.

Uso:
    from apps.tenant.{app_name}.services import get_{model_name}_data, qs_list
    
    # Obtener datos
    data = get_{model_name}_data(id)
    if data:
        nombre = data['nombre']
        # ...
"""
from typing import Dict, Any, Optional
from django.db import transaction
from apps.tenant.{app_name}.models import {ModelName}

# ⚠️ v2.37: LIST_FIELDS y DETAIL_FIELDS para alineación Serializers ↔ Services ↔ UI
LIST_FIELDS = (
    "id",
    "nombre",
    # ... campos para listado
    "created_at",
    "updated_at",
)

DETAIL_FIELDS = (
    "id",
    "nombre",
    # ... campos para detalle
    "created_at",
    "updated_at",
)


def qs_list():
    """
    QuerySet optimizado para listado (singleton o collection).
    
    ⚠️ v2.37: Usa LIST_FIELDS con only().
    ✅ Solo carga campos necesarios para la tabla
    """
    return {ModelName}.objects.only(*LIST_FIELDS)


def qs_detail():
    """
    QuerySet optimizado para detalle (retrieve).
    
    ⚠️ v2.37: Usa DETAIL_FIELDS con only().
    ✅ Solo carga campos necesarios para el detalle
    """
    return {ModelName}.objects.only(*DETAIL_FIELDS)


def get_{model_name}_data(id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene los datos de {model_name} por ID.
    
    ⚠️ POLÍTICA SSoT: Esta es la ÚNICA fuente de datos para consumo interno.
    
    Returns:
        Dict con datos o None si no existe:
        {
            'id': int,
            'nombre': str,
            # ... campos canónicos
        }
    """
    try:
        instance = {ModelName}.objects.only(*DETAIL_FIELDS).get(id=id)
        return {
            'id': instance.id,
            'nombre': instance.nombre,
            # ... mapeo de campos
        }
    except {ModelName}.DoesNotExist:
        return None
    except Exception:
        return None


@transaction.atomic
def crear_{model_name}(data: dict):
    """
    Crea una nueva instancia de {model_name}.
    
    Args:
        data: Dict con datos (contrato canónico del serializer)
    
    Returns:
        Instancia de {ModelName} creada
    
    Raises:
        ValueError: Si hay error de validación
    """
    from apps.tenant.{app_name}.impl.{app_name}_service import create_{model_name}
    
    # Usar servicio interno
    dto = create_{model_name}(data)
    instance = {ModelName}.objects.get(id=dto['id'])
    return instance


@transaction.atomic
def actualizar_{model_name}(instance, data: dict):
    """
    Actualiza una instancia existente.
    
    Args:
        instance: Instancia de {ModelName} a actualizar
        data: Dict con datos a actualizar (contrato canónico del serializer)
    
    Returns:
        Instancia de {ModelName} actualizada
    """
    from apps.tenant.{app_name}.impl.{app_name}_service import update_{model_name}
    
    # Usar servicio interno
    update_{model_name}(instance.id, data)
    return {ModelName}.objects.get(id=instance.id)
```

### 3.4. Plantilla Base: `api/viewsets.py`

```python
"""
ViewSets para la app {app_name}.

⚠️ v2.40: Configuración moderna con DataTables server-side y lazy loading.

⚠️ IMPORTANTE: 
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id
- JSON-first: JSONParser (principal) + FormParser (fallback para DataTables)
- SessionAuthentication + CSRF para workspace
"""
import logging
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer
from apps.tenant.{app_name}.models import {ModelName}
from apps.tenant.{app_name}.api.serializers import (
    {ModelName}ListSerializer,
    {ModelName}DetailSerializer,
    {ModelName}UpsertSerializer,
)
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.config.api.pagination import StandardResultsSetPagination

log = logging.getLogger("{app_name}.api")


class {ModelName}ViewSet(viewsets.ModelViewSet):
    """
    ViewSet para {ModelName}.
    
    ⚠️ v2.40: Configuración moderna con soporte para DataTables server-side.
    ⚠️ ENFORCED MODE: POST/PATCH/PUT solo para STAFF/ADMIN; no-staff recibe 405.
    
    ⚠️ JSON-ONLY (con fallback form-urlencoded para DataTables):
    - JSONParser (principal) + FormParser (fallback para compatibilidad)
    - Solo JSONRenderer (no BrowsableAPIRenderer)
    - Todas las respuestas son JSON
    
    ⚠️ SESSION AUTH + CSRF:
    - SessionAuthentication para workspace (cookies)
    - CSRF requerido en mutaciones (manejado por DRF)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination
    
    def _check_enforced_mode(self, request):
        """
        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        
        ⚠️ ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        """
        from rest_framework.permissions import SAFE_METHODS
        from apps.tenant.{app_name}.permissions import IsTenantAdmin
        
        if request.method in SAFE_METHODS:
            return True
        
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        
        return IsTenantAdmin().has_permission(request, self)
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == 'list':
            return {ModelName}ListSerializer
        elif self.action == 'retrieve':
            return {ModelName}DetailSerializer
        else:
            return {ModelName}UpsertSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado.
        
        ⚠️ Usa qs_list() o qs_detail() del service para optimización.
        """
        from apps.tenant.{app_name}.services import qs_list, qs_detail
        
        if self.action == 'list':
            return qs_list()
        else:
            return qs_detail()
    
    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Lista instancias (paginado).
        
        Endpoint: GET /api/v1/{app_name}/
        
        ⚠️ Retorna objeto paginado DRF: {count, results, next, previous}
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='dt/{model_name}')
    def datatables(self, request: Request) -> Response:
        """
        Endpoint DataTables server-side (POST obligatorio v2.40).
        
        ⚠️ v2.40: POST obligatorio según arquitectura, acepta JSON y form-urlencoded.
        ⚠️ OPTIMIZACIÓN: Usa qs_list() que ya aplica only() con LIST_FIELDS.
        ✅ Solo carga campos necesarios para la tabla
        ✅ Usa {ModelName}ListSerializer para serializar datos
        ✅ Maneja length=-1 cuando paginación está deshabilitada
        """
        from apps.tenant.{app_name}.services import qs_list
        
        # ⚠️ MANEJO ROBUSTO: request.data puede ser QueryDict (FormParser) o dict (JSONParser)
        if hasattr(request, 'data'):
            if hasattr(request.data, 'dict'):
                params = request.data.dict()
            elif isinstance(request.data, dict):
                params = request.data
            else:
                params = dict(request.data) if request.data else {}
        else:
            params = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
        
        try:
            draw = int(params.get("draw", "1"))
        except (ValueError, TypeError):
            draw = 1
        
        try:
            start = int(params.get("start", "0"))
            length = int(params.get("length", "10"))
        except (ValueError, TypeError):
            start, length = 0, 10
        
        # Manejar search
        search_value = ""
        if isinstance(params.get("search"), dict):
            search_value = params.get("search", {}).get("value", "") or ""
        elif "search[value]" in params:
            search_value = params.get("search[value]", "") or ""
        elif "search.value" in params:
            search_value = params.get("search.value", "") or ""
        search_value = search_value.strip()
        
        # Base queryset (usa qs_list() del service - LIST_FIELDS)
        qs = qs_list()
        records_total = qs.count()
        
        # Búsqueda simple sobre campos permitidos
        if search_value:
            qs = qs.filter(
                Q(nombre__icontains=search_value)
                # ... agregar más campos según necesidad
            )
        
        records_filtered = qs.count()
        
        # Orden (mapea columnas 0..n a campos del LIST_FIELDS)
        col_map = {
            "0": "nombre",
            # ... mapear más columnas
        }
        
        # ⚠️ MANEJO ROBUSTO: order puede venir como lista (JSONParser) o como dict anidado (FormParser)
        if isinstance(params.get("order"), list) and len(params.get("order", [])) > 0:
            order_col = str(params.get("order", [{}])[0].get("column", "0"))
            order_dir = params.get("order", [{}])[0].get("dir", "asc")
        elif "order[0][column]" in params:
            order_col = str(params.get("order[0][column]", "0"))
            order_dir = params.get("order[0][dir]", "asc")
        elif "order.0.column" in params:
            order_col = str(params.get("order.0.column", "0"))
            order_dir = params.get("order.0.dir", "asc")
        else:
            order_col = "0"
            order_dir = "asc"
        
        order_field = col_map.get(str(order_col), "nombre")
        
        if order_dir == "desc":
            order_field = f"-{order_field}"
        
        qs = qs.order_by(order_field)
        
        # Paginación (slice estilo DataTables)
        # ⚠️ CORRECCIÓN: Si length es -1, DataTables quiere todos los registros
        if length == -1:
            data_list = list(qs[start:])
        else:
            data_list = list(qs[start:start + length])
        
        # Serializar datos
        serializer = self.get_serializer(data_list, many=True)
        
        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    @transaction.atomic
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Crea una nueva instancia.
        
        Endpoint: POST /api/v1/{app_name}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden crear. No-staff recibe 405.
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "POST /api/v1/{app_name}/ solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        return Response(
            {ModelName}DetailSerializer(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED
        )
    
    @transaction.atomic
    def update(self, request: Request, *args, **kwargs) -> Response:
        """
        Actualiza una instancia existente (full update).
        
        Endpoint: PUT /api/v1/{app_name}/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden actualizar. No-staff recibe 405.
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PUT /api/v1/{app_name}/{id}/ solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=False,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {ModelName}DetailSerializer(serializer.instance, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK
        )
    
    @transaction.atomic
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        Actualiza parcialmente una instancia existente.
        
        Endpoint: PATCH /api/v1/{app_name}/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden actualizar. No-staff recibe 405.
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "PATCH /api/v1/{app_name}/{id}/ solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {ModelName}DetailSerializer(serializer.instance, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK
        )
    
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Elimina una instancia.
        
        Endpoint: DELETE /api/v1/{app_name}/{id}/
        
        ⚠️ ENFORCED MODE: Solo STAFF/ADMIN pueden eliminar. No-staff recibe 405.
        """
        # ⚠️ ENFORCED: Verificar permisos antes de procesar
        if not self._check_enforced_mode(request):
            return Response(
                {
                    "error": "method_not_allowed",
                    "detail": "DELETE /api/v1/{app_name}/{id}/ solo está permitido para usuarios ADMIN/STAFF."
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### 3.5. Plantilla Base: `api/serializers.py`

```python
"""
Serializers para la app {app_name}.

⚠️ v2.40: Alineado con configuración moderna de DataTables y lazy loading.

⚠️ CONTRATO CANÓNICO (DTO): Este serializer define el contrato estable de datos.
Todas las TENANT_APPS deben consumir este contrato vía API o servicio provider.

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from rest_framework import serializers
from apps.tenant.{app_name}.models import {ModelName}


class {ModelName}ListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado DataTables (POST server-side).
    
    ⚠️ v2.40: Exposición mínima - Solo campos visibles en la tabla.
    ⚠️ Alineado con LIST_FIELDS de services.py
    """
    class Meta:
        model = {ModelName}
        fields = (
            'id',
            'nombre',
            # ... campos para listado (alineados con LIST_FIELDS)
        )
        read_only_fields = fields


class {ModelName}DetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle (campos extendidos).
    
    ⚠️ Incluye todos los campos necesarios para el detalle.
    ⚠️ Alineado con DETAIL_FIELDS de services.py
    """
    class Meta:
        model = {ModelName}
        fields = (
            'id',
            'nombre',
            # ... campos para detalle (alineados con DETAIL_FIELDS)
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class {ModelName}UpsertSerializer(serializers.ModelSerializer):
    """
    Serializer para create/update (input validation).
    
    ⚠️ Valida datos de entrada antes de crear/actualizar.
    """
    class Meta:
        model = {ModelName}
        fields = (
            'nombre',
            # ... campos editables (sin id, created_at, updated_at)
        )
        extra_kwargs = {
            'nombre': {'required': True},
            # ... configurar más campos según necesidad
        }
    
    def validate_nombre(self, value):
        """Valida formato de nombre."""
        if not value:
            raise serializers.ValidationError("El nombre es obligatorio")
        return value.strip()
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        # Agregar validaciones cruzadas si es necesario
        return attrs
```

### 3.6. Plantilla Base: `api/urls.py`

```python
"""
URLs de API para la app {app_name}.

⚠️ v2.40: Arquitectura API-First con DataTables server-side.
- Todas las rutas están bajo /api/v1/{app_name}/
- Usa routers de DRF para generar endpoints automáticamente
- Endpoint DataTables: POST /api/v1/{app_name}/dt/{model_name}/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.tenant.{app_name}.api.viewsets import {ModelName}ViewSet

# Router para esta app
router = DefaultRouter()

# ⚠️ IMPORTANTE: No incluir el prefijo aquí porque ya está en config/api_urls.py
# El router se incluye con path('{app_name}/', include(...)), así que registramos sin prefijo
router.register(r'', {ModelName}ViewSet, basename='{app_name}')

# URLs generadas por el router
urlpatterns = router.urls
```

### 3.7. Plantilla Base: JavaScript (`{app_name}.page.js`)

```javascript
/**
 * {app_name}.page.js - Módulo {AppName} v2.40 (DataTables Server-Side POST con Lazy Loading)
 * 
 * ⚠️ v2.40: Configuración moderna de DataTables con JSON estricto y lazy loading
 * 
 * Configuración:
 * - DataTables Server-Side con POST obligatorio
 * - Lazy Loading: Se inicializa solo cuando el tab está visible
 * 
 * Dependencias globales requeridas:
 * - jQuery y DataTables
 * - API_HELPERS: authHeaders(), getCSRF()
 * - Routes: get()
 * - CRUD: read()
 * - DOMUtils: onVisibleOnce()
 */

(function (w, d) {
  'use strict';

  const NS = '[{app_name}.page]';
  const MOD = '{app_name}';
  const TABLE_ID = '#table-{app_name}';
  const TAB_CONTAINER_ID = '#tab-{app_name}';
  
  // Estado del módulo
  let state = {
    initialized: false,
    listenersAttached: false,
    table: null,
    routes: null,
  };

  // Logger
  const DEBUG = (w && (w.__DEBUG__ === true)) || (w?.API_HELPERS?.DEBUG === true) || false;
  function log(...args) {
    if (DEBUG) console.debug(NS, ...args);
  }
  function error(...args) {
    console.error(NS, ...args);
  }
  function warn(...args) {
    console.warn(NS, ...args);
  }

  // Guards del Core
  function requireCore() {
    if (!w.API_HELPERS) throw new Error('API_HELPERS no está disponible.');
    if (!w.DataTablesUtils) throw new Error('DataTablesUtils no está disponible.');
    if (!w.Routes) throw new Error('Routes no está disponible.');
    if (!w.CRUD) throw new Error('CRUD no está disponible.');
    if (!w.DOMUtils) throw new Error('DOMUtils no está disponible.');
  }

  /**
   * Inicializa DataTables con configuración server-side
   */
  async function initDataTable{AppName}() {
    requireCore();
    
    const tableEl = d.querySelector(TABLE_ID);
    if (!tableEl) {
      error('Tabla no encontrada:', TABLE_ID);
      return;
    }

    // Obtener ruta del DataTable desde Routes
    const routes = await w.Routes.get();
    const datatableUrl = routes?.[MOD]?.datatable || `/api/v1/${MOD}/dt/{model_name}/`;

    log('Inicializando DataTable en:', TABLE_ID, 'URL:', datatableUrl);

    state.table = $(TABLE_ID).DataTable({
      serverSide: true,
      processing: true,
      ajax: {
        url: datatableUrl,
        type: 'POST',
        contentType: 'application/json; charset=utf-8',
        processData: false,
        headers: w.API_HELPERS.authHeaders(),
        data: function (d) {
          return JSON.stringify(d);
        },
        error: function (xhr, textStatus, errorThrown) {
          error('Error en DataTable AJAX:', textStatus, errorThrown);
          const feedback = d.getElementById('feedback-{app_name}-list');
          if (feedback) {
            feedback.className = 'alert alert-danger';
            feedback.textContent = `Error cargando datos: ${errorThrown || textStatus}`;
            feedback.classList.remove('d-none');
          }
        }
      },
      columns: [
        { data: 'id', visible: false },
        { data: 'nombre', title: 'Nombre' },
        // ... más columnas según LIST_FIELDS
        {
          data: null,
          title: 'Acciones',
          orderable: false,
          searchable: false,
          className: 'text-end',
          render: function (data, type, row) {
            return `
              <button class="btn btn-sm btn-primary btn-{app_name}-editar" data-id="${row.id}">
                <i class="bi bi-pencil"></i> Editar
              </button>
              <button class="btn btn-sm btn-danger btn-{app_name}-eliminar" data-id="${row.id}">
                <i class="bi bi-trash"></i> Eliminar
              </button>
            `;
          }
        }
      ],
      paging: true,
      searching: true,
      ordering: true,
      pageLength: 10,
      language: {
        url: '/static/core/js/lib/datatables-es.json'
      }
    });

    log('DataTable inicializado exitosamente');
  }

  /**
   * Recolecta datos del formulario
   */
  function collect{AppName}Payload(modalType = 'create') {
    const prefix = modalType === 'create' ? '{app_name}-create' : '{app_name}-edit';
    
    return {
      nombre: d.getElementById(`${prefix}-nombre`)?.value || '',
      // ... recolectar más campos según necesidad
    };
  }

  /**
   * Llena formulario con datos
   */
  function populate{AppName}Form(data, modalType = 'edit') {
    const prefix = modalType === 'create' ? '{app_name}-create' : '{app_name}-edit';
    
    if (data.nombre) {
      const nombreEl = d.getElementById(`${prefix}-nombre`);
      if (nombreEl) nombreEl.value = data.nombre;
    }
    // ... poblar más campos según necesidad
  }

  /**
   * Limpia formulario
   */
  function clear{AppName}Form(modalType = 'create') {
    const prefix = modalType === 'create' ? '{app_name}-create' : '{app_name}-edit';
    const form = d.getElementById(`form-{app_name}-${modalType}`);
    if (form) {
      form.reset();
    }
    const feedback = d.getElementById(`${prefix}-feedback`);
    if (feedback) {
      feedback.classList.add('d-none');
      feedback.textContent = '';
    }
  }

  /**
   * Handler para crear/editar
   */
  async function handleGuardar{AppName}(modalType = 'create') {
    try {
      const payload = collect{AppName}Payload(modalType);
      log('Payload recolectado:', payload);

      // Validar payload
      if (!payload.nombre) {
        throw new Error('El nombre es obligatorio.');
      }

      const routes = await w.Routes.get();
      const url = modalType === 'create'
        ? routes?.[MOD]?.collection || `/api/v1/${MOD}/`
        : `${routes?.[MOD]?.detail?.replace('{id}', state.currentId)}` || `/api/v1/${MOD}/${state.currentId}/`;

      const method = modalType === 'create' ? 'POST' : 'PATCH';

      const data = await w.API_HELPERS.safeFetchJson(url, {
        method: method,
        body: payload
      });

      log('Guardado exitoso:', data);
      
      // Cerrar modal y recargar tabla
      const modalEl = d.getElementById(`modal-${modalType}-{app_name}`);
      if (modalEl) {
        const modal = w.bootstrap?.Modal?.getInstance?.(modalEl);
        if (modal) modal.hide();
      }
      
      if (state.table) {
        state.table.ajax.reload(null, false);
      }

    } catch (err) {
      error('Error guardando:', err);
      const feedback = d.getElementById(`{app_name}-${modalType}-feedback`);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = err.message || 'Error desconocido';
        feedback.classList.remove('d-none');
      }
    }
  }

  /**
   * Adjunta event listeners
   */
  function attachEventListeners() {
    if (state.listenersAttached) return;

    // Botón crear
    const btnCrear = d.getElementById('btn-{app_name}-crear');
    if (btnCrear) {
      btnCrear.addEventListener('click', () => {
        clear{AppName}Form('create');
        const modal = new w.bootstrap.Modal(d.getElementById('modal-create-{app_name}'));
        modal.show();
      });
    }

    // Botón guardar (crear)
    const btnGuardarCrear = d.getElementById('btn-guardar-{app_name}-create');
    if (btnGuardarCrear) {
      btnGuardarCrear.addEventListener('click', () => handleGuardar{AppName}('create'));
    }

    // Botones editar (delegación desde tabla)
    d.addEventListener('click', async (e) => {
      if (e.target.closest('.btn-{app_name}-editar')) {
        const btn = e.target.closest('.btn-{app_name}-editar');
        const id = parseInt(btn.dataset.id);
        
        try {
          const routes = await w.Routes.get();
          const url = routes?.[MOD]?.detail?.replace('{id}', id) || `/api/v1/${MOD}/${id}/`;
          const data = await w.CRUD.read(MOD, id);
          
          populate{AppName}Form(data, 'edit');
          state.currentId = id;
          
          const modal = new w.bootstrap.Modal(d.getElementById('modal-edit-{app_name}'));
          modal.show();
        } catch (err) {
          error('Error cargando datos:', err);
        }
      }
    });

    // Botón guardar (editar)
    const btnGuardarEdit = d.getElementById('btn-guardar-{app_name}-edit');
    if (btnGuardarEdit) {
      btnGuardarEdit.addEventListener('click', () => handleGuardar{AppName}('edit'));
    }

    state.listenersAttached = true;
    log('Event listeners adjuntados');
  }

  /**
   * Inicialización del módulo
   */
  async function init() {
    if (state.initialized) {
      log('Módulo ya inicializado');
      return;
    }

    requireCore();

    // Lazy Loading: Solo inicializar cuando el tab está visible
    w.DOMUtils.onVisibleOnce(TAB_CONTAINER_ID, async () => {
      log('Tab visible, inicializando módulo...');
      
      await initDataTable{AppName}();
      attachEventListeners();
      
      state.initialized = true;
      log('Módulo inicializado exitosamente');
    });
  }

  // Exportar API pública
  w.{AppName}Module = {
    init: init,
    refresh: () => {
      if (state.table) {
        state.table.ajax.reload(null, false);
      }
    }
  };

  // Auto-inicializar si DOM está listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(window, document);
```

### 3.8. Plantilla Base: Template HTML (`list.html`)

```django
{% load static %}
{# list.html - Shell HTML para DataTables Server-Side (POST) v2.40 #}
{# ⚠️ Alineado con {ModelName}ListSerializer y configuración moderna de DataTables #}
{# ⚠️ LAZY INIT: DataTables se inicializa solo cuando el tab está visible #}
<div id="ui-{app_name}-list" class="ui-module ui-{app_name}">
  <!-- Card Container -->
  <div class="card">
    <!-- Card Header -->
    <div class="card-header d-flex justify-content-between align-items-center">
      <h5 class="card-title mb-0">
        <i class="bi bi-{icon}"></i> {AppName}
      </h5>
      <div>
        <button id="btn-{app_name}-crear" class="btn btn-sm btn-success">
          <i class="bi bi-plus-circle"></i> Crear {ModelName}
        </button>
      </div>
    </div>
    
    <!-- Card Body -->
    <div class="card-body">
      <!-- Feedback -->
      <div id="feedback-{app_name}-list" class="alert d-none" role="alert" aria-live="polite"></div>
      
      <!-- Tabla DataTables (Shell - sin datos renderizados) -->
      <table id="table-{app_name}" class="table table-striped table-hover w-100" style="width:100%">
        <thead>
          <tr>
            <th>Nombre</th>
            <!-- ... más columnas según LIST_FIELDS -->
            <th class="text-end">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <!-- DataTables llenará esto vía AJAX POST con JSON -->
        </tbody>
      </table>
    </div>
  </div>
</div>
```

### 3.9. Checklist de Replicación

#### **Fase 1: Backend (Modelos y Servicios)**

- [ ] Crear estructura de carpetas: `apps/tenant/{app_name}/`
- [ ] Crear `models.py` con modelo base (incluir FK a Empresa si aplica)
- [ ] Crear migración inicial: `python manage.py makemigrations {app_name}`
- [ ] Crear `services.py` con `LIST_FIELDS`, `DETAIL_FIELDS`, `qs_list()`, `qs_detail()`
- [ ] Crear `impl/{app_name}_service.py` con lógica de negocio
- [ ] Crear `api/serializers.py` con `ListSerializer`, `DetailSerializer`, `UpsertSerializer`
- [ ] Crear `api/viewsets.py` con `ViewSet` completo (incluir `datatables` action)
- [ ] Crear `api/urls.py` y registrar router
- [ ] Registrar URLs en `config/api_urls.py`: `path('{app_name}/', include('apps.tenant.{app_name}.api.urls'))`
- [ ] Agregar app a `TENANT_APPS` en `config/settings.py`

#### **Fase 2: Frontend (JavaScript y Templates)**

- [ ] Crear `apps/tenant/core/templates/tenant/core/partials/{app_name}/list.html`
- [ ] Crear `apps/tenant/core/templates/tenant/core/partials/{app_name}/modals.html`
- [ ] Crear `apps/tenant/core/static/core/js/{app_name}/{app_name}.page.js`
- [ ] Incluir templates en `workspace.html`: `{% include 'tenant/core/partials/{app_name}/list.html' %}`
- [ ] Incluir JS en `workspace.html` o en `assets_{app_name}.html`
- [ ] Agregar ruta en `CoreRoutesView` (opcional, para descubrimiento)

#### **Fase 3: Validación y Testing**

- [ ] Verificar que `GET /api/v1/{app_name}/` retorna lista paginada
- [ ] Verificar que `POST /api/v1/{app_name}/dt/{model_name}/` funciona con DataTables
- [ ] Verificar que `POST /api/v1/{app_name}/` crea instancia (solo ADMIN/STAFF)
- [ ] Verificar que `PATCH /api/v1/{app_name}/{id}/` actualiza instancia (solo ADMIN/STAFF)
- [ ] Verificar que no-staff recibe 405 en mutaciones
- [ ] Verificar que DataTables se inicializa correctamente con lazy loading
- [ ] Verificar que modales funcionan (crear, editar, ver)
- [ ] Verificar que validaciones del frontend coinciden con backend

#### **Fase 4: Documentación**

- [ ] Documentar campos canónicos en `services.py` (LIST_FIELDS, DETAIL_FIELDS)
- [ ] Documentar endpoints en `api/urls.py`
- [ ] Agregar comentarios en JavaScript explicando flujo
- [ ] Actualizar `ARQUITECTURA_GENERAL.md` si es necesario

---

## 4. Notas Finales

### 4.1. Principios Arquitectónicos

1. **Service Layer Pattern:** Toda la lógica de negocio está en `services.py` e `impl/`, no en viewsets
2. **API-First:** El frontend consume JSON, nunca HTML renderizado
3. **SSoT (Single Source of Truth):** Cada app expone servicios públicos para consumo interno
4. **ENFORCED MODE:** Mutaciones solo para ADMIN/STAFF, UI debe usar Core Orchestrator cuando aplique
5. **Lazy Loading:** DataTables se inicializa solo cuando el tab está visible

### 4.2. Diferencias con App "Empresa"

La app "Empresa" tiene características especiales:

1. **Singleton Pattern:** Solo una instancia por tenant (no aplica a todas las apps)
2. **Core Orchestrator:** `PATCH /api/v1/core/empresa/` es la única vía de mutación desde UI
3. **Sin FK a Empresa:** Empresa no tiene FK a sí misma

Para apps normales (collection):
- Usar endpoints directos: `POST /api/v1/{app_name}/`, `PATCH /api/v1/{app_name}/{id}/`
- No requiere Core Orchestrator (a menos que sea necesario para composición)
- FK a Empresa es requerida para ENFORCED MODE v2.40

### 4.3. Recursos Adicionales

- **Arquitectura General:** `docs/ARQUITECTURA_GENERAL.md`
- **Service Layer Pattern:** Ver `apps/tenant/empresa/services.py`
- **DataTables Server-Side:** Ver `apps/tenant/empresa/api/viewsets.py` → método `datatables()`
- **Core Orchestrator:** Ver `apps/tenant/core/api/views.py` → `MiEmpresaView`

---

**Fin del Documento**
