# Arquitectura General — SINTEL ERP

**Version:** 3.20.0
**Ultima actualizacion:** 2026-08-09 (DOC-M7) — cierre de FASE 13 (Knowledge Graph Organizacional) + FASE 14 (Gobernanza Automatica), alcance real documentado en `documentacion/F13_F14_FINAL_REPORT.md` (no el 100% del espec original — reduccion de alcance explicita, no oculta). Se construyo `tools/organizational_governance/` (paquete nuevo, independiente de `tools/ekg/` por decision documentada — ver `documentacion/F13_0_EKG_AUDIT.md`): un grafo real (165 entidades, 220 relaciones, extraidas por AST de las 17 apps tenant) mas un motor de gobernanza con 8 reglas implementadas y probadas (23/23 tests). Ejecucion real contra el codigo actual: **0 findings, FINAL STATUS: PASS** — consistente con que FASE 7 de la consolidacion OCF/OSF ya habia corregido los 2 bugs reales que 2 de esas 8 reglas (`SEC-002`/`SEC-003`) fueron disenadas para detectar. Comando: `python -m tools.organizational_governance.cli --report`. Detalle completo, incluyendo las ~27 reglas nombradas en el pedido original que NO se implementaron (con la razon de cada una) en `documentacion/F13_F14_EXECUTION_STATUS.md`.
**Actualizacion previa:** 2026-08-09 (DOC-M6) — sincronizacion tras cerrar el plan de consolidacion OCF/OSF completo (FASE 0-12, ver `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`). Trabajo de OCF/OSF commiteado (5 commits, `0295932`..`34fc020`); 2 bugs reales encontrados y corregidos (bypass de `HasOrganizationalScope` en HTMX; `PermissionDenied`->500 en vez de 403); ADR-004 con adenda, ADR-005 nuevo.
**Actualizacion previa:** 2026-08-09 (DOC-M5) — pasada de validacion completa contra codigo real (conteo directo de apps/migraciones/modelos/tests/endpoints/namespaces JS) que corrigio numeros internamente contradictorios en §2.2/§9/§12 y establecio el estado real de OCF/OSF contra codigo (agente de investigacion dedicado). Detalle completo en el historial de este documento.
**Fuente canonica:** `documentacion/arquitectura_general.md`
**Reglas de desarrollo:** `AGENTS.md` (raiz del proyecto)
**Estado actual del proyecto:** `MEMORY.md` (raiz del proyecto)
**Modo de Proyecto:** EN DESARROLLO (Development Mode)

> Antes de modificar cualquier app, leer `AGENTS.md` completo y el documento `.agent/AUDITORIA_FLUJO_*.md` de esa app. Este documento describe la infraestructura global, no la logica interna de cada app.

---

## 1. Vision y Core Tecnologico del Proyecto

SINTEL es un ERP SaaS multi-tenant para gestion contable y facturacion electronica en Colombia. Cada empresa (tenant) opera en un esquema PostgreSQL aislado, compartiendo la misma infraestructura de servidores. El sistema implementa Feature-Sliced Design (FSD) con Service Layer estricto, autenticacion Dual-Auth (JWT + Session) y frontend sin build step.

**Dominio de negocio principal:** facturacion electronica DIAN (XML, envio, estados), contabilidad NIIF PYMES, nomina colombiana, inventario con Kardex, gastos operativos, cotizaciones comerciales, proyectos, CRM basico y dashboard ejecutivo.

### 1.1. Stack Backend

| Tecnologia | Version | Rol |
|---|---|---|
| Python | 3.12 | Lenguaje principal |
| Django | 5.0–5.1 | Framework web |
| Django REST Framework | 3.16–3.17 | APIs JSON (ViewSets, Serializers, Routers) |
| django-tenants | 3.9–3.10 | Aislamiento multi-tenant por esquemas PostgreSQL |
| PostgreSQL | 15+ | Base de datos relacional |
| Celery | 5.3–6.0 | Tareas asincronas y procesamiento en segundo plano |
| Redis | 5.0–6.0 | Broker de Celery y cache |
| WhiteNoise | 6.x | Servicio de archivos estaticos en produccion |
| djangorestframework-simplejwt | 5.3–6.0 | Tokens JWT (access 15 min, refresh 7 dias, HS256) |
| anthropic | 0.40–1.0 | SDK para agentes IA especializados (Asistente Contable) |
| drf-spectacular | 0.29–0.30 | Generacion de schema OpenAPI |
| django-filter | 25.1+ | Filtros query para APIs |
| djangorestframework-mcp | — | **[DOC-M5, nuevo, no documentado antes]** Expone ViewSets decorados con `@mcp_viewset()` como herramientas MCP en `/mcp/` (`config/settings.py:73,105`; montado en `config/urls_public.py:117` y `config/urls_tenant.py:166`). Compatible con `mcp-remote` (STDIO transport). |
| django-cors-headers | — | **[DOC-M5, nuevo]** CORS para subdominios dinamicos de `sintel.net.co` (`config/settings.py`, `SHARED_APPS`) |
| psycopg (binary) | 3.1–4.0 | Adaptador PostgreSQL (psycopg3) |
| pandas | 2.0–3.0 | Procesamiento ETL y datos masivos |
| lxml | 5.2.1 | Parsing XML/HTML (facturas electronicas DIAN) |
| Pillow | 10.3.0 | Procesamiento de imagenes |

### 1.2. Stack Frontend

| Tecnologia | Version | Rol |
|---|---|---|
| HTMX | 1.9.10 | Server-driven UI, carga dinamica de fragmentos HTML |
| Bootstrap | 5.3.2 | Sistema de diseno UI, Offcanvas para modales laterales |
| django-tables2 | 2.7.x | **Patron actual para grillas nuevas** — tablas server-rendered + HTMX, reemplaza Tabulator progresivamente (ver §4.6) |
| Tabulator | 6.2.5 | Grillas de datos reactivas con paginacion remota client-side — **en migracion, no usar en modulos nuevos** (ver §4.6) |
| Vanilla JS ES6+ | — | Modulos por namespace `window.Sintel.<App>` |
| Bootstrap Icons + Font Awesome | — | Iconografia |

**No hay build step.** Todas las librerias se cargan via CDN. No existe Webpack, Vite ni compilacion de frontend. Alpine.js esta disponible via CDN pero no es parte del estandar aprobado.

**Migracion de grillas (Tabulator → django-tables2+HTMX), estado real verificado 2026-08-07:** 13 de ~17 apps tenant ya tienen `tables.py` (`bancos`, `clientes`, `compras`, `contabilidad`, `empleados`, `empresa`, `facturas`, `gastos`, `inventario`, `perfil`, `proveedores`, `proyectos`, `ventas`). Solo `cotizaciones` y `dashboard` siguen exclusivamente en Tabulator. Varias apps con `tables.py` conservan Tabulator vivo en vistas puntuales no migradas (`contabilidad`: `pendiente_list.js`/`libro_diario_list.js`/reportes; `inventario`: 6 sitios; `clientes`: `clientes.cartera.js`; `ventas`: `resolucion_list.js`) — coexistencia deliberada, no regresion. Ver nota DOC-M4 en §4.6 para el detalle completo y la discrepancia encontrada con el estado que describia `MEMORY.md` antes de esta validacion.

### 1.3. Infraestructura

| Componente | Tecnologia |
|---|---|
| Contenedores | Docker + Docker Compose |
| Servidor WSGI | Gunicorn (produccion) / `runserver` (desarrollo, ver `docker-compose.yaml`) |
| Proxy inverso | Nginx — sirve `/static/` y `/media/` directamente desde `/app/staticfiles`, `/app/media` (bind mount de solo lectura) y reenvia todo lo demas a `web:8000` |
| DNS interno | Windows Server 2022 wildcard `*.sintel.net.co → 192.168.2.15` |
| Autenticacion asimetrica | HS256 JWT via variable de entorno `JWT_SECRET_KEY` |

**Politica de cache de estaticos (Nginx), fijada 2026-08-06:** `/static/` usa `Cache-Control: "no-cache, public, no-transform"` (revalidacion condicional obligatoria via ETag/Last-Modified, sin `expires`) — **no** `expires 30d` como `/media/`. Un `expires 30d` sobre `/static/` estuvo vigente hasta el hallazgo C4/C7 de la Auditoria Enterprise 2026-08-06: cualquier fix de JS/CSS quedaba invisible para navegadores que ya hubieran cargado el archivo anterior, durante 30 dias, sin importar cuantos reinicios del contenedor `web` se hicieran. `nginx.conf` se hornea en la imagen en build-time (no es un volumen montado) — un cambio ahi requiere `docker compose build nginx && docker compose up -d nginx`, no solo un restart.

### 1.4. Directorio `config/` — Nucleo de Configuracion

El directorio `config/` es el nucleo de configuracion del proyecto. Toda la orquestacion de URLs, settings y tareas asincronas pasa por aqui.

| Archivo | Responsabilidad |
|---|---|
| `settings.py` | SSoT de toda la configuracion Django (SHARED_APPS, TENANT_APPS, JWT, Celery, etc.) — 911 lineas |
| `urls_public.py` | ROOT_URLCONF — dominio admin mapea al esquema public |
| `urls_tenant.py` | TENANT_URLCONF — subdominios mapean al esquema tenant |
| `api_urls.py` | SSoT de TODAS las rutas API REST (`/api/v1/...`). Registros resilientes con try/except por app |
| `public_api_urls.py` | Rutas API del esquema publico |
| `celery.py` | Configuracion Celery + autodiscovery de tasks |
| `well_known.py` | Endpoints `.well-known` (DIAN, OAuth) |

### 1.5. Resolucion de Tenant por Hostname

```
request → TenantMiddleware → hostname match → set schema PostgreSQL

admin.sintel.net.co   →  public schema    →  urls_public.py
empresa.sintel.net.co →  tenant schema    →  urls_tenant.py
192.168.2.15       →  public (fallback) →  soporte IP en DEBUG
```

---

## 2. Inventario de Apps

### 2.1. Esquema Public (`SHARED_APPS`) — 5 apps activas

| App | App Label | Modelos | Migraciones | Responsabilidad |
|---|---|---|---|---|
| `apps/public/accounts/` | `accounts` | User, DeletionAudit | 2 | Modelo `User` global (AbstractUser), gestion de usuarios |
| `apps/public/tenants/` | `tenants` | Client, Domain, TenantMembership, FailedTenantTask | 2 | Registro de tenants, dominios, invitaciones OTT |
| `apps/public/impuestos/` | `impuestos` | TipoImpuesto, TarifaIVA, ConceptoRetencion, CodigoTributario, ActividadEconomica, DocumentoFuente, IngestaLog, NormaTributaria, ContribuyenteTipo, RegimenRenta, ResponsabilidadRUT, PerfilTributario | 1 | Catalogo DIAN, tarifas, normativas tributarias |
| `apps/public/console/` | `console` | ConsoleActionLog | 4 | Consola admin: crear tenants, gestionar membresias, JWT bridge |
| `apps/public/core/` | `core` (public) | (sin modelos) | — | Middleware de resolucion de tenant, infraestructura compartida |

**Total public models: 19** — **[DOC-M5, corregido]** recuento anterior (17) subestimaba `impuestos` (12 modelos reales, no 11). Total migraciones public: 2+2+1+4 = **9** (antes: 8; `console` paso de 3 a 4 migraciones).

### 2.2. Esquema Tenant (`TENANT_APPS`) — 17 apps registradas, 15 con modelos de negocio

**[DOC-M5, corregido 2026-08-09]** `TENANT_APPS` (`config/settings.py`) tiene 17 entradas `apps.tenant.*`. Este documento tenia tres numeros distintos y mutuamente contradictorios para "apps de negocio" (14 en este encabezado, 16 filas en la tabla, 13 en la tabla de metricas §12) — ninguno era correcto. El numero real: **15 apps con modelos de negocio concretos** (todas las filas de abajo excepto `core`, que solo aporta las clases base abstractas) + `core` + `landing` (sin `models.py`, ver §2.3) = 17 apps registradas.

| App | App Label | Modelos | Migraciones | Responsabilidad |
|---|---|---|---|---|
| `apps/tenant/core/` | `core` | SintelTenantBaseModel, SedeAwareModel (ambas abstractas) | 0 | UI Shell, bridge cross-schema, onboarding, auth JWT |
| `apps/tenant/empresa/` | `empresa` | Empresa, MailInboxConfig, Sede, Area | 9 | Datos fiscales, logo, sedes y areas del tenant |
| `apps/tenant/perfil/` | `perfil` | Departamento, TenantProfile (+ RolTenant, AlcanceOrganizacional como `TextChoices`, no modelos) | 8 | Roles y perfiles de usuario dentro del tenant |
| `apps/tenant/facturas/` | `facturas` | Factura, ItemFactura, NotaCredito, MailIngestionRun, MailInboxState, FacturaAnexos, FacturaImpuesto | 30 | Facturacion electronica DIAN (XML, envio, estados) |
| `apps/tenant/contabilidad/` | `contabilidad` | CatalogoMaestroNIIF, CuentaContable, TipoComprobante, AsientoContable, MovimientoContable, PeriodoContable, ReglaContable, TarifaImpuesto, ConfiguracionRetenciones, Retencion, PlantillaContable, LineaPlantilla, ImpuestoDocumento | 16 | PUC NIIF, asientos, extractores Pull, agente IA, Motor de Plantillas |
| `apps/tenant/gastos/` | `gastos` | ResolucionDIAN, DocumentoSoporte | 22 | Gastos operativos, documentos soporte, retenciones |
| `apps/tenant/inventario/` | `inventario` | CategoriaItem, Producto, Servicio, ActivoFijo, MovimientoInventario, HistorialServicio (+ TimeStampedModel abstract) | 10 | Productos, servicios, activos fijos, Kardex unificado |
| `apps/tenant/empleados/` | `empleados` | Empleado, Contrato, Devengo, ResolucionDIAN, TransmisionNominaDIAN, LiquidacionPrestacion | 13 | Nomina colombiana, devengos, contratos, liquidaciones |
| `apps/tenant/cotizaciones/` | `cotizaciones` | Cotizacion, CotizacionItem (+ Producto y Servicio propios) | 5 | Cotizaciones comerciales, vinculacion con facturas |
| `apps/tenant/clientes/` | `clientes` | Cliente, ContactoCliente, Cartera | 8 | CRM basico, terceros clientes, cartera, retenciones |
| `apps/tenant/proveedores/` | `proveedores` | Proveedor, CuentasPagar, Representante | 18 | Terceros proveedores, cartera unificada, documentos soporte |
| `apps/tenant/proyectos/` | `proyectos` | Proyecto, AsignacionPersonal, PedidoProyecto, ItemPedido, ItemPresupuestoProyecto, TareaCorta, TareaDiariaProyecto | 20 | Gestion de proyectos, presupuesto, tareas cortas |
| `apps/tenant/dashboard/` | `dashboard` | SnapshotMetricaDiaria | 3 | Dashboard ejecutivo, metricas consolidadas |
| `apps/tenant/bancos/` | `bancos` | CuentaBancaria, ExtractoBancario, TransaccionBancaria | 5 | Estados de cuenta bancarios, conciliacion manual via UUID soft-references |
| `apps/tenant/compras/` | `compras` | PlantillaOrdenCompra, OrdenCompra (hereda `SedeAwareModel`, ver §3.2/ADR-003), ItemOrdenCompra | 7 | Ordenes de compra a proveedores (agregada 2026-06-17, ver `.agent/AUDITORIA_FLUJO_COMPRAS.md`) |
| `apps/tenant/ventas/` | `ventas` | ResolucionFacturacion, Venta, ItemVenta | 3 | Ordenes de venta y su puente hacia `facturas` (agregada 2026-06-17, ver `.agent/ARQUITECTURA_VENTAS.md`) |

**Nota (`ResolucionDIAN` duplicado):** `gastos` y `empleados` tienen cada una su propia clase `ResolucionDIAN` — son dos modelos distintos, no un bug de referencia cruzada (hallazgo confirmado durante la auditoria EKG 2026-08-07, ver `documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md` §4.1).

**Total tenant models: 67 concretos + 3 abstractos** (`SintelTenantBaseModel`, `SedeAwareModel`, `TimeStampedModel`) — **[DOC-M5, corregido, conteo real 2026-08-09 via `grep '^class .*(Model|Base)'` por app]**, reemplaza el "52 + 1 abstract" que este documento reportaba antes (desactualizado por las migraciones nuevas de contabilidad/proveedores/clientes/empleados/facturas listadas arriba, la mayoria sin commitear aun — ver advertencia general al inicio del documento).
**Total migraciones: 177 (tenant) + 9 (public) = 186 total** — **[DOC-M5, corregido]** conteo directo de archivos `NNNN_*.py` en cada carpeta `migrations/`, reemplaza el "133" que este documento reportaba antes.

### 2.3. Apps de Infraestructura Tenant (sin modelos de negocio)

**[DOC-M5, corregido 2026-08-09]** Esta tabla listaba `apps/tenant/mail/` y `apps/tenant/mailinbox/`, que **no existen como directorios** en el repositorio actual (verificado, `ls apps/tenant/`) y nunca estuvieron en `TENANT_APPS`. Los modelos de correo viven hoy dentro de `facturas` (`MailIngestionRun`, `MailInboxState`) y `empresa` (`MailInboxConfig`) — ver tabla de §2.2. `apps/tenant/api/` tampoco es una app Django registrada (no tiene `apps.py` ni aparece en `TENANT_APPS`) — es una carpeta de codigo compartido (permisos DRF centrales, `BaseTenantViewSet`), no una "app de infraestructura" en el sentido de django-tenants.

| App | Registrada en `TENANT_APPS` | Responsabilidad |
|---|---|---|
| `apps/tenant/landing/` | Si | Pagina publica estatica del tenant — sin `models.py` |
| `apps/tenant/api/` | No (carpeta de codigo compartido) | `BaseTenantViewSet`, `BaseServiceMixin`, permisos DRF centrales |

---

## 3. Capa de Datos e Infraestructura Multi-Tenant (Zero-Trust)

### 3.1. Division de Esquemas PostgreSQL

| Esquema | Apps | Contenido |
|---|---|---|
| `public` | `SHARED_APPS` | Usuarios globales (`accounts.User`), registro de tenants (`tenants.Client`), catalogo DIAN (`impuestos`), consola admin (`console`) |
| Tenant (uno por empresa) | `TENANT_APPS` | Todos los datos de negocio del tenant: facturas, contabilidad, empleados, inventario, etc. |

Los esquemas tenant estan completamente aislados a nivel de base de datos. Una consulta en el esquema de "Empresa A" nunca puede acceder a los datos de "Empresa B" por disenio del ORM.

### 3.2. Modelo Base Obligatorio — `SintelTenantBaseModel`

**SSoT:** `apps/tenant/core/models.py`

Todos los modelos del esquema tenant heredan de `SintelTenantBaseModel`, nunca de `models.Model`. Este modelo base inyecta automaticamente:

| Campo | Tipo | Detalle |
|---|---|---|
| `empresa` | `ForeignKey('empresa.Empresa', PROTECT)` | Clave de particion — filtra al tenant actual |
| `created_at` | `DateTimeField(auto_now_add=True)` | Timestamp de creacion, indexado |
| `updated_at` | `DateTimeField(auto_now=True)` | Timestamp de ultima modificacion, indexado |

**Indices declarados en `SintelTenantBaseModel.Meta`:** `[empresa]` y `[empresa, -created_at]`. **Correccion (2026-08-07, verificado durante ADR-003):** Django NO fusiona estos indices con el `Meta.indexes` propio de un modelo concreto cuando este ultimo declara el suyo — verificado empiricamente (`Model._meta.indexes`) en `OrdenCompra` y `PlantillaOrdenCompra`, ninguno de los dos hereda estos dos indices pese a heredar el campo `empresa`. Cualquier modelo que declare su propio `Meta.indexes` debe repetirlos explicitamente ahi si los necesita.

**Proteccion en `save()`:** el modelo base lanza `ValueError` si `empresa_id` es `None`, evitando registros huerfanos por error de programacion.

**Extension opcional — `SedeAwareModel` (ADR-003, `docs/ADR-003-contexto-organizacional-sede-area.md`):** mixin abstracto que hereda de `SintelTenantBaseModel` y agrega `sede`/`area` (Contexto Organizacional Empresa->Sede->Area). Opt-in, no reemplaza `SintelTenantBaseModel` — piloto unico hoy: `apps/tenant/compras/models.py:OrdenCompra`.

### 3.3. Regla Zero-Trust de Consultas

Toda consulta ORM en apps tenant debe filtrar por `empresa_id`. Las siguientes practicas estan prohibidas:

- Usar `.all()` sin filtro de empresa
- Usar `.filter()` sin encadenar `.only()` o `.defer()`
- Acceder a `obj.fk.campo` sin `select_related()` previo (problema N+1)

**Patron obligatorio en ViewSets:**

```
queryset = Model.objects.none()   # nivel de clase
get_queryset() → .filter(empresa_id=...).only(campos).select_related(...)
```

### 3.4. UUID como Lookup Field

`BaseTenantViewSet` (`apps/tenant/api/base.py`) define `lookup_field = "uuid"`. Todos los ViewSets tenant heredan este valor. Las PKs enteras nunca se exponen en URLs publicas de la API.

### 3.5. Seguridad y Autenticacion (Dual-Auth)

**SSoT de autenticacion:** `BaseTenantViewSet` en `apps/tenant/api/base.py`.

`authentication_classes = [JWTAuthentication, SessionAuthentication]` — heredado por todos los ViewSets. Prohibido sobrescribir en ViewSets hijos.

DRF evalua JWT primero (header `Authorization: Bearer`). Si falla, usa Session (cookie). Esto permite que el mismo endpoint sirva a clientes API y al workspace del navegador.

**Bridge Session → JWT:** `GET /api/v1/core/auth/from-session/`

**Endpoints de token:**

| Endpoint | Metodo | Accion |
|---|---|---|
| `/api/token/` | POST | Obtener par access/refresh |
| `/api/token/refresh/` | POST | Renovar access token |
| `/api/token/verify/` | POST | Verificar validez de token |

**Parametros JWT (`config/settings.py`):** access 15 min, refresh 7 dias, ROTATE=True, BLACKLIST=True, algoritmo HS256.

### 3.6. Roles y Permisos

**SSoT de roles:** `TenantProfile.rol` en `apps/tenant/perfil/models.py`

| Rol | Capacidades |
|---|---|
| `ADMIN` | CRUD completo, asignar roles, configuracion de empresa |
| `OPERADOR` | Lectura + escritura segun app |
| `VISOR` | Solo lectura |

**SSoT de permisos:** `apps/tenant/api/permissions.py` — unica fuente para importar permisos en todo el proyecto.

| Permiso | Descripcion |
|---|---|
| `IsTenantMember` | Verifica membresia activa en el tenant. Obligatorio en todo ViewSet |
| `IsTenantAdminOrReadOnly` | Lectura para autenticados; escritura solo para ADMIN |
| `IsTenantProfileOperadorOrAdmin` | Requiere ADMIN u OPERADOR |
| `HasTenantRole` | Generico — el ViewSet declara `required_roles` |

**Auto-creacion de perfil:** al hacer login, si el usuario no tiene `TenantProfile` en el tenant actual, se crea automaticamente con rol `VISOR`.

**Alcance organizacional (ADR-003, 2026-08-07 — fundamentos + piloto `compras`, ver
`docs/ADR-003-contexto-organizacional-sede-area.md`):** `TenantProfile.alcance`
(`EMPRESA`/`SEDE`/`AREA`, default `EMPRESA`) es un campo nuevo, **ortogonal** a `rol` — no lo
reemplaza. Un perfil con `alcance=SEDE`/`AREA` solo puede operar sobre sus `sedes_asignadas`/
`areas_asignadas`. "ADMIN GLOBAL" no es un valor de `alcance`: es el
staff/superuser de Django del esquema publico, fuera de `TenantProfile`.

**[DOC-M6, 2026-08-09 — distinguir dos mecanismos que no son lo mismo, ya commiteados]** Tras
ADR-003 (piloto `compras`), el proyecto interno Organizational Context/Scope Framework (OCF/OSF —
ADR-004 y **ADR-005**, ver §7) extendio el *filtrado* por alcance a mas apps, pero **no** de la
misma forma que el piloto original — distincion verificada y consolidada tras el plan de FASE 0-12
de `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`:
- La clase de permiso `HasOrganizationalScope` (`apps/tenant/api/permissions.py`) sigue aplicada
  **solo** a `OrdenCompraViewSet` y a `apps/tenant/core/api/contexto.py` — rollout deliberadamente
  no extendido a las demas apps hasta resolver una asimetria real encontrada durante la
  consolidacion: `HasOrganizationalScope` deniega objetos con `sede_id=None`, mientras que el
  filtrado de listas de las 6 apps de abajo trata esos mismos registros como visibles (100% de los
  historicos de esas apps tienen `sede=NULL`) — ver `documentacion/OSF_TECHNICAL_AUDIT.md` §4.
- `SedeAwareModel` (el mixin de modelo) tambien sigue heredado **solo** por `OrdenCompra`
  (`apps/tenant/compras/models.py`) — decision confirmada, no pendiente: el rollout a las demas
  apps usa un patron mas liviano (siguiente punto) en vez de migracion de esquema, ver ADR-005.
- Lo que si se extendio: **filtrado consciente de alcance a nivel de selector/business-service**
  (`OrganizationalScope.filter()` / `filter_by_scope()` / `filter_by_scope_null_safe()`, en
  `apps/tenant/core/services/organizational_scope.py` y `organizational_filters.py`) — presente en
  `compras`, `cotizaciones`, `empleados`, `facturas`, `gastos`, `inventario`, `proyectos`. `ventas`
  usa el mecanismo hermano `OrganizationalContext.resolve()` (no `OrganizationalScope`) para
  defaultear la `sede` de la `Factura` que genera, nunca desde el payload del cliente — ver
  `documentacion/VENTAS_FACTURAS_AUDIT.md`.
- **Dos bugs reales de aislamiento encontrados y corregidos durante la consolidacion** (FASE 7):
  las acciones HTMX `render_offcanvas_detalle`/`render_offcanvas_editar` de `compras`
  (`apps/tenant/compras/api/viewsets.py`) resolvian el objeto con `get_object_or_404()` en vez de
  `self.get_object()`, bypaseando `HasOrganizationalScope` por completo — corregido agregando
  `self.check_object_permissions(request, instance)` explicito. Y `BaseServiceMixin.
  handle_service_error()` (`apps/tenant/api/mixins.py`, compartido por **todo** el proyecto, no
  solo `compras`) no tenia un caso para `rest_framework.exceptions.PermissionDenied` y devolvia
  `500` en vez de `403` cuando `HasOrganizationalScope` denegaba un `update()`/`destroy()` — la
  escritura ya estaba bloqueada en ambos casos (no era una fuga de seguridad), pero el codigo de
  estado era incorrecto. Ambos corregidos, verificados con 20/20 tests reales pasando
  (`documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md`).
- Estos modulos `organizational_*.py` de `apps/tenant/core/services/`, junto con el resto del
  trabajo de OCF/OSF (modelos, migraciones, tests, los 2 fixes de arriba), **ya estan commiteados**
  — 5 commits (`0295932` OCF core, `120d17e` piloto compras, `c63b35e` scope en 6 apps, `1d19d8f`
  tests, `34fc020` ADRs/documentacion), verificado con `git log`. Detalle completo en
  `documentacion/FASE11_CONSOLIDACION_GIT.md`.

**Frontend JWT:**

```javascript
// CORRECTO:
const token = window.jwtAuth?.getAccessToken?.();

// PROHIBIDO — la propiedad .token no existe:
window.jwtAuth.token
```

---

## 4. Patron de Arquitectura del Backend (Service Layer Unificada)

### 4.1. Feature-Sliced Design (FSD) — Un Ecosistema por Modelo

Cada app tenant implementa un ecosistema completo e independiente por modelo de dominio.

```
apps/tenant/<app>/
  models.py
  services/
    __init__.py          — Re-exporta clases principales (imports explicitos, sin wildcards)
    crud_service.py      — SOLO persistencia DB (@transaction.atomic)
    business_service.py  — Reglas de negocio + Double Semantic Verification (IDOR)
    selectors.py         — QuerySets read-only con .only(), LIST_FIELDS/DETAIL_FIELDS
    api_mixins.py        — <Modelo>ServiceMixin inyectado en ViewSet (hereda BaseServiceMixin)
    services.py          — Facade estable (re-exporta desde business_service)
  api/
    viewsets.py          — Hereda BaseTenantViewSet + ServiceMixin
    serializers.py
    urls.py
  templates/tenant/<app>/
    offcanvas_crear_<modelo>.html
    offcanvas_editar_<modelo>.html
    offcanvas_detalle_<modelo>.html
    list_<modelo>.html
    partials/
  static/<app>/js/
    <app>.api.js                   — SSoT de todas las URLs de endpoint
    features/
      <modelo>_list.js             — Grilla Tabulator
      <modelo>_editor.js           — Formularios Offcanvas
  .agent/
    AUDITORIA_FLUJO_*.md           — Flujo especifico de la app (leer antes de modificar)
    docs/
    skills/
```

### 4.2. Flujo Unidireccional (Obligatorio)

```
ViewSet → ServiceMixin → BusinessService (DSV + reglas) → CRUDService (DB) → Response JSON / HTMX OOB
```

El ViewSet es un enrutador HTTP puro. Toda logica de negocio vive en el Service Layer. Los modelos no contienen logica de negocio. Los Serializers solo realizan validacion sintactica y de tipos.

### 4.3. Responsabilidades por Capa

| Capa | Archivo | Responsabilidad |
|---|---|---|
| ViewSet | `api/viewsets.py` | Ingesta HTTP, delegacion a ServiceMixin, respuesta |
| Serializer | `api/serializers.py` | Validacion sintactica y de tipos, serializacion de salida |
| ServiceMixin | `services/api_mixins.py` | Inyecta `get_qs_list()`, `get_qs_detail()`, `service_crear_*()`. Hereda `BaseServiceMixin` |
| BusinessService | `services/business_service.py` | DSV, reglas de dominio, calculos, idempotencia |
| CRUDService | `services/crud_service.py` | Persistencia DB unica (`@transaction.atomic`) |
| Selector | `services/selectors.py` | QuerySets de lectura con `.only()`, `LIST_FIELDS`, `DETAIL_FIELDS` |

### 4.4. BaseServiceMixin — Mixin Canonico (v3.10.1)

**SSoT:** `apps/tenant/api/mixins.py`

Todos los ServiceMixins heredan de `BaseServiceMixin` que provee:
- `_get_empresa_id_seguro()` — extrae `empresa_id` de forma Zero-Trust (nunca desde `request.user.perfil`)
- `get_empresa()` / `get_empresa_id()` — helpers de contexto
- `NormalizationMixin` — `normalize_data()` en serializers para validacion de entrada

**Prohibido:** usar `request.user.perfil` en serializers directamente. Causa `AttributeError` en GET list. Usar `_get_empresa_id()` helper.

### 4.5. Double Semantic Verification (DSV)

Toda mutacion en `business_service.py` valida que los FKs del payload pertenezcan al tenant actual (`empresa_id`). Esta verificacion es la defensa principal contra ataques IDOR (Insecure Direct Object Reference) a nivel de aplicacion.

La DSV verifica:
1. Que el recurso objetivo exista en el tenant
2. Que todos los FKs referenciados en el payload pertenezcan al mismo tenant
3. Que el usuario autenticado tenga membresia activa

### 4.6. Frontend — Patron de Modulos JS

**Namespace por app:** `window.Sintel.<App>`

**[DOC-M5]** Verificado 2026-08-09 via `grep -ohE "window\.Sintel\.[A-Za-z]+" apps/tenant/*/static/*/js/**/*.js` — la tabla anterior (10 namespaces) omitia 5 namespaces reales:

| Namespace activo | App |
|---|---|
| `window.Sintel.Bancos` | bancos |
| `window.Sintel.Compras` | compras |
| `window.Sintel.Contabilidad` | contabilidad |
| `window.Sintel.Core` | core |
| `window.Sintel.Cotizaciones` | cotizaciones |
| `window.Sintel.Dashboard` | dashboard |
| `window.Sintel.Empleados` | empleados |
| `window.Sintel.Empresa` | empresa |
| `window.Sintel.Gastos` | gastos |
| `window.Sintel.Inventario` | inventario (Productos.Editor, Activos.List, etc.) |
| `window.Sintel.Perfil` | perfil |
| `window.Sintel.Proveedores` | proveedores |
| `window.Sintel.Clientes` | clientes |
| `window.Sintel.Proyectos` | proyectos |
| `window.Sintel.Ventas` | ventas |

Ademas existen 3 sub-namespaces no listados aqui por ser especificos de una feature, no de una app completa: `window.Sintel.ProyectosPresupuesto`, `window.Sintel.Representante` (proveedores), `window.Sintel.TareasDiarias` (proyectos).

Archivos por rol:

| Archivo | Responsabilidad |
|---|---|
| `<app>.api.js` | SSoT de todas las URLs y consumo de endpoints. Sin logica de UI |
| `features/<modelo>_list.js` | Grilla Tabulator (columnas compactas apiladas, KPI strips) o, en el patron actual, solo delegacion de eventos de fila sobre el panel HTMX server-rendered (ver dos patrones abajo) |
| `features/<modelo>_editor.js` | Ciclo de vida del Offcanvas (crear/editar/detalle), listeners de formulario con guard `data-editor-initialized` |

**Dos patrones de grilla coexisten (migracion en curso, ver §1.2):**

**A) django-tables2 + HTMX (patron actual, usar en modulos nuevos).** La grilla es server-rendered: `tables.py` define una `django_tables2.Table`, la vista HTML retorna el fragmento ya paginado/ordenado, y el panel se auto-carga y recarga via atributos HTMX declarativos — sin JS de terceros ni estado de grilla en el cliente.

```html
<div id="<modelo>-panel"
     hx-get="{% url '<app>:<modelo>-tabla' %}"
     hx-trigger="load, <modelo>-updated from:body"
     hx-target="this"
     hx-swap="innerHTML"
     hx-boost="true"></div>
```

- El JS del modulo (`features/<modelo>_list.js`) NO inicializa la grilla — solo delega eventos de fila (`d.querySelector('#<modelo>-panel').addEventListener('click', ...)`, filtrando por clases `.btn-editar-*`/`.btn-eliminar-*`) y expone `window.<Modelo>List.reload()` que dispara `document.body.dispatchEvent(new CustomEvent('<modelo>-updated'))` — el UNICO mecanismo correcto para forzar una recarga tras crear/editar/eliminar.
- **Prohibido:** un listener generico (`htmx:afterSettle` u otro) que refresque MULTIPLES paneles a la vez cuando esos mismos paneles viven dentro del contenedor que observa — causa un bucle de retroalimentacion infinito (incidente real: Auditoria Enterprise 2026-08-06, hallazgo C7, ~47 peticiones/segundo sostenidas en las 4 tablas de `empresa`; ver `documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md` Fase 4). Cada tabla se refresca a si misma via su propio evento `<modelo>-updated`, nunca via un orquestador que reaccione a swaps ajenos.
- **IDs de contenedor/panel deben llevar namespace de app** (`gastos-resoluciones-panel`, no `resoluciones-panel`) cuando el nombre generico del modelo puede repetirse en otro modulo coexistente en el mismo Workspace — el Workspace monta los ~15 modulos simultaneamente en una sola pagina, y `getElementById`/`querySelector` siempre resuelven al primer match del DOM (incidente real: Auditoria Enterprise 2026-08-06, hallazgo C6, colision entre `gastos_list.html` y `empleados_list.html`).

**B) Tabulator (patron legacy, en migracion — no usar en modulos nuevos).** Todas las grillas Tabulator usan `TabulatorFactory.create()` definido en `apps/tenant/core/static/core/js/common/tabulator.factory.js`. Inyecta JWT automaticamente y espera respuesta DRF paginada: `{ count, next, previous, results: [] }`.

**Patron de refresh de tabla Tabulator:** Siempre usar `table.replaceData()` (no `setData()` sin args). Diferir con `setTimeout(() => tbl.replaceData(), 50)` cuando se llama desde un click handler de Tabulator para evitar `Event Target Lookup Error`.

> **[DOC-M4, 2026-08-07]** Validacion directa del codigo (no solo documentacion cruzada) encontro que la migracion esta mas avanzada de lo que `MEMORY.md` describia: 13 de ~17 apps tenant ya tienen `tables.py` — incluyendo `inventario`, `proveedores`, `empresa`, `proyectos`, `clientes`, `perfil`, que `MEMORY.md` listaba como "pendientes" de Fase 5-BIS. Lo que SI sigue pendiente en esas apps es la limpieza de sitios Tabulator puntuales aun vivos dentro de modulos ya migrados (ver §1.2). Antes de asumir que una app necesita migrarse desde cero, verificar si ya tiene `tables.py` — `grep -l "import django_tables2" apps/tenant/*/tables.py`.

**Guard de inicializacion en editors:** Para prevenir doble-inicializacion cuando MutationObserver + htmx:afterSwap disparan simultaneamente:
```javascript
if (form.dataset.editorInitialized === 'true') return;
form.dataset.editorInitialized = 'true';
```

**HTMX (Offcanvas):** Los Offcanvas se cargan via `hx-get` apuntando a `render-offcanvas/crear/`. El backend retorna HTML parcial. Usar siempre `mostrarOffcanvasSeguro(el)` que limpia backdrops acumulados antes de llamar `show()`.

**Helpers globales de infraestructura:** `apps/tenant/core/static/core/js/common/` — disponibles en todo el tenant.

| Helper | Archivo |
|---|---|
| `UIManager` | `ui-manager.js` — notificaciones, manejo de errores 400, offcanvas |
| `TabulatorFactory` | `tabulator.factory.js` — creacion de grillas con JWT auto-inyectado |
| `http` | `http.js` — wrapper Fetch API que retorna `{ok, status, data}` |

### 4.7. Procesamiento Asincrono

Las tareas masivas, calculos sobre datos historicos e integraciones de terceros se despachan a workers Celery via `.delay()`. Toda tarea define politicas de reintentos (`max_retries`). Al agotar reintentos, el payload se inserta en un registro `FailedTenantTask` para observabilidad y reencola manual.

---

## 5. Aislamiento Cross-Schema y Gobernanza de Datos

### 5.1. Core Membership Bridge

**SSoT del bridge:** `apps/tenant/core/services/membership.py`

Las apps tenant **no pueden** importar directamente desde `apps.public.*`. El bridge es la unica interfaz autorizada para consultar datos del esquema publico.

| Operacion del Bridge | Descripcion |
|---|---|
| `check_membership(user, empresa)` | Verifica membresia activa. Retorna `TenantMembership` o `None` |
| `check_membership_exists(user, empresa)` | Retorna `bool` para verificacion rapida |
| `check_admin_membership(user, empresa)` | Verifica membresia con rol ADMIN |
| `check_primary_admin(empresa)` | Retorna el `TenantMembership` del administrador primario |
| `get_user_role(user, empresa)` | Retorna el string del rol o `None` |
| `get_primary_domain(empresa)` | Retorna el dominio primario del tenant |
| `verify_invitation(token)` | Valida token de invitacion |

**Excepcion:** Solo `apps/tenant/core/` y `apps/tenant/api/` (permisos centrales) pueden importar desde `apps.public`. Ninguna otra app tenant tiene esta autorizacion.

### 5.2. Reglas de Aislamiento de Assets (CSS/JS)

Todos los archivos `.html` y `.js` deben residir dentro del nucleo de la app a la que pertenecen.

| Tipo | Ruta obligatoria |
|---|---|
| Templates tenant | `apps/tenant/<app>/templates/tenant/<app>/` |
| JS estatico tenant | `apps/tenant/<app>/static/<app>/js/` |
| Templates public | `apps/public/<app>/templates/<app>/` |
| JS estatico public | `apps/public/<app>/static/<app>/js/` |
| Helpers globales (excepcion controlada) | `apps/tenant/core/static/core/js/common/` |

Cada app define un template `assets_<app>.html` que centraliza la inclusion de sus scripts y estilos. Prohibidos: scripts compartidos entre modelos no relacionados, templates monoliticos, referencias cruzadas de assets entre apps.

**Helper global `offcanvas.helper.js` (FE-A5, PLAN_UNICO_CORRECCIONES.md Fase 5):** `apps/tenant/core/static/core/js/common/offcanvas.helper.js` expone `window.Sintel.Core.mostrarOffcanvasSeguro(elOrId)` — SSoT que reemplaza las 16 reimplementaciones locales encontradas en la auditoria 2026-07-26. Se carga globalmente desde `assets_core.html`, antes de cualquier modulo. Todo codigo nuevo que abra un Bootstrap Offcanvas debe usar este helper en vez de reimplementar el patron dispose+create.

**Estado dual de `http.js` (FE-M4, deuda documentada, no resuelta):** existen 2 versiones de `http.js` cargadas ambas en el shell del workspace: `core/static/js/http.js` (SSoT moderno, inyecta JWT) y `core/static/core/js/lib/http.js` (version "legacy" que gana por orden de carga en `assets_core.html`/`workspace.html`). La version legacy **no se elimino** (ver `REPORTE_FASE_1.md`, hallazgo FE-C3) porque es la unica que maneja correctamente `FormData` (subida de archivos) y expone `window.getCookie`, del que dependen ~20 features. El fix aplicado en Fase 1 inyecto el JWT tambien en la version legacy, cerrando el bug de seguridad sin tocar el resto de su comportamiento. Consolidar ambas en un solo archivo sigue pendiente (Fase 6/7 del plan de correcciones).

### 5.3. Prohibiciones de Gobernanza

| Regla | Detalle |
|---|---|
| Sin emojis en `.py` | Causan `SyntaxError` → Django 500 |
| `SintelTenantBaseModel` obligatorio | Todos los modelos tenant lo heredan; nunca `models.Model` directamente |
| `empresa_id` en toda query | Sin `.all()` ni `.filter()` sin empresa |
| `.only()` obligatorio | Toda queryset especifica campos |
| Sin Signals para logica de negocio | Todo en Service Layer |
| Sin `.py` nuevos fuera del Service Layer | Requiere autorizacion explicita del usuario |
| `apps/public/` bloqueado | Requiere RFC + etiqueta `needs-admin-approval` |
| UUID como lookup field | `BaseTenantViewSet` expone UUID; nunca PKs enteras en URLs |
| FK a `perfil.TenantProfile` | Nunca FK a `settings.AUTH_USER_MODEL` desde modelos tenant |
| `parseInt()` sobre UUID | PROHIBIDO — `parseInt("9abc...",10)=9` corrompe UUID a entero parcial |
| `getOrCreateInstance().show()` HTMX | PROHIBIDO — acumula backdrops; usar `mostrarOffcanvasSeguro(el)` |
| `setData()` sin args en Tabulator | Usar `replaceData()` para forzar nuevo fetch del servidor |
| `py_compile` hook | PostToolUse hook valida toda edicion `.py`. Corregir antes de continuar |
| `if settings.DEBUG:` en autorizacion | PROHIBIDO — nunca condicionar una verificacion de permiso/membresia/rol al valor de `DEBUG`. Incidente real: los 5 permisos SSoT de `apps/tenant/api/permissions.py` mas 3 `get_permissions()` de ViewSets tenian `if settings.DEBUG: return True`, desactivando por completo la verificacion de pertenencia al tenant en cualquier instancia con `DEBUG=True` — causa raiz de una fuga completa de datos entre tenants (Auditoria Enterprise 2026-08-06, hallazgo C1, ver `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`). Verificado limpio (`grep DEBUG apps/tenant/api/permissions.py` sin resultados) el 2026-08-07 |
| Comentarios `{# #}` multilinea en templates Django | PROHIBIDO — el motor de plantillas de Django no reconoce `{#`/`#}` si abarcan mas de una linea; el bloque completo se renderiza como texto HTML literal visible al usuario. Usar `{% comment %}...{% endcomment %}` para comentarios multilinea, o colapsar a una sola linea. Hallazgo transversal confirmado en 9 archivos / 10 bloques preexistentes (ver M1 en `documentacion/PLAN_PRUEBASUI_PRIVADAS.md`) mas 3 instancias nuevas introducidas y corregidas durante la Auditoria Enterprise 2026-08-06 (Fases 3 y 4 de `documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md`) |
| Nombre de carpeta en `dependencies` de migraciones | PROHIBIDO — usar el `app_label` real (`grep label apps/tenant/<app>/apps.py`), no el nombre de carpeta. 10 de 17 apps tenant sobre-escriben `label` (ver `.agents/skills/backend/django-tenant.md`). Incidente real: migracion `0020` de `proyectos` referenciaba `('proyectos', ...)` en vez de `('tenant_proyectos', ...)`, bloqueando `migrate_schemas` — y por tanto el arranque de `web` — para todo el proyecto. Ver `apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` (FIX v3.10.5). Mejor practica: dejar que `makemigrations` genere `dependencies` automaticamente |

### 5.4. Principios de Idempotencia

Toda operacion de mutacion (creacion/actualizacion) o ingesta de datos debe ser idempotente. La base de datos respalda esto mediante constraints unicos. Los servicios manejan conflictos via Silent Success o Upsert.

---

## 6. Capa de Integracion Contable Centralizada (Modelo Pull)

### 6.1. Principio Fundamental

Ningun asiento contable se crea directamente desde apps fuente. El `Contabilizador` de `contabilidad` extrae activamente los documentos pendientes. Las apps fuente no conocen ni importan desde `contabilidad`.

**Patron Push (PROHIBIDO):** app fuente llama funcion de contabilidad.
**Patron Pull (OBLIGATORIO):** extractor de contabilidad lee app fuente.

### 6.2. Desacoplamiento Contable Completo (v3.10.2)

**Estado:** COMPLETADO — 2026-05-28

Los campos `cuenta_contable_uuid` / `cuenta_*_uuid` fueron **eliminados de todos los modelos de negocio**. Contabilidad es la unica propietaria de mapeos PUC. Las apps fuente son ahora Pure Pull.

| App | Campos Eliminados | Migracion |
|---|---|---|
| proveedores | `codigo_contable`, `cuenta_contable_uuid` | 0007 |
| clientes | `cuenta_contable_uuid` | 0007 |
| inventario | `cuenta_inventario_uuid`, `cuenta_costo_uuid`, `cuenta_ingreso_uuid`, `cuenta_activo_uuid`, `cuenta_depreciacion_uuid` | 0009 |
| facturas | `cuenta_contable_uuid` | 0026 |
| gastos | `cuenta_gasto_uuid` | 0020 |
| empleados | `cuenta_contable_uuid` (Devengo) | 0010 |

**Total:** 15 campos eliminados, 6 apps, 30 archivos modificados. `0 referencias` en codigo vivo.

### 6.3. Paquete de Integracion

**Ruta:** `apps/tenant/contabilidad/integracion/`

| Modulo | Responsabilidad |
|---|---|
| `dtos.py` | DTOs inmutables (`@dataclass(frozen=True)`) — contrato entre apps fuente y Contabilizador |
| `contabilizador.py` | Orquestador unico — valida, resuelve cuentas, construye y persiste asientos atomicamente |
| `resolver.py` | Mapea (`tipo_transaccion` + `concepto`) a codigo PUC via `ReglaContable` por tenant |
| `validadores.py` | Validators stateless — cuadratura, periodo abierto, documento origen existe |
| `excepciones.py` | Jerarquia `ContabilidadError` y subclases |
| `extractores/base.py` | `AbstractExtractor` — interfaz comun |
| `extractores/gastos.py` | `ExtractorGastos` — extrae `DocumentoSoporte` pendientes (sin `cuenta_gasto_uuid`) |
| `extractores/inventario.py` | `ExtractorInventario` — extrae `MovimientoInventario` pendientes |
| `extractores/facturas.py` | `ExtractorFacturas` — extrae `Factura` ACEPTADA pendientes (sin `cuenta_contable_uuid`) |
| `extractores/nomina.py` | `ExtractorNomina` — extrae todos los `Devengo` no anulados (sin filtro por cuenta) |

**Nota v3.10.2:** Los extractores ya no usan `cuenta_hint` desde modelos origen. Las cuentas se resuelven exclusivamente via `ReglaContable` segun `tipo_transaccion` y `concepto`. El filtro `cuenta_contable_uuid__isnull=False` fue eliminado de `ExtractorNomina`.

### 6.4. DTOs — Contrato Inmutable

Los DTOs son frozen dataclasses que encapsulan el contexto economico del documento origen:

- `TransaccionEconomica` — envelope principal con tipo, fecha, tercero (snapshot), lineas y documento origen
- `LineaTransaccion` — concepto, monto y lado del asiento (`'DEBE'` o `'HABER'`)
- `ImpuestoLinea` — tipo, valor y lado (impuestos van siempre a `'HABER'`)
- `TerceroSnapshot` — snapshot del tercero sin FK (inmutable en el tiempo)
- `DocumentoOrigen` — app_label, modelo, id para idempotencia

El campo `empresa_id` no va dentro del DTO — lo inyecta el `Contabilizador` desde su contexto. La idempotencia se garantiza via constraint UNIQUE sobre `documento_origen` en `AsientoContable`.

### 6.5. Numero de Asiento — Formato Canonico

| Tipo | Formato |
|---|---|
| Normal | `ASI-{YYYYMMDD}-{UUID8}` |
| Reversal | `RVER-{YYYYMMDD}-{UUID8}` |

El numero lo genera exclusivamente el `Contabilizador._construir_asiento()`. Prohibido que el caller externo lo provea.

### 6.6. APP_ORIGEN_PREFIJOS — SSoT de Codigos PUC

**SSoT:** `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS`

Todos los codigos PUC de vinculacion contable para todas las apps de negocio se obtienen exclusivamente desde este diccionario. Prohibido hardcodear prefijos en apps fuente.

| App | Ejemplos de prefijos autorizados |
|---|---|
| `facturas` | `1305`, `4135`, `4175`, `2365`, `2368`, `240805` |
| `clientes` | `1305`, `1375`, `4135`, `413505`, `413510` |
| `gastos` | `233505`, `51`, `6`, `2365`, `240810` |
| `empleados` | `5105`, `5110`, `2370`, `25`, `51` |
| `inventario` | `143505`, `1435`, `6135`, `4135`, `51`, `15` |
| `proveedores` | `2205`, `2335`, `2365`, `2805`, `280505` |

### 6.7. Retenciones — ADR-001 Pull Model

**SSoT:** `docs/ADR-001-retention-pull-model.md`

El modelo `Retencion` vive en `contabilidad`. Las apps fuente nunca almacenan montos de retencion directamente. Para crear o consultar retenciones se usa `RetencionesService` de `apps/tenant/contabilidad/services/retenciones_service.py`.

**Endpoints de retenciones:**

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/contabilidad/retenciones/obtener-por-tercero/` | GET | Configuracion de retencion para un NIT dado |
| `/api/v1/contabilidad/retenciones/obtener-por-documento/` | GET | Retenciones de un documento origen |
| `/api/v1/contabilidad/retenciones/` | GET / POST | Listado y creacion |

### 6.8. Activacion de Extractores

Los extractores se invocan exclusivamente desde management commands o tareas Celery periodicas. Nunca desde ViewSets ni Signals.

```bash
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
```

---

## 7. Decisiones Arquitectonicas Relevantes (ADRs)

> **Nota de gobernanza (2026-08-08):** esta tabla tenia una numeracion ADR duplicada — `ADR-002`
> y `ADR-003` se usaban aqui para dos decisiones tecnicas antiguas (nunca formalizadas en su
> propio archivo `docs/ADR-NNN-*.md`), mientras que esos mismos numeros ya estaban en uso por
> archivos reales y activamente referenciados en codigo (`docs/ADR-002-public-schema-api-dual-registration.md`,
> `docs/ADR-003-contexto-organizacional-sede-area.md`). Verificado por grep: **cero** referencias
> de codigo usan "ADR-002"/"ADR-003" con el significado antiguo — todas (docenas, en
> `apps/tenant/api/`, `apps/tenant/compras/`, `apps/tenant/core/services/organizational_*.py`,
> comentarios de tests) usan el significado nuevo. Resuelto conservando los 4 archivos
> `docs/ADR-NNN-*.md` existentes sin renombrar (son la convencion activa) y retirando el prefijo
> "ADR-NNN" de las 2 decisiones antiguas sin archivo propio (quedan documentadas como decisiones
> tecnicas historicas, no como ADRs numerados) — ver "Organizational Scope Framework, Fase 1" en
> `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`.

| ADR | Titulo | Estado | Fecha | Documento |
|---|---|---|---|---|
| ADR-001 | Retencion Pull Model (v3.7.1) — Contabilidad owns Retencion | ACCEPTED | 2026-05-13 | `docs/ADR-001-retention-pull-model.md` |
| ADR-002 | Registro Dual de Endpoints en Schemas Publico y Tenant | ACCEPTED | 2026-06-09 | `docs/ADR-002-public-schema-api-dual-registration.md` |
| ADR-003 | Contexto Organizacional (Empresa -> Sede -> Area) — Fundamentos + piloto `compras` | ACCEPTED (alcance parcial, ver nota DOC-M5 en §3.6) | 2026-08-07 | `docs/ADR-003-contexto-organizacional-sede-area.md` |
| ADR-004 | Organizational Context Framework (OCF) — Modelo de Diseño | ACCEPTED (parcialmente implementado, ver Adenda 2026-08-09 en el propio archivo) | 2026-08-07 (adenda 2026-08-09) | `docs/ADR-004-organizational-context-framework-diseno.md` |
| ADR-005 | Organizational Scope Framework (OSF) — Contrato Independiente y Rollout sin Migracion de Esquema | ACCEPTED (parcialmente implementado) | 2026-08-09 | `docs/ADR-005-organizational-scope-framework.md` |

> **[DOC-M6, 2026-08-09] ADR-004/ADR-005 y el plan de consolidacion OCF/OSF — cerrado, verificado
> y commiteado.** El proyecto de consolidacion OCF/OSF (`documentacion/
> ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`, 12 fases, FASE 0-12) audito codigo real (no solo
> `MEMORY.md`) linea por linea, con ejecucion real de tests (no solo lectura), y cerro con
> **🟢 ORGANIZATIONAL BASELINE**: Codigo + Tests + ADR + Documentacion + Git alineados y
> verificados. `docs/ADR-004-*.md` gano una "Adenda 2026-08-09" que actualiza su Estado a ACCEPTED
> (parcial) y documenta 2 divergencias reales entre lo diseñado y lo construido (`OrganizationalScope`
> NO se construye a partir de `OrganizationalContext`, contrario al diagrama original;
> `OrganizationalSelector` como clase nunca se construyo — su rol lo cumplen funciones puras +
> metodos de las dataclasses). `docs/ADR-005-organizational-scope-framework.md` (nuevo) formaliza
> 2 decisiones arquitectonicas reales tomadas explicitamente con el usuario durante el proyecto OSF
> (independencia de `OrganizationalScope` respecto a `OrganizationalContext`; `filter_by_scope_null_safe()`
> como patron de rollout SIN migracion de esquema para las 6 apps con `sede` historicamente en NULL).
> Durante la consolidacion se encontraron y **corrigieron** 2 bugs reales de aislamiento (ver §3.6).
> **Ya esta commiteado**: 5 commits (`0295932`..`34fc020`, ver `documentacion/FASE11_CONSOLIDACION_GIT.md`)
> — el ultimo commit del repositorio es `34fc020`, no `371f19d` como indicaba la version anterior de
> este documento. Detalle completo: `documentacion/OCF_TECHNICAL_AUDIT.md`,
> `documentacion/OSF_TECHNICAL_AUDIT.md`, `documentacion/ORGANIZATIONAL_CONTRACT.md`,
> `documentacion/ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` (cierre). **Pendiente, fuera de esta
> consolidacion por decision explicita** (no por omision): FASE 13/14 del plan (extension del
> Knowledge Graph EKG con capas organizacionales + gobernanza automatica) — ver justificacion en
> `ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` §9.

**Decisiones tecnicas historicas (anteriores a la convencion `docs/ADR-NNN-*.md`, sin archivo dedicado propio):**
- **Desacoplamiento Contable Total** (2026-05-28, COMPLETED) — Eliminacion de `cuenta_*_uuid` en
  apps fuente. Impacto: Contabilidad es la unica propietaria de mapeos PUC; las apps fuente son
  Pure Pull (zero coupling); los extractores resuelven cuentas exclusivamente via `ReglaContable`.
  El checklist de esta refactorizacion no quedo formalizado en un documento aparte (referencia
  rota a `REFACTORIZAR_DESACOPLAMIENTO_CONTABLE_FRAMEWORK.md` retirada en Fase 9, DOC-A4 — el
  archivo nunca existio).
- **TareaCorta.cliente FK PROTECT → SET_NULL** (2026-05-29, APPLIED) — permite eliminacion de
  clientes inactivos sin bloquear por tareas cortas historicas asociadas.

---

## 8. Ecosistema de Agentes de Inteligencia Artificial

### 8.1. Principio de Diseno

El asistente IA es un metodo de entrada rapida para lineas de asiento contable en el flujo Manual On-Demand. La validacion local (cuadratura, nivel 6, `TipoComprobante`) es siempre la fuente de verdad final. La IA nunca persiste datos sin confirmacion explicita del usuario.

### 8.2. Agentes Especializados por Dominio

| Agent ID | App Label | Conocimiento NIIF Colombia | Modelo |
|---|---|---|---|
| `FacturacionAgent` | `facturas` | CxC (1305), IVA generado (240805), Retefuente (2365xx), ReteICA (2368xx), Ingresos (4135xx) | `claude-haiku-4-5-20251001` |
| `GastosAgent` | `gastos` | CxP Proveedor (2335xx), IVA descontable (240810), Retefuente (2365xx), Gastos operativos (51xx) | `claude-haiku-4-5-20251001` |
| `NominaAgent` | `empleados` | Salarios (5105xx), Aportes seguridad social (2370xx), Obligaciones laborales (25xx) | `claude-haiku-4-5-20251001` |
| `InventarioAgent` | `inventario` | Inventario (1435xx), CMV (6135xx), Ingresos (4135xx) | `claude-haiku-4-5-20251001` |

### 8.3. Flujo del Orquestador

```
POST /api/v1/contabilidad/pendientes/asistente-ia/
    |
    +-- AsistenteIAInputSerializer.validate()
    |
    +-- ContabilidadBusinessService.sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)
    |       +-- filtrar_cuentas_por_app_origen(qs, app_label) → cuentas nivel-6 del tenant
    |       +-- anthropic.messages.create(model='claude-haiku-4-5-20251001', ...)
    |       +-- Validar cuenta: nivel==6, activa==True, empresa_id (DSV)
    |       +-- Validar cuadratura: |Sum(Debe) - Sum(Haber)| < 0.01
    |
    +-- Response({ lineas: [{cuenta_codigo, cuenta_nombre, debe, haber, descripcion}, ...] })
```

### 8.4. Configuracion y Compliance

| Variable de entorno | Descripcion | Obligatoria |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key del tenant Anthropic | Si |

**Regla critica:** Prohibido persistir asientos desde la IA sin confirmacion explicita del usuario. El boton "Generar Asiento" siempre requiere cuadratura local < 0.01.

### 8.5. Agentes de Codigo (Claude Code)

El archivo `AGENTS.md` es el contexto primario para cualquier agente de codigo. El archivo `MEMORY.md` en la raiz del proyecto es la fuente canonica del estado actual, decisiones arquitectonicas recientes (ADRs) y progreso activo.

Regla para agentes de codigo: al iniciar cualquier sesion o tarea nueva, leer `MEMORY.md` primero, luego `AGENTS.md`, luego el `.agent/AUDITORIA_FLUJO_*.md` de la app objetivo.

---

## 9. Endpoints API REST

**SSoT de endpoints:** `config/api_urls.py` — **[DOC-M5, corregido]** 203 lineas, 17 modulos montados con try/except resiliente por app (antes reportado como "149 lineas, 14 modulos" — desactualizado; la tabla de abajo tambien omitia `bancos` por completo, ya corregido).

| Prefijo | App | Modelos Principales |
|---|---|---|
| `/api/v1/empresas/` | empresa | Empresa, Sede, Area |
| `/api/v1/facturas/` | facturas | Factura, ItemFactura, NotaCredito |
| `/api/v1/contabilidad/` | contabilidad | CuentaContable, AsientoContable, Retencion, ReglaContable, PlantillaContable |
| `/api/v1/inventario/` | inventario | Producto, Servicio, ActivoFijo, MovimientoInventario, HistorialServicio, CategoriaItem |
| `/api/v1/perfil/` | perfil | TenantProfile |
| `/api/v1/dashboard/` | dashboard | Metricas consolidadas |
| `/api/v1/core/` | core | Auth bridge, onboarding, configuraciones globales, contexto organizacional (`/core/contexto/`) |
| `/api/v1/empleados/` | empleados | Empleado, Contrato, Devengo, ResolucionDIAN |
| `/api/v1/gastos/` | gastos | DocumentoSoporte, ResolucionDIAN |
| `/api/v1/bancos/` | bancos | CuentaBancaria, ExtractoBancario, TransaccionBancaria |
| `/api/v1/proveedores/` | proveedores | Proveedor, CuentasPagar, Representante |
| `/api/v1/clientes/` | clientes | Cliente, ContactoCliente, Cartera |
| `/api/v1/cotizaciones/` | cotizaciones | Cotizacion, CotizacionItem |
| `/api/v1/proyectos/` | proyectos | Proyecto, TareaCorta, AsignacionPersonal |
| `/api/v1/compras/` | compras | OrdenCompra, ItemOrdenCompra, PlantillaOrdenCompra |
| `/api/v1/ventas/` | ventas | Venta, ItemVenta, ResolucionFacturacion |
| `/api/v1/impuestos/` (public) | impuestos | Catalogo DIAN |

**`/mcp/` (nuevo, DOC-M5):** endpoint separado (no en `api_urls.py`, montado directo en `config/urls_public.py`/`config/urls_tenant.py`) que expone ViewSets decorados con `@mcp_viewset()` como herramientas MCP — ver §1.1.

**Formato de respuesta paginada (estandar DRF):**
```json
{ "count": 100, "next": "...", "previous": "...", "results": [...] }
```

**Lookup field:** todas las URLs usan UUID: `/api/v1/<app>/{uuid}/`

---

## 10. Indice General de Fuentes de Verdad

### 10.1. Documentos de Referencia Global

| SSoT | Ruta | Descripcion |
|---|---|---|
| Arquitectura global | `documentacion/arquitectura_general.md` | Este documento |
| Reglas de desarrollo | `AGENTS.md` | Reglas estrictas e inmutables para todo el proyecto |
| Estado del proyecto | `MEMORY.md` (raiz) | Estado actual, ADRs activos, progreso en curso |
| Rutas API | `config/api_urls.py` | Unica fuente de verdad para endpoints REST |
| Settings | `config/settings.py` | Configuracion Django, JWT, Celery, SHARED/TENANT_APPS |
| Codigos PUC por app | `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS` | Prefijos autorizados por app de negocio |
| Roles de tenant | `apps/tenant/perfil/models.py:TenantProfile.rol` | ADMIN / OPERADOR / VISOR |
| Permisos DRF | `apps/tenant/api/permissions.py` | Unica fuente para importar permisos en ViewSets |
| Autenticacion | `apps/tenant/api/base.py:BaseTenantViewSet` | Dual-Auth centralizado (JWT + Session) |
| BaseServiceMixin | `apps/tenant/api/mixins.py:BaseServiceMixin` | Mixin canonico para todos los ServiceMixins |
| Modelo base tenant | `apps/tenant/core/models.py:SintelTenantBaseModel` | Herencia obligatoria para todos los modelos tenant |
| Bridge cross-schema | `apps/tenant/core/services/membership.py` | Unica interfaz autorizada para consultar esquema public |
| ADR Retenciones | `docs/ADR-001-retention-pull-model.md` | Contabilidad owns Retencion, Pull Model |
| ADR Dual-Registration API Publica | `docs/ADR-002-public-schema-api-dual-registration.md` | Endpoints accesibles desde `home.sintel.net.co` — registro dual public/tenant |
| Auditoria Enterprise UI (2026-08-06) | `documentacion/PLAN_PRUEBASUI_PRIVADAS.md` | Informe de auditoria via UI real, 23 hallazgos clasificados; marcadores `[CORREGIDO]` indican los ya remediados |
| Remediacion Fase 1 (Criticos Seguridad) | `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md` | Detalle 10-secciones de C1/C2/C3 + hallazgo de onboarding |
| Remediacion Fases 2-8 | `documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md` | Detalle 10-secciones de C4/C5/C6/C7, onboarding, regresion y documentacion |
| Consolidacion OCF/OSF (2026-08-09) | `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md` | Indice maestro de las 12 fases (auditoria de codigo real, ADR-004/005, matriz de cobertura de 17 apps, piloto `compras`, `facturas`, `Ventas->Facturas`, rollout controlado, consolidacion git) — enlaza los 12 documentos de detalle. Cierre: `documentacion/ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` |
| Knowledge Graph Organizacional + Gobernanza Automatica (2026-08-09) | `documentacion/F13_F14_FINAL_REPORT.md` | `tools/organizational_governance/` (grafo + motor de reglas, independiente de `tools/ekg/`) — estado fase por fase en `documentacion/F13_F14_EXECUTION_STATUS.md`, findings en `documentacion/GOVERNANCE_REMEDIATION_PLAN.md` |

### 10.2. Documentos de Auditoria por App (SSoT por modulo)

> **Regla (AGENTS.md §16):** antes de modificar cualquier app, leer su documento de auditoria.

| App | Ruta | SSoT de auditoria |
|---|---|---|
| `core` (tenant) | `apps/tenant/core/` | `apps/tenant/core/.agent/AUDITORIA_FLUJO_CORE.md` |
| `empresa` | `apps/tenant/empresa/` | `apps/tenant/empresa/.agent/AUDITORIA_EMPRESA.md` |
| `perfil` | `apps/tenant/perfil/` | `apps/tenant/perfil/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `facturas` | `apps/tenant/facturas/` | `apps/tenant/facturas/.agent/AUDITORIA_FLUJO_COMPLETO_FACTUR.md` |
| `contabilidad` | `apps/tenant/contabilidad/` | `apps/tenant/contabilidad/.agent/AUDITORIA_COMPLETA_CONTABILIDAD.md` |
| `gastos` | `apps/tenant/gastos/` | `apps/tenant/gastos/.agent/AUDITORIA_FLUJO_COMPLETO_GASTOS.md` |
| `inventario` | `apps/tenant/inventario/` | `apps/tenant/inventario/.agent/AUDITORIA_FLUJO_INVENTARIO.md` |
| `empleados` | `apps/tenant/empleados/` | `apps/tenant/empleados/.agent/AUDITORIA_FLUJO_EMPLEADOS.md` |
| `cotizaciones` | `apps/tenant/cotizaciones/` | `apps/tenant/cotizaciones/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `clientes` | `apps/tenant/clientes/` | `apps/tenant/clientes/.agent/AUDITORIA_FLUJO_CLIENTES.md` |
| `proveedores` | `apps/tenant/proveedores/` | `apps/tenant/proveedores/.agent/AUDITORIA_FLUJO_COMPLETO_PROVE.md` |
| `proyectos` | `apps/tenant/proyectos/` | `apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `dashboard` | `apps/tenant/dashboard/` | `apps/tenant/dashboard/.agent/` |
| `bancos` | `apps/tenant/bancos/` | `apps/tenant/bancos/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `compras` | `apps/tenant/compras/` | `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md` |
| `ventas` | `apps/tenant/ventas/` | `apps/tenant/ventas/.agent/ARQUITECTURA_VENTAS.md` |
| `landing` | `apps/tenant/landing/` | `apps/tenant/landing/.agent/AUDITORIA_FLUJO_LANDING.md` |

### 10.3. Cobertura de Tests

> **[DOC-M5, recontado 2026-08-09; DOC-M6 nota de estado]** Tabla recontada por conteo directo de `apps/tenant/<app>/tests/test_*.py` + `tests/tenant/<app>/test_*.py`. El conteo anterior (2026-08-03, tabla de abajo la reemplaza) esta muy desactualizado — el trabajo de Contexto/Alcance Organizacional (§7) y otras fases agregaron un numero grande de tests nuevos. Los tests de OCF/OSF especificamente (las suites `test_organizational_*.py`/`test_scope_*_fN.py` citadas en la columna de aislamiento) **ya estan commiteados** (commit `1d19d8f`, ver §7) — 53/53 (core) y 20/20 (compras) confirmados pasando por ejecucion real. Los tests nuevos de OTRAS lineas de trabajo (Auditoria Enterprise, EKG) siguen sin commitear. No incluye suites cross-cutting no atribuibles a una sola app (`tests/api`, `tests/celery*`, `tests/general`, `tests/multitenant`, `tests/smoke`, etc.) — el total real de archivos `test_*.py` en todo el repositorio (excluyendo `venv/`) era **401** al momento del conteo DOC-M5 (2026-08-09, antes de esta sincronizacion; no se re-conto tras los commits porque commitear no cambia el numero de archivos en disco).

| App | Archivos de Test (in-app + centralizado) | `test_multitenant_isolation*.py` / `test_cross_tenant*.py`? |
|---|---:|---|
| core | 63 | — |
| facturas | 44 | Parcial (`test_multitenant_isolation_tabla_html.py`) |
| empresa | 29 | — |
| empleados | 13 | Parcial (`test_multitenant_isolation_tablas_html.py`, nuevo) |
| gastos | 12 | ✅ Completo (`test_multitenant_isolation.py`) |
| dashboard | 12 | — |
| contabilidad | 9 | ✅ Nuevo (`test_multitenant_isolation.py`) |
| clientes | 8 | — |
| perfil | 6 | — |
| inventario | 8 | — |
| landing | 20 | — |
| cotizaciones | 7 | — |
| proveedores | 6 | — |
| proyectos | 8 | — |
| bancos | 6 | ✅ Completo (`test_multitenant_isolation.py` + `test_cross_tenant_isolation.py`) |
| compras | 4 | Parcial (`test_multitenant_isolation_tabla_html.py`) |
| ventas | 2 | ✅ (`test_multitenant_isolation.py`) |
| **Total atribuido por app** | **257** | **4 completos / 3 parciales de 17 apps** |

---

## 11. Comandos Esenciales

```bash
# Docker
make up                  # Levantar servicios (web:8000, db:5432, redis:6379, celery)
make down                # Detener
make logs                # Tail logs del contenedor web
make shell               # Shell en el contenedor web

# Migraciones multi-tenant
make migrate-tenants     # Todos los esquemas tenant
make migrate-shared      # Esquema public
make makemigrations      # Crear migraciones
make check-migrations    # Verificar pendientes

# Migraciones manuales (dentro del container)
docker compose exec web python manage.py migrate_schemas --shared
docker compose exec web python manage.py migrate_schemas

# Calidad de codigo
make audit               # ruff + bandit + django check
make ruff                # Lint + autofix (line-length 100, py3.12)
make bandit              # Escaneo de seguridad
make dj-check            # Django system check

# Tests
make test                # Todos los tests (pytest)
make test-file FILE="path/to/test.py"  # Un archivo especifico
make smoke               # Suite de smoke tests

# Contabilidad
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]

# Tenant
make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py ensure_public_domains

# Validacion pre-PR (obligatorio)
python -m py_compile <archivo.py>
python manage.py check
```

---

## 12. Metricas del Proyecto (v3.18.0 — 2026-08-09, DOC-M5)

**[DOC-M5]** Esta tabla estaba etiquetada `v3.10.4 — 2026-05-29` y nunca se habia vuelto a tocar en pases de validacion posteriores (DOC-A1 a DOC-M4) — de ahi que tuviera numeros distintos e inconsistentes con el resto del documento (ver §2.2). Recontada 2026-08-09 con la misma metodologia del resto de este pase (conteo directo sobre codigo, no sobre documentacion previa).

| Metrica | Cantidad |
|---|---|
| Apps publicas activas | 5 |
| Apps tenant registradas (`TENANT_APPS`) | 17 (15 con modelos de negocio + `core` + `landing`, ver §2.2/§2.3) |
| Modelos publicos | 19 |
| Modelos tenant | 67 concretos + 3 abstractos |
| Total migraciones | 186 (177 tenant + 9 public) |
| Endpoints API (prefijos en `api_urls.py`) | 17 modulos (16 tenant + 1 public) + endpoint `/mcp/` separado |
| Archivos de test (atribuidos por app) | 257 (401 en todo el repo, excluyendo `venv/`) |
| Dependencias Python | 20+ |
| Namespaces JS activos | 15 (`window.Sintel.*`) + 3 sub-namespaces de feature |
| Campos contables eliminados (v3.10.2) | 15 en 6 apps |
| Apps con Pure Pull Model contable | 6 (Proveedores, Clientes, Inventario, Facturas, Gastos, Empleados) |
| Django system check | No re-verificado en esta pasada (validacion fue por lectura de codigo, no ejecucion; ver advertencia general al inicio del documento sobre el working tree sin commitear) |
