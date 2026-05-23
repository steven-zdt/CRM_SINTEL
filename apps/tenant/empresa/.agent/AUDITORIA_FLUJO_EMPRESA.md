# AUDITORIA Y SSoT: Modulo Empresa

**Version:** 3.10.2
**Estado:** PRODUCTION READY
**Ubicacion:** `apps/tenant/empresa/`
**Ultima Auditoria:** 2026-05-22

---

## Documentacion Especializada (SSoT)

| Documento | Descripcion |
|:---|:---|
| [Arquitectura y Microtareas](docs/empresa_microtasks_architecture.md) | Desglose atomico de responsabilidades y tareas tecnicas. |
| [Mapas de Flujo](docs/empresa_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [Logica de Negocio](docs/empresa_business_logic.md) | SSoT de reglas, validaciones y calculos. |
| [Plan CRUD Sedes-Areas](PLAN_SEDES_AREAS_CRUD.md) | Plan de accion v1.1 — relaciones, bugs corregidos, tests. |
| [Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones. |

---

## Responsabilidades Core

1. **Patron Singleton**: Un unico registro de Empresa por tenant (`UniqueConstraint(singleton_key=1)` en BD).
2. **Identidad Legal (NIT)**: Gestion del NIT y Digito de Verificacion (SSoT para Facturacion).
3. **Sedes (1:N)**: Sucursales fisicas de la empresa. Cada sede pertenece a una empresa.
4. **Areas (1:N por Sede)**: Departamentos operativos dentro de una sede. Cada area pertenece a una sede y hereda empresa.
5. **MailInboxConfig**: Credenciales IMAP/SMTP para ingesta automatica de documentos.
6. **SSoT de Emisor**: Provisiona datos maestros a Facturas, Nomina y Contabilidad via Selectors.

---

## Arquitectura de Modelos (v3.10.2)

### Jerarquia de Relaciones

```
Tenant (esquema PostgreSQL)
  └── Empresa (SINGLETON — UniqueConstraint singleton_key=1)
        ├── sedes   (related_name='sedes')   1:N
        │     └── areas  (related_name='areas' via Sede)  1:N
        └── areas   (related_name='areas')   1:N  [acceso directo]
```

### Modelo Empresa

- **Tabla:** `empresa_empresa`
- **Singleton:** `singleton_key=1` con UniqueConstraint en BD
- **FK self-referencial:** `empresa` nullable (solo para seed inicial de onboarding)
- **Propiedades:** `sedes` → `Sede.objects.filter(empresa_id=self.id)`, `areas` → igual
- **Campos clave:** `razon_social`, `nit`, `dv`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `moneda`, `logo`

### Modelo Sede (v3.10 — FK explicita)

- **Tabla:** `empresa_sede`
- **FK empresa:** `on_delete=CASCADE`, `related_name='sedes'`, NOT NULL — **declaracion explicita** (override del base class)
- **UUID lookup:** `uuid` unique, `db_index=True`
- **Constraint:** `unique_sede_nombre_per_empresa` — `(empresa, nombre)`
- **Campos:** `nombre`, `direccion`, `telefono`, `encargado_nombre`

### Modelo Area (v3.10 — FK explicita)

- **Tabla:** `empresa_area`
- **FK empresa:** `on_delete=CASCADE`, `related_name='areas'`, NOT NULL — **declaracion explicita**
- **FK sede:** `on_delete=CASCADE`, `related_name='areas'`, NOT NULL — explicita
- **UUID lookup:** `uuid` unique, `db_index=True`
- **Constraints:**
  - `unique_area_nombre_per_sede` — `(sede, nombre)`
  - `unique_area_codigo_per_sede` — `(sede, codigo_funcionamiento)`
- **Campos:** `nombre`, `codigo_funcionamiento`

### Modelo MailInboxConfig

- **Tabla:** auto-generada por SintelTenantBaseModel
- **Campos IMAP:** `imap_host`, `imap_port`, `imap_ssl`, `imap_starttls`, `imap_username`, `imap_password`, `imap_mailbox`, `imap_mark_as_seen`, `imap_max_attachment_mb`
- **Campos SMTP:** `smtp_host`, `smtp_port`, `smtp_ssl`, `smtp_starttls`, `smtp_username`, `smtp_password`
- **Proveedor:** `provider` choices `('custom', 'gmail')`
- **Estado:** `is_active`

---

## Migraciones

| Migration | Descripcion |
|-----------|-------------|
| 0001 | Initial — tabla empresa_empresa |
| 0002–0007 | Campos adicionales, empresa FK, owner_email |
| 0008 | Crea empresa_sede y empresa_area (FK base class implicita) |
| 0009 | Override FK empresa en Sede y Area: CASCADE + related_name semantico |

**Estado actual:** `No changes detected` — modelos sincronizados con BD.

---

## Service Layer

### apps/tenant/empresa/services/selectors.py

| Clase | Metodo | Descripcion |
|-------|--------|-------------|
| `EmpresaSelector` | `get_list(search=None)` | Listado singleton optimizado |
| `EmpresaSelector` | `get_detail()` | Detalle completo |
| `EmpresaSelector` | `get_by_id(pk)` | Por PK |
| `SedeSelector` | `get_list(empresa_id, search=None)` | Listado con SEDE_LIST_FIELDS |
| `SedeSelector` | `get_by_uuid(empresa_id, uuid)` | Anti-IDOR por UUID |
| `AreaSelector` | `get_list(empresa_id, search=None)` | Listado con select_related('sede') |
| `AreaSelector` | `get_by_uuid(empresa_id, uuid)` | Anti-IDOR por UUID |

### apps/tenant/empresa/services/crud_service.py

| Funcion | Validaciones |
|---------|-------------|
| `crear_sede_db(empresa_id, data)` | Unicidad nombre por empresa |
| `actualizar_sede_db(sede, data)` | Unicidad nombre (excluye self) |
| `eliminar_sede_db(sede)` | BLOQUEA si `sede.areas.exists()` |
| `crear_area_db(empresa_id, data)` | DSV: sede debe pertenecer a empresa_id; unicidad nombre+codigo |
| `actualizar_area_db(area, data)` | DSV: nueva sede pertenece a empresa_id; unicidad (excluye self) |
| `eliminar_area_db(area)` | Sin restriccion adicional |

### apps/tenant/empresa/services/business_service.py

| Clase | Descripcion |
|-------|-------------|
| `EmpresaService` | `get_or_create_empresa`, `update_empresa`, `has_active_profiles` |
| `SedeService` | `crear_sede`, `actualizar_sede` (anti-IDOR), `eliminar_sede` (anti-IDOR) |
| `AreaService` | `crear_area`, `actualizar_area` (anti-IDOR), `eliminar_area` (anti-IDOR) |

---

## API Layer

### Endpoints

| Endpoint | ViewSet | Descripcion |
|----------|---------|-------------|
| `/api/v1/empresas/` | `EmpresaViewSet` | CRUD singleton; GET/PATCH/PUT solo ADMIN |
| `/api/v1/empresas/gestor-offcanvas/` | `EmpresaViewSet.render_offcanvas` | HTML offcanvas crear/editar |
| `/api/v1/empresas/sedes/` | `SedeViewSet` | CRUD sedes paginado |
| `/api/v1/empresas/sedes/render-offcanvas/?id=N` | `SedeViewSet.render_offcanvas` | HTML offcanvas crear/editar sede |
| `/api/v1/empresas/areas/` | `AreaViewSet` | CRUD areas paginado |
| `/api/v1/empresas/areas/render-offcanvas/?id=N` | `AreaViewSet.render_offcanvas` | HTML offcanvas crear/editar area (incluye sedes) |
| `/api/v1/empresas/mail-inbox-config/` | `MailInboxConfigViewSet` | CRUD buzones |
| `/api/v1/empresas/mail-inbox-config/test-connection/` | `test_connection` | Probar IMAP |
| `/api/v1/empresas/mail-inbox-config/render-offcanvas/` | `render_offcanvas` | HTML offcanvas buzon |

### Resolucion de Empresa en ViewSets (v3.10 — patron correcto)

```python
# CORRECTO — todos los ViewSets usan este patron:
@cached_property
def tenant_empresa(self):
    return resolve_tenant_empresa(self.request, self)

def get_empresa(self):
    return self.tenant_empresa

# PROHIBIDO — patron que falla con JWT:
# empresa_id = request.user.perfil.empresa_id
```

### SedeViewSet y AreaViewSet — get_serializer_context

`AreaViewSet` inyecta `empresa_id` en el contexto del serializer para que `AreaUpsertSerializer` filtre el queryset de sedes:

```python
def get_serializer_context(self):
    context = super().get_serializer_context()
    context['empresa_id'] = self.get_empresa().id
    return context
```

---

## Serializers

| Serializer | Uso | Notas |
|-----------|-----|-------|
| `EmpresaListSerializer` | Tabulator list | read_only, exposicion minima |
| `EmpresaDetailSerializer` | retrieve/update | incluye logo URL |
| `EmpresaUpsertSerializer` | create/update | NormalizationMixin, singleton validation |
| `SedeListSerializer` | Tabulator list | campos: id, uuid, nombre, direccion, telefono, encargado_nombre |
| `SedeDetailSerializer` | retrieve | mismos campos + timestamps |
| `SedeUpsertSerializer` | create/update | valida nombre obligatorio |
| `AreaListSerializer` | Tabulator list | incluye `sede_nombre`, `sede_uuid` via source |
| `AreaDetailSerializer` | retrieve | mismos campos |
| `AreaUpsertSerializer` | create/update | `sede` filtrado por `empresa_id` del context (anti-IDOR) |
| `MailInboxConfigListSerializer` | Tabulator list | oculta credenciales |
| `MailInboxConfigDetailSerializer` | retrieve/update | expone campos IMAP seguros |

### AreaUpsertSerializer — Filtro Anti-IDOR (v3.10)

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    empresa_id = self.context.get('empresa_id')
    if empresa_id:
        self.fields['sede'].queryset = Sede.objects.filter(empresa_id=empresa_id)
    else:
        self.fields['sede'].queryset = Sede.objects.all()
```

---

## Frontend (Feature-Sliced Architecture)

### Estructura de Assets

```
apps/tenant/empresa/static/empresa/js/
  empresa.api.js              # Legacy API wrapper
  features/
    empresa_list.js           # Tabulator Empresa
    empresa_editor.js         # Editor Empresa (offcanvas)
    sede_list.js              # Tabulator Sedes (v2.61)
    sede_editor.js            # Editor Sedes
    area_list.js              # Tabulator Areas (v2.61)
    area_editor.js            # Editor Areas
    mailinboxconfig_list.js   # Tabulator MailInbox (v4.2)
    mailinboxconfig_editor.js # Editor MailInbox (v4.2)
```

### Patron Offcanvas Seguro (v3.9.0 — obligatorio)

**NUNCA usar `bootstrap.Offcanvas.getOrCreateInstance(el).show()` despues de HTMX swap.**
Acumula backdrops huerfanos → pantalla negra en el segundo intento.

```javascript
// CORRECTO — presente en todos los *_list.js del modulo:
function mostrarOffcanvasSeguro(el) {
    if (!el || !w.bootstrap || !w.bootstrap.Offcanvas) return;
    d.querySelectorAll('.offcanvas-backdrop').forEach(function(b) { b.remove(); });
    d.body.classList.remove('overflow-hidden', 'modal-open');
    var prev = bootstrap.Offcanvas.getInstance(el);
    if (prev) prev.dispose();
    new bootstrap.Offcanvas(el).show();
}
```

**En templates**, usar `hx-on::after-settle` (no `after-request`) con el helper global:
```html
hx-on::after-settle="if(event.detail.successful !== false){ sintelAbrirOffcanvasEmpresa('offcanvas-sede'); }"
```

`sintelAbrirOffcanvasEmpresa` esta definido en `empresa_list.html` (inline script).

### Parametro correcto para render-offcanvas

Los botones editar en Tabulator usan `data-id="${rowData.id}"` (integer PK) y llaman `?id=${id}`.
Los botones eliminar usan `data-uuid="${rowData.uuid}"` y llaman `DELETE /${uuid}/`.

```javascript
// sede_list.js y area_list.js — CORRECTO:
<button class="btn-edit-sede" data-id="${id}">   // editar usa PK
<button class="btn-delete-sede" data-uuid="${uuid}">  // eliminar usa UUID
await htmx.ajax('GET', `/api/v1/empresas/sedes/render-offcanvas/?id=${id}`, ...)
```

### Templates Offcanvas (FSD — un template por accion)

```
apps/tenant/empresa/templates/tenant/empresa/
  empresa_list.html               # Workspace principal — 3 tabs: Empresa | Sedes | Areas
  offcanvas_form.html             # Empresa crear/editar
  offcanvas_crear_sede.html       # Sede — crear
  offcanvas_editar_sede.html      # Sede — editar (preloaded desde context)
  offcanvas_detalle_sede.html     # Sede — solo lectura
  offcanvas_crear_area.html       # Area — crear (select sedes)
  offcanvas_editar_area.html      # Area — editar (select sedes, pre-seleccion)
  offcanvas_detalle_area.html     # Area — solo lectura
  offcanvas_crear_mailinboxconfig.html    # MailInbox — crear
  offcanvas_editar_mailinboxconfig.html   # MailInbox — editar
  offcanvas_detalle_mailinboxconfig.html  # MailInbox — solo lectura
  assets_empresa.html             # Carga ordenada de scripts JS
  mailinbox_list.html             # Tabla MailInbox (incluida en tab Empresa)
```

### Tabs del Workspace (empresa_list.html)

| Tab | ID | Contenido |
|-----|----|-----------|
| Datos de Empresa | `#subtab-datos` | Grid Empresa + MailInboxConfig |
| Sedes | `#subtab-sedes` | Grid Sedes full-width + CRUD |
| Areas | `#subtab-areas` | Grid Areas full-width + CRUD |

Los tabs de Sedes y Areas tienen listener `shown.bs.tab` que llama `table.redraw(true)` para corregir columnas Tabulator en contenedores ocultos.

---

## Invariantes de Negocio Garantizados

| Invariante | Mecanismo |
|------------|-----------|
| 1 empresa por tenant | `UniqueConstraint(singleton_key=1)` en BD |
| Sede pertenece a 1 empresa | FK `Sede.empresa NOT NULL CASCADE` |
| Area pertenece a 1 sede | FK `Area.sede NOT NULL CASCADE` |
| Area hereda empresa de su sede | `crear_area_db` valida `sede.empresa_id == empresa_id` |
| Sede con areas no se puede eliminar | `eliminar_sede_db` verifica `sede.areas.exists()` |
| Nombre de sede unico por empresa | `UniqueConstraint(empresa, nombre)` en BD |
| Nombre de area unico por sede | `UniqueConstraint(sede, nombre)` en BD |
| Codigo funcionamiento unico por sede | `UniqueConstraint(sede, codigo_funcionamiento)` en BD |
| Sede solo ve sedes de su empresa en form | `AreaUpsertSerializer` filtra queryset por `empresa_id` |

---

## Bugs Corregidos en v3.10 (2026-05-22)

| # | Archivo | Bug | Impacto | Fix |
|---|---------|-----|---------|-----|
| B1 | `viewsets.py` SedeViewSet/AreaViewSet | `request.user.perfil.empresa_id` — falla con JWT | 500 en GET /sedes/ y /areas/ | Reemplazado por `resolve_tenant_empresa()` + `@cached_property tenant_empresa` |
| B2 | `viewsets.py` SedeViewSet/AreaViewSet | `SedeSelector.obtener_sedes_empresa()` no existe | 500 en list y render-offcanvas | Correcto: `SedeSelector.get_list()`, `AreaSelector.get_list()` |
| B3 | `viewsets.py` AreaViewSet.create/update | Pasa clave `sede_id` pero `crud_service` espera `sede` | Area creation/update siempre fallaba con 400 | Cambiado a clave `sede` |
| B4 | `sede_list.js`, `area_list.js` | `?uuid=${uuid}` pero viewset lee `?id=` | Editar sede/area cargaba form vacío (modo crear) | Cambiado a `data-id` y `?id=${id}` |
| B5 | `sede_list.js`, `area_list.js`, `empresa_list.js`, `mailinboxconfig_list.js`, `mailinboxconfig_editor.js` | `getOrCreateInstance(el).show()` tras HTMX swap | `offcanvas.js:116 Cannot read properties of null (reading 'scroll')` + pantalla negra 2do intento | Reemplazado por `mostrarOffcanvasSeguro(el)` en todos los archivos |
| B6 | `empresa_list.html` buttons | `hx-on::after-request` dispara ANTES del swap DOM | Offcanvas no encontrado o elemento incorrecto | Cambiado a `hx-on::after-settle` + `sintelAbrirOffcanvasEmpresa()` |
| B7 | `models.py` Sede/Area | FK `empresa` implicita via base class, related_name generico (`empresa_sede_related`) | `e.empresa_sede_related` falla, propiedades fragiles | Override explicito: `related_name='sedes'`/`'areas'`, CASCADE — migration 0009 |

---

## Conformidad AGENTS.md

| Regla | Estado |
|-------|--------|
| No emojis en .py | Cumple |
| SintelTenantBaseModel como base | Cumple |
| empresa_id en toda query | Cumple — DSV via `get_empresa().id` |
| `.only()` en querysets | Cumple — SEDE_LIST_FIELDS, AREA_LIST_FIELDS |
| No signals para logica negocio | Cumple |
| UUID lookup en URLs | Cumple — `lookup_field='uuid'` |
| No `request.user.perfil` | Cumple — usa `resolve_tenant_empresa()` |
| Anti-IDOR en serializers | Cumple — `AreaUpsertSerializer` filtra por empresa_id |
| FSD — template por accion | Cumple — 11 templates independientes |
| JS por modelo separado | Cumple — 8 archivos JS feature-sliced |
| Imports globales, no dentro de def | Cumple |
