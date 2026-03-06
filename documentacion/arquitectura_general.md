# 🏗️ Arquitectura General del Proyecto SINTEL

**Versión:** 2.60  
**Última Actualización:** 2026-02-10 (Fase 5 Completada - Pruebas y CI: Smoke UX tests, auditoría automatizada, GitHub Actions + Fase 4 En Progreso - Migración por App a DataTables server-side + Migración Completa Pipeline Universal de Documentos - Sistema unificado para ingestión de XML, PDF, XLS/XLSX, CSV, TXT + Alineación Técnica Fase 0 - Normalización de assets, sanity checks, ajuste automático de columnas + Refactorización Cotizaciones v2.60 - Limpieza profunda, eliminación de monolitos, Feature-Sliced + Error Boundary Pattern v2.60 - Implementación de UIManager para aislamiento de lógica de negocio y presentación de errores, estandarización de respuestas JSON en handlers de error, integración con Tabulator Factory + Refactorización Módulo de Cotizaciones v2.60 - Eliminación completa del campo `cliente_nombre_manual`, simplificación del flujo de creación, cliente obligatorio desde base de datos + Sistema de Documento Soporte Inmutable para Gastos v2.40 - Refactorización completa a arquitectura de evidencia legal según normativa DIAN colombiana + Sistema de Choices para Centro de Costo y Categoría Contable + Resolución DIAN Automática + Guía de Solución de Problemas Comunes v2.40 - Documentación completa de problemas resueltos en URLs, importaciones y arquitectura multi-tenant + **Módulo Inventario v2.40 - Arquitectura Standalone Completa: Todos los módulos (Categorías, Productos, Servicios, Activos) son completamente independientes con Tabulator Factory v2.40, eliminación automática de datos relacionados (CASCADE), categorías opcionales (null=True), y reglas de seguridad de eliminación (Inactivar antes de Borrar)** + **Tabulator Factory v2.40 - Arquitectura Global de Tabulator para estandarización de tablas interactivas, implementación completa en módulos Clientes, Proveedores, Gastos, Empleados, Facturas, Inventario, Empresa y MailInboxConfig con CRUD completo, soft delete, manejo de errores y limpieza Zero-Legacy** + **Document Ingest Pipeline v2.40 - Arquitectura App-Specific: Routing y validación por app, parsers independientes por app, protección contra fallback genérico, auto-registro de parsers, SemanticMapper para mapeo inteligente de columnas**)  
**Estado:** ✅ Sistema completamente funcional - **Fase 5 Completada (Pruebas y CI)** - Smoke UX tests desde workspace, auditoría automatizada con scripts Node.js, GitHub Actions configurado, suites completas para módulos CRUD + **Fase 4 En Progreso (Migración por App)** - Migración de módulos a DataTables server-side con `rowId:'id'` y `refreshSafe()`, Proveedores y Gastos completados + **Migración Completa Pipeline Universal de Documentos** - Sistema unificado para ingestión de XML, PDF, XLS/XLSX, CSV, TXT, migración completa desde xml_ingest/xml_parser + **Alineación Técnica Fase 0** - Normalización de assets_core.html, sanity checks de helpers, ajuste automático de columnas en tabs + **Refactorización Cotizaciones v2.60** - Limpieza profunda eliminando monolitos, migración a Feature-Sliced, helpers dedicados + URLs separadas público/privado implementadas + Sistema de suspensión implementado + Acceso a tenants configurado + Normalización de dominios implementada + CSRF mejorado para dominios arbitrarios + Acceso en puerto 80 habilitado + Testing robusto con TenantTestCase (Fase 5) + Documentación Django 5.0 y django-tenants normalizada + Blindaje del Login (Fase 1) + Perfil Privado del Colaborador (Fase 2) + Aislamiento completo del Admin de Tenant + Eliminación de referencias a /admin/login/ en tenants privados + Solución automática de puerto en dominios + Auditoría de dominios y acceso web + Scripts de reinicio total (Nuclear Reset) + Aprovisionamiento Atómico "Zero-Orphan" + Normalización de dominios con soporte de puerto en desarrollo + Server Guard mejorado (omite validaciones durante comandos de mantenimiento) + Script reset_migrations.py mejorado (asegura __init__.py) + Conflicto de labels resuelto (apps.public.core y apps.tenant.core) + Entrypoint.sh mejorado (mejor manejo de conexión BD) + Estandarización Puerto 80 (HTTP estándar) + Refactorización API-First completa del módulo landing + **Alineación completa de apps/tenant con django-tenants verificada (98% conforme)** + **Corrección username='' en onboarding** + **Configuración producción HTTPS (sintel.com)** + **Sistema de Invitación/Activación de Owners (v2.24)** + **Autogeneración de Dominios FQDN (v2.25)** + **Enrutamiento por Hostname Estable (v2.26)** + **Garantía de Dominios Públicos Permanentes (v2.26)** + **Solución Error 404 en /activate/ (v2.28)** + **Solución Error Redirect después de Activación (v2.27)** + **Middleware TenantURLConfMiddleware (v2.28)** + **Onboarding sin Contraseñas - Activación Exclusiva (v2.29)** + **Migración API-First Completa de Landing (v2.30)** + **Reenvío de Token de Activación desde Consola (v2.30)** + **Core API como Orquestador Único de UI Privada (v2.30)** + **Auth Centralizado en Core (v2.30)** + **Workspace Consumiendo Core API (v2.30)** + **Suite Completa de Smoke Tests E2E (v2.30)** + **Facturas Migrado a API-First con Service Layer (v2.30)** + **Workspace UI para CRUD de Facturas (v2.30)** + **Facturas - Inmutabilidad Estricta y Mejoras (v2.30)** + **Perfil API-First Completo con Serializer de Actualización Parcial (v2.31)** + **CSRF Relajado Solo en Desarrollo (v2.31)** + **Workspace Perfil con Archivo JS Estático (v2.31)** + **SessionAuthentication en Workspace (v2.32)** + **Manejo Inteligente de 401 en Módulos No Críticos (v2.32)** + **Fase 5: Observabilidad + Smoke Test CLI (v2.33)** + **Fase 6: Pruebas Críticas Multitenant (v2.33)** + **Canonización Pipeline XML + SSoT Operativo (v2.34)** + **Notas Crédito UBL 2.1 - Pipeline Completo (v2.35)** + **Document Ingest Pipeline Universal - Arquitectura Aprobada (v2.36)** + **Auditoría Masiva DataTables v2.40 - Alineación completa de tenant apps (v2.40)** + **Corrección importación Empresa en facturas/services.py (v2.40)** + **Implementación columna Naturaleza (VENTA/COMPRA) en DataTable de Facturas (v2.40)**  
**Fuente Única de Verdad:** Este documento es la referencia oficial de la arquitectura del proyecto.  
**Ubicación:** `documentacion/arquitectura_general.md` (ÚNICA FUENTE DE VERDAD)  
**Documento Base Original:** `aquitectura_crm_sintel_v_1_operativo.docx` (Arquitectura inicial v1.0)

> **⚠️ IMPORTANTE:** 
> - **TODOS los archivos de documentación (.md) están consolidados en `documentacion/`**
> - **Este es el ÚNICO directorio de documentación del proyecto**
> - **Cualquier otro archivo .md fuera de esta carpeta debe moverse aquí**
> - Este documento Markdown tiene prioridad como fuente única de verdad para el desarrollo

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura Multi-Tenant](#arquitectura-multi-tenant)
4. [Arquitectura API-First (DRF)](#arquitectura-api-first-drf)
5. [Estándar de Listados y APIs (DataTables + Logging)](#estándar-de-listados-y-apis-datatables--logging)
6. [Autenticación JWT](#autenticación-jwt)
7. [Infraestructura Docker](#infraestructura-docker)
7. [Estructura de Directorios](#estructura-de-directorios)
8. [Aplicaciones y Módulos](#aplicaciones-y-módulos)
9. [Configuración Django](#configuración-django)
10. [Base de Datos](#base-de-datos)
11. [Flujos de Trabajo](#flujos-de-trabajo)
12. [Comandos Esenciales](#comandos-esenciales)

---

## 🎯 Visión General

SINTEL es un sistema SaaS multi-tenant para gestión contable y facturación electrónica en Colombia, diseñado con arquitectura por esquemas usando `django-tenants`. El sistema permite que múltiples empresas (tenants) compartan la misma infraestructura mientras mantienen sus datos completamente aislados.

### Enfoque API-First

El proyecto está **basado en Django REST Framework (DRF) con enfoque API-first**, lo que significa:

- **APIs REST como capa principal**: Todas las funcionalidades están expuestas a través de APIs REST
- **Frontend agnóstico**: El backend puede ser consumido por cualquier frontend (React, Vue, Angular, móvil, etc.)
- **Documentación automática**: APIs documentadas automáticamente con herramientas como Swagger/OpenAPI
- **Versionado de APIs**: Capacidad de versionar APIs para mantener compatibilidad
- **Integración fácil**: Facilita la integración con sistemas externos y terceros

### Objetivo del Sistema

El sistema está diseñado para:
- Gestionar múltiples empresas (tenants) de forma aislada
- Procesar facturas electrónicas XML según normativa DIAN
- Mantener contabilidad separada por empresa
- Proporcionar APIs REST para integración (enfoque API-first)
- Procesar correos electrónicos con facturas adjuntas
- Ejecutar tareas asíncronas con Celery

### Principios Arquitectónicos

Estos principios reducen significativamente la deuda técnica:

1. **Service Layer Pattern**: 
   - Lógica de negocio separada de modelos y vistas
   - Facilita pruebas unitarias y mantenimiento
   - Lógica específica en `apps/services/` (paquetes Python puros)
   - **⚠️ v2.37+: Patrón `LIST_FIELDS` / `DETAIL_FIELDS` / `qs_list()` / `qs_detail()`**
     - **LIST_FIELDS**: Tupla de campos mínimos para listados (optimización con `only()`)
     - **DETAIL_FIELDS**: Tupla de campos ampliados para detalle
     - **qs_list()**: Función que retorna QuerySet optimizado para listados (`only(*LIST_FIELDS)`)
     - **qs_detail()**: Función que retorna QuerySet optimizado para detalle (`only(*DETAIL_FIELDS)`)
     - **Alineación**: Serializers usan los mismos campos que `LIST_FIELDS` / `DETAIL_FIELDS`
     - **Ubicación**: `apps/tenant/{app}/services.py`
     - **Ejemplo**:
       ```python
       # apps/tenant/clientes/services.py
       LIST_FIELDS = ("id", "razon_social", "numero_documento", "activo")
       DETAIL_FIELDS = (*LIST_FIELDS, "email", "telefono", "direccion")
       
       def qs_list():
           return Cliente.objects.only(*LIST_FIELDS)
       
       def qs_detail():
           return Cliente.objects.only(*DETAIL_FIELDS)
       ```

2. **Cero Signals**: 
   - Evitar el acoplamiento invisible de Django signals
   - Previene efectos secundarios difíciles de depurar en entornos multi-tenant
   - Toda la lógica es explícita y rastreable

3. **Client-Side First / API-First**: 
   - **DataTables client-side por defecto**: Todas las tablas DataTables deben usar procesamiento client-side a menos que se solicite explícitamente server-side
   - Server-side solo cuando se requiera: Para consultas pesadas o cuando se solicite explícitamente
   - APIs REST con paginación y filtrado eficiente
   - Enfoque API-first: todas las funcionalidades expuestas como APIs REST
   - Frontend agnóstico: cualquier cliente puede consumir las APIs

4. **Settings Simple**: 
   - Configuración central (`settings.py`) simple y declarativa
   - Sin lógica de negocio en settings
   - Extensiones y configuraciones específicas en módulos `apps/services/`

5. **Multi-Tenant por Esquemas**:
   - Aislamiento completo de datos por tenant
   - Esquema `public` compartido para catálogos y usuarios globales
   - Esquemas `tenant_*` para datos específicos de cada empresa

6. **Single Source of Truth (SSoT)**:
   - Cada dominio de datos tiene una única fuente de verdad
   - Datos empresariales: `apps/tenant/empresa/api` es la única fuente
   - Otras apps consumen datos empresariales vía API o servicio provider
   - Evita duplicación de datos y lógica entre apps
   - Facilita mantenimiento y garantiza consistencia
   - **⚠️ v2.40: ForeignKey a Empresa (Obligatorio)**
     - **REQUERIDO**: Todos los modelos de TENANT_APPS deben tener `empresa = ForeignKey(Empresa, on_delete=PROTECT)`
     - **Índice**: `models.Index(fields=["empresa"])` en `Meta.indexes` (obligatorio)
     - **Propósito**: Garantizar integridad referencial y facilitar consultas por tenant
     - **Asignación automática**: Los servicios deben asignar `empresa_id` automáticamente al crear registros
     - **Ejemplo**:
       ```python
       class Cliente(models.Model):
           empresa = models.ForeignKey(
               'empresa.Empresa',
               on_delete=models.PROTECT,
               related_name='clientes',
               verbose_name=_('Empresa'),
               help_text=_('Empresa propietaria (SSoT por tenant).')
           )
           
           class Meta:
               indexes = [
                   models.Index(fields=["empresa"]),  # ⚠️ v2.40: Obligatorio
               ]
       ```

7. **UI Standard para Tenant Apps (v2.30+)**:
   - **TODAS las páginas de UI en `TENANT_APPS` DEBEN** seguir el estándar:
     - Extender `tenant/base.html` (navbar/footer automático)
     - Usar `TemplateView` con `LoginRequiredMixin` (sin lógica de negocio)
     - Obtener datos exclusivamente vía JavaScript desde APIs REST
     - Registrar ruta en `config/urls_tenant.py` con nombre descriptivo
     - Incluir tests de humo que verifiquen renderizado y consumo de APIs
   - **Prohibido**: Renderizar datos server-side, lógica de negocio en vistas de UI, shells estáticos para páginas principales
   - **Referencia**: Ver `documentacion/REGLAS_UI_TENANT_APPS.md` para detalles completos
   - **Auditoría**: Ejecutar `python scripts/audit_tenant_ui_compliance.py` para verificar cumplimiento

8. **⚠️ Zero Trust - Capa de Normalización (v2.40)**:
   - **Principio Fundamental**: "Nunca confíes en la entrada del usuario"
   - **Aplicación Obligatoria**: Todos los serializadores DRF DEBEN aplicar normalización antes de guardar datos
   - **Mixin Reutilizable**: Usar `NormalizationMixin` en todos los serializadores que procesen datos del usuario
   - **Componentes de Normalización**:
     - **Limpieza de Strings**: `.strip()`, eliminación de espacios dobles, sanitización HTML/scripts
     - **Estandarización de Formatos**: Conversión a MAYÚSCULAS para campos técnicos (marca, referencia, unidad)
     - **Validación Numérica Estricta**: Casteo a Decimal con validación de rangos y valores no negativos
     - **Validación de Relaciones**: Verificación de existencia de ForeignKeys antes de asignar
     - **Recálculo de Totales**: Los totales económicos DEBEN recalcularse en el backend (NO confiar en valores del frontend)
   - **Implementación**:
     ```python
     from apps.tenant.cotizaciones.api.serializers import NormalizationMixin
     
     class MiSerializer(NormalizationMixin, serializers.ModelSerializer):
         def validate(self, attrs):
             attrs = self.normalize_data(attrs)  # Aplicar normalización
             # Validaciones adicionales...
             return attrs
     ```
   - **Ubicación**: `apps/tenant/{app}/api/serializers.py`
   - **Referencia**: Ver implementación en `apps/tenant/cotizaciones/api/serializers.py`
   - **Seguridad**: Protege contra inyección de scripts, valores inválidos y manipulación de datos

---

## 📊 Estándar de Listados y APIs (Tabulator Factory + DataTables + Logging)

### Regla de Arquitectura (Obligatoria)

**⚠️ PATRÓN PREDEFINIDO: DataTables Client-Side**

- **Por defecto**: Todas las tablas DataTables deben usar procesamiento **client-side**
- **Server-side solo cuando se solicite**: Usar server-side únicamente cuando se requiera explícitamente (consultas pesadas, grandes volúmenes de datos, etc.)

**Todas las tablas DataTables y endpoints asociados deben:**

1. **Client-side (predeterminado)**: Cargar datos completos desde API REST y procesar en el cliente
   - Usar endpoints de listado estándar (GET) con paginación opcional
   - DataTables procesa ordenamiento, búsqueda y paginación en el navegador
   - **Server-side (solo si se solicita)**: Usar POST para server-side (evitar querystrings visibles) y enviar solo las columnas visibles/útiles.
   - Referencia: [DataTables POST](https://webdevservices.in/secure-datatables-implementation/)

2. **Exponer campos mínimos en serializadores DRF** y limitar queryset con `only()`/`defer()` + `select_related()`/`prefetch_related()` según relaciones.
   - Referencia: [DRF Optimization](https://pypi.org/project/django-rest-framework/)

3. **Paginar con DRF** (LimitOffset por start/length o Cursor para listas grandes/feeds), configurable por vista.
   - Referencia: [DRF Pagination](https://docs.benchhub.co/drf-pagination/)

4. **Whitelistear orden y búsquedas** (solo sobre columnas visibles/permitidas) y responder con el contrato DataTables (draw/recordsTotal/recordsFiltered/data).
   - Referencia: [DataTables Security](https://webdevservices.in/secure-datatables-implementation/)

5. **Logging limpio**: en dev, bajar ruido de `django.server`; en prod (Gunicorn) registrar ruta sin query (usar `%(U)s`, sin `%(q)s`).
   - Referencia: [Django Logging](https://pypy-django.github.io/logging/), [Gunicorn Format](https://github.com/benoitc/gunicorn/blob/master/docs/settings.rst#accesslog)

6. **⚠️ v2.40: DataTables como @action en ViewSets** (Solo para server-side cuando se solicite)
   - **NOTA**: Este patrón solo se usa cuando se requiere explícitamente server-side
   - **Para client-side**: Usar el endpoint de listado estándar del ViewSet (GET)
   - **DEPRECADO**: Archivos `datatables.py` separados (serán eliminados en v2.41)
   - **REQUERIDO (solo para server-side)**: Implementar DataTables como `@action` dentro del ViewSet principal
   - **Patrón**: `@action(detail=False, methods=["post"], url_path="dt/{model_name}")`
   - **Parser/Renderer**: `parser_classes = [JSONParser, FormParser, MultiPartParser]`, `renderer_classes = [JSONRenderer]`
   - **Manejo robusto**: `request.data` puede ser `QueryDict` (FormParser) o `dict` (JSONParser)

> **⚠️ IMPORTANTE:** Esta regla aplica **solo cuando se requiera server-side explícitamente**. Para client-side, usar endpoints GET estándar.

### Helper Reutilizable DataTables (Solo para server-side)

**Ubicación:** `apps/shared/datatable.py`

> **Nota**: Este helper solo debe usarse cuando se requiera explícitamente server-side. Para client-side, usar endpoints GET estándar.

**Clases:**
- `DataTableSpec`: Especificación declarativa para endpoints DataTables server-side
  - `fields_map`: Mapeo índice → campo ORM (whitelist)
  - `search_fields`: Campos permitidos para búsqueda global
  - `base_qs`: QuerySet base (con `only()`/`select_related()` aplicados)
  - `serializer`: Serializador DRF para serializar datos
  - `extra_filter`: Callable opcional para filtros adicionales

- `DataTableServer`: Helper server-side para procesar requests
  - Lee parámetros desde `request.data` (POST)
  - Aplica whitelist de orden/búsqueda
  - Pagina con `[start:start+length]`
  - Responde con contrato DataTables estándar

**Ejemplo de uso (solo cuando se requiera server-side):**
```python
from apps.shared.datatable import DataTableSpec, DataTableServer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser

@api_view(["POST"])
@permission_classes([IsAdminUser])
def tenants_dt(request):
    # Solo usar cuando se requiera explícitamente server-side
    spec = DataTableSpec(
        fields_map={0: "id", 1: "nombre", 2: "domain", 3: "created_at"},
        search_fields=["nombre", "domain"],
        base_qs=Tenant.objects.only("id", "nombre", "domain", "created_at"),
        serializer=TenantListSerializer,
    )
    return DataTableServer(spec).handle(request)
```

### Cliente DataTables (JavaScript)

**⚠️ PATRÓN PREDEFINIDO: Client-Side**

**Obligatorio:**
- **Client-side por defecto**: No especificar `serverSide: true` a menos que se requiera explícitamente
- Usar endpoints GET estándar para cargar datos
- Declarar solo columnas visibles en `columns`
- No habilitar `column-search` si no se usa

**⚠️ v2.40: Lazy Loading con `onVisibleOnce` (Obligatorio):**
- **REQUERIDO**: Usar `DOMUtils.onVisibleOnce(CONTAINER_ID, init)` en lugar de `DOMContentLoaded`
- **Beneficio**: DataTables se inicializan solo cuando el contenedor/tab es visible
- **Patrón**: Identificar el contenedor padre (tab/panel) y usar su ID como selector

**⚠️ v2.40: Carga Inmediata al Hacer Clic en Tabs (Patrón Inventario):**
- **Patrón implementado**: Listeners directos a los botones de tabs para cargar tablas inmediatamente
- **Evento**: `shown.bs.tab` de Bootstrap para detectar cuando un tab se activa
- **Beneficio**: Mejor UX - las tablas se cargan al hacer clic, no esperan a lazy loading
- **Fallback**: Mantener `DOMUtils.onVisibleOnce` como respaldo
- **Ejemplo**:
  ```javascript
  // Listener directo al tab para carga inmediata
  const serviciosTab = document.getElementById('inventario-servicios-tab');
  if (serviciosTab) {
      serviciosTab.addEventListener('shown.bs.tab', async function() {
          if (!state.servicios.initialized || !state.servicios.table) {
              await initServiciosTable();
          }
      });
  }
  
  // Fallback: Lazy loading como respaldo
  DOMUtils.onVisibleOnce('#subtab-servicios', async () => {
      if (!state.servicios.initialized || !state.servicios.table) {
          await initServiciosTable();
      }
  });
  ```

**Ejemplo client-side (patrón predefinido) con lazy loading:**
```javascript
// ❌ DEPRECADO: DOMContentLoaded
document.addEventListener('DOMContentLoaded', init);

// ✅ CORRECTO: onVisibleOnce
const CONTAINER_ID = '#workspace-clientes'; // ID del contenedor/tab
window.DOMUtils.onVisibleOnce(CONTAINER_ID, init);

function init() {
  // Inicializar DataTable (client-side por defecto)
  new DataTable('#table-clientes', {
    ajax: {
      url: '/api/v1/clientes/',  // Endpoint GET estándar
      type: 'GET'
    },
    columns: [
      { data: 'id' },
      { data: 'razon_social' },
      { data: 'numero_documento' }
    ]
    // serverSide: false (por defecto, no es necesario especificarlo)
  });
}
```

**Ejemplo server-side (solo cuando se solicite explícitamente):**
```javascript
// ✅ Server-side solo cuando se requiera explícitamente
new DataTable('#table-clientes', {
  processing: true,
  serverSide: true,  // Solo cuando se solicite explícitamente
  ajax: {
    url: '/api/v1/clientes/dt/clientes/',
    type: 'POST',  // Obligatorio para server-side
    headers: { 'X-CSRFToken': getCookie('csrftoken') }
  },
  columns: [
    { data: 'id' },
    { data: 'razon_social' },
    { data: 'numero_documento' }
  ]
});
```

### API DRF (Backend)

**Obligatorio:**
- Serializadores con `fields` mínimos (solo lo necesario)
- QuerySets con `only()` para evitar lecturas innecesarias
- `select_related()` para FK/OneToOne
- `prefetch_related()` para M2M/reversos
- Paginación con LimitOffset o Cursor según caso
- **⚠️ Zero Trust (v2.40)**: Normalización obligatoria en todos los serializadores que procesen datos del usuario

**⚠️ Zero Trust - Normalización Obligatoria en Serializadores (v2.40):**

**Principio Fundamental**: "Nunca confíes en la entrada del usuario"

Todos los serializadores que procesen datos del usuario DEBEN aplicar `NormalizationMixin`:

```python
from apps.tenant.cotizaciones.api.serializers import NormalizationMixin

class MiSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ Zero Trust: Aplica normalización y validación estricta.
    """
    
    def validate(self, attrs):
        """
        ⚠️ Zero Trust: Normalización y validación estricta.
        """
        # 1. Aplicar normalización automática
        attrs = self.normalize_data(attrs)
        
        # 2. Validar ForeignKeys
        if 'cliente' in attrs:
            attrs['cliente'] = self.validate_foreign_key(
                attrs['cliente'], Cliente, 'cliente'
            )
        
        # 3. Validar campos numéricos
        if 'precio' in attrs:
            attrs['precio'] = self.normalize_decimal(
                attrs['precio'], 'precio', max_digits=14, decimal_places=2
            )
            if attrs['precio'] < 0:
                raise serializers.ValidationError({
                    'precio': _('El precio no puede ser negativo.')
                })
        
        return attrs
```

**Componentes de Normalización:**
1. **Limpieza de Strings**: `.strip()`, eliminación de espacios dobles, sanitización HTML/scripts
2. **Estandarización de Formatos**: Conversión a MAYÚSCULAS para campos técnicos (marca, referencia, unidad)
3. **Validación Numérica Estricta**: Casteo a Decimal con validación de rangos y valores no negativos
4. **Validación de Relaciones**: Verificación de existencia de ForeignKeys antes de asignar
5. **Recálculo de Totales**: Los totales económicos DEBEN recalcularse en el backend (NO confiar en valores del frontend)

**Ubicación del Mixin**: `apps/tenant/cotizaciones/api/serializers.py` (reutilizable en todas las apps)

**Referencia de Implementación**: Ver `apps/tenant/cotizaciones/api/serializers.py` para ejemplo completo

**⚠️ v2.40: Patrón @action para DataTables Server-Side (Solo cuando se solicite):**

> **Nota**: Este patrón solo debe usarse cuando se requiera explícitamente server-side. Para client-side, usar el endpoint de listado estándar del ViewSet.

```python
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer

class ClienteViewSet(viewsets.ModelViewSet):
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    
    @action(detail=False, methods=["post"], url_path="dt/clientes")
    def datatables(self, request):
        """
        Endpoint DataTables server-side POST (solo cuando se solicite explícitamente).
        Maneja tanto QueryDict (FormParser) como dict (JSONParser).
        """
        # Obtener parámetros DataTables desde request.data
        draw = int(request.data.get("draw", 1))
        start = int(request.data.get("start", 0))
        length = int(request.data.get("length", 10))
        search_value = request.data.get("search[value]", "").strip()
        
        # QuerySet base optimizado
        qs = Cliente.objects.only(*LIST_FIELDS)
        
        # Aplicar filtros, búsqueda, ordenamiento
        # ...
        
        # Paginación
        if length == -1:
            data = list(qs)
            records_total = qs.count()
        else:
            data = list(qs[start:start+length])
            records_total = qs.count()
        
        # Serializar
        serializer = ClienteListSerializer(data, many=True)
        
        # Retornar contrato DataTables
        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_total,
            "data": serializer.data
        })
```

**Ejemplo básico (legacy - deprecado):**
```python
# Serializador mínimo
class TenantListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ("id", "name", "domain", "created_at")

# QuerySet optimizado
queryset = Tenant.objects.only("id", "name", "domain", "created_at").select_related("owner")
```

### Tabulator Factory (Arquitectura Global v2.40)

**⚠️ NUEVO PATRÓN: Tabulator Factory para Estandarización**

A partir de v2.40, se implementó una **Factory Global de Tabulator** para estandarizar la creación de tablas interactivas y eliminar código repetido. Esta arquitectura reemplaza implementaciones aisladas de DataTables y proporciona una base reutilizable para todos los módulos.

#### Arquitectura Tabulator Factory

**Ubicación:** `apps/tenant/core/static/core/js/common/tabulator.factory.js`

**Objetivo:**
- Centralizar configuración base de Tabulator
- Estandarizar integración con Django Rest Framework (DRF)
- Proporcionar formatters reutilizables
- Manejar errores de forma consistente (401, 403, 404, 500)

#### Componentes Principales

**1. `TabulatorFactory.create(selector, apiUrl, columns, options)`**
- **Configuración Base Obligatoria:**
  - `layout: "fitColumns"` - Ajuste automático de columnas
  - `pagination: true` - Paginación habilitada
  - `paginationMode: "remote"` - Paginación server-side siempre
  - `paginationSize: 10` - Tamaño de página por defecto
  - `ajaxURL: apiUrl` - URL base para carga inicial de datos

- **Adaptador DRF Automático:**
  - `ajaxURLGenerator`: Construye URLs con parámetros `page`, `page_size`, `search` (desde input selector)
  - `ajaxRequest`: Usa `fetch` API con headers `X-CSRFToken` y `Content-Type: application/json`
  - `ajaxResponse`: Transforma respuesta DRF `{count, results}` a formato Tabulator `{last_page, data}`
    - **Caso 1**: Array directo → convierte a `{last_page: 1, data: [...]}`
    - **Caso 2**: Formato DRF paginado `{count, results}` → `{last_page: Math.ceil(count/pageSize), data: results}`
    - **Caso 3**: Formato Tabulator existente `{data}` → retorna sin cambios
    - **Caso 4**: Objeto directo (singleton) → convierte a `{last_page: 1, data: [objeto]}`
    - **Caso 5**: Formato desconocido → retorna `{last_page: 1, data: []}`
  - `ajaxError`: Maneja errores de red y API (401, 403) con notificaciones `notyf`

- **Manejo de Búsqueda:**
  - Soporte para `searchInputSelector` (ej: `'#search-cliente'`)
  - Debounce automático para evitar requests excesivos
  - Integración con paginación remota
  - Parámetro `?search=` agregado automáticamente a las peticiones

**2. `TabulatorFactory.formatters`**
- **`statusBadge(cell)`:**
  - Formatea booleanos como badges "Activo" (verde) / "Inactivo" (gris)
  - Usa clases Bootstrap: `badge bg-success` / `badge bg-secondary`

- **`actions(config)`:**
  - Genera columna de acciones estándar (Editar/Eliminar)
  - Recibe callbacks: `onEdit(id)`, `onDelete(id)`
  - Usa iconos Font Awesome: `fas fa-edit`, `fas fa-trash`
  - Retorna configuración de columna Tabulator lista para usar

- **`badge(cell, colorClass)`:**
  - Formatter genérico para badges personalizados
  - Recibe clase de color Bootstrap (ej: `bg-primary`, `bg-warning`)

- **`valueOrFallback(cell, fallback)`:**
  - Muestra valor de celda o texto de fallback si está vacío
  - Útil para campos opcionales
  - Fallback por defecto: `'-'` si no se especifica

- **`defaultAjaxURLGenerator(url, config, params)`:**
  - Generador de URL por defecto para paginación remota
  - Agrega parámetros `page`, `page_size`, `search` automáticamente
  - Puede ser sobrescrito en `options` para casos especiales

#### Ejemplo de Uso

```javascript
// apps/tenant/core/static/core/js/clientes/clientes.page.js
const w = window;

function initTabulator() {
    const columns = [
        { title: "ID", field: "id", width: 80 },
        { 
            title: "Documento", 
            field: "documento_completo",
            formatter: (cell) => {
                const row = cell.getRow().getData();
                return `${row.tipo_documento_display} ${row.documento_completo}`;
            }
        },
        { title: "Razón Social", field: "razon_social" },
        { title: "Email", field: "email" },
        { 
            title: "Estado", 
            field: "activo",
            formatter: w.TabulatorFactory.formatters.statusBadge
        },
        w.TabulatorFactory.formatters.actions({
            onEdit: (id) => editar(id),
            onDelete: (id) => eliminar(id)
        })
    ];
    
    const table = w.TabulatorFactory.create(
        '#grid-clientes',
        '/api/v1/clientes/',
        columns,
        {
            searchInputSelector: '#search-cliente',
            paginationSize: 10
        }
    );
    
    return table;
}

// Lazy loading con DOMUtils
w.DOMUtils.onVisibleOnce('#tab-clientes', () => {
    const table = initTabulator();
    // Exponer módulo globalmente para acceso externo
    w.ClientesModule = { table, refresh: () => table.replaceData() };
});
```

#### Requisitos Backend (DRF)

**ViewSet con Paginación Estándar (v2.40):**
```python
# apps/tenant/clientes/api/viewsets.py
from apps.config.api.pagination import StandardResultsSetPagination

class ClienteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    queryset = Cliente.objects.none()  # ⚠️ CRÍTICO: DRF requiere queryset definido
    serializer_class = ClienteDetailSerializer  # ⚠️ CRÍTICO: DRF requiere serializer_class
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """QuerySet optimizado con soporte ?search= (Tabulator v2.40)."""
        from apps.tenant.clientes.services import qs_list
        empresa = self.get_empresa()
        search = self.request.query_params.get('search', None)
        return qs_list(empresa.id, search=search)
    
    def list(self, request):
        """Endpoint para Tabulator (GET /api/v1/clientes/).
        
        ⚠️ v2.40: SIEMPRE retorna formato paginado para consistencia con Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            # Caso normal: paginación activa
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Caso fallback: paginación deshabilitada, pero forzamos formato paginado
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
```

**Formato de Respuesta DRF (Tabulator espera):**
```json
{
  "count": 100,
  "next": "http://example.com/api/v1/clientes/?page=2",
  "previous": null,
  "results": [
    {"id": 1, "razon_social": "Cliente 1", ...},
    {"id": 2, "razon_social": "Cliente 2", ...}
  ]
}
```

**Transformación Automática (TabulatorFactory):**
```javascript
// TabulatorFactory.ajaxResponse transforma automáticamente:
{
  "last_page": 10,  // Math.ceil(count / pageSize)
  "data": [...]     // results
}
```

#### Ventajas de Tabulator Factory

1. **DRY (Don't Repeat Yourself):**
   - Configuración base centralizada
   - No duplicar lógica de paginación, búsqueda, errores
   - Formatters reutilizables

2. **Consistencia:**
   - Todas las tablas se comportan igual
   - Manejo de errores uniforme (401, 403, 404, 500)
   - Transformación automática DRF → Tabulator

3. **Mantenibilidad:**
   - Cambios en un solo lugar afectan todos los módulos
   - Actualizaciones de Tabulator centralizadas
   - Código legacy eliminado (Zero-Legacy)

4. **Escalabilidad:**
   - Agregar nueva tabla requiere ~10 líneas de código
   - Fácil onboarding de nuevos desarrolladores
   - Soporte para diferentes formatos de respuesta (DRF, array, objeto directo)

5. **Rendimiento:**
   - Paginación remota por defecto (reduce carga inicial)
   - Búsqueda en tiempo real con debounce
   - Lazy loading con `DOMUtils.onVisibleOnce()`

6. **Seguridad:**
   - CSRF automático en todas las peticiones
   - Manejo robusto de errores de autenticación
   - Headers de seguridad consistentes

#### Módulos Implementados con Tabulator Factory

- ✅ **Clientes** (`apps/tenant/core/static/core/js/clientes/clientes.page.js`)
  - Backend: `ClienteViewSet` con `StandardResultsSetPagination` y soporte `?search=`
  - Frontend: Tabla con columnas personalizadas, acciones Editar/Eliminar
  - Funcionalidades: CRUD completo, soft delete, validación de duplicados

- ✅ **Proveedores** (`apps/tenant/core/static/core/js/proveedores/proveedores.page.js`)
  - Backend: `ProveedorViewSet` con `StandardResultsSetPagination` y soporte `?search=`
  - Frontend: Tabla con columnas personalizadas, acciones Editar/Eliminar
  - Funcionalidades: CRUD completo, soft delete, validación de duplicados
  - Limpieza: Eliminado código legacy (DataTables, forms.py, views.py)

- ✅ **Gastos** (`apps/tenant/core/static/core/js/gastos/gastos.page.js`)
  - Backend: `GastoViewSet` con `StandardResultsSetPagination` y soporte `?search=`
  - Frontend: Tabla con columnas personalizadas, acciones Editar/Eliminar
  - Funcionalidades: CRUD completo, panel de resumen financiero
  - Limpieza: Eliminado `forms.py`, código legacy DataTables

- ✅ **Empleados** (`apps/tenant/core/static/core/js/empleados/empleados.page.js`)
  - Backend: `EmpleadoViewSet`, `ContratoViewSet`, `DevengoViewSet` con `StandardResultsSetPagination`
  - Frontend: Tabla con acciones Editar, Asignar Contrato, Asignar Devengo, Ver Historial, Eliminar
  - Funcionalidades: CRUD completo, gestión de contratos y devengos

- ✅ **Facturas** (`apps/tenant/core/static/core/js/facturas/facturas.page.js`)
  - Backend: `FacturaViewSet`, `NotaCreditoViewSet` con `StandardResultsSetPagination` y soporte `?search=`
  - Frontend: Tabla con columnas personalizadas, panel de resumen financiero (Ventas Netas, Compras Netas)
  - Funcionalidades: Filtro de Nota de Crédito, acciones Ver, Descargar XML, Aplicar NC, Eliminar
  - Limpieza: Eliminado `datatables.py`, archivos legacy DataTables

- ✅ **Inventario** (`apps/tenant/core/static/core/js/inventario/`)
  - **Productos** (`productos.page.js`): Tabla con stock, acciones Editar, Eliminar, Ver Kardex
  - **Servicios** (`servicios.page.js`): Tabla con acciones Editar, Eliminar
  - **Activos Fijos** (`activos.page.js`): Tabla con acciones Editar, Eliminar
  - **Movimientos** (`movimientos.page.js`): Kardex global con historial de movimientos
  - Backend: ViewSets con `StandardResultsSetPagination` y soporte `?search=`
  - Limpieza: Eliminado código legacy DataTables

- ✅ **Empresa** (`apps/tenant/core/static/core/js/empresa/empresa.page.js`)
  - Backend: `EmpresaViewSet` con `StandardResultsSetPagination` y soporte `?search=`
  - Frontend: Tabla singleton (0-1 registros), acciones Editar, Ver Detalle
  - Funcionalidades: CRUD completo, ENFORCED MODE (mutaciones solo vía Core Orchestrator)
  - Limpieza: Eliminado código legacy DataTables, directorio `static/` legacy

- ✅ **MailInboxConfig** (`apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js`)
  - Backend: `MailInboxConfigViewSet` con `StandardResultsSetPagination` y soporte `?search=`
  - Frontend: Tabla con columnas personalizadas (Nombre, Email, Proveedor, Host IMAP, Puerto, SSL, Estado)
  - Funcionalidades: CRUD completo, Probar Conexión, acciones Editar, Probar Conexión, Eliminar
  - Seguridad: Passwords nunca expuestos, cifrado automático
  - Limpieza: Eliminado código legacy DataTables

#### Checklist de Implementación

- [ ] Crear archivo JS del módulo (ej: `clientes.page.js`)
- [ ] Definir columnas específicas del módulo
- [ ] Usar `TabulatorFactory.create()` en lugar de configuración manual
- [ ] Implementar callbacks `onEdit` y `onDelete` para acciones
- [ ] Conectar input de búsqueda con `searchInputSelector`
- [ ] Usar `DOMUtils.onVisibleOnce()` para lazy loading
- [ ] Exponer módulo globalmente (ej: `w.ClientesModule`) para acceso externo
- [ ] Verificar que ViewSet tenga `queryset` y `serializer_class` definidos
- [ ] Verificar que ViewSet use `StandardResultsSetPagination`
- [ ] Verificar que `list()` retorne formato DRF estándar `{count, results}`

### Error Boundary Pattern (UIManager v2.60)

**⚠️ ARQUITECTURA v2.60: Error Boundary Pattern para Aislamiento de Lógica de Negocio**

**Objetivo:**
- Aislar la lógica de negocio de la presentación de errores y manejo de modales
- Centralizar el manejo de errores, modales y formularios en un orquestador único
- Compatible con Zero Trust v2.40
- Eliminar bloques `try/catch` redundantes que solo muestran alertas básicas

**Componentes:**

#### 1. UIManager (`apps/tenant/core/static/core/js/common/ui-manager.js`)

**Orquestador central de UI** que expone cuatro métodos principales:

**`handleError(response, context, options)`** ⚠️ v2.60: Boundary principal
- Decide dónde mostrar el error (notificación flotante o mensaje en modal)
- Si hay un modal abierto y un contenedor de error disponible, muestra el error ahí
- Si no, muestra notificación flotante (fallback)
- ⚠️ **REGLA DE ORO**: Si el error es 401, NO muestra notificación (interceptor global maneja redirección)
- Parámetros:
  - `response`: Objeto de respuesta de la API con formato `{ok, status, data}`
  - `context`: Contexto para logs (ej: `"[mailinbox.page]"`)
  - `options`: `{modalSelector, errorContainerSelector}` - Selectores opcionales para mostrar error en modal
- Retorna: `true` si el error fue manejado, `false` en caso contrario

**`notifyError(response, context)`**
- Procesa objetos de respuesta de error de la API
- Busca `data.detail` o `data.message` en el objeto de respuesta
- Usa `SintelFeedback.handleAPIError()` (preferido) o `window.notyf.error()` (fallback)
- ⚠️ **REGLA DE ORO**: Si el error es 401, NO muestra notificación (interceptor global maneja redirección)
- Parámetros:
  - `response`: Objeto de respuesta de error (puede ser `{status, data}`, `Response`, o `Error`)
  - `context`: Contexto para logs (ej: `"[TabulatorFactory]"`)

**`handleModal(selector, action)`**
- Encapsula la lógica de Bootstrap 5 para abrir/cerrar modales de forma segura
- Verifica que la instancia del modal exista antes de operar
- Parámetros:
  - `selector`: Selector CSS del modal (ej: `'#modal-cliente'`)
  - `action`: Acción a realizar (`'show'` o `'hide'`)
- Retorna: `true` si la operación fue exitosa, `false` en caso contrario

**`resetForm(selector)`**
- Limpia formularios y oculta contenedores de error locales
- Resetea campos nativos del formulario
- Oculta contenedores de error (`.alert-danger`, `.invalid-feedback`, `.error-message`)
- Remueve clases de error de Bootstrap (`.is-invalid`)
- Parámetros:
  - `selector`: Selector CSS del formulario (ej: `'#form-cliente'`)
- Retorna: `true` si la operación fue exitosa, `false` en caso contrario

**Dependencias:**
- `SintelFeedback` (preferido) - `apps/tenant/core/static/core/js/utils/feedback.js`
- `Bootstrap 5` (para modales)
- `window.notyf` (fallback para notificaciones)

**Uso:**
```javascript
// ⚠️ v2.60: Aislamiento Gradual - Boundary principal (decide dónde mostrar error)
window.UIManager.handleError(
  { ok: false, status: 400, data: { detail: 'Cliente no encontrado' } },
  '[mailinbox.page]',
  {
    modalSelector: '#modal-mailinbox-form',
    errorContainerSelector: '#mailinbox-form-feedback'
  }
);

// Notificar error de API (notificación flotante)
window.UIManager.notifyError(
  { status: 400, data: { detail: 'Cliente no encontrado' } },
  '[clientes.page]'
);

// Abrir modal
window.UIManager.handleModal('#modal-cliente', 'show');

// Cerrar modal
window.UIManager.handleModal('#modal-cliente', 'hide');

// Limpiar formulario
window.UIManager.resetForm('#form-cliente');
```

#### 2. Integración con Tabulator Factory

**Actualización v2.60:**
- `TabulatorFactory.ajaxError()` ahora delega a `UIManager.notifyError()`
- Eliminado manejo directo de errores con `SintelFeedback` en Tabulator Factory
- Fallback a `SintelFeedback` si `UIManager` no está disponible (compatibilidad)

**Código:**
```javascript
ajaxError: function(error) {
    console.error('[TabulatorFactory] Error AJAX:', error);
    // ⚠️ v2.60: Error Boundary Pattern - Delegar a UIManager
    if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
            { status: 500, data: { detail: 'Error al cargar los datos. Por favor, intenta nuevamente.' } },
            '[TabulatorFactory]'
        );
    } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
        // Fallback: usar SintelFeedback directamente si UIManager no está disponible
        w.SintelFeedback.handleAPIError({ status: 500, data: { detail: 'Error al cargar los datos. Por favor, intenta nuevamente.' } }, '[TabulatorFactory]', false);
    }
}
```

#### 3. Estandarización de Respuestas en el Core (Backend)

**Actualización v2.60:**
- Los handlers de error (`custom_page_not_found_view`, `custom_permission_denied_view`) ahora detectan peticiones API
- Si la petición es API (path `/api/` o headers `Accept: application/json`), devuelven JSON estructurado
- Si la petición es HTML, mantienen el comportamiento original (renderizar template)

**Formato JSON Estructurado:**
```json
{
  "detail": "Mensaje de error legible",
  "status": 404,
  "code": "NOT_FOUND"
}
```

**Código:**
```python
# Detectar si es petición API
is_api_request = (
    request.path.startswith('/api/') or
    request.headers.get('Accept', '').startswith('application/json') or
    request.headers.get('Content-Type', '').startswith('application/json')
)

# Si es petición API, devolver JSON estructurado
if is_api_request:
    return JsonResponse(
        {
            'detail': 'Recurso no encontrado (404). Verifica la URL y el tenant actual.',
            'status': 404,
            'code': 'NOT_FOUND'
        },
        status=404
    )
```

**Ubicación:**
- `apps/tenant/core/api/handlers.py`

**Restricciones:**
- ⚠️ **NO usar lógica de negocio específica en `ui-manager.js`**
- ⚠️ **Eliminar bloques `try/catch` que solo muestren alertas básicas** - delegar a `UIManager`
- ⚠️ **Asegurar compatibilidad con Zero Trust v2.40**

**Beneficios:**
1. **Separación de responsabilidades**: Lógica de negocio separada de presentación de errores
2. **Consistencia**: Manejo uniforme de errores en toda la aplicación
3. **Mantenibilidad**: Cambios en un solo lugar afectan todos los módulos
4. **Testabilidad**: Fácil mockear `UIManager` en tests
5. **Reutilización**: Métodos reutilizables para modales y formularios

#### Aislamiento Gradual (v2.60)

**⚠️ PATRÓN: Aislamiento Gradual por Aplicación**

Para que la implementación sea exitosa por aplicación (como en `mailinbox.page.js`), el flujo debe seguir esta estructura de 3 capas:

**1. Capa de Datos (`*.api.js`):**
- Realiza el `fetch` y retorna el objeto de respuesta completo `{ok, status, data}`
- **NO lanza excepciones** - siempre retorna un objeto estructurado
- Usa `window.http()` que ya retorna `{ok, status, data}`
- Ejemplo:
```javascript
// mailinbox.api.js
w.mailinboxAPI = {
  get: (id) => w.http('GET', `${API_BASE}/${id}/`),
  create: (payload) => w.http('POST', `${API_BASE}/`, payload),
  update: (id, payload) => w.http('PUT', `${API_BASE}/${id}/`, payload)
};
```

**2. Capa de Presentación (`ui-manager.js`):**
- Es un "Boundary" o frontera que decide dónde mostrar el error
- `UIManager.handleError(response, context, options)` decide:
  - **Notificación flotante (toast)**: Para errores generales
  - **Mensaje dentro del modal**: Si hay un modal abierto y un contenedor de error disponible
- Parámetros:
  - `response`: Objeto `{ok, status, data}` de la capa de datos
  - `context`: Contexto para logs (ej: `"[mailinbox.page]"`)
  - `options`: `{modalSelector, errorContainerSelector}` para mostrar error en modal
- Ejemplo:
```javascript
// ui-manager.js
function handleError(response, context = '', options = {}) {
  if (response.ok) return false;
  if (response.status === 401) return false; // Interceptor global maneja
  
  // Si hay modal abierto, mostrar error ahí
  if (options.modalSelector && options.errorContainerSelector) {
    const modal = d.querySelector(options.modalSelector);
    const errorContainer = d.querySelector(options.errorContainerSelector);
    if (modal && errorContainer && modal.classList.contains('show')) {
      errorContainer.className = 'alert alert-danger';
      errorContainer.textContent = response.data.detail || 'Error desconocido';
      errorContainer.classList.remove('d-none');
      return true;
    }
  }
  
  // Fallback: notificación flotante
  notifyError(response, context);
  return true;
}
```

**3. Lógica de Negocio (`*.page.js`):**
- **Antes**: Tenía bloques `try { ... } catch (e) { notyf.error(e) }` que causaban errores de sintaxis si se anidaban mal
- **Ahora**: Solo pregunta `if (!res.ok) return UIManager.handleError(res);`
- **Sin bloques try/catch** para manejo de errores de API
- Ejemplo:
```javascript
// mailinbox.page.js
async function guardar() {
  const { id, payload } = collectMailInboxPayload();
  
  // Validaciones básicas
  if (!payload.nombre) {
    if (w.SintelFeedback) {
      w.SintelFeedback.error('Por favor complete todos los campos requeridos');
    }
    return;
  }
  
  // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
  const res = id 
    ? await w.mailinboxAPI.update(id, payload)
    : await w.mailinboxAPI.create(payload);
  
  // ⚠️ v2.60: Aislamiento Gradual - Lógica de Negocio solo verifica ok
  if (!res.ok) {
    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
      w.UIManager.handleError(res, '[mailinbox.page]', {
        modalSelector: '#modal-mailinbox-form',
        errorContainerSelector: '#mailinbox-form-feedback'
      });
    }
    return;
  }
  
  // Éxito: mostrar notificación y cerrar modal
  if (w.SintelFeedback) {
    w.SintelFeedback.success(id ? 'Configuración actualizada correctamente' : 'Configuración creada correctamente');
  }
  
  // Cerrar modal usando UIManager
  if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
    w.UIManager.handleModal('#modal-mailinbox-form', 'hide');
  }
  
  // Refrescar tabla
  if (table) {
    table.replaceData();
  }
}
```

**Ventajas del Aislamiento Gradual:**
1. **Eliminación de bloques try/catch redundantes**: No más errores de sintaxis por anidamiento incorrecto
2. **Código más limpio**: La lógica de negocio se enfoca en el flujo, no en el manejo de errores
3. **Decisión inteligente de presentación**: El error se muestra donde tiene más sentido (modal o toast)
4. **Reutilización**: La misma capa de datos puede usarse en múltiples contextos
5. **Testabilidad**: Fácil mockear cada capa independientemente

**Checklist de Migración:**
- [ ] Crear archivo `*.api.js` que retorne `{ok, status, data}` usando `window.http()`
- [ ] Eliminar bloques `try/catch` que solo muestren alertas básicas
- [ ] Reemplazar con `if (!res.ok) return UIManager.handleError(res, context, options)`
- [ ] Definir `modalSelector` y `errorContainerSelector` si hay modal
- [ ] Verificar que los errores se muestren correctamente (en modal o toast)

### Logging Estándar

**⚠️ OBSERVABILIDAD (v2.34 - Implementado):**

**Configuración Normalizada:**
- **Desarrollo**: Logging simple a consola, sin `request_id` (evita errores en arranque/import-time)
  - Formatter: `brief` (simple y legible)
  - `django.server` a nivel `WARNING` (reducir ruido)
- **Producción**: Access log sin query string (Gunicorn usa `%(U)s`, sin `%(q)s`)
  - Formatter: `simple` (sin campos opcionales)
  - Loggers específicos por dominio: `facturas`, `apps.services.xml_ingest`, `celery`

**Correlación de Logs (request_id) - Opcional:**
- **Middleware**: `RequestContextMiddleware` (opcional, no activo por defecto)
  - Genera `request_id` (UUID4) y lo almacena en `request.META['REQUEST_ID']`
  - Extrae `schema_name` de `request.tenant` y lo adjunta a logs vía filtro
  - Filtro: `RequestContextLogFilter` añade `request_id`/`schema_name` a LogRecords (con fallback a "-")
- **Formatters opcionales**: `verbose_with_context` disponible si se activa el middleware
- **⚠️ IMPORTANTE**: El formatter por defecto NO incluye `%(request_id)s` para evitar errores si el middleware no está activo

**Separación de Logs por Dominio:**
- Loggers específicos: `facturas`, `apps.services.xml_ingest`, `celery`, `django.server`
- Handlers: `console` con formatter apropiado según entorno
- Beneficio: Facilita análisis y monitoreo por área funcional

#### Desarrollo
```python
# config/settings.py (dev)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "brief": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "%(levelname)s | %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",  # Simple, sin request_id
            "level": "INFO",
        },
    },
    "loggers": {
        "django.server": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "facturas": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.services.xml_ingest": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
```

#### Producción (Gunicorn)
```python
# infra/docker/app/gunicorn.conf.py
accesslog = "-"
access_logformat = '%(h)s %(t)s "%(m)s %(U)s HTTP/%(H)s" %(s)s %(B)s'
# %(U)s = path sin query (omite %(q)s para evitar exponer parámetros)
```

#### Middleware Opcional (RequestContextMiddleware)
```python
# apps/public/core/middleware.py
# ⚠️ OPCIONAL: Solo activar si se necesita correlación de logs
# Añadir a MIDDLEWARE después de TenantMainMiddleware:
'apps.public.core.middleware.RequestContextMiddleware',
```

### Checklist de Aplicación (por módulo)

**Para módulos nuevos o refactorización completa (v2.40+):**
- [ ] **⚠️ v2.40: Usar Tabulator Factory** en lugar de DataTables manual
  - [ ] Crear archivo JS del módulo usando `TabulatorFactory.create()`
  - [ ] Definir columnas específicas del módulo
  - [ ] Implementar callbacks `onEdit` y `onDelete` para acciones
  - [ ] Conectar input de búsqueda con `searchInputSelector`
  - [ ] Usar `DOMUtils.onVisibleOnce()` para lazy loading
- [ ] **Backend API-First:**
  - [ ] Verificar que ViewSet tenga `queryset` y `serializer_class` definidos (requerido por DRF router)
  - [ ] Verificar que ViewSet use `StandardResultsSetPagination` (page_size=10)
  - [ ] Verificar que `list()` retorne formato DRF estándar `{count, results}`
  - [ ] Implementar `LIST_FIELDS`, `DETAIL_FIELDS`, `qs_list()`, `qs_detail()` en services.py
  - [ ] Aplicar `only()`/`defer()` y `select_related()`/`prefetch_related()` en QuerySets
  - [ ] Manejar `IntegrityError` en servicios (duplicados) con `ValidationError` amigable
- [ ] **Frontend:**
  - [ ] Crear templates: `list.html` (shell estático), `modals.html` (modal único), `assets_*.html` (carga ordenada)
  - [ ] Integrar en `workspace.html` (tab, sección, assets)
- [ ] **Limpieza Zero-Legacy:**
  - [ ] Eliminar `forms.py`, `views.py`, `urls.py` (HTML views)
  - [ ] Eliminar `api/datatables.py` (si existe)
  - [ ] Eliminar templates legacy (si existen)
  - [ ] Eliminar JS legacy (si existen)

**Para módulos legacy con DataTables (mantenimiento):**
- [ ] Cambiar todas las tablas DataTables a POST con CSRF y columnas visibles
- [ ] Añadir/ajustar serializadores de lista (fields mínimos)
- [ ] Aplicar `only()`/`defer()` y `select_related()`/`prefetch_related()` en QuerySets
- [ ] Activar DRF Pagination global (o por vista) y revisar tamaños
- [ ] **⚠️ v2.40: Migrar DataTables a @action en ViewSets** (deprecar `datatables.py` separados)
- [ ] **⚠️ v2.40: Implementar lazy loading con `DOMUtils.onVisibleOnce()`** en JavaScript
- [ ] **⚠️ v2.40: Agregar FK a Empresa e índice** en modelos Meta
- [ ] **⚠️ v2.37+: Implementar `LIST_FIELDS`, `DETAIL_FIELDS`, `qs_list()`, `qs_detail()`** en services.py
- [ ] Reemplazar endpoints existentes por el Helper DataTables (`DataTableServer` + `DataTableSpec`) con whitelists (opcional, legacy)
- [ ] Configurar LOGGING dev y access-log prod sin querystrings

---

## 🛠️ Stack Tecnológico

### Backend
- **Python:** 3.12
- **Django:** 5.x (>=5.0,<5.1) - Compatible con Python 3.12
- **django-tenants:** >=3.9,<3.10 (Multi-tenant por esquemas, versión mínima 3.9.0 validada)
- **Django REST Framework (DRF):** >=3.14,<4.0 (API REST, enfoque API-first)
- **django-filter:** >=23.5,<24.0 (Filtrado avanzado para APIs)

### Base de Datos
- **PostgreSQL:** 16
- **Driver:** psycopg[binary] >=3.1,<4.0 (psycopg3 como adaptador recomendado)

### Infraestructura
- **Docker:** Contenedorización
- **Docker Compose:** Orquestación de servicios
- **Redis:** 7-alpine (Cola de tareas y caché)
- **Celery:** Tareas asíncronas

### Utilidades
- **python-dotenv:** Gestión de variables de entorno
- **requests>=2.31,<3.0:** Para integraciones externas (DIAN, descargas)
- **Pillow>=10.0,<11.0:** Para ImageField en modelos Django (requerido para campos de imagen)

### Producción
- **gunicorn>=21.2,<22.0:** WSGI server para producción
- **whitenoise>=6.6,<7.0:** Servir staticfiles en producción (alternativa a Nginx)

### ETL - Parsers para Documentos Tributarios
- **pdfminer.six>=20221105:** Parser PDF
- **lxml>=5.0,<6.0:** Parser HTML/XML
- **pandas>=2.0,<3.0:** Parser Excel/CSV
- **openpyxl>=3.1,<4.0:** Engine para pandas.read_excel
- **beautifulsoup4>=4.12,<5.0:** Fallback para HTML malformado

### Generación de PDFs
- **⚠️ WeasyPrint eliminado:** Ya no se usa en el proyecto. La generación de PDF debe implementarse con una biblioteca alternativa.

### Testing y Auditoría
- **pytest>=7.4,<8.0:** Framework de testing
- **pytest-django>=4.7,<5.0:** Plugin Django para pytest
- **factory-boy>=3.3,<4.0:** Factories para datos de prueba
- **responses>=0.24,<1.0:** Mock de requests para tests
- **ruff:** Linter/formatter ultrarrápido (reglas de estilo, bugs, simplificación)
- **bandit:** Análisis de seguridad SAST (detección de issues de seguridad comunes)

---

## 🏢 Arquitectura Multi-Tenant

### Concepto

El proyecto utiliza **multi-tenancy por esquemas** de PostgreSQL, donde cada tenant (empresa) tiene su propio esquema de base de datos, mientras que el esquema `public` contiene datos compartidos.

### Esquemas

#### Esquema `public` (Compartido)
- **Apps:** `SHARED_APPS`
- **Contenido:**
  - Gestión de tenants (`apps.public.tenants`)
  - Usuarios globales (`apps.public.accounts`)
  - Catálogo DIAN (`apps.public.impuestos`)
  - Tablas de Django contrib (auth, admin, sessions, etc.)

#### Esquemas `tenant_*` (Por Empresa)
- **Apps:** `TENANT_APPS`
- **Contenido:**
  - Datos de la empresa (`apps.tenant.empresa`)
  - Facturas y documentos (`apps.tenant.facturas`)
  - Contabilidad (`apps.tenant.contabilidad`)
  - APIs REST específicas del tenant

### Middleware

#### TenantMainMiddleware

`TenantMainMiddleware` es el **primer middleware** y se encarga de:
1. Identificar el tenant según el dominio
2. Establecer el esquema de base de datos activo
3. Enrutar las consultas al esquema correcto

#### TenantSecurityAndURLConfMiddleware (v2.28, mejorado v2.29)

**Ubicación:** `apps/public/tenants/middleware_urlconf.py`

**Función:** Protege el ámbito público y garantiza que `request.urlconf` se establezca correctamente.

**Problema Resuelto (v2.28):**
- `TenantMainMiddleware` resuelve el tenant correctamente pero en algunos casos NO establece `request.urlconf`
- Django usa `ROOT_URLCONF` por defecto cuando `request.urlconf` no está establecido
- Esto causaba 404 en rutas de tenant como `/activate/` que solo existen en `TENANT_URLCONF`

**Solución (v2.28):**
- Este middleware se ejecuta DESPUÉS de `TenantMainMiddleware`
- Verifica si hay un tenant privado resuelto y establece `request.urlconf` automáticamente
- Establece `request.urlconf = settings.TENANT_URLCONF` para tenants privados
- Establece `request.urlconf = settings.ROOT_URLCONF` para tenant público

**Mejoras de Seguridad (v2.29):**
- ✅ **Múltiples capas de seguridad** para proteger el ámbito público:
  - **Capa 1**: Whitelist estricta de dominios permitidos (`ALLOWED_PUBLIC_DOMAINS`)
  - **Capa 2**: Bloqueo de subdominios intentando acceder al público
  - **Capa 3**: Validación de subdominios de localhost (solo `localhost` exacto)
- ✅ **Protección contra Host Header Attacks**: Normalización y validación estricta de host
- ✅ **Logging de seguridad completo**: Logger dedicado `security.tenants` con auditoría de intentos
- ✅ **Validación estricta de dominios**: Para ambos ámbitos (público y privado)
- ✅ **Aislamiento garantizado**: No hay posibilidad de acceso cruzado entre ámbitos

**Dominios Permitidos para Ámbito Público:**
- `sintel.com` (producción)
- `localhost` (desarrollo - solo exacto, no subdominios)
- `127.0.0.1` (desarrollo)
- `0.0.0.0` (desarrollo)

**Bloqueos de Seguridad:**
- ❌ Subdominios intentando acceder al público: `cliente.sintel.com` → 404
- ❌ Subdominios de localhost: `test.localhost` → 404
- ❌ Dominios no permitidos: `cualquier-dominio.com` → 404
- ❌ Dominio público intentando acceder a tenant privado: `sintel.com` → 403

**Posición en MIDDLEWARE:**
- Debe ir **INMEDIATAMENTE DESPUÉS** de `TenantMainMiddleware`
- Debe ir **ANTES** de `TenantSecurityMiddleware`
- Combina seguridad y establecimiento de URLConf en un solo middleware

**Referencias:**
- Informe completo: `documentacion/INFORME_AUDITORIA_404_ACTIVATE.md`
- Resumen: `documentacion/RESUMEN_SOLUCION_404_ACTIVATE.md`
- Seguridad v2.29: `documentacion/SEGURIDAD_AMBITO_PUBLICO_v2.29.md`

#### TenantSecurityMiddleware (v2.11)

**Ubicación:** `apps/public/tenants/middleware.py`

**Función:** Bloquea el acceso a tenants suspendidos (`is_active=False`)

**Posición en MIDDLEWARE:**
- Debe ir **DESPUÉS** de `TenantURLConfMiddleware` (v2.28)
- Razón: Necesita que `request.tenant` ya esté resuelto, pero debe bloquear antes de procesar vistas

**Lógica:**
1. **Excepción crítica**: Si `tenant.schema_name == 'public'`, permite el paso inmediatamente (nunca bloquea el admin global)
2. Si `tenant.is_active == False`, retorna `HttpResponseForbidden` (403) con mensaje HTML bilingüe
3. Si el tenant está activo o no existe, continúa con el flujo normal

**Mensaje de Error:**
- HTML bilingüe (Español/Inglés): "Servicio Suspendido / Service Suspended"
- Diseño responsive con CSS inline
- Informa al usuario que contacte al administrador

**Configuración en `settings.py` (v2.28):**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.public.core.middleware.ForceNoPortMiddleware',  # Normaliza HTTP_HOST
    'django_tenants.middleware.main.TenantMainMiddleware',  # Resuelve tenant
    'apps.public.tenants.middleware_urlconf.TenantURLConfMiddleware',  # ✅ v2.28: Establece request.urlconf
    'apps.public.tenants.middleware.TenantSecurityMiddleware',  # SEGURIDAD (después de TenantURLConfMiddleware)
    'apps.public.core.middleware.CSRFTrustedOriginMiddleware',  # DESARROLLO (v2.14): Permite dominios arbitrarios en CSRF
    'apps.public.core.middleware.HTTPSRedirectMiddleware',  # DESARROLLO (v2.14): Redirige HTTPS -> HTTP
    # ... resto de middlewares
]
``` 

#### CSRF Relajado en Desarrollo (v2.31)

**Ubicación:** `apps/tenant/api/authentication.py`

**Clase:** `UnsafeSessionAuthentication`

**Propósito:** Permite PATCH/POST sin validar CSRF token en desarrollo (`DEBUG=True`) para facilitar testing del workspace, sin afectar la seguridad en producción.

**Características:**
- Extiende `SessionAuthentication` de DRF
- Método `enforce_csrf()` omite la validación de CSRF
- **SOLO se usa cuando `DEBUG=True`** (condicionado en `get_authenticators()`)
- En producción (`DEBUG=False`), se usa `SessionAuthentication` estándar (CSRF estricto)

**Uso:**
```python
from django.conf import settings
from apps.tenant.api.authentication import UnsafeSessionAuthentication
from rest_framework.authentication import SessionAuthentication

class PerfilViewSet(viewsets.ModelViewSet):
    def get_authenticators(self):
        if settings.DEBUG:
            return [UnsafeSessionAuthentication()]  # Desarrollo: CSRF relajado
        else:
            return [SessionAuthentication()]  # Producción: CSRF estricto
```

**Seguridad:**
- ✅ La autenticación de sesión sigue funcionando (usuario debe estar logueado)
- ✅ Los permisos siguen aplicándose (`IsAuthenticated`, `IsTenantMember`, etc.)
- ✅ El aislamiento multi-tenant se mantiene intacto
- ✅ Solo se omite la validación de CSRF token (en desarrollo únicamente)

**Aplicado en:**
- `apps/tenant/perfil/api/viewsets.py` - `PerfilViewSet`

**Referencia:** Ver sección "Fase 2: Perfil Privado del Colaborador" para más detalles.

---

#### SessionAuthentication en Workspace (v2.32)

**Ubicación:** `config/settings.py` (REST_FRAMEWORK) y ViewSets de tenant

**Propósito:** Permitir que el workspace use cookies de sesión para autenticación desde el mismo host del tenant, evitando el problema de "logout inmediato" cuando un módulo no crítico devuelve 401.

**Configuración DRF Global:**
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # ✅ JWT para APIs externas
        'rest_framework.authentication.SessionAuthentication',  # ✅ DEV: Workspace usa cookies de sesión
    ],
}
```

**ViewSets con SessionAuthentication:**
- `apps/tenant/gastos/api/viewsets.py`: `GastoViewSet`
- `apps/tenant/clientes/api/viewsets.py`: `ClienteViewSet`, `VentaClienteViewSet`
- `apps/tenant/proveedores/api/viewsets.py`: `ProveedorViewSet`, `CompraProveedorViewSet`
- `apps/tenant/empleados/api/viewsets.py`: Todos los ViewSets (Empleado, Contrato, Afiliacion, Devengo, Capacitacion)

**Características:**
- DRF prioriza `authentication_classes` del ViewSet sobre `DEFAULT_AUTHENTICATION_CLASSES`
- Los ViewSets específicos pueden sobrescribir la configuración global
- `SessionAuthentication` solo requiere CSRF en mutaciones (POST/PATCH/DELETE); GET no necesita CSRF
- Las cookies de sesión solo funcionan desde el mismo host/puerto del tenant

**Seguridad:**
- ✅ La autenticación de sesión requiere que el usuario esté logueado
- ✅ Los permisos siguen aplicándose (`IsAuthenticated`, `IsTenantMember`, etc.)
- ✅ El aislamiento multi-tenant se mantiene intacto
- ✅ CSRF sigue siendo requerido para mutaciones (POST/PATCH/DELETE)

---

#### Manejo Inteligente de 401 en Workspace (v2.32)

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html` (función `http()`)

**Propósito:** Evitar que el workspace redirija a `/login/` cuando un módulo no crítico devuelve 401, permitiendo que el usuario permanezca en el workspace y vea el error en feedback local.

**Módulos No Críticos:**
- `gastos` (`/api/v1/gastos/`)
- `clientes` (`/api/v1/clientes/`)
- `proveedores` (`/api/v1/proveedores/`)

**Módulos Críticos (mantienen redirección):**
- `core` (`/api/v1/core/`)
- `perfil` (`/api/v1/perfil/`)
- `empresa` (`/api/v1/empresa/`)
- Otros endpoints críticos de sesión

**Implementación:**
```javascript
async function http(method, url, body) {
  const res = await fetch(url, init);
  
  if (res.status === 401) {
    // Módulos no críticos: no redirigir, retornar error para manejo local
    if (
      url.includes("/api/v1/gastos/") ||
      url.includes("/api/v1/clientes/") ||
      url.includes("/api/v1/proveedores/")
    ) {
      return { ok: false, status: 401, data: { detail: "No autorizado en módulo no crítico" } };
    }
    // Endpoints críticos: mantener redirección
    goLogin("401");
    return { ok: false, status: 401, data: { detail: "Unauthorized" } };
  }
  
  // ... resto del manejo de errores
}
```

**Módulos JS Individuales:**
- `gastos.page.js`: Lanza `Error` en lugar de redirigir a login
- `clientes.page.js`: Lanza `Error` en lugar de redirigir a login
- `proveedores.page.js`: Lanza `Error` en lugar de redirigir a login
- Todos muestran errores en `<div id="...-list-feedback">` sin interrumpir el workspace

**Comportamiento:**
- **Antes (v2.31):** Cualquier 401 redirigía a `/login/` → ciclo de logout
- **Ahora (v2.32):** 
  - Módulos no críticos: muestran error en feedback local, usuario permanece en workspace
  - Endpoints críticos: mantienen redirección a login en 401

**Tests:**
- `apps/tenant/gastos/tests/test_auth_session_smoke.py`
- `apps/tenant/clientes/tests/test_auth_session_smoke.py`
- `apps/tenant/proveedores/tests/test_auth_session_smoke.py`
- `apps/tenant/core/tests/test_workspace_401_handler_smoke.py`

**Referencia:** Ver sección "Autenticación JWT" y "SessionAuthentication en Workspace" para más detalles.

---

#### CSRFTrustedOriginMiddleware (v2.14, mejorado v2.15)

**Ubicación:** `apps/public/core/middleware.py`

**Propósito:** Permite dominios arbitrarios en desarrollo agregándolos automáticamente a `CSRF_TRUSTED_ORIGINS`.

**Funcionamiento:**
- En `DEBUG=True`, detecta el dominio de la request (sin puerto)
- Agrega automáticamente los orígenes HTTP y HTTPS a `CSRF_TRUSTED_ORIGINS` si no están presentes
- Establece `HTTP_ORIGIN` en `request.META` para que Django lo use en validación CSRF
- Permite usar dominios arbitrarios (ej: `ejemplo.com`, `tupapi.com`) sin configuración manual

**Mejoras v2.15:**
- Soporte automático para HTTP y HTTPS
- Establecimiento de `HTTP_ORIGIN` en `request.META` para validación CSRF más robusta
- Mejor manejo de dominios con y sin puerto

**Posición en MIDDLEWARE:**
- Debe ir **DESPUÉS** de `TenantSecurityMiddleware`
- Debe ir **ANTES** de `HTTPSRedirectMiddleware` y `CsrfViewMiddleware`

**Seguridad:**
- Solo funciona en `DEBUG=True`
- En producción, se requiere lista explícita en `CSRF_TRUSTED_ORIGINS`

#### HTTPSRedirectMiddleware (v2.14)

**Ubicación:** `apps/public/core/middleware.py`

**Propósito:** Redirige peticiones HTTPS a HTTP en modo desarrollo y maneja headers de seguridad.

**Funcionamiento:**
- Detecta peticiones HTTPS mediante `request.is_secure()` o headers del proxy
- Redirige a URL HTTP equivalente
- En desarrollo, establece `Cross-Origin-Opener-Policy` solo para `localhost` y `127.0.0.1` para evitar advertencias del navegador

**Limitación:**
- Si el navegador fuerza HTTPS, el servidor HTTP no puede procesarla antes de que el middleware intervenga
- Solución: usar HTTP explícitamente (`http://`) o limpiar HSTS del navegador (`chrome://net-internals/#hsts`)

**Posición en MIDDLEWARE:**
- Debe ir **DESPUÉS** de `CSRFTrustedOriginMiddleware`
- Debe ir **ANTES** de `SecurityMiddleware`

#### ForceNoPortMiddleware (v2.20)

**Ubicación:** `apps/public/core/middleware.py`

**Propósito:** Normaliza `HTTP_HOST` eliminando puertos antes de que `django-tenants` intente resolver el tenant.

**Funcionamiento:**
- Elimina el puerto de `HTTP_HOST` (ej: `cliente.localhost:8000` → `cliente.localhost`)
- Garantiza que `django-tenants` siempre busque dominios sin puerto en la base de datos
- Conforme a la documentación oficial: los dominios en `Domain.domain` deben ser FQDN puro sin puerto

**Posición en MIDDLEWARE:**
- Debe ir **DESPUÉS** de `SessionMiddleware`
- Debe ir **ANTES** de `TenantMainMiddleware` (crítico)

### Acceso por Dominio (Alineación con django-tenants) ✅ v2.22

**Conforme a la documentación oficial de django-tenants:** Cada tenant privado es accesible exclusivamente por su dominio (hostname). El middleware resuelve el tenant por host y cambia el `search_path` al esquema del tenant; las rutas del tenant se sirven vía `TENANT_URLCONF` y el usuario propietario puede logear en `/login/` bajo ese dominio.

#### Routing por Hostname

**Estrategia:** Routing por hostname (no por subcarpeta), recomendada por la documentación oficial de django-tenants.

**Flujo (v2.28):**
1. `ForceNoPortMiddleware` normaliza `HTTP_HOST` eliminando puertos
2. `TenantMainMiddleware` lee el hostname, busca el `Domain` en el esquema `public` y fija el esquema del tenant
3. `TenantURLConfMiddleware` (v2.28) garantiza que `request.urlconf = TENANT_URLCONF` para tenants privados
4. Django usa `TENANT_URLCONF = 'config.urls_tenant'` para servir rutas del tenant
5. **Activación del Owner (v2.24, corregido v2.27)**: El owner accede a `/activate?token=...` en el subdominio del tenant
   - Valida token firmado con TTL (24 horas)
   - Verifica membresía activa en el tenant
   - Establece password y loguea automáticamente
   - **Redirige usando URL absoluta** (v2.27): `http://{domain}/dashboard/` para garantizar que el middleware resuelva el tenant correctamente
6. **Login normal**: Usuarios con password usable pueden logear en `/login/` bajo el dominio del tenant

**⚠️ Problemas Resueltos (v2.27-v2.28):**
- **v2.27**: Error de redirect después de activación - Solucionado usando URL absoluta en lugar de `reverse()`
- **v2.28**: Error 404 en `/activate/` - Solucionado con `TenantURLConfMiddleware` que garantiza `request.urlconf`

**Referencias:**
- Solución Redirect: `documentacion/SOLUCION_REDIRECT_TENANT.md`
- Informe 404: `documentacion/INFORME_AUDITORIA_404_ACTIVATE.md`

**Configuración:**
```python
# config/settings.py
ROOT_URLCONF = 'config.urls_public'  # Dominio público
TENANT_URLCONF = 'config.urls_tenant'  # Dominios de tenants
```

#### Normalización de Dominios

**⚠️ CRÍTICO: `Domain.domain` SIEMPRE es FQDN puro (sin protocolo, sin www, sin puerto, sin rutas)**

**Reglas estrictas (conforme a doc oficial de django-tenants):**
- **Sin protocolo:** Eliminar `http://` y `https://`
- **Sin www:** Eliminar prefijo `www.`
- **Sin puerto:** Eliminar `:8000`, `:443`, etc. (PROHIBIDO según doc oficial)
- **Sin rutas:** Eliminar `/admin/login/`, etc.
- **FQDN puro:** Solo dominio en minúsculas (ej: `cliente.sintel.com`)

**⚠️ IMPORTANTE - Separación de Dominios vs URLs:**
- **`Domain.domain` (base de datos):** SIEMPRE FQDN puro, NUNCA incluye puerto
  - Ejemplo válido: `cliente.sintel.com`
  - Ejemplo inválido: `cliente.sintel.com:8000` (rechazado por validador)
- **URLs absolutas (construcción en runtime):** Los puertos SOLO se usan para construir URLs en desarrollo
  - Desarrollo: `http://cliente.sintel.com:8000/login/` (puerto en URL, NO en `Domain.domain`)
  - Producción: `https://cliente.sintel.com/login/` (sin puerto)
  - El puerto se obtiene de `settings.APP_PORT` (8000 en dev, 80/443 en prod)

**Implementación:**
- Función `normalize_domain()` en `apps/public/tenants/utils.py`
- Validador en `DomainSerializer.validate_domain()` rechaza dominios con puerto
- `ForceNoPortMiddleware` normaliza `HTTP_HOST` antes de `django-tenants`

**Ejemplos:**
```python
# Normalización (para guardar en Domain.domain)
normalize_domain("HTTPS://WWW.CLIENTE.LOCALHOST:8000/admin/")  # → "cliente.localhost"
normalize_domain("http://www.ejemplo.com:443/")  # → "ejemplo.com"

# Construcción de URLs (en runtime, NO se guarda en DB)
domain = "cliente.sintel.com"  # Desde Domain.domain (sin puerto)
port = settings.APP_PORT  # 8000 en dev, 80/443 en prod
url = f"http://{domain}:{port}/login/"  # Solo para construir URLs, NO para guardar
```

#### Client + Domain (auto_create_schema)

**Modelo Client:**
```python
class Client(TenantMixin):
    auto_create_schema = True  # A nivel de clase (no como argumento)
    # Al guardar, se crea/sincroniza el esquema del tenant automáticamente
```

**Modelo Domain:**
```python
class Domain(DomainMixin):
    domain = models.CharField(...)  # FQDN limpio (sin puerto, sin www)
    is_primary = models.BooleanField(...)  # Un primario por tenant (constraint)
```

**Constraints:**
- `UniqueConstraint` en `Domain`: solo un `is_primary=True` por tenant
- `unique=True` en `Domain.domain`: unicidad global

#### Onboarding de Tenants

**Servicio:** `apps/services/onboarding/empresa_service.py`

**Flujo (transacción atómica):**
1. **Usuario global** (public): Crea usuario con `set_unusable_password()` (v2.24, reforzado v2.29)
   - ⚠️ **v2.29**: NO se aceptan campos de password en onboarding (serializer rechaza password/password1/password2/owner_password)
   - ⚠️ **v2.24**: Owner se crea SIN password usable (`set_unusable_password()`)
   - ⚠️ **v2.24**: El password se establece EXCLUSIVAMENTE durante la activación en el subdominio del tenant
   - Usa generación de username único desde email (igual que v2.23)
   - Si el usuario existe con password usable, se mantiene (compatibilidad hacia atrás)
2. **Client** (public): `Client.objects.create()` → crea esquema automáticamente (`auto_create_schema=True`)
3. **Domain** (public): `Domain.objects.get_or_create(domain=_build_primary_domain(...), is_primary=True)` (v2.25)
   - ⚠️ **v2.25**: Autogeneración de dominio FQDN como `<schema>.<TENANT_DOMAIN_BASE>` si no se proporciona
   - ⚠️ **v2.25**: El dominio se normaliza (sin protocolo/www/puerto/rutas) y valida como FQDN antes de guardar
   - ⚠️ **v2.25**: Formato esperado: `cliente.sintel.com` (siempre con TLD)
4. **TenantMembership** (public): `TenantMembership.objects.get_or_create(client=..., user=..., rol="ADMIN", is_primary_admin=True)`
5. **Token de invitación** (public): Genera token firmado con TTL (default: 24 horas, configurable por entorno) y envía email (v2.24)
   - ⚠️ **v2.24**: Token incluye `user_id` y `tenant_id` para validación
   - ⚠️ **v2.24**: Email contiene link absoluto al subdominio: `https://{tenant}.{base}/activate?token=...`
   - ⚠️ **v2.25**: El link usa el dominio FQDN autogenerado (ej: `https://cliente.sintel.com/activate?token=...`)
   - ⚠️ **v2.24**: Si falla el envío de email, el onboarding continúa (no bloquea)
6. **Activación del Owner** (tenant, v2.24, corregido v2.27-v2.30):
   - ⚠️ **v2.30**: **API-First completo** - NO existen vistas HTML para activación
   - ⚠️ **v2.30**: El endpoint `/api/v1/landing/auth/activate/?token=...` responde SOLO JSON
   - ⚠️ **v2.30**: Abrir la URL en el navegador NUNCA mostrará un formulario HTML
   - ⚠️ **v2.24**: El owner accede a `/api/v1/landing/auth/activate/?token=...` en el subdominio del tenant
   - ⚠️ **v2.28**: `TenantURLConfMiddleware` garantiza que la ruta se resuelva correctamente (no 404)
   - ⚠️ **v2.29**: Solo funciona si el usuario NO tiene password usable (una sola activación)
   - ⚠️ **v2.29**: Si el usuario ya tiene password usable, retorna **409 Conflict** con mensaje JSON
   - ⚠️ **v2.27**: Después de activación, redirect usa URL absoluta `http://{domain}/dashboard/` para garantizar resolución correcta del tenant
   - ⚠️ **v2.24**: Valida token, verifica membresía, establece password y loguea automáticamente
   
   **⚠️ IMPORTANTE v2.30 - Responsabilidad del Frontend:**
   - El frontend es responsable de:
     - Mostrar formulario de activación si `GET /api/v1/landing/auth/activate/?token=...` retorna **200 OK**
     - Mostrar mensaje "Cuenta ya activada" + redirigir a `/login/` si retorna **409 Conflict**
     - Mostrar error si retorna **400 Bad Request** (token inválido/expirado)
   - Django NO renderiza formularios HTML - toda la UI pertenece al frontend
7. **Seed opcional** (tenant): `with schema_context(schema_name): ...` para crear datos iniciales dentro del tenant
   - ⚠️ **v2.23**: Verifica que la tabla exista antes de seedear (resiliente a timing de migraciones)

**Idempotencia:**
- `get_or_create` / `update_or_create` previene duplicados
- Manejo de `IntegrityError` con read-back para condiciones de carrera
- Usuario se obtiene por email si existe (idempotente)

**Seguridad (v2.23 + v2.24 + v2.29 + v2.30):**
- **Username nunca vacío**: `UserManager._create_user()` genera username desde email con fallback a "user"
- **Password unusable en onboarding** (v2.24, reforzado v2.29): Owner se crea con `set_unusable_password()`
- **NO se aceptan campos de password en onboarding** (v2.29): Serializer rechaza explícitamente password/password1/password2/owner_password
- **Password se establece EXCLUSIVAMENTE en activación** (v2.24, reforzado v2.29): El owner define su password solo en `/api/v1/landing/auth/activate/?token=...` del subdominio del tenant
- **Una sola activación** (v2.29): Si el usuario ya tiene password usable, la activación retorna **409 Conflict**
- **⚠️ CRÍTICO v2.29**: Si se usa `create_user()` o `set_password()` en onboarding → activación quedará bloqueada (409)
- **Token de invitación** (v2.24): Firmado con `SECRET_KEY`, TTL configurable (default: 24 horas), one-time use
- **Validación de membresía** (v2.24): La activación verifica que el usuario tenga membresía activa en el tenant
- **⚠️ v2.30**: El Owner DEBE crearse con `set_unusable_password()` - cualquier otro método bloqueará la activación

**Login URL (v2.23):**
- Construido sin puerto: `http://{domain}/login/` (o `https://` en producción)
- Apunta a `/login/` del `TENANT_URLCONF`
- ⚠️ **v2.24**: Se mantiene para compatibilidad con consola, pero el owner debe activar primero

**Activation URL (v2.24, corregido v2.28, actualizado v2.30):**
- Construido sin puerto: `http://{domain}/api/v1/landing/auth/activate/?token=...` (o `https://` en producción)
- ⚠️ **v2.30**: URL API-first - apunta a `/api/v1/landing/auth/activate/` del `TENANT_URLCONF`
- ⚠️ **v2.28**: `TenantURLConfMiddleware` garantiza que la ruta se resuelva correctamente (no 404)
- ⚠️ **v2.30**: El endpoint responde SOLO JSON - NO renderiza formularios HTML

**Redirect después de Activación (v2.27, actualizado v2.30):**
- ⚠️ **Problema resuelto**: El redirect después de activación usaba `reverse()` que podía usar `ROOT_URLCONF` incorrecto
- ⚠️ **Solución**: Usa URL absoluta `http://{domain}/dashboard/` para garantizar que el middleware resuelva el tenant correctamente
- ⚠️ **Implementación (v2.30)**: `apps/tenant/landing/api/views.py` - `OwnerActivationAPIView.post()` retorna `redirect_url` absoluta en la respuesta JSON
- ⚠️ **v2.28**: `TenantURLConfMiddleware` garantiza que la ruta se resuelva correctamente (no 404)
- ⚠️ **v2.30**: Vistas HTML eliminadas - toda la funcionalidad está en la API REST
- Incluido en respuesta del onboarding si se generó token de invitación

**⚠️ IMPORTANTE v2.30 - Significado del Status 409 Conflict:**
- **409 Conflict** = El usuario YA tiene contraseña usable
- Esto NO es un error técnico - es el comportamiento esperado cuando:
  - El usuario fue activado previamente
  - O fue creado incorrectamente (sin `set_unusable_password()`)
- En este caso, NO se debe mostrar formulario de activación
- El frontend debe mostrar mensaje: "La cuenta ya fue activada. Por favor, inicia sesión."
- Response JSON incluye:
  - `redirect_url: "/login/"` - Consistencia documental (frontend maneja desde allí)
  - `login_api_url: "/api/v1/landing/auth/login/"` - URL de la API de login para referencia
- ⚠️ **v2.30**: `redirect_url="/login/"` en 409 para consistencia documental (frontend maneja desde allí)

**Responsabilidades del Frontend (v2.30):**
- **Renderizar formularios**: El frontend debe crear y mostrar formularios HTML para activación y login
- **Manejar redirecciones**: El frontend debe procesar `redirect_url` de las respuestas JSON
- **Manejar estados de error**: El frontend debe mostrar mensajes apropiados para 400, 409, etc.
- **Consumir APIs REST**: El frontend debe hacer llamadas `fetch` o `axios` a los endpoints `/api/v1/landing/*`
- **NO esperar HTML del backend**: Django NO renderiza templates para landing/login/activación

**Reenvío de Token de Activación (v2.30):**
- Disponible desde la consola: `/console/tenants/` → botón "Reenviar Token"
- Endpoint: `POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/`
- El reenvío:
  - NO resetea la cuenta automáticamente
  - Solo funciona si el usuario NO tiene contraseña usable
  - Si el usuario ya tiene contraseña usable, retorna **409 Conflict**
- Para entornos DEV: existe opción "Reset + Reenviar" detrás del flag `ALLOW_RESET_ACTIVATION=True`
- Incluye rate limiting (1 intento cada 5 minutos por tenant+owner)
- Registra auditoría en `ConsoleActionLog`
- **Alineación API-First**: El email SIEMPRE apunta a `/api/v1/landing/auth/activate/?token=...` (no HTML)
- **URL siempre visible**: La respuesta incluye `activation_url` para que el operador pueda copiarla y probarla
- **Query param `?dry_run=true`**: Permite generar token sin enviar email (útil para QA)

#### ⚠️ IMPORTANTE v2.30 - Landing API-First (Sin Vistas HTML)

**⚠️ CRÍTICO: En v2.30 NO hay HTML en /activate, /login o /index. El backend solo devuelve JSON. El formulario es responsabilidad del FRONTEND.**

**⚠️ IMPORTANTE: `/api/v1/landing/` NO tiene índice. Acceder a `/api/v1/landing/` retornará 404. Se deben usar rutas específicas:**
- `GET /api/v1/landing/info/` - Información pública del tenant
- `POST /api/v1/landing/auth/login/` - Login
- `POST /api/v1/landing/auth/logout/` - Logout (API-First, retorna `redirect_url="/"`)
- `GET /api/v1/landing/auth/logout/` - Logout (compatibilidad GET, retorna `redirect_url="/"`)
- `GET /api/v1/landing/auth/activate/?token=...` - Validar token (API JSON)
- `POST /api/v1/landing/auth/activate/?token=...` - Procesar activación (API JSON)
- `POST /api/v1/landing/auth/password-reset/request/` - Solicitar reset de contraseña (v2.30)
- `GET /api/v1/landing/auth/password-reset/validate/?uidb64=...&token=...` - Validar token de reset (v2.30)
- `POST /api/v1/landing/auth/password-reset/confirm/` - Confirmar reset de contraseña (v2.30)

**Shells estáticos (v2.30):**
- ⚠️ **REGLA DE ORGANIZACIÓN**: Todos los archivos estáticos deben estar en la app de origen
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/`
  - Después de `collectstatic`, Django los copia a `staticfiles/tenant/landing/`
  - Se sirven desde `STATIC_URL/tenant/landing/` (WhiteNoise en desarrollo, Nginx en producción)
- `GET /activate/?token=...` - Shell HTML estático de activación
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/activate.html`
  - URL servida: `/static/tenant/landing/activate.html`
  - Consume `/api/v1/landing/auth/activate/` internamente
  - Estados: validando, formulario (200), ya activada (409), inválido (400)
  - CTAs: `/login/` y `/reset-password/`
- `GET /login/` - Shell HTML estático de login
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/login.html`
  - URL servida: `/static/tenant/landing/login.html`
  - Consume `POST /api/v1/landing/auth/login/` (con CSRF si hay sesión)
  - Redirige a `/dashboard/` en éxito (usando `redirect_url` de la respuesta JSON)
  - Soporta `?reason=already_activated` para mostrar mensajes
  - CTA: `/reset-password/`
- `GET /reset-password/` - Shell HTML estático para solicitar reset
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/reset-request.html`
  - URL servida: `/static/tenant/landing/reset-request.html`
  - Consume `POST /api/v1/landing/auth/password-reset/request/`
  - Respuesta siempre 200 (idempotente - evita enumeración de usuarios)
- `GET /reset-password/confirm/?uidb64=...&token=...` - Shell HTML estático para confirmar reset
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/reset-confirm.html`
  - URL servida: `/static/tenant/landing/reset-confirm.html`
  - Valida con `GET /api/v1/landing/auth/password-reset/validate/`
  - Confirma con `POST /api/v1/landing/auth/password-reset/confirm/`
  - ⚠️ **Opción A**: La API devuelve `redirect_url="/"` (página principal del tenant - landing)
  - El shell estático consume `redirect_url` de la respuesta JSON y redirige a `/` (landing con botón de login e información del servicio)
- **Servidos por**: WhiteNoise (desarrollo) o Nginx (producción)
- **Rutas Django**: `/activate/`, `/login/`, `/reset-password/`, `/reset-password/confirm/` redirigen a `STATIC_URL/tenant/landing/{filename}.html`
- **Query params preservados**: Los parámetros de query (ej: `?token=...`) se preservan en la redirección
- **CSRF**: Todos los POST incluyen `X-CSRFToken` si hay sesión (mismo origen)
- **Helper CSRF**: `apps/tenant/landing/static/tenant/landing/_csrf.js` (función `getCookie()`)

**Comportamiento del Endpoint de Activación:**

El endpoint `/api/v1/landing/auth/activate/?token=...` es **completamente API-first**:

1. **GET `/api/v1/landing/auth/activate/?token=...`**:
   - **200 OK**: Token válido, usuario sin contraseña usable
     - Response JSON: `{"user": {...}, "tenant": {...}, "token_valid": true}`
     - **Frontend debe**: Mostrar formulario de activación (password + confirmación)
   - **409 Conflict**: Usuario ya tiene contraseña usable
     - Response JSON: `{"detail": "Cuenta ya activada. Inicia sesión.", "redirect_url": "/login/", "login_api_url": "/api/v1/landing/auth/login/"}`
     - **Frontend debe**: Mostrar mensaje y redirigir a `/login/` o usar `login_api_url` para login programático
     - ⚠️ **v2.30**: `redirect_url="/login/"` para consistencia documental
     - **⚠️ NO es un error técnico** - es el comportamiento esperado cuando el usuario ya fue activado
   - **400 Bad Request**: Token inválido o expirado
     - Response JSON: `{"detail": "Token de activación inválido o expirado..."}`
     - **Frontend debe**: Mostrar error y opción de solicitar nuevo token

2. **POST `/api/v1/landing/auth/activate/?token=...`**:
   - **200 OK**: Activación exitosa
     - Response JSON: `{"detail": "...", "redirect_url": "http://{domain}/dashboard/", "user": {...}, "tenant": {...}}`
     - **Frontend debe**: Redirigir a `redirect_url` de la respuesta
   - **409 Conflict**: Usuario ya tiene contraseña usable
     - Response JSON: `{"detail": "Cuenta ya activada. Inicia sesión.", "redirect_url": "/login/", "login_api_url": "/api/v1/landing/auth/login/"}`
     - **Frontend debe**: Mostrar mensaje y redirigir a `/login/` o usar `login_api_url` para login programático
     - ⚠️ **v2.30**: `redirect_url="/login/"` para consistencia documental
   - **400 Bad Request**: Token inválido/expirado o datos inválidos
     - **Frontend debe**: Mostrar errores de validación

**⚠️ CRÍTICO:**
- Django **NO renderiza formularios HTML** para activación desde vistas Django
- Los endpoints `/api/v1/landing/auth/activate/` responden **SOLO JSON**
- **Shell estático disponible**: `/activate/?token=...` sirve un HTML estático que consume la API
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/activate.html`
  - URL servida: `/static/tenant/landing/activate.html`
  - Servido por: WhiteNoise (desarrollo) o Nginx (producción)
  - El shell HTML maneja toda la UI (formularios, mensajes, redirecciones)
  - Consume la API `/api/v1/landing/auth/activate/` internamente
- **URLs de activación**: Apuntan a `/activate/?token=...` (shell estático), no directamente a la API

**Alineación Consola ↔ Tenant Landing (v2.30):**
- **Consola (`apps/public/console/api`)**: Provee tokens de activación
  - Endpoint: `POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/`
  - Siempre construye URLs al shell estático: `{protocol}://{domain}/activate/?token=...`
  - Email siempre apunta al shell estático del tenant (que consume la API internamente)
  - Respuesta incluye `activation_url` para pruebas (siempre visible)
  - Query param `?dry_run=true` permite generar token sin enviar email
- **Tenant Landing (`apps/tenant/landing/api`)**: Consume tokens de activación
  - Endpoint: `GET/POST /api/v1/landing/auth/activate/?token=...`
  - GET: Valida token (200/409/400) sin consumirlo
  - POST: Consume token, establece password, retorna `redirect_url` absoluta
  - One-time use efectivo: una vez activado (`has_usable_password()==True`), retorna 409
- **Contrato unificado**: Ambos módulos usan el mismo servicio `apps/public/tenants/services/invitations.py`
  - `generate_invitation_token()`: Genera tokens firmados con TTL
  - `verify_invitation_token()`: Valida tokens (sin consumo explícito, pero efectivo por estado de usuario)
  - `build_activation_url()`: Construye URLs al shell estático `/activate/?token=...` (v2.30)
  - `send_invitation_email()`: Envía emails con URLs API-first

**Reglas de Onboarding (Reforzadas v2.29-v2.30):**

1. **Owner DEBE crearse con `set_unusable_password()`**:
   ```python
   user = User.objects.create(email=email, ...)
   user.set_unusable_password()  # ⚠️ CRÍTICO
   user.save()
   ```

2. **NO usar `set_password()` en onboarding**:
   - Si se usa `set_password()` → el usuario tendrá contraseña usable
   - La activación retornará **409 Conflict**
   - El owner NO podrá activar su cuenta

3. **NO usar `create_user()` con password**:
   - `User.objects.create_user(email, password=...)` → crea usuario con contraseña usable
   - Esto bloqueará la activación (409 Conflict)

4. **Serializer rechaza campos de password**:
   - `OnboardTenantWithOwnerSerializer` rechaza explícitamente: `password`, `password1`, `password2`, `owner_password`
   - Esto previene errores de configuración

#### Seed Opcional en Esquema del Tenant

**Utilidad oficial:** `schema_context(schema_name)` de `django_tenants.utils`

**Uso:**
```python
from django_tenants.utils import schema_context

with schema_context(client.schema_name):
    # Operaciones dentro del esquema del tenant
    obtener_o_crear_perfil(user=admin_user, ...)
```

**Propósito:** Crear datos iniciales "dentro del tenant" (ej: `TenantProfile`, branding, configuraciones).

#### Seguridad de Host

**⚠️ CRÍTICO - ALLOWED_HOSTS:**
- **Desarrollo (`DEBUG=True`):** Lista dinámica construida automáticamente (`.localhost`, `localhost`, `127.0.0.1`, `sintel.com`, `.sintel.com`)
- **Producción (`DEBUG=False`):** Lista explícita de dominios/subdominios (ej: `[".sintel.com", "sintel.com"]`)
- **⚠️ SEGURIDAD:** `ALLOWED_HOSTS = ["*"]` es SOLO para desarrollo local. En producción NUNCA usar comodín (riesgo de Host Header Attack)

**Configuración (v2.23):**
```python
# Desarrollo (DEBUG=True)
ALLOWED_HOSTS = [
    f".{TENANT_DOMAIN_BASE}",  # .sintel.com o .localhost
    TENANT_DOMAIN_BASE,  # sintel.com o localhost
    "localhost",
    ".localhost",  # Subdominios locales
    "127.0.0.1",
    # ⚠️ v2.23: Siempre incluir sintel.com y .sintel.com (incluso en desarrollo)
    # Esto permite pruebas locales con el dominio de producción
    "sintel.com",
    ".sintel.com",
]

# Producción (DEBUG=False) - ⚠️ NUNCA usar ["*"]
ALLOWED_HOSTS = [
    ".sintel.com",  # Subdominios (cliente.sintel.com)
    "sintel.com",   # Dominio principal
    # Agregar otros dominios explícitos si es necesario
]
```

**⚠️ ADVERTENCIA DE SEGURIDAD - Host Header Attack:**
- Usar `ALLOWED_HOSTS = ["*"]` en producción permite que atacantes envíen requests con headers `Host` arbitrarios
- Esto puede causar:
  - Cache poisoning
  - Password reset poisoning
  - Cross-site scripting (XSS) mediante subdominios maliciosos
- **Solución:** Siempre usar lista explícita de dominios permitidos en producción

**CSRF_TRUSTED_ORIGINS (v2.23):**
- **Desarrollo:** HTTP localhost y sintel.com (validación dinámica mediante `CSRFTrustedOriginMiddleware`)
- **Producción:** `https://sintel.com` + validación dinámica mediante `CSRFTrustedOriginMiddleware`
- ⚠️ **Nota**: Django no soporta wildcards en `CSRF_TRUSTED_ORIGINS`, por lo que el middleware valida dominios dinámicamente

**Configuración de Producción (v2.23):**
- Ver `documentacion/configuracion_produccion_https.md` para guía completa
- Scripts de verificación: `scripts/verify_production_config.py`, `scripts/add_sintel_domain.py`
- Ejemplo Nginx: `config/nginx/sintel.conf.example`

**⚠️ IMPORTANTE:** No usar `'*'` con `DEBUG=False` (riesgo de seguridad - Host Header Attack).

#### Tests de Garantía

**Ubicación:** `tests/public/tenants/test_tenant_domain_access.py`

**Casos cubiertos:**
1. **Routing por hostname:** `HTTP_HOST='miempresa.localhost'` → activa `TENANT_URLCONF`
2. **Dominio sin puerto:** Rechazar dominios con puerto en validadores
3. **Membresía obligatoria:** Usuario sin `TenantMembership` → login denegado
4. **Unicidad de dominio primario:** Solo un `is_primary=True` por tenant
5. **Unicidad global de dominio:** Un dominio no puede pertenecer a múltiples tenants
6. **Aislamiento:** Tenant accesible solo por su dominio

**Ejecución:**
```bash
docker compose exec web pytest tests/public/tenants/test_tenant_domain_access.py -v
```

#### Referencias

- [django-tenants Documentation](https://django-tenants.readthedocs.io/)
- [Django URL Configuration](https://docs.djangoproject.com/en/stable/topics/http/urls/)
- [Multi-tenant Routing](https://django-tenants.readthedocs.io/en/latest/use.html)

---

## 🐳 Infraestructura Docker

### Servicios

#### 1. `db` - PostgreSQL 16
```yaml
image: postgres:16
ports: 5432:5432
volumes: postgres_data
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
  interval: 5s
  timeout: 5s
  retries: 10
```

**Variables de Entorno:**
- `POSTGRES_DB`: sintel
- `POSTGRES_USER`: sintel
- `POSTGRES_PASSWORD`: sintel

#### 2. `redis` - Redis 7-alpine
```yaml
image: redis:7-alpine
ports: 6379:6379
```

**Uso:**
- Cola de tareas Celery
- Caché de sesiones
- Caché de datos

#### 3. `web` - Aplicación Django
```yaml
build: . (Dockerfile)
ports: 8000:8000
volumes: .:/app (montaje de código)
command: migrate + setup + runserver
```

**Dockerfile:**
- Base: `python:3.12-slim`
- Dependencias del sistema: `gcc`, `libpq-dev` (para psycopg)
- Instalación de requirements.txt
- Variables: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`

### Comandos de Inicio

#### Desarrollo (docker-compose.yaml en raíz)

El contenedor `web` ejecuta automáticamente el siguiente flujo seguro:

1. `makemigrations accounts || true` - Crea migraciones para accounts (si hay cambios)
2. `makemigrations || true` - Crea migraciones para todas las apps (si hay cambios)
3. `migrate_schemas --shared --fake-initial` - Aplica migraciones del esquema public
4. `check_migrations` - **Server Guard**: Verifica que no queden migraciones pendientes (bloquea si hay)
5. `runserver 0.0.0.0:8000` - Inicia el servidor (solo si todo está OK)

**Nota:** El `--fake-initial` permite aplicar migraciones iniciales sin errores si las tablas ya existen.

**Server Guard:** El comando `check_migrations` previene que el servidor arranque si hay migraciones pendientes, garantizando que la base de datos esté siempre sincronizada.

#### Producción (infra/compose/) ✅ Fase 10

Stack completo "prod-like" con Gunicorn, WhiteNoise, Celery, OpenSearch y Traefik opcional.

**Servicios del stack producción:**

1. **`app`**: Gunicorn + WhiteNoise (puerto 8000)
   - Dockerfile: `infra/docker/app/Dockerfile`
   - Configuración: `infra/docker/app/gunicorn.conf.py`
   - Entrypoint: `infra/scripts/entrypoint.sh` (migraciones + Gunicorn)
   - Healthcheck: `/health` endpoint

2. **`db`**: PostgreSQL 16 (igual que desarrollo)

3. **`redis`**: Redis 7-alpine (igual que desarrollo)

4. **`celery`**: Celery Worker (`celery -A config worker --loglevel=info --concurrency=4 -Q high_priority,default`)
   - Entrypoint específico: `entrypoint-celery.sh` (ejecuta migraciones y configuración antes del worker)
   - Colas prioritarias: `high_priority` para tareas críticas (ej: `onboard_tenant_task`)
   - Configuración en `CELERY_TASK_ROUTES` para enrutamiento explícito

5. **`beat`**: Celery Beat Scheduler (`celery -A config beat -l INFO`)

**⚠️ DOCUMENTACIÓN: Celery y Tareas Asíncronas por Entorno**

**Desarrollo:**
- **Modo eager:** `CELERY_TASK_ALWAYS_EAGER = True` (opcional, para debugging)
  - Las tareas se ejecutan sincrónicamente en el mismo proceso
  - Útil para desarrollo sin workers, pero NO recomendado para pruebas de concurrencia
- **Workers reales:** Ejecutar `celery -A config worker` manualmente si se requiere comportamiento asíncrono
- **Redis:** Requerido para broker de mensajes (desarrollo y producción)

**CI (Continuous Integration):**
- **Modo eager:** `CELERY_TASK_ALWAYS_EAGER = True` (recomendado)
  - Simplifica tests sin necesidad de Redis/workers
  - Las tareas se ejecutan sincrónicamente durante tests
- **Tests de tareas:** Ejecutar tests de tareas Celery con modo eager para validar lógica

**Producción:**
- **Workers reales:** Múltiples workers con `--concurrency` configurado según CPU
- **Colas prioritarias:** Separación de tareas críticas (`high_priority`) vs tareas normales (`default`)
- **Beat scheduler:** Ejecutar en contenedor separado para tareas periódicas
- **Monitoreo:** Configurar monitoreo de workers (healthchecks, logs, métricas)

**Configuración de Colas:**
```python
# config/celery.py
CELERY_TASK_ROUTES = {
    'apps.public.tenants.tasks.onboard_tenant_task': {'queue': 'high_priority'},
    # Otras tareas críticas → high_priority
    # Tareas normales → default (o sin especificar)
}
```

**⚠️ IMPORTANTE:**
- En desarrollo, el modo eager facilita debugging pero no refleja comportamiento real
- En producción, siempre usar workers reales con Redis como broker
- Las tareas deben ser idempotentes cuando sea posible (reintentos seguros)

6. **`opensearch`**: OpenSearch single-node (512MB heap, puertos 9200/9600)

7. **`traefik`**: Reverse proxy opcional (rutado por hostname para multi-tenant)

**Comandos:**

```bash
cd infra/compose
cp .env.example .env
# Editar .env (DEBUG=False, ALLOWED_HOSTS, SECRET_KEY, etc.)
docker compose -f docker-compose.yml --env-file .env up -d --build
docker compose -f docker-compose.yml logs -f app
curl http://localhost:8000/health
```

**Características:**
- Gunicorn con workers configurables (`(2 x CPU) + 1`)
- WhiteNoise para staticfiles (compresión + versionado)
- Migraciones automáticas en entrypoint
- Seed tenant opcional (variables `SEED_TENANT_*`)
- Tests en contenedor (`docker-compose.test.yml`)
- Makefile con targets (`make -C infra/compose up`)

**Referencias:**
- [Django + Gunicorn](https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/gunicorn/)
- [WhiteNoise](https://whitenoise.readthedocs.io/)
- [Docker Compose](https://docs.docker.com/compose/)

---

## 📁 Estructura de Directorios

```
sintel_project/
├── apps/
│   ├── public/                    # Aplicaciones compartidas (Esquema public)
│   │   ├── tenants/              # Gestión de clientes y dominios
│   │   │   ├── models.py         # Client, Domain
│   │   │   ├── admin.py         # Admin para Client y Domain
│   │   │   ├── api/              # API REST (API-first)
│   │   │   │   ├── serializers.py
│   │   │   │   ├── viewsets.py
│   │   │   │   └── urls.py
│   │   │   └── management/
│   │   │       └── commands/
│   │   │           ├── setup_public_tenant.py
│   │   │           └── check_migrations.py  # Server Guard
│   │   ├── accounts/             # Usuarios globales
│   │   │   ├── models.py        # User (AbstractUser)
│   │   │   ├── apps.py          # AppConfig con guardas para migraciones
│   │   │   ├── admin.py         # Admin personalizado
│   │   │   └── api/              # API REST (API-first)
│   │   │       ├── serializers.py
│   │   │       ├── viewsets.py
│   │   │       └── urls.py
│   │   ├── console/             # Consola de administración
│   │   │   ├── views.py         # Vistas HTML (dashboard, listas)
│   │   │   ├── urls.py          # URLs de la consola
│   │   │   ├── templates/       # Templates de la consola
│   │   │   └── static/          # CSS/JS de la consola
│   │   └── impuestos/           # Core Legal/DIAN + Ingesta + ETL
│   │       ├── models.py        # Catálogo DIAN + DocumentoFuente + NormaTributaria
│   │       ├── admin.py         # Admin para catálogo e ingesta
│   │       ├── api/              # API REST (API-first)
│   │       │   ├── serializers.py  # Catálogo (ReadOnly)
│   │       │   ├── viewsets.py     # Catálogo (ReadOnly)
│   │       │   ├── urls.py         # URLs del catálogo
│   │       │   └── ingesta/        # API de Ingesta (Capa A)
│   │       │       ├── serializers.py
│   │       │       ├── views.py
│   │       │       ├── urls.py
│   │       │       ├── permissions.py
│   │       │       └── throttling.py
│   │       ├── services/         # Servicios ETL (Capa B)
│   │       │   ├── robots.py     # Verificación robots.txt
│   │       │   └── etl/          # Pipeline ETL
│   │       │       ├── detectors.py
│   │       │       ├── parse_pdf.py
│   │       │       ├── parse_html.py
│   │       │       ├── parse_xml.py
│   │       │       ├── parse_excel.py
│   │       │       ├── parse_csv.py
│   │       │       ├── tokenizer.py
│   │       │       ├── normalizer.py
│   │       │       ├── validators.py
│   │       │       ├── upserts.py
│   │       │       └── pipeline.py
│   │       ├── tasks.py          # Tareas Celery (descargar_fuente, procesar_fuente)
│   │       ├── dashboard/        # Dashboard web (opcional, separado)
│   │       │   ├── views_dashboard.py
│   │       │   ├── urls_dashboard.py
│   │       │   └── templates/
│   │       ├── templates/        # Templates integrados en consola
│   │       │   └── console/pages/impuestos/
│   │       └── management/
│   │           └── commands/
│   │               └── poblar_catalogo_dian.py
│   ├── tenant/                   # Aplicaciones privadas (Esquema por empresa)
│   │   ├── empresa/              # Datos de la empresa
│   │   │   └── api/               # API REST (API-first)
│   │   │       ├── serializers.py
│   │   │       ├── viewsets.py
│   │   │       └── urls.py
│   │   ├── facturas/             # Core: Procesamiento XML
│   │   │   └── api/               # API REST (API-first)
│   │   │       ├── serializers.py
│   │   │       ├── viewsets.py
│   │   │       └── urls.py
│   │   └── contabilidad/        # Contabilidad
│   │       └── api/               # API REST (API-first)
│   │           ├── serializers.py
│   │           ├── viewsets.py
│   │           └── urls.py
│   ├── config/                   # Configuración compartida
│   │   └── api/                   # Módulo API compartido
│   │       ├── pagination.py      # StandardResultsSetPagination
│   │       ├── permissions.py     # Permisos base
│   │       └── exceptions.py      # Handler de excepciones
│   ├── services/                 # Lógica pura (Python packages) sin modelos
│   │   ├── maildigester/         # Procesamiento de correos
│   │   ├── xml_parser/           # Parser de XML de facturas (legacy, mantenido por compatibilidad)
│   │   ├── xml_ingest/           # Ingesta XML (legacy, mantenido por compatibilidad)
│   │   ├── document_parser/      # ⚠️ v2.36: Pipeline universal de parsing (XML, PDF, XLS, CSV, TXT)
│   │   │   ├── interfaces.py     # IParser, IDetector, INormalizer
│   │   │   ├── dto.py            # DTO unificado JSON
│   │   │   ├── normalizers.py    # Normalización UTF-8, limpieza
│   │   │   └── parsers/          # Parsers específicos (XML, PDF, Excel, CSV, TXT)
│   │   └── document_ingest/      # ⚠️ v2.36: Orquestación, routing, validación
│   │       ├── registry.py       # DocumentRegistry (Strategy Pattern)
│   │       ├── ingest_service.py # Servicio principal de ingesta
│   │       └── validators.py     # Validación de integridad DTO
│   └── documentacion/            # Documentación del proyecto (ÚNICA UBICACIÓN - documentacion/)
│       └── arquitectura_general.md  # Este documento
├── config/                       # Configuración de Django
│   ├── settings.py               # Configuración principal
│   ├── urls_public.py            # URLs para esquema público (ROOT_URLCONF)
│   ├── urls_tenant.py           # URLs para tenants privados (TENANT_URLCONF)
│   ├── api_urls.py              # Router para APIs por tenant
│   ├── public_api_urls.py       # Router para APIs públicas
│   ├── wsgi.py                  # WSGI application
│   └── asgi.py                  # ASGI application
├── manage.py                     # Django management script
├── requirements.txt              # Dependencias Python
├── docker-compose.yaml           # Orquestación de servicios
├── Dockerfile                    # Imagen de la aplicación
├── .env.sample                   # Variables de entorno de ejemplo
├── .env                          # Variables de entorno (no versionado)
├── .gitignore                    # Archivos ignorados por Git
├── Makefile                      # Comandos de conveniencia
└── README.md                     # Documentación básica
```

**⚠️ REGLA DE ORGANIZACIÓN DE ARCHIVOS (v2.30+):**

**ARCHIVOS ESTÁTICOS:**
- **Todos los archivos estáticos deben estar en la app de origen**
- **Estructura requerida**: `apps/{app}/static/{namespace}/{subdirectory}/`
  - Ejemplo: `apps/tenant/landing/static/tenant/landing/`
  - Ejemplo: `apps/tenant/dashboard/static/tenant/dashboard/`
- **Después de `collectstatic`**: Django copia los archivos a `staticfiles/{namespace}/{subdirectory}/`
- **URL servida**: `/static/{namespace}/{subdirectory}/{filename}` (mediante WhiteNoise/Nginx)
- **NO usar directorio raíz `static/`**: Todos los archivos estáticos deben estar dentro de su app correspondiente
- **Esta regla aplica a todas las apps**: `apps/public/*`, `apps/tenant/*`, etc.

**TEMPLATES:**
- **Templates namespaced por app**: `apps/{app}/templates/{namespace}/{app}/`
  - Ejemplo: `apps/tenant/core/templates/tenant/base.html`
  - Ejemplo: `apps/tenant/core/templates/tenant/partials/_header.html`
  - Ejemplo: `apps/public/console/templates/console/base.html`
- **Template base por ámbito**: 
  - Tenant: `apps/tenant/core/templates/tenant/base.html`
  - Consola pública: `apps/public/console/templates/console/base.html`
- **Partials reutilizables**: `apps/{app}/templates/{namespace}/partials/_*.html`
  - Usar `{% include 'tenant/partials/_header.html' %}` en templates
- **App Directories Loader**: Django busca automáticamente en `templates/` de cada app (APP_DIRS=True)

---

## 📦 Aplicaciones y Módulos

### Arquitectura de Aplicaciones

El proyecto sigue una separación clara entre:
- **Apps Públicas (SHARED_APPS)**: En el esquema `public`, compartidas por todos los tenants
- **Apps de Tenant (TENANT_APPS)**: En esquemas individuales, específicas de cada empresa
- **Servicios (apps/services)**: Lógica pura sin modelos, siguiendo Service Layer Pattern

### Apps Públicas (SHARED_APPS)

#### 1. `apps.public.tenants` ✅ CRUD + Onboarding IMPLEMENTADO
**Función:** Gestión de tenants y dominios (Núcleo Multitenant Funcional)

**Modelos (Conforme a documentación oficial de django-tenants):**

**Client (TenantMixin):**
```python
class Client(TenantMixin):
    auto_create_schema = True  # ✅ CRÍTICO: Crea esquema automáticamente
    auto_drop_schema = False
    nombre = models.CharField(max_length=100)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Desactiva para suspender el servicio. El tenant no recibirá tráfico."
    )
```
- ✅ `auto_create_schema = True`: Crea esquema automáticamente al crear un Client
- ✅ Conforme a instalación oficial de django-tenants
- ✅ Al crear un Client, django-tenants crea automáticamente el esquema PostgreSQL
- ✅ La señal `post_save` en `Client` crea automáticamente el dominio principal basado en `schema_name`
  - Si `schema_name` contiene punto (FQDN), se usa como dominio
  - Si no contiene punto, se construye como `{schema_name}.{TENANT_DOMAIN_BASE}`
- ✅ Si se proporciona un dominio explícito en el formulario de creación, se actualiza el dominio creado automáticamente
- ✅ **Campo `is_active`** (v2.11): Control de suspensión de servicio
  - `default=True`: Todos los tenants nuevos están activos por defecto
  - Si `is_active=False`: El middleware bloquea todo el acceso (403 Forbidden)
  - **Excepción crítica**: El tenant público (`schema_name='public'`) NUNCA puede ser suspendido
- ✅ **Modelo `TenantMembership`** (Fase 9): Relación User ↔ Client con roles (ADMIN, STAFF, USER)
- ✅ **API Admin** (`/api/admin/v1/tenants/`): CRUD completo + endpoint `onboard` + `toggle-status`
- ✅ **Consola DataTables** (`/console/tenants/`): Lista server-side con acciones Editar/Borrar/Acceder/Pausar-Reanudar

**Domain (DomainMixin):**
```python
class Domain(DomainMixin):
    pass  # ✅ Conforme a documentación oficial
```
- ✅ Campos heredados de `DomainMixin`: `domain`, `tenant`, `is_primary`
- ✅ Conforme a instalación oficial de django-tenants

**Comandos:**
- `setup_public_tenant`: Crea el tenant público inicial (conforme a guía oficial)
  - Crea tenant "public" con `schema_name='public'`
  - Crea dominio principal (default: 'localhost')
  - Crea dominios adicionales para desarrollo
- `check_migrations`: **Server Guard** - Verifica que no haya migraciones pendientes
- `fix_migration_history`: Corrige historial de migraciones inconsistente

**Migración Inicial del Esquema Público:**
- ✅ Comando: `python manage.py migrate_schemas --shared`
- ✅ Instala SOLO las apps de `SHARED_APPS` en el esquema `public`
- ✅ Integrado en `entrypoint.sh` (ejecución automática)

#### 2. `apps.public.accounts` ✅ CRUD ROBUSTO IMPLEMENTADO
**Función:** Usuarios globales del sistema

**Modelos:**
- `User` (AbstractUser): Usuario personalizado
  - Email único y obligatorio
  - Generación automática de username desde email (si el modelo lo tiene)
  - Campo adicional: `telefono`

**Service Layer (`apps/public/accounts/api/services/user_service.py`):**
- `create_user_service()`: Crea usuarios con hashing seguro de contraseñas
  - ⚠️ **v2.23**: Genera username único automáticamente si el modelo tiene campo `username`
  - ⚠️ **v2.23**: Validación adicional para evitar username vacío (fallback a "user" con sufijo)
  - Usa `set_password()` para hashing seguro (nunca texto plano)
  - Maneja `IntegrityError` para emails/username duplicados
  - Transaccional: `@transaction.atomic`
- `update_user_service()`: Actualiza usuarios con validación de contraseñas
  - Actualización parcial de campos
  - Hashing seguro si se proporciona nueva contraseña

**UserManager (`apps/public/accounts/managers.py` - v2.23):**
- `_create_user()`: Genera username desde email con validación robusta
  - Si el local-part del email está vacío → usa "user" como base
  - Si el username generado está vacío → usa "user" con sufijo incremental
  - Evita colisiones con sufijos incrementales (`-1`, `-2`, etc.)
  - Garantiza que username nunca esté vacío

**APIs REST (`apps/public/accounts/api/`):**
- **ViewSet:** `UserAdminViewSet` (solo staff - `IsAdminUser`)
  - `GET /api/admin/v1/accounts/users/`: Lista paginada de usuarios
  - `POST /api/admin/v1/accounts/users/`: Crear usuario (requiere `password` + `password2`)
  - `GET /api/admin/v1/accounts/users/{id}/`: Detalle de usuario
  - `PATCH /api/admin/v1/accounts/users/{id}/`: Actualizar usuario parcialmente
  - `DELETE /api/admin/v1/accounts/users/{id}/`: Eliminar usuario
  - `GET /api/admin/v1/accounts/users/me/`: Perfil del usuario autenticado
- **Serializers:**
  - `UserListSerializer`: Solo lectura, campos mínimos (sin password)
  - `UserCreateSerializer`: Creación con validación de `password` y `password2` (deben coincidir)
  - `UserUpdateSerializer`: Actualización parcial con password opcional
- **Autenticación:** `SessionAuthentication` para permitir cookies de sesión desde la UI

**Consola UI (`/console/users/`):**
- **Template:** `apps/public/console/templates/console/pages/users/list.html`
  - DataTables server-side con POST + CSRF
  - Modal moderno para crear/editar usuarios
  - Campo `password2` (confirmar contraseña) integrado
  - Validación JavaScript: verifica que contraseñas coincidan antes de enviar
  - Mensajes de error específicos por campo
- **JavaScript:** `apps/public/console/static/js/users_manager.js`
  - Inicialización de DataTables con autenticación de sesión
  - Validación de formulario (password + password2)
  - Manejo de errores de API con feedback visual

**Características:**
- `AUTH_USER_MODEL = "accounts.User"` (usuarios globales)
- Username se genera automáticamente desde email si el modelo lo tiene
- ⚠️ **v2.23**: Si el username existe, se agrega un sufijo incremental (`-1`, `-2`, etc.)
- ⚠️ **v2.23**: Validación adicional garantiza que username nunca esté vacío
- **Política de usuarios:** Usuarios globales compartidos entre todos los tenants
- **Seguridad:**
  - Password siempre hasheado con `set_password()` (nunca texto plano)
  - Password `write_only` en serializers (nunca se expone en respuestas)
  - Validación de contraseñas coincidentes en múltiples capas (HTML5, JavaScript, Serializer)
  - Manejo robusto de errores (`IntegrityError` para duplicados)

**Scripts de Mantenimiento (v2.23):**
- `sanitize_empty_usernames`: Comando de management para corregir usuarios existentes con username=''
  - Genera username único desde email
  - Soporta `--dry-run` para ver qué se corregiría sin hacer cambios
  - Transaccional: todos los cambios en una sola transacción

**AppConfig con Guardas:**
- `apps.py` implementa guardas en `ready()` para evitar consultas a DB durante comandos de mantenimiento
- Protege contra consultas en import-time cuando hay migraciones pendientes
- Comandos protegidos: `migrate`, `migrate_schemas`, `makemigrations`, `collectstatic`, `shell`, `check`, `test`

#### 3. `apps.public.impuestos` ✅ IMPLEMENTADO COMPLETO
**Función:** Catálogo legal de la DIAN (Colombia) + Sistema de Ingesta y ETL

**Modelos del Catálogo:**
- `TipoImpuesto`: Tipos de impuestos (IVA, Retención, ICA, Renta)
- `TarifaIVA`: Tarifas de IVA (19%, Excluido, Exento, Reducido)
- `ConceptoRetencion`: Conceptos de retención (ICA, IVA, Renta)
- `CodigoTributario`: Códigos tributarios (Responsabilidades, Régimenes)
- `ActividadEconomica`: Actividades económicas (CIIU)

**Modelos de Ingesta (Capa A):**
- `DocumentoFuente`: Documento fuente para ingesta (archivo/URL)
  - Campos: `archivo`, `url_origen`, `fuente`, `tipo`, `estado`
  - Metadatos: `content_type`, `extension`, `size_bytes`, `hash_sha256`
  - Cumplimiento: `user_agent`, `robots_observado`, `crawl_delay_s`
- `IngestaLog`: Logs de procesamiento (descarga, parseo, normalización)
- `NormaTributaria`: Normas tokenizadas extraídas de documentos (Fase B)

**APIs REST:**
- **Catálogo (ReadOnly):**
  - `GET /api/v1/impuestos/tipos/`: Listar tipos de impuesto
  - `GET /api/v1/impuestos/tarifas-iva/`: Listar tarifas IVA
  - `GET /api/v1/impuestos/conceptos-retencion/`: Listar conceptos de retención
  - `GET /api/v1/impuestos/codigos-tributarios/`: Listar códigos tributarios
  - `GET /api/v1/impuestos/actividades-economicas/`: Listar actividades económicas

- **Ingesta (Capa A):**
  - `POST /api/public/v1/impuestos/ingesta/`: Crear documento fuente (archivo/URL)
  - `GET /api/public/v1/impuestos/ingesta/`: Listar documentos
  - `GET /api/public/v1/impuestos/ingesta/{id}/`: Detalle con logs
  - Throttling: `impuestos_ingesta` (20/hour)
  - Parsers: `MultiPartParser` (archivos), `JSONParser` (URLs)

**Servicios ETL (Capa B):**
- **Estructura:** `apps/public/impuestos/services/etl/`
  - `detectors.py`: Detección de tipo por extensión/MIME
  - `parse_pdf.py`: Parser PDF (pdfminer.six)
  - `parse_html.py`: Parser HTML (lxml + BeautifulSoup opcional)
  - `parse_xml.py`: Parser XML (lxml.etree)
  - `parse_excel.py`: Parser Excel (pandas + openpyxl)
  - `parse_csv.py`: Parser CSV (pandas)
  - `tokenizer.py`: Tokenización (Artículo/Impuesto/Tema/Vigencia)
  - `normalizer.py`: Normalización a entidades canónicas
  - `validators.py`: Validaciones de negocio (porcentajes, códigos, solapes)
  - `upserts.py`: Upserts atómicos con `transaction.atomic()`
  - `pipeline.py`: Orquestación completa (parse → tokenize → normalize → validate → upsert)

**Servicios de Crawling:**
- `services/robots.py`: Verificación de robots.txt antes de descargar URLs

**Tareas Celery:**
- `descargar_fuente`: Descarga desde URL respetando robots.txt
- `procesar_fuente`: Ejecuta pipeline ETL completo

**Dashboard Web (Consola):**
- **Ubicación:** Integrado en `/console/impuestos/ingesta/`
- **Vistas:**
  - `impuestos_ingesta_list`: Listado con filtros y auto-refresh HTMX
  - `impuestos_ingesta_create`: Crear ingesta (archivo/URL)
  - `impuestos_ingesta_detail`: Detalle con logs en tiempo real
- **Fragmentos HTMX:** Auto-refresh de filas y polling de logs
- **Templates:** `templates/console/pages/impuestos/`

**Comandos:**
- `poblar_catalogo_dian`: Pobla el catálogo con datos iniciales

**Dependencias ETL:**
- `pdfminer.six>=20221105`: Parser PDF
- `lxml>=5.0,<6.0`: Parser HTML/XML
- `pandas>=2.0,<3.0`: Parser Excel/CSV
- `openpyxl>=3.1,<4.0`: Engine para pandas.read_excel
- `beautifulsoup4>=4.12,<5.0`: Fallback para HTML malformado

**Características:**
- ✅ Captura por archivo (PDF/XLSX/CSV/HTML) o URL
- ✅ Validación de tipos y tamaño (máx 50MB)
- ✅ Detección automática de tipo por extensión/MIME
- ✅ Descarga respetando robots.txt y crawl_delay
- ✅ Pipeline ETL completo con soporte multi-formato
- ✅ Upserts atómicos garantizando consistencia
- ✅ Dashboard integrado en consola con HTMX
- ✅ Logs detallados de todas las etapas

### Apps de Tenant (TENANT_APPS) - Estructura Final Consolidada

**Ubicación:** Esquema específico de cada tenant (`tenant_<schema_name>`)

Estas aplicaciones residen en el esquema específico de cada tenant y contienen los datos de negocio de cada empresa. Cada tenant tiene su propio esquema con estas apps.

#### 1. `apps.tenant.empresa` ✅ IMPLEMENTADO - **ÚNICA FUENTE DE VERDAD (SSoT)**

**Función:** Datos de la empresa (por tenant)
- Información fiscal y tributaria de la empresa
- Configuración específica del tenant
- Datos de contacto y ubicación

**⚠️ POLÍTICA SSoT (Single Source of Truth):**
- `apps/tenant/empresa/api` es la **ÚNICA fuente de verdad** para datos empresariales
- Todas las TENANT_APPS deben consumir datos empresariales desde:
  - **API REST**: `GET /api/v1/empresas/` o `GET /api/v1/core/mi-empresa/`
  - **Servicio Python**: `apps.tenant.empresa.services.get_empresa_data()`
- **NO duplicar** campos empresariales (razon_social, nit, email, telefono, logo) en otras apps
- **Patrón Singleton**: Solo una empresa por tenant (garantizado por `UniqueConstraint` en DB)

**Estado:** ✅ Implementado con modelos, serializers, viewsets, admin y frontend Tabulator Factory v2.40
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propios datos de empresa

**Modelos:**
- `Empresa`: Datos fiscales y de configuración de la empresa
  - **Singleton por tenant**: `UniqueConstraint` en `singleton_key` garantiza una sola empresa por esquema
  - Campos canónicos: `razon_social`, `nit`, `dv`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `logo`, `website`, `moneda`

- `MailInboxConfig`: Configuración de buzones de correo para ingesta de facturas
  - **SSoT**: Única fuente de verdad para credenciales de correo
  - Campos IMAP/SMTP: `imap_host`, `imap_port`, `imap_username`, `imap_password`, `smtp_host`, `smtp_port`
  - Campos legacy mantenidos para compatibilidad (deprecados)
  - Seguridad: Passwords nunca expuestos en serializers, cifrado automático

**APIs REST - Empresa:**
- `GET /api/v1/empresas/`: Listar empresa (retorna formato paginado `{count, results}` para Tabulator)
  - Soporte `?search=` para búsqueda en tiempo real
  - Paginación: `StandardResultsSetPagination`
- `POST /api/v1/empresas/`: Crear empresa (retorna 409 si ya existe)
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN (no-staff recibe 405)
- `GET /api/v1/empresas/{id}/`: Obtener empresa
- `PATCH /api/v1/empresas/{id}/`: Actualizar empresa
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN (no-staff recibe 405)
- `PUT /api/v1/empresas/{id}/`: Actualizar empresa (completo)
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN (no-staff recibe 405)
- `DELETE /api/v1/empresas/{id}/`: Eliminar empresa
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN
- `GET /api/v1/empresas/mi-empresa/`: Obtener empresa del tenant (acción personalizada)

**APIs REST - MailInboxConfig:**
- `GET /api/v1/empresas/mail-inbox-config/`: Listar configuraciones (formato paginado `{count, results}`)
  - Soporte `?search=` para búsqueda en tiempo real
  - Filtros opcionales: `?is_active=true/false`, `?provider=gmail/custom`
  - Paginación: `StandardResultsSetPagination`
- `GET /api/v1/empresas/mail-inbox-config/{id}/`: Obtener configuración (sin passwords)
- `POST /api/v1/empresas/mail-inbox-config/`: Crear configuración
  - ⚠️ DEPRECATED v2.40: Retorna 405, usar `PATCH /api/v1/core/empresa/` con `mail_inbox_config`
- `PUT /api/v1/empresas/mail-inbox-config/{id}/`: Actualizar configuración
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN (no-staff recibe 405)
- `PATCH /api/v1/empresas/mail-inbox-config/{id}/`: Actualizar configuración parcial
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN (no-staff recibe 405)
- `DELETE /api/v1/empresas/mail-inbox-config/{id}/`: Eliminar configuración
  - ⚠️ ENFORCED MODE: Solo STAFF/ADMIN (no-staff recibe 405)
- `POST /api/v1/empresas/mail-inbox-config/test-connection/`: Probar conexión IMAP/SMTP
  - No persiste datos, solo prueba conexión
  - Password nunca se expone en respuesta ni logs

**Servicio Provider (Consumo Interno):**
- **Ubicación**: `apps/tenant/empresa/services.py`
- **Funciones**:
  - `qs_list(search=None)`: QuerySet optimizado para listado con soporte `?search=` (Tabulator v2.40)
  - `qs_detail()`: QuerySet optimizado para detalle
  - `get_empresa_data()`: Obtiene datos completos de la empresa del tenant actual
  - `get_empresa_emisor_data()`: Obtiene datos del emisor para facturas
  - `get_mailbox_config(config_id)`: Obtiene configuración de buzón de correo (SSoT para maildigester)
- **Uso**: Otras TENANT_APPS deben usar este servicio en lugar de consultas ORM directas
- **Ventajas**: Sin latencia HTTP, lógica centralizada, fácil de testear
- **⚠️ v2.40**: `qs_list()` acepta parámetro `search` para filtrado en tiempo real

**Contrato Canónico (DTO):**
- `EmpresaListSerializer`: Serializer optimizado para listado Tabulator v2.40
  - Campos mínimos: `id`, `razon_social`, `nit`, `dv`, `direccion`, `telefono`, `email_contacto`
- `EmpresaDetailSerializer`: Serializer para detalle con campos extendidos
- `EmpresaUpsertSerializer`: Serializer para crear/actualizar
- `MailInboxConfigListSerializer`: Serializer para listado (campos operativos, sin passwords)
- `MailInboxConfigDetailSerializer`: Serializer para detalle (campos extendidos, sin passwords)

**Frontend Tabulator Factory v2.40:**
- **Ubicación**: `apps/tenant/core/static/core/js/empresa/empresa.page.js`
- **Características**:
  - Tabla singleton (0-1 registros) con Tabulator Factory
  - Búsqueda en tiempo real con `?search=`
  - Botones condicionales: Crear (si no existe) / Editar (si existe)
  - Lazy loading con `DOMUtils.onVisibleOnce()`
  - Integración con modales existentes
- **Orden de carga de scripts** (`assets_empresa.html`):
  1. `empresa.api.js` (define `window.empresaAPI`)
  2. `empresa.modals.js` (define `window.empresaModals`, depende de `empresaAPI`)
  3. `empresa.page.js` (depende de `empresaModals` y `TabulatorFactory`)
  4. `mailinbox.page.js` (módulo independiente)

**Frontend MailInboxConfig Tabulator Factory v2.40:**
- **Ubicación**: `apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js`
- **Características**:
  - Tabla con paginación remota y búsqueda en tiempo real
  - Columnas: Nombre, Email, Proveedor (badge), Host IMAP, Puerto IMAP, SSL (badge), Activa (badge), Estado (badge), Última Sinc.
  - Acciones: Editar, Probar Conexión, Eliminar
  - Funcionalidad completa de CRUD con validaciones
  - Test de conexión sin persistir datos
  - Lazy loading con `DOMUtils.onVisibleOnce()`
- **Templates**:
  - `mailinbox_list.html`: Contenedor Tabulator con input de búsqueda
  - `mailinbox_modals.html`: Modal de crear/editar con formulario completo

**Auditorías y Pruebas:**
- Script de auditoría: `scripts/audit_empresa_duplication.py` (detecta duplicación de campos)
- Pruebas de humo: `tests/tenant/empresa/test_empresa_ssoT.py` (verifica SSoT)
- **Limpieza Zero-Legacy v2.40**:
  - Eliminado: `apps/tenant/empresa/static/` (directorio legacy)
  - Eliminado: Métodos `datatables()` de ViewSets (deprecados)
  - Actualizado: Comentarios y documentación a Tabulator Factory

#### 2. `apps.tenant.facturas` ✅ IMPLEMENTADO (API-First v2.30)

**Función:** Procesamiento de facturas electrónicas XML (API-First, DRF JSON-only)
- Recepción y procesamiento de facturas XML UBL 2.1 (DIAN)
- Validación de documentos electrónicos
- Almacenamiento de facturas recibidas y emitidas
- Service Layer Pattern: Toda la lógica de negocio en `services.py` y `ubl_parser.py`
- SSoT: Usa `apps.tenant.empresa.services.get_empresa_emisor_data()` para datos del emisor

**⚠️ POLÍTICA SSoT:**
- Los campos `emisor_nit` y `emisor_razon_social` son **datos históricos** (snapshot al momento de emisión)
- Deben poblarse automáticamente desde `apps.tenant.empresa.services.get_empresa_emisor_data()` al crear la factura
- **NO duplican** la lógica de Empresa; son snapshots para mantener integridad histórica

**⚠️ REGLA SSoT – PROCESAMIENTO DE DOCUMENTOS (v2.37 - REFACTOR CRUD ISOLATION):**
- **ÚNICA vía de ingesta/parseo**: `apps/services/document_parser` + `apps/services/document_ingest`
  - `document_parser`: Parsing low-level genérico (XML, PDF, XLS/XLSX, CSV, TXT)
    - `detector.py`: Detección de tipo por magic bytes, MIME type, extensión y heurísticas
    - `normalizers.py`: UTF-8, limpieza de binarios, saneamiento de texto, normalización numérica
    - `dto.py`: DTO unificado JSON (`DocumentoDTO`) con soporte para múltiples tipos de documentos
    - Parsers específicos: `xml_parser/`, `pdf_parser/`, `excel_parser/`, `csv_parser/`, `txt_parser/`
    - Cada parser implementa `parse_to_dto(file_bytes) -> dict(JSON)` con DTO unificado
  - `document_ingest`: ⚠️ **SOLO ORQUESTACIÓN Y PARSING, NO PERSISTE**
    - `router.py`: Routing dinámico de documentos según tipo detectado
    - `ingest_service.py`: Servicio principal `ingest_document()` - **SIEMPRE devuelve DTO sin persistir**
    - `validations/`: Sistema de validadores plug-in por tipo de documento
      - `base.py`: `BaseValidator` (interfaz abstracta)
      - `router.py`: Router de validaciones por tipo (`run_validations(dto_json)`)
      - Validadores específicos: `factura.py`, `nota_credito.py`, `gasto.py`, `inventario.py`
- **⚠️ REFACTOR v2.37: AISLAMIENTO COMPLETO DE CRUD**
  - **`document_ingest` SOLO parsea**: NO crea, modifica ni borra registros de ninguna app
  - **NO llama a servicios CRUD**: NO invoca el router de dominio para materializar
  - **Flujo separado**: `document_parser` → `document_ingest` → **DTO** → **App endpoint** → **Persistencia**
  - **Endpoints de app**: Cada app tiene su propio endpoint para persistir desde DTO:
    - `POST /api/v1/facturas/create-from-dto/`: Recibe DTO y persiste usando `guardar_factura_desde_dto()`
    - `POST /api/v1/gastos/create-from-dto/`: Recibe DTO y persiste usando `materializar_gasto_desde_dto()`
    - `POST /api/v1/inventario/create-from-dto/`: Recibe DTO y persiste usando `materializar_inventario_desde_dto()`
  - **CRUD independiente**: Cada app mantiene su CRUD manual y CRUD asistido por documento
  - **Prohibido**: Parseo/ingesta de documentos fuera de `apps/services/document_*`
  - **Prohibido**: Parseo/ingesta en `apps/tenant/*` (solo materialización desde DTO)
  - **Prohibido**: Persistencia automática desde `document_ingest` o `document_router`
- **Backward Compatibility (v2.34)**: `apps/services/xml_ingest` y `apps/services/xml_parser` siguen funcionando
  - Migración gradual: Parsers XML se migrarán a nueva estructura en fases siguientes
- **Artefactos pesados**: Solo en endpoints dedicados `/xml/` (no en list/detail)
- **Datos empresariales**: Siempre desde `apps.tenant.empresa.services.*` (SSoT)
- **Auditorías**: `scripts/audit_no_duplication.py` detecta violaciones
- **Tests**: Suite completa de tests unitarios en `tests/services/`, `tests/tenant/`, `tests/api/`, `tests/multitenant/`

**⚠️ REGLAS DE NEGOCIO - INMUTABILIDAD ESTRICTA:**
- **Las facturas son documentos históricos importados desde sistemas externos**
- **NUNCA se pueden editar, actualizar o modificar** (PUT/PATCH bloqueados → 405 Method Not Allowed)
- **Solo se pueden eliminar para corregir un error de carga** (rollback técnico)
- **Las correcciones fiscales se realizan mediante Notas Crédito/Débito** (no editando facturas)
- **POST manual está bloqueado** → 405 Method Not Allowed (solo se permite importación UBL)

**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios y UI en workspace
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propias facturas (aislamiento por esquema)

**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/facturas/services.py` - Lógica CRUD e importación UBL
  - `importar_ubl_sync()`: Procesamiento síncrono (consume `apps/services/document_ingest`)
  - `importar_ubl_async()`: Procesamiento asíncrono (consume `apps/services/document_ingest`, tenant-aware)
  - `consultar_tarea()`: Consulta estado de tareas (consume `apps/services/document_ingest.task_status`)
  - `guardar_factura_desde_dto()`: Materializa desde DTO (valida campos obligatorios, idempotencia por CUFE)
  - `guardar_nota_credito_desde_dto()`: Materializa nota crédito desde DTO (idempotencia por CUDE)
  - ⚠️ **REFACTOR v2.37**: Estas funciones son llamadas desde endpoints de la app, NO desde `document_ingest`
- **Parser UBL:** `apps/tenant/facturas/ubl_parser.py` - Mapeo UBL→DTO (dominio específico)
  - Consume `apps/services/xml_parser` para parsing low-level
  - Soporta `AttachedDocument` con `Invoice` interno (CDATA/base64)
  - Manejo robusto de namespaces dinámicos con `local-name()`
  - Extracción de prefijo/consecutivo con regex `^([A-Z]+)(\d+)$`
- **Servicios Canónicos (SSoT XML):**
  - `apps/services/xml_parser`: Parsing low-level genérico (reutilizable, sin lógica de negocio)
  - `apps/services/xml_ingest`: Orquestación sync/async, detección de tipos, tenant-aware
- **ViewSets DRF:** `apps/tenant/facturas/api/viewsets.py` - Solo orquestan servicios (sin lógica de negocio)
  - Hereda de `mixins.ListModelMixin`, `mixins.RetrieveModelMixin`, `mixins.DestroyModelMixin`, `viewsets.GenericViewSet`
  - `http_method_names = ['get', 'head', 'options', 'post', 'delete']` (bloquea PUT/PATCH)
  - `upload_ubl`: Logging estructurado con `request_id`, `schema_name`, `size`, `async`
  - `ingest_status`: Nunca retorna 500, siempre 200 con JSON estructurado
- **Permisos:** `IsTenantAdminOrReadOnly` - Lectura autenticados, escritura solo ADMIN/STAFF (TenantMembership)
- **UI:** Consumo desde `apps/tenant/core/templates/tenant/core/workspace.html` (Session + CSRF)
- **Norma de Exposición de Datos:** Cumple con reglas de mínima exposición (List vs Detail, `only()`, paginación)

**Modelos:**
- `Factura`: Factura electrónica con datos completos
  - `numero`: CharField(max_length=50, unique=True) - Número de factura único por tenant
  - `prefijo`, `consecutivo`: Extraídos del número con regex
  - `emisor_nit`, `emisor_razon_social`: Datos históricos del emisor (snapshot)
  - `receptor_nit`, `receptor_razon_social`: Datos del receptor
  - `cufe`: CharField(max_length=128) - CUFE/CUDE de DIAN
  - `qr_code`: TextField - QR Code completo (multilínea)
  - `qr_url`: URLField(max_length=1024) - URL del QR DIAN
  - `xml_content`: TextField - XML UBL completo (read-only, expuesto en endpoint dedicado)
- `ItemFactura`: Items de una factura (totales calculados automáticamente)

**APIs REST (TENANT_URLCONF):**
- `GET /api/v1/facturas/`: Listar facturas (paginado, filtros y búsqueda)
  - **Filtros**: `naturaleza`, `nit`, `fecha_emision__date__gte`, `fecha_emision__date__lte`
  - **Búsqueda**: `search` (busca en `numero`, `cufe`, `receptor_razon_social`, `emisor_razon_social`)
  - **Paginación**: `page`, `page_size` (default: 10)
  - **Ordenamiento**: `ordering` (default: `-fecha_emision`)
  - Serializer: `FacturaListSerializer` (campos mínimos: id, numero, naturaleza, estado, fecha_emision, moneda, subtotal, impuestos, total, emisor_nit, emisor_razon_social, receptor_nit, receptor_razon_social, cufe, qr_url, has_nc, nota_credito_id)
  - **has_nc**: SerializerMethodField que retorna `hasattr(obj, 'nota_credito') and obj.nota_credito is not None`
  - **nota_credito_id**: SerializerMethodField que retorna ID de NC si existe
  - QuerySet optimizado con `select_related("nota_credito")` y `only()` para reducir columnas
  - **NO incluye** `xml_content` ni datos pesados
- `GET /api/v1/facturas/{id}/`: Obtener detalle de factura (read-only)
  - Serializer: `FacturaDetailSerializer` (campos ampliados, sin `xml_content` ni `items` nested)
- `GET /api/v1/facturas/{id}/xml/`: Obtener XML de factura (endpoint dedicado para datos pesados)
  - Retorna: `{"xml": "<Invoice>...</Invoice>"}`
- `POST /api/v1/facturas/upload-ubl/`: Importar factura o nota crédito desde XML UBL 2.1 (multipart/form-data)
  - Body: `file` (archivo XML)
  - Query params:
    - `async=true` (default): Encola tarea Celery y retorna 202 + `task_id`
    - `async=false`: Parsea y materializa síncronamente (retorna 201/200)
    - `preview=true`: Modo preview (solo retorna DTO sin persistir, válido para Invoice y CreditNote)
  - **Pipeline canónico**: Usa `apps/services/xml_ingest` + `apps/services/xml_parser`
  - **Detección automática**: Detecta Invoice o CreditNote (raíz o embebida en AttachedDocument)
  - **Persistencia condicional**: Si `FEATURE_XML_PIPELINE=True` y `preview=false`, persiste automáticamente
  - Requiere CSRF token (`X-CSRFToken` header)
  - Logging estructurado: `facturas` logger con `request_id`, `schema_name`, `size`, `async`
  - Manejo de errores:
    - `{"error": "missing_xml", "message": "Falta archivo XML."}` → 400
    - `{"error": "read_error", "message": "Error al leer el archivo XML."}` → 400
    - `{"error": "missing_required_fields", "message": "...", "missing_fields": [...]}` → 422
    - `{"error": "internal", "message": "..."}` → 500
  - Retorna:
    - `async=true`: `{"task_id": str, "status": "PENDING"}` → 202 Accepted
    - `async=false`: `FacturaDetailSerializer` → 201 Created / 200 OK
- `GET /api/v1/facturas/ingest/{task_id}/status/`: Consulta estado de tarea de ingesta (polling)
  - **Nunca retorna 500**: Siempre 200 OK con JSON estructurado
  - Retorna: `{"state": "PENDING|STARTED|SUCCESS|FAILURE|UNKNOWN", "result": {...}, "error_code": "...", "message": "...", "hint": "..."}`
  - Logging estructurado: `apps.services.xml_ingest` logger con `request_id`, `schema_name`, `task_id`
- `POST /api/v1/facturas/create-from-dto/`: ⚠️ **REFACTOR v2.37** - Crea factura desde DTO parseado por `document_ingest`
  - Body: `{"dto": {...}, "persist_anexos": true|false}`
  - **Flujo separado**: Recibe DTO del pipeline universal y lo persiste bajo lógica propia
  - Validación: Verifica campos obligatorios (`emisor_nit`, `emisor_razon_social`, `receptor_nit`, `receptor_razon_social`)
  - Retorna: `{"id": int, "numero": str, "naturaleza": str, "created": bool}` → 201/200
  - Errores:
    - `{"error": "missing_dto", "message": "Falta 'dto' en el cuerpo."}` → 400
    - `{"error": "missing_required_fields", "message": "...", "missing_fields": [...]}` → 422
- `POST /api/v1/facturas/materialize/`: ⚠️ **DEPRECATED** - Usar `create-from-dto` en su lugar
  - Mantenido por compatibilidad temporal
- `POST /api/v1/facturas/importar-ubl/`: Importar factura desde XML UBL 2.1 (texto pegado) - **DEPRECADO**
  - Body: `{"xml": "<Invoice>...</Invoice>"}`
  - Retorna: `FacturaDetailSerializer`
  - **Nota**: Usar `upload-ubl` en su lugar (soporta async y mejor logging)
- `DELETE /api/v1/facturas/{id}/`: Eliminar factura (rollback de error de carga)
  - **Siempre permitido** (sin validaciones de estado o CUFE)
  - Requiere CSRF token (`X-CSRFToken` header)
  - Retorna: 204 No Content
- `POST /api/v1/facturas/`: **BLOQUEADO** → 405 Method Not Allowed
  - Mensaje: "Las facturas son documentos históricos importados. Use /api/v1/facturas/upload-ubl/ para importar desde XML UBL."
- `PUT /api/v1/facturas/{id}/`: **BLOQUEADO** → 405 Method Not Allowed
- `PATCH /api/v1/facturas/{id}/`: **BLOQUEADO** → 405 Method Not Allowed

**Workspace UI (Arquitectura Modular v2.30+):**
- **Arquitectura modular**: JS/CSS externos en `static/tenant/landing/workspace/`
  - `facturas.page.js`: Lógica completa del workspace (sin código inline)
  - `facturas.styles.css`: Estilos específicos del módulo
  - Assets incluidos vía partial: `apps/tenant/core/templates/tenant/core/partials/assets_facturas.html`
- **Toolbar unificada**: Una sola toolbar en `#workspace-facturas` con IDs estándar
  - `#btn-buscar`, `#btn-refrescar`, `#btn-importar-ubl`
  - `#txt-buscar`: Input de búsqueda con soporte Enter
- **Modales únicos**: Bootstrap 5 con data attributes
  - `#import-modal`: Modal de importación UBL con zona de feedback local
  - `#import-error-modal`: Modal reusable para errores
  - Contenedor de toasts global: `#toast-feedback`
- **Sistema de feedback consistente**:
  - **Alertas locales en modales**: `#feedback-import`, `#feedback-estado` con `aria-live="polite"`
  - **Toasts globales**: Notificaciones no intrusivas en esquina superior derecha
  - **Helpers estándar**: `showErrorLocal()`, `showWarnLocal()`, `showInfoLocal()`, `showSuccessLocal()`, `showToast()`
  - **Validación previa**: Advertencia si no hay archivo antes de enviar
  - **Cierre automático**: Modal se cierra después de 1.5s tras éxito
- **Funcionalidades**:
  - Listar/refrescar facturas con filtros y búsqueda (GET requests con parámetro `search`)
  - Búsqueda en tiempo real: Input `#txt-buscar` mapea a `?search=...` en API
  - Ver detalle de factura (modal read-only)
  - **NO hay botón "Editar"** (facturas son inmutables)
  - **Aplicar Nota Crédito** (v2.35): Modal para subir XML de NC desde workspace
    - Preview opcional con validación de referencia a factura
    - Persistencia con idempotencia por CUDE
    - Relación 1:1 con Factura (OneToOneField con PROTECT)

**⚠️ NOTAS CRÉDITO UBL 2.1 (v2.35 - Fases 0-9 Completadas):**

**Función:** Gestión de Notas Crédito UBL 2.1 vinculadas a Facturas
- Recepción y procesamiento de Notas Crédito XML UBL 2.1 (DIAN)
- Validación de referencia a Factura (número y CUFE)
- Almacenamiento con relación 1:1 con Factura
- Service Layer Pattern: Toda la lógica en `services.py`
- Pipeline canónico: Usa `apps/services/xml_ingest` + `apps/services/xml_parser`

**⚠️ REGLAS DE NEGOCIO - INMUTABILIDAD ESTRICTA:**
- **Las Notas Crédito son documentos históricos importados desde sistemas externos**
- **NUNCA se pueden editar, actualizar o modificar** (PUT/PATCH bloqueados → 405 Method Not Allowed)
- **Solo se pueden eliminar para corregir un error de carga** (rollback técnico)
- **POST manual está bloqueado** → 405 Method Not Allowed (solo se permite importación UBL)
- **Relación 1:1 con Factura**: Una factura solo puede tener UNA nota crédito (OneToOneField con PROTECT)
- **Idempotencia por CUDE**: Si ya existe una NC con el mismo CUDE, retorna 409 Conflict

**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios y UI en workspace
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propias notas crédito (aislamiento por esquema)

**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/facturas/services.py` - Lógica de persistencia
  - `guardar_nota_credito_desde_dto()`: Persiste NotaCrédito desde DTO canónico
    - Idempotencia por CUDE (409 si duplicado)
    - Validación de existencia de Factura referenciada (422 si no existe)
    - Validación 1:1 (422 si factura ya tiene NC)
    - Transaccional (`@transaction.atomic`)
- **Parser UBL:** `apps/services/xml_parser/ubl_credit_note.py` - Detección y parsing de NC (legacy)
  - Detecta `<CreditNote>` raíz o embebida en `AttachedDocument` CDATA
  - Extrae número, CUDE, fecha, moneda, totales, motivo, referencia a factura
  - Retorna DTO canónico con formato estándar
- **Pipeline Canónico (v2.36):** `apps/services/document_ingest/ingest_service.py`
  - `ingest_document()`: Orquesta detección, parsing y persistencia condicional (universal: XML, PDF, XLS, CSV, TXT)
  - Modo preview (`preview=True`): Solo retorna DTO sin persistir
  - Modo persistencia (`preview=False`): Delega a `guardar_nota_credito_desde_dto()`
  - Feature flag: `FEATURE_XML_PIPELINE` (default: `False`) controla rollout
  - **Backward Compatibility**: `apps/services/xml_ingest/ingest_service.ingest_xml()` sigue funcionando
- **ViewSets DRF:** `apps/tenant/facturas/api/viewsets.py`
  - `NotaCreditoViewSet`: List, Retrieve, Destroy (bloquea POST/PUT/PATCH)
  - `upload_ubl` (FacturaViewSet): Soporta preview mode (`?preview=true`) para NC
  - Endpoint dedicado `/xml/` para XML completo (no en list/detail)

**Modelos:**
- `NotaCredito`: Nota Crédito UBL 2.1 vinculada a Factura
  - `factura`: OneToOneField(Factura, related_name="nota_credito", on_delete=PROTECT)
  - `numero`: CharField(max_length=50, unique=True) - Número de NC (ej: "NC135")
  - `cude`: CharField(max_length=128, unique=True) - CUDE (identificador legal, clave de idempotencia)
  - `fecha_emision`: DateTimeField - Fecha/hora de emisión
  - `moneda`: CharField(max_length=8, default="COP")
  - `subtotal`, `impuestos`, `total`: DecimalField - Totales (alineados a LegalMonetaryTotal del XML)
  - `motivo`: TextField - Motivo de la nota crédito
  - `ref_factura_numero`: CharField - Número de factura referenciada (redundante)
  - `ref_factura_cufe`: CharField - CUFE de factura referenciada (redundante)
  - `xml_content`: TextField - XML UBL completo (expuesto solo en endpoint `/xml/`)
  - `created_at`, `updated_at`: DateTimeField - Metadatos
  - **Índices**: `cude`, `numero`, `fecha_emision`, `factura`
- `Factura.tiene_nota_credito`: Property que retorna `hasattr(self, "nota_credito")`

**APIs REST (TENANT_URLCONF):**
- `GET /api/v1/notas-credito/`: Listar notas crédito (paginado, filtros y búsqueda)
  - **Filtros**: `fecha_emision__date__gte`, `fecha_emision__date__lte`, `factura__id`, `factura__numero`, `factura__cufe`
  - **Búsqueda**: `search` (busca en `numero`, `cude`, `factura__numero`, `factura__cufe`, `motivo`)
  - **Paginación**: `page`, `page_size` (default: 10)
  - **Ordenamiento**: `ordering` (default: `-fecha_emision`)
  - Serializer: `NotaCreditoListSerializer` (campos mínimos, sin `xml_content`)
  - QuerySet optimizado con `select_related("factura")` y `only()`
- `GET /api/v1/notas-credito/{id}/`: Obtener detalle de nota crédito (read-only)
  - Serializer: `NotaCreditoDetailSerializer` (campos ampliados, sin `xml_content`)
- `GET /api/v1/notas-credito/{id}/xml/`: Obtener XML de nota crédito (endpoint dedicado)
  - Retorna: XML completo con `Content-Type: application/xml`
  - Inline si <= 2MB, descarga forzada si mayor
  - 204 No Content si no hay XML disponible
- `POST /api/v1/facturas/upload-ubl/?preview=true`: Preview de Nota Crédito (sin persistir)
  - Body: `file` (archivo XML de NC)
  - Retorna: `{"document_type": "creditnote.ubl21", "dto": {...}, "persisted": false}`
  - Validación client-side: Compara `dto.referencia.numero` y `dto.referencia.cufe` con factura seleccionada
- `POST /api/v1/facturas/upload-ubl/`: Importar Nota Crédito desde XML (persistencia)
  - Body: `file` (archivo XML de NC)
  - **Pipeline canónico**: Usa `ingest_xml(xml_text, preview=False)` cuando `FEATURE_XML_PIPELINE=True`
  - Retorna:
    - 201 Created: `{"document_type": "creditnote.ubl21", "dto": {...}, "persisted": true, "id": int, "numero": str, "cude": str, "created": true}`
    - 409 Conflict: `{"error": "duplicate", "message": "La nota crédito ya existe (CUDE duplicado)."}`
    - 422 Unprocessable Entity: `{"error": "missing_invoice|already_has_nc|missing_reference", "message": "..."}`
- `DELETE /api/v1/notas-credito/{id}/`: Eliminar nota crédito (rollback de error de carga)
  - Retorna: 204 No Content
  - 409 Conflict si hay relaciones protegidas
- `POST /api/v1/notas-credito/`: **BLOQUEADO** → 405 Method Not Allowed
- `PUT /api/v1/notas-credito/{id}/`: **BLOQUEADO** → 405 Method Not Allowed
- `PATCH /api/v1/notas-credito/{id}/`: **BLOQUEADO** → 405 Method Not Allowed

**Workspace UI (v2.35):**
- **Columna "NC" en tabla de facturas**: Muestra "Sí" (enlace) si tiene NC, "No" si no tiene
- **Botón "Aplicar NC"**: Visible solo en facturas sin NC (columna Acciones)
- **Modal "Aplicar Nota Crédito"**: `#aplicarNCModal`
  - Muestra factura seleccionada (número y CUFE)
  - Campo de archivo XML
  - Checkbox "Previsualizar y validar" (activado por defecto)
  - Feedback local (`#nc-feedback`) con mensajes de éxito/error
- **Flujo de aplicación**:
  1. Usuario hace clic en "Aplicar NC" de una factura sin NC
  2. Modal se abre con datos de factura
  3. Usuario selecciona archivo XML de NC
  4. (Opcional) Preview: POST a `upload-ubl/?preview=true`, valida tipo y referencia
  5. Persistencia: POST a `upload-ubl/` (sin preview), backend persiste con idempotencia
  6. Modal se cierra, tabla se refresca, columna NC cambia a "Sí"
- **Modal "Ver NC"**: Muestra detalle de NC existente con enlace a XML

**Feature Flag:**
- `FEATURE_XML_PIPELINE` (configurable vía variable de entorno, default: `False`)
- Cuando `True`: Pipeline canónico activo (preview y persistencia)
- Cuando `False`: Flujo legacy (solo preview, persistencia manual)

**Fases de Implementación (0-9):**
- **FASE 0**: Preparación y baseline (feature flag, validación de build)
- **FASE 1**: Skeleton del pipeline (IParser, ParserRegistry, ingest_service, validators, detectors, dto)
- **FASE 2**: Parsers iniciales (UBLInvoiceParser, UBLCreditNoteParser, preview-only)
- **FASE 3**: Integración no intrusiva en ViewSets (preview mode con `?preview=true`)
- **FASE 4**: Persistencia por dominio (guardar_nota_credito_desde_dto con idempotencia)
- **FASE 5**: Conectar persistencia por flag (ingest_xml delega a domain services)
- **FASE 6**: Endpoints pesados y contratos (/xml, bloqueo PUT/PATCH)
- **FASE 7**: API/Serializers + Endpoint pesado /xml (NotaCreditoViewSet completo)
- **FASE 8**: Workspace UI (columna NC + modal "Aplicar NC")
- **FASE 9**: Smoke tests + Auditorías + Rollout (tests multitenant, script de auditoría)

**Tests:**
- `apps/tenant/facturas/tests/test_nota_credito_pipeline.py`: Smoke tests completos
  - Detección de NC (raíz y embebida)
  - Preview mode
  - Persistencia e idempotencia
  - Relación 1:1 con Factura
  - Manejo de errores
  - Contratos API (list/detail sin XML, endpoint /xml)
  - Inmutabilidad (POST/PUT/PATCH bloqueados)

**Auditorías:**
- `scripts/audit_no_duplication.py`: Detecta lógica de parsing XML fuera de `apps/services/xml_*`
  - Eliminar factura (botón "Eliminar (error de carga)" con confirmación)
    - Mensaje: "Esta factura será eliminada solo del sistema SINTEL por error de carga. Esta acción es irreversible."
    - Incluye CSRF token en DELETE request
    - Actualización en tiempo real: fila se elimina sin recargar página
  - Importar UBL (modal con archivo XML)
    - Feedback local: errores se muestran en `#feedback-import` dentro del modal
    - Toast opcional: notificaciones globales para éxito/error
    - Respuestas minimalistas: `{"error": "<code>", "message": "<texto>"}`
    - Actualización en tiempo real: fila se inserta sin recargar página
- **Limpieza completa**: Sin código legacy, sin JS inline, sin referencias a DataTables antiguo

---

## 📄 Document Ingest Pipeline Universal (v2.40 - APP-SPECIFIC ARCHITECTURE)

**Función:** Pipeline universal para procesamiento de documentos (XML, PDF, XLS/XLSX, CSV, TXT)
- Detección automática de tipo de documento
- Parsing a DTO JSON unificado
- Validación por tipo de documento (sistema plug-in)
- ⚠️ **SOLO PARSEA, NO PERSISTE** (v2.37)
- Preview mode (siempre activo - siempre devuelve DTO sin persistir)
- Multi-tenant seguro con aislamiento por esquema

**⚠️ REFACTOR v2.37 - AISLAMIENTO COMPLETO DE CRUD:**
- `document_ingest` actúa **SOLO como parser auxiliar**
- NO crea, modifica ni borra registros de ninguna app
- NO llama a servicios CRUD de apps
- NO invoca el router de dominio para materializar
- Las apps consumen el DTO y persisten bajo su propia lógica mediante endpoints propios

**Estado:** ✅ Implementado completamente (FASE 0-9 + REFACTOR v2.37 + APP-SPECIFIC v2.40)
**Versión:** 2.40
**Última Actualización:** 2026-02-17

**⚠️ v2.40 - CAMBIOS PRINCIPALES:**
- **Routing por app**: Cada app tiene sus parsers independientes (`apps/services/document_parser/{app}/`)
- **Validación por app**: Cada app puede tener su validador específico (`validations/{app}.py`)
- **Protección contra fallback**: Inventario/cotizaciones NUNCA usan validaciones de facturas
- **Auto-registro de parsers**: Los parsers se registran automáticamente al importar módulos de app
- **SemanticMapper**: Mapeo inteligente de columnas con fuzzy matching y sinónimos

### Arquitectura del Pipeline

El pipeline universal sigue una arquitectura de capas estrictamente separadas:

```
┌─────────────────────────────────────────────────────────────┐
│  API Endpoint (apps/tenant/core/api/viewsets_documentos.py) │
│  POST /api/v1/core/documentos/upload/                       │
│  ⚠️ SIEMPRE devuelve DTO sin persistir                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Document Ingest Service                                     │
│  (apps/services/document_ingest/ingest_service.py)         │
│  ⚠️ SOLO PARSEA, NO PERSISTE                                │
│  - Calcular SHA256                                           │
│  - Registrar metadatos                                       │
│  - Llamar router → parsear a DTO                            │
│  - Normalizar DTO                                            │
│  - Ejecutar validaciones (run_validations)                  │
│  - Retornar DTO (SIEMPRE sin persistir)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Document Parser     │    │  Validation Router  │
│  (document_parser/)  │    │  (validations/)      │
│  - Detector          │    │  - BaseValidator     │
│  - Normalizers       │    │  - Validators por   │
│  - Parsers (XML,     │    │    tipo (factura,   │
│    PDF, Excel, CSV,  │    │    creditnote,      │
│    TXT)              │    │    gasto, inventario)│
└──────────────────────┘    └──────────────────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  DTO JSON Unificado                                          │
│  {                                                           │
│    "success": true,                                          │
│    "persisted": false,  ← SIEMPRE false                     │
│    "dto": {...},                                            │
│    "sha256": "...",                                          │
│    "tipo": "invoice|creditnote|gasto|...",                  │
│    "create_endpoint": "/api/v1/facturas/create-from-dto/"  │
│  }                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  App Endpoint (apps/tenant/*/api/viewsets.py)                │
│  POST /api/v1/facturas/create-from-dto/                     │
│  POST /api/v1/gastos/create-from-dto/                       │
│  POST /api/v1/inventario/create-from-dto/                    │
│  - Recibe DTO del pipeline universal                        │
│  - Valida internamente                                       │
│  - Persiste bajo lógica propia                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Domain Services     │    │  Domain Services      │
│  (facturas/services) │    │  (gastos/services)    │
│  - guardar_factura   │    │  - materializar_gasto │
│  - guardar_nc        │    │                       │
└──────────────────────┘    └──────────────────────┘
```

### Componentes Principales

#### 1. Document Parser (`apps/services/document_parser/`)

**Responsabilidad:** Parsing low-level genérico, agnóstico del dominio

**Estructura:**
- `detector.py`: Detección de tipo por magic bytes, MIME type, extensión, heurísticas
  - Retorna: `{"media_type": "xml|pdf|excel|csv|txt", "confidence": 0.0-1.0}`
- `normalizers.py`: Normalización de contenido
  - UTF-8 encoding
  - Limpieza de acentos y caracteres ilegales
  - Normalización de whitespace
  - Sanitización de texto
  - Conversión numérica a decimal-string
  - Extracción de texto desde PDF (pdfminer.six)
  - Normalización de Excel/CSV a DataFrame
- `dto.py`: DTO unificado JSON (`DocumentoDTO`)
  - Campos comunes: `document_type`, `type`, `numero`, `identificadores`, `fecha_emision`, `emisor`, `receptor`, `totales`
  - Campos específicos por tipo: `categoria`, `centro_costo` (gasto), `items`, `almacen` (inventario), etc.
- Parsers específicos:
  - `xml_parser/parser.py`: UBL 2.1 Invoice/CreditNote
  - `pdf_parser/parser.py`: Extracción de texto y heurísticas
  - `excel_parser/parser.py`: XLS/XLSX a DataFrame → DTO
  - `csv_parser/parser.py`: CSV a DataFrame → DTO
  - `txt_parser/parser.py`: Heurísticas de texto → DTO

**Principios:**
- ✅ Agnóstico del dominio: no conoce modelos Django
- ✅ Reutilizable: puede ser usado por cualquier app
- ✅ Extensible: permite agregar nuevos tipos sin tocar la orquestación

#### 2. Document Ingest (`apps/services/document_ingest/`)

**⚠️ v2.40: Responsabilidad:** Orquestación, routing por app, validación por app - **SOLO PARSEA, NO PERSISTE**

**Estructura:**
- `app_router.py`: ⚠️ **NUEVO v2.40** - Router específico por app
  - `register_app_parser(app_name, media_type, parser_func)`: Registra parser específico de app
  - `get_app_parser(app_name, media_type)`: Obtiene parser específico de app
  - `detect_app_from_kind_hint(kind_hint)`: Detecta app desde hint (ej: "inventario" → "cotizaciones")
  - `route_by_app(file_bytes, media_type, filename, kind_hint, app_name)`: Enruta a parser específico de app
  - **Principio**: Cada app tiene sus parsers independientes (ej: `cotizaciones`, `facturas`)
- `router.py`: Routing dinámico según tipo detectado (genérico + app-specific)
  - `route(file_bytes, filename, mime_type, kind_hint) -> {"document_type": str, "dto": dict}`
  - ⚠️ **v2.40**: Prioriza parsers específicos por app antes de parsers genéricos
  - ⚠️ **v2.40**: Si detecta `kind_hint=inventario` y app=cotizaciones, fuerza uso de parser específico
  - Mapeo de `media_type` a función de parsing (fallback genérico si no hay parser específico)
- `ingest_service.py`: Servicio principal
  - `ingest_document(content, filename, mime_type, kind_hint, preview, async_mode) -> (result, status_code)`
  - Flujo: `route()` (app-specific primero) → `normalize()` → `run_validations()` (app-specific primero) → **Retorna DTO (SIEMPRE sin persistir)**
  - ⚠️ **Parámetro `preview` ignorado**: Siempre devuelve DTO sin persistir
  - ⚠️ **v2.40**: Protección contra fallback genérico para inventario/cotizaciones (no usa validaciones de facturas)
  - Retorna: `{"success": true, "persisted": false, "dto": {...}, "sha256": str, "metadata": {...}, "tipo": str, "create_endpoint": str, "confidence_score": float, "mapping_metadata": dict}`
- `validations/`: Sistema de validadores plug-in por app
  - `base.py`: `BaseValidator` (interfaz abstracta con `app_name` property)
  - `router.py`: Router de validaciones (`run_validations(dto_json)`)
    - ⚠️ **v2.40**: Prioriza validadores específicos por app (ej: `CotizacionesValidator` sobre `InventarioValidator`)
    - ⚠️ **v2.40**: NUNCA usa fallback genérico para inventario/cotizaciones (evita validaciones de facturas)
  - Validadores específicos por app:
    - `cotizaciones.py`: ⚠️ **NUEVO v2.40** - Validador específico para catálogos de productos en cotizaciones
    - `factura.py`: Validaciones de facturas UBL 2.1
    - `nota_credito.py`: Validaciones de notas crédito UBL 2.1
    - `gasto.py`: Validaciones de gastos
    - `inventario.py`: Validaciones genéricas de inventario (fallback si no hay validador específico de app)
- `validators.py`: Validadores legacy (mantenido por compatibilidad)
  - ⚠️ **v2.40**: NUNCA usa `_validate_document_dto_generic` para inventario/cotizaciones

**Principios v2.40:**
- ✅ **Routing por app**: Cada app tiene sus parsers independientes en `apps/services/document_parser/{app}/`
- ✅ **Validación por app**: Cada app puede tener su validador específico en `validations/{app}.py`
- ✅ **Aislamiento completo**: Parsers y validadores de una app no afectan a otras
- ✅ **Protección contra fallback**: Inventario/cotizaciones NUNCA usan validaciones de facturas
- ✅ Orquestación: Coordina parsing, normalización y validación
- ✅ **NO persiste**: NO crea, modifica ni borra registros de ninguna app
- ✅ Agnóstico del dominio: no conoce modelos Django
- ✅ Siempre devuelve DTO: El parámetro `preview` es ignorado - siempre devuelve DTO sin persistir
- ✅ Las apps persisten: Cada app tiene su propio endpoint para persistir desde DTO

#### 3. Domain Router (`apps/tenant/core/document_router.py`)

**⚠️ REFACTOR v2.37: DESACTIVADO - Ya no se usa para materialización automática**

**Estado:** El router de dominio ya no se invoca desde `document_ingest`. Las apps persisten directamente mediante sus propios endpoints.

**Funcionalidad (Legacy - mantenido por compatibilidad):**
- `materialize_document(dto, request_id) -> (payload, status_code)` - ⚠️ NO se usa desde `document_ingest`
- Registro lazy de materializadores (mantenido para referencia):
  - `"invoice"` → `apps.tenant.facturas.services.guardar_factura_desde_dto()`
  - `"creditnote"` → `apps.tenant.facturas.services.guardar_nota_credito_desde_dto()`
  - `"gasto"` → `apps.tenant.gastos.services.materializar_gasto_desde_dto()`
  - `"inventario"` → `apps.tenant.inventario.services.materializar_inventario_desde_dto()`

**⚠️ NUEVO FLUJO v2.37:**
- Las apps tienen endpoints propios para persistir desde DTO:
  - `POST /api/v1/facturas/create-from-dto/`: Recibe DTO y persiste usando `guardar_factura_desde_dto()`
  - `POST /api/v1/gastos/create-from-dto/`: Recibe DTO y persiste usando `materializar_gasto_desde_dto()`
  - `POST /api/v1/inventario/create-from-dto/`: Recibe DTO y persiste usando `materializar_inventario_desde_dto()`

### Endpoint Universal

**API:** `POST /api/v1/core/documentos/upload/`

**Ubicación:** `apps/tenant/core/api/viewsets_documentos.py`

**⚠️ REFACTOR v2.37: Características:**
- Recibe `file` (multipart/form-data)
- Parámetros:
  - `preview=true|false` (query param o form field): ⚠️ **Ignorado** - siempre devuelve DTO sin persistir
  - `tipo=gasto|inventario|...` (opcional): Sugerencia de tipo para optimizar detección
- Detección automática de tipo de documento
- Soporta: XML, PDF, XLS/XLSX, CSV, TXT
- ⚠️ **SIEMPRE devuelve DTO sin persistir** - `persisted` siempre es `false`
- Retorna JSON estructurado:
  ```json
  {
    "success": true,
    "persisted": false,  ← SIEMPRE false
    "dto": {...},
    "sha256": "...",
    "metadata": {...},
    "tipo": "invoice | creditnote | gasto | inventario | ...",
    "create_endpoint": "/api/v1/facturas/create-from-dto/" | null
  }
  ```
- Códigos HTTP:
  - `200 OK`: DTO parseado (siempre sin persistir)
  - `400 Bad Request`: Error de parsing/detección
  - `415 Unsupported Media Type`: Tipo no soportado
  - `422 Unprocessable Entity`: Error de validación
  - `500 Internal Server Error`: Error interno

**Ejemplo de uso:**
```bash
# Parsear documento (siempre devuelve DTO sin persistir)
curl -X POST "https://tenant.sintel.com/api/v1/core/documentos/upload/?tipo=gasto" \
  -H "X-CSRFToken: ..." \
  -F "file=@gasto.csv"

# Respuesta: {"success": true, "persisted": false, "dto": {...}, "create_endpoint": "/api/v1/gastos/create-from-dto/"}

# Persistir DTO en la app (endpoint propio de la app)
curl -X POST "https://tenant.sintel.com/api/v1/gastos/create-from-dto/" \
  -H "X-CSRFToken: ..." \
  -H "Content-Type: application/json" \
  -d '{"dto": {...}, "persist_anexos": true}'
```

---

## ✅ Validadores por Tipo de Documento (v2.36 - FASE 4-5 COMPLETADAS)

**Función:** Sistema de validadores plug-in para validar DTOs según tipo de documento
- Validadores modulares y extensibles
- Registro automático de validadores
- Routing dinámico por tipo de documento
- Errores deterministas y estructurados

**Estado:** ✅ Implementado completamente
**Ubicación:** `apps/services/document_ingest/validations/`

### Arquitectura de Validadores

El sistema de validadores sigue un patrón plug-in:

```
┌─────────────────────────────────────────────────────────────┐
│  Validation Router                                           │
│  (validations/router.py)                                     │
│  - run_validations(dto_json)                                 │
│  - Selecciona validador según dto["type"]                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│  FacturaValidator    │    │  GastoValidator      │
│  (factura.py)        │    │  (gasto.py)          │
│  - CUFE obligatorio  │    │  - Total > 0         │
│  - Totales coherentes│    │  - Fecha válida      │
│  - Fechas válidas    │    │  - Proveedor requerido│
└──────────────────────┘    └──────────────────────┘
        │                             │
        ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│  NotaCreditoValidator │    │  InventarioValidator │
│  (nota_credito.py)    │    │  (inventario.py)     │
│  - CUDE obligatorio   │    │  - Items ≥ 1         │
│  - Referencia factura │    │  - Cantidades > 0     │
│  - Totales coherentes │    │  - Unidades válidas   │
└──────────────────────┘    └──────────────────────┘
```

### BaseValidator (Interfaz Abstracta)

**Ubicación:** `apps/services/document_ingest/validations/base.py`

**Interfaz:**
```python
class BaseValidator(ABC):
    @property
    @abstractmethod
    def document_type(self) -> str:
        """Tipo de documento que valida (ej: 'invoice.ubl21', 'gasto')"""
        pass
    
    @property
    def app_name(self) -> str:
        """Nombre de la app (ej: 'facturas', 'gastos')"""
        return "general"
    
    @abstractmethod
    def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Valida un DTO.
        
        Returns:
            Tuple[bool, Optional[str], List[str]]: (is_valid, error_code, errors)
        """
        pass
    
    def validate_common_fields(self, dto: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida campos comunes a todos los documentos."""
        pass
```

### Validadores Implementados

#### 1. FacturaValidator (`factura.py`)

**Tipo:** `"invoice.ubl21"`  
**App:** `"facturas"`

**Validaciones:**
- ✅ CUFE obligatorio (`identificadores.cufe` o `identificadores.uuid`)
- ✅ Totales coherentes (subtotal + impuestos = total)
- ✅ Fechas válidas (`fecha_emision`)
- ✅ Emisor y receptor presentes
- ✅ Número de documento detectado

**Errores:**
- `"missing_required_fields"`: Campos obligatorios faltantes
- `"validation_error"`: Errores de validación (totales, fechas, etc.)

#### 2. NotaCreditoValidator (`nota_credito.py`)

**Tipo:** `"creditnote.ubl21"`  
**App:** `"facturas"`

**Validaciones:**
- ✅ CUDE obligatorio (`identificadores.cude` o `identificadores.uuid`)
- ✅ Referencia a factura obligatoria (`referencia.numero` o `referencia.cufe`)
- ✅ Totales coherentes
- ✅ Fechas válidas
- ✅ Emisor y receptor presentes

**Errores:**
- `"missing_required_fields"`: Campos obligatorios faltantes
- `"validation_error"`: Errores de validación

#### 3. GastoValidator (`gasto.py`)

**Tipo:** `"gasto"`  
**App:** `"gastos"`

**Validaciones:**
- ✅ Total > 0 (`totales.total`)
- ✅ Fecha válida (`fecha_emision`)
- ✅ Emisor y receptor presentes
- ✅ Campos comunes (número, emisor, receptor, totales)

**Errores:**
- `"validation_error"`: Total <= 0, fecha inválida
- `"missing_required_fields"`: Campos obligatorios faltantes

#### 4. CotizacionesValidator (`cotizaciones.py`) ⚠️ **NUEVO v2.40**

**Tipo:** `"inventario.catalogo"`  
**App:** `"cotizaciones"`

**Validaciones:**
- ✅ Al menos 1 item (`items` no vacío)
- ✅ Cada item tiene `codigo` y `nombre` (obligatorios)
- ✅ `precio_venta` válido si está presente (numérico, no negativo)
- ✅ `unidad` válida si está presente (string)
- ⚠️ **NO valida campos de facturas** (emisor, receptor, CUFE, etc.)

**Errores:**
- `"validation_errors"`: Items sin código/nombre, precios inválidos
- `"missing_items"`: Sin items en el catálogo

**Prioridad:** Este validador tiene prioridad sobre `InventarioValidator` para documentos de tipo `inventario` cuando la app es `cotizaciones`.

#### 5. InventarioValidator (`inventario.py`)

**Tipo:** `"inventario.catalogo"`  
**App:** `"inventario"` (genérico, fallback)

**Validaciones:**
- ✅ Al menos 1 item (`items` no vacío)
- ✅ Cada item tiene `codigo` y `nombre` (obligatorios)
- ✅ `precio_venta` válido si está presente
- ✅ `unidad` válida si está presente
- ⚠️ **NO valida campos de facturas**

**Errores:**
- `"validation_errors"`: Items sin código/nombre, precios inválidos
- `"missing_items"`: Sin items en el catálogo

**Nota:** Este validador se usa como fallback genérico. Si existe un validador específico de app (ej: `CotizacionesValidator`), ese tiene prioridad.

### Router de Validaciones

**Ubicación:** `apps/services/document_ingest/validations/router.py`

**Funcionalidad:**
- `run_validations(dto_json) -> (is_valid, error_code, errors)`
- Selecciona validador según `dto["type"]` o `dto["document_type"]`
- Registro automático de validadores al importar módulo
- Fallback a validación genérica si no hay validador específico

**Registro v2.40:**
```python
# Validadores se registran automáticamente en validations/__init__.py
# Prioridad: Validadores específicos por app tienen prioridad sobre genéricos

VALIDATORS = {
    "invoice": FacturaValidator(),  # app_name: "facturas"
    "creditnote": NotaCreditoValidator(),  # app_name: "facturas"
    "gasto": GastoValidator(),  # app_name: "gastos"
    "inventario": CotizacionesValidator(),  # ⚠️ v2.40: Prioridad sobre InventarioValidator
}

# Validadores también se registran por app_name para routing específico
_validators = {
    "cotizaciones:inventario.catalogo": CotizacionesValidator(),
    "cotizaciones:inventario": CotizacionesValidator(),
    "inventario:inventario.catalogo": InventarioValidator(),  # Fallback genérico
}
```

**⚠️ v2.40 - Priorización:**
- Si `doc_type_base == "inventario"`, el router busca primero `CotizacionesValidator` (app_name="cotizaciones")
- Si no encuentra validador específico de app, usa `InventarioValidator` (genérico)
- **NUNCA** usa fallback genérico de facturas para inventario/cotizaciones

### Integración en Pipeline

El sistema de validadores se integra en `ingest_service.py`:

```python
# 6. Ejecutar validaciones (FASE 5: run_validations)
is_valid, error_code, missing_fields = run_validations(dto_dict)

if not is_valid:
    return {
        "persisted": False,
        "dto": dto_dict,
        "error": error_code,
        "message": f"Validación fallida: {', '.join(missing_fields[:5])}",
        "missing_fields": missing_fields,
    }, 422
```

### Extensibilidad v2.40

Para agregar un nuevo parser y validador por app:

#### 1. Crear Parser Específico de App

1. Crear directorio: `apps/services/document_parser/{app}/`
2. Crear `excel_parser.py` (o `pdf_parser.py`, etc.):
   ```python
   from apps.services.document_parser.cotizaciones.normalizers import SemanticMapper
   
   def parse_catalogo_to_dto(file_bytes: bytes, filename: str = None, kind_hint: str = None) -> Dict[str, Any]:
       # Lógica de parsing específica de la app
       return {
           "document_type": "inventario.catalogo",
           "type": "inventario",
           "items": [...],
           "mapping_metadata": {...}
       }
   ```
3. Crear `__init__.py` para auto-registro:
   ```python
   from .excel_parser import parse_catalogo_to_dto
   
   def _register_parsers():
       from apps.services.document_ingest.app_router import register_app_parser
       register_app_parser("cotizaciones", "excel", parse_catalogo_to_dto)
       register_app_parser("cotizaciones", "xls", parse_catalogo_to_dto)
       register_app_parser("cotizaciones", "xlsx", parse_catalogo_to_dto)
   
   _register_parsers()
   ```

#### 2. Crear Validador Específico de App

1. Crear archivo: `apps/services/document_ingest/validations/{app}.py`
2. Heredar de `BaseValidator`:
   ```python
   class CotizacionesValidator(BaseValidator):
       @property
       def document_type(self) -> str:
           return "inventario.catalogo"
       
       @property
       def app_name(self) -> str:
           return "cotizaciones"  # ⚠️ CRÍTICO: Identifica la app
       
       def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
           # Validaciones específicas de la app
           # ⚠️ NO validar campos de facturas (emisor, receptor, CUFE, etc.)
           pass
   ```
3. Registrar en `validations/__init__.py`:
   ```python
   from .cotizaciones import CotizacionesValidator
   register_validator(CotizacionesValidator())  # ⚠️ Registrar ANTES de validadores genéricos
   ```

**⚠️ v2.40 - Principios de Extensibilidad:**
- Cada app tiene sus parsers y validadores **independientes**
- Los parsers se auto-registran al importar el módulo de app
- Los validadores específicos de app tienen **prioridad** sobre genéricos
- **NUNCA** usar fallback genérico de facturas para inventario/cotizaciones

---

## 🔗 Integración con Apps de Negocio (v2.36 - FASE 6-7 COMPLETADAS)

**Función:** Permitir que apps de negocio (`gastos`, `inventario`, `ordenes_compra`, etc.) usen el pipeline universal
- Cada app define su propio validador especializado
- Cada app define su propia interpretación DTO → Dominio
- Cada app aplica sus propias reglas de negocio
- Sin duplicar parsers (SSoT)
- Respetando Domain-Driven Design

**Estado:** ✅ Patrón de integración documentado e implementado
**Documentación:** `documentacion/FASE_6_INTEGRACION_APPS.md`

### Principios de Integración

1. **SSoT (Single Source of Truth):**
   - El pipeline produce solo DTO JSON unificado
   - El dominio aplica validaciones específicas y materialización

2. **Separación de Responsabilidades:**
   - **Parsing/Normalización**: `apps/services/document_parser/*` (low-level)
   - **Orquestación/Validación**: `apps/services/document_ingest/*` (middleware)
   - **Materialización**: `apps/tenant/*/services.py` (dominio)

3. **Extensibilidad:**
   - Agregar nuevos tipos sin modificar core
   - Validadores plug-in por tipo
   - Materializadores registrados dinámicamente

### Patrón de Integración

Para integrar una nueva app al pipeline universal:

#### Paso 1: Extender DTO (si es necesario)

El DTO unificado (`DocumentoDTO`) ya soporta campos específicos por tipo:

```python
@dataclass
class DocumentoDTO:
    # Campos comunes
    document_type: str
    type: Optional[DocumentTypeBase]  # "invoice" | "creditnote" | "gasto" | "inventario" | ...
    numero: str
    identificadores: IdentificadoresDTO
    fecha_emision: str
    emisor: PartyDTO
    receptor: PartyDTO
    totales: TotalesDTO
    
    # Campos específicos para Gasto
    categoria: Optional[str] = None
    centro_costo: Optional[str] = None
    
    # Campos específicos para Inventario
    items: List[Dict[str, Any]] = field(default_factory=list)
    almacen: Optional[str] = None
```

Si necesitas campos adicionales, extiende `DocumentoDTO` en `dto.py`.

#### Paso 2: Crear Validador Especializado

Crear archivo: `apps/services/document_ingest/validations/nueva_app.py`

```python
from typing import Dict, Any, Tuple, List, Optional
from .base import BaseValidator

class NuevaAppValidator(BaseValidator):
    @property
    def document_type(self) -> str:
        return "nuevo_tipo"
    
    @property
    def app_name(self) -> str:
        return "nueva_app"
    
    def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
        missing_fields = []
        errors = []
        
        # Validar campos obligatorios
        is_valid_common, missing_common = self.validate_common_fields(dto)
        if not is_valid_common:
            missing_fields.extend(missing_common)
        
        # Validaciones específicas de la app
        if dto.get("totales", {}).get("total", "0.00") <= "0.00":
            errors.append("El total debe ser mayor a cero")
        
        if missing_fields or errors:
            error_code = "validation_error" if errors else "missing_required_fields"
            return False, error_code, missing_fields + errors
        return True, None, []
```

Registrar en `validations/__init__.py`:
```python
from .nueva_app import NuevaAppValidator
register_validator(NuevaAppValidator())
```

#### Paso 3: Crear Materializador en Dominio

Crear archivo: `apps/tenant/nueva_app/services.py`

```python
"""
Servicios de dominio para NuevaApp (FASE 6 + REFACTOR v2.37).

⚠️ PRINCIPIOS:
- Mapeo DTO → Dominio: Convierte DTO JSON unificado a modelos Django
- Idempotencia: Previene duplicados usando claves legales
- Transaccional: Todo o nada (transaction.atomic)
- Multi-tenant: Opera en el contexto del tenant actual (schema_context)
"""
import logging
from typing import Dict, Any, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context
from decimal import Decimal
from datetime import datetime

from .models import NuevoModelo

logger = logging.getLogger("tenant.nueva_app.materializer")

def materializar_nuevo_desde_dto(dto: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Materializa un NuevoModelo desde DTO JSON unificado (FASE 6 + REFACTOR v2.37).
    
    ⚠️ REFACTOR v2.37: Esta función es llamada desde el endpoint de la app,
    NO desde document_ingest ni document_router.
    
    Mapeo DTO → Dominio:
    - dto["fecha_emision"] → NuevoModelo.fecha
    - dto["emisor"]["nit"] → NuevoModelo.proveedor_nit
    - dto["totales"]["total"] → NuevoModelo.total
    - dto["numero"] → NuevoModelo.numero
    
    Reglas:
    - Idempotencia: Previene duplicados usando número de documento
    - Transaccional: Todo o nada
    - Multi-tenant: Opera en el contexto del tenant actual
    
    Returns:
        Tuple (result, status_code):
        - result: {"id": int, "numero": str, "created": bool, ...}
        - status_code: 200 (actualizado), 201 (creado), 409 (duplicado), 422 (validación)
    """
    numero = dto.get("numero")
    if not numero:
        raise ValidationError({"error": "missing_number", "message": "Número es obligatorio"})
    
    # Idempotencia: buscar duplicados
    try:
        existente = NuevoModelo.objects.get(numero=numero)
        # Actualizar si es necesario
        return {"id": existente.id, "numero": existente.numero, "created": False}, 200
    except NuevoModelo.DoesNotExist:
        pass
    
    # Extraer campos del DTO
    fecha_emision_str = dto.get("fecha_emision")
    total_str = dto.get("totales", {}).get("total")
    
    if not all([fecha_emision_str, total_str]):
        missing = [f for f, v in {"fecha_emision": fecha_emision_str, "totales.total": total_str}.items() if not v]
        raise ValidationError({"error": "missing_required_fields", "message": f"Campos faltantes: {', '.join(missing)}"})
    
    try:
        fecha_emision = datetime.fromisoformat(fecha_emision_str.replace('Z', '+00:00'))
        total = Decimal(total_str)
    except (ValueError, TypeError) as e:
        raise ValidationError({"error": "invalid_data_format", "message": f"Formato inválido: {e}"})
    
    with transaction.atomic():
        nuevo = NuevoModelo.objects.create(
            numero=numero,
            fecha=fecha_emision,
            total=total,
            # ... otros campos
        )
        return {"id": nuevo.id, "numero": nuevo.numero, "created": True}, 201
```

#### Paso 4: Crear Endpoint en App para Persistir desde DTO

**⚠️ REFACTOR v2.37: NO se registra en Domain Router. Se crea endpoint propio en la app.**

Crear endpoint en `apps/tenant/nueva_app/api/viewsets.py`:

```python
@action(detail=False, methods=["post"], url_path="create-from-dto")
def create_from_dto(self, request: Request) -> Response:
    """
    ⚠️ REFACTOR v2.37: Crea un NuevoModelo desde DTO parseado por document_ingest.
    
    POST /api/v1/nueva_app/create-from-dto/
    
    Body: {"dto": {...}, "persist_anexos": true|false}
    
    Returns: 201 Created | 200 OK | 409 Conflict | 422 Unprocessable Entity
    """
    dto = request.data.get("dto")
    if not dto:
        return Response({"error": "missing_dto", "message": "Falta 'dto' en el cuerpo."}, status=400)
    
    from .services import materializar_nuevo_desde_dto
    payload, code = materializar_nuevo_desde_dto(dto)
    return Response(payload, status=code)
```

### Apps Integradas

#### 1. Gastos (`apps/tenant/gastos/`)

**Validador:** `apps/services/document_ingest/validations/gasto.py`  
**Materializador:** `apps/tenant/gastos/services.py::materializar_gasto_desde_dto()`

**Validaciones:**
- Total > 0
- Fecha válida
- Proveedor requerido

**Mapeo DTO → Dominio (v2.40 - Sistema de Documento Soporte Inmutable):**
- **DocumentoSoporte (Evidencia Legal Inmutable):**
  - `dto["fecha_emision"]` → `DocumentoSoporte.fecha`
  - `dto["emisor"]["nit"]` → `DocumentoSoporte.vendedor_nit` (normalizado)
  - `dto["emisor"]["razon_social"]` → `DocumentoSoporte.vendedor_razon_social`
  - `dto["totales"]["subtotal"]` → `DocumentoSoporte.subtotal`
  - `dto["totales"]["retefuente"]` → `DocumentoSoporte.retefuente`
  - `dto["totales"]["reteica"]` → `DocumentoSoporte.reteica`
  - `dto["totales"]["total"]` → `DocumentoSoporte.total`
  - `dto["numero_documento"]` → `DocumentoSoporte.numero_factura_proveedor`
  - `consecutivo`: Generado automáticamente con `generar_consecutivo_soporte(empresa)`
- **Gasto (Clasificación Contable):**
  - `dto["categoria"]` → `Gasto.categoria_contable`
  - `dto["centro_costo"]` → `Gasto.centro_costo`
  - `dto["periodo"]` → `Gasto.periodo`
  - `Gasto.documento_soporte`: OneToOneField al DocumentoSoporte creado
- **⚠️ REGLA DE ORO v2.40**: El DocumentoSoporte se crea primero (inmutable), luego el Gasto (clasificación)

#### 2. Inventario (`apps/tenant/inventario/`)

**Validador:** `apps/services/document_ingest/validations/inventario.py`  
**Materializador:** `apps/tenant/inventario/services.py::materializar_inventario_desde_dto()`

**Validaciones:**
- Al menos 1 item
- Cantidades > 0
- Unidades válidas

**Mapeo DTO → Dominio:**
- `dto["fecha_emision"]` → `Inventario.fecha`
- `dto["almacen"]` → `Inventario.almacen`
- `dto["items"]` → `ItemInventario` (múltiples registros)

### Flujo Completo de Integración (v2.37 - REFACTOR)

**⚠️ REFACTOR v2.37: Flujo Separado (Parseo → Persistencia)**

```
1. Usuario sube documento → POST /api/v1/core/documentos/upload/?tipo=gasto
2. Endpoint llama → ingest_document(content, kind_hint="gasto", preview=True)
   ⚠️ preview siempre True - document_ingest NO persiste
3. Pipeline detecta tipo → route() → parse_to_dto() → DTO con type="gasto"
4. Pipeline valida → run_validations(dto) → GastoValidator.validate()
5. Pipeline retorna DTO → {"success": true, "persisted": false, "dto": {...}, "create_endpoint": "/api/v1/gastos/create-from-dto/"}
6. App (JS o backend) recibe DTO → Llama a POST /api/v1/gastos/create-from-dto/ con DTO
7. Endpoint de app valida internamente → materializar_gasto_desde_dto(dto)
8. Materializador persiste → Gasto.objects.create(...)
9. Retorna → {"id": 123, "numero": "...", "created": true} → 201 Created
```

**Separación de Responsabilidades:**
- **`document_ingest`**: SOLO parsea y devuelve DTO
- **App endpoint**: Recibe DTO y persiste bajo lógica propia
- **CRUD independiente**: Cada app mantiene su CRUD manual y CRUD asistido por documento

### Tests de Integración

Cada app integrada debe tener tests:

- `tests/tenant/gastos/test_gasto_parser_integration.py`: Parser → DTO
- `tests/tenant/gastos/test_gasto_materialization.py`: DTO → Dominio
- `tests/tenant/gastos/test_gasto_validator.py`: Validaciones
- `tests/api/test_upload_document_endpoint_gasto.py`: Endpoint API

Ver `tests/` para ejemplos completos.

---

#### 3. `apps.tenant.contabilidad` ✅ IMPLEMENTADO
**Función:** Módulo contable
- Registros contables por tenant
- Asientos contables
- Reportes financieros (pendiente)
- Integración con facturas
**Estado:** ✅ Implementado con modelos, serializers, viewsets y admin
**Esquema:** `tenant_<schema_name>`
**Nota:** DataTables client-side por defecto - server-side solo cuando se solicite explícitamente
**Aislamiento:** Cada tenant tiene su propia contabilidad
**Modelos:**
- `CuentaContable`: Plan de cuentas contables
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **Índice**: `models.Index(fields=["empresa"])` en `Meta.indexes` (v2.40)
- `AsientoContable`: Asientos contables
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **Índice**: `models.Index(fields=["empresa"])` en `Meta.indexes` (v2.40)
- `MovimientoContable`: Movimientos (partidas) de un asiento
**APIs REST:**
- `GET /api/v1/cuentas-contables/`: Listar cuentas contables
- `POST /api/v1/cuentas-contables/`: Crear cuenta contable
- `GET /api/v1/asientos-contables/`: Listar asientos contables
- `POST /api/v1/asientos-contables/`: Crear asiento contable
- `POST /api/v1/asientos-contables/{id}/aprobar/`: Aprobar asiento contable
- `GET /api/v1/movimientos-contables/`: Listar movimientos contables
- `POST /api/v1/cuentas-contables/dt/cuentas/`: DataTables endpoint (v2.40 - @action en ViewSet)

#### 4. `apps.tenant.clientes` ✅ IMPLEMENTADO (v2.40)
**Función:** Gestión de clientes y ventas
- Información legal y comercial de clientes
- Gestión de ventas por cliente
- Alineado con normativa colombiana
- Service Layer Pattern: `qs_list()` y `qs_detail()` en `services.py`
**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios y admin
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propios clientes
**Modelos:**
- `Cliente`: Información legal y comercial de clientes
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **Índice**: `models.Index(fields=["empresa"])` en `Meta.indexes` (v2.40)
  - Campos: `tipo_persona`, `tipo_documento`, `numero_documento`, `razon_social`, `nombre_comercial`, `regimen_tributario`, `responsable_iva`, `activo`
- `VentaCliente`: Ventas asociadas a clientes
**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/clientes/services.py`
  - `LIST_FIELDS`: Campos mínimos para listados (optimización con `only()`)
  - `DETAIL_FIELDS`: Campos ampliados para detalle
  - `qs_list()`: QuerySet optimizado para listados
  - `qs_detail()`: QuerySet optimizado para detalle
- **ViewSets DRF:** `apps/tenant/clientes/api/viewsets.py`
  - `ClienteViewSet`: CRUD completo con `IsTenantAdminOrReadOnly`
  - `@action(detail=False, methods=["post"], url_path="dt/clientes")`: DataTables endpoint (v2.40)
  - Serializers separados: `ClienteListSerializer`, `ClienteDetailSerializer`
  - Filtros: `tipo_persona`, `tipo_documento`, `segmento`, `activo`, `ciudad`
  - Búsqueda: `razon_social`, `numero_documento`, `nombre_comercial`, `email`
- **Permisos:** `IsTenantAdminOrReadOnly` - Lectura autenticados, escritura solo ADMIN/STAFF
- **Parser/Renderer:** `JSONParser`, `FormParser` (DataTables), `JSONRenderer`
**APIs REST:**
- `GET /api/v1/clientes/`: Listar clientes (paginado, filtros, búsqueda)
- `POST /api/v1/clientes/`: Crear cliente (solo ADMIN/STAFF)
- `GET /api/v1/clientes/{id}/`: Obtener detalle de cliente
- `PATCH /api/v1/clientes/{id}/`: Actualizar cliente (solo ADMIN/STAFF)
- `PUT /api/v1/clientes/{id}/`: Actualizar cliente completo (solo ADMIN/STAFF)
- `DELETE /api/v1/clientes/{id}/`: Eliminar cliente (solo ADMIN/STAFF)
- `POST /api/v1/clientes/dt/clientes/`: DataTables endpoint (v2.40 - @action)
**Frontend:**
- **Tabulator Factory:** Implementación con `TabulatorFactory.create()` (v2.40)
- **Lazy Loading:** `DOMUtils.onVisibleOnce('#tab-clientes', init)` (v2.40)
- **JavaScript:** `apps/tenant/core/static/core/js/clientes/clientes.page.js`
- **Columnas:** ID, Documento (tipo + número), Razón Social, Nombre Comercial, Email, Teléfono, Ciudad, Estado (badge), Acciones (Editar/Eliminar)
- **Búsqueda:** Input `#search-cliente` con debounce integrado
- **Modales:** Modal único `#modal-cliente` para crear/editar
- **CRUD Completo:** Crear, Editar, Eliminar (soft delete) con notificaciones `notyf`

#### 5. `apps.tenant.proveedores` ✅ IMPLEMENTADO (v2.40)
**Función:** Gestión de proveedores y compras
- Información legal y comercial de proveedores
- Gestión de compras y relaciones comerciales
- Alineado con normativa colombiana
- Service Layer Pattern: `qs_list()` y `qs_detail()` en `services.py`
**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios, admin y frontend Tabulator
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propios proveedores
**Modelos:**
- `Proveedor`: Información legal y comercial de proveedores
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **Índice**: `models.Index(fields=["empresa", "activo"])` en `Meta.indexes` (v2.40)
  - **Campos:** `tipo_persona`, `tipo_documento`, `numero_documento`, `digito_verificacion`, `razon_social`, `nombre_comercial`, `regimen_tributario`, `email_contacto`, `telefono_contacto`, `direccion`, `ciudad`, `activo`
  - **Constraint:** `UniqueConstraint(fields=["empresa", "tipo_documento", "numero_documento"])` (v2.40)
**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/proveedores/services.py`
  - `LIST_FIELDS`: Campos mínimos para listados (optimización con `only()`)
  - `DETAIL_FIELDS`: Campos ampliados para detalle
  - `qs_list(empresa_id, search=None)`: QuerySet optimizado para listados con búsqueda
  - `qs_detail(empresa_id, pk)`: QuerySet optimizado para detalle
  - `crear_proveedor(empresa, data)`: Crea proveedor con manejo de `IntegrityError` (duplicados)
  - `actualizar_proveedor(proveedor, data)`: Actualiza proveedor con manejo de `IntegrityError`
- **ViewSets DRF:** `apps/tenant/proveedores/api/viewsets.py`
  - `ProveedorViewSet`: CRUD completo con `GenericViewSet` + Mixins
  - `queryset = Proveedor.objects.none()` y `serializer_class = ProveedorDetailSerializer` (requerido por DRF router)
  - `pagination_class = StandardResultsSetPagination` (page_size=10)
  - `list()`: Soporta `?search=` (búsqueda en `razon_social`, `numero_documento`, `email_contacto`, `nombre_comercial`)
  - `destroy()`: Soft delete (marca `activo=False`)
- **Serializers:** `apps/tenant/proveedores/api/serializers.py`
  - `ProveedorListSerializer`: Campos mínimos + `*_display` para choices + `documento_completo`
  - `ProveedorDetailSerializer`: Campos completos para crear/editar
- **Permisos:** `IsTenantAdminOrReadOnly` (lectura autenticados, escritura solo ADMIN/STAFF)
**APIs REST:**
- `GET /api/v1/proveedores/`: Listar proveedores (paginado, filtros, búsqueda)
- `POST /api/v1/proveedores/`: Crear proveedor (solo ADMIN/STAFF)
- `GET /api/v1/proveedores/{id}/`: Obtener detalle de proveedor
- `PATCH /api/v1/proveedores/{id}/`: Actualizar proveedor parcialmente (solo ADMIN/STAFF)
- `PUT /api/v1/proveedores/{id}/`: Actualizar proveedor completo (solo ADMIN/STAFF)
- `DELETE /api/v1/proveedores/{id}/`: Eliminar proveedor (soft delete, solo ADMIN/STAFF)
**Frontend:**
- **Tabulator Factory:** Implementación con `TabulatorFactory.create()` (v2.40)
- **Lazy Loading:** `DOMUtils.onVisibleOnce('#tab-proveedores', init)` (v2.40)
- **JavaScript:** `apps/tenant/core/static/core/js/proveedores/proveedores.page.js`
- **Columnas:** ID, Documento (tipo + número completo con dígito verificación), Razón Social, Nombre Comercial, Email, Teléfono, Ciudad, Estado (badge), Acciones (Editar/Eliminar)
- **Búsqueda:** Input `#search-proveedor` con debounce integrado
- **Modales:** Modal único `#modal-proveedor` para crear/editar
- **CRUD Completo:** Crear, Editar, Eliminar (soft delete) con notificaciones `notyf`
- **Manejo de Errores:** Validación de duplicados (IntegrityError) con mensajes amigables
**Templates:**
- `apps/tenant/core/templates/tenant/core/partials/proveedores/list.html`: Shell estático con `#grid-proveedores`
- `apps/tenant/core/templates/tenant/core/partials/proveedores/modals.html`: Modal único para crear/editar
- `apps/tenant/core/templates/tenant/core/partials/proveedores/assets_proveedores.html`: Carga ordenada de JS (Factory antes del módulo)
**Limpieza Zero-Legacy (v2.40):**
- ✅ Eliminados: `forms.py`, `views.py`, `urls.py` (HTML views)
- ✅ Eliminados: `api/datatables.py`, `services/proveedor_service.py`, `services/__init__.py`
- ✅ Eliminados: Templates legacy (`create.html`, `edit.html`, `delete.html`)
- ✅ Eliminados: JS legacy (`proveedores.api.js`, `proveedores.dt.js`, `proveedores.modals.js`, `proveedores.ui.js`)
- ✅ Actualizados: Tests removieron referencias a `CompraProveedor` (modelo eliminado)

#### 6. `apps.tenant.empleados` ✅ IMPLEMENTADO (v2.40)
**Función:** Gestión de empleados y nómina
- Información de empleados y colaboradores
- Contratos laborales
- Gestión de nómina (pendiente)
- Service Layer Pattern: `qs_list()` y `qs_detail()` en `services.py`
**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios y admin
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propios empleados
**Modelos:**
- `Empleado`: Información de empleados
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **Índice**: `models.Index(fields=["empresa"])` en `Meta.indexes` (v2.40)
- `Contrato`: Contratos laborales
**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/empleados/services.py`
  - `LIST_FIELDS`, `DETAIL_FIELDS`, `qs_list()`, `qs_detail()`
- **ViewSets DRF:** `apps/tenant/empleados/api/viewsets.py`
  - `EmpleadoViewSet`, `ContratoViewSet`
  - `@action` para DataTables (v2.40 - deprecado `datatables.py` separado)
- **Permisos:** `IsTenantAdminOrReadOnly`
**APIs REST:**
- `GET /api/v1/empleados/empleados/`: Listar empleados
- `POST /api/v1/empleados/empleados/`: Crear empleado (solo ADMIN/STAFF)
- `GET /api/v1/empleados/empleados/{id}/`: Obtener detalle
- `PATCH /api/v1/empleados/empleados/{id}/`: Actualizar (solo ADMIN/STAFF)
- `DELETE /api/v1/empleados/empleados/{id}/`: Eliminar (solo ADMIN/STAFF)
- `POST /api/v1/empleados/empleados/dt/empleados/`: DataTables endpoint (v2.40 - @action)
- `GET/POST/PATCH/DELETE /api/v1/empleados/contratos/`: CRUD de contratos
**Frontend:**
- **Lazy Loading:** `DOMUtils.onVisibleOnce(TAB_CONTAINER_ID, init)` (v2.40)
- **JavaScript:** `apps/tenant/core/static/core/js/empleados/empleados.page.js`

#### 7. `apps.tenant.gastos` ✅ IMPLEMENTADO (v2.40 - Sistema de Documento Soporte Inmutable)
**Función:** Gestión de gastos operativos con sistema de Documento Soporte Inmutable según normativa DIAN colombiana (Art. 1.6.1.4.12 DR 1625 de 2016)
- **⚠️ ARQUITECTURA v2.40:** Sistema de evidencia legal inmutable
  - `DocumentoSoporte`: Evidencia legal inmutable (valores monetarios no editables)
  - `Gasto`: Clasificación contable (centro de costos/categoría)
  - `ResolucionDIAN`: Autorización DIAN con rango de números y vigencia
- Registro de gastos operativos con consecutivo único
- Integración con Document Ingest Pipeline (opcional)
- Service Layer Pattern: `qs_list()`, `qs_detail()`, `get_gastos_summary()` en `services.py`
**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios, admin y migraciones limpias
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propios gastos
**Modelos:**
- `ResolucionDIAN`: Resolución DIAN para Documentos Soporte
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - Campos: `numero_resolucion`, `prefijo`, `rango_desde`, `rango_hasta`, `fecha_resolucion`, `fecha_inicio`, `fecha_fin`, `vigente`
  - **⚠️ v2.40 - Sistema Automático**: 
    - `fecha_resolucion` actúa como `fecha_inicio` automáticamente (no se requiere campo separado en formulario)
    - Solo una resolución puede estar `vigente=True` por empresa (SSoT)
    - `save()` con `transaction.atomic` garantiza atomicidad
    - `obtener_siguiente_numero_soporte()` busca automáticamente la resolución vigente
  - **Índices**: `(empresa, vigente)`, `(prefijo, rango_desde, rango_hasta)`
  - **Validación**: `clean()` valida rango y que `fecha_fin >= fecha_resolucion`
  - **Método**: `esta_dentro_de_fecha(fecha_referencia=None)` verifica si una fecha está en el rango permitido
- `DocumentoSoporte`: Documento soporte inmutable (evidencia legal)
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **FK a ResolucionDIAN**: `resolucion_dian = ForeignKey(ResolucionDIAN, on_delete=PROTECT)`
  - **Consecutivo**: `consecutivo = IntegerField(editable=False, db_index=True)` - Generado automáticamente, único por resolución
  - Campos monetarios inmutables: `subtotal`, `retefuente`, `reteica`, `total`
  - Campos de proveedor (snapshot histórico): `vendedor_nit`, `vendedor_nombre`, `vendedor_razon_social`, `vendedor_direccion`, `vendedor_telefono`
  - Campos de documento: `prefijo`, `numero_factura_proveedor`, `fecha`, `adjunto` (FileField)
  - **Estado**: `anulado = BooleanField(default=False, db_index=True)`, `fecha_anulacion`
  - **Índices**: `(empresa, fecha)`, `(resolucion_dian, consecutivo)`, `(prefijo, consecutivo)`, `(vendedor_nit, numero_factura_proveedor)`, `(anulado)`
  - **Constraints**: 
    - `unique_ds_resolucion_consecutivo`: Único consecutivo por resolución (si no anulado)
    - `unique_ds_vendedor_factura`: Único vendedor+factura por empresa (si no anulado)
  - **Validación**: `clean()` valida total = subtotal - retefuente - reteica
  - **⚠️ REGLA DE ORO**: Una vez generado el consecutivo, los valores monetarios son INMUTABLES
- `Gasto`: Clasificación contable del documento soporte
  - **OneToOne a DocumentoSoporte**: `documento_soporte = OneToOneField(DocumentoSoporte, on_delete=PROTECT)`
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - Campos de clasificación: `centro_costo`, `categoria_contable`, `periodo`, `descripcion`, `observaciones`
  - **⚠️ Choices v2.40**: Campos con opciones predefinidas
    - `centro_costo`: `choices=CENTRO_COSTO_CHOICES` (21 opciones: Administrativos, Materia Prima, Mantenimiento, Viáticos, etc.)
    - `categoria_contable`: `choices=CATEGORIA_CONTABLE_CHOICES` (31 opciones: Arrendamientos, Servicios Públicos, Papelería, etc.)
    - **Ubicación choices**: `apps/tenant/gastos/choices/centros_costo.py` y `apps/tenant/gastos/choices/categoria_contable.py`
    - **Patrón**: Mismo formato que otros choices del proyecto (type hints, función helper `get_*_choices()`)
  - **Properties delegadas**: `subtotal`, `retefuente`, `reteica`, `total`, `fecha`, `numero_documento` (delegan a `documento_soporte`)
  - **Categorías eliminadas**: 'SALARIO', 'APORTE_SALUD', 'APORTE_PENSION', 'APORTE_ARL', 'APORTE_CAJA', 'PERSONAL' (v2.40)
**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/gastos/services.py`
  - `qs_list()`: QuerySet optimizado para listados con `select_related('documento_soporte')`
  - `qs_detail()`: QuerySet optimizado para detalle con `select_related('documento_soporte', 'empresa')`
  - `get_gastos_summary(empresa_id)`: Resumen agregado (subtotal_neto, retefuente_neto, reteica_neto, retenciones_neto, total_neto, cantidad)
    - **⚠️ v2.40**: Excluye gastos anulados (`anulado=False`)
    - Campos agregados: `subtotal`, `retefuente`, `reteica`, `total` desde `DocumentoSoporte`
  - `obtener_resolucion_vigente(empresa)`: Obtiene la resolución DIAN vigente para una empresa (SSoT)
  - `obtener_siguiente_numero_soporte(empresa)`: Genera consecutivo único formato "DS-0000X" (atómico)
    - **⚠️ v2.40**: Busca automáticamente la resolución vigente (no requiere parámetro `resolucion`)
    - Valida que la resolución esté vigente y dentro de fecha usando `esta_dentro_de_fecha()`
  - `normalize_document_number(value)`: Normaliza NITs y números de documento
  - `anular_gasto_service(gasto_id)`: Anula un gasto (marca `anulado=True`, registra `fecha_anulacion`, atómico)
  - `materializar_gasto_desde_dto()`: Materialización desde Document Ingest Pipeline
- **ViewSets DRF:** `apps/tenant/gastos/api/viewsets.py`
  - `GastoViewSet`: ViewSet principal con `queryset = Gasto.objects.select_related("documento_soporte", "empresa").all()`
  - `@action(detail=False, methods=["get"], url_path="summary")`: Resumen de gastos netos
  - `@action(detail=False, methods=["get"], url_path="resolucion-activa")`: Obtiene la resolución DIAN vigente (retorna 404 si no existe)
  - `@action(detail=False, methods=["post"], url_path="configurar-resolucion")`: Crea o actualiza resolución DIAN como vigente
  - `@action(detail=False, methods=["get"], url_path="resoluciones")`: Resoluciones DIAN activas (deprecado, usar `resolucion-activa`)
  - `@action` para DataTables (v2.40 - deprecado `datatables.py` separado)
  - `POST /api/v1/gastos/create-from-dto/`: Endpoint para persistir desde DTO
  - **⚠️ v2.40 - Creación Automática**: `create()` usa automáticamente la resolución vigente sin requerir selección manual
  - **Filtros**: `filterset_fields = ['periodo', 'categoria_contable', 'centro_costo']` (permite filtrado exacto por choices)
  - **Búsqueda**: `search_fields = ['documento_soporte__vendedor_nombre', 'descripcion']`
  - **Ordenamiento**: `ordering_fields = ['documento_soporte__fecha', 'documento_soporte__total']`
- **Serializers:** `apps/tenant/gastos/api/serializers.py`
  - `ResolucionDIANNestedSerializer`: Serializer para ResolucionDIAN con campos de fecha explícitos (`DateField` para evitar errores `utcoffset`)
  - `DocumentoSoporteDetailSerializer`: Serializer completo con `fecha` como `DateField` explícito
  - `GastoListSerializer`: Serializer para listados con campos aplanados (`ds_consecutivo`, `ds_prefijo`, etc.)
    - **⚠️ v2.40 - Campos Display**: Incluye `centro_costo_display` y `categoria_contable_display` (texto legible de choices)
    - Campos: `id`, `categoria_contable`, `categoria_contable_display`, `centro_costo`, `centro_costo_display`, `ds_*`
  - `GastoDetailSerializer`: Serializer de detalle completo
    - **⚠️ v2.40 - Campos Display**: Incluye `centro_costo_display` y `categoria_contable_display`
  - **Optimización**: Excluye `adjunto` (FileField) para reducir payload JSON
  - **⚠️ CORRECCIÓN v2.40**: Todos los campos de fecha explícitamente declarados como `DateField` o `DateTimeField` según corresponda
- **Permisos:** `IsTenantAdminOrReadOnly`
**APIs REST:**
- `GET /api/v1/gastos/`: Listar gastos (serializer optimizado con campos display)
- `POST /api/v1/gastos/`: Crear gasto (solo ADMIN/STAFF) - ⚠️ Usa automáticamente resolución vigente
- `GET /api/v1/gastos/{id}/`: Obtener detalle (incluye campos display)
- `POST /api/v1/gastos/{id}/anular/`: Anular gasto (marca `anulado=True`, inmutable)
- `DELETE /api/v1/gastos/{id}/`: Eliminar (solo ADMIN/STAFF)
- `GET /api/v1/gastos/summary/`: Resumen agregado de gastos netos (excluye anulados)
- `GET /api/v1/gastos/resolucion-activa/`: Obtiene la resolución DIAN vigente (retorna 404 si no existe)
- `POST /api/v1/gastos/configurar-resolucion/`: Crea o actualiza resolución DIAN como vigente
- `GET /api/v1/gastos/resoluciones/`: Resoluciones DIAN activas (deprecado, usar `resolucion-activa`)
- `POST /api/v1/gastos/dt/gastos/`: DataTables endpoint (v2.40 - @action)
- `POST /api/v1/gastos/create-from-dto/`: Crear desde DTO (Document Ingest Pipeline)
**Frontend:**
- **Lazy Loading:** `DOMUtils.onVisibleOnce(TAB_CONTAINER_ID, init)` (v2.40)
- **JavaScript:** `apps/tenant/core/static/core/js/gastos/gastos.page.js`
  - **DataTables**: Columnas optimizadas (Documento, Fecha, Vendedor, Categoría, Centro Costo, Total, Estado)
    - **⚠️ v2.40 - Visualización Display**: Usa `categoria_contable_display` y `centro_costo_display` (texto legible)
    - Renderizado con fallback: muestra display si está disponible, sino código, sino '---'
  - **Panel de Finanzas**: Muestra subtotal_neto, retefuente_neto, reteica_neto, retenciones_neto, total_neto
  - **Validación Resolución**: Al crear gasto, valida resolución activa; si no existe, abre modal de configuración
  - **API_URL**: `/api/v1/gastos/`
  - **APIs**: `gastosAPI.getResolucionActiva()`, `gastosAPI.setConfigResolucion()`
- **Templates:** `apps/tenant/core/templates/tenant/core/partials/gastos/list.html`
  - Botón "Configurar Resolución" para gestionar resolución DIAN
- **Modals:** `apps/tenant/core/templates/tenant/core/partials/gastos/modals.html`
  - **Modal Crear Gasto**: 
    - Campo `categoria_contable`: `<select>` con 31 opciones predefinidas
    - Campo `centro_costo`: `<select>` con 21 opciones predefinidas (opcional)
    - Campo `resolucion_dian`: `readonly` (se usa automáticamente la vigente)
  - **Modal Configurar Resolución**: 
    - Campos: `numero_resolucion`, `prefijo`, `rango_desde`, `rango_hasta`, `fecha_resolucion`, `fecha_fin`, `clave_tecnica`, `vigente`
    - Muestra resolución guardada con detalles antes de cerrar
**Sistema de Choices (v2.40):**
- **Ubicación**: `apps/tenant/gastos/choices/`
- **Archivos**:
  - `centros_costo.py`: Define `CENTRO_COSTO_CHOICES` (21 opciones) y `get_centro_costo_choices()`
  - `categoria_contable.py`: Define `CATEGORIA_CONTABLE_CHOICES` (31 opciones) y `get_categoria_contable_choices()`
  - `__init__.py`: Exporta todos los choices del módulo
- **Patrón**: Mismo formato que otros choices del proyecto (`apps/public/impuestos/choices/`, `apps/tenant/empresa/choices/`)
  - Type hints: `List[Tuple[str, str]]`
  - Función helper: `get_*_choices()` para acceso dinámico
  - Documentación: Docstrings explicativos
- **Uso en Modelos**: `choices=CENTRO_COSTO_CHOICES` y `choices=CATEGORIA_CONTABLE_CHOICES`
- **Uso en Serializers**: Campos `*_display` usando `source='get_*_display'` para texto legible
- **Uso en Frontend**: 
  - HTML: `<select>` con opciones predefinidas
  - JavaScript: Visualización de valores `*_display` en DataTables

**Migraciones:**
- **Migración inicial**: `apps/tenant/gastos/migrations/0001_initial.py`
  - Crea modelos: `ResolucionDIAN`, `DocumentoSoporte`, `Gasto`
  - Crea índices y constraints únicos
  - **Dependencia**: `empresa.0009_remove_empresa_actividad_economica_and_more`
- **Migración 0002**: Agrega campo `fecha_fin` a `ResolucionDIAN`
- **Migración 0003**: Agrega campo `fecha_inicio` y ajusta campos de `ResolucionDIAN`
- **Migración 0004**: Migración de datos para asegurar solo una resolución vigente por empresa
- **⚠️ Nota**: Los choices no requieren migración (son validación a nivel de Django, no afectan esquema de BD)
- **Comandos de Management:**
  - `python manage.py reset_migrations_history tenant_gastos`: Resetea historial de migraciones en todos los esquemas
  - `python manage.py migrate_schemas --tenant tenant_gastos`: Aplica migraciones a todos los tenants
- **Scripts de Utilidad:**
  - `scripts/reset_gastos_migrations.py`: Script para resetear historial de migraciones (local)
  - `scripts/drop_old_gastos_tables.py`: Elimina tablas antiguas antes de aplicar nueva migración
  - `scripts/check_gastos_tables.py`: Verifica existencia de tablas en todos los esquemas
**Normativa:**
- **Base Legal**: Art. 1.6.1.4.12 del Decreto Reglamentario 1625 de 2016 (DIAN Colombia)
- **Inmutabilidad**: Los valores monetarios del Documento Soporte son inmutables una vez generado el consecutivo
- **Consecutivo**: Formato "DS-0000X" generado automáticamente y único por resolución DIAN
- **Anulación**: Los documentos pueden anularse (campo `anulado=True`) pero no editarse

#### 8. `apps.tenant.inventario` ✅ IMPLEMENTADO (v2.40) - Arquitectura Standalone + Tabulator Factory

**Función:** Gestión de inventario y activos
- Catálogo de productos, servicios, activos fijos y categorías
- Control de stock con Kardex (movimientos de inventario)
- Integración con Document Ingest Pipeline (opcional)
- Service Layer Pattern: `qs_list()` y `qs_detail()` en `services.py`
- **⚠️ ARQUITECTURA STANDALONE:** Todos los módulos son completamente independientes

**Estado:** ✅ Completamente funcional con Tabulator Factory v2.40 y arquitectura standalone

**Esquema:** `tenant_<schema_name>`

**Aislamiento:** Cada tenant tiene su propio inventario (SSoT con `empresa = ForeignKey`)

**⚠️ ARQUITECTURA STANDALONE (v2.40):**
- **Categorías**: Módulo completamente independiente, no depende de otros módulos
- **Productos**: Módulo completamente independiente, no depende de otros módulos
- **Servicios**: Módulo completamente independiente, no depende de otros módulos
- **Activos Fijos**: Módulo completamente independiente, no depende de otros módulos
- **Comunicación**: Los módulos se comunican mediante eventos personalizados (`categorias:updated`)
- **APIs**: Cada módulo expone su propia API global (`window.categoriasPage`, `window.InventarioProductosModule`, etc.)

**Modelos:**
- `Producto`: Productos tangibles con stock
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **FK a CategoriaItem**: `categoria = ForeignKey(CategoriaItem, null=True, blank=True, on_delete=PROTECT)`
    - **⚠️ Categoría opcional**: Los productos pueden tener o no categoría asignada
  - **Índice**: `models.Index(fields=["empresa", "nombre"])` en `Meta.indexes`
- `Servicio`: Servicios intangibles
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **FK a CategoriaItem**: `categoria = ForeignKey(CategoriaItem, null=True, blank=True, on_delete=PROTECT)`
    - **⚠️ Categoría opcional**: Los servicios pueden tener o no categoría asignada
- `ActivoFijo`: Activos fijos de la empresa
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
  - **FK a CategoriaItem**: `categoria = ForeignKey(CategoriaItem, null=True, blank=True, on_delete=SET_NULL)`
    - **⚠️ Categoría opcional**: Los activos pueden tener o no categoría asignada
  - **Índice**: `models.Index(fields=["empresa"])` en `Meta.indexes`
- `CategoriaItem`: Categorías maestras (Producto, Servicio, Activo, TODO)
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=PROTECT)` (SSoT)
- `MovimientoInventario`: Historial de movimientos (Kardex) - Inmutable
  - **FK a Producto**: `producto = ForeignKey(Producto, on_delete=CASCADE)`
    - **⚠️ CASCADE**: Al eliminar un producto, se eliminan automáticamente todos sus movimientos
- `HistorialServicio`: Historial de ventas de servicios
  - **FK a Servicio**: `servicio = ForeignKey(Servicio, on_delete=CASCADE)`
    - **⚠️ CASCADE**: Al eliminar un servicio, se eliminan automáticamente todos sus historiales

**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/inventario/services.py` (SSoT)
  - `LIST_FIELDS`, `DETAIL_FIELDS` para cada modelo
  - `qs_producto_list()`, `qs_servicio_list()`, `qs_activo_list()`, `qs_movimiento_list()`, `qs_categoria_list()`
  - `materializar_inventario_desde_dto()`: Materialización desde Document Ingest Pipeline
  - `recalcular_stock_producto()`: Recalcula stock basado en movimientos
  - `registrar_movimiento()`: Registra movimiento y recalcula stock automáticamente
- **ViewSets DRF:** `apps/tenant/inventario/api/viewsets.py`
  - `ProductoViewSet`, `ServicioViewSet`, `ActivoFijoViewSet`, `MovimientoInventarioViewSet`, `CategoriaItemViewSet`
  - `@action(detail=False, methods=["get", "post"], url_path="dt")` para Server-Side DataTables (legacy)
  - `@action(detail=True, methods=["get"], url_path="kardex")` en `ProductoViewSet` para historial de movimientos
  - `@action(detail=True, methods=["get"], url_path="resumen")` en `CategoriaItemViewSet` para conteo de ítems asociados
  - **⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN (Inactivar antes de Borrar):**
    - **Productos**: Solo se puede eliminar si está inactivo. Al eliminar, se eliminan automáticamente stock y todos los movimientos de kardex (CASCADE)
    - **Servicios**: Solo se puede eliminar si está inactivo. Al eliminar, se eliminan automáticamente todos los historiales de ventas (CASCADE)
    - **Categorías**: Solo se puede eliminar si está inactiva. Al eliminar, los productos/servicios/activos asociados quedan sin categoría (null)
- **Permisos:** `IsTenantAdminOrReadOnly`

**APIs REST - Tabulator Factory (v2.40):**
- `GET /api/v1/inventario/productos/`: Listado paginado para Tabulator (StandardResultsSetPagination)
- `GET /api/v1/inventario/servicios/`: Listado paginado para Tabulator (StandardResultsSetPagination)
- `GET /api/v1/inventario/activos/`: Listado paginado para Tabulator (StandardResultsSetPagination)
- `GET /api/v1/inventario/categorias/`: Listado paginado para Tabulator (StandardResultsSetPagination)
- `GET /api/v1/inventario/movimientos/`: Listado paginado para Tabulator (StandardResultsSetPagination)

**APIs REST - Server-Side DataTables (Legacy - Deprecated):**
- `POST /api/v1/inventario/productos/dt/`: DataTables server-side para Productos (legacy)
- `POST /api/v1/inventario/servicios/dt/`: DataTables server-side para Servicios (legacy)
- `POST /api/v1/inventario/activos/dt/`: DataTables server-side para Activos Fijos (legacy)
- `POST /api/v1/inventario/movimientos/dt/`: DataTables server-side para Kardex (legacy)

**APIs REST - CRUD Estándar:**
- `GET /api/v1/inventario/productos/`: Listar productos
- `POST /api/v1/inventario/productos/`: Crear producto
- `GET /api/v1/inventario/productos/{id}/`: Obtener detalle
- `PATCH /api/v1/inventario/productos/{id}/`: Actualizar producto
- `DELETE /api/v1/inventario/productos/{id}/`: Eliminar producto
- `GET /api/v1/inventario/productos/{id}/kardex/`: Obtener historial de movimientos (Kardex)
- (Mismos endpoints para `servicios/`, `activos/`, `categorias/`, `movimientos/`)

**Frontend - Arquitectura Standalone con Tabulator Factory (v2.40):**

**⚠️ MÓDULOS STANDALONE:**
- Cada módulo es completamente independiente y no depende de otros módulos del inventario
- Comunicación mediante eventos personalizados (`categorias:updated`)
- Cada módulo expone su propia API global

**Módulos Standalone:**
- **`categorias.page.js`**: Módulo standalone para gestión de categorías
  - API global: `window.categoriasPage` (`refresh()`, `ver()`, `editar()`, `eliminar()`)
  - Evento: `categorias:updated` (notifica cambios a otros módulos)
  - Tabulator Factory con paginación estándar
  - Al eliminar: los ítems asociados quedan sin categoría (null)
- **`productos.page.js`**: Módulo standalone para gestión de productos
  - API global: `window.InventarioProductosModule` (`refresh()`, `editar()`, `eliminar()`, `verKardex()`)
  - Tabulator Factory con paginación estándar
  - Al eliminar: se eliminan producto, stock y todos los movimientos de kardex (CASCADE)
- **`servicios.page.js`**: Módulo standalone para gestión de servicios
  - API global: `window.InventarioServiciosModule` (funciones expuestas)
  - Tabulator Factory con paginación estándar
  - Al eliminar: se eliminan servicio y todos los historiales de ventas (CASCADE)
- **`activos.page.js`**: Módulo standalone para gestión de activos fijos
  - Tabulator Factory con paginación estándar
- **`movimientos.page.js`**: Módulo standalone para gestión de movimientos (Kardex)
  - Tabulator Factory con paginación estándar

**Carga Inmediata de Tablas (v2.40):**
- **Lazy Loading**: `DOMUtils.onVisibleOnce` para inicialización diferida
- **Listeners directos a tabs**: Evento `shown.bs.tab` de Bootstrap para redraw
- **Tabs con carga inmediata**: `#inventario-productos-tab`, `#inventario-servicios-tab`, `#inventario-activos-tab`, `#inventario-movimientos-tab`, `#inventario-categorias-tab`
- **Patrón**: Verificar estado antes de cargar, evitar recargas innecesarias

**Archivos JavaScript:**
- `categorias.page.js`: Módulo standalone con Tabulator Factory
- `productos.page.js`: Módulo standalone con Tabulator Factory
- `servicios.page.js`: Módulo standalone con Tabulator Factory
- `activos.page.js`: Módulo standalone con Tabulator Factory
- `movimientos.page.js`: Módulo standalone con Tabulator Factory
- `inventario.api.js`: API client centralizado (usado por todos los módulos)

**Modales Funcionales:**
- **Categorías**: Crear/editar categorías con validación
- **Productos**: Crear/editar productos con carga dinámica de categorías, validación y Kardex
- **Servicios**: Crear/editar servicios con carga dinámica de categorías y validación
- **Activos Fijos**: Crear/editar activos con carga dinámica de categorías y validación
- **Movimientos**: Registrar movimientos de inventario con carga dinámica de productos y validación

**Patrón de Implementación Server-Side:**

```python
# Backend: ViewSet con @action usando DataTableServer
@action(detail=False, methods=["get", "post"], url_path="dt")
def datatables(self, request):
    from apps.shared.datatable import DataTableSpec, DataTableServer
    from apps.tenant.inventario.services import qs_producto_list
    from apps.tenant.inventario.api.serializers import ProductoListSerializer
    
    qs_base = qs_producto_list()
    empresa = Empresa.objects.first()
    if empresa:
        qs_base = qs_base.filter(empresa=empresa)
    
    spec = DataTableSpec(
        fields_map={0: 'codigo', 1: 'nombre', 2: 'categoria__nombre', ...},
        search_fields=['codigo', 'nombre', 'categoria__nombre'],
        base_qs=qs_base,
        serializer=ProductoListSerializer,
        extra_filter=lambda req, qs: qs
    )
    
    dt_server = DataTableServer(spec)
    return dt_server.handle(request)
```

```javascript
// Frontend: Carga inmediata al hacer clic en tab
const serviciosTab = document.getElementById('inventario-servicios-tab');
if (serviciosTab) {
    serviciosTab.addEventListener('shown.bs.tab', async function() {
        if (!state.servicios.initialized || !state.servicios.table) {
            await initServiciosTable();
        }
    });
}

// Función genérica para inicializar tablas Server-Side
async function initTableServerSide(config) {
    const { tableId, endpoint, columns } = config;
    const ajaxUrl = await endpoint();
    
    const dtConfig = {
        serverSide: true,
        processing: true,
        ajax: {
            url: ajaxUrl,
            type: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') || '' }
        },
        columns: columns,
        // ... configuración adicional
    };
    
    return DataTablesUtils.initOrUpdateDataTable(tableEl, dtConfig);
}
```

**Comportamiento de Eliminación (v2.40):**
- **Productos**: 
  - Validación: Solo se puede eliminar si está inactivo
  - Eliminación automática: Stock y todos los movimientos de kardex (CASCADE)
  - Sin validación de stock: Se puede eliminar incluso con stock disponible
- **Servicios**:
  - Validación: Solo se puede eliminar si está inactivo
  - Eliminación automática: Todos los historiales de ventas (CASCADE)
- **Categorías**:
  - Validación: Solo se puede eliminar si está inactiva
  - Comportamiento: Los productos/servicios/activos asociados quedan sin categoría (null)
  - Los ítems pueden tener o no categoría asignada (null=True en modelos)

**Correcciones Aplicadas (v2.40):**
- Eliminación de duplicaciones en `inventario.api.js` (había dos definiciones de `movimientos` y `activos`)
- Corrección de modales: Botones submit correctos (`type="submit"`), validación robusta, manejo de errores
- Alineación de `fields_map` en backend con columnas del frontend
- Sincronización de modales con tablas: Refresh correcto después de guardar
- **Migración completa a Tabulator Factory**: Todos los módulos usan TabulatorFactory con paginación estándar
- **Arquitectura Standalone**: Todos los módulos son completamente independientes
- **Categorías opcionales**: Productos, servicios y activos pueden tener o no categoría asignada
- **CASCADE en relaciones**: Movimientos e historiales se eliminan automáticamente al eliminar producto/servicio

#### 9. `apps.tenant.perfil` ✅ IMPLEMENTADO
**Función:** Perfil privado del colaborador (por tenant)
- Datos específicos del usuario dentro del tenant (cargo, departamento, teléfono corporativo)
- Avatar del colaborador
- Configuración de UI (preferencias) almacenada en JSONField
- Relación OneToOneField con User global (sin "contaminar" el modelo de usuario)
**Estado:** ✅ Implementado con modelo, servicio, serializers, viewsets, admin y tests
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propios perfiles de colaboradores
**Modelos:**
- `TenantProfile`: Perfil del colaborador con cargo, departamento, teléfono corporativo, avatar, configuración
**APIs REST:**
- `GET /api/v1/perfil/perfiles/me/`: Obtener perfil del usuario actual
- `PATCH /api/v1/perfil/perfiles/me/`: Actualizar perfil del usuario actual
- `PATCH /api/v1/perfil/perfiles/me/configuracion/`: Actualizar configuración de UI
**Servicios:**
- `obtener_o_crear_perfil(user, defaults=None)`: Obtiene o crea el perfil del usuario
- `actualizar_configuracion_ui(user, clave, valor, merge=True)`: Actualiza configuración de forma segura
**Ubicación:** `apps/tenant/perfil/`, `apps/services/perfil/perfil_service.py`

#### 10. `apps.tenant.cotizaciones` ✅ IMPLEMENTADO (v2.60)
**Función:** Gestión de cotizaciones comerciales con sistema de perfiles de configuración y numeración automática
- Creación, edición, visualización y eliminación de cotizaciones
- Sistema de perfiles de configuración múltiples (CRUD completo)
- Numeración automática por perfil (prefijo, semilla, sufijo)
- Editor estilo Excel con Tabulator
- Inmutabilidad de cotizaciones aceptadas
- DNA Dinámico: Estructura de secciones basada en plantillas
- AIU (Administración, Imprevistos, Utilidad) opcional por cotización
- Service Layer Pattern: `crear_preforma()`, `recalcular_totales()`, `_generar_numero_cotizacion()`
**Estado:** ✅ Implementado con modelos, serializers, viewsets, servicios, admin y frontend Tabulator
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propias cotizaciones (SSoT con `empresa = ForeignKey`)
**Modelos:**
- `Cotizacion`: Cabecera de cotización
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=CASCADE)` (SSoT)
  - **FK a Cliente**: `cliente = ForeignKey('tenant_clientes.Cliente', on_delete=SET_NULL, null=True, blank=True)`
    - **⚠️ v2.60**: Cliente es obligatorio. Campo `cliente_nombre_manual` eliminado completamente.
  - **FK a ConfiguracionCotizacion**: `configuracion = ForeignKey('ConfiguracionCotizacion', on_delete=SET_NULL, null=True, blank=True)`
  - **UUID**: `uuid = UUIDField(default=uuid.uuid4, editable=False, unique=True)` (lookup por UUID)
  - **Número**: `numero_cotizacion = CharField(max_length=50)` - Generado automáticamente desde perfil
  - **Constraint**: `UniqueConstraint(fields=['empresa', 'configuracion', 'numero_cotizacion'])` (v2.60)
  - **Estado**: `estado = CharField(choices=Estado.choices, default='BORRADOR')` - BORRADOR, ENVIADA, ACEPTADA
  - **DNA Financiero**: `porcentaje_aiu_admin`, `porcentaje_aiu_imprevistos`, `porcentaje_aiu_utilidad`, `iva_porcentaje`, `total_con_impuestos`
  - **Fechas**: `fecha_emision = DateField(auto_now_add=True)`, `fecha_vencimiento = DateField()`
  - **Tipo**: `tipo_cotizacion = CharField(max_length=20, default='MIXTO')` - PRODUCTOS, SERVICIOS, MATERIALES, MIXTO
- `CotizacionItem`: Items de cotización
  - **FK a Cotizacion**: `cotizacion = ForeignKey(Cotizacion, related_name='items', on_delete=CASCADE)`
  - **Tipo Item**: `tipo_item = CharField(choices=TipoItem.choices)` - PRODUCTO, MATERIAL, SERVICIO
  - **Referencias Opcionales**: `producto = ForeignKey(Producto, null=True, blank=True)`, `servicio = ForeignKey(Servicio, null=True, blank=True)`
  - **Snapshot (Inmutable)**: `descripcion`, `marca`, `referencia`, `unidad` - Datos reales impresos
  - **Cálculos**: `cantidad`, `costo_unitario`, `porcentaje_utilidad`, `precio_unitario_venta`, `subtotal_linea`
  - **Orden**: `orden = PositiveIntegerField(default=0)` - Mantiene secuencia de items
- `Producto`: Catálogo de productos (interno al módulo)
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=CASCADE)` (SSoT)
  - Campos: `codigo`, `nombre`, `marca`, `referencia`, `unidad`, `precio_venta`, `activo`
- `Servicio`: Catálogo de servicios (interno al módulo)
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=CASCADE)` (SSoT)
  - Campos: `nombre`, `precio_venta`, `activo`
- `ConfiguracionCotizacion`: Perfiles de configuración (DNA Dinámico)
  - **FK a Empresa**: `empresa = ForeignKey(Empresa, on_delete=CASCADE)` (SSoT)
  - **Gestión de Perfiles**: `nombre_configuracion`, `tipo_plantilla`, `es_activo`
  - **DNA Financiero**: `iva_porcentaje_default`, `porcentaje_utilidad_default`
  - **AIU Opcional**: `usa_aiu = BooleanField(default=False)`, `aiu_admin_default`, `aiu_imprevistos_default`, `aiu_utilidad_default`
  - **Numeración**: `prefijo_secuencia`, `semilla_inicial`, `sufijo_secuencia`, `ultimo_numero`
**Arquitectura API-First:**
- **Service Layer:** `apps/tenant/cotizaciones/services.py`
  - `crear_preforma(empresa, datos)`: Crea cotización con DNA del perfil (IVA, AIU, numeración automática)
  - `_generar_numero_cotizacion(plantilla)`: Genera número automático usando `select_for_update()` (atómico)
  - `recalcular_totales(cotizacion)`: Recalcula totales desde items
  - `calcular_linea(cantidad, costo, utilidad)`: Cálculo estandarizado para Tabulator y Models
- **ViewSets DRF:** `apps/tenant/cotizaciones/api/viewsets.py`
  - `CotizacionViewSet`: CRUD completo con `BaseTenantViewSet`, lookup por UUID
  - `get_queryset()`: Filtra por empresa (SSoT), búsqueda en `numero_cotizacion` y `cliente__razon_social`
  - `create()`: Usa `CotizacionService.crear_preforma()` para generación automática de número
  - `@action(detail=True, methods=['post'])`: `recalcular()` - Recalcula totales
  - `CotizacionItemViewSet`: CRUD de items con recálculo automático de totales
- **ViewSets Configuración:** `apps/tenant/cotizaciones/configuracion/viewsets.py`
  - `ConfiguracionCotizacionViewSet`: CRUD completo de perfiles de configuración
  - `get_queryset()`: Filtra por empresa (SSoT), búsqueda en `nombre_configuracion`
  - `perform_create()`: Asigna empresa automáticamente (SSoT)
  - `@action(detail=True, methods=['post'])`: `activar()` - Activa perfil y desactiva otros
- **Serializers:** `apps/tenant/cotizaciones/api/serializers.py`
  - `CotizacionSerializer`: Serializer principal con `cliente_display` (read_only)
  - **⚠️ v2.60**: Campo `cliente_nombre_manual` eliminado completamente
  - `get_cliente_display()`: Muestra `cliente.razon_social` o "Cliente no especificado"
  - `create()`: Valida que `cliente` (ID) esté presente, ignora `cliente_nombre_manual` si existe
  - `CotizacionItemSerializer`: Serializer de items con campos snapshot y calculados
- **Serializers Configuración:** `apps/tenant/cotizaciones/configuracion/serializers.py`
  - `ConfiguracionCotizacionSerializer`: Serializer completo con validación Zero Trust
  - `ConfiguracionCotizacionListSerializer`: Serializer ligero para listados
  - `empresa`: `read_only=True` (SSoT - se asigna automáticamente)
- **Permisos:** `IsTenantMember` (lectura), `IsTenantAdminOrReadOnly` (escritura)
**APIs REST:**
- `GET /api/v1/cotizaciones/`: Lista paginada (Tabulator Factory v2.40)
- `POST /api/v1/cotizaciones/`: Crear cotización (genera número automáticamente)
- `GET /api/v1/cotizaciones/{uuid}/`: Detalle por UUID
- `PATCH /api/v1/cotizaciones/{uuid}/`: Actualizar (solo si no ACEPTADA)
- `DELETE /api/v1/cotizaciones/{uuid}/`: Eliminar (solo si no ACEPTADA)
- `POST /api/v1/cotizaciones/{uuid}/recalcular/`: Recalcular totales
- `GET /api/v1/cotizaciones/configuracion/`: Lista de perfiles de configuración
- `POST /api/v1/cotizaciones/configuracion/`: Crear perfil de configuración
- `GET /api/v1/cotizaciones/configuracion/{id}/`: Detalle de perfil
- `PATCH /api/v1/cotizaciones/configuracion/{id}/`: Actualizar perfil
- `POST /api/v1/cotizaciones/configuracion/{id}/activar/`: Activar perfil
- `DELETE /api/v1/cotizaciones/configuracion/{id}/`: Eliminar perfil
**Frontend:**
- **Tabulator Factory:** Implementación con `TabulatorFactory.create()` (v2.40)
- **JavaScript Principal:** `apps/tenant/core/static/core/js/cotizaciones/cotizaciones.page.js`
  - Tabla principal de cotizaciones con columnas: `numero`, `fecha`, `cliente`, `total`, `estado`, `vencimiento`, `acciones`
  - Tabla secundaria de perfiles de configuración (colapsable)
  - Búsqueda en tiempo real
  - Acciones: Ver, Editar, Eliminar, Convertir a Factura
- **JavaScript Modales:** `apps/tenant/core/static/core/js/cotizaciones/cotizacion_modals.js`
  - `showCreate()`: Modal de creación con carga dinámica de clientes y perfiles
  - `cargarClientesEnSelect()`: Carga clientes activos desde API
  - `cargarPerfilesEnSelect()`: Carga perfiles activos desde API
  - `showEdit()`, `showDetail()`: Modales de edición y detalle
- **Templates:** `apps/tenant/core/templates/tenant/core/partials/cotizaciones/`
  - `list.html`: Vista principal con tabla de cotizaciones y tabla de configuraciones (colapsable)
  - `modals.html`: Modales de creación, edición, detalle y configuración de parámetros
**Reglas de Negocio:**
- **Cliente Obligatorio**: Todas las cotizaciones deben tener un cliente de la base de datos
- **Numeración Automática**: El número se genera automáticamente desde el perfil seleccionado
- **Inmutabilidad**: Cotizaciones con estado `ACEPTADA` son completamente inmutables
- **SSoT (Single Source of Truth)**: La empresa se obtiene del tenant (singleton), nunca del payload
- **DNA Inheritance**: Los valores del perfil (IVA, AIU) se copian a la cotización para integridad histórica
- **Folios Dinámicos**: Cada perfil tiene su propia secuencia independiente (prefijo, semilla, sufijo)
**Migraciones:**
- `0005_remove_cotizacion_cliente_nombre_manual.py`: Eliminación del campo `cliente_nombre_manual` (v2.60)
**Referencias:**
- **Documentación Detallada**: `documentacion/COTIZACIONES_REFACTOR_v2.60.md`
- **Configuración y Numeración**: `documentacion/COTIZACIONES_CONFIGURACION_Y_NUMERACION.md`
- **Editor Estilo Excel**: `documentacion/COTIZACIONES_EDITOR_V2.40.md`
- **Estructura Funcional**: `documentacion/INFORME_ESTRUCTURA_FUNCIONAL_COTIZACIONES.md`

#### 5. `apps.tenant.core` ✅ IMPLEMENTADO - Core API Centralizada
**Función:** Core API para composición y orquestación de datos de TENANT_APPS
- **⚠️ POLÍTICA:** Centralización de toda la lógica de presentación/orquestación
- **⚠️ NO duplica lógica:** Solo compone datos de apps dueñas (empresa, facturas, contabilidad, perfil)
- **⚠️ API-First:** Endpoints JSON para presentación, sin HTML dinámico
- **⚠️ Branding dinámico:** Sin hardcodes de marca, todo desde BD
- **Manejadores de error:** 404 y 403 personalizados con branding dinámico
- **Templates base:** Base templates y partials reutilizables para tenant
- **Templatetags:** Tags para branding dinámico en templates

**Estructura:**
```
apps/tenant/core/
├── api/
│   ├── handlers.py      # Manejadores de error (404, 403) con branding dinámico
│   ├── serializers.py   # Serializers compuestos (sin hardcodes)
│   ├── urls.py          # URLs de Core API (/api/v1/core/...)
│   └── views.py         # ViewSets que usan servicios (sin queries directas)
├── services/
│   └── orchestration.py # Orquestación de datos (único lugar con queries)
├── branding.py          # Branding dinámico desde BD (get_tenant_branding)
├── templatetags/
│   └── tenant_branding.py # Tags para templates ({% tenant_branding_name %})
└── templates/
    ├── tenant/
    │   ├── base.html    # Template base para tenant
    │   ├── partials/    # Partials reutilizables (_header, _footer, _branding_header)
    │   └── errors/      # Templates de error (403, 404) con branding
```

**Estructura de Servicios Core (v2.30):**
- `apps/tenant/core/services/auth_service.py`: SSoT de autenticación (login, logout, password-reset)
- `apps/tenant/core/services/landing_adapter.py`: Adaptador que consume servicios de Landing (info, activate)
- `apps/tenant/core/services/orchestration.py`: Orquestación de datos de múltiples TENANT_APPS
- `apps/tenant/core/services/empresa.py`: Servicios de empresa (SSoT)
- `apps/tenant/core/services/facturas.py`: Servicios de facturas
- `apps/tenant/core/services/contabilidad.py`: Servicios de contabilidad
- `apps/tenant/core/services/perfil.py`: Servicios de perfil

**Endpoints Core API (v2.30 - UI Única):**

**Autenticación (SSoT en Core):**
- `POST /api/v1/core/auth/login/` - Login centralizado
- `POST /api/v1/core/auth/logout/` - Logout centralizado
- `POST /api/v1/core/auth/password-reset/request/` - Solicitar reset
- `POST /api/v1/core/auth/password-reset/validate/` - Validar token
- `POST /api/v1/core/auth/password-reset/confirm/` - Confirmar reset

**Landing vía Core (UI única):**
- `GET /api/v1/core/landing/info/` - Información pública del tenant
- `GET /api/v1/core/landing/auth/activate/?token=...` - Verificar token de activación
- `POST /api/v1/core/landing/auth/activate/?token=...` - Procesar activación

**Orquestación de Datos:**
- `GET /api/v1/core/dashboard/` - Dashboard completo compuesto
- `GET /api/v1/core/mi-empresa/` - Información de empresa con branding
- `GET /api/v1/core/mi-perfil/` - Perfil del usuario autenticado (⚠️ v2.31: Deprecado, usar `/api/v1/perfil/perfiles/me/`)
- `GET /api/v1/core/facturas/resumen/` - Resumen de facturas
- `GET /api/v1/core/contabilidad/resumen/` - Resumen de contabilidad

**⚠️ v2.31: Endpoints Directos de Perfil (Recomendado):**
- `GET /api/v1/perfil/perfiles/me/` - Obtener perfil del usuario actual
- `PATCH /api/v1/perfil/perfiles/me/` - Actualizar perfil del usuario actual
- `PATCH /api/v1/perfil/perfiles/me/configuracion/` - Actualizar solo configuración
- `PATCH /api/v1/perfil/perfiles/me/avatar/` - Actualizar solo avatar

**Servicios de Orquestación:**
- `get_dashboard_completo(user, tenant)` - Compone todos los datos del dashboard
- `get_mi_empresa(tenant)` - Obtiene empresa usando `apps.tenant.empresa.services.get_empresa_data()` (SSoT)
- `get_empresa_summary(tenant)` - Resumen de empresa usando provider SSoT
- `get_empresas_snapshot(tenant)` - Snapshot de empresas usando provider SSoT
- `get_facturas_resumen(tenant, user)` - Estadísticas de facturas
- `get_contabilidad_resumen(tenant, user)` - Estadísticas de contabilidad
- `get_perfil_resumen(user, tenant)` - Perfil del usuario

**Branding Dinámico:**
- `get_tenant_branding(request)` - Obtiene branding desde BD (Empresa o tenant)
- Sin hardcodes: "SINTEL", "ACME", "Mi Empresa" prohibidos en código
- Fallback: Si no hay Empresa, usa `tenant.nombre` o "Sistema de Gestión"

**Manejadores de Error:**
- `custom_page_not_found_view(request, exception)` - Handler 404 con branding
- `custom_permission_denied_view(request, exception)` - Handler 403 con branding
- Ubicación: `apps/tenant/core/api/handlers.py`
- Configuración: `handler404` y `handler403` en `config/urls_tenant.py`

**Scripts de Auditoría:**
- `scripts/audit_templates_and_branding.py` - Verifica templates y hardcodes
- `scripts/audit_no_duplication.py` - Detecta duplicación de lógica
- Ejecución: `python scripts/audit_templates_and_branding.py`

**Pruebas de Humo (v2.30):**
- `tests/tenant/core/smoke/test_core_orchestration.py` - Orquestación (dashboard, mi-empresa, mi-perfil)
- `tests/tenant/core/smoke/test_core_modules_smoke.py` - Módulos (facturas, contabilidad)
- `tests/tenant/core/smoke/test_core_landing_integration.py` - Landing vía Core (info, activate)
- `tests/tenant/core/smoke/test_core_auth_smoke.py` - Auth centralizado (login, logout, password-reset)
- `tests/tenant/core/smoke/test_core_security_routing.py` - Seguridad y routing multi-tenant
- `tests/tenant/core/smoke/test_ui_contracts.py` - Contratos UI (JSON-only, redirect_url)
- `tests/tenant/core/smoke/test_e2e_full_flow.py` - Flujo E2E completo (onboarding → workspace)
- Verifica: estructura de respuestas, branding dinámico, ausencia de hardcodes, flujo completo
- Requiere: BD disponible para ejecutar

**Estado:** ✅ Implementado completo
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene su propia Core API
**Ubicación:** `apps/tenant/core/`

#### 6. `rest_framework` y `django_filters`
**Función:** APIs REST y filtrado avanzado
- APIs REST disponibles por tenant (enfoque API-first)
- Filtrado avanzado para consultas complejas
- Paginación server-side
**Esquema:** `tenant_<schema_name>`
**Aislamiento:** Cada tenant tiene sus propias APIs

### Servicios (apps/services)

Estos son paquetes Python puros sin modelos Django. Contienen lógica de negocio reutilizable que puede ser llamada desde cualquier app.

**Principio:** Service Layer Pattern - Lógica de negocio separada de modelos y vistas.

#### 1. `apps.services.maildigester`
**Función:** Procesamiento de correos electrónicos
- Recepción de correos con facturas adjuntas
- Extracción de archivos XML de correos
- Integración con servicios de email (IMAP/POP3)
- Procesamiento asíncrono con Celery
**Estado:** Paquete vacío, pendiente implementación
**Uso:** Llamado desde tareas Celery o APIs REST
**Dependencias:** `apps.services.xml_parser`

#### 2. `apps.services.xml_parser` ✅ IMPLEMENTADO (v2.34)
**Función:** Parser low-level genérico de XML (reutilizable, sin lógica de negocio)
- Parsing seguro de XML (resolve_entities=False, namespaces dinámicos)
- Helpers robustos: `local_name()`, `xpath()`, `text()`, `attr()` (namespace-agnostic)
- Detección de tipos: `is_attached_document()`, `is_invoice()`
- Extracción de artefactos: `extract_embedded_invoice_root()`, `extract_application_response()`
- Función orquestadora: `ensure_invoice_root_and_artifacts()` (AttachedDocument o Invoice cruda)
**Estado:** ✅ Implementado completo
**Uso:** Consumido por `apps/services/xml_ingest` y `apps/tenant/facturas/ubl_parser.py`
**Dependencias:** `lxml` (etree)
**⚠️ SSoT XML:** Única vía de parsing low-level; prohibido parseo XML fuera de este servicio

#### 3. `apps.services.xml_ingest` ✅ IMPLEMENTADO (v2.34)
**Función:** Orquestación de ingesta XML (sync/async, tenant-aware)
- `ingest_ubl_sync()`: Procesamiento síncrono (retorna DTO enriquecido)
- `ingest_ubl_async()`: Procesamiento asíncrono (Celery, tenant-aware)
- `task_status()`: Consulta estado de tareas (nunca retorna 500)
- Soporta AttachedDocument con Invoice embebida y ApplicationResponse opcional
- Retorna payload enriquecido: `{"dto": {...}, "anexos": {...}, "meta": {...}}`
**Estado:** ✅ Implementado completo
**Uso:** Consumido por `apps/tenant/facturas/services.py` (orquestación)
**Dependencias:** `apps/services/xml_parser`, `apps/tenant/facturas/ubl_parser`
**⚠️ SSoT XML:** Única vía de orquestación de ingesta; prohibida ingesta XML fuera de este servicio

#### 3. `apps.services.perfil` ✅ IMPLEMENTADO
**Función:** Gestión de perfiles de colaboradores dentro de tenants
- **Service Layer Pattern:** Lógica de negocio separada de modelos y vistas
- **Cero Signals:** Toda la lógica es explícita
- **Funciones:**
  - `obtener_o_crear_perfil(user, defaults=None)`: Obtiene o crea el perfil del usuario en el tenant actual
  - `actualizar_configuracion_ui(user, clave, valor, merge=True)`: Actualiza configuración de UI de forma segura
**Estado:** ✅ Implementado completo
**Ubicación:** `apps/services/perfil/perfil_service.py`
**Uso:** Llamado desde APIs REST y vistas para gestionar perfiles de colaboradores

#### 4. `apps.public.impuestos.services.etl` ✅ IMPLEMENTADO
**Función:** Pipeline ETL para normalización de documentos tributarios
- **Pipeline completo:** parse → tokenize → normalize → validate → upsert
- **Parsers multi-formato:** PDF, HTML, XML, Excel, CSV
- **Tokenización:** Extrae Artículo, Impuesto, Tema, Vigencia, Referencias
- **Normalización:** Mapea a entidades canónicas (TipoImpuesto, TarifaIVA, NormaTributaria, etc.)
- **Validaciones:** Porcentajes 0-100, códigos DIAN, solapes de vigencia
- **Upserts atómicos:** `transaction.atomic()` garantiza consistencia
**Estado:** ✅ Implementado completo
**Ubicación:** `apps/public/impuestos/services/etl/`
**Uso:** Llamado desde tarea Celery `procesar_fuente`
**Dependencias:** pdfminer.six, lxml, pandas, openpyxl, beautifulsoup4

#### 4. `apps.public.impuestos.services.robots` ✅ IMPLEMENTADO
**Función:** Verificación de robots.txt antes de descargar URLs
- Respeto de robots.txt para scraping ético
- Detección de crawl_delay y permisos
- User-Agent identificable
**Estado:** ✅ Implementado
**Ubicación:** `apps/public/impuestos/services/robots.py`
**Uso:** Llamado desde tarea Celery `descargar_fuente`

#### 5. `apps.services.onboarding` ✅ IMPLEMENTADO
**Función:** Servicio de onboarding para creación automática de empresas (tenants)

**⚠️ v2.19: Aprovisionamiento Atómico "Zero-Orphan":**
- La función `crear_tenant()` está completamente envuelta en `@transaction.atomic`
- Garantiza que si falla cualquier paso (Client, Domain, Membership, Migrations), TODO se revierte
- Previene completamente la creación de tenants "huérfanos" sin administrador vinculado
- Manejo robusto de errores con logging detallado antes del rollback automático
- Try/except específico para `TenantMembership` con mensajes de error claros
- Centraliza el proceso de creación de tenants de forma segura y reproducible
- Flujo estándar de alta de empresa automatizado
- Generación automática de schema_name desde nombre de empresa
- Creación de dominio principal
- Ejecución automática de migraciones del tenant
- Creación opcional de usuario administrador
**Estado:** ✅ Implementado
**Uso:** Llamado desde comando `crear_empresa` o directamente desde código
**Servicio Principal:** `empresa_service.crear_empresa()`
**Dependencias:** `apps.public.tenants`, `apps.public.accounts`

**Ventajas del Service Layer:**
- Fácil de testear (lógica pura, sin dependencias de Django)
- Reutilizable entre diferentes apps
- Mantenimiento simplificado
- Sin acoplamiento con modelos específicos

---

## ⚙️ Configuración Django

### settings.py

#### SHARED_APPS (Esquema Public) - Estructura Final Consolidada

**Apps que existen SOLO en el esquema 'public' (compartidas por todos los tenants):**

```python
SHARED_APPS = [
    # django-tenants debe ir PRIMERO (requisito obligatorio)
    "django_tenants",
    
    # Apps públicas del proyecto (esquema public)
    "apps.public.core",     # Core público (middleware, Server Guard) - label: 'public_core'
    "apps.public.tenants",   # Gestión de tenants y dominios
    "apps.public.accounts",  # Usuarios globales (AUTH_USER_MODEL)
    "apps.public.impuestos", # Catálogo legal/DIAN (compartido)
    "apps.public.console",   # Consola de administración pública (interfaz web)
    
    # DRF y herramientas API para esquema public (APIs públicas)
    "rest_framework",  # DRF para APIs públicas en esquema public
    "rest_framework_simplejwt",  # Autenticación JWT (SimpleJWT)
    "rest_framework_simplejwt.token_blacklist",  # Blacklist de refresh tokens
    "django_filters",  # Filtrado para APIs públicas
    "drf_spectacular",  # OpenAPI schema generation para APIs públicas
    "corsheaders",  # CORS para subdominios dinámicos (sintel.com)
    
    # Django contrib apps necesarias para el admin y funcionalidad base
    "django.contrib.contenttypes",  # Requerido por admin y relaciones genéricas
    "django.contrib.auth",          # Sistema de autenticación (usuarios globales)
    "django.contrib.admin",         # Admin de Django (en public para gestión global)
    "django.contrib.sessions",      # Sesiones compartidas (usuarios globales)
    "django.contrib.messages",      # Sistema de mensajes
    "django.contrib.staticfiles",   # Archivos estáticos
]
```

**⚠️ IMPORTANTE - Labels Únicos:**
- `apps.public.core` tiene `label = 'public_core'` para evitar conflicto con `apps.tenant.core`
- `apps.tenant.core` tiene `label = 'tenant_core'` para evitar conflicto con `apps.public.core`
- Esto previene el error "Application labels aren't unique, duplicates: core"

**Política de Sessions:**
- ✅ `django.contrib.sessions` está en `SHARED_APPS` porque los usuarios son globales
- ✅ Un usuario puede tener sesiones activas en múltiples tenants
- ✅ Si necesitaras sesiones aisladas por tenant, moverías `sessions` a `TENANT_APPS`

#### TENANT_APPS (Esquema por Empresa) - Estructura Final Consolidada

**Apps que viven en cada esquema de tenant (específicas de cada empresa):**

```python
TENANT_APPS = [
    # API y filtros (disponibles por tenant)
    "rest_framework",           # Django REST Framework (API-first)
    "django_filters",           # Filtrado avanzado para APIs
    "drf_spectacular",          # OpenAPI schema generation
    
    # Aplicaciones de negocio por tenant (datos específicos de cada empresa)
    "apps.tenant.core",         # Core API: orquestación, branding, manejadores de error (404, 403) - label: 'tenant_core'
    "apps.tenant.empresa",      # Datos de la empresa (por tenant)
    "apps.tenant.facturas",     # Facturación (por tenant)
    "apps.tenant.contabilidad", # Contabilidad (por tenant)
    "apps.tenant.landing",      # Landing page para tenants (accesible anónimamente) - API-First (v2.30: vistas HTML eliminadas)
    "apps.tenant.dashboard",    # Dashboard con control de roles
    "apps.tenant.perfil",       # Perfil privado del colaborador (por tenant) ✅ v2.16
    "apps.tenant.cotizaciones", # Gestión de cotizaciones comerciales (por tenant) ✅ v2.60
]
```

**⚠️ IMPORTANTE - Labels Únicos:**
- `apps.public.core` tiene `label = 'public_core'` para evitar conflicto
- `apps.tenant.core` tiene `label = 'tenant_core'` para evitar conflicto
- Esto previene el error "Application labels aren't unique, duplicates: core"

#### INSTALLED_APPS
```python
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
```

#### MIDDLEWARE
```python
# ⚠️ CONFIGURACIÓN CRÍTICA: Orden de middlewares es VITAL
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ WhiteNoise para servir staticfiles en producción
    'corsheaders.middleware.CorsMiddleware',  # ✅ CORS: Debe ir ANTES de CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',  # ✅ CRÍTICO: Debe ejecutarse antes de ForceNoPortMiddleware
    'apps.public.core.middleware.ForceNoPortMiddleware',  # ✅ ESTÁNDAR (v2.20): Normaliza HTTP_HOST eliminando puerto (ANTES de TenantMainMiddleware)
    'django_tenants.middleware.main.TenantMainMiddleware',  # ✅ CRÍTICO: Identifica tenant usando HTTP_HOST normalizado (sin puerto)
    'apps.public.tenants.middleware_urlconf.TenantURLConfMiddleware',  # ✅ FIX (v2.28): Garantiza que request.urlconf se establezca para tenants privados
    'apps.public.tenants.middleware.TenantSecurityMiddleware',  # ✅ SEGURIDAD (v2.11): Bloquea tenants suspendidos (debe ir después de TenantURLConfMiddleware)
    'apps.public.core.middleware.CSRFTrustedOriginMiddleware',  # ✅ DESARROLLO (v2.14): Permite dominios arbitrarios en CSRF_TRUSTED_ORIGINS
    'apps.public.core.middleware.HTTPSRedirectMiddleware',  # ✅ DESARROLLO (v2.14): Redirige HTTPS -> HTTP en DEBUG
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**⚠️ IMPORTANTE - Orden de Middlewares (v2.28):**
- `SessionMiddleware` debe ir ANTES de `ForceNoPortMiddleware` (necesario para sesiones)
- `ForceNoPortMiddleware` debe ir ANTES de `TenantMainMiddleware` (normaliza hostname antes de resolver tenant)
- `TenantMainMiddleware` debe ir ANTES de `TenantURLConfMiddleware` (v2.28: necesita tenant resuelto)
- `TenantURLConfMiddleware` (v2.28) debe ir ANTES de `TenantSecurityMiddleware` (garantiza request.urlconf antes de validaciones)
- `TenantSecurityMiddleware` debe ir DESPUÉS de `TenantURLConfMiddleware` (necesita tenant y urlconf resueltos)
- `ForceNoPortMiddleware` elimina puertos de `HTTP_HOST` para estandarizar a Puerto 80 (HTTP estándar)

**Explicación de Middlewares Personalizados (v2.14):**

1. **CSRFTrustedOriginMiddleware** (`apps/public/core/middleware.py`):
   - **Propósito**: Permite dominios arbitrarios en desarrollo agregándolos automáticamente a `CSRF_TRUSTED_ORIGINS`
   - **Funcionamiento**: En `DEBUG=True`, detecta el dominio de la request y lo agrega a `CSRF_TRUSTED_ORIGINS` si no está presente
   - **Seguridad**: Solo funciona en desarrollo. En producción, se requiere lista explícita en `CSRF_TRUSTED_ORIGINS`
   - **Posición**: Después de `TenantSecurityMiddleware`, antes de `HTTPSRedirectMiddleware`

2. **HTTPSRedirectMiddleware** (`apps/public/core/middleware.py`):
   - **Propósito**: Redirige peticiones HTTPS a HTTP en modo desarrollo
   - **Funcionamiento**: Detecta peticiones HTTPS y las redirige a HTTP equivalente
   - **Limitación**: Si el navegador fuerza HTTPS, el servidor HTTP no puede procesarla. Solución: usar HTTP explícitamente o limpiar HSTS del navegador
   - **Headers de Seguridad**: En desarrollo, solo establece `Cross-Origin-Opener-Policy` para `localhost` y `127.0.0.1` para evitar advertencias del navegador

#### Configuración de URLs (django-tenants)
```python
# ⚠️ CONFIGURACIÓN CRÍTICA: URLs separadas para público y privado
# django-tenants usa ROOT_URLCONF para el esquema 'public' y TENANT_URLCONF para tenants
ROOT_URLCONF = 'config.urls_public'   # URLs para esquema público (sintel.com)
TENANT_URLCONF = 'config.urls_tenant'  # URLs para tenants privados (ej: cliente.sintel.com) ✅ v2.19

# ⚠️ CONFIGURACIÓN DE ACCESO A TENANTS (v2.19)
# Política actualizada: se evita el comodín "*" incluso en DEBUG.
# - En desarrollo: ALLOWED_HOSTS se construye dinámicamente (localhost, 127.0.0.1, dominios de pruebas)
# - En producción: ALLOWED_HOSTS = [".sintel.com", "sintel.com"] + hosts explícitos necesarios
# La resolución final de tenant SIEMPRE la realiza TenantMainMiddleware contra la tabla Domain.
```

**Explicación:**
- **ROOT_URLCONF (`config.urls_public.py`)**: Se usa cuando se accede al dominio público (sintel.com)
  - Contiene: admin global, consola, APIs públicas, JWT, documentación
  - Vista raíz: `PublicIndexView` (redirección inteligente según estado del usuario)
- **TENANT_URLCONF (`config.urls_tenant.py`)**: Se usa cuando se accede a un tenant privado (ej: cliente.sintel.com) ✅ v2.19
  - ⚠️ v2.30: Vistas HTML de landing eliminadas - toda la funcionalidad está en `/api/v1/landing/`
  - Contiene: dashboard del tenant, admin aislado del tenant, APIs REST del tenant (facturas, contabilidad, empresa)
  - APIs REST de landing: `/api/v1/landing/info/`, `/api/v1/landing/auth/login/`, `/api/v1/landing/auth/activate/`
  - El frontend debe consumir las APIs REST para landing, login y activación

**Detección de URL y Enrutamiento Diferenciado (v2.19)**

1. **Dominio público (`sintel.com`)**
   - TenantMainMiddleware establece el esquema `public`.
   - Django usa `ROOT_URLCONF = 'config.urls_public'`.
   - `PublicIndexView` decide:
     - Staff / superuser → `/console/`
     - Usuario no staff o anónimo → `/admin/login/`.

2. **Tenant privado anónimo (`cliente.sintel.com`)** ⚠️ v2.30
   - TenantMainMiddleware resuelve el tenant a partir de `tenants_domain.domain`.
   - Django usa `TENANT_URLCONF = 'config.urls_tenant'`.
   - ⚠️ **PÁGINA PRINCIPAL (`/`)**: `TenantRootView` SIEMPRE redirige a `/static/tenant/landing/index.html` (shell estático de landing)
   - ⚠️ **ESTABLECIDO COMO PÁGINA PRINCIPAL**: Esta es la página principal para TODOS los tenants (cliente.sintel.com, etc.)
   - El shell estático de landing tiene botón de login e información del servicio
   - El shell estático consume `/api/v1/landing/info/` para obtener datos del tenant (API-First)
   - Ubicación en código: `apps/tenant/landing/static/tenant/landing/index.html`

3. **Tenant privado autenticado (`cliente.sintel.com`)** ⚠️ v2.30
   - Misma resolución de tenant que arriba.
   - ⚠️ **PÁGINA PRINCIPAL (`/`)**: `TenantRootView` redirige a `/static/tenant/dashboard/index.html` (shell estático del dashboard)
   - El shell estático del dashboard consume `/api/v1/dashboard/...` para obtener datos (API-First)

4. **Aislamiento de rutas públicas**
   - `config/urls_tenant.py` **no** incluye `/console/` ni `/api/public/v1/`.
   - `TenantSecurityMiddleware` bloquea cualquier intento de acceder a rutas públicas desde un schema privado devolviendo 404.

5. **Tests automatizados de routing**
   - Archivo: `tests/tenant/core/test_routing_logic.py`.
   - Casos cubiertos:
     - Dominio público usa `urls_public` y ejecuta `PublicIndexView`.
     - Tenant privado anónimo devuelve 200 en `/` (landing).
     - Tenant privado autenticado redirige a `/dashboard/`.
     - `urls_public` no expone rutas de tenant (`/dashboard/` → 404).
     - `urls_tenant` no expone rutas públicas (`/console/`, `/api/public/v1/` → 404).

Para más detalle, ver también `documentacion/ENRUTAMIENTO_DIFERENCIADO_PUBLICO_PRIVADO.md` (playbook específico de routing público vs. privado).

#### Base de Datos
```python
# ⚠️ CONFIGURACIÓN CRÍTICA: ENGINE debe ser django_tenants.postgresql_backend
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  # ✅ CRÍTICO: Backend especial para multi-tenant
        'NAME': os.getenv('DATABASE_NAME', 'sintel'),
        'USER': os.getenv('DATABASE_USER', 'sintel'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'sintel'),
        'HOST': os.getenv('DATABASE_HOST', 'db'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}

# ⚠️ CONFIGURACIÓN CRÍTICA: DATABASE_ROUTERS debe ser una tupla con TenantSyncRouter
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',  # ✅ CRÍTICO: Router para enrutar queries al esquema correcto
)
```

#### Configuración de Tenant
```python
TENANT_MODEL = "tenants.Client"
TENANT_DOMAIN_MODEL = "tenants.Domain"
AUTH_USER_MODEL = "accounts.User"

# ⚠️ CONFIGURACIÓN DE SUBDOMINIOS (v2.17) - POLÍTICA ESTRICTA
# Dominio base del SaaS para construcción automática de subdominios
TENANT_DOMAIN_BASE = os.getenv('TENANT_DOMAIN_BASE', 'sintel.com')

# Puerto de la aplicación para construcción de URLs absolutas
# En desarrollo: 8000 (runserver)
# En producción: 80 (HTTP) o 443 (HTTPS) - configurar según servidor web
APP_PORT = os.getenv('APP_PORT', '8000')

# ⚠️ URLs de Autenticación (v2.18)
# Login y logout personalizados para tenants privados
LOGIN_URL = '/login/'  # URL de login (usado por LoginRequiredMixin)
LOGIN_REDIRECT_URL = '/dashboard/'  # URL por defecto (se sobrescribe en vistas según contexto)
LOGOUT_REDIRECT_URL = '/'  # ⚠️ Página principal del tenant (landing con botón de login e información del servicio)
```

#### ⚠️ SEGURIDAD: Backends de Autenticación Tenant-Aware (v2.16)
```python
# El orden es importante: TenantAwareBackend debe ir ANTES de ModelBackend
# para que filtre primero y valide la membresía del tenant
AUTHENTICATION_BACKENDS = [
    'apps.public.tenants.auth_backend.TenantAwareBackend',  # ✅ SEGURIDAD: Filtro tenant (debe ir primero)
    'django.contrib.auth.backends.ModelBackend',  # Fallback estándar (opcional, pero recomendado para compatibilidad)
]
```

**Explicación:**
- **TenantAwareBackend**: Valida que el usuario tenga `TenantMembership` activa en el tenant actual antes de permitir login
- **ModelBackend**: Fallback estándar de Django para compatibilidad
- **Ubicación**: `apps/public/tenants/auth_backend.py`
- **Funcionamiento**: 
  - Valida credenciales usando backend estándar
  - Si credenciales válidas, valida membresía en tenant actual
  - Si no tiene membresía, retorna `None` (login fallido) + log warning
  - Permite acceso al tenant `public` sin membresía
  - Permite acceso sin tenant (comandos de consola)

#### Django REST Framework (API-First)

**⚠️ FILOSOFÍA API-FIRST (v2.30):**
- **Solo JSONRenderer:** APIs devuelven exclusivamente JSON (sin BrowsableAPIRenderer)
- **Sin vistas HTML dinámicas:** Django NO renderiza formularios HTML desde vistas (desde v2.30)
- **Shells estáticos:** La UI se resuelve mediante shells HTML estáticos que consumen la API
- **Frontend agnóstico:** Cualquier cliente puede consumir las APIs (React, Vue, Angular, móvil, etc.)

**Configuración:**
```python
REST_FRAMEWORK = {
    # Solo JSON: APIs solo devuelven JSON (sin BrowsableAPIRenderer)
    # UI dedicada: Toda presentación HTML pasa por templates en /console/... o shells estáticos
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        # NO incluir BrowsableAPIRenderer: APIs solo JSON, UI en templates dedicados
    ],
    
    # Parsers (formato de entrada)
    # MultiPartParser: para subida de archivos en /ingesta (multipart/form-data)
    # FormParser: para formularios POST (application/x-www-form-urlencoded)
    # JSONParser: para JSON en /ingesta y otras APIs (application/json)
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',  # Para form-urlencoded
        'rest_framework.parsers.MultiPartParser',  # Para /ingesta multipart
    ],
    
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    
    # Autenticación por defecto (puede sobrescribirse por endpoint)
    # ⚠️ v2.32: SessionAuthentication añadido para workspace (cookies de sesión desde mismo host)
    # DRF prioriza authentication_classes del ViewSet sobre DEFAULT_AUTHENTICATION_CLASSES
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # ✅ JWT para APIs externas
        'rest_framework.authentication.SessionAuthentication',  # ✅ DEV: Workspace usa cookies de sesión
    ],
    
    # Permisos por defecto (recomendación documental)
    # ⚠️ NOTA: Cada endpoint puede sobrescribir estos permisos según sus necesidades
    # - APIs públicas: `AllowAny` o `IsAuthenticated`
    # - APIs de tenant: `IsAuthenticated` + permisos específicos por rol (IsAdminOrHigher, etc.)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Requiere autenticación por defecto
    ],
    
    # Configuración API-first:
    # - Todas las funcionalidades expuestas como APIs REST
    # - Frontend agnóstico (React, Vue, Angular, móvil, etc.)
    # - Documentación automática con Swagger/OpenAPI (futuro)
    # - Versionado de APIs (futuro)
}
```

**Política CORS (Cross-Origin Resource Sharing):**

**Desarrollo:**
- `CORS_ALLOW_CREDENTIALS = True` (permite cookies en requests cross-origin)
- `CORS_ALLOWED_ORIGINS` o `CORS_ALLOWED_ORIGIN_REGEXES` configurados para localhost y dominios de desarrollo
- `CSRF_TRUSTED_ORIGINS` validado dinámicamente por `CSRFTrustedOriginMiddleware`

**Producción:**
- `CORS_ALLOW_CREDENTIALS = True` (si se requiere compartir cookies entre subdominios)
- `CORS_ALLOWED_ORIGINS` lista explícita de orígenes permitidos (ej: `["https://sintel.com"]`)
- `CORS_ALLOWED_ORIGIN_REGEXES` para patrones de subdominios (ej: `r"^https://.*\.sintel\.com$"`)
- `CSRF_TRUSTED_ORIGINS` lista explícita + validación dinámica por middleware

**⚠️ IMPORTANTE:**
- CORS debe configurarse según el modelo de frontend (mismo origen vs cross-origin)
- Si el frontend se sirve desde el mismo dominio, CORS puede ser más restrictivo
- Si el frontend se sirve desde subdominios diferentes, CORS debe permitir esos orígenes

---

## 🗄️ Base de Datos

### Esquema Public

**Tablas Principales:**
- `tenants_client`: Tenants (empresas)
- `tenants_domain`: Dominios asociados
- `accounts_user`: Usuarios globales
- `impuestos_tipoimpuesto`: Tipos de impuestos
- `impuestos_tarifaiva`: Tarifas de IVA
- `impuestos_conceptoretencion`: Conceptos de retención
- `impuestos_codigotributario`: Códigos tributarios
- `impuestos_actividadeconomica`: Actividades económicas
- Tablas de Django contrib (auth, admin, sessions, etc.)

### Esquemas Tenant

Cada tenant tiene su propio esquema con:
- Tablas de `apps.tenant.empresa`
- Tablas de `apps.tenant.facturas`
- Tablas de `apps.tenant.contabilidad`
- Tablas de DRF si aplica

### Migraciones

**Flujo Seguro de Migraciones:**

El sistema implementa un **Server Guard** que previene el arranque si hay migraciones pendientes:

1. **Crear migraciones:**
   ```bash
   python manage.py makemigrations
   python manage.py makemigrations accounts  # Solo para accounts
   ```

2. **Aplicar migraciones del esquema public:**
   ```bash
   python manage.py migrate_schemas --shared --fake-initial
   ```

3. **Verificar migraciones pendientes (Server Guard):**
   ```bash
   python manage.py check_migrations
   ```

4. **Aplicar migraciones para tenant específico:**
   ```bash
   python manage.py migrate_schemas --schema=<schema_name> --fake-initial
   ```

5. **Aplicar migraciones para todos los tenants:**
   ```bash
   python manage.py migrate_schemas --tenant --fake-initial
   ```

**Nota:** El flag `--fake-initial` permite aplicar migraciones iniciales sin errores si las tablas ya existen.

**Server Guard:**
- El comando `check_migrations` verifica que no haya migraciones pendientes
- Si hay pendientes, el servidor **NO** arranca
- Garantiza que la base de datos esté siempre sincronizada con el código

---

## 🛡️ Server Guard y Migraciones Seguras

### Concepto

El sistema implementa un **Server Guard** que previene el arranque del servidor si hay migraciones pendientes, garantizando que la base de datos esté siempre sincronizada con el código.

### Implementación

#### 1. Comando check_migrations

**Ubicación:** `apps/public/tenants/management/commands/check_migrations.py`

**Funcionalidad:**
- Usa `MigrationExecutor` para verificar migraciones pendientes
- Falla con `CommandError` si hay migraciones pendientes
- Maneja errores cuando la tabla de migraciones no existe aún

**Uso:**
```bash
python manage.py check_migrations
```

**Comportamiento:**
- ✅ Si no hay migraciones pendientes: continúa normalmente
- ❌ Si hay migraciones pendientes: lanza `CommandError` y detiene el proceso
- ❌ Si no puede validar (tabla no existe): asume pendientes y falla

#### 2. Guardas en AppConfig.ready()

**Ubicación:** `apps/public/core/apps.py` (Server Guard principal)

**Funcionalidad:**
- `CoreConfig.ready()` implementa guardas que omiten validaciones durante comandos de mantenimiento
- Evita el problema "Chicken-Egg": no intenta acceder a tablas que aún no existen durante `makemigrations`
- Protege contra consultas a DB en import-time cuando hay migraciones pendientes

**Comandos Protegidos:**
- `makemigrations`, `migrate`, `migrate_schemas`
- `collectstatic`, `shell`, `check`, `test`, `flush`, `loaddata`, `dumpdata`

**Comportamiento:**
- Si se ejecuta un comando de mantenimiento: `ready()` retorna inmediatamente sin ejecutar validaciones
- Solo ejecuta validaciones cuando el servidor está corriendo (`runserver`, `gunicorn`, etc.)
- Previene errores durante la creación de migraciones cuando las tablas aún no existen

**Nota:** `apps/public/accounts/apps.py` mantiene `ready()` vacío para evitar consultas prematuras a la BD.

#### 3. Flujo Automático en Docker Compose

El contenedor `web` ejecuta automáticamente (vía `entrypoint.sh`):

```bash
# 1. Esperar a que la BD esté lista (wait_for_db)
# 2. Asegurar directorios estáticos
mkdir -p /app/static /app/media /app/staticfiles

# 3. Corregir historial de migraciones (silencioso)
python manage.py fix_migration_history --fake-accounts --verbosity 0 || true

# 4. Aplicar migraciones del esquema public (silencioso)
python manage.py migrate_schemas --shared --fake-initial --verbosity 0

# 5. Verificar que no queden migraciones pendientes (Server Guard) - silencioso
python manage.py check_migrations --verbosity 0 2>/dev/null || true

# 6. Configurar tenant público si no existe (silencioso)
python manage.py setup_public_tenant --skip-migrations --verbosity 0 || true

# 7. Iniciar servidor de desarrollo (con logs normales)
exec python manage.py runserver 0.0.0.0:8000
```

**Orden de Ejecución:**
1. **Espera a BD**: `wait_for_db()` verifica conexión usando Django (más confiable)
2. **Prepara directorios**: Asegura que `/app/static`, `/app/media`, `/app/staticfiles` existan
3. **Corrige historial**: Arregla migraciones si es necesario
4. **Aplica migraciones**: Del esquema public (con `--fake-initial`)
5. **Verifica pendientes**: Server Guard (silencioso, no bloquea si hay errores menores)
6. **Configura tenant público**: Si no existe
7. **Inicia servidor**: Solo si todo está OK

**Nota:** 
- `--fake-initial` permite aplicar migraciones iniciales sin errores si las tablas ya existen
- `--verbosity 0` reduce ruido en logs para comandos de mantenimiento
- `wait_for_db()` usa Django para verificar conexión (más robusto que `psycopg2` directo)
- El contenedor `celery` NO ejecuta migraciones (solo espera BD/Redis y arranca worker)

### Beneficios

- ✅ **Prevención de Errores:** El servidor no arranca con migraciones pendientes
- ✅ **Sincronización Garantizada:** La base de datos siempre está alineada con el código
- ✅ **Protección en Import-Time:** No hay consultas a DB durante comandos de mantenimiento
- ✅ **Flujo Automático:** Todo se ejecuta automáticamente al hacer `make up`
- ✅ **CI/CD Ready:** Puede integrarse en pipelines para validar migraciones

---

## 🌐 Rutas y APIs REST

### URLs Principales

**Consola de Administración (Dominio Público - sintel.com):**
- `/`: Root (redirige a `/console/` - dashboard del tenant actual)
- `/admin/`: Admin de Django
- `/admin/logout/`: Logout personalizado (acepta GET, redirige a `/` - landing page)
- `/console/`: Dashboard principal
- `/console/tenants/`: Gestión de empresas
- `/console/users/`: Gestión de usuarios
- `/console/impuestos/ingesta/`: Sistema de ingesta (Catálogo DIAN)

**Tenants Privados (ej: cliente.sintel.com):**
- ⚠️ **`/`**: Página principal del tenant (landing - shell estático `index.html` con botón de login e información del servicio)
  - ⚠️ **ESTABLECIDO COMO PÁGINA PRINCIPAL**: Esta es la página principal para TODOS los tenants (cliente.sintel.com, etc.)
  - Usuario autenticado → redirige a `/dashboard/` (shell estático)
  - Usuario anónimo → muestra shell estático de landing (`/static/tenant/landing/index.html`)
  - El shell estático consume `/api/v1/landing/info/` para obtener información del tenant
  - Ubicación en código: `apps/tenant/landing/static/tenant/landing/index.html`
  - URL servida: `/static/tenant/landing/index.html`
- `/login/`: Shell estático de login (redirige a `/static/tenant/landing/login.html`)
- `/activate/`: Shell estático de activación (redirige a `/static/tenant/landing/activate.html`)
- `/reset-password/`: Shell estático para solicitar reset (redirige a `/static/tenant/landing/reset-request.html`)
- `/reset-password/confirm/`: Shell estático para confirmar reset (redirige a `/static/tenant/landing/reset-confirm.html`)
- `/dashboard/`: Shell estático del dashboard (redirige a `/static/tenant/dashboard/index.html`)
- ⚠️ **Logout**: 
  - Endpoint API-First: `POST /api/v1/core/auth/logout/` (SSoT en Core, v2.30)
  - Retorna JSON con `redirect_url="/"` (página principal del tenant - landing)
  - El frontend consume `redirect_url` y redirige usando JavaScript
  - `LOGOUT_REDIRECT_URL = '/'` en settings.py (para logout tradicional si existe)

**APIs REST:**
- `/api/v1/`: APIs por tenant (namespace `v1`)
  - `/api/v1/empresas/`
  - `/api/v1/facturas/`
  - `/api/v1/cuentas-contables/`
  - `/api/v1/impuestos/tipos/` (catálogo DIAN compartido)
  - `/api/v1/impuestos/tarifas-iva/`
  - `/api/v1/impuestos/conceptos-retencion/`
  - `/api/v1/impuestos/codigos-tributarios/`
  - `/api/v1/impuestos/actividades-economicas/`

- `/api/public/v1/`: APIs públicas (esquema public)
  - `/api/public/v1/tenants/` (CRUD completo + acciones `onboard`, `toggle-active`)
  - `/api/public/v1/impuestos/ingesta/` (Ingesta de documentos)

- `/api/admin/v1/`: APIs de administración (solo staff - `IsAdminUser`)
  - `/api/admin/v1/accounts/users/` (CRUD completo de usuarios globales)
  - `/api/admin/v1/console/dt/users/` (DataTables server-side para usuarios)
  - `/api/admin/v1/console/dt/tenants/` (DataTables server-side para tenants)
  - `/api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/` (Reenviar token de activación del owner - v2.30)
  - `/api/admin/v1/console/health/` (Estado de la consola)

**Documentación API:**
- `/api/schema/`: OpenAPI schema (drf-spectacular)
- `/api/docs/`: Swagger UI
- `/api/redoc/`: ReDoc

### Estructura de URLs

**Configuración (django-tenants):**
- `config/urls_public.py`: URLs para esquema público (sintel.com) - **ROOT_URLCONF**
  - `PublicIndexView`: Redirección inteligente según estado del usuario
  - Admin, consola, APIs públicas, JWT, documentación
- `config/urls_tenant.py`: URLs para tenants privados (ej: cliente.sintel.com:8000) - **TENANT_URLCONF** ✅ v2.13
  - ⚠️ v2.30: `path('', include('apps.tenant.landing.urls'))` DESHABILITADO - Vistas HTML eliminadas
  - `path('dashboard/', include('apps.tenant.dashboard.urls'))`: Dashboard del tenant
  - `path('api/v1/landing/', include('apps.tenant.landing.api.urls'))`: APIs REST de landing/login/activación ⚠️ v2.30
  - `path('admin/login/', tenant_admin_login_redirect)`: Redirige a `/` (landing page) ✅ v2.18
  - `path('admin/', tenant_admin_site.urls)`: Admin aislado del tenant (solo modelos de TENANT_APPS) ✅ v2.18
  - APIs REST del tenant (facturas, contabilidad, empresa)
  - JWT también disponible en tenants
- `config/api_urls.py`: Router para APIs por tenant (`/api/v1/`)
- `config/public_api_urls.py`: Router para APIs públicas (`/api/public/v1/`)
- `apps/*/api/urls.py`: URLs específicas de cada app
- `apps/public/console/urls.py`: URLs de la consola
- `apps/public/core/views.py`: Vistas core públicas (PublicIndexView)
- ⚠️ v2.30: `apps/tenant/landing/views.py` ELIMINADO - Toda la funcionalidad está en `apps/tenant/landing/api/`
- `apps/tenant/dashboard/views.py`: Dashboard del tenant con control de roles ✅ v2.13

**Principio:**
- **Esquema Público (sintel.com)**: Usa `ROOT_URLCONF = 'config.urls_public'`
  - Acceso a admin, consola de gestión, APIs públicas
  - Redirección inteligente: staff → consola, anónimo → login
- **Tenants Privados (ej: cliente.sintel.com:8000)**: Usa `TENANT_URLCONF = 'config.urls_tenant'` ✅ v2.13
  - ⚠️ v2.30: **Vistas HTML eliminadas** - Toda la funcionalidad está en `/api/v1/landing/`
  - **APIs REST de Landing (`/api/v1/landing/`)** ⚠️ v2.30:
    - ⚠️ **IMPORTANTE**: `/api/v1/landing/` NO tiene índice. Acceder a esta ruta retornará 404.
    - ⚠️ **IMPORTANTE**: Usar rutas específicas listadas a continuación.
    - `GET /api/v1/landing/info/` - Información pública del tenant
    - `POST /api/v1/landing/auth/login/` - Login con validación de membresía
    - `GET /api/v1/landing/auth/activate/?token=...` - Validar token de activación (retorna JSON)
      - **200 OK**: Token válido, usuario sin contraseña usable → frontend muestra formulario
      - **409 Conflict**: Usuario ya tiene contraseña usable → frontend muestra mensaje y redirige a `/` (raíz del tenant)
      - **400 Bad Request**: Token inválido/expirado → frontend muestra error
    - `POST /api/v1/landing/auth/activate/?token=...` - Procesar activación (retorna JSON)
      - **200 OK**: Activación exitosa → frontend redirige a `redirect_url` absoluta de la respuesta
      - **409 Conflict**: Usuario ya tiene contraseña usable → frontend muestra mensaje y redirige a `/` (raíz del tenant)
      - **400 Bad Request**: Token inválido/expirado o datos inválidos → frontend muestra error
    - ⚠️ **v2.30**: NO existen vistas HTML - Django responde SOLO JSON
    - ⚠️ **v2.30**: El frontend es responsable de renderizar formularios y manejar redirecciones
    - ⚠️ **v2.30**: Templates legacy eliminados (`activate.html`, `login.html`, `index.html`)
  - **Dashboard (`/dashboard/`)**: Dashboard del tenant con control de roles
  - **Admin (`/admin/`)**: Admin aislado del tenant (`tenant_admin_site`) - Solo modelos de TENANT_APPS ✅ v2.18
    - Acceso a `/admin/login/` redirige a `/` (landing page)
  - APIs REST del tenant: `/api/v1/...`
  - Redirección: autenticado → dashboard, no autenticado → landing page
- APIs por tenant: `/api/v1/...` (acceden al esquema del tenant actual)
- APIs públicas: `/api/public/v1/...` (acceden siempre al esquema `public`)

---

## 🔄 Flujos de Trabajo

### Flujo de Datos Multi-Tenant

1. **Request HTTP llega al servidor**
   - `TenantMainMiddleware` identifica el tenant por dominio
   - Establece el esquema de BD activo (`public` o `tenant_<schema>`)

2. **Consulta a Base de Datos**
   - `TenantSyncRouter` enruta la consulta al esquema correcto
   - Apps en SHARED_APPS → esquema `public`
   - Apps en TENANT_APPS → esquema del tenant actual

3. **Procesamiento**
   - Vistas/APIs procesan la request
   - Servicios (`apps/services`) ejecutan lógica de negocio
   - Modelos acceden solo a su esquema correspondiente

4. **Response**
   - Datos del tenant correcto son retornados
   - Aislamiento completo garantizado

### Flujo de Ingesta y ETL

**Proceso completo de ingesta de documentos tributarios:**

1. **Captura (Capa A):**
   - Usuario sube archivo o proporciona URL desde `/console/impuestos/ingesta/nuevo/`
   - API POST `/api/public/v1/impuestos/ingesta/` recibe datos
   - Validación: tipo permitido (PDF/XLSX/CSV/HTML), tamaño (máx 50MB)
   - Creación de `DocumentoFuente` con estado `RECIBIDO`

2. **Descarga (si URL):**
   - Tarea Celery `descargar_fuente` se ejecuta automáticamente
   - Verificación de robots.txt (respeta `crawl_delay` si existe)
   - Descarga del archivo con User-Agent identificable
   - Guardado en `FileField` con metadatos (`content_type`, `extension`, `size_bytes`)
   - Detección automática de tipo por extensión/MIME
   - Cálculo de hash SHA256
   - Estado cambia a `EN_PROCESO`

3. **Procesamiento ETL (Capa B):**
   - Tarea Celery `procesar_fuente` ejecuta pipeline completo:
     - **Parse:** Detecta tipo y parsea según formato (PDF/HTML/XML/Excel/CSV)
     - **Tokenize:** Extrae Artículo, Impuesto, Tema, Vigencia, Referencias
     - **Normalize:** Mapea tokens a entidades canónicas (TipoImpuesto, TarifaIVA, NormaTributaria, etc.)
     - **Validate:** Valida porcentajes (0-100), códigos DIAN, solapes de vigencia
     - **Upsert:** Inserta/actualiza catálogos en transacción atómica
   - Estado cambia a `PROCESADO` (o `ERROR` si falla)

4. **Seguimiento:**
   - Logs registrados en `IngestaLog` en cada etapa
   - Dashboard muestra progreso en tiempo real (HTMX auto-refresh)
   - Acciones de reintento disponibles si hay errores

**Características:**
- ✅ Atomicidad: Todos los upserts en `transaction.atomic()`
- ✅ Multi-tenant: Escribiendo en esquema `public` (catálogo compartido)
- ✅ Validación: Reglas de negocio antes de persistir
- ✅ Logs: Estadísticas y errores en `IngestaLog`
- ✅ Extensibilidad: Parsers modulares, fácil agregar nuevos tipos

### Inicialización del Sistema

**Flujo Automático (Recomendado):**

El contenedor `web` ejecuta automáticamente el flujo completo al hacer `make up`:

1. **Levantar servicios Docker:**
   ```bash
   make up
   ```
   Esto ejecuta automáticamente:
   - `makemigrations accounts || true`
   - `makemigrations || true`
   - `migrate_schemas --shared --fake-initial`
   - `check_migrations` (Server Guard)
   - `runserver` (solo si no hay migraciones pendientes)

**Flujo Manual (Si necesitas más control):**

1. **Levantar servicios:**
   ```bash
   make up
   ```

2. **Crear migraciones (si hay cambios):**
   ```bash
   make makemigrations
   # O solo para accounts:
   make makemigrations-accounts
   ```

3. **Aplicar migraciones del esquema public:**
   ```bash
   make migrate-shared
   ```

4. **Verificar migraciones pendientes:**
   ```bash
   make check-migrations
   ```

5. **Crear tenant público:**
   ```bash
   make setup
   ```

6. **Poblar catálogo DIAN:**
   ```bash
   make poblar-dian
   ```

7. **Crear superusuario:**
   ```bash
   make superuser
   ```

### Creación de un Nuevo Tenant (Onboarding Automático - Fase 3)

**✅ RECOMENDADO: Usar el comando de onboarding automático**

```bash
# Opción 1: Comando directo
python manage.py crear_empresa "Mi Empresa S.A." "mi-empresa.localhost" "admin@mi-empresa.com"

# Opción 2: Usando Makefile
make crear-empresa NOMBRE="Mi Empresa S.A." DOMINIO="mi-empresa.localhost" EMAIL="admin@mi-empresa.com"
```

**Flujo Automático:**
1. ✅ Genera `schema_name` automáticamente desde el nombre
2. ✅ Crea `Client` (genera esquema automáticamente)
3. ✅ Crea dominio principal con `is_primary=True`
4. ✅ Ejecuta migraciones del tenant automáticamente
5. ✅ Crea usuario administrador (si no existe)

**Otras Opciones:**

1. **Desde el Servicio (Código Python):**
   ```python
   from apps.services.onboarding.empresa_service import crear_tenant
   # ⚠️ IMPORTANTE: auto_create_schema es un atributo de clase, NO se pasa como argumento
   client, domain, login_url = crear_tenant(
       nombre="Mi Empresa",
       schema_name="mi_empresa",
       admin_user_id=1,
       dominio="mi-empresa.localhost"  # Opcional
   )
   ```

2. **Desde el Admin (Manual):**
   - Ir a http://localhost:8000/admin/
   - Crear nuevo `Client` con `schema_name` único
   - Crear `Domain` asociado con `is_primary=True`
   - Ejecutar migraciones: `python manage.py migrate_schemas --schema=<schema_name>`

3. **Desde el Shell (Manual):**
   ```python
   from apps.public.tenants.models import Client, Domain
   from django.core.management import call_command
   
   tenant = Client(schema_name='mi_empresa', nombre='Mi Empresa')
   tenant.save()  # Crea el esquema automáticamente
   
   domain = Domain(domain='mi-empresa.localhost', tenant=tenant, is_primary=True)
   domain.save()
   
   # Ejecutar migraciones del tenant
   call_command('migrate_schemas', '--schema', 'mi_empresa', '--fake-initial')
   ```

### Desarrollo Diario

1. **Levantar servicios:**
   ```bash
   make up
   ```

2. **Ver logs:**
   ```bash
   make logs
   ```

3. **Acceder al shell:**
   ```bash
   make shell
   ```

4. **Detener servicios:**
   ```bash
   make down
   ```

---

## 🚀 Comandos Esenciales

### Makefile

**Servicios Docker:**
```makefile
make up          # Levantar servicios Docker (detached)
make down        # Detener servicios y eliminar volúmenes
make shell       # Acceder a shell del contenedor web
make logs        # Ver logs del contenedor web
```

**Migraciones:**
```makefile
make makemigrations          # Crear migraciones para todas las apps
make makemigrations-accounts  # Crear migraciones solo para accounts
make migrate-shared          # Aplicar migraciones del esquema public (--fake-initial)
make migrate-tenants          # Aplicar migraciones de tenant apps (--fake-initial)
make check-migrations         # Verificar migraciones pendientes (Server Guard)
```

**Setup y Configuración:**
```makefile
make setup       # Crear tenant público
make poblar-dian # Poblar catálogo DIAN
make superuser   # Crear superusuario
```

**Auditoría y Refactor:**
```makefile
make audit        # Ejecutar todas las auditorías (ruff, bandit, dj-check, static-check)
make ruff         # Linter y formatter con auto-fix
make bandit       # Análisis de seguridad SAST
make dj-check     # Django System Check (check --deploy)
make static-check # Validación de archivos estáticos (collectstatic --dry-run)
```

**Tests:**
```makefile
make test         # Ejecutar todos los tests de impuestos (pytest)
make test-ingesta # Tests de ingesta (Fase A)
make test-etl     # Tests de ETL (Fase B)
make test-api     # Tests de API ReadOnly (Fase C)
make test-search  # Tests de búsqueda (Fase C)
make test-ops     # Tests de operación (Fase D)
```

### Docker Compose

```bash
docker compose up --build        # Levantar y construir
docker compose up -d              # Levantar en segundo plano
docker compose down                # Detener
docker compose down -v            # Detener y eliminar volúmenes
docker compose logs -f web         # Ver logs
docker compose exec web bash       # Shell del contenedor
docker compose ps                  # Estado de servicios
```

### Django Management

```bash
# Migraciones
python manage.py makemigrations                    # Crear migraciones para todas las apps
python manage.py makemigrations accounts          # Crear migraciones solo para accounts
python manage.py migrate_schemas --shared --fake-initial  # Aplicar migraciones del esquema public
python manage.py migrate_schemas --tenant --fake-initial  # Aplicar migraciones de tenant apps
python manage.py migrate_schemas --schema=<schema> --fake-initial  # Aplicar para tenant específico
python manage.py check_migrations                  # Server Guard: Verificar migraciones pendientes

# Setup
python manage.py setup_public_tenant               # Crear tenant público
python manage.py poblar_catalogo_dian              # Poblar catálogo DIAN
python manage.py crear_empresa "Nombre" "dominio.localhost" "admin@email.com"  # Crear nueva empresa (Fase 3)

# Usuarios
python manage.py createsuperuser                   # Crear superusuario

# Shell
python manage.py shell                             # Shell interactivo de Django

# Diagnóstico
python manage.py debug_tenant_creation              # Diagnóstico forense de creación de tenants

# Diagnóstico
python manage.py debug_tenant_creation              # Diagnóstico forense de creación de tenants
```

---

## 📊 Estado Actual del Proyecto

### ✅ Fase 1: Entorno Base y Scaffolding (COMPLETADA)

- [x] Infraestructura Docker (PostgreSQL 16, Redis 7-alpine, Python 3.12-slim)
- [x] Estructura de directorios completa
- [x] Configuración de dependencias (requirements.txt)
- [x] Docker Compose con 3 servicios (db, redis, web)
- [x] Makefile con comandos de conveniencia
- [x] Variables de entorno (.env.sample)

### ✅ Fase 2: Núcleo Multitenant Funcional (COMPLETADA Y VERIFICADA)

**Objetivo:** Habilitar multitenancy estable basado en esquemas.

#### 2.1. Modelo de Tenant y Domain ✅
- [x] `Client(TenantMixin)` con `auto_create_schema = True` (conforme a documentación oficial) ✅
- [x] `Domain(DomainMixin)` con `pass` (conforme a documentación oficial) ✅
- [x] Modelos validados según instalación oficial de django-tenants ✅
- [x] Admin configurado para ambos modelos ✅

#### 2.2. Migración Inicial del Esquema Público ✅
- [x] Comando `migrate_schemas --shared` implementado ✅
- [x] Instala SOLO `SHARED_APPS` en el esquema `public` ✅
- [x] Comportamiento documentado del flag `--shared` verificado ✅
- [x] Integrado en `entrypoint.sh` (ejecución automática) ✅

#### 2.3. Implementación del Comando setup_public_tenant ✅
- [x] Comando `setup_public_tenant` implementado ✅
- [x] Crea tenant "public" con `schema_name='public'` ✅
- [x] Crea dominio principal (default: 'localhost') ✅
- [x] Conforme a guía oficial de creación del public tenant ✅
- [x] Integrado en `entrypoint.sh` (ejecución automática) ✅

#### Otros Componentes ✅
- [x] Configuración multi-tenant (SHARED_APPS, TENANT_APPS) ✅
- [x] Modelo de usuario global (AbstractUser con generación automática de username) ✅
- [x] Catálogo DIAN completo (5 modelos) ✅
- [x] Comandos de management (poblar_catalogo_dian, check_migrations) ✅
- [x] Admin personalizado para todos los modelos ✅

**📋 Verificación Completa:** Ver `FASE_2_COMPLETA_VERIFICADA.md` y `FASE_2_VERIFICACION.md` (en esta misma carpeta) para detalles completos de la implementación.

### ✅ Fase 3: Onboarding Automático de Empresas (COMPLETADA)

**Objetivo:** Automatizar la creación de tenants de forma segura, reproducible y coherente.

#### 3.1. Flujo Estándar de Alta de Empresa ✅
- [x] Recibir datos mínimos: nombre empresa, dominio, email administrador ✅
- [x] Generar `schema_name` automáticamente desde nombre (slug) ✅
- [x] Crear instancia de `Client(schema_name=empresa_slug)` ✅
- [x] Guardar → genera esquema automáticamente (`auto_create_schema=True`) ✅
- [x] Crear dominio principal (`Domain(is_primary=True)`) ✅
- [x] Ejecutar migraciones del tenant automáticamente ✅

#### 3.2. Servicio Interno de Creación de Empresas ✅
- [x] Servicio centralizado en `apps/services/onboarding/empresa_service.py` ✅
- [x] Función `crear_empresa()` que centraliza todo el proceso ✅
- [x] Validaciones de datos (nombre, dominio, email) ✅
- [x] Generación automática de schema_name válido ✅
- [x] Manejo de transacciones para garantizar consistencia ✅
- [x] Función `verificar_empresa()` para validar configuración ✅

#### 3.3. Comando de Management ✅
- [x] Comando `crear_empresa` para facilitar onboarding desde CLI ✅
- [x] Integrado en Makefile como `make crear-empresa` ✅
- [x] Opciones para poblar datos iniciales (opcional) ✅
- [x] Opciones para configurar período de prueba ✅

#### 3.4. Poblamiento Inicial del Tenant ✅
- [x] El catálogo DIAN está en `SHARED_APPS`, disponible para todos los tenants ✅
- [x] No requiere poblamiento específico por tenant ✅
- [x] Si se necesitan datos iniciales por tenant, se pueden agregar al servicio ✅

**Nota:** El proyecto NO usa signals (principio de cero signals), por lo que el poblamiento se hace explícitamente en el servicio si es necesario.

**Uso:**
```bash
# Desde CLI
python manage.py crear_empresa "Mi Empresa S.A." "mi-empresa.localhost" "admin@mi-empresa.com"

# Desde Makefile
make crear-empresa NOMBRE="Mi Empresa S.A." DOMINIO="mi-empresa.localhost" EMAIL="admin@mi-empresa.com"

# Desde código Python
from apps.services.onboarding.empresa_service import crear_empresa
resultado = crear_empresa(nombre="...", dominio="...", email_admin="...")
```

### ✅ Fase 4: APIs REST y Modelos de Negocio por Tenant (COMPLETADA PARCIALMENTE)

#### 4.1. Modelos de Tenant ✅ IMPLEMENTADO
- [x] Modelos de empresa (`apps.tenant.empresa`)
- [x] Modelos de facturas (`apps.tenant.facturas`)
- [x] Modelos de contabilidad (`apps.tenant.contabilidad`)
- [x] Relaciones entre modelos de tenant
- [x] Migraciones de tenant apps

#### 4.2. APIs REST por Tenant ✅ IMPLEMENTADO
- [x] ViewSets y Serializers para todos los modelos de tenant
- [x] Filtrado avanzado con django-filter
- [x] Paginación server-side
- [x] Acciones personalizadas (`@action`)
- [x] Permisos y autenticación por tenant
- [ ] Documentación automática con Swagger/OpenAPI (pendiente)
- [ ] Versionado de APIs (v1, v2, etc.) (pendiente)

### ✅ Fase 5: Sistema de Ingesta y ETL (COMPLETADA - Fases A-D)

#### Fase A: Ingesta (DRF API) ✅ IMPLEMENTADO
- [x] Modelos `DocumentoFuente` y `IngestaLog`
- [x] API REST `/api/public/v1/impuestos/ingesta/`
- [x] Soporte multipart (archivos) y JSON (URLs)
- [x] Validación de tipos y tamaño (máx 50MB)
- [x] Throttling (`impuestos_ingesta`: 20/hour)
- [x] Tareas Celery `descargar_fuente` y `procesar_fuente`
- [x] Detección automática de tipo por extensión/MIME
- [x] Cumplimiento robots.txt y crawl_delay
- [x] Hash SHA256 para deduplicación

#### Fase B: ETL Pipeline ✅ IMPLEMENTADO
- [x] Integración en consola (`/console/impuestos/ingesta/`)
- [x] Listado con filtros y auto-refresh HTMX
- [x] Formulario de creación (archivo/URL)
- [x] Vista de detalle con logs en tiempo real
- [x] Fragmentos HTMX para auto-refresh
- [x] Acciones de reintento (reintentar descarga/procesamiento)

#### Fase C: Exposición y Búsqueda (OpenSearch) ✅ IMPLEMENTADO
- [x] Integración con OpenSearch (opensearch-py)
- [x] Modelo `NormaTributaria` indexado en OpenSearch
- [x] API de búsqueda `/api/public/v1/impuestos/search/`
- [x] Multi-match query con highlighting
- [x] Búsqueda tributaria en consola (`/console/impuestos/search/`)
- [x] Blue/green deployment con alias (`impuestos-docs`)
- [x] Comando `impuestos_reindex --version N` para reindexación
- [x] Bulk indexing con `bulk_index_normas()`

#### Fase D: Operación, Cumplimiento y Observabilidad ✅ IMPLEMENTADO
- [x] **Cumplimiento:**
  - Idempotencia por `hash_sha256` (deduplicación automática)
  - Logging de robots.txt (allow/deny, crawl_delay)
  - User-Agent identificable (`SINTEL-ImpuestosBot/1.0`)
- [x] **Observabilidad:**
  - Endpoint de salud `/api/public/v1/impuestos/search/health/` (solo admin)
  - Logging con `duration_ms` por etapa (descarga, parseo, upsert, indexado)
  - Dashboard de salud en consola (`/console/impuestos/search/health/`)
  - Comando `impuestos_smoke` para smoke testing
- [x] **Resiliencia:**
  - Reintentos con backoff en tareas Celery (`autoretry_for`, `retry_backoff`)
  - DLQ simple (Dead Letter Queue): estado ERROR al alcanzar `max_retries`
  - Logs de errores detallados en `IngestaLog`
- [x] **Operabilidad:**
  - Comando `impuestos_seed` para re-indexación completa
  - Comando `impuestos_export_json` para backups textuales
  - Comando `impuestos_reindex --version N` para blue/green deployment
  - Integración en CI/CD para reindexación y smoke testing

#### 5.2. Dashboard Web (Consola) ✅ IMPLEMENTADO
- [x] Parsers: PDF, HTML, XML, Excel, CSV
- [x] Tokenizador (Artículo/Impuesto/Tema/Vigencia)
- [x] Normalizador (mapeo a entidades canónicas)
- [x] Validadores (porcentajes, códigos, solapes)
- [x] Upserts atómicos con `transaction.atomic()`
- [x] Pipeline orquestado (`run_etl()`)
- [x] Modelo `NormaTributaria` para normas tokenizadas
- [x] Integración Celery con logs detallados

#### 5.3. Captura Multi-Formato ✅ IMPLEMENTADO
- [x] Soporte PDF, XLSX, XLS, CSV, HTML
- [x] Validación de extensiones permitidas
- [x] Límite de tamaño (50MB)
- [x] Descarga por URL respetando robots.txt
- [x] Metadatos rastreados (content_type, extension, size_bytes)

### ✅ Fase 6: Separación API JSON vs UI Templates (COMPLETADA)

#### 6.1. DRF Solo JSON ✅ IMPLEMENTADO
- [x] `BrowsableAPIRenderer` desactivado globalmente
- [x] Solo `JSONRenderer` en `DEFAULT_RENDERER_CLASSES`
- [x] APIs `/api/public/v1/...` devuelven solo JSON (sin HTML)

#### 6.2. UI Dedicada en Templates ✅ IMPLEMENTADO
- [x] Todas las vistas HTML en `/console/impuestos/*` usan templates dedicados
- [x] Vistas consumen APIs JSON con `requests` internamente
- [x] Formularios HTML apuntan a `/api/public/v1/impuestos/ingesta/`
- [x] CSRF habilitado (`{% csrf_token %}`, `X-CSRFToken` header en HTMX)
- [x] Parsers: `MultiPartParser` (archivos), `FormParser` (form-urlencoded), `JSONParser` (JSON)

### ✅ Fase 7: Suite de Pruebas E2E (COMPLETADA)

#### 7.1. Tests End-to-End ✅ IMPLEMENTADO
- [x] Suite completa en `tests/public/impuestos/`
- [x] Fixtures: `conftest.py` (Django DB, Celery eager, CSRF client, OpenSearch fake)
- [x] Tests E2E: `test_ingesta_e2e.py` (multipart, form-urlencoded, JSON, CSRF)
- [x] Tests de API: `test_ingesta_api.py` (throttling, idempotencia, estados)
- [x] Tests de ETL: `test_etl_pipeline.py` (pipeline completo, atomicidad)
- [x] Tests de catálogos: `test_api_readonly.py` (filtros, orden, paginación)
- [x] Tests de búsqueda: `test_search_api.py` (OpenSearch con fake client)
- [x] Tests de operación: `test_ops_health.py` (salud, comandos)
- [x] Dependencias: `pytest`, `pytest-django`, `factory-boy`, `responses`

### ✅ Fase 5: Testing Robusto con TenantTestCase (COMPLETADA)

#### 5.1. Clase Base SintelTenantTestCase ✅ IMPLEMENTADO
- [x] Clase base `SintelTenantTestCase` en `tests/tenant/base_test.py`
  - Hereda de `django_tenants.test.cases.TenantTestCase`
  - Setup automático de tenant, domain, user global, TenantMembership
  - Configuración de `self.client` (Django Client) y `self.api_client` (DRF APIClient) con `HTTP_HOST` correcto
  - Métodos helper: `setup_tenant()`, `setup_domain()`, `setup_user()`, `setup_membership()`
  - Configuración de cookies CSRF y autenticación automática

#### 5.2. Tests de Lógica de Negocio ✅ IMPLEMENTADO
- [x] `tests/tenant/empresa/test_empresa_logic.py`
  - `test_calculo_dv`: Verifica cálculo correcto de dígito verificador para NITs conocidos
  - `test_empresa_singleton`: Verifica patrón singleton (una empresa por tenant)
  - `test_data_isolation_check`: Verifica aislamiento de datos entre tenants (cross-tenant isolation)

#### 5.3. Tests de Seguridad y Acceso ✅ IMPLEMENTADO
- [x] `tests/tenant/dashboard/test_access.py`
  - `test_anonymous_redirect`: Verifica redirección 302 a login para usuarios anónimos
  - `test_cross_tenant_access_denied`: Verifica 403 Forbidden para usuarios sin membresía en el tenant
  - `test_authorized_access`: Verifica 200 OK para usuarios con membresía válida

#### 5.4. Tests de API Pública ✅ IMPLEMENTADO
- [x] `tests/tenant/landing/test_public_api.py`
  - `test_serializer_whitelist`: Verifica que APIs públicas solo exponen datos permitidos (whitelist)
  - Verifica que datos sensibles (NIT, régimen tributario, ID) NO se exponen en APIs públicas
  - Verifica que datos públicos (razón social, logo) SÍ se exponen correctamente

#### 5.5. Mejores Prácticas Implementadas
- [x] **Uso obligatorio de TenantTestCase**: Todos los tests tenant heredan de `SintelTenantTestCase`
- [x] **HTTP_HOST configurado**: Todos los clientes (Client y APIClient) tienen `HTTP_HOST` apuntando al dominio del tenant
- [x] **Aislamiento de datos verificado**: Tests validan que los datos de un tenant no son accesibles desde otro
- [x] **Seguridad validada**: Tests verifican permisos, redirecciones y acceso cross-tenant
- [x] **Privacidad de datos**: Tests verifican que APIs públicas no exponen información sensible

**Referencias:**
- `documentacion/DJANGO_TENANTS_PLAYBOOK_SINTEL.md`: Guía completa de testing con django-tenants
- `documentacion/DJANGO_5_PLAYBOOK_SINTEL.md`: Mejores prácticas de testing en Django 5.0

### ✅ Fase 1: Blindaje del Login (COMPLETADA)

#### 1.1. Formulario de Autenticación Seguro ✅ IMPLEMENTADO
- [x] `TenantAuthenticationForm` en `apps/tenant/landing/forms.py`
  - Hereda de `django.contrib.auth.forms.AuthenticationForm`
  - Método `clean()` que distingue entre:
    - **Credenciales inválidas** → Error genérico de Django
    - **Credenciales válidas pero sin membresía** → Mensaje específico sobre acceso
  - Mensaje específico: "Tu cuenta existe, pero no tienes acceso a la empresa [NombreTenant]. Contacta a tu administrador."
  - Método `confirm_login_allowed()` con validación de membresía en tenant actual
  - Validación de tenant activo (no suspendido)

#### 1.2. API de Login (API-First) ✅ IMPLEMENTADO (v2.30)
- [x] ⚠️ v2.30: `TenantLoginView` ELIMINADO - Funcionalidad movida a `POST /api/v1/landing/auth/login/`
  - `TenantLoginAPIView` en `apps/tenant/landing/api/views.py`
  - Usa `TenantLoginSerializer` para validar credenciales y membresía
  - Template: `tenant/landing/login.html`
  - `redirect_authenticated_user = True` (redirige si ya está logueado)
  - Redirección forzosa a `/dashboard/` con `reverse_lazy('tenant_dashboard:index')`
  - Contexto con `tenant_name` y `tenant_logo` para personalización
  - **Ubicación**: `apps/tenant/landing/views.py`

#### 1.3. Template de Login Moderno ✅ IMPLEMENTADO
- [x] Template `tenant/landing/login.html`
  - Diseño moderno con Tailwind CSS
  - Centrado vertical y horizontal (`min-h-screen flex items-center justify-center`)
  - Tarjeta blanca con sombra suave y header con gradiente
  - Muestra logo/nombre de la empresa en el header
  - Campos `username` y `password` estilizados con Tailwind
  - Botón "Ingresar" ancho completo con color primario (indigo-600)
  - Manejo de errores con alerta roja clara encima del formulario
  - Mensajes de error específicos sobre membresía vs. credenciales
  - Enlace de regreso a la landing page
  - Responsive y accesible
  - **Ubicación**: `apps/tenant/landing/templates/tenant/landing/login.html`

#### 1.4. Backend de Autenticación Tenant-Aware ✅ IMPLEMENTADO
- [x] `TenantAwareBackend` en `apps/public/tenants/auth_backend.py`
  - Hereda de `django.contrib.auth.backends.ModelBackend`
  - Método `authenticate()` que valida:
    1. Credenciales usando backend estándar
    2. Contexto del request (permite acceso sin tenant para comandos de consola)
    3. Esquema público (permite acceso sin membresía)
    4. Membresía activa en tenant actual
  - Si no tiene membresía: retorna `None` + log warning de seguridad
  - Manejo de errores: restaura esquema y rechaza login por seguridad
  - Registrado en `AUTHENTICATION_BACKENDS` (primero en la lista)
  - **Ubicación**: `apps/public/tenants/auth_backend.py`
  - **Configuración**: `config/settings.py` (línea 164-167)

#### 1.5. Tests de Seguridad ✅ IMPLEMENTADO
- [x] `tests/tenant/landing/test_login_security.py`
  - **Escenario A**: Acceso legítimo (usuario con membresía → 302 Redirect)
  - **Escenario B**: Intrusión cross-tenant (usuario sin membresía → Formulario inválido)
  - **Escenario C**: Usuario sin membresía (formulario inválido con mensaje específico)
  - **Escenario D**: Credenciales inválidas (test de control)
  - **Escenario E**: Tenant público permite acceso (sin membresía)
- [x] `tests/public/tenants/test_auth_backend.py`
  - Tests unitarios del backend de autenticación
  - Validación de barrera de backend (nivel API/Core)
  - Validación de fallback para comandos de consola
  - Validación de acceso al tenant público
- [x] `tests/tenant/security/test_full_integration.py`
  - **Test de Garantía Total**: Valida integración completa de todos los componentes
  - **Test 1**: Barrera de Backend (Nivel API/Core)
  - **Test 2**: Feedback de Formulario (Nivel UX)
  - **Test 3**: Acceso Exitoso y Perfil (Happy Path)
  - **Test 4**: Protección de Tenant Público
  - **Test 5**: Aislamiento Cruzado (Cross-Check)

#### 1.6. Características de Seguridad Implementadas
- [x] **Doble Capa de Validación**:
  - Backend: Bloquea acceso sin membresía a nivel de autenticación
  - Formulario: Valida y proporciona feedback preciso al usuario
- [x] **Mensajes de Error Específicos**:
  - Distingue entre "contraseña incorrecta" y "no autorizado en este tenant"
  - Evita confusión del usuario sobre el motivo del fallo
- [x] **Logging de Seguridad**:
  - Registra intentos de acceso cruzado con detalles (usuario, tenant, timestamp)
  - Facilita auditoría de seguridad
- [x] **Aislamiento Multi-Tenant**:
  - Usuarios solo pueden acceder a tenants donde tienen membresía
  - Validado en múltiples capas (backend, formulario, vista)

### ✅ Fase 2: Perfil Privado del Colaborador (COMPLETADA)

#### 2.1. Modelo de Perfil ✅ IMPLEMENTADO (v2.31: Cargo Opcional)
- [x] `TenantProfile` en `apps/tenant/perfil/models.py`
  - Relación `OneToOneField` con `settings.AUTH_USER_MODEL` (related_name='tenant_profile')
  - Campos:
    - `cargo`: CharField (opcional, `blank=True, null=True`) - ⚠️ v2.31: Cambiado a opcional
    - `departamento`: CharField (opcional)
    - `telefono_corporativo`: CharField (opcional)
    - `avatar`: ImageField (upload_to='perfiles/avatars/', opcional)
    - `configuracion`: JSONField (default `{}`) para preferencias de UI
    - `created_at`, `updated_at`: Timestamps automáticos
  - Método `__str__` retornando `f"{self.user.email} - {self.cargo}"`
  - **Ubicación**: `apps/tenant/perfil/models.py`
  - **App registrada**: `apps.tenant.perfil` en `TENANT_APPS`
  - **Migración**: `0003_make_cargo_optional.py` (v2.31)

#### 2.2. Capa de Servicio ✅ IMPLEMENTADO
- [x] `perfil_service.py` en `apps/services/perfil/perfil_service.py`
  - Función `obtener_o_crear_perfil(user, defaults=None)`:
    - Intenta obtener el perfil del usuario en el tenant actual
    - Si no existe, lo crea con valores por defecto
    - Reemplaza el uso de señales `post_save`
  - Función `actualizar_configuracion_ui(user, clave, valor, merge=True)`:
    - Actualiza el JSONField de configuración de forma segura
    - Preserva valores existentes si `merge=True`
    - Permite actualizar claves individuales o reemplazar toda la configuración
  - **Ubicación**: `apps/services/perfil/perfil_service.py`

#### 2.3. API Serializers ✅ IMPLEMENTADO (v2.31: Serializer de Actualización Parcial)
- [x] `TenantProfileSerializer` en `apps/tenant/perfil/api/serializers.py`
  - Incluye todos los campos del perfil
  - Campos nested del User global (user_id, user_email, user_username, user_first_name, user_last_name) como solo lectura
  - Validación del campo `configuracion` (debe ser dict, normaliza `None` a `{}`)
  - **Ubicación**: `apps/tenant/perfil/api/serializers.py`
- [x] `TenantProfileMeUpdateSerializer` en `apps/tenant/perfil/api/serializers.py` (v2.31)
  - Serializer específico para PATCH `/api/v1/perfil/perfiles/me/`
  - Solo incluye campos editables: `cargo`, `departamento`, `telefono_corporativo`, `configuracion`
  - Todos los campos son opcionales (`allow_blank=True, allow_null=True`)
  - Normaliza strings vacíos a `None` para campos opcionales
  - Valida que `configuracion` sea dict (normaliza `None` a `{}`)
  - **Uso**: Usado por `PerfilViewSet.me()` para actualización parcial

#### 2.4. API ViewSet ✅ IMPLEMENTADO (v2.31: CSRF Relajado en Desarrollo)
- [x] `PerfilViewSet` en `apps/tenant/perfil/api/viewsets.py`
  - Hereda de `viewsets.ModelViewSet`
  - Acción `me` (GET/PATCH): `/api/v1/perfil/perfiles/me/`
    - GET: Retorna el perfil del usuario actual (lo crea si no existe)
    - PATCH: Actualiza el perfil del usuario actual usando `TenantProfileMeUpdateSerializer`
    - Soporta `application/json` y `multipart/form-data` (para avatar)
  - Acción `me_configuracion` (PATCH): `/api/v1/perfil/perfiles/me/configuracion/`
    - Actualiza solo el campo `configuracion` (JSONField) de forma segura
  - Acción `me_avatar` (PATCH): `/api/v1/perfil/perfiles/me/avatar/`
    - Actualiza solo el avatar del perfil
  - Usa `perfil_service.obtener_o_crear_perfil` para garantizar que el objeto exista
  - Permisos: `IsAuthenticated`, `IsTenantMember`, `IsOwnerOrReadOnly` (cross-tenant isolation)
  - **Autenticación (v2.31):**
    - En `DEBUG=True`: `UnsafeSessionAuthentication` (CSRF relajado para desarrollo)
    - En `DEBUG=False`: `SessionAuthentication` (CSRF estricto para producción)
    - Método `get_authenticators()` retorna la clase apropiada según entorno
  - **Ubicación**: `apps/tenant/perfil/api/viewsets.py`

#### 2.5. URLs y Configuración ✅ IMPLEMENTADO
- [x] URLs registradas en `apps/tenant/perfil/api/urls.py`
  - Router DRF con `basename='perfil'`
  - Endpoints generados automáticamente
- [x] Ruta registrada en `config/urls_tenant.py`
  - `path('api/v1/perfil/', include('apps.tenant.perfil.api.urls'))`
- [x] App registrada en `config/settings.py`
  - `apps.tenant.perfil` agregado a `TENANT_APPS`

#### 2.6. Tests de Perfil ✅ IMPLEMENTADO
- [x] `tests/tenant/perfil/test_perfil.py`
  - **Test A**: Crear perfil vía Service Layer
  - **Test B**: Consumir endpoint `/me/` y verificar datos combinados (User global + Perfil local)
  - **Test C**: Verificar aislamiento entre tenants (mismo usuario, diferentes perfiles)
  - Tests adicionales: obtener perfil existente, actualizar configuración UI

#### 2.7. Características Implementadas
- [x] **Service Layer Pattern**: Lógica de negocio en `apps/services/perfil/perfil_service.py`
- [x] **Cero Signals**: Toda la lógica es explícita
- [x] **Aislamiento Multi-Tenant**: django-tenants maneja automáticamente el aislamiento por esquema
- [x] **API-First**: Endpoints RESTful con DRF
- [x] **Datos Combinados**: Serializer incluye datos del User global (nested) como solo lectura
- [x] **Configuración JSON**: Campo `configuracion` (JSONField) para preferencias de UI sin crear tablas extra

### ✅ Fase 8: Auditoría y Refactor Seguro (COMPLETADA)

#### 8.1. Herramientas de Auditoría ✅ IMPLEMENTADO
- [x] `pyproject.toml` configurado con Ruff (linter/formatter ultrarrápido)
  - Reglas: E (pycodestyle), F (pyflakes), B (bugbear), I (isort), UP (pyupgrade), SIM (simplify)
  - Auto-fix habilitado para correcciones seguras
- [x] `Makefile` actualizado con targets de auditoría
  - `make audit`: Ejecuta todas las auditorías (ruff, bandit, dj-check, static-check)
  - `make ruff`: Linter y formatter con auto-fix
  - `make bandit`: Análisis de seguridad SAST
  - `make dj-check`: Django System Check (`check --deploy`)
  - `make static-check`: Validación de archivos estáticos (`collectstatic --dry-run`)
- [x] Dependencias de desarrollo: `ruff`, `bandit`, `pytest`, `pytest-django`

#### 8.2. Tests Funcionales Adicionales ✅ IMPLEMENTADO
- [x] `test_links_templates.py`: Verificación de enlaces y templates
  - Tests para todas las páginas de consola (`/console/impuestos/*`)
  - Validación de status 200 y uso correcto de templates con `assertTemplateUsed`
- [x] `test_crud_tipos.py`: Tests CRUD completos de TipoImpuesto
  - Crear, editar, listar, obtener detalle, borrar vía API CRUD
  - Validación de autenticación requerida
- [x] `test_datatables_tipos.py`: Tests para DataTables server-side
  - Validación de formato de respuesta DataTables (draw, recordsTotal, recordsFiltered, data)
  - Paginación, búsqueda y ordenamiento
- [x] `test_queries_perf.py`: Tests de performance para evitar queries N+1
  - Validación con `assertNumQueries` para mantener límites de queries
  - Verificación de optimizaciones con `select_related`/`prefetch_related`

#### 8.3. Refactors Seguros ✅ IMPLEMENTADO
- [x] **URLs hardcodeadas corregidas**
  - `apps/public/console/views.py`: `'/admin/login/'` → `reverse('admin:login')`
  - Uso consistente de `reverse()` en lugar de URLs hardcodeadas en Python
  - Uso de `{% url %}` en templates en lugar de URLs hardcodeadas
- [x] **Código zombie/duplicado**
  - Ruff detecta y corrige automáticamente imports no usados (F401)
  - Detección de código duplicado y simplificable (SIM)
- [x] **Validaciones/consultas optimizadas**
  - Análisis de queries N+1 con tests de performance
  - Uso de `select_related`/`prefetch_related` donde es necesario
  - Tests con `assertNumQueries` para mantener límites

#### 8.4. Verificación de Enlaces y Estáticos ✅ IMPLEMENTADO
- [x] Verificación de enlaces internos en templates (`href`, `action`, `url`)
  - Tests funcionales validan que todas las páginas carguen correctamente
- [x] Validación de archivos estáticos
  - `collectstatic --dry-run` verifica referencias en templates
  - `findstatic` confirma rutas de assets (CSS/JS/img)

#### 8.5. Pipeline de Pruebas ✅ IMPLEMENTADO
```bash
# Auditoría completa
make audit

# Tests funcionales
pytest tests/public/impuestos/test_links_templates.py -v
pytest tests/public/impuestos/test_crud_tipos.py -v
pytest tests/public/impuestos/test_datatables_tipos.py -v
pytest tests/public/impuestos/test_queries_perf.py -v
```

### ✅ Fase 9: CRUD + Onboarding de Tenants (COMPLETADA)

#### 9.1. Modelo de Membresía ✅ IMPLEMENTADO
- [x] `TenantMembership` en `apps/public/tenants/models.py`
  - Relación Client ↔ User con roles (ADMIN, STAFF, USER)
  - Campo `is_primary_admin` para identificar admin principal
  - `unique_together` para evitar membresías duplicadas
  - Índices optimizados (`client`, `user`)
- [x] Migración creada (ejecutar: `makemigrations tenants && migrate_schemas --shared`)

#### 9.2. Servicio de Onboarding ✅ IMPLEMENTADO
- [x] Función `crear_tenant()` en `apps/services/onboarding/empresa_service.py` ✅ v2.13 + v2.19
  - **Firma actualizada:** `crear_tenant(nombre, admin_user_id, schema_name=None, ...)`
  - **⚠️ v2.17:** Ya no recibe `dominio` como parámetro - todos los tenants usan subdominios automáticos
  - Genera `schema_name` automáticamente desde `nombre` si no se proporciona
  - Crea Client (dispara `auto_create_schema=True` y la señal `post_save` crea Domain automáticamente)
  - **⚠️ IMPORTANTE:** `auto_create_schema` es un atributo de clase del modelo `Client`, NO se pasa como argumento al constructor
  - Ejecuta migraciones del tenant
  - Asigna admin global como `TenantMembership` con `is_primary_admin=True` e `is_active=True`
  - **⚠️ v2.19: Aprovisionamiento Atómico "Zero-Orphan":**
    - Todo el proceso envuelto en `@transaction.atomic` (decorador de función)
    - Si falla cualquier paso (Client, Domain, Membership, Profile), TODO se revierte automáticamente
    - Manejo robusto de errores con try/except específico para `TenantMembership` y logging detallado
    - Previene completamente la creación de tenants "huérfanos" sin administrador ni perfil asociado
  - **Creación inmediata de perfil de colaborador (`TenantProfile`)**:
    - Usa `with tenant_context(client):` para cambiar al esquema del tenant
    - Invoca `obtener_o_crear_perfil(user=admin_user, defaults=...)` desde `apps.services.perfil.perfil_service`
    - Crea un perfil por defecto con rol "Administrador Principal" y configuración inicial (`theme`, `notifications`, etc.)
  - **Construcción de `login_url` (v2.18 + v2.19):**
    - En desarrollo (`DEBUG=True`): Si existe un dominio con puerto (`{schema}.{TENANT_DOMAIN_BASE}:{APP_PORT}`) lo usa; si no, lo construye manualmente
    - En producción: Usa dominio sin puerto (`{schema}.{TENANT_DOMAIN_BASE}`)
    - El `login_url` devuelto apunta SIEMPRE a la raíz del tenant (`http://cliente.localhost:8000/` o `https://cliente.sintel.com/`), donde se muestra la landing con el botón de login
  - Retorna `(client, domain, login_url)` para acceso inmediato a la landing del tenant
  - Compatible con `crear_empresa()` existente (extiende funcionalidad)
- [x] Generación automática de `schema_name` desde nombre (slugify)
- [x] Validaciones de dominio y schema_name únicos
- [x] **Normalización de dominios (v2.13 + v2.19):**
  - Función `normalize_domain()` en `apps/public/tenants/utils.py`
  - Elimina protocolo (`http://`, `https://`)
  - Elimina prefijo `www.`
  - Elimina rutas y barras finales (`/admin/login/` → dominio limpio)
  - **⚠️ v2.19: Manejo de puertos según entorno:**
    - En desarrollo (`DEBUG=True`): **MANTIENE** el puerto si viene en el string (ej: `cliente.sintel.com:8000`)
    - En producción (`DEBUG=False`): Elimina el puerto como antes (ej: `cliente.sintel.com`)
    - Resuelve el problema de django-tenants que busca coincidencia exacta del hostname
  - Convierte a minúsculas
  - Valida FQDN (RFC 1035, máximo 253 caracteres)
- [x] Tarea Celery `onboard_tenant_task` ejecuta `crear_tenant()` en el esquema `public` y retorna `login_url` apuntando a la raíz del tenant
- [x] **Configuración de Colas Prioritarias:**
  - `onboard_tenant_task` enrutada a cola `high_priority` en `CELERY_TASK_ROUTES`
  - Worker de Celery configurado para escuchar `high_priority,default` en `docker-compose.yaml`
  - Entrypoint específico `entrypoint-celery.sh` para el contenedor Celery
- [x] **Logging Detallado:**
  - Logging en `tenants_create` para diagnóstico de errores
  - Logging en `onboard_tenant_task` para seguimiento de ejecución
- [x] **Script de Diagnóstico Forense:**
  - Comando `python manage.py debug_tenant_creation` para diagnóstico paso a paso
  - Valida configuración, creación síncrona, Celery eager mode y cola real

#### 9.3. API Admin (CRUD + Onboard) ✅ IMPLEMENTADO
- [x] Estructura `apps/public/tenants/api_admin/`
  - **Serializers**: `ClientSerializer`, `DomainSerializer`, `TenantMembershipSerializer`, `OnboardTenantSerializer`, `OnboardAsyncSerializer`
  - **ViewSets**: `ClientAdminViewSet` (con acción `onboard` y `toggle-status`), `DomainAdminViewSet`, `MembershipAdminViewSet`
  - **DataTables**: `TenantDataTablesView` para server-side processing
  - **URLs**: Registrado en `/api/admin/v1/tenants/` (solo staff)
- [x] **Estandarización de Dominios (Capa API)** ✅ IMPLEMENTADO (v2.13)
  - **Validación en Serializers:** Todos los endpoints de creación de tenants implementan normalización estricta en `apps/public/tenants/api/serializers.py` y `apps/public/tenants/api_admin/serializers.py`
  - **Función Helper:** `apps/public/tenants/utils.py` contiene `normalize_domain()` y `validate_fqdn()`
  - **Regla de Transformación:**
    * `lower()`: Todo a minúsculas
    * `strip()`: Sin espacios al inicio/final
    * `remove_protocol`: Se eliminan `http://` y `https://`
    * `remove_www`: Se elimina prefijo `www.` (opcional, para estandarizar)
    * `remove_path`: Se eliminan barras finales `/` y rutas
    * `remove_port`: Se eliminan puertos (ej: `:8000`) **SOLO en producción** - En desarrollo se mantienen
  - **Validación FQDN:** Se valida que el dominio sea un FQDN válido (RFC 1035, máximo 253 caracteres, debe contener al menos un punto)
  - **Objetivo:** Garantizar que `Domain.domain` siempre contenga un FQDN válido y limpio (ej: `cliente.sintel.com`) utilizable para enrutamiento `django-tenants`
  - **Aplicación:** Se aplica en:
    * `DomainSerializer.validate_domain()` (ambos: `api/serializers.py` y `api_admin/serializers.py`)
    * `OnboardTenantSerializer.validate_dominio()`
    * `OnboardAsyncSerializer.validate_dominio()`
    * `crear_tenant()` en `empresa_service.py` (normaliza antes de guardar)
  - **Construcción de `login_url` (v2.13 + v2.19):**
    * **Ubicación:** `apps/services/onboarding/empresa_service.py` en función `crear_tenant()`
    * **Lógica actualizada:**
      - Usa el dominio principal del tenant:
        - En desarrollo (`DEBUG=True`): prioriza `Domain.domain="{schema}.{TENANT_DOMAIN_BASE}:{APP_PORT}"` si existe
        - En producción (`DEBUG=False`): usa `{schema}.{TENANT_DOMAIN_BASE}` sin puerto
      - Determina protocolo según `DEBUG` y `SECURE_SSL_REDIRECT`
      - Construye una URL absoluta apuntando a la **raíz** del tenant: `"{protocol}://{login_domain}/"`
    * **Objetivo:** Garantizar que el `login_url` siempre apunte a la landing del tenant (no a `/admin/login/`), preservando dominio y puerto en desarrollo y separando el login de tenant del login del admin público
  - **Ejemplos de Normalización:**
    * `"HTTPS://Mi.Empresa.Com/"` → `"mi.empresa.com"`
    * `"http://www.cliente.sintel.com:8000/admin/"` → `"cliente.sintel.com"`
    * `"  cliente.sintel.com  "` → `"cliente.sintel.com"`
- [x] Endpoint de onboarding: `POST /api/admin/v1/tenants/onboard/`
  - Parámetros: `nombre`, `schema_name`, `dominio` (opcional, normalizado automáticamente), `admin_user_id`
  - Si no se proporciona `dominio`, se genera automáticamente basado en `schema_name`
  - Retorna: `client`, `domain`, `login_url`
- [x] Endpoint DataTables: `POST /api/admin/v1/dt/tenants/` (v2.11: cambiado a POST)
  - Formato estándar DataTables: `draw`, `recordsTotal`, `recordsFiltered`, `data`
  - Paginación, búsqueda (nombre, schema_name), ordenamiento

#### 9.4. Consola /console/tenants/ (UI + DataTables + Suspensión) ✅ IMPLEMENTADO Y FUNCIONAL
- [x] **Vistas de consola** (`apps/public/console/views.py`):
  - `tenants_list`: Lista con DataTables server-side
  - `tenants_new_page`: Formulario para crear tenant con campos:
    - `nombre`: Nombre de la empresa (requerido)
    - `schema_name`: Código del tenant (requerido, validado con `validate_schema_name`)
    - `dominio`: Dominio principal (opcional, si no se proporciona se genera automáticamente)
    - `admin_user_id`: Usuario administrador existente (requerido, select de usuarios)
  - `tenants_create`: Procesa POST, encola tarea Celery y redirige a página de estado
  - `tenants_status_page`: Muestra estado de creación con polling HTMX
- [x] **Flujo completo funcional:**
  - ✅ Formulario en `/console/tenants/new/` captura datos correctamente
  - ✅ Vista `tenants_create` valida datos y encola tarea Celery en cola `high_priority`
  - ✅ Worker de Celery procesa tarea inmediatamente (no queda en PENDING)
  - ✅ Polling HTMX actualiza estado automáticamente hasta completar
  - ✅ Redirección a página de estado con `task_id` para seguimiento
  - ✅ Logging detallado para diagnóstico de errores
- [x] **URLs** (`apps/public/console/urls.py`):
  - `/console/tenants/` → lista con DataTables
  - `/console/tenants/new/` → formulario de creación
  - `/console/tenants/create/` → procesa creación (POST) y redirige a status
  - `/console/tenants/status/` → página de estado con polling HTMX
- [x] **Templates** (`console/pages/tenants/`):
  - `list.html`: DataTables server-side con estilos Tailwind CSS (v2.11: actualizado con suspensión)
    - Columnas: ID, Empresa, Schema, Dominio, Admin, Trial (badges 🟡 Trial / 🔵 Activo), Estado (badges ✓ Activo / ⚠ SUSPENDIDO), Creado, Vence
    - Botones de acción: 🔗 Acceder, ✏️ Editar (admin Django), ⏸️ Pausar/▶️ Reanudar (v2.11), 🗑️ Borrar, 📧 Reenviar Token (v2.30)
    - Botón Pausar/Reanudar: Oculto para tenant público (protección UI)
    - Botón Reenviar Token (v2.30): Reenvía token de activación del owner desde la consola
      - Endpoint: `POST /api/admin/v1/console/tenants/{tenant_id}/owner/resend-activation/`
      - Validaciones: v2.29 (una sola activación), rate limiting, auditoría
      - Opciones: Enviar email automáticamente o solo generar token (dry_run)
    - Función `toggleTenantStatus()`: Conectada a API con autenticación JWT
    - Actualización automática de tabla tras cambio de estado
    - Búsqueda, paginación (10, 25, 50, 100, Todos), ordenamiento
    - Mensajes con badges de colores (éxito/error/info)
  - `new.html`: Formulario con validación:
    - `nombre`: Nombre de la empresa (requerido)
    - `schema_name`: Código del tenant (requerido, validado con `validate_schema_name`)
    - `dominio`: Dominio principal (opcional, si no se proporciona se genera automáticamente por la señal)
      - **Normalización automática (v2.13):** El dominio se normaliza en el serializer antes de llegar al servicio
      - Se eliminan protocolos, puertos, rutas, y se convierte a minúsculas
    - `admin_user_id`: Usuario administrador existente (requerido, select de usuarios)

#### 9.6. Acceso a Tenants (Landing Page, Login & Routing) ✅ IMPLEMENTADO (v2.19)
- [x] **Configuración de URLs (`config/urls_tenant.py`):**
  - ⚠️ v2.30: `path('', include('apps.tenant.landing.urls'))` DESHABILITADO - Vistas HTML eliminadas, toda la funcionalidad en `/api/v1/landing/`
  - Dashboard: `path('dashboard/', include('apps.tenant.dashboard.urls', namespace='tenant_dashboard'))` → Dashboard del tenant
  - Admin de tenant (oculto): `path('soporte-tecnico-seguro/', tenant_admin_site.urls)` → Panel de admin aislado por tenant
  - Trampa de seguridad: `path('admin/', tenant_admin_trap, ...)` redirige cualquier intento de acceder a `/admin/` en un tenant privado hacia la landing (`/`)
  - APIs REST: `/api/v1/*` → APIs del tenant
  - JWT: `/api/token/*` → Autenticación JWT (por tenant)
- [x] **APIs REST de Landing (`apps/tenant/landing/api/`)** ⚠️ v2.30
  - `GET /api/v1/landing/info/` → `LandingInfoView` - Información pública del tenant
  - `POST /api/v1/landing/auth/login/` → `TenantLoginAPIView` - Login con validación de membresía
  - `GET /api/v1/landing/auth/activate/?token=...` → `OwnerActivationAPIView` - Validar token de activación
  - `POST /api/v1/landing/auth/activate/?token=...` → `OwnerActivationAPIView` - Procesar activación (establecer/actualizar password)
  - Serializers: `TenantPublicInfoSerializer`, `TenantLoginSerializer`, `OwnerActivationSerializer`
- [x] **Vistas HTML ELIMINADAS** ⚠️ v2.30
  - `apps/tenant/landing/urls.py` - ELIMINADO
  - `apps/tenant/landing/views.py` - ELIMINADO
  - Referencias en `config/urls_tenant.py` comentadas
  - Toda la funcionalidad se maneja exclusivamente mediante APIs REST
  - El frontend debe consumir las APIs REST para landing, login y activación
- [x] **Formulario de Autenticación Seguro (`apps/tenant/landing/forms.py`):**
  - `TenantAuthenticationForm(AuthenticationForm)`:
    * En `clean()`: diferencia entre password incorrecto y usuario sin membresía en el tenant actual
    * En `confirm_login_allowed()`: valida `TenantMembership` en el esquema `public` usando `connection.set_schema_to_public()`
    * Si no hay membresía activa o el tenant está suspendido, lanza `ValidationError` con mensaje claro
- [x] **Configuración de Seguridad (`config/settings.py`):**
  - `LOGIN_URL = '/login/'` (relativo, preserva dominio y puerto del tenant)
  - `LOGOUT_REDIRECT_URL = '/'` (vuelve a la landing del dominio actual)
  - `TENANT_DOMAIN_BASE` dinámico:
    * Desarrollo (`DEBUG=True`): `_default_tenant_domain_base = 'localhost'` → subdominios `{schema}.localhost`
    * Producción (`DEBUG=False`): `_default_tenant_domain_base = 'sintel.com'` → subdominios `{schema}.sintel.com`
  - `ALLOWED_HOSTS` basado en `TENANT_DOMAIN_BASE` (`.{TENANT_DOMAIN_BASE}`, `TENANT_DOMAIN_BASE`, `localhost`, `127.0.0.1`)
- [x] **Flujo de Acceso:**
  1. Usuario accede a `http://home.localhost:8000`
  2. `TenantMainMiddleware` identifica el tenant por dominio `home.localhost`
  3. Django usa `TENANT_URLCONF = 'config.urls_tenant'`
  4. ⚠️ v2.30: `path('', include('apps.tenant.landing.urls'))` DESHABILITADO - Vistas HTML eliminadas
  5. El frontend debe consumir `/api/v1/landing/info/` para obtener datos del tenant
  6. El frontend debe consumir `/api/v1/landing/auth/login/` para autenticación
  7. El frontend debe consumir `/api/v1/landing/auth/activate/` para activación
  8. Toda la funcionalidad se maneja exclusivamente mediante APIs REST

#### 9.7. Tests Funcionales ✅ IMPLEMENTADO
- [x] `tests/public/tenants/test_onboard.py`:
  - Verifica que `onboard` crea Client, Domain y TenantMembership correctamente
  - Valida autenticación requerida (401/403)
  - Valida datos requeridos (400 si faltan campos)
- [x] `tests/public/tenants/test_console_pages.py`:
  - Verifica carga de páginas (`tenants_list`, `tenants_new`) con status 200
  - Valida que `create` redirige si no es POST
  - Verifica que `tenants_list` requiere staff (403)
- [x] `tests/public/tenants/test_datatables_tenants.py`:
  - Valida formato de respuesta DataTables (draw, recordsTotal, recordsFiltered, data)
  - Verifica búsqueda (filtra por nombre/schema_name)
  - Valida autenticación requerida (401/403)
- [x] `tests/public/tenants/test_tenant_suspension.py` (v2.11): Suite completa de tests funcionales
  - **Regresión**: Estado por defecto (`is_active=True`) y acceso permitido
  - **Bloqueo**: Middleware bloquea tenants suspendidos (403) con mensaje HTML
  - **Seguridad**: Tenant público nunca se bloquea (incluso con `is_active=False` forzado)
  - **API**: Toggle status, múltiples toggles, protección del tenant público
  - **Integración**: Flujo completo E2E (crear → suspender → verificar → reactivar)
  - 11 tests cubriendo todos los escenarios críticos

#### 9.6. Acceso a Tenants (Landing Page & Routing) ✅ IMPLEMENTADO (v2.13)
- [x] **Configuración de URLs (`config/urls_tenant.py`):**
  - ⚠️ v2.30: `path('', include('apps.tenant.landing.urls'))` DESHABILITADO - Vistas HTML eliminadas, toda la funcionalidad en `/api/v1/landing/`
  - Dashboard: `path('dashboard/', include('apps.tenant.dashboard.urls'))` → Dashboard del tenant
  - Admin: `path('admin/', admin.site.urls)` → Login disponible en `/admin/login/`
  - APIs REST: `/api/v1/*` → APIs del tenant
  - JWT: `/api/token/*` → Autenticación JWT
- [x] **Vista de Landing (`apps/tenant/landing/views.py`):**
  - `TenantLandingView`: Vista de landing page para tenants privados
  - **Lógica:**
    * Si `request.user.is_authenticated`: Redirige a `tenant_dashboard:index`
    * Si NO está autenticado: Renderiza `tenant/landing/index.html`
  - **Contexto:**
    * `tenant_name`: Nombre del tenant (de `request.tenant.nombre`)
    * `tenant`: Objeto completo del tenant
    * `login_url`: URL de login (`admin:login` → `/admin/login/`)
- [x] **Template de Landing (`apps/tenant/landing/templates/tenant/landing/index.html`):**
  - Muestra `{{ tenant_name }}` (nombre del tenant)
  - Botón "Iniciar Sesión" que apunta a `{{ login_url }}`
  - Diseño con Tailwind CSS, responsive y moderno
- [x] **Configuración de Seguridad (`config/settings.py`):**
  - `ALLOWED_HOSTS = ["*"]` en desarrollo (permite dominios arbitrarios)
  - django-tenants valida el dominio contra la base de datos, así que es seguro
  - En producción: `ALLOWED_HOSTS = [".sintel.com", "sintel.com", "localhost", "127.0.0.1"]`
- [x] **Flujo de Acceso:**
  1. Usuario accede a `http://home.com:8000`
  2. `TenantMainMiddleware` identifica el tenant por dominio `home.com`
  3. Django usa `TENANT_URLCONF = 'config.urls_tenant'`
  4. Resuelve `path('', ...)` → `TenantLandingView`
  5. Si está autenticado: Redirige a `/dashboard/`
  6. Si no está autenticado: Muestra landing page con botón "Iniciar Sesión"
- [x] **Paso Manual Obligatorio:**
  - Editar archivo hosts del sistema para que `home.com` resuelva a `127.0.0.1`
  - Windows: `C:\Windows\System32\drivers\etc\hosts`
  - Mac/Linux: `/etc/hosts`
  - Agregar: `127.0.0.1   home.com`

#### 9.7. Características Implementadas ✅
- [x] **DataTables server-side** con paginación, búsqueda y ordenamiento
- [x] **Badges de estado** visuales (Trial/Activo) con colores
- [x] **Formateo de datos**:
  - Fechas en formato `dd/mm/yyyy`
  - Dominios como código (`<code>`)
  - Admin como email (o "Sin admin" si no hay)
- [x] **Botones de acción** con iconos y tooltips
- [x] **Mensajes de usuario** con badges de colores (éxito/error/info)
- [x] **Seguridad**: Solo staff puede acceder (`IsAdminUser`, `_check_staff_or_raise`)
- [x] **URLs dinámicas**: Uso de `reverse()` y `{% url %}` (sin hardcoding)
- [x] **✅ VERIFICADO:** Flujo completo funcional desde `/console/tenants/new/` sin fallos
  - Creación de tenants operativa
  - Worker de Celery procesa tareas inmediatamente
  - Polling HTMX actualiza estado correctamente
- [x] **✅ VERIFICADO:** Flujo completo funcional desde `/console/tenants/new/` sin fallos
  - Creación de tenants operativa
  - Worker de Celery procesa tareas inmediatamente
  - Polling HTMX actualiza estado correctamente

#### 9.7. Endpoints API Admin Disponibles
```
POST   /api/admin/v1/tenants/onboard/          # Crear tenant (onboarding)
GET    /api/admin/v1/tenants/                  # Listar tenants
POST   /api/admin/v1/tenants/                  # Crear tenant (CRUD)
GET    /api/admin/v1/tenants/{id}/             # Detalle de tenant
PUT    /api/admin/v1/tenants/{id}/             # Actualizar tenant
PATCH  /api/admin/v1/tenants/{id}/             # Actualizar parcialmente
DELETE /api/admin/v1/tenants/{id}/             # Eliminar tenant
POST   /api/admin/v1/tenants/{id}/toggle-status/  # Toggle is_active (v2.11)
GET    /api/admin/v1/dt/tenants/               # DataTables server-side
GET    /api/admin/v1/tenant-domains/           # Listar dominios
GET    /api/admin/v1/tenant-memberships/       # Listar membresías
```

#### 9.8. Próximos Pasos
```bash
# Crear migración para TenantMembership
python manage.py makemigrations tenants
python manage.py migrate_schemas --shared

# Ejecutar tests
pytest tests/public/tenants/ -v
```

### ✅ Fase 10: Dockerización "Prod-like" + Pruebas E2E (COMPLETADA)

#### 10.1. Estructura Docker ✅ IMPLEMENTADO
- [x] Directorio `infra/` con estructura organizada:
  - `infra/docker/app/`: Dockerfile y configuración Gunicorn
  - `infra/compose/`: docker-compose.yml, docker-compose.test.yml, .env.example
  - `infra/scripts/`: entrypoint.sh, wait-for-it.sh
- [x] Separación de entornos: desarrollo (docker-compose.yaml raíz) y producción (infra/compose/)

#### 10.2. Dockerfile de Producción ✅ IMPLEMENTADO
- [x] **Base**: `python:3.12-slim`
- [x] **Dependencias**: build-essential, curl, libpq-dev
- [x] **Instalación**: requirements.txt + gunicorn + whitenoise
- [x] **Collectstatic**: Ejecutado en build time
- [x] **System check**: `check --deploy` en build
- [x] **Entrypoint**: Script que ejecuta migraciones y arranca Gunicorn

#### 10.3. Gunicorn Configuration ✅ IMPLEMENTADO
- [x] **Archivo**: `infra/docker/app/gunicorn.conf.py`
- [x] **Workers**: `(2 x CPU cores) + 1` (configurable vía `GUNICORN_WORKERS`)
- [x] **Timeout**: 60s (configurable)
- [x] **Logging**: stdout/stderr (compatible con Docker logs)
- [x] **Preload**: Habilitado para mejor rendimiento
- [x] **Max requests**: 1000 requests por worker (previene memory leaks)

#### 10.4. WhiteNoise para Staticfiles ✅ IMPLEMENTADO
- [x] **Middleware**: `whitenoise.middleware.WhiteNoiseMiddleware` después de `SecurityMiddleware`
- [x] **Storage**: `CompressedManifestStaticFilesStorage` (compresión + versionado)
- [x] **Configuración**: `WHITENOISE_USE_FINDERS=False` (solo STATIC_ROOT, más rápido)
- [x] **Auto-refresh**: Solo en desarrollo (`WHITENOISE_AUTOREFRESH=DEBUG`)

#### 10.5. Entrypoint con Migraciones ✅ IMPLEMENTADO
- [x] **Script**: `infra/scripts/entrypoint.sh`
- [x] **Flujo**:
  1. Espera PostgreSQL (healthcheck)
  2. `migrate --noinput` (esquema public)
  3. `migrate_schemas --shared --fake-initial` (django-tenants)
  4. Seed tenant opcional (si `SEED_TENANT_NAME` y `SEED_TENANT_DOMAIN` están definidos)
  5. `check --deploy` (validación producción)
  6. Arranca Gunicorn
- [x] **Seed tenant**: Crea Client + Domain + ejecuta migraciones del tenant si variables están definidas

#### 10.6. Docker Compose Producción ✅ IMPLEMENTADO
- [x] **Servicios**:
  - `app`: Gunicorn + WhiteNoise (puerto 8000)
  - `db`: PostgreSQL 16 con healthcheck
  - `redis`: Redis 7-alpine con healthcheck
  - `celery`: Worker Celery (concurrency=4, colas: `high_priority,default`)
    - Entrypoint específico: `entrypoint-celery.sh`
    - Configuración de colas prioritarias para tareas críticas
  - `beat`: Celery Beat scheduler
  - `opensearch`: OpenSearch single-node (512MB heap)
  - `traefik`: Reverse proxy opcional (rutado por hostname)
- [x] **Healthchecks**: Todos los servicios con healthchecks configurados
- [x] **Volúmenes**: `pgdata`, `static_volume`, `opensearch_data`
- [x] **Dependencias**: `depends_on` con condiciones (`service_healthy`, `service_started`)

#### 10.7. Docker Compose Tests ✅ IMPLEMENTADO
- [x] **Archivo**: `docker-compose.test.yml` (override para tests)
- [x] **Comando**: Ejecuta `pytest` en lugar de Gunicorn
- [x] **Migraciones**: Ejecuta `migrate` y `migrate_schemas` antes de tests
- [x] **Servicios deshabilitados**: Celery, beat, traefik (profiles: `test-disabled`)

#### 10.8. Configuración Django Producción ✅ IMPLEMENTADO
- [x] **DEBUG**: `False` (vía `DJANGO_DEBUG=False` en .env)
- [x] **ALLOWED_HOSTS**: Lista de dominios (vía `DJANGO_ALLOWED_HOSTS` en .env)
- [x] **Health endpoint**: `/health` en `config/urls.py` (verifica BD)
- [x] **WhiteNoise**: Configurado en `MIDDLEWARE` y `STORAGES`
- [x] **Staticfiles**: `STATIC_ROOT` configurado, `collectstatic` en build

#### 10.9. Variables de Entorno ✅ IMPLEMENTADO
- [x] **Archivo**: `infra/compose/.env.example`
- [x] **Variables críticas**:
  - `DEBUG=False` (obligatorio en producción)
  - `ALLOWED_HOSTS` (lista de dominios permitidos)
  - `SECRET_KEY` (clave fuerte)
  - `OPENSEARCH_PASSWORD` (admin de OpenSearch)
  - `SEED_TENANT_*` (opcional, para crear tenant inicial)

#### 10.10. Scripts de Utilidad ✅ IMPLEMENTADO
- [x] **wait-for-it.sh**: Espera a que un servicio esté disponible (host:port)
- [x] **Makefile**: Targets para gestión del stack (`up`, `down`, `build`, `logs`, `test`, `health`, `clean`)

#### 10.11. Comandos de Uso
```bash
# 1) Configurar variables de entorno
cd infra/compose
cp .env.example .env
# Editar .env con tus valores

# 2) Construir y levantar stack
docker compose -f docker-compose.yml --env-file .env up -d --build

# 3) Ver logs
docker compose -f docker-compose.yml logs -f app

# 4) Ejecutar tests
docker compose -f docker-compose.yml -f docker-compose.test.yml --env-file .env up --abort-on-container-exit --build

# 5) Verificar health
curl http://localhost:8000/health

# 6) Ejecutar comandos Django
docker compose -f docker-compose.yml exec app python manage.py shell
docker compose -f docker-compose.yml exec app python manage.py createsuperuser
```

#### 10.12. Características Implementadas
- [x] **Gunicorn**: WSGI server para producción (workers, timeout, logging)
- [x] **WhiteNoise**: Servir staticfiles sin Nginx (compresión + versionado)
- [x] **Health checks**: Endpoint `/health` y healthchecks Docker
- [x] **Migraciones automáticas**: `migrate` + `migrate_schemas` en entrypoint
- [x] **Seed tenant**: Creación automática de tenant inicial (opcional)
- [x] **Tests en Compose**: Suite de pruebas ejecutándose en contenedor
- [x] **Traefik opcional**: Rutado por hostname para multi-tenant

#### 10.13. Consideraciones de Producción
- [x] **OpenSearch**: Requiere `vm.max_map_count=262144` en host (Linux)
- [x] **Memoria**: OpenSearch mínimo 512MB heap (configurado)
- [x] **Staticfiles**: `collectstatic` en build time (no en runtime)
- [x] **ALLOWED_HOSTS**: Obligatorio con `DEBUG=False` (seguridad Host header)
- [x] **SECRET_KEY**: Generar clave fuerte (no usar default)

### 🚧 Fase 11: Modelos de Negocio por Tenant (PENDIENTE)

- [ ] Modelos de empresa (datos fiscales, configuración)
- [ ] Modelos de facturas (recepción, emisión, almacenamiento XML)
- [ ] Modelos de contabilidad (asientos, registros, reportes)
- [ ] Relaciones entre modelos de tenant
- [ ] Migraciones de tenant apps

### 🚧 Fase 12: Frontend e Integración (PENDIENTE)

- [ ] Frontend/Interfaz de usuario
- [ ] Integración con servicios DIAN
- [ ] Generación de reportes
- [ ] Dashboard por tenant

---

## 🔐 Variables de Entorno

Archivo `.env` (copiar desde `.env.sample`):

```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=*
DATABASE_HOST=db
DATABASE_PORT=5432
DATABASE_NAME=sintel
DATABASE_USER=sintel
DATABASE_PASSWORD=sintel
REDIS_URL=redis://redis:6379/0
DEFAULT_FROM_EMAIL=no-reply@sintel.local
TIME_ZONE=America/Bogota
```

---

## 📝 Notas Importantes y Decisiones de Diseño

### Decisiones Arquitectónicas Clave

1. **TenantMainMiddleware debe ser el primer middleware** ⚠️ CRÍTICO
   - El esquema debe establecerse antes de cualquier otra operación
   - Cualquier consulta a BD antes de esto fallará
   - Orden crítico en MIDDLEWARE
   - **Validado:** Está configurado como PRIMERO en `config/settings.py`

2. **ENGINE debe ser django_tenants.postgresql_backend** ⚠️ CRÍTICO
   - Backend especial para multi-tenant por esquemas
   - No usar el backend estándar de Django (`django.db.backends.postgresql`)
   - **Validado:** Configurado correctamente en `config/settings.py`

3. **DATABASE_ROUTERS debe ser una tupla con TenantSyncRouter** ⚠️ CRÍTICO
   - Debe ser una tupla, no una lista
   - Router que enruta queries al esquema correcto
   - **Validado:** Configurado como tupla en `config/settings.py`

4. **django.template.context_processors.request debe estar en TEMPLATES** ⚠️ CRÍTICO
   - Requerido por django-tenants para funcionar correctamente
   - **Validado:** Presente en `config/settings.py`

5. **El esquema public se crea automáticamente**
   - Con `migrate_schemas --shared` se crean todas las tablas de SHARED_APPS
   - El tenant público se crea con `setup_public_tenant`
   - El dominio `localhost` está asociado al tenant `public`

3. **Cada tenant necesita un dominio asociado**
   - El middleware identifica el tenant por el dominio de la request
   - Un tenant puede tener múltiples dominios (principal y secundarios)
   - El dominio principal tiene `is_primary=True`

4. **El catálogo DIAN es compartido**
   - Todos los tenants pueden referenciar los mismos códigos tributarios
   - Evita duplicación de datos
   - Actualizaciones centralizadas

5. **Los usuarios son globales** ⚠️ POLÍTICA DE USUARIOS
   - Un usuario puede tener acceso a múltiples tenants (futuro)
   - Autenticación centralizada en esquema public
   - Permisos por tenant se implementarán en Fase 3+
   - **Ubicación:** `apps.public.accounts` en `SHARED_APPS`
   - **Sesiones:** `django.contrib.sessions` está en `SHARED_APPS` porque los usuarios son globales
   - **Implicación:** Un usuario puede tener sesiones activas en múltiples tenants

6. **Estructura de Apps Consolidada** ⚠️ CRÍTICO
   - `SHARED_APPS`: Apps que existen SOLO en el esquema 'public' (compartidas por todos los tenants)
   - `TENANT_APPS`: Apps que viven en cada esquema de tenant (específicas de cada empresa)
   - Django consultará primero el esquema del tenant y luego 'public'
   - **Validado:** Estructura final consolidada en `config/settings.py`
   - **Política de Sessions:** `django.contrib.sessions` en `SHARED_APPS` porque usuarios son globales

6. **No usar Django signals**
   - Seguir el principio de Service Layer Pattern
   - Toda la lógica debe ser explícita y rastreable
   - Evitar acoplamiento invisible

7. **Settings Simple**
   - `settings.py` solo contiene configuración declarativa
   - Lógica específica va a `apps/services/`
   - Facilita mantenimiento y testing

8. **Client-Side First / API-First**
   - **DataTables client-side por defecto**: Todas las tablas DataTables deben usar procesamiento client-side a menos que se solicite explícitamente server-side
   - Server-side solo cuando se requiera: Para consultas pesadas o cuando se solicite explícitamente
   - APIs REST con paginación eficiente
   - Frontend agnóstico: cualquier cliente puede consumir las APIs

9. **Server Guard y Migraciones Seguras**
   - El servidor **NO** arranca si hay migraciones pendientes
   - Comando `check_migrations` verifica estado antes de iniciar
   - Guardas en `AppConfig.ready()` previenen consultas durante comandos de mantenimiento
   - Protección contra consultas a DB en import-time cuando hay migraciones pendientes
   - Flujo automático: `makemigrations → migrate_schemas --shared --fake-initial → check_migrations → runserver`

---

## 📚 Fuentes y Referencias

### Documentos de Arquitectura

1. **`aquitectura_crm_sintel_v_1_operativo.docx`** (Documento Base Original)
   - **Versión:** 1.0
   - **Tipo:** Arquitectura inicial del proyecto
   - **Contenido:** Definición original de la estructura, principios y decisiones arquitectónicas
   - **Estado:** Documento base de referencia
   - **Ubicación:** Raíz del proyecto

2. **`arquitectura_general.md`** (Este documento - Fuente Única de Verdad)
    - **Ubicación:** `documentacion/arquitectura_general.md`
    - **Versión:** 2.22
   - **Tipo:** Arquitectura actualizada y alineada
   - **Contenido:** Implementación actual, estructura de directorios, configuración, comandos
   - **Estado:** Documento activo y actualizado
   - **Prioridad:** Este documento tiene prioridad sobre el Word para desarrollo

### Relación entre Documentos

- El documento Word (`aquitectura_crm_sintel_v_1_operativo.docx`) contiene la **arquitectura inicial y diseño conceptual**
- Este documento Markdown contiene la **arquitectura implementada y estado actual del código**
- Ambos documentos deben estar alineados, pero este Markdown refleja la realidad del código

### Otros Documentos del Proyecto

- **Fase 2 Completa:** `FASE_2_COMPLETA.md`
- **Checklist Inicialización:** `CHECKLIST_INICIALIZACION.md`
- **Comandos Tenant Público:** `COMANDOS_TENANT_PUBLICO.md`
- **Cambios Settings:** `CAMBIOS_SETTINGS.md`
- **Solución Tenant Público:** `SOLUCION_TENANT_PUBLICO.md`

### Referencias Técnicas Externas

- **django-tenants:** https://django-tenants.readthedocs.io/
- **Django 5.x:** https://docs.djangoproject.com/
- **DIAN Colombia:** https://www.dian.gov.co/
- **PostgreSQL 16:** https://www.postgresql.org/docs/16/
- **Docker Compose:** https://docs.docker.com/compose/
- **Celery:** https://docs.celeryproject.org/
- **Redis:** https://redis.io/documentation

### Documentación Normalizada del Proyecto

- **[DJANGO_TENANTS_PLAYBOOK_SINTEL.md](DJANGO_TENANTS_PLAYBOOK_SINTEL.md)** ⭐ Playbook normalizado para django-tenants (routing, URLConf, migraciones, testing, troubleshooting)
- **[DJANGO_5_PLAYBOOK_SINTEL.md](DJANGO_5_PLAYBOOK_SINTEL.md)** ⭐ Fuente de verdad normalizada para Django 5.0 (settings, seguridad, performance, testing, deployment) basada en documentación oficial
- **[ALINEACION_TENANT_DJANGO_TENANTS.md](ALINEACION_TENANT_DJANGO_TENANTS.md)** ⭐ Informe completo de alineación de la lógica de negocio en `apps/tenant` con django-tenants (98% conforme)
- **[SOLUCION_CSRF_403.md](SOLUCION_CSRF_403.md)**: Solución al error 403 CSRF en login admin

### Historial de Versiones

#### v2.22 (2026-01-30) - CRUD Robusto de Usuarios ✅ ACTUAL
- ✅ **Service Layer con Generación de Username Único**
  - Función `_generate_unique_username()` genera username desde email si el modelo lo tiene
  - Compatibilidad con `AbstractUser` (que conserva username único)
  - Evita colisiones añadiendo sufijos incrementales (`-1`, `-2`, etc.)
  - **Ubicación**: `apps/public/accounts/api/services/user_service.py`
- ✅ **Validación de Password + Confirmación**
  - `UserCreateSerializer` incluye campo `password2` (write_only, min_length=8)
  - Validación `validate()` verifica que `password` y `password2` coincidan
  - Mensaje de error claro: "Las contraseñas no coinciden."
  - **Ubicación**: `apps/public/accounts/api/serializers.py`
- ✅ **ViewSet con Manejo Robusto de Errores**
  - `UserAdminViewSet` captura `IntegrityError` y retorna 400 con mensaje claro
  - Remueve `password2` antes de pasar al servicio (solo se usa para validación)
  - Retorna `{"detail": ...}` para consistencia con DRF
  - **Ubicación**: `apps/public/accounts/api/viewsets.py`
- ✅ **UI Moderna con Modal y Validación JavaScript**
  - Modal rediseñado con estructura similar a formulario de tenants
  - Campo `password2` visible y funcional con placeholder y mensaje de ayuda
  - Validación JavaScript: verifica que contraseñas coincidan antes de enviar
  - Mensajes de error específicos por campo (`error-password2`)
  - Estilos consistentes con Tailwind CSS (transiciones, placeholders, padding)
  - **Ubicación**: `apps/public/console/templates/console/pages/users/list.html`, `apps/public/console/static/js/users_manager.js`
- ✅ **Tests de Creación de Usuarios**
  - `test_create_user_minimal_ok`: Verifica creación exitosa y que password no esté en respuesta
  - `test_create_user_password_mismatch`: Verifica que contraseñas diferentes retornen 400
  - `test_create_user_duplicate_email`: Verifica que emails duplicados retornen 400
  - `test_create_user_without_password2`: Verifica que falta de password2 retorne 400
  - `test_create_user_password_too_short`: Verifica que passwords cortos retornen 400
  - **Ubicación**: `tests/public/accounts/test_users_create.py`
- ✅ **Características de Seguridad**
  - Password siempre hasheado con `set_password()` (nunca texto plano)
  - Password `write_only` en serializers (nunca se expone en respuestas JSON)
  - Validación en múltiples capas: HTML5, JavaScript, Serializer, Service Layer
  - Manejo robusto de `IntegrityError` para emails/username duplicados

#### v2.21 (2026-01-29) - Alineación Completa con django-tenants
- ✅ **Alineación completa de apps/tenant con django-tenants verificada (98% conforme)**
  - Verificación exhaustiva de modelos, APIs, servicios y lógica de negocio
  - Documentación en `ALINEACION_TENANT_DJANGO_TENANTS.md`
  - Ajustes menores para cumplir 100% con documentación oficial

#### v2.16 (2026-01-23) - Blindaje del Login y Perfil del Colaborador
- ✅ **Fase 1: Blindaje del Login (COMPLETADA)**
  - Formulario de autenticación seguro (`TenantAuthenticationForm`) con validación de membresía
  - Vista de login personalizada (`TenantLoginView`) con template moderno Tailwind CSS
  - Backend de autenticación tenant-aware (`TenantAwareBackend`) que valida membresía antes de permitir login
  - Mensajes de error específicos que distinguen entre "contraseña incorrecta" y "no autorizado en este tenant"
  - Tests de seguridad completos: unitarios, integración y test de garantía total
  - **Ubicación**: `apps/tenant/landing/forms.py`, `apps/tenant/landing/views.py`, `apps/public/tenants/auth_backend.py`, `apps/tenant/landing/templates/tenant/landing/login.html`
  - **Tests**: `tests/tenant/landing/test_login_security.py`, `tests/public/tenants/test_auth_backend.py`, `tests/tenant/security/test_full_integration.py`
- ✅ **Fase 2: Perfil Privado del Colaborador (COMPLETADA)**
  - Modelo `TenantProfile` con OneToOneField a User global
  - Campos: cargo, departamento, telefono_corporativo, avatar, configuracion (JSONField)
  - Service Layer: `obtener_o_crear_perfil()` y `actualizar_configuracion_ui()`
  - API REST: Endpoints `/api/v1/perfil/perfiles/me/` (GET/PATCH) y `/api/v1/perfil/perfiles/me/configuracion/` (PATCH)
  - Serializer con datos nested del User global (solo lectura)
  - Tests de servicio, API y aislamiento entre tenants
  - **Ubicación**: `apps/tenant/perfil/`, `apps/services/perfil/perfil_service.py`
  - **Tests**: `tests/tenant/perfil/test_perfil.py`
- ✅ **Configuración de Backend de Autenticación**
  - `AUTHENTICATION_BACKENDS` configurado con `TenantAwareBackend` primero
  - Backend valida membresía antes de permitir login
  - Logging de intentos de acceso cruzado
  - **Ubicación**: `config/settings.py` (línea 164-167)

#### v2.19 (2026-01-24) - Aprovisionamiento Atómico "Zero-Orphan" y Normalización de Puertos
- ✅ **Aprovisionamiento Atómico "Zero-Orphan"**
  - Mejora crítica en `crear_tenant()` con manejo robusto de errores y logging detallado
  - Transacción atómica garantiza que si falla cualquier paso (Client, Domain, Membership), TODO se revierte
  - Previene completamente la creación de tenants "huérfanos" sin administrador vinculado
  - Try/except específico para `TenantMembership` con mensajes de error claros
  - Logging detallado antes del rollback automático para diagnóstico
  - **Ubicación**: `apps/services/onboarding/empresa_service.py`
- ✅ **Normalización de Dominios con Soporte de Puerto en Desarrollo**
  - Función `normalize_domain()` actualizada para mantener puerto en `DEBUG=True`
  - En desarrollo: Mantiene el puerto si viene en el string (ej: `cliente.sintel.com:8000`)
  - En producción: Elimina el puerto como antes (ej: `cliente.sintel.com`)
  - Resuelve el problema de django-tenants que busca coincidencia exacta del hostname
  - **Ubicación**: `apps/public/tenants/utils.py`
- ✅ **Mejora en Construcción de URL de Login**
  - `crear_tenant()` ahora busca y usa el dominio con puerto si existe en desarrollo
  - La URL de login incluye el puerto cuando `DEBUG=True` (ej: `http://tupapi.sintel.com:8000/login/`)
  - Script `fix_dev_domains.py` para reparar dominios existentes sin puerto
  - **Ubicación**: `apps/services/onboarding/empresa_service.py`, `scripts/fix_dev_domains.py`

#### v2.18 (2026-01-24) - Aislamiento Completo del Admin de Tenant y Solución de Puerto
- ✅ **Aislamiento Completo del Admin de Tenant**
  - `TenantAdminSite` personalizado en `apps/tenant/core/admin.py` que solo muestra modelos de `TENANT_APPS`
  - Eliminación de modelos públicos (Client, Domain, TenantMembership) del admin de tenant
  - Registro automático de modelos tenant en `AppConfig.ready()` para evitar problemas de importación circular
  - Tests completos en `tests/tenant/core/test_tenant_admin_site.py` y `test_admin_integration.py`
  - **Ubicación**: `apps/tenant/core/admin.py`, `apps/tenant/core/apps.py`
- ✅ **Eliminación de Referencias a `/admin/login/` en Tenants Privados**
  - `LOGIN_URL = '/login/'` y `LOGOUT_REDIRECT_URL = '/'` en `config/settings.py`
  - Vista `TenantLoginView` personalizada en `/login/` (reemplaza `/admin/login/`)
  - Redirección de `/admin/login/` a `/` (landing page) en `config/urls_tenant.py`
  - Actualización de decoradores y referencias en código y templates
  - Comando `auditar_referencias_admin_login` para verificar eliminación completa
  - **Ubicación**: `config/settings.py`, `apps/tenant/landing/views.py`, `config/urls_tenant.py`
- ✅ **Solución Automática de Puerto en Dominios**
  - La señal `post_save` en `apps/public/tenants/signals.py` crea automáticamente dominio con puerto en desarrollo
  - Resuelve el problema de django-tenants que busca coincidencia exacta del hostname
  - Dominio principal: `cliente.sintel.com` (sin puerto, `is_primary=True`)
  - Dominio con puerto: `cliente.sintel.com:8000` (solo en `DEBUG=True`, `is_primary=False`)
  - Comando `fix_all_tenant_domains` para corregir tenants existentes
  - **Ubicación**: `apps/public/tenants/signals.py`, `apps/public/tenants/management/commands/fix_all_tenant_domains.py`
- ✅ **Auditoría de Dominios y Acceso Web**
  - Comando `auditar_dominios_tenants` verifica: dominio activo, esquema PostgreSQL, acceso web
  - Tests automatizados en `tests/public/tenants/test_domain_activation.py`
  - Script `verificar_tenant_web.py` para verificación rápida
  - **Ubicación**: `apps/public/tenants/management/commands/auditar_dominios_tenants.py`
- ✅ **Scripts de Reinicio Total (Nuclear Reset)**
  - `scripts/reset_docker.sh`: Limpia y reconstruye contenedores Docker
  - `scripts/reset_migrations.py`: Elimina archivos de migración (excepto `__init__.py`) y **asegura que `__init__.py` exista** (v2.20)
  - `scripts/init_project.sh`: Inicializa proyecto en orden correcto
  - `scripts/reinicio_total.ps1`: Script PowerShell automatizado para Windows
  - Documentación completa en `documentacion/REINICIO_TOTAL.md`
  - **Mejoras v2.20**: Asegura que `__init__.py` exista después de limpiar (previene `ValueError: Dependency on app with no migrations`), soporte Windows (encoding UTF-8), modo no interactivo (`--yes`/`--force`)
  - **Ubicación**: `scripts/`, `documentacion/REINICIO_TOTAL.md`
- ✅ **Eliminación de Referencias Específicas a Tenants**
  - Eliminación de todas las referencias hardcodeadas a "home.com" o "home.sintel.com"
  - Actualización de scripts y comandos para usar ejemplos genéricos (ej: `ejemplo`, `test_subdomain`)
  - Documentación actualizada con ejemplos genéricos
  - **Ubicación**: `scripts/`, `apps/public/tenants/management/commands/`, `documentacion/ELIMINACION_REFERENCIAS_ESPECIFICAS_TENANT.md`
- ✅ **Política de Subdominios Estricta**
  - Todos los tenants privados deben usar subdominios de `TENANT_DOMAIN_BASE` (ej: `cliente.sintel.com`)
  - Validación en `crear_tenant` para rechazar FQDNs arbitrarios
  - Generación automática de subdominio desde `schema_name`
  - Documentación en `documentacion/POLITICA_SUBDOMINIOS_ESTRICTA.md`
  - **Ubicación**: `apps/services/onboarding/empresa_service.py`, `config/settings.py`

#### v2.33 (2026-02-09) - Observabilidad + Smoke Test CLI + Pruebas Críticas
- ✅ **Fase 5: Observabilidad + Smoke Test CLI (v2.33)**
  - Logging estructurado con categorías por dominio (`facturas`, `apps.services.xml_ingest`, `celery`)
  - Instrumentación de tareas Celery con métricas (duración, tamaños)
  - Healthcheck API endpoint (`GET /api/v1/core/health/`)
  - Script de smoke end-to-end (`tools/smoke_facturas.sh`) para validación completa del flujo
  - Makefile actualizado con comandos `smoke-facturas` y `health`
  - **Ubicación**: `config/settings.py` (LOGGING), `apps/services/xml_ingest/tasks.py`, `apps/tenant/core/api/health.py`, `tools/smoke_facturas.sh`, `Makefile`
- ✅ **Fase 6: Pruebas Críticas Multitenant (v2.33)**
  - Tests de Tenant Onboarding (6 tests): validación de creación completa, esquema, dominio, admin, independencia, idempotencia
  - Tests de Aislamiento de Datos (4 tests): validación de que cada tenant solo accede a sus propios datos
  - Tests de Autenticación y Autorización (4 tests): validación de control de acceso básico
  - Tests Funcionales Básicos (6 tests): CRUD básico para apps core (Facturas, Clientes, Empresa)
  - Tests de Errores Críticos (5 tests): validación de resiliencia ante errores esperables
  - Tests de Arranque y Disponibilidad (6 tests): validación de que el sistema puede iniciar y operar
  - Total: 31 tests críticos distribuidos en 6 categorías
  - **Ubicación**: `tests/tenant/critical/`
  - **Documentación**: `tests/tenant/critical/README.md`
- ✅ **Canonización Pipeline XML + SSoT Operativo (v2.34)**
  - **Pipeline XML canónico**: `apps/services/xml_ingest` + `apps/services/xml_parser` como única vía
  - **Logging normalizado**: Formatters sin `request_id` por defecto (evita errores en arranque)
  - **RequestContextMiddleware**: Opcional para correlación de logs (no activo por defecto)
  - **Validación de campos obligatorios**: Materialización valida `emisor_nit`, `emisor_razon_social`, `receptor_nit`, `receptor_razon_social`
  - **Auditoría automatizada**: `scripts/audit_xml_pipeline_duplication.py` detecta violaciones
  - **Smoke tests**: `apps/tenant/facturas/tests/test_xml_pipeline_canonical.py` valida contratos
  - **Makefile**: Comandos `smoke-xml-pipeline` y `smoke` (suite completa)
  - **Documentación**: Regla SSoT XML añadida a `arquitectura_general.md`
  - **Ubicación**: `scripts/audit_xml_pipeline_duplication.py`, `apps/tenant/facturas/tests/test_xml_pipeline_canonical.py`, `Makefile`, `documentacion/arquitectura_general.md`

#### v2.15 (2026-01-23) - Testing Robusto y Documentación Normalizada
- ✅ **Testing Robusto con TenantTestCase (Fase 5)**
  - Clase base `SintelTenantTestCase` heredando de `django_tenants.test.cases.TenantTestCase`
  - Setup automático de tenant, domain, user, membership y clientes (Client y APIClient) con `HTTP_HOST` configurado
  - Tests de lógica de negocio (`test_empresa_logic.py`): cálculo DV, singleton pattern, aislamiento de datos
  - Tests de seguridad y acceso (`test_access.py`): redirección anónima, acceso cross-tenant, acceso autorizado
  - Tests de API pública (`test_public_api.py`): whitelist de datos, privacidad de información sensible
  - **Ubicación**: `tests/tenant/base_test.py`, `tests/tenant/empresa/test_empresa_logic.py`, `tests/tenant/dashboard/test_access.py`, `tests/tenant/landing/test_public_api.py`
- ✅ **Documentación Normalizada**
  - `DJANGO_TENANTS_PLAYBOOK_SINTEL.md`: Playbook normalizado para django-tenants (routing, URLConf, migraciones, testing, troubleshooting)
  - `DJANGO_5_PLAYBOOK_SINTEL.md`: Fuente de verdad normalizada para Django 5.0 basada en documentación oficial (settings, seguridad, performance, testing, deployment)
  - `SOLUCION_CSRF_403.md`: Solución al error 403 CSRF en login admin con troubleshooting completo
  - **Fuente primaria**: PDFs oficiales (`django-readthedocs-io-en-5.0.x.pdf`, `django-tenants-readthedocs-io-en-latest.pdf`)
- ✅ **Middleware CSRF Mejorado**
  - `CSRFTrustedOriginMiddleware` mejorado para agregar automáticamente dominios a `CSRF_TRUSTED_ORIGINS` en desarrollo
  - Establece `HTTP_ORIGIN` en `request.META` para que Django lo use en validación CSRF
  - Soporte para HTTP y HTTPS automáticamente
  - **Ubicación**: `apps/public/core/middleware.py`
- ✅ **Dependencia Pillow Agregada**
  - `Pillow>=10.0,<11.0` agregado a `requirements.txt` para soportar `ImageField` en modelos Django
  - Requerido para campos de imagen como `Empresa.logo`
- ✅ **Templates de Error Personalizados**
  - Templates `tenant/errors/404.html` y `tenant/errors/403.html` para errores tenant-aware
  - Handlers personalizados en `apps.tenant.core.api.handlers` con branding dinámico
  - **Ubicación**: `apps/tenant/core/templates/tenant/errors/`, `apps/tenant/core/api/handlers.py`

#### v2.14 (2026-01-21) - Configuración CSRF y Acceso Puerto 80
- ✅ **Configuración CSRF para Dominios Arbitrarios**
  - Middleware `CSRFTrustedOriginMiddleware` que agrega automáticamente dominios a `CSRF_TRUSTED_ORIGINS` en desarrollo
  - Permite usar dominios arbitrarios (ej: `ejemplo.com`, `tupapi.com`) sin agregarlos manualmente a la configuración
  - Solo funciona en `DEBUG=True`. En producción, se requiere lista explícita
  - **Ubicación**: `apps/public/core/middleware.py`
- ✅ **Configuración de Cookies CSRF**
  - `CSRF_COOKIE_DOMAIN = None` en desarrollo (permite cualquier dominio)
  - `CSRF_COOKIE_SAMESITE = 'Lax'` para permitir cookies en requests del mismo sitio
  - `CSRF_COOKIE_HTTPONLY = False` para permitir acceso desde JavaScript si es necesario
  - `CSRF_USE_SESSIONS = False` para usar cookies en lugar de sesiones para CSRF
- ✅ **Middleware HTTPSRedirectMiddleware Mejorado**
  - Redirige peticiones HTTPS a HTTP en modo desarrollo
  - Maneja headers de seguridad (`Cross-Origin-Opener-Policy`) solo para `localhost` y `127.0.0.1` en desarrollo
  - Evita advertencias del navegador para dominios arbitrarios
- ✅ **Acceso en Puerto 80 Habilitado**
  - Docker Compose mapea puerto 80 del host a puerto 8000 del contenedor (`- "80:8000"`)
  - URLs generadas sin puerto explícito (puerto 80 implícito) en desarrollo
  - Ejemplo: `http://cliente.sintel.com/` en lugar de `http://cliente.sintel.com:8000/`
  - Actualizado en: `apps/services/onboarding/empresa_service.py`, `apps/public/console/templates/console/pages/tenants/list.html`, `apps/tenant/landing/api/serializers.py`, `apps/public/core/middleware.py`
- ✅ **Solución a Error CSRF "cookie not set"**
  - El middleware `CSRFTrustedOriginMiddleware` resuelve el error 403 CSRF al agregar dominios automáticamente
  - Configuración de cookies CSRF permite cualquier dominio en desarrollo
  - Login en tenants privados funciona correctamente sin errores CSRF
- ✅ **Documentación Actualizada**
  - Sección de configuración de seguridad y CSRF agregada
  - Explicación de middlewares personalizados
  - Instrucciones para acceso en puerto 80

#### v2.13 (2026-01-21) - Acceso a Tenants y Landing Page
- ✅ **Configuración de Acceso a Tenants**
  - `config/urls_tenant.py` configurado para manejar la ruta raíz (`/`)
  - `TenantLandingView` implementada como puerta de entrada pública
  - Template `tenant/landing/index.html` creado con Tailwind CSS
  - `ALLOWED_HOSTS = ["*"]` en desarrollo para permitir dominios arbitrarios
- ✅ **Landing Page Pública**
  - Vista pública accesible sin autenticación en la raíz del tenant (`/`)
  - Muestra nombre del tenant y botones condicionales según estado de autenticación
  - Botón "Iniciar Sesión" si no está autenticado, "Ir a mi Dashboard" si está autenticado
- ✅ **API-First para Landing Page (v2.30)**
  - API `/api/v1/landing/info/` expone información pública del tenant (Nombre, Dominio, Login URL)
  - API `/api/v1/landing/auth/login/` maneja login con validación de membresía
  - API `/api/v1/landing/auth/activate/` maneja activación de owner (GET valida token, POST procesa activación)
  - Serializers: `TenantPublicInfoSerializer`, `TenantLoginSerializer`, `OwnerActivationSerializer`
  - ⚠️ v2.30: Vistas HTML eliminadas - toda la funcionalidad se maneja mediante APIs REST
  - Tests funcionales: `tests/tenant/landing/test_landing_architecture.py`
  - Pruebas de humo: `tests/tenant/landing/test_landing_api_smoke.py`
- ✅ **Normalización de Dominios**
  - Función `normalize_domain()` en `apps/public/tenants/utils.py` para limpiar dominios
  - Validación FQDN con `validate_fqdn()`
  - Aplicado en todos los serializers (público y admin)
  - Tests funcionales: `tests/public/tenants/test_domain_normalization.py`
- ✅ **Eliminación de Referencias a `/admin/login/` en Tenants Privados (v2.18)**
  - `LOGIN_URL = '/login/'` en `config/settings.py` (reemplaza `/admin/login/`)
  - `LOGOUT_REDIRECT_URL = '/'` (redirige a landing page después del logout)
  - Función `tenant_admin_login_redirect` que redirige `/admin/login/` a `/` (landing page)
  - Vista `TenantLoginView` personalizada para tenants con template `tenant/landing/login.html`
  - `TenantAdminSite` aislado que solo muestra modelos de `TENANT_APPS` (no modelos públicos)
  - CSRF configurado correctamente para dominios arbitrarios en desarrollo
- ✅ **Solución Automática de Puerto en Dominios (v2.18)**
  - La señal `post_save` crea automáticamente dominio con puerto en desarrollo
  - Resuelve el problema de django-tenants que busca coincidencia exacta del hostname
  - Comando `fix_all_tenant_domains` para corregir tenants existentes
  - Comando `auditar_dominios_tenants` para verificar dominio y acceso web
- ✅ **Auditoría de Dominios y Acceso Web (v2.18)**
  - Comando `auditar_dominios_tenants` verifica: dominio activo, esquema PostgreSQL, acceso web
  - Tests automatizados en `tests/public/tenants/test_domain_activation.py`
  - Script `verificar_tenant_web.py` para verificación rápida
- ✅ **Scripts de Reinicio Total (Nuclear Reset) (v2.18)**
  - `scripts/reset_docker.sh`: Limpia y reconstruye contenedores Docker
  - `scripts/reset_migrations.py`: Elimina archivos de migración (excepto `__init__.py`)
  - `scripts/init_project.sh`: Inicializa proyecto en orden correcto
  - `scripts/reinicio_total.ps1`: Script PowerShell automatizado para Windows

#### v2.6 (2026-01-19)
- ✅ **CRUD + Onboarding de Tenants (Fase 9)** implementado completo
  - Modelo `TenantMembership` para gestión de membresías (User ↔ Client con roles)
  - Servicio `crear_tenant()` en `empresa_service.py` (onboarding completo: Client + Domain + Migrations + Membership)
  - API Admin (`/api/admin/v1/tenants/`) con CRUD completo y endpoint `onboard`
  - DataTables server-side (`/api/admin/v1/dt/tenants/`) para lista de tenants
  - Consola `/console/tenants/` con DataTables, formulario de creación y acciones (Editar/Borrar/Acceder)
  - Tests funcionales: `test_onboard.py`, `test_console_pages.py`, `test_datatables_tenants.py`
  - Estilos mejorados: badges de estado (🟡 Trial / 🔵 Activo), botones con iconos, formateo de fechas (dd/mm/yyyy)
  - Seguridad: Solo staff (`IsAdminUser`, `_check_staff_or_raise`)
  - URLs dinámicas: Uso de `reverse()` y `{% url %}` (sin hardcoding)

#### v2.5 (2026-01-19)
- ✅ **Auditoría y Refactor Seguro (Fase 8)**
  - Herramientas configuradas: `pyproject.toml` con Ruff, `Makefile` con targets de auditoría
  - Tests funcionales: `test_links_templates.py`, `test_crud_tipos.py`, `test_datatables_tipos.py`, `test_queries_perf.py`
  - Refactors seguros: URLs hardcodeadas corregidas (uso de `reverse()` y `{% url %}`)
  - Verificación de enlaces y estáticos: `collectstatic --dry-run`, tests de templates
  - Pipeline de pruebas: `make audit` para auditoría completa, tests funcionales con pytest
  - Optimizaciones: detección de queries N+1 con `assertNumQueries`, uso de `select_related`/`prefetch_related`
- ✅ **Dependencias de desarrollo**: `ruff`, `bandit` agregadas para auditoría

#### v2.4 (2026-01-19)
- ✅ **Fases A-D completadas** (Ingesta, ETL, Exposición/Búsqueda, Operación)
  - Fase A: Ingesta con multipart/form-data, form-urlencoded, JSON
  - Fase B: ETL Pipeline completo (parse → tokenize → normalize → validate → upsert)
  - Fase C: Búsqueda con OpenSearch (multi-match, highlighting, blue/green deployment)
  - Fase D: Cumplimiento (idempotencia, robots.txt), Observabilidad (salud, métricas), Resiliencia (DLQ, reintentos), Operabilidad (comandos, blue/green)
  - Fase 5 (v2.33): Observabilidad + Smoke Test CLI (logging estructurado, instrumentación Celery, healthcheck, script smoke)
  - Fase 6 (v2.33): Pruebas Críticas Multitenant (31 tests críticos en 6 categorías)
- ✅ **Separación API JSON vs UI Templates**
  - `BrowsableAPIRenderer` desactivado globalmente (solo JSON)
  - UI dedicada en `/console/impuestos/*` consume APIs JSON
  - Parsers: `MultiPartParser`, `FormParser`, `JSONParser`
  - CSRF habilitado en formularios HTML y peticiones HTMX
- ✅ **Suite de Pruebas E2E**
  - Tests E2E: multipart, form-urlencoded, JSON, CSRF
  - Tests de API, ETL, catálogos, búsqueda, operación
  - Fixtures: Celery eager, CSRF client, OpenSearch fake
  - Dependencias: `pytest`, `pytest-django`, `factory-boy`, `responses`
- ✅ **DRF Renderers/Parsers configurados**
  - Solo `JSONRenderer` (sin `BrowsableAPIRenderer`)
  - `FormParser` para form-urlencoded
  - `MultiPartParser` para multipart/form-data
  - `JSONParser` para application/json

#### v2.10 (2026-01-21) - Corrección de Celery y Diagnóstico ✅ RESUELTO
- ✅ **Corrección de Worker de Celery**
  - Creado `entrypoint-celery.sh` específico para el contenedor Celery
  - Worker ahora ejecuta correctamente `celery -A config worker` en lugar del servidor Django
  - Configuración de colas prioritarias: `high_priority` para `onboard_tenant_task`
  - Worker escucha `high_priority,default` para procesar tareas críticas inmediatamente
  - **✅ VERIFICADO:** Worker procesa tareas inmediatamente, sin quedarse en PENDING
- ✅ **Corrección de `empresa_service.py`**
  - Eliminado `auto_create_schema=True` del constructor de `Client` (es un atributo de clase, no argumento)
  - El modelo `Client` ya tiene `auto_create_schema = True` definido como atributo de clase
  - **✅ VERIFICADO:** Creación de tenants funciona correctamente desde consola
- ✅ **Script de Diagnóstico Forense**
  - Comando `python manage.py debug_tenant_creation` para diagnóstico paso a paso
  - Valida: configuración Celery, creación síncrona, Celery eager mode, cola real
  - Identifica exactamente dónde falla la cadena de creación de tenants
  - **✅ RESULTADO:** Todas las pruebas pasan (configuración, lógica, eager mode, cola real)
- ✅ **Logging Mejorado**
  - Logging detallado en `tenants_create` para diagnóstico de errores
  - Logging en `onboard_tenant_task` para seguimiento de ejecución
  - Facilita identificación de problemas en producción
- ✅ **Flujo Completo Funcional**
  - **✅ VERIFICADO:** Creación de tenants desde `/console/tenants/new/` funciona sin fallos
  - Formulario captura datos correctamente
  - Tarea Celery se encola y procesa inmediatamente
  - Polling HTMX actualiza estado automáticamente
  - Sistema completamente operativo
- ✅ **Flujo Completo Funcional**
  - **✅ VERIFICADO:** Creación de tenants desde `/console/tenants/new/` funciona sin fallos
  - Formulario captura datos correctamente
  - Tarea Celery se encola y procesa inmediatamente
  - Polling HTMX actualiza estado automáticamente
  - Sistema completamente operativo

#### v2.20 (2026-01-27) - Mejoras de Estabilidad y Server Guard
- ✅ **Server Guard Mejorado**
  - `apps/public/core/apps.py` implementa `CoreConfig` con guardas que omiten validaciones durante comandos de mantenimiento
  - Previene el problema "Chicken-Egg": no intenta acceder a tablas que aún no existen durante `makemigrations`
  - Comandos protegidos: `makemigrations`, `migrate`, `migrate_schemas`, `collectstatic`, `shell`, `check`, `test`, etc.
  - Solo ejecuta validaciones cuando el servidor está corriendo (`runserver`, `gunicorn`)
- ✅ **Script reset_migrations.py Mejorado**
  - Asegura que `__init__.py` exista después de limpiar migraciones
  - Previene `ValueError: Dependency on app with no migrations`
  - Crea `__init__.py` automáticamente si falta
  - Soporte para Windows (encoding UTF-8)
  - Modo no interactivo con `--yes` o `--force`
- ✅ **Conflicto de Labels Resuelto**
  - `apps.public.core` tiene `label = 'public_core'` (único)
  - `apps.tenant.core` tiene `label = 'tenant_core'` (único)
  - Previene error "Application labels aren't unique, duplicates: core"
- ✅ **Entrypoint.sh Mejorado**
  - `wait_for_db()` usa Django para verificar conexión (más robusto que `psycopg2` directo)
  - Mejor manejo de errores con límite de intentos (60 intentos = 2 minutos máximo)
  - Muestra información de diagnóstico si falla la conexión
  - Eliminado `set -e` problemático (comandos críticos usan `|| exit 1` explícitamente)
  - Comandos de mantenimiento con `--verbosity 0` para reducir ruido en logs
  - Separación clara entre servicio `web` (migraciones + servidor) y `celery` (solo worker)
- ✅ **Estandarización Puerto 80 (HTTP Estándar)**
  - `ForceNoPortMiddleware` normaliza `HTTP_HOST` eliminando puertos antes de `django-tenants`
  - Dominios almacenados sin puerto (solo `cliente.localhost` o `cliente.sintel.com`)
  - Comando `fix_tenant_domains.py` elimina dominios con puerto y asegura dominio limpio único
  - `normalize_domain()` siempre elimina puertos (sin importar DEBUG)
- ✅ **Migración API-First Completa del Módulo Landing (v2.30)**
  - **TODA la lógica de negocio migrada a `apps/tenant/landing/api/`**
  - Endpoints API:
    - `GET /api/v1/landing/info/` - Información del tenant
    - `POST /api/v1/landing/auth/login/` - Login
    - `POST /api/v1/landing/auth/logout/` - Logout (API-First, retorna `redirect_url="/"`)
    - `GET /api/v1/landing/auth/logout/` - Logout (compatibilidad GET, retorna `redirect_url="/"`)
    - `GET /api/v1/landing/auth/activate/?token=...` - Validar token de activación
    - `POST /api/v1/landing/auth/activate/?token=...` - Procesar activación
    - `POST /api/v1/landing/auth/password-reset/request/` - Solicitar reset de contraseña (v2.30)
    - `GET /api/v1/landing/auth/password-reset/validate/?uidb64=...&token=...` - Validar token de reset (v2.30)
    - `POST /api/v1/landing/auth/password-reset/confirm/` - Confirmar reset de contraseña (v2.30)
      - ⚠️ **Opción A**: Devuelve `redirect_url="/"` (página principal del tenant - landing)
      - El shell estático consume `redirect_url` de la respuesta JSON y redirige a `/`
  - Serializers: `TenantPublicInfoSerializer`, `TenantLoginSerializer`, `OwnerActivationSerializer`
  - **Vistas HTML eliminadas** (`apps/tenant/landing/urls.py` y `apps/tenant/landing/views.py` eliminados)
  - URLs HTML deshabilitadas en `config/urls_tenant.py` (comentadas)
  - Toda la funcionalidad se maneja exclusivamente mediante APIs REST
  - Pruebas de humo creadas: `tests/tenant/landing/test_landing_api_smoke.py`
  - Documentación: `MIGRACION_API_FIRST_LANDING_v2.30.md`, `ELIMINACION_VISTAS_LANDING_v2.30.md`
- ✅ **Segregación Estricta de Apps**
  - `SHARED_APPS` y `TENANT_APPS` mutuamente excluyentes
  - Validaciones runtime en `settings.py` para prevenir contaminación
  - `apps.public.core` agregado a `SHARED_APPS`
  - `apps.tenant.*` JAMÁS en `SHARED_APPS`
  - `apps.public.*` JAMÁS en `TENANT_APPS`

#### v2.32 (2026-02-02)
- ✅ **SessionAuthentication en Workspace**
  - `SessionAuthentication` añadido a `DEFAULT_AUTHENTICATION_CLASSES` en DRF
  - ViewSets de gastos, clientes, proveedores y empleados usan `SessionAuthentication`
  - Permite cookies de sesión desde el mismo host del tenant para el workspace
  - DRF prioriza `authentication_classes` del ViewSet sobre configuración global
  - CSRF solo requerido para mutaciones (POST/PATCH/DELETE); GET no necesita CSRF
- ✅ **Manejo Inteligente de 401 en Módulos No Críticos**
  - Handler global del workspace no redirige módulos no críticos (gastos, clientes, proveedores) en 401
  - Módulos JS individuales lanzan `Error` en lugar de redirigir a login
  - Errores se muestran en feedback local sin interrumpir el workspace
  - Endpoints críticos (core, perfil, empresa) mantienen redirección a login en 401
  - Evita el problema de "logout inmediato" cuando un módulo falla
- ✅ **Tests de Smoke para Autenticación**
  - `test_auth_session_smoke.py` para gastos, clientes y proveedores
  - `test_workspace_401_handler_smoke.py` para validar comportamiento del handler global
  - Verifican que endpoints no devuelvan 401 tras login con sesión activa

#### v2.31 (2026-02-02)
- ✅ **Perfil API-First Completo con Serializer de Actualización Parcial**
  - `TenantProfileMeUpdateSerializer` permite actualización parcial de campos
  - Soporte para `application/json` y `multipart/form-data` (avatar)
  - Acciones específicas: `me_configuracion`, `me_avatar`
  - Service layer: `obtener_o_crear_perfil` garantiza existencia del objeto
- ✅ **CSRF Relajado Solo en Desarrollo**
  - `UnsafeSessionAuthentication` para desarrollo (`DEBUG=True`)
  - `SessionAuthentication` estándar para producción (`DEBUG=False`)
  - Aplicado en `PerfilViewSet` con `get_authenticators()` condicional
- ✅ **Workspace Perfil con Archivo JS Estático**
  - JS modular en `static/tenant/perfil/perfil.page.js`
  - Sin código inline en templates
  - Sistema de feedback consistente

#### v2.9 (2026-01-21)
- ✅ **Redirección de Root (`/`) a Consola**
  - `http://localhost:8000/` redirige automáticamente a `/console/` (dashboard del tenant actual)
  - En tenant público: redirige al dashboard global
  - En tenant privado: redirige al dashboard de ese tenant
  - Mantiene arquitectura API-First (APIs en `/api/*`), pero mejora UX
- ✅ **Logout Personalizado para Admin**
  - Vista `admin_logout_view` que acepta GET en `/admin/logout/`
  - Soluciona error 405 (Method Not Allowed) del logout por defecto de Django
  - Cierra sesión y redirige a `/` (landing page) ✅ v2.18
  - Registrado antes de `path('admin/', ...)` para override del logout por defecto

#### v2.8 (2026-01-20)
- ✅ **Autenticación JWT Global** implementada
  - JWT exclusivo para APIs REST (`Authorization: Bearer`)
  - SessionAuthentication solo para consola/UI (formularios HTML)
  - Endpoints: `/api/token/`, `/api/token/refresh/`, `/api/token/verify/`
  - Helper JS (`jwt-auth.js`): login, refresh, auto-login desde sesión
  - Endpoint helper `/console/jwt/from-session/`: genera JWT desde sesión Django
  - Integración DataTables/HTMX con auto-inyección de JWT
  - Configuración: lifetimes (15min/7d), rotación, blacklist
  - Dependencia: `djangorestframework-simplejwt>=5.3,<6.0`

#### v2.3 (2026-01-18)
- ✅ **Sistema de Ingesta (Capa A)** implementado completo
  - API REST para captura de documentos (archivo/URL)
  - Modelos `DocumentoFuente` e `IngestaLog`
  - Tareas Celery `descargar_fuente` y `procesar_fuente`
  - Soporte multi-formato (PDF/XLSX/CSV/HTML)
  - Validación de tipos y tamaño
  - Cumplimiento robots.txt y crawl_delay
- ✅ **Dashboard Web integrado** en consola
  - Listado con filtros y auto-refresh HTMX
  - Formulario de creación
  - Vista de detalle con logs en tiempo real
- ✅ **Pipeline ETL (Capa B)** implementado completo
  - Parsers: PDF, HTML, XML, Excel, CSV
  - Tokenización y normalización
  - Validaciones de negocio
  - Upserts atómicos
  - Modelo `NormaTributaria` para normas tokenizadas
- ✅ **Consola de administración** actualizada
  - Menú "Catálogo DIAN" como enlace directo
  - Integración de módulo impuestos
  - Templates dinámicos
- ✅ **Dependencias ETL** agregadas (pdfminer.six, lxml, pandas, openpyxl, beautifulsoup4)
- ✅ **Documentación actualizada** con todas las fases implementadas

#### v2.23 (2026-01-30)
- ✅ **Corrección username='' en onboarding**: UserManager mejorado para generar username único desde email, validación adicional para evitar username vacío
- ✅ **Service Layer robusto**: `create_user_service` garantiza username válido y password hasheado con `set_password()`
- ✅ **Script de saneamiento**: `sanitize_empty_usernames` para corregir usuarios existentes con username=''
- ✅ **Tests de garantía**: Verificación de username no vacío en onboarding, manejo de colisiones, idempotencia
- ✅ **Configuración producción HTTPS**: ALLOWED_HOSTS incluye siempre sintel.com y .sintel.com (incluso en desarrollo)
- ✅ **Scripts de verificación**: `verify_production_config.py` y `add_sintel_domain.py` para validar configuración
- ✅ **Documentación producción**: Guía completa en `configuracion_produccion_https.md` con Nginx, DNS, certificados
- ✅ **Configuración Nginx**: Ejemplo completo en `config/nginx/sintel.conf.example` con headers de seguridad

#### v2.22 (2026-01-30)
- ✅ **CRUD robusto de usuarios**: Service Layer con generación de username único, validación de password+password2
- ✅ **UI moderna**: Modal para crear/editar usuarios, DataTables con columnas optimizadas
- ✅ **Seguridad mejorada**: Password write_only, set_password() para hashing seguro
- ✅ **Tests completos**: Validación de creación, actualización, permisos, tenant association

#### v2.2 (2026-01-17)
- ✅ Infraestructura Docker completa (PostgreSQL 16, Redis 7, Python 3.12)
- ✅ Configuración multi-tenant (SHARED_APPS, TENANT_APPS)
- ✅ Modelo de usuario global (AbstractUser con generación automática de username)
- ✅ Gestión de tenants (Client, Domain con auto_create_schema)
- ✅ Catálogo DIAN completo (5 modelos con datos iniciales)
- ✅ Comandos de management (setup_public_tenant, poblar_catalogo_dian, check_migrations)
- ✅ Admin personalizado para todos los modelos
- ✅ **Server Guard implementado** (check_migrations bloquea arranque si hay migraciones pendientes)
- ✅ **Guardas en AppConfig.ready()** (protección contra consultas durante comandos de mantenimiento)
- ✅ **Flujo seguro de migraciones** (makemigrations → migrate → check → runserver)
- ✅ **Healthcheck mejorado** (interval: 5s, retries: 10)
- ✅ **Targets de Makefile actualizados** (makemigrations, migrate-shared, migrate-tenants, check-migrations)
- ✅ Documentación completa de arquitectura

#### v2.1 (2026-01-17)
- ✅ Infraestructura Docker completa (PostgreSQL 16, Redis 7, Python 3.12)
- ✅ Configuración multi-tenant (SHARED_APPS, TENANT_APPS)
- ✅ Modelo de usuario global (AbstractUser con generación automática de username)
- ✅ Gestión de tenants (Client, Domain con auto_create_schema)
- ✅ Catálogo DIAN completo (5 modelos con datos iniciales)
- ✅ Comandos de management (setup_public_tenant, poblar_catalogo_dian)
- ✅ Admin personalizado para todos los modelos
- ✅ Documentación completa de arquitectura

#### v1.0 (Original) - Documento Word
- Arquitectura inicial del proyecto
- Definición de principios arquitectónicos
- Estructura base propuesta
- Decisiones de diseño fundamentales

---

## ⚠️ REGLA DE ALINEACIÓN

> **OBLIGATORIO:** La estructura del proyecto (directorios, archivos, dependencias, tecnologías, configuración) **DEBE estar siempre alineada** con este documento.

**Ver:** `REGLAS_ALINEACION.md` (en esta misma carpeta) para el proceso completo de alineación y checklist.

**Antes de cualquier cambio arquitectónico:**
1. Actualizar este documento primero
2. Implementar según la documentación
3. Verificar alineación con el checklist

---

**Última Revisión:** 2026-01-31  
**Mantenido por:** Equipo de Desarrollo SINTEL  
**Versión del Documento:** 2.30  
**Documento Base:** `aquitectura_crm_sintel_v_1_operativo.docx` v1.0  
**Alineado con:** Implementación actual del código  
**Reglas de Alineación:** `REGLAS_ALINEACION.md` (en esta misma carpeta)  
**Cambios Recientes (v2.30):** 
- **Migración API-First Completa de Landing (v2.30)**
  - TODA la lógica de negocio migrada a `apps/tenant/landing/api/`
  - Vistas HTML eliminadas completamente (`apps/tenant/landing/urls.py` y `apps/tenant/landing/views.py`)
  - Endpoints API: `/api/v1/landing/info/`, `/api/v1/landing/auth/login/`, `/api/v1/landing/auth/activate/`
  - Pruebas de humo creadas: `tests/tenant/landing/test_landing_api_smoke.py`
  - Documentación: `MIGRACION_API_FIRST_LANDING_v2.30.md`, `ELIMINACION_VISTAS_LANDING_v2.30.md`
- **Facturas - Inmutabilidad Estricta y Mejoras (v2.30)**
  - **Inmutabilidad estricta**: Facturas son documentos históricos inmutables
  - **PUT/PATCH bloqueados**: Retornan 405 Method Not Allowed
  - **POST manual bloqueado**: Solo se permite importación UBL (`/upload-ubl/`, `/importar-ubl/`)
  - **DELETE como rollback**: Solo para corregir errores de carga (sin validaciones de estado/CUFE)
  - **Manejo de errores mejorado**: Detección de duplicados con mensajes amigables (`error_type: "duplicate"`)
  - **Parser UBL robusto**: Soporte para `AttachedDocument` con `Invoice` interno, namespaces dinámicos, extracción de prefijo/consecutivo
  - **Norma de Exposición de Datos**: List vs Detail serializers, QuerySets optimizados con `only()`, endpoint dedicado `/xml/`
  - **CSRF en DELETE**: Frontend incluye `X-CSRFToken` header en todas las operaciones DELETE
  - **UI mejorada**: Presentación de errores con iconos y colores, mensajes formateados, sin botón "Editar"
  - **DataTables con GET**: Cambio de POST a GET para cumplir con diseño read-only
  - Pruebas: `tests/tenant/facturas/test_factura_immutability.py`, `tests/tenant/facturas/test_attached_document_smoke.py`
- **Facturas - Workspace Limpio y Sistema de Feedback (v2.30)**
  - **Arquitectura modular**: JS/CSS externos, sin código inline en templates
  - **Sistema de feedback consistente**: Alertas locales en modales + toasts globales
  - **Toolbar unificada**: Una sola toolbar con IDs estándar (`#btn-buscar`, `#btn-refrescar`, `#btn-importar-ubl`), sin duplicados
  - **Modales únicos**: Bootstrap 5 con data attributes (`#import-modal`, `#import-error-modal`), sin legacy
  - **Búsqueda funcional**: Input `#txt-buscar` mapea a `?search=...` en API
  - **Actualización en tiempo real**: Filas se insertan/eliminan sin recargar página
  - **Limpieza completa**: Sin código legacy, sin referencias a DataTables antiguo, sin botones innecesarios (crear smoke, estado)
  - **Tests funcionales**: `tests/tenant/facturas/test_api_facturas_minimal.py` (API), `tests/e2e/test_facturas_workspace.py` (E2E)
- **Core API Centralizada (v2.30)**
  - **Orquestador único de UI privada**: Todos los flujos de autenticación y presentación están en Core
  - **SSoT de autenticación**: Login, logout, password-reset centralizados exclusivamente en `/api/v1/core/auth/*`
  - **Landing vía Core**: Info y activate accesibles desde `/api/v1/core/landing/*` consumiendo servicios de Landing
  - Toda la lógica de presentación/orquestación centralizada en `apps/tenant/core/api/`
  - Endpoints de composición: `/api/v1/core/dashboard/`, `/api/v1/core/mi-empresa/`, `/api/v1/core/mi-perfil/`, etc.
  - Servicios de orquestación en `apps/tenant/core/services/orchestration.py`
  - Servicio de auth: `apps/tenant/core/services/auth_service.py` (SSoT de autenticación)
  - Adaptador de Landing: `apps/tenant/core/services/landing_adapter.py` (consume servicios de Landing)
  - Manejadores de error (404, 403) migrados a `apps/tenant/core/api/handlers.py`
  - Branding dinámico desde BD (sin hardcodes): `apps/tenant/core/branding.py`
  - Templates base y partials reutilizables: `apps/tenant/core/templates/tenant/`
  - Workspace: `apps/tenant/core/templates/tenant/core/workspace.html` consume Core API
  - Templatetags para branding: `apps/tenant/core/templatetags/tenant_branding.py`
  - Scripts de auditoría: `scripts/audit_templates_and_branding.py`, `scripts/audit_no_duplication.py`
  - Pruebas de humo: `tests/tenant/core/smoke/` (orquestación, módulos, landing, auth, seguridad, UI contracts, E2E)
  - Política: Sin duplicación de lógica, sin hardcodes de marca, API-First estricto, UI única vía Core
- **Política SSoT de Empresa (v2.30+)**
  - `apps/tenant/empresa/api` como única fuente de verdad para datos empresariales
  - Servicio provider `apps/tenant/empresa/services.py` para consumo interno (sin HTTP)
  - Core services actualizados para usar provider (sin consultas ORM directas)
  - Campos históricos en Factura (`emisor_*`) documentados y poblados automáticamente
  - Auditorías: `scripts/audit_empresa_duplication.py` (detecta duplicación)
  - Pruebas de humo: `tests/tenant/empresa/test_empresa_ssoT.py` (verifica SSoT)
  - Patrón Singleton: `UniqueConstraint` en DB garantiza una empresa por tenant
- Server Guard mejorado (v2.20): `apps/public/core/apps.py` omite validaciones durante comandos de mantenimiento
- Script `reset_migrations.py` mejorado: asegura que `__init__.py` exista después de limpiar
- Conflicto de labels resuelto: `apps.public.core` y `apps.tenant.core` tienen labels únicos
- Entrypoint.sh mejorado: mejor manejo de conexión BD y separación web/celery
- Estandarización Puerto 80: dominios sin puerto, middleware de normalización
- Servicio centralizado de creación de tenants en `apps.public.tenants.services`
- Regla de owner único (un solo `TenantMembership.is_primary_admin=True` por tenant)
- Desacople completo de `apps.public.accounts` en la creación de tenants (solo `AUTH_USER_MODEL`)
- **Alineación completa de apps/tenant con django-tenants verificada (v2.21)**: Ver `ALINEACION_TENANT_DJANGO_TENANTS.md`
- **CRUD robusto de usuarios (v2.22)**: Service Layer con generación de username único, validación de password+password2, UI moderna con modal

# Norma General de Exposición de Datos (Proyecto SINTEL)

> **Aplica a todas las apps y endpoints del proyecto.**  
> Objetivo: garantizar **mínima exposición de datos**, **singularidad en el acceso**, **performance** y **seguridad** en un entorno **multi‑tenant por hostname**.

## 1) Principios obligatorios

1. **Mínimo necesario (Need‑to‑Know)**  
   - Las respuestas **solo** incluyen los campos requeridos por la UI/consumidor **para ese caso de uso**.  
   - Queda **prohibido** exponer columnas/campos "por si acaso".

2. **Separación Lista vs Detalle**  
   - **LIST**: endpoint de listado **ligero** (para tablas, paneles y DataTables).  
   - **DETAIL**: endpoint de detalle **bajo demanda** (uno a uno), con más campos.  
   - **Ningún** endpoint de lista debe incluir información "pesada" (XML, binarios, textos largos) o datos sensibles.

3. **Singularidad de acceso**  
   - El detalle se solicita **uno a uno** (`GET /recurso/{id}/`), nunca masivo.  
   - Cargas "pesadas" (XML, adjuntos) se exponen en **endpoints específicos** (`/xml`, `/file`, etc.), siempre **detalle**.

4. **Cero bulk por defecto**  
   - **Prohibido**: `Model.objects.all()` sin filtros contextuales o sin seleccionar campos.  
   - **Prohibido**: `fields = "__all__"` en serializers.  
   - **Obligatorio**: declarar campos explícitos en serializers y limitar columnas en QuerySets (`only`, `values`, `defer`).

5. **Paginación server‑side**  
   - Todos los listados deben paginarse (por configuración DRF/limit‑offset o cursor).  
   - La UI debe solicitar páginas de datos, jamás "traer todo".

6. **Multi‑tenant seguro (hostname)**  
   - Toda consulta debe ejecutarse **dentro del esquema** del tenant resuelto por middleware.  
   - **Prohibido**: accesos cross‑tenant.

## 2) Contrato de API

### 2.1. LIST (para tablas/paneles/DataTables)

- Ruta convencional: `GET /api/v1/<recurso>/`  
- **Serializer de lista** (campos mínimos): `*ListSerializer`  
- **QuerySet** limitado: `only(...)`, `values(...)` o `defer(...)` para reducir columnas  
- **Filtros** explícitos por query params (ej.: `?naturaleza=VENTA&nit=900&desde=YYYY-MM-DD&hasta=YYYY-MM-DD`)  
- **Respuesta** paginada  

**Ejemplo de campos típicos de lista (facturas):**  
`id`, `numero`, `naturaleza`, `estado`, `fecha_emision`, `moneda`, `subtotal`, `impuestos`, `total`, `emisor_nit`, `emisor_razon_social`, `receptor_nit`, `receptor_razon_social`, `cufe`, `qr_url`.

> Nota: **NO** incluir `xml_content`, campos muy largos, ni datos irrelevantes para la tabla.

### 2.2. DETAIL (uno a uno)

- Ruta convencional: `GET /api/v1/<recurso>/{id}/`  
- **Serializer de detalle**: `*DetailSerializer`  
- Incluye campos adicionales **solo** cuando el caso de uso lo requiera (p. ej., correos/direcciones, metadatos UBL, etc.).  
- Para artefactos "pesados", usar **acciones dedicadas**:  
  - `GET /api/v1/<recurso>/{id}/xml/` → **solo** XML  
  - `GET /api/v1/<recurso>/{id}/file/` → **solo** archivo  
  - Nunca mezclar con la respuesta de **LIST**.

## 3) Lineamientos de implementación (DRF + Django)

- **Serializers**  
  - Declarar `fields = (<lista_de_campos>)`.  
  - Mantener **dos** serializers por recurso: `*ListSerializer` (ligero) y `*DetailSerializer` (ampliado).

- **ViewSets**  
  - `get_serializer_class()` → retorna `*DetailSerializer` **solo** para `retrieve`; `*ListSerializer` para el resto.  
  - `get_queryset()`:
    - **Prohibido**: `objects.all()` "en crudo".  
    - **Obligatorio**: limitar columnas con `only(...)` / `values(...)` / `defer(...)` y **aplicar filtros** por query params.  
    - Ordenar con índices soportados por el modelo para consultas frecuentes (p. ej., `-fecha_emision`).

- **Endpoints "pesados"**  
  - Implementar como **acciones detail** (`@action(detail=True)`) que traen **solo** el artefacto solicitado (XML, PDF, etc.).  
  - **Nunca** incluir estos campos en la respuesta de listados.

- **Paginación & límites**  
  - Configurar paginación global (DRF) y, para DataTables, mapear `start/length` ↔ `limit/offset`.  
  - Ajustar tamaños por defecto (p. ej., 25–100 filas) según rendimiento.

## 4) Checklist de revisión (DoD)

**Antes de mergear una PR que agregue/ajuste endpoints:**

- [ ] El **serializer de lista** define **solo** los campos necesarios.  
- [ ] No hay `fields="__all__"` en ningún serializer.  
- [ ] El **serializer de detalle** se usa **solo** en `retrieve`.  
- [ ] `get_queryset()` **no** usa `.all()` sin limitar columnas.  
- [ ] Se usan `only()/values()/defer()` y **filtros** por query params.  
- [ ] El endpoint de **LIST** está **paginado**.  
- [ ] Artefactos pesados (XML/archivos) tienen **endpoints dedicados**.  
- [ ] Pruebas de humo:
  - **LIST** no contiene campos pesados ni sensibles.
  - **DETAIL** retorna exactamente **un** recurso.
  - **XML** solo se entrega en `/xml/`.
- [ ] Cumple el aislamiento **multi‑tenant** (middleware en orden y tests de dominio/tenant).

## 5) Ejemplo mínimo (patrón obligatorio)

> **Nota:** No es código final del proyecto; sirve como guía para cualquier app.

```python
# serializers.py
from rest_framework import serializers
from .models import Recurso

class RecursoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = ("id", "campo_a", "campo_b", "campo_c")  # mínimos de lista

class RecursoDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = ("id", "campo_a", "campo_b", "campo_c", "campo_extra_1", "campo_extra_2")
```

```python
# viewsets.py
from rest_framework.viewsets import ReadOnlyModelViewSet
from .models import Recurso
from .serializers import RecursoListSerializer, RecursoDetailSerializer
from django.db.models import Q

class RecursoViewSet(ReadOnlyModelViewSet):
    def get_serializer_class(self):
        return RecursoDetailSerializer if self.action == "retrieve" else RecursoListSerializer
    
    def get_queryset(self):
        qs = Recurso.objects.only("id", "campo_a", "campo_b", "campo_c")  # limitar columnas
        # filtros (ejemplo)
        if q := self.request.GET.get("q"):
            qs = qs.filter(Q(campo_a__icontains=q) | Q(campo_b__icontains=q))
        return qs.order_by("-id")
```

## 6) Notas para UI (DataTables / Front)

- La tabla siempre consume `GET /api/v1/<recurso>/` (lista paginada y ligera).
- Al abrir un renglón, la UI llama `GET /api/v1/<recurso>/{id}/` (detalle).
- Para ver XML/archivo, la UI llama `GET /api/v1/<recurso>/{id}/xml/` o `.../file/`.
- Nunca intentar hidratar la tabla con todos los campos del detalle.

## Mantenimiento

- Esta norma es **obligatoria** para nuevas apps/recursos.
- Refactors deben alinear endpoints existentes a estos lineamientos durante su ciclo de vida.

---

## 📚 Documentación Frontend (Helpers Core)

**Helpers Core — SINTEL v2.37:**
- **README Helpers:** `apps/tenant/core/static/core/js/helpers/README.md`
  - Documentación de `lib/` (http.js, api-helpers.js, dom-utils.js, datatables-utils.js)
  - Documentación de `helpers/` (routes.js, crud.js, module.js, error-service.js, modal-service.js)
  - Convenciones y ejemplo antes → después

- **Guía Columnas / rowId:** `documentacion/GUIA_COLUMNAS_ROWID.md`
  - Alineación de columnas con `<th>`
  - Configuración de `rowId` y `DT_RowId`
  - Buenas prácticas para evitar re-inicializaciones

- **Cookbook Modales CRUD:** `documentacion/COOKBOOK_MODALES_CRUD.md`
  - Ejemplos de uso de `ModalService` + `CRUD`
  - Patrones para crear/editar/eliminar
  - Integración con DataTables y recarga sin perder estado

- **Snippets Mínimos DataTables:** `documentacion/SNIPPETS_MINIMOS_DATATABLES.md`
  - Snippets listos para producción
  - Ajuste de columnas en tabs
  - Inyección CSRF por request
  - Error handling global
  - StateSave y persistencia de estado
  - Referencias a documentación oficial

---

## 🔧 Guía de Solución de Problemas Comunes (v2.40)

**⚠️ IMPORTANTE:** Esta guía documenta problemas comunes y sus soluciones para evitar errores en futuras apps.

- **Guía Solución Problemas URLs:** `documentacion/GUIA_SOLUCION_PROBLEMAS_URLS_V2.40.md`
  - **Problema 1:** ImportError en `services/__init__.py` (conflicto paquete/archivo)
  - **Problema 2:** AttributeError 'User' object has no attribute 'empresa' (multi-tenant)
  - **Problema 3:** 404 en endpoints de API (router no configurado)
  - **Problema 4:** TypeError en GET requests con body (protocolo HTTP)
  - **Checklist completo** para nuevas apps
  - **Patrones correctos** con ejemplos de código
  - **Referencias** a apps corregidas (empleados, gastos)

**⚠️ REGLA DE ORO:** Antes de crear una nueva app tenant, revisar esta guía para evitar problemas comunes.

---

## 📋 Workspace Módulo Empresa (v2.37 - Estabilizado)

**⚠️ IMPORTANTE:** El módulo Empresa en el workspace ha sido completamente refactorizado y estabilizado. Cualquier modificación debe seguir estrictamente las reglas documentadas.

**Documentación completa:** Ver `documentacion/WORKSPACE_MODULO_EMPRESA_v2.37.md`

### Arquitectura del Módulo

El tab `workspace/#empresa` contiene **dos módulos completamente independientes**:

1. **EmpresaModule** → Consume `/api/v1/empresas/`
   - Tabla: `#tabla-empresa`
   - Columnas: NIT, Dirección, Teléfono, Email, Régimen, Moneda, Acciones (7 columnas)
   - Serializer: `EmpresaListSerializer` (campos mínimos)
   - JS: `apps/tenant/core/static/core/js/empresa/empresa.page.js`

2. **MailInboxConfigModule** → Consume `/api/v1/empresas/mail-inbox-config/`
   - Tabla: `#tabla-mailinbox`
   - Serializer: `MailInboxConfigListSerializer`
   - JS: `apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js`

### Reglas Obligatorias

1. **Backend:**
   - `EmpresaListSerializer` solo expone: `nit`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `moneda`
   - NO expone: `id`, `razon_social`, `logo`, `website`, ni campos pesados
   - Endpoint `GET /api/v1/empresas/` retorna array: `[]` o `[data]` (singleton)

2. **Frontend HTML:**
   - Exactamente 7 columnas en `<thead>` (orden específico)
   - Selector: `id="tabla-empresa"` (NO cambiar)
   - Shell puro (sin render server-side)

3. **Frontend JS:**
   - Fetcher resiliente: `fetchEmpresaList()` maneja índice HATEOAS y colección directa
   - Columnas alineadas exactamente con HTML y Serializer
   - Logging consistente: `[empresa.page]`
   - Manejo 401 inteligente (no redirige)

4. **Tests:**
   - Tests de smoke actúan como salvaguardas
   - Validación de columnas, campos API, selector

### ⚠️ Cambios Prohibidos Sin Justificación

- Agregar/quitar columnas sin actualizar HTML, JS y tests
- Cambiar selector `#tabla-empresa`
- Exponer campos adicionales en `EmpresaListSerializer`
- Cambiar formato de respuesta del endpoint
- Eliminar tests de smoke sin reemplazo

**Referencia completa:** `documentacion/WORKSPACE_MODULO_EMPRESA_v2.37.md`