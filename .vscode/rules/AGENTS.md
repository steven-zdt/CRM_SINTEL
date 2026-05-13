---
name: reglas-vscode
description: Reglas SINTEL v3.5.0 — Sincronizado con root AGENTS.md
sync_source: ../AGENTS.md
last_sync: 2026-05-09
---

> **FUENTE CANONICA:** El archivo de reglas autoritativo es `AGENTS.md` en la raíz del proyecto.
> Este archivo replica las reglas para herramientas de editor (VSCode Copilot, extensiones de análisis).
> **NO editar este archivo directamente.** Toda modificación de reglas va en el root `AGENTS.md`.

---

# [CORE] SINTEL v3.5.0 — Reglas de Arquitectura y Estructura de Proyecto

Estas reglas son **ESTRICTAS, INMUTABLES Y OBLIGATORIAS** para cualquier modificación, refactorización o creación de código en este proyecto. Este archivo debe ser procesado y asimilado antes de implementar cualquier prompt o sugerencia de código.

Este documento refleja el **ADN real** del codebase: patrones, convenciones y estructuras que ya están materializados en producción.

## [CRITICAL] 0. Cero Caracteres Especiales en Código Python

**REGLA FUNDAMENTAL - NO EMOJIS EN ARCHIVOS .PY**

- **[PROHIBIDO]**: Usar emojis en CUALQUIER archivo `.py`.
- **[PROHIBIDO]**: Caracteres especiales Unicode/multibyte en código Python.
- **[PERMITIDO]**: Comentarios y docstrings en texto plano SOLAMENTE.
- **RAZON**: Los emojis en código Python causan `SyntaxError` que rompen la compilación y generan `500 Internal Server Error` en Django.
- **ALCANCE**: Aplica a TODO el proyecto - `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`.
- **VALIDACION**: Toda PR debe pasar `python -m py_compile archivo.py` sin errores.

## [TECH] 1. Tecnologías Implementadas y Stack Base

**Frontend (`static/<app_name>/js`):**
- Vanilla JavaScript ES6+ modular, bajo el namespace `window.Sintel.<App_Name>`.
- Orquestador central: `<app_name>.main.js` (controlador raíz, delega a submódulos).
- Submódulos especializados:
   - `<app_name>.api.js`: Unica fuente de verdad para URLs y consumo de endpoints directos (Gateway Directo, sin Facade).
   - `<app_name>.table.js`: Inicialización y configuración de Tabulator, definición de columnas y eventos.
   - `<app_name>.ui.js`: Manejo de DOM, ciclo de vida de Offcanvas Bootstrap, integración con HTMX, recolección de formularios y DOM Shield.
   - `<app_name>.utils.js`: Funciones puras de formateo, validación y helpers (sin efectos secundarios).
   - `<app_name>.sync.js` (si aplica): Orquestación de sincronización o tareas en segundo plano, emisión de eventos y feedback UI.
- Integración nativa con HTMX para acciones asíncronas y feedback reactivo.
- Estricto aislamiento por módulo: ningún JS cruza lógica entre modelos.

**Templates (`templates/tenant/<app_name>`):**
- Estructura Feature-Sliced: cada template corresponde a una acción o vista específica (listado, offcanvas crear/editar/detalle).
- Partials dedicados en `partials/` para componentes reutilizables y tablas.
- Prohibido el uso de templates monolíticos o modals compartidos entre modelos.
- Integración directa con endpoints Gateway Directo vía HTMX (`hx-get`).
- **Ruta obligatoria:** `apps/tenant/<app_name>/templates/tenant/<app_name>/` (prefijo `tenant/` OBLIGATORIO).

**Backend Service Layer (`services/`):**
- Modularización estricta por responsabilidad (paquete `services/`):
   - `__init__.py`: Punto de entrada. Exporta clases principales para imports limpios.
   - `crud_service.py`: Acceso a datos puro y persistencia transaccional (`@transaction.atomic`). Sin lógica de negocio.
   - `business_service.py`: Orquestación y lógica de negocio. Sin acceso directo a ViewSets.
   - `selectors.py`: Consultas GET optimizadas (read-only). Define tuplas `LIST_FIELDS`, `DETAIL_FIELDS` como SSoT.
   - `services.py`: Fachada que reexporta desde `business_service.py` para compatibilidad de imports existentes.
   - `api_mixins.py`: `<Modelo>ServiceMixin` que inyecta acceso estandarizado a Selectors, CRUDService y BusinessService.
- Todos los métodos son `@staticmethod` o `@classmethod` y stateless.
- El ViewSet hereda de `BaseTenantViewSet` y opcionalmente de un `<Modelo>ServiceMixin`.
- Prohibido invocar lógica de negocio desde templates, serializers o signals.
- Validación estricta de `empresa_id` y anti-IDOR en toda mutación.

**Stack obligatorio (prohibido sugerir alternativas sin autorización):**
1. Python + Django + DRF + django-tenants + PostgreSQL + Celery
2. HTMX + Vanilla JS ES6+ + Bootstrap 5 + Tabulator

## [ARCH] 2. Principios Generales de Arquitectura (Bounded Contexts & Zero-Trust)

1. **Comunicación Directa y Bounded Contexts (Gateway Directo):**
   - Frontend consume exclusivamente endpoints directos de cada app (`/api/v1/<app_name>/`).
   - El patrón Facade monolítico esta ELIMINADO. Los facades legacy en `core/api/v1/` NO deben usarse para nuevas integraciones.
2. **Aislamiento de `core` y Bridge al Esquema Publico:**
   - `apps/tenant/core` actua como UI Shell y como UNICO puente autorizado entre apps tenant y esquema publico.
   - PROHIBIDO para `core`: lógica de negocio de dominio, proxy de datos, orquestar APIs adyacentes, persistir datos de otras apps.
3. **Aislamiento de Datos SSoT:** Todo modelo DEBE heredar de `SintelTenantBaseModel` (inyecta `empresa_id` a nivel ORM).
4. **Idempotencia por Diseño:** Toda operación de mutación DEBE ser idempotente. BD respalda con constraints únicos.
5. **Centralización del Aprovisionamiento:** Onboarding de tenants es EXCLUSIVO de `apps/tenant/core`.

## [INFO] 3. Unica Fuente de Verdad Documental (SSoT)

1. **Documentación Global:** `documentacion/arquitectura_general.md` es la referencia suprema.
2. **Flujo por Aplicación:** Cada `apps/<app_name>/` DEBE contener `AUDITORIA_FLUJO_COMPLETO.md`.
3. **Gestión de Documentos:** Todos los `.md` de soporte residen en `documentacion/`.

## [BACKEND] 4. Capa de Datos y Optimización Backend (Zero Waste)

1. **Cero Archivos `.py` no Autorizados:** PROHIBIDO crear archivos fuera de la estructura de Service Layer. Requiere autorización explícita.
2. **Restricción de `apps/public/`:** PROHIBIDO modificar sin aprobación explícita (requiere RFC/Issue + etiqueta `needs-admin-approval`).
3. **Prohibición de `views.py` Tradicionales:** No usar el archivo `views.py` legacy para lógica de negocio.
4. **Multi-Tenant Estricto (Zero-Trust SaaS):** PROHIBIDO consultas a modelos sin filtrar por `empresa_id`.
5. **Optimización Estricta (Zero Waste):** PROHIBIDO `.all()` o `.filter()` sin encadenar `.only()` o `.defer()`.
6. **Desacoplamiento Operativo:** ForeignKeys a usuarios operativos DEBEN apuntar a `'perfil.TenantProfile'`, NUNCA a `settings.AUTH_USER_MODEL`.
7. **Cero Signals:** PROHIBIDO usar Django Signals para lógica de negocio. Todo en Service Layer.

## [CRUD-E2E] 5. Ciclo de Vida CRUD End-to-End

Flujo estrictamente unidireccional: UI → ViewSet → ServiceMixin → BusinessService → CRUDService → DB → Response

1. **UI:** DOM Shield obligatorio, payload via inputs ocultos.
2. **ViewSet:** SOLO enrutador HTTP. Delega a ServiceMixin.
3. **BusinessService:** Double Semantic Verification (IDOR prevention) + reglas de dominio.
4. **CRUDService:** UNICA capa con permisos de escritura. `@transaction.atomic` obligatorio en Maestro-Detalle.
5. **Response:** 200/201 (JSON o HTMX OOB Swap). Frontend usa `table.replaceData()` + `UIManager.notifySuccess`.

## [UI] 6. Interfaz de Usuario y Frontend (UI SSoT)

- **Templates tenant:** `apps/tenant/<app_name>/templates/tenant/<app_name>/` (prefijo `tenant/` OBLIGATORIO)
- **JS tenant:** `apps/tenant/<app_name>/static/<app_name>/js/`
- **Templates public:** `apps/public/<app_name>/templates/<app_name>/`
- **JS public:** `apps/public/<app_name>/static/<app_name>/js/`
- **Helpers globales:** `apps/tenant/core/static/core/js/common/` (UIManager, TabulatorFactory, notyf.init.js)

## [ARCHITECTURE] 7. Arquitectura Feature-Sliced Design (FSD)

**PRINCIPIO:** Cada modelo tiene su propio ecosistema completo e independiente.

1. **Templates:** `offcanvas_crear_{modelo}.html`, `offcanvas_editar_{modelo}.html`, `offcanvas_detalle_{modelo}.html`, `list_{modelo}.html`. Partials en `partials/`. PROHIBIDO: archivos monolíticos.
2. **JS:** `<app_name>.api.js` (SSoT endpoints). Subcarpeta `features/` con `{modelo}_list.js`, `{modelo}_editor.js`. PROHIBIDO: scripts compartidos entre modelos no relacionados.
3. **API Endpoints:** Offcanvas usan `hx-get` → `render-offcanvas/crear/`, `editar/`, `detalle/`.

## [WIZARD] 8. Patron Wizard y Flujo de Estado

1. **Asistente en Memoria:** Fase inicial de recolección NO guarda en BD.
2. **Traspaso por SessionStorage:** JS empaqueta payload JSON en `sessionStorage`, lanza por HTMX el Editor principal.

## [SHIELD] 9. Principio Zero Trust (Validación y Calculos UI)

1. **Validación Explícita:** Normalizar numéricamente (`parseFloat(value) || 0`) para evitar `NaN`.
2. **SSoT en Calculos:** Validaciones matemáticas en JS deben coincidir con tolerancia del backend.
3. **Serialización JSON Dura:** Formularios Maestro-Detalle envían JSON puro.

## [ALERT] 10. Manejo de Errores y Logging

1. **Logging Obligatorio:** Todo error debe incluir contexto: `[modulo:accion]`.
2. **Aislamiento de Errores UI:** Fallas DRF delegadas EXCLUSIVAMENTE a `UIManager.handleError`.

## [ASYNC] 11. Procesamiento Asíncrono, DLQ y Alto Rendimiento

1. **Desacoplamiento:** Tareas masivas, cálculos históricos, integraciones terceros DEBEN ir a Celery vía `.delay()`.
2. **Eficiencia en Workers:** Operar en lotes (batching). Evitar cargar estructuras masivas en RAM.
3. **DLQ:** Toda tarea Celery define `max_retries`. Al fallar definitivamente → `FailedTenantTask` en BD.

## [HTMX-ADVANCED] 12. Server-Driven UI y Out of Band Swaps (OOB)

1. **Reactividad:** Tabulator suscrito nativamente a respuestas HTMX (`HX-Trigger`).
2. **OOB:** POST exitoso que afecta elementos externos → `hx-swap-oob="true"` o `HX-Trigger`.

## [SaaS-DEFENSE] 13. Ciberseguridad Defensiva y Prevención IDOR

1. **Verificación Continua en DML:** Todo endpoint DML valida que entidades referenciadas pertenezcan al tenant autenticado.
2. **Implementacion via DSV:** Double Semantic Verification en `business_service.py` antes de persistir.
3. **Protección Horizontal:** PROHIBIDO confiar ciegamente en IDs de requests HTTP.

## [CORE-DB] 14. Herencia Obligatoria de Modelos SSoT

1. **SintelTenantBaseModel:** Todos los modelos tenant DEBEN heredar de `SintelTenantBaseModel` (`apps.tenant.core.models`).
2. **PROHIBIDO:** Heredar de `models.Model` directamente.
3. **Campos inyectados automáticamente:**
   - `empresa`: `ForeignKey('empresa.Empresa', on_delete=PROTECT, null=False, blank=False, db_index=True)`
   - `created_at`: `DateTimeField(auto_now_add=True, db_index=True)`
   - `updated_at`: `DateTimeField(auto_now=True, db_index=True)`
4. **Indices heredados:** `[empresa]` y `[empresa, -created_at]`. Modelos hijos pueden agregar índices adicionales.
5. **Protección en `save()`:** Lanza `ValueError` si `empresa_id` es `None`.
6. **UUID como Lookup Field:** `BaseTenantViewSet` define `lookup_field="uuid"`. NUNCA exponer PKs internos en URLs.

## [SECURITY] 15. Seguridad, Autenticacion JWT y Roles (Dual-Auth Pattern)

### 15.1. Dual-Auth Centralizado (JWT + Session)
- `BaseTenantViewSet` define `authentication_classes = [JWTAuthentication, SessionAuthentication]`. Todos los ViewSets heredan.
- PROHIBIDO sobrescribir `authentication_classes` en ViewSets hijos.
- Bridge Session-to-JWT: `GET /api/v1/core/auth/from-session/`

### 15.2. Configuracion JWT
- `djangorestframework-simplejwt[blacklist]>=5.3`
- ACCESS_TOKEN_LIFETIME: 15 min | REFRESH_TOKEN_LIFETIME: 7 días | ROTATE_REFRESH_TOKENS: True | HS256

### 15.3. Frontend JWT (`window.jwtAuth`)
```javascript
const token = window.jwtAuth?.getAccessToken?.();
if (token) { headers['Authorization'] = `Bearer ${token}`; }
```
- PROHIBIDO: `window.jwtAuth.token` (la propiedad `.token` NO existe).
- Asincrono (con auto-refresh): `await window.jwtAuth.getValidAccessToken()`

### 15.4. Jerarquia de Roles
- `TenantProfile.rol` es la UNICA SSoT de permisos dentro del tenant.
- Roles: `ADMIN` (CRUD total) | `OPERADOR` (lectura + escritura limitada) | `VISOR` (solo lectura)

### 15.5. Permisos Materializados (`apps/tenant/api/permissions.py`)
```python
permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
```
- PROHIBIDO importar permisos desde `apps/tenant/empresa/permissions.py` (wrapper legacy deprecado).

## [GOVERNANCE] 16. Reglas de Gobernanza por Aplicacion

1. **Modulos Privados:** Antes de cualquier modificación, se DEBE solicitar autorización explícita al USUARIO.
2. **Lectura Previa SSoT:** OBLIGATORIO leer `AUDITORIA_FLUJO_COMPLETO.md` antes de proponer cambios.

## [BRIDGE] 17. Aislamiento de Esquema Publico via Core Membership Bridge

1. **SSoT del Bridge:** `apps/tenant/core/services/membership.py` es la UNICA interfaz autorizada para que apps tenant consulten el esquema publico.
2. **PROHIBIDO:** Cualquier app tenant (excepto `core` y `api`) importe directamente desde `apps.public`.
3. **API Surface del Bridge:** `check_membership()`, `check_membership_exists()`, `check_admin_membership()`, `check_primary_admin()`, `get_user_role()`, `get_primary_domain()`, `verify_invitation()`
4. **Extension:** Nueva consulta al esquema publico → agregar al bridge. PROHIBIDO crear imports directos.

## [CONTAB] 18. Capa de Integracion Contable Centralizada (v3.5 — Modelo Pull / Extractores)

**PRINCIPIO:** Todo asiento contable es generado EXCLUSIVAMENTE por el `Contabilizador`. Ninguna app puede crear `AsientoContable` ni `MovimientoContable` directamente. Las apps fuente NO conocen ni dependen de `contabilidad`.

### 18.1. Paquete de Integracion (`apps/tenant/contabilidad/integracion/`)

| Modulo | Responsabilidad |
|---|---|
| `dtos.py` | DTOs inmutables (`@dataclass(frozen=True)`) — contrato entre apps fuente y Contabilizador |
| `contabilizador.py` | Orquestador unico — valida, resuelve cuentas, construye y persiste asientos atomicamente |
| `resolver.py` | Mapea (`tipo_transaccion` + `concepto`) a codigo PUC via `ReglaContable` por tenant |
| `validadores.py` | Validators stateless — cuadratura, periodo abierto, documento origen existe |
| `excepciones.py` | Jerarquia `ContabilidadError` y subclases |
| `extractores/base.py` | `AbstractExtractor` — interfaz comun (ver §18.3) |
| `extractores/gastos.py` | `ExtractorGastos` — extrae `DocumentoSoporte` pendientes |
| `extractores/inventario.py` | `ExtractorInventario` — extrae `MovimientoInventario` pendientes |
| `extractores/facturas.py` | `ExtractorFacturas` — extrae `Factura` ACEPTADA pendientes |
| `extractores/nomina.py` | `ExtractorNomina` — extrae `Devengo` aprobados pendientes |

### 18.2. DTOs — Contrato Inmutable

```python
TransaccionEconomica(
    tipo=TipoTransaccion.COMPRA_GASTO,
    fecha=date(2026, 5, 3),
    tercero=TerceroSnapshot(...),          # Snapshot, sin FK
    lineas=[LineaTransaccion(...)],
    documento_origen=DocumentoOrigen(...)  # Para idempotencia
)
LineaTransaccion(concepto='GASTO_OPERATIVO', monto=..., lado='DEBE')   # default='DEBE'
ImpuestoLinea(tipo='RETEFUENTE', valor=..., lado='HABER')              # default='HABER'
```

- **`lado`**: controla columna del asiento (`'DEBE'` o `'HABER'`). OBLIGATORIO para cuadratura.
- **Idempotencia**: `documento_origen` mapea a `AsientoContable.documento_origen_*`. Constraint UNIQUE en BD.
- **`empresa_id`**: PROHIBIDO pasarlo dentro del DTO — lo inyecta el `Contabilizador` desde su contexto.

### 18.3. Patron de Integracion — Modelo Pull (Extractores)

**Arquitectura:** `contabilidad` extrae activamente de apps fuente. Las apps fuente no conocen ni importan de `contabilidad`.

```python
# En apps/tenant/contabilidad/integracion/extractores/base.py
class AbstractExtractor(ABC):
    def __init__(self, empresa_id: int):
        self.empresa_id = empresa_id
        self.contabilizador = Contabilizador(empresa_id)

    @abstractmethod
    def extraer_pendientes(self) -> list[TransaccionEconomica]: ...

    def contabilizar_pendientes(self) -> dict:
        resultados = {'contabilizados': 0, 'errores': [], 'omitidos': 0}
        for dto in self.extraer_pendientes():
            try:
                self.contabilizador.contabilizar(dto)
                resultados['contabilizados'] += 1
            except Exception as e:
                resultados['errores'].append({'origen': str(dto.documento_origen), 'error': str(e)})
        return resultados
```

**Activacion:** Desde management commands (`manage.py backfill_asientos_gastos`) o Celery. Nunca desde ViewSets ni Signals.

### 18.4. Cuadratura Obligatoria (Ejemplo COMPRA_GASTO)

```
DEBE 51xxxx Gasto              [subtotal]
HABER 236540 Retefuente        [retefuente]  (si > 0)
HABER 236801 ReteICA           [reteica]     (si > 0)
HABER 233595 CXP Proveedor     [total neto]
TOTAL DEBE == TOTAL HABER == subtotal
```

### 18.5. Numero de Asiento — Formato Canonico

- Normal: `ASI-{YYYYMMDD}-{UUID8}` — generado por `Contabilizador._construir_asiento()`.
- Reversal: `RVER-{YYYYMMDD}-{UUID8}`.
- PROHIBIDO que el caller externo provea el numero.

### 18.6. Prohibiciones

- PROHIBIDO crear `AsientoContable`/`MovimientoContable` directamente desde ViewSets, Signals o apps fuente.
- PROHIBIDO que apps fuente importen desde `apps.tenant.contabilidad`.
- PROHIBIDO hardcodear codigos PUC en apps fuente — usar `cuenta_hint` o `ReglaContable`.
- PROHIBIDO usar `lado='DEBE'` para impuestos/retenciones (su natural es `'HABER'`).
- PROHIBIDO el patron Push — solo Pull (extractor de contabilidad lee app fuente).

## [MEMORY] 19. Memory Bank y Estado a Largo Plazo (MEMORY.md)

**REGLA OBLIGATORIA PARA TODOS LOS AGENTES Y EDITORES DE CODIGO (Claude Code, Cursor, Copilot, etc.)**

1. **Lectura Inicial Obligatoria:** Al iniciar cualquier sesion, tarea o contexto nuevo, el agente DEBE leer `MEMORY.md` en la raiz del proyecto.
2. **Proposito del Memory Bank:** `MEMORY.md` es la fuente canonica del estado actual del proyecto, ADRs recientes y progreso activo. Evita refactorizaciones ciclicas y perdida de contexto.
3. **Mantenimiento Continuo:** Al finalizar hitos importantes o implementar cambios estructurales, el agente DEBE actualizar `MEMORY.md` proactivamente.
4. **Inmutabilidad de ADRs:** Las decisiones listadas bajo ADRs en `MEMORY.md` no pueden alterarse sin autorizacion explicita del usuario principal.

## [KARPATHY] 21. Karpathy Coding Principles (Caution over Speed)

**PRINCIPIO FUNDAMENTAL:** Reducir errores comunes de LLMs mediante cautela, simplicidad y cambios quirurgicos.

1. **Pensar antes de Codificar**: No asumir. Si hay incertidumbre, preguntar. Explicitar suposiciones. Si hay multiples interpretaciones, presentarlas antes de elegir una.
2. **Simplicidad Primero**: Codigo minimo necesario. Prohibido crear abstracciones para codigo de un solo uso o agregar "flexibilidad" no solicitada. Si se puede hacer en 50 lineas en vez de 200, reescribir.
3. **Cambios Quirurgicos**: Tocar SOLO lo estrictamente necesario. No "mejorar" codigo adyacente ni refactorizar lo que no esta roto. Empatar el estilo existente. Si se detecta codigo muerto no relacionado, reportarlo pero NO borrarlo sin permiso.
4. **Ejecucion Basada en Objetivos**: Transformar tareas en metas verificables. Para tareas de multiples pasos, definir un plan: `1. [Paso] -> verificar: [check]`.

---

## Apendice A. Comandos de Operacion

- **Levantar:** `make up` / `docker compose up --build`
- **Migraciones tenants:** `make migrate-tenants`
- **Migraciones shared:** `make migrate-shared`
- **Tests:** `make test` | archivo: `make test-file FILE="path/to/test.py"`
- **Auditoria completa:** `make audit` (ruff + bandit + django check)
- **Lint + autofix:** `make ruff` (py3.12, line-length 100)
- **Compilacion Python (pre-PR):** `python -m py_compile archivo.py`
- **Seed reglas contables:** `python manage.py seed_reglas_contables`
- **Seed catalogo NIIF:** `python manage.py poblar_catalogo_niif`
- **Backfill asientos gastos:** `python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]`
