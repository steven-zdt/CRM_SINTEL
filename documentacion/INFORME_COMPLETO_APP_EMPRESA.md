# 📊 Informe Completo y Estructural: App `apps/tenant/empresa`

**Fecha de Generación:** 2025-01-XX  
**Versión del Sistema:** v2.30+  
**Estado:** ✅ Funcional y Operativo

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Estructura de la App](#estructura-de-la-app)
4. [Modelos de Datos](#modelos-de-datos)
5. [Service Layer](#service-layer)
6. [APIs REST (DRF)](#apis-rest-drf)
7. [Integración con Otras Apps (SSoT)](#integración-con-otras-apps-ssoT)
8. [Integración con Workspace](#integración-con-workspace)
9. [Flujos de Datos](#flujos-de-datos)
10. [Casos de Uso](#casos-de-uso)
11. [Validaciones y Seguridad](#validaciones-y-seguridad)
12. [Comandos de Gestión](#comandos-de-gestión)
13. [Tests y Calidad](#tests-y-calidad)
14. [Diagramas de Flujo](#diagramas-de-flujo)
15. [Conclusiones y Recomendaciones](#conclusiones-y-recomendaciones)

---

## 1. Resumen Ejecutivo

### 1.1 Propósito

La app `apps/tenant/empresa` es el **Single Source of Truth (SSoT)** para todos los datos empresariales del sistema. Implementa el patrón **Singleton** (una empresa por tenant) y proporciona servicios centralizados para consumo interno entre apps.

### 1.2 Principios Arquitectónicos

- ✅ **API-First**: Todas las operaciones expuestas vía APIs REST (JSON-only)
- ✅ **Service Layer**: Lógica de negocio centralizada en servicios, no en vistas
- ✅ **Multi-tenant**: Aislamiento por esquema (django-tenants)
- ✅ **Singleton**: Una única empresa por tenant (garantizado por constraint DB)
- ✅ **Cero Signals**: Toda la lógica es explícita y controlada
- ✅ **SSoT**: Única fuente de verdad para datos empresariales
- ✅ **Optimización**: Querysets optimizados con `only()`, `select_related()`

### 1.3 Estado Actual

**✅ FUNCIONAL Y OPERATIVO**

- Modelos correctamente definidos y migrados
- Service Layer completo y funcional
- APIs REST completas (CRUD)
- Integración SSoT con otras apps (facturas)
- Integración con workspace funcional
- Comandos de auditoría disponibles
- Tests básicos implementados

---

## 2. Arquitectura General

### 2.1 Patrón de Diseño

```
┌─────────────────────────────────────────────────────────────┐
│                    apps/tenant/empresa                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Models     │───▶│  Services    │───▶│     APIs     │ │
│  │ (Empresa,    │    │  (SSoT)      │    │  (ViewSets)  │ │
│  │  MailInbox)  │    │              │    │              │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │         │
│         └────────────────────┼────────────────────┘         │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │   Workspace UI    │                   │
│                    │  (HTML + JS)      │                   │
│                    └────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Separación de Responsabilidades

| Capa | Responsabilidad | Ubicación |
|------|----------------|-----------|
| **Modelos** | Definición de esquema de datos | `models.py` |
| **Service Layer** | Lógica de negocio, validaciones | `services.py`, `impl/` |
| **APIs** | Exposición REST, serialización | `api/viewsets.py`, `api/serializers.py` |
| **UI** | Presentación, interacción usuario | `workspace.html`, `empresa.ui.js` |
| **Integración** | Consumo SSoT por otras apps | `facturas/services.py`, `core/services/` |

### 2.3 Multi-tenancy

- **Aislamiento**: Por esquema (django-tenants)
- **Middleware**: `TenantMainMiddleware` establece schema antes de queries
- **Transparencia**: Los servicios no necesitan filtrar por `tenant_id`
- **Singleton**: Una empresa por esquema (garantizado por `UniqueConstraint`)

---

## 3. Estructura de la App

### 3.1 Árbol de Directorios

```
apps/tenant/empresa/
├── __init__.py
├── apps.py                    # Configuración de app (label: 'tenant_empresa')
├── models.py                  # Modelos: Empresa, MailInboxConfig
├── admin.py                   # Configuración Django Admin
├── permissions.py             # Permisos personalizados (IsTenantAdmin)
├── services.py                # ⚠️ SSoT Provider: get_empresa_emisor_data()
│
├── api/                       # APIs REST (DRF)
│   ├── __init__.py
│   ├── viewsets.py           # EmpresaViewSet (CRUD completo)
│   ├── serializers.py        # EmpresaSerializer (DTO canónico)
│   ├── urls.py               # Router DRF + endpoints auxiliares
│   ├── views.py              # Vistas auxiliares (form-metadata, lookup)
│   ├── views_mailbox.py      # APIs para MailInboxConfig
│   ├── filters.py            # Filtros DRF
│   ├── pagination.py         # Paginación personalizada
│   ├── permissions.py        # Permisos API
│   └── redirects.py          # Redirecciones de compatibilidad
│
├── impl/                      # ⚠️ Service Layer interno (renombrado desde services/)
│   ├── __init__.py
│   ├── empresa_service.py    # get_empresa(), get_or_create_empresa(), update_empresa()
│   ├── mailbox_service.py     # CRUD para MailInboxConfig
│   └── mailbox_provider.py   # Provider SSoT para configuraciones de correo
│
├── choices/                   # Catálogos DIAN (choices locales)
│   ├── __init__.py
│   ├── ciiu.py               # Códigos CIIU
│   ├── regimen.py            # Régimen tributario
│   ├── responsabilidad_rut.py # Responsabilidades RUT
│   └── segmento_dian.py     # Segmentos DIAN
│
├── management/commands/       # Comandos Django
│   ├── audit_empresa_app.py  # Auditoría completa de la app
│   └── audit_empresa_nit.py  # Auditoría de NIT por tenant
│
├── migrations/                # Migraciones Django
│   ├── 0001_initial.py
│   ├── 0002_add_singleton_constraint.py
│   ├── 0003_add_catalogos_dian_referencias.py
│   ├── 0004_add_actividad_economica.py
│   ├── 0005_rename_actividad_economica_codigo_to_actividad_economica.py
│   ├── 0006_alter_empresa_actividad_economica.py
│   ├── 0007_add_mail_inbox_config.py
│   └── 0008_mailinboxconfig_gmail_fields.py
│
├── static/                    # Assets estáticos
│   ├── empresa/
│   │   └── js/
│   │       └── empresas.js    # JS legacy (deprecado)
│   └── tenant/empresa/
│       ├── empresa.ui.js     # UI Module (API-First)
│       └── index.html        # Página standalone (opcional)
│
├── templates/                 # Templates HTML
│   └── tenant/empresa/
│       ├── page.html          # Página standalone (opcional)
│       └── partials/
│           └── card.html      # Partial para HTMX (opcional)
│
├── tests/                     # Tests
│   ├── __init__.py
│   ├── test_api_empresa.py   # Tests de APIs
│   └── test_templates.py     # Tests de templates
│
├── urls_ui.py                 # URLs UI (DEPRECADO en v2.30+)
├── views_ui.py                # Vistas UI (DEPRECADO en v2.30+)
├── views.py                    # Vistas auxiliares
└── AUDITORIA.md               # Auditoría de la app (documentación interna)
```

### 3.2 Dependencias

**Internas:**
- `apps.tenant.api.permissions` → `IsTenantMember`
- `apps.tenant.empresa.permissions` → `IsTenantAdmin`
- `apps.tenant.core.services` → Adapter para Core API

**Externas:**
- `django-tenants` → Multi-tenancy por esquema
- `djangorestframework` → APIs REST
- `django-filters` → Filtros avanzados

**Consumidas por:**
- `apps.tenant.facturas` → `get_empresa_emisor_data()` (SSoT)
- `apps.tenant.core` → Core API adapter
- `apps/tenant/core/templates/tenant/core/workspace.html` → UI del workspace

---

## 4. Modelos de Datos

### 4.1 Modelo `Empresa`

**Ubicación:** `apps/tenant/empresa/models.py`

#### 4.1.1 Características Principales

- **Patrón Singleton**: Una única instancia por tenant
- **Constraint DB**: `UniqueConstraint` en `singleton_key` garantiza singleton
- **Multi-tenant**: Aislado por esquema (django-tenants)
- **Cero Signals**: Toda la lógica en Service Layer

#### 4.1.2 Campos Principales

| Campo | Tipo | Descripción | Restricciones |
|-------|------|-------------|---------------|
| `singleton_key` | `PositiveSmallIntegerField` | Clave técnica para singleton | `default=1`, `editable=False` |
| `razon_social` | `CharField(255)` | Nombre legal de la empresa | Requerido |
| `nit` | `CharField(20)` | NIT sin DV | `unique=True`, Requerido |
| `dv` | `CharField(1)` | Dígito verificador | Calculado automáticamente |
| `direccion` | `CharField(500)` | Dirección completa | Requerido |
| `telefono` | `CharField(20)` | Teléfono de contacto | Requerido |
| `email_contacto` | `EmailField` | Email de contacto | Opcional |
| `tipo_contribuyente_clase` | `CharField(2)` | PN o PJ | Opcional |
| `tipo_contribuyente_segmento` | `CharField(32)` | Segmento DIAN | Opcional |
| `regimen_renta_codigo` | `CharField(20)` | Régimen de renta | Opcional |
| `responsabilidades_rut_codigos` | `JSONField` | Lista de códigos RUT | Opcional |
| `actividad_economica` | `CharField(16)` | Código CIIU | Opcional |
| `regimen_tributario` | `CharField(50)` | ⚠️ Legacy (deprecado) | Opcional |
| `logo` | `ImageField` | Logo de la empresa | Opcional |
| `website` | `URLField` | Sitio web | Opcional |
| `moneda` | `CharField(3)` | Código ISO 4217 | `default='COP'` |
| `created_at` | `DateTimeField` | Fecha de creación | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Fecha de actualización | `auto_now=True` |

#### 4.1.3 Constraints y Validaciones

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['singleton_key'],
            name='unique_singleton_empresa_per_schema',
            violation_error_message=_('Solo se permite una empresa por tenant.')
        )
    ]
```

**Garantías:**
- ✅ Una sola empresa por esquema (tenant)
- ✅ NIT único a nivel de base de datos
- ✅ Validaciones de formato en Service Layer

### 4.2 Modelo `MailInboxConfig`

**Ubicación:** `apps/tenant/empresa/models.py`

#### 4.2.1 Propósito

Configuración de buzones de correo para ingesta automática de facturas (SSoT para credenciales de correo).

#### 4.2.2 Campos Principales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | `CharField(120)` | Nombre descriptivo de la configuración |
| `provider` | `CharField(20)` | `custom` o `gmail` |
| `protocol` | `CharField(10)` | `imap` o `pop3` |
| `host` | `CharField(255)` | Servidor IMAP/POP3 |
| `port` | `PositiveIntegerField` | Puerto del servidor |
| `username` | `CharField(255)` | Usuario/email |
| `password` | `CharField(255)` | ⚠️ Contraseña (sin cifrar, TODO) |
| `activo` | `BooleanField` | Si está activo para ingesta |
| `imap_max_attachment_mb` | `PositiveIntegerField` | Límite de tamaño de adjuntos |

#### 4.2.3 Características

- **Multi-tenant**: Aislado por esquema
- **SSoT**: Única fuente de credenciales de correo
- **Gmail Preset**: Autocompletado de IMAP/SMTP para Gmail
- **Seguridad**: ⚠️ Password sin cifrar (TODO: implementar cifrado)

---

## 5. Service Layer

### 5.1 Arquitectura del Service Layer

El Service Layer está dividido en dos partes:

1. **`services.py` (SSoT Provider)**: Funciones para consumo interno entre apps
2. **`impl/` (Service Layer interno)**: Lógica de negocio del dominio Empresa

### 5.2 `apps/tenant/empresa/services.py` (SSoT Provider)

#### 5.2.1 Función Principal: `get_empresa_emisor_data()`

**Propósito:** SSoT para otras apps (especialmente `facturas`)

**Ubicación:** `apps/tenant/empresa/services.py:164`

**Contrato:**
```python
def get_empresa_emisor_data() -> Dict[str, Any]:
    """
    SSoT: Devuelve el NIT de la Empresa del tenant actual.
    
    ⚠️ REQUISITO: Requiere que TenantMainMiddleware ya haya fijado el schema.
    Sin Empresa/NIT → lanza EmpresaNotConfiguredError (no retorna None).
    
    Returns:
        Dict con datos del emisor:
        {
            'nit': str,
            'razon_social': str,
            'dv': str,
            'nit_completo': str,
            'direccion': str,
            'telefono': str,
            'email_contacto': str | None,
        }
        
    Raises:
        EmpresaNotConfiguredError: Si no existe Empresa o carece de NIT
    """
```

**Uso en otras apps:**
```python
from apps.tenant.empresa.services import get_empresa_emisor_data, EmpresaNotConfiguredError

try:
    empresa = get_empresa_emisor_data()
    empresa_nit = empresa.get("nit")
    # Usar empresa_nit para determinar naturaleza de factura
except EmpresaNotConfiguredError:
    # Retornar 422 si falta SSoT
    return {"error": "empresa_no_configurada"}, 422
```

**Características:**
- ✅ **Nunca retorna None**: Lanza excepción si falta empresa/NIT
- ✅ **Optimizado**: Usa `only()` para limitar columnas
- ✅ **Tenant-aware**: Transparente gracias a django-tenants

#### 5.2.2 Otras Funciones (Deprecadas)

- `get_empresa_data()`: ⚠️ Deprecado, usar `impl.get_empresa()`
- `crear_empresa()`: ⚠️ Deprecado, usar `impl.get_or_create_empresa()`
- `actualizar_empresa()`: ⚠️ Deprecado, usar `impl.update_empresa()`

### 5.3 `apps/tenant/empresa/impl/` (Service Layer Interno)

#### 5.3.1 `empresa_service.py`

**Funciones principales:**

| Función | Propósito | Retorna |
|---------|-----------|---------|
| `get_empresa()` | Obtiene empresa del tenant (singleton) | `Dict[str, Any] \| None` |
| `get_or_create_empresa(defaults)` | Obtiene o crea empresa | `Dict[str, Any]` |
| `update_empresa(data)` | Actualiza empresa con validaciones | `Dict[str, Any]` |

**Validaciones en `update_empresa()`:**
- ✅ Tipos de datos (str, int, etc.)
- ✅ Longitudes máximas
- ✅ Formatos (email, URL)
- ✅ Campos requeridos no vacíos

**Ejemplo de uso:**
```python
from apps.tenant.empresa.impl import get_empresa, update_empresa

# Obtener empresa
empresa_dto = get_empresa()
if empresa_dto:
    print(f"NIT: {empresa_dto['nit']}")

# Actualizar empresa
update_empresa({
    'razon_social': 'Nueva Razón Social',
    'nit': '901123299',
    'email_contacto': 'nuevo@email.com'
})
```

#### 5.3.2 `mailbox_service.py`

**Funciones CRUD para `MailInboxConfig`:**

| Función | Propósito |
|---------|-----------|
| `list_mailbox_configs()` | Lista configuraciones activas |
| `create_mailbox_config(data)` | Crea nueva configuración |
| `update_mailbox_config(id, data)` | Actualiza configuración |
| `delete_mailbox_config(id)` | Elimina configuración |

#### 5.3.3 `mailbox_provider.py`

**Provider SSoT para configuraciones de correo:**

- Obtiene configuraciones activas por tenant
- Filtra por `activo=True`
- Optimizado con `only()`

---

## 6. APIs REST (DRF)

### 6.1 ViewSet Principal: `EmpresaViewSet`

**Ubicación:** `apps/tenant/empresa/api/viewsets.py:32`

#### 6.1.1 Configuración

```python
class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
```

**Características:**
- ✅ **SessionAuthentication**: Compatible con cookies de sesión
- ✅ **IsTenantAdmin**: Solo admins pueden escribir
- ✅ **MultiPartParser**: Soporte para subida de logo

#### 6.1.2 Endpoints CRUD

| Método | Endpoint | Acción | Service Layer | Status Codes |
|--------|----------|--------|---------------|--------------|
| `GET` | `/api/v1/empresas/` | Lista empresa (singleton) | `get_queryset().first()` | `200` (array con 1 elemento o vacío) |
| `GET` | `/api/v1/empresas/{id}/` | Obtiene empresa por ID | `get_queryset().get()` | `200`, `404` |
| `POST` | `/api/v1/empresas/` | Crea empresa | `impl.get_or_create_empresa()` | `201`, `409` (si ya existe) |
| `PUT` | `/api/v1/empresas/{id}/` | Actualiza empresa completa | `impl.update_empresa()` | `200`, `404` |
| `PATCH` | `/api/v1/empresas/{id}/` | Actualiza empresa parcial | `impl.update_empresa()` | `200`, `404` |
| `DELETE` | `/api/v1/empresas/{id}/` | Elimina empresa | `instance.delete()` | `204`, `404` |

#### 6.1.3 Acciones Personalizadas

| Acción | Endpoint | Método | Propósito |
|--------|----------|--------|-----------|
| `mi_empresa` | `/api/v1/empresas/mi-empresa/` | `GET` | Endpoint de conveniencia (singleton) |
| `options` | `/api/v1/empresas/options/` | `GET` | Metadata de opciones (choices) |

#### 6.1.4 Optimización de Querysets

```python
def get_queryset(self):
    empresa_fields = (
        'id', 'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
        'tipo_contribuyente_clase', 'tipo_contribuyente_segmento', 'regimen_renta_codigo',
        'responsabilidades_rut_codigos', 'actividad_economica', 'regimen_tributario',
        'logo', 'website', 'moneda', 'created_at', 'updated_at'
    )
    
    if self.action in ("list", "retrieve"):
        qs = Empresa.objects.only(*empresa_fields)  # ✅ Optimizado
    else:
        qs = Empresa.objects.all()  # Para create/update/delete
    
    return qs
```

**Beneficios:**
- ✅ Reduce carga de datos innecesarios
- ✅ Mejora rendimiento en listados
- ✅ Respeta principio de mínima exposición

### 6.2 Serializer: `EmpresaSerializer`

**Ubicación:** `apps/tenant/empresa/api/serializers.py:16`

#### 6.2.1 Contrato Canónico (DTO)

El serializer define el **contrato estable** de datos empresariales que todas las apps deben consumir.

**Campos expuestos:**
```python
fields = [
    'id', 'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
    'tipo_contribuyente_clase', 'tipo_contribuyente_segmento', 'regimen_renta_codigo',
    'responsabilidades_rut_codigos', 'actividad_economica', 'regimen_tributario',
    'logo', 'website', 'moneda', 'created_at', 'updated_at',
]
```

**Read-only fields:**
- `id`, `dv`, `created_at`, `updated_at`

**SerializerMethodField:**
- `logo`: Retorna URL absoluta usando `request.build_absolute_uri()`

#### 6.2.2 Validaciones

- ✅ **NIT**: Formato y longitud
- ✅ **Email**: Formato válido
- ✅ **URL**: Formato válido (http:// o https://)
- ✅ **Coherencia DIAN**: No permite 48 y 49 simultáneos; SIMPLE requiere 47

### 6.3 Router y URLs

**Ubicación:** `apps/tenant/empresa/api/urls.py`

#### 6.3.1 Rutas Principales

```python
router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresas')

urlpatterns = router.urls + [
    path('empresa/form-metadata/', form_metadata, name='empresa-form-metadata'),
    path('empresa/actividades-lookup/', actividades_lookup, name='empresa-actividades-lookup'),
    path('empresa/ciiu-lookup/', ciiu_lookup, name='empresa-ciiu-lookup'),
    path('mailbox/configs/', MailInboxConfigListCreateAPIView.as_view()),
    path('mailbox/configs/<int:id>/', MailInboxConfigRetrieveUpdateDestroyAPIView.as_view()),
]
```

#### 6.3.2 Integración en `config/api_urls.py`

```python
urlpatterns.append(path('empresas/', include('apps.tenant.empresa.api.urls')))
```

**Rutas resultantes:**
- `/api/v1/empresas/` → Lista/Crea empresa
- `/api/v1/empresas/{id}/` → Obtiene/Actualiza/Elimina empresa
- `/api/v1/empresas/mi-empresa/` → Endpoint de conveniencia
- `/api/v1/empresas/options/` → Metadata de opciones
- `/api/v1/empresa/form-metadata/` → Metadata para formularios
- `/api/v1/empresa/actividades-lookup/` → Búsqueda de actividades
- `/api/v1/empresa/ciiu-lookup/` → Búsqueda CIIU
- `/api/v1/mailbox/configs/` → CRUD de configuraciones de correo

---

## 7. Integración con Otras Apps (SSoT)

### 7.1 Consumo desde `apps/tenant/facturas`

**Ubicación:** `apps/tenant/facturas/services.py:21`

```python
from apps.tenant.empresa.services import (
    get_empresa_emisor_data,
    EmpresaNotConfiguredError,
)

# En importar_ubl():
try:
    empresa = get_empresa_emisor_data()
    empresa_nit = empresa.get("nit")
    # Calcular naturaleza comparando emisor_nit vs empresa_nit
except EmpresaNotConfiguredError:
    return {"error": "empresa_no_configurada"}, 422
```

**Propósito:**
- Determinar naturaleza de factura (VENTA/COMPRA)
- Comparar `emisor_nit` del XML vs `empresa_nit` del tenant
- Si coinciden → VENTA (el tenant emite)
- Si difieren → COMPRA (el tenant recibe)

### 7.2 Consumo desde `apps/tenant/core`

**Ubicación:** `apps/tenant/core/services/empresa.py`

```python
from apps.tenant.empresa.services import get_empresa_data

def get_mi_empresa(tenant):
    empresa_data = get_empresa_data()
    # Componer DTO para Core API
    return {...}
```

**Propósito:**
- Orquestar datos de empresa para Core API
- Componer DTOs con branding
- Exponer `/api/v1/core/empresa/` para workspace

### 7.3 Política SSoT

**Reglas:**
1. ✅ **Única fuente**: `apps/tenant/empresa` es la única fuente de datos empresariales
2. ✅ **No duplicar**: Otras apps NO deben duplicar campos como `nit`, `razon_social`
3. ✅ **Consumo vía servicio**: Usar `get_empresa_emisor_data()` o `get_empresa_data()`
4. ✅ **No HTTP interno**: Usar ORM directo, no llamadas HTTP internas

---

## 8. Integración con Workspace

### 8.1 HTML en Workspace

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html:108`

#### 8.1.1 Sección `#view-empresa`

```html
<section class="panel card" id="view-empresa" hidden>
  <div class="card-header">
    <div class="card-title">🏢 Empresa (SSoT)</div>
    <div class="actions-row">
      <button class="btn" id="btn-edit-empresa">Editar</button>
      <button class="btn primary hidden" id="btn-save-empresa">Guardar</button>
      <button class="btn hidden" id="btn-cancel-empresa">Cancelar</button>
    </div>
  </div>
  <div class="card-body">
    <form id="form-empresa" class="kgrid-2" novalidate enctype="multipart/form-data">
      <!-- Campos del formulario -->
    </form>
    <div class="status" id="status-empresa"></div>
  </div>
</section>
```

**Características:**
- ✅ Formulario completo con todos los campos de Empresa
- ✅ Soporte para subida de logo (multipart/form-data)
- ✅ Modo edición/visualización
- ✅ Feedback de estado (`status-empresa`)

#### 8.1.2 Navegación

```html
<li>
  <a href="#empresa" data-view="empresa" role="link">
    🏢 Empresa <span class="pill" id="pill-empresa">SSoT</span>
  </a>
</li>
```

**Indicador SSoT:** El pill "SSoT" indica que esta es la Single Source of Truth.

### 8.2 JavaScript en Workspace

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html:901`

#### 8.2.1 Funciones Principales

| Función | Propósito | Endpoint |
|---------|-----------|----------|
| `loadEmpresa()` | Carga datos de empresa | `GET /api/v1/core/empresa/` |
| `readEmpresaForm()` | Lee valores del formulario | - |
| `saveEmpresa()` | Guarda cambios | `PATCH /api/v1/core/empresa/` |

#### 8.2.2 Flujo de Carga

```javascript
async function loadEmpresa(){
  const r = await http("GET", "/api/v1/core/empresa/");
  if (r.ok) {
    const data = await r.json();
    // Llenar formulario con datos
    document.getElementById("emp_razon_social").value = data.razon_social || "";
    // ... más campos
  } else {
    // Mostrar mensaje: "Aún no existe Empresa en este tenant"
  }
}
```

#### 8.2.3 Flujo de Guardado

```javascript
async function saveEmpresa(){
  const payload = readEmpresaForm();
  const formData = new FormData();
  // Agregar campos al FormData
  // Incluir logo si hay archivo
  
  const r = await makeRequest("PATCH", "/api/v1/core/empresa/", formData, true);
  if (r.ok) {
    // Mostrar éxito
  } else {
    // Mostrar error
  }
}
```

### 8.3 Core API Adapter

**Ubicación:** `apps/tenant/core/services/empresa.py`

**Propósito:** Orquestar datos de empresa para Core API (`/api/v1/core/empresa/`)

**Funciones:**
- `get_mi_empresa(tenant)`: Obtiene empresa con branding
- `get_empresas_snapshot(tenant)`: Snapshot para dashboard

**Endpoint Core API:**
- `GET /api/v1/core/empresa/` → Retorna empresa del tenant con branding
- `PATCH /api/v1/core/empresa/` → Actualiza empresa (usa `impl.update_empresa()`)

---

## 9. Flujos de Datos

### 9.1 Flujo de Creación de Empresa

```
┌─────────────┐
│   Usuario   │
│  (Workspace)│
└──────┬──────┘
       │ 1. Llena formulario
       ▼
┌─────────────────┐
│  workspace.html │
│  (JavaScript)   │
└──────┬──────────┘
       │ 2. POST /api/v1/empresas/
       ▼
┌─────────────────┐
│ EmpresaViewSet  │
│   .create()     │
└──────┬──────────┘
       │ 3. Valida singleton
       ▼
┌─────────────────┐
│ impl.get_or_    │
│ create_empresa()│
└──────┬──────────┘
       │ 4. Crea Empresa
       ▼
┌─────────────────┐
│   models.Empresa│
│   .objects.     │
│   create()      │
└──────┬──────────┘
       │ 5. Persiste en BD
       ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Schema)      │
└─────────────────┘
```

### 9.2 Flujo de Consumo SSoT (Facturas)

```
┌─────────────────┐
│  facturas/      │
│  services.py     │
└──────┬──────────┘
       │ 1. importar_ubl()
       ▼
┌─────────────────┐
│ get_empresa_    │
│ emisor_data()   │
└──────┬──────────┘
       │ 2. Query Empresa
       ▼
┌─────────────────┐
│   models.Empresa│
│   .objects.     │
│   .first()      │
└──────┬──────────┘
       │ 3. Retorna NIT
       ▼
┌─────────────────┐
│  facturas/      │
│  services.py     │
│  _determinar_    │
│  naturaleza()   │
└──────┬──────────┘
       │ 4. Compara NITs
       ▼
┌─────────────────┐
│  VENTA/COMPRA   │
└─────────────────┘
```

### 9.3 Flujo de Actualización desde Workspace

```
┌─────────────┐
│   Usuario   │
│  (Workspace)│
└──────┬──────┘
       │ 1. Edita campos
       ▼
┌─────────────────┐
│  workspace.html │
│  saveEmpresa()  │
└──────┬──────────┘
       │ 2. PATCH /api/v1/core/empresa/
       ▼
┌─────────────────┐
│  Core API       │
│  (empresa.py)   │
└──────┬──────────┘
       │ 3. Orquesta
       ▼
┌─────────────────┐
│ impl.update_    │
│ empresa()       │
└──────┬──────────┘
       │ 4. Valida datos
       ▼
┌─────────────────┐
│   models.Empresa│
│   .save()       │
└──────┬──────────┘
       │ 5. Persiste
       ▼
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘
```

---

## 10. Casos de Uso

### 10.1 Caso de Uso 1: Crear Empresa en Nuevo Tenant

**Actor:** Administrador del tenant

**Flujo:**
1. Accede a `workspace/#empresa`
2. Ve mensaje: "Aún no existe Empresa en este tenant"
3. Llena formulario con datos de la empresa
4. Sube logo (opcional)
5. Guarda
6. Sistema crea empresa con `singleton_key=1`
7. Muestra éxito: "Empresa guardada"

**Validaciones:**
- ✅ NIT único
- ✅ Campos requeridos no vacíos
- ✅ Formato de email válido
- ✅ Formato de URL válido

### 10.2 Caso de Uso 2: Importar Factura (Requiere Empresa)

**Actor:** Usuario del tenant

**Flujo:**
1. Accede a `workspace/#facturas`
2. Intenta importar XML
3. Sistema llama `get_empresa_emisor_data()`
4. Si no hay empresa → Error 422: "Empresa no configurada"
5. Si hay empresa → Calcula naturaleza (VENTA/COMPRA)
6. Persiste factura con naturaleza correcta

**Validaciones:**
- ✅ Empresa debe existir
- ✅ Empresa debe tener NIT
- ✅ Naturaleza calculada automáticamente

### 10.3 Caso de Uso 3: Actualizar Datos de Empresa

**Actor:** Administrador del tenant

**Flujo:**
1. Accede a `workspace/#empresa`
2. Ve datos actuales de la empresa
3. Hace clic en "Editar"
4. Modifica campos (ej: email, teléfono)
5. Guarda
6. Sistema valida y actualiza
7. Muestra éxito: "Empresa guardada"

**Validaciones:**
- ✅ Tipos de datos correctos
- ✅ Longitudes máximas
- ✅ Formatos válidos (email, URL)

### 10.4 Caso de Uso 4: Auditoría de Tenants sin Empresa

**Actor:** Administrador del sistema

**Flujo:**
1. Ejecuta: `python manage.py all_tenants_command audit_empresa_nit`
2. Sistema itera todos los tenants
3. Para cada tenant, verifica si existe Empresa y NIT
4. Reporta:
   - ✅ Tenants con Empresa y NIT
   - ❌ Tenants sin Empresa
   - ⚠️ Tenants con Empresa pero sin NIT

**Uso:**
- Identificar tenants que necesitan configuración
- Validar integridad de datos
- Preparar migraciones o backfills

---

## 11. Validaciones y Seguridad

### 11.1 Validaciones en Service Layer

**Ubicación:** `apps/tenant/empresa/impl/empresa_service.py:93`

**Validaciones implementadas:**

| Campo | Validación |
|------|------------|
| `razon_social` | Tipo str, longitud ≤ 255, no vacío |
| `nit` | Tipo str, longitud ≤ 20, no vacío |
| `email_contacto` | Tipo str o null, formato email válido |
| `website` | Tipo str o null, formato URL válido (http:// o https://) |

**Ejemplo:**
```python
if campo == 'razon_social':
    if not isinstance(valor, str):
        raise ValueError("El campo 'razon_social' debe ser una cadena de texto.")
    if len(valor) > 255:
        raise ValueError("El campo 'razon_social' no puede exceder 255 caracteres.")
    if not valor.strip():
        raise ValueError("El campo 'razon_social' no puede estar vacío.")
```

### 11.2 Validaciones en Serializer

**Ubicación:** `apps/tenant/empresa/api/serializers.py:115`

**Validaciones:**
- ✅ Coherencia de selecciones DIAN
- ✅ Formato de NIT
- ✅ Formato de email
- ✅ Formato de URL

### 11.3 Permisos

**ViewSet:**
- `IsAuthenticated`: Usuario debe estar autenticado
- `IsTenantAdmin`: Solo admins pueden escribir (create/update/delete)

**Definición:**
```python
permission_classes = [IsAuthenticated, IsTenantAdmin]
```

**Efecto:**
- ✅ Cualquier usuario autenticado puede leer (GET)
- ✅ Solo admins pueden crear/actualizar/eliminar (POST/PATCH/DELETE)

### 11.4 Autenticación

**Tipo:** `SessionAuthentication`

**Compatibilidad:**
- ✅ Cookies de sesión (compatible con workspace)
- ✅ No requiere tokens JWT
- ✅ Funciona con formularios HTML

### 11.5 Seguridad de Datos

**Multi-tenancy:**
- ✅ Aislamiento por esquema (django-tenants)
- ✅ No es posible acceder a datos de otros tenants
- ✅ Transparente para el código (no necesita filtrar por tenant_id)

**Singleton:**
- ✅ Constraint DB garantiza una sola empresa por tenant
- ✅ No es posible crear múltiples empresas en el mismo tenant

**Credenciales de Correo:**
- ⚠️ **TODO**: Cifrar `password` en `MailInboxConfig` (actualmente sin cifrar)

---

## 12. Comandos de Gestión

### 12.1 `audit_empresa_nit`

**Ubicación:** `apps/tenant/empresa/management/commands/audit_empresa_nit.py`

**Propósito:** Lista tenants sin Empresa o sin NIT

**Uso:**
```bash
# Todos los tenants
python manage.py all_tenants_command audit_empresa_nit

# Tenant específico
python manage.py tenant_command audit_empresa_nit --schema=tenant1
```

**Salida:**
```
[tenant1] OK: NIT=901123299
[tenant2] SIN Empresa
[tenant3] Empresa SIN NIT (razon_social: Mi Empresa)
```

### 12.2 `audit_empresa_app`

**Ubicación:** `apps/tenant/empresa/management/commands/audit_empresa_app.py`

**Propósito:** Auditoría completa de la app (modelos, servicios, APIs, persistencia)

**Uso:**
```bash
# Todos los tenants
python manage.py all_tenants_command audit_empresa_app

# Tenant específico con verbose
python manage.py tenant_command audit_empresa_app --schema=tenant1 --verbose
```

**Verifica:**
- ✅ Modelos y campos
- ✅ Servicios (SSoT Provider)
- ✅ APIs (ViewSet, Serializer, Router)
- ✅ Persistencia en BD
- ✅ CRUD básico
- ✅ Integración SSoT

---

## 13. Tests y Calidad

### 13.1 Tests Existentes

**Ubicación:** `apps/tenant/empresa/tests/`

#### 13.1.1 `test_api_empresa.py`

**Tests de APIs:**
- Test de listado (singleton)
- Test de creación
- Test de actualización
- Test de permisos

#### 13.1.2 `test_templates.py`

**Tests de templates:**
- Test de renderizado de templates
- Test de partials

### 13.2 Cobertura Recomendada

**Pendiente de implementar:**
- ✅ Tests unitarios de Service Layer
- ✅ Tests de integración SSoT con facturas
- ✅ Tests de validaciones
- ✅ Tests de permisos
- ✅ Tests de multi-tenancy

---

## 14. Diagramas de Flujo

### 14.1 Flujo Completo: Crear → Consumir → Actualizar

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO COMPLETO                            │
└─────────────────────────────────────────────────────────────┘

1. CREAR EMPRESA
   Usuario → Workspace → Core API → impl.get_or_create_empresa()
   → models.Empresa.create() → PostgreSQL

2. CONSUMIR SSoT (Facturas)
   facturas/services.py → get_empresa_emisor_data()
   → models.Empresa.objects.first() → Retorna NIT
   → _determinar_naturaleza() → VENTA/COMPRA

3. ACTUALIZAR EMPRESA
   Usuario → Workspace → Core API → impl.update_empresa()
   → Validaciones → models.Empresa.save() → PostgreSQL
```

### 14.2 Flujo de Importación de Factura con SSoT

```
┌─────────────────────────────────────────────────────────────┐
│         IMPORTACIÓN DE FACTURA (Con SSoT)                   │
└─────────────────────────────────────────────────────────────┘

1. Usuario sube XML en workspace/#facturas
2. facturas/api/viewsets.py → upload_ubl()
3. facturas/services.py → importar_ubl()
4. facturas/services.py → get_empresa_emisor_data()
   ├─ Si existe → Retorna NIT
   └─ Si no existe → Lanza EmpresaNotConfiguredError → 422
5. facturas/services.py → _determinar_naturaleza()
   ├─ emisor_nit == empresa_nit → VENTA
   └─ emisor_nit != empresa_nit → COMPRA
6. Persiste factura con naturaleza calculada
7. Retorna 201 Created
```

---

## 15. Conclusiones y Recomendaciones

### 15.1 Estado Actual

**✅ FUNCIONAL Y OPERATIVO**

La app `empresa` está completamente funcional y correctamente implementada:

- ✅ Modelos correctamente definidos con singleton
- ✅ Service Layer completo y funcional
- ✅ APIs REST completas (CRUD)
- ✅ Integración SSoT funcionando
- ✅ Workspace integrado
- ✅ Comandos de auditoría disponibles

### 15.2 Fortalezas

1. **Arquitectura sólida:**
   - Service Layer bien definido
   - Separación de responsabilidades clara
   - API-First implementado correctamente

2. **SSoT bien implementado:**
   - `get_empresa_emisor_data()` funciona correctamente
   - Integración con facturas operativa
   - No hay duplicación de datos

3. **Multi-tenancy robusto:**
   - Aislamiento por esquema funcionando
   - Singleton garantizado por constraint DB
   - Transparente para el código

4. **Optimización:**
   - Querysets optimizados con `only()`
   - Validaciones eficientes
   - Logging adecuado

### 15.3 Áreas de Mejora

1. **Seguridad:**
   - ⚠️ **TODO**: Cifrar `password` en `MailInboxConfig`
   - Considerar usar `django-encrypted-model-fields`

2. **Tests:**
   - ⚠️ **TODO**: Aumentar cobertura de tests
   - Tests unitarios de Service Layer
   - Tests de integración SSoT

3. **Documentación:**
   - ✅ Este informe completo
   - Considerar diagramas visuales adicionales

### 15.4 Recomendaciones

1. **Corto Plazo:**
   - Implementar cifrado de passwords en `MailInboxConfig`
   - Aumentar cobertura de tests
   - Documentar casos de uso adicionales

2. **Mediano Plazo:**
   - Considerar cache para `get_empresa_emisor_data()` si hay muchos accesos
   - Implementar versionado de API si hay cambios mayores
   - Considerar auditoría de cambios (django-auditlog)

3. **Largo Plazo:**
   - Evaluar migración a GraphQL si el sistema crece
   - Considerar eventos/notificaciones cuando cambia la empresa
   - Evaluar integración con servicios externos (DIAN, RUT)

---

## 16. Referencias y Enlaces

### 16.1 Documentación Interna

- `apps/tenant/empresa/AUDITORIA.md` - Auditoría de la app
- `documentacion/arquitectura_general.md` - Arquitectura general del sistema
- `documentacion/CORRECCION_IMPORT_EMPRESA.md` - Corrección de import SSoT

### 16.2 Archivos Clave

- **Modelos:** `apps/tenant/empresa/models.py`
- **SSoT Provider:** `apps/tenant/empresa/services.py`
- **Service Layer:** `apps/tenant/empresa/impl/empresa_service.py`
- **APIs:** `apps/tenant/empresa/api/viewsets.py`
- **Serializers:** `apps/tenant/empresa/api/serializers.py`
- **Workspace:** `apps/tenant/core/templates/tenant/core/workspace.html:108`

### 16.3 Endpoints Principales

- `GET /api/v1/empresas/` - Lista empresa (singleton)
- `GET /api/v1/empresas/mi-empresa/` - Endpoint de conveniencia
- `POST /api/v1/empresas/` - Crea empresa
- `PATCH /api/v1/empresas/{id}/` - Actualiza empresa
- `GET /api/v1/core/empresa/` - Core API (workspace)
- `PATCH /api/v1/core/empresa/` - Core API update (workspace)

---

## 17. Apéndices

### 17.1 Ejemplo de Payload JSON

**GET /api/v1/empresas/mi-empresa/**

```json
{
  "id": 1,
  "razon_social": "SINTEL TECNOLOGY SAS",
  "nit": "901123299",
  "dv": "1",
  "direccion": "Calle 123 #45-67",
  "telefono": "+57 300 123 4567",
  "email_contacto": "contacto@sintel.com",
  "tipo_contribuyente_clase": "PJ",
  "tipo_contribuyente_segmento": "GRAN_CONTRIBUYENTE",
  "regimen_renta_codigo": "ORDINARIO",
  "responsabilidades_rut_codigos": ["48", "52"],
  "actividad_economica": "6201",
  "regimen_tributario": "Ordinario",
  "logo": "https://home.sintel.com/media/logos/logo.png",
  "website": "https://www.sintel.com",
  "moneda": "COP",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### 17.2 Ejemplo de Error 422 (Sin Empresa)

**POST /api/v1/facturas/upload-ubl/**

```json
{
  "error": "empresa_no_configurada",
  "message": "Empresa no configurada en el tenant: cree la Empresa y asigne NIT."
}
```

### 17.3 Ejemplo de Uso de SSoT

```python
from apps.tenant.empresa.services import get_empresa_emisor_data, EmpresaNotConfiguredError

try:
    empresa = get_empresa_emisor_data()
    print(f"NIT: {empresa['nit']}")
    print(f"Razón Social: {empresa['razon_social']}")
except EmpresaNotConfiguredError as e:
    print(f"Error: {e}")
    # Retornar 422 o mostrar mensaje al usuario
```

---

**Fin del Informe**

*Este documento fue generado automáticamente basado en el estado actual del código (2025-01-XX).*
