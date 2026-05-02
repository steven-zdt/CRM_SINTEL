# Auditoría de la App "Facturas" - Alineación con Arquitectura v2.40

**Fecha:** 2024  
**Versión Base:** Arquitectura Empresa v2.40  
**Objetivo:** Validar y corregir el flujo estructural y funcional de `apps/tenant/facturas` para alinearlo con el boilerplate y la app "Empresa".

---

## 1. Análisis Estructural Comparativo

### 1.1. Estructura de Carpetas

#### ✅ **Cumplimiento Parcial:**

```
apps/tenant/facturas/
├── ✅ models.py                    # Existe
├── ✅ services.py                  # Existe (con LIST_FIELDS, DETAIL_FIELDS)
├── ❌ impl/                        # NO EXISTE (debería tener facturas_service.py)
├── ✅ api/
│   ├── ✅ serializers.py           # Existe
│   ├── ✅ viewsets.py              # Existe
│   ├── ✅ urls.py                  # Existe
│   ├── ⚠️ datatables.py            # Existe (separado, debería estar en viewsets.py)
│   └── ✅ permissions.py            # Existe
└── ✅ migrations/                  # Existe

apps/tenant/core/templates/tenant/core/partials/facturas/
├── ✅ list.html                    # Existe
└── ✅ modals.html                  # Existe

apps/tenant/core/static/core/js/facturas/
├── ✅ facturas.page.js             # Existe
├── ✅ facturas.api.js              # Existe
├── ✅ facturas.modals.js           # Existe
└── ✅ facturas.table.js            # Existe (legacy, puede deprecarse)
```

#### ⚠️ **Desviaciones Identificadas:**

1. **Falta `impl/` directory:** La lógica de negocio está mezclada en `services.py` en lugar de estar en `impl/facturas_service.py`
2. **`datatables.py` separado:** El endpoint DataTables está en un archivo separado en lugar de ser un `@action` en `viewsets.py`
3. **No hay FK a Empresa:** El modelo `Factura` NO tiene ForeignKey a `Empresa` (requerido para ENFORCED MODE v2.40)

---

## 2. Análisis de Flujo Funcional

### 2.1. Flujo Actual de Facturas (vs. Boilerplate)

#### **Flujo Actual:**

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (JavaScript)                                            │
│ apps/tenant/core/static/core/js/facturas/facturas.page.js        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1. Usuario importa XML
                              │    → Upload vía modal
                              │
                              │ 2. POST /api/v1/facturas/upload-ubl/
                              │    → Multipart/form-data
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ API LAYER                                                        │
│ apps/tenant/facturas/api/viewsets.py → FacturaViewSet           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 3. upload_ubl() action
                              │    → Delega a importar_documento()
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SERVICE LAYER                                                    │
│ apps/tenant/facturas/services.py                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 4. importar_documento()
                              │    → Pipeline universal o legacy
                              │
                              │ 5. guardar_factura_desde_dto()
                              │    → Idempotencia por CUFE
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                       │
│ apps/tenant/facturas/models.py → Factura.save()                 │
└─────────────────────────────────────────────────────────────────┘
```

#### ⚠️ **Diferencias con Boilerplate:**

1. **No hay Core Orchestrator:** Facturas no usa Core Orchestrator (correcto, es inmutable)
2. **Service Layer mezclado:** La lógica está en `services.py` directamente, no en `impl/`
3. **DataTables separado:** El endpoint está en `datatables.py` en lugar de `@action` en ViewSet
4. **No hay ENFORCED MODE:** Es `ReadOnlyModelViewSet` (correcto para inmutabilidad, pero falta validación explícita)

---

## 3. Validación de Desacoplamiento

### 3.1. ✅ **Desacoplamiento Correcto:**

1. **API Layer → Service Layer:**
   - `FacturaViewSet` delega correctamente a `services.importar_documento()`
   - `services.guardar_factura_desde_dto()` contiene la lógica de negocio
   - No hay lógica de negocio en `viewsets.py`

2. **Service Layer → Model Layer:**
   - `services.py` contiene lógica de negocio pura
   - El modelo solo tiene validaciones básicas y persistencia

### 3.2. ⚠️ **Puntos de Mejora:**

1. **Falta separación `impl/`:**
   - La lógica detallada debería estar en `impl/facturas_service.py`
   - `services.py` debería ser solo el provider público

2. **DataTables endpoint separado:**
   - Debería ser un `@action` en `FacturaViewSet` (como en empresa)
   - El archivo `datatables.py` puede deprecarse

3. **Falta FK a Empresa:**
   - Requerido para ENFORCED MODE v2.40
   - Permite auditoría y trazabilidad

---

## 4. Comparación Detallada con Boilerplate

### 4.1. Models.py

#### ✅ **Cumplimiento:**
- ✅ Tiene `clean()` y `save()` (parcial, solo en `Factura.save()`)
- ✅ Timestamps (`created_at`, `updated_at`)
- ✅ Índices definidos
- ✅ Meta con `ordering` y `db_table`

#### ❌ **Desviaciones:**
- ❌ **NO tiene FK a Empresa** (requerido para ENFORCED MODE v2.40)
- ⚠️ No tiene `clean()` explícito en todos los modelos (solo `save()` en `Factura`)
- ⚠️ `ItemFactura` no tiene FK a Empresa (debería tenerla)

### 4.2. Services.py

#### ✅ **Cumplimiento:**
- ✅ Tiene `LIST_FIELDS` y `DETAIL_FIELDS` (alineado con boilerplate)
- ✅ Tiene `qs_list()` y `qs_detail()` optimizados
- ✅ Usa `only()` para optimización
- ✅ Funciones públicas bien definidas

#### ⚠️ **Desviaciones:**
- ⚠️ **Falta `impl/` directory:** La lógica detallada está en `services.py` en lugar de `impl/facturas_service.py`
- ⚠️ Funciones muy largas (ej: `guardar_factura_desde_dto()` tiene ~150 líneas)
- ⚠️ Mezcla de lógica de negocio y adaptadores

### 4.3. API/Viewsets.py

#### ✅ **Cumplimiento:**
- ✅ Usa `SessionAuthentication`
- ✅ Usa `IsTenantAdminOrReadOnly` (correcto para inmutabilidad)
- ✅ `ReadOnlyModelViewSet` (correcto para documentos históricos)
- ✅ Bloquea `create()`, `update()`, `partial_update()` con 405 (correcto)
- ✅ Usa `qs_list()` y `qs_detail()` del service

#### ⚠️ **Desviaciones:**
- ⚠️ **DataTables en archivo separado:** Debería ser `@action` en ViewSet
- ⚠️ No tiene `_check_enforced_mode()` explícito (aunque es ReadOnly, debería documentarse)
- ⚠️ `datatables()` action existe pero también hay `datatables.py` separado (duplicación)

### 4.4. API/Serializers.py

#### ✅ **Cumplimiento:**
- ✅ Tiene `FacturaListSerializer` (alineado con `LIST_FIELDS`)
- ✅ Tiene `FacturaDetailSerializer` (alineado con `DETAIL_FIELDS`)
- ✅ Serializers optimizados (sin campos pesados en list)

#### ⚠️ **Desviaciones:**
- ⚠️ No tiene `FacturaUpsertSerializer` (correcto, es inmutable, pero debería documentarse)
- ⚠️ `FacturaWriteSerializer` existe pero no se usa (legacy)

### 4.5. JavaScript (facturas.page.js)

#### ✅ **Cumplimiento:**
- ✅ Usa `DataTablesUtils.initServerSide()` (helper centralizado)
- ✅ Usa `Routes.get()` para discovery de URLs
- ✅ Usa `DOMUtils.awaitVisibleAny()` para lazy loading
- ✅ Columnas alineadas con `LIST_FIELDS`

#### ⚠️ **Desviaciones:**
- ⚠️ **No usa `DOMUtils.onVisibleOnce()`:** Usa `awaitVisibleAny()` que puede timeout
- ⚠️ No tiene patrón `Module.init` explícito (como empresa)
- ⚠️ No tiene helpers `collectFacturaPayload()`, `populateFacturaForm()` (no aplica, es inmutable)

### 4.6. Templates (list.html)

#### ✅ **Cumplimiento:**
- ✅ Shell HTML para DataTables (sin datos renderizados)
- ✅ Estructura de Card con Header y Body
- ✅ Feedback div para mensajes

#### ⚠️ **Desviaciones:**
- ⚠️ No sigue exactamente el patrón de empresa (toolbar diferente)
- ⚠️ Falta comentario sobre lazy loading

---

## 5. Correcciones Propuestas

### 5.1. **CRÍTICO: Agregar FK a Empresa**

#### **Problema:**
El modelo `Factura` NO tiene ForeignKey a `Empresa`, lo cual es requerido para ENFORCED MODE v2.40 y permite auditoría/trazabilidad.

#### **Solución:**

```python
# apps/tenant/facturas/models.py

class Factura(models.Model):
    # ... campos existentes ...
    
    # ⚠️ v2.40: FK a Empresa (requerido para ENFORCED MODE)
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name=_('Empresa'),
        help_text=_('Empresa del tenant (SSoT)')
    )
    
    # ... resto de campos ...
    
    class Meta:
        # ... meta existente ...
        indexes = [
            # ... índices existentes ...
            models.Index(fields=["empresa"]),  # ⚠️ NUEVO: Índice para FK
        ]
```

#### **Migración Requerida:**

```python
# apps/tenant/facturas/migrations/0013_add_empresa_fk.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('facturas', '0012_add_nota_credito'),
        ('empresa', '0001_initial'),  # ⚠️ IMPORTANTE: Dependencia a empresa
    ]

    operations = [
        migrations.AddField(
            model_name='factura',
            name='empresa',
            field=models.ForeignKey(
                null=True,  # ⚠️ Temporal: null=True para backfill
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='facturas',
                to='empresa.empresa',
                verbose_name='Empresa'
            ),
        ),
        # ⚠️ FASE 2: Backfill con singleton Empresa
        migrations.RunPython(
            code=backfill_empresa_fk,
            reverse_code=migrations.RunPython.noop
        ),
        # ⚠️ FASE 3: Hacer campo no-nullable
        migrations.AlterField(
            model_name='factura',
            name='empresa',
            field=models.ForeignKey(
                null=False,  # ⚠️ Ahora no-nullable
                on_delete=django.db.models.deletion.PROTECT,
                related_name='facturas',
                to='empresa.empresa',
                verbose_name='Empresa'
            ),
        ),
        # ⚠️ FASE 4: Agregar índice
        migrations.AddIndex(
            model_name='factura',
            index=models.Index(fields=['empresa'], name='facturas_factura_empresa_idx'),
        ),
    ]

def backfill_empresa_fk(apps, schema_editor):
    """Backfill: Asigna singleton Empresa a todas las facturas existentes."""
    Factura = apps.get_model('facturas', 'Factura')
    Empresa = apps.get_model('empresa', 'Empresa')
    
    # Obtener singleton Empresa
    empresa = Empresa.objects.first()
    if not empresa:
        # Si no existe Empresa, crear una dummy (o lanzar error)
        raise ValueError("No existe Empresa en este tenant. Cree una Empresa antes de ejecutar esta migración.")
    
    # Backfill: Asignar empresa a todas las facturas sin empresa
    Factura.objects.filter(empresa__isnull=True).update(empresa=empresa)
```

### 5.2. **IMPORTANTE: Mover DataTables a ViewSet**

#### **Problema:**
El endpoint DataTables está en `api/datatables.py` separado, cuando debería ser un `@action` en `FacturaViewSet` (como en empresa).

#### **Solución:**

```python
# apps/tenant/facturas/api/viewsets.py

class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
    # ... código existente ...
    
    @action(detail=False, methods=['post'], url_path='dt/facturas')
    def datatables(self, request: Request) -> Response:
        """
        Endpoint DataTables server-side (POST obligatorio v2.40).
        
        ⚠️ v2.40: POST obligatorio según arquitectura, acepta JSON y form-urlencoded.
        ⚠️ OPTIMIZACIÓN: Usa qs_list() que ya aplica only() con LIST_FIELDS.
        ✅ Solo carga campos necesarios para la tabla
        ✅ Usa FacturaListSerializer para serializar datos
        ✅ Maneja length=-1 cuando paginación está deshabilitada
        """
        from apps.tenant.facturas.services import qs_list
        
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
                Q(numero__icontains=search_value) |
                Q(cufe__icontains=search_value) |
                Q(receptor_razon_social__icontains=search_value) |
                Q(emisor_razon_social__icontains=search_value)
            )
        
        records_filtered = qs.count()
        
        # Orden (mapea columnas 0..n a campos del LIST_FIELDS)
        col_map = {
            "0": "numero",
            "1": "fecha_emision",
            "2": "naturaleza",
            "3": "emisor_razon_social",
            "4": "receptor_razon_social",
            "5": "total",
            "6": "cufe",
        }
        
        # ⚠️ MANEJO ROBUSTO: order puede venir como lista (JSONParser) o como dict anidado (FormParser)
        if isinstance(params.get("order"), list) and len(params.get("order", [])) > 0:
            order_col = str(params.get("order", [{}])[0].get("column", "1"))
            order_dir = params.get("order", [{}])[0].get("dir", "desc")
        elif "order[0][column]" in params:
            order_col = str(params.get("order[0][column]", "1"))
            order_dir = params.get("order[0][dir]", "desc")
        elif "order.0.column" in params:
            order_col = str(params.get("order.0.column", "1"))
            order_dir = params.get("order.0.dir", "desc")
        else:
            order_col = "1"
            order_dir = "desc"
        
        order_field = col_map.get(str(order_col), "fecha_emision")
        
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
        serializer = FacturaListSerializer(data_list, many=True, context={'request': request})
        
        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
```

#### **Deprecar `datatables.py`:**

```python
# apps/tenant/facturas/api/datatables.py
# ⚠️ DEPRECATED v2.40: Este archivo está deprecado.
# Use FacturaViewSet.datatables() action en su lugar.
# Este archivo será removido en v2.41.

# ... código existente con warning ...
```

### 5.3. **MEJORA: Separar Service Layer en `impl/`**

#### **Problema:**
La lógica de negocio detallada está en `services.py` en lugar de estar en `impl/facturas_service.py`.

#### **Solución:**

```python
# apps/tenant/facturas/impl/__init__.py
# (vacío)

# apps/tenant/facturas/impl/facturas_service.py
"""
Implementación privada de servicios de facturas.

⚠️ PRIVADO: Este módulo NO debe importarse directamente desde otras apps.
Use apps.tenant.facturas.services en su lugar.
"""

from typing import Dict, Any, Tuple
from django.db import transaction
from apps.tenant.facturas.models import Factura, FacturaAnexos
from apps.tenant.empresa.services import get_empresa_emisor_data, EmpresaNotConfiguredError

def _resolver_naturaleza(emisor_nit: str | None, empresa_nit: str | None) -> str:
    """Resuelve naturaleza (VENTA/COMPRA) comparando emisor vs empresa (SSoT)."""
    # ... lógica existente de services.py ...

@transaction.atomic
def guardar_factura_desde_dto(dto: Dict[str, Any], xml_text: str) -> Tuple[Dict[str, Any], int]:
    """
    Persiste factura desde DTO canónico del pipeline XML (SSoT).
    
    ⚠️ PRIVADO: Use services.guardar_factura_desde_dto() en su lugar.
    """
    # ... mover lógica de services.py aquí ...
```

```python
# apps/tenant/facturas/services.py
"""
Service Provider para datos de Facturas (consumo interno entre apps).

⚠️ POLÍTICA SSoT: Este servicio es la ÚNICA fuente de datos de facturas para consumo interno.
"""

from typing import Dict, Any, Tuple
from apps.tenant.facturas.impl.facturas_service import (
    guardar_factura_desde_dto as _guardar_factura_desde_dto,
    guardar_nota_credito_desde_dto as _guardar_nota_credito_desde_dto,
)

# ⚠️ RE-EXPORT: Funciones públicas
def guardar_factura_desde_dto(dto: Dict[str, Any], xml_text: str) -> Tuple[Dict[str, Any], int]:
    """Wrapper público para guardar_factura_desde_dto."""
    return _guardar_factura_desde_dto(dto, xml_text)

def guardar_nota_credito_desde_dto(dto: Dict[str, Any], *, xml_text: str):
    """Wrapper público para guardar_nota_credito_desde_dto."""
    return _guardar_nota_credito_desde_dto(dto, xml_text=xml_text)

# ... mantener LIST_FIELDS, DETAIL_FIELDS, qs_list(), qs_detail() ...
```

### 5.4. **MEJORA: Actualizar JavaScript para Lazy Loading**

#### **Problema:**
`facturas.page.js` usa `DOMUtils.awaitVisibleAny()` que puede timeout, en lugar de `DOMUtils.onVisibleOnce()` (patrón de empresa).

#### **Solución:**

```javascript
// apps/tenant/core/static/core/js/facturas/facturas.page.js

/**
 * Inicialización del módulo
 */
async function init() {
  if (state.initialized) {
    log('Módulo ya inicializado');
    return;
  }

  requireCore();

  // ⚠️ v2.40: Lazy Loading - Solo inicializar cuando el tab está visible
  const TAB_CONTAINER_ID = '#tab-facturas';
  w.DOMUtils.onVisibleOnce(TAB_CONTAINER_ID, async () => {
    log('Tab visible, inicializando módulo...');
    
    await initDataTable();
    bindEvents();
    
    state.initialized = true;
    log('Módulo inicializado exitosamente');
  });
}

// Auto-inicializar si DOM está listo
if (d.readyState === 'loading') {
  d.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
```

### 5.5. **MEJORA: Actualizar URLs para DataTables**

#### **Problema:**
Las URLs tienen `datatables.py` separado y el router no está configurado correctamente.

#### **Solución:**

```python
# apps/tenant/facturas/api/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.tenant.facturas.api.viewsets import (
    FacturaViewSet,
    ItemFacturaViewSet,
    NotaCreditoViewSet,
)
from apps.tenant.facturas.api.views_mail_ingestion import (
    MailIngestionRunCreateAPIView,
    MailIngestionRunsListAPIView,
)

# Router para esta app
router = DefaultRouter()

# ⚠️ IMPORTANTE: Registrar con ruta vacía "" porque el include en config/api_urls.py es path('facturas/', ...)
router.register(r'', FacturaViewSet, basename='factura')
router.register(r'items-factura', ItemFacturaViewSet, basename='item-factura')
router.register(r'notas-credito', NotaCreditoViewSet, basename='nota-credito')

# URLs generadas por el router
urlpatterns = router.urls

# URLs adicionales para ingesta por correo
urlpatterns += [
    path("ingesta-correo/run/", MailIngestionRunCreateAPIView.as_view(), name="facturas_mail_run"),
    path("ingesta-correo/runs/", MailIngestionRunsListAPIView.as_view(), name="facturas_mail_runs"),
    # ⚠️ DEPRECATED: datatables.py endpoint (mantener por compatibilidad temporal)
    # path("dt/facturas/", facturas_dt, name="facturas_dt"),  # ⚠️ DEPRECATED: Usar FacturaViewSet.datatables()
]
```

### 5.6. **MEJORA: Agregar Parser Classes en ViewSet**

#### **Problema:**
`FacturaViewSet` no tiene `parser_classes` explícitos para aceptar JSON y form-urlencoded (como empresa).

#### **Solución:**

```python
# apps/tenant/facturas/api/viewsets.py

from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    FACTURAS MODULE — CONTROL CONTABLE
    
    ⚠️ INMUTABILIDAD: Las facturas son documentos históricos importados.
    - Solo lectura (GET, DELETE para rollback)
    - NO se pueden crear/editar manualmente
    - Correcciones mediante Notas Crédito/Débito
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser]  # ⚠️ NUEVO: Acepta JSON y form-urlencoded
    renderer_classes = [JSONRenderer]  # ⚠️ NUEVO: Solo JSON (no BrowsableAPIRenderer)
    http_method_names = ['get', 'head', 'options', 'post', 'delete']
    
    # ... resto del código ...
```

---

## 6. Checklist de Correcciones

### 6.1. **CRÍTICO (Debe hacerse):**

- [ ] **Agregar FK a Empresa en modelo Factura**
  - [ ] Crear migración con `null=True` inicial
  - [ ] Backfill con singleton Empresa
  - [ ] Cambiar a `null=False`
  - [ ] Agregar índice

- [ ] **Mover DataTables a ViewSet**
  - [ ] Agregar `@action` `datatables()` en `FacturaViewSet`
  - [ ] Deprecar `api/datatables.py`
  - [ ] Actualizar URLs

- [ ] **Agregar Parser Classes**
  - [ ] `parser_classes = [JSONParser, FormParser]`
  - [ ] `renderer_classes = [JSONRenderer]`

### 6.2. **IMPORTANTE (Recomendado):**

- [ ] **Separar Service Layer en `impl/`**
  - [ ] Crear `impl/facturas_service.py`
  - [ ] Mover lógica detallada a `impl/`
  - [ ] `services.py` como wrapper público

- [ ] **Actualizar JavaScript para Lazy Loading**
  - [ ] Usar `DOMUtils.onVisibleOnce()` en lugar de `awaitVisibleAny()`
  - [ ] Patrón `Module.init` explícito

- [ ] **Actualizar Templates**
  - [ ] Agregar comentarios sobre lazy loading
  - [ ] Alinear estructura con empresa (opcional)

### 6.3. **OPCIONAL (Mejoras):**

- [ ] **Agregar `clean()` explícito en modelos**
  - [ ] `Factura.clean()` para normalización
  - [ ] `ItemFactura.clean()` si aplica

- [ ] **Documentar Inmutabilidad**
  - [ ] Agregar docstrings explicando por qué es ReadOnly
  - [ ] Documentar flujo de correcciones (Notas Crédito)

---

## 7. Resumen de Desviaciones

| Aspecto | Estado | Acción Requerida |
|---------|---------|------------------|
| **FK a Empresa** | ❌ Falta | **CRÍTICO:** Agregar migración |
| **DataTables en ViewSet** | ⚠️ Separado | **CRÍTICO:** Mover a `@action` |
| **Parser Classes** | ⚠️ Implícito | **CRÍTICO:** Agregar explícitamente |
| **Service Layer `impl/`** | ❌ Falta | **IMPORTANTE:** Crear estructura |
| **Lazy Loading JS** | ⚠️ Parcial | **IMPORTANTE:** Usar `onVisibleOnce()` |
| **Templates** | ✅ Correcto | **OPCIONAL:** Mejoras menores |

---

## 8. Notas Finales

### 8.1. **Inmutabilidad vs. ENFORCED MODE**

La app "Facturas" es **inmutable por diseño** (documentos históricos), lo cual es correcto. Sin embargo:

- ✅ **Correcto:** `ReadOnlyModelViewSet` bloquea `create()`, `update()`, `partial_update()`
- ✅ **Correcto:** Solo permite `GET` y `DELETE` (rollback técnico)
- ⚠️ **Mejorable:** Agregar FK a Empresa para auditoría (no afecta inmutabilidad)
- ⚠️ **Mejorable:** Documentar explícitamente la política de inmutabilidad

### 8.2. **Diferencias Aceptables con Boilerplate**

1. **No hay Core Orchestrator:** Correcto, facturas no se crean desde UI
2. **No hay `UpsertSerializer`:** Correcto, es inmutable
3. **No hay modales de creación/edición:** Correcto, solo importación XML

### 8.3. **Próximos Pasos**

1. **Fase 1 (CRÍTICO):** Agregar FK a Empresa y migración
2. **Fase 2 (CRÍTICO):** Mover DataTables a ViewSet
3. **Fase 3 (IMPORTANTE):** Separar Service Layer en `impl/`
4. **Fase 4 (IMPORTANTE):** Actualizar JavaScript
5. **Fase 5 (OPCIONAL):** Mejoras menores

---

**Fin del Documento**
