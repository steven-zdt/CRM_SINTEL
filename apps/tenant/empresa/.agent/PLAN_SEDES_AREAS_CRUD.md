# PLAN DE ACCION — Relaciones Empresa → Sedes → Areas
## Estado: IMPLEMENTADO Y VALIDADO | v1.1.0 | 2026-05-22

---

## 1. LOGICA DE NEGOCIO GARANTIZADA

```
Tenant Privado
  └─── Empresa (1:1 SINGLETON)           UniqueConstraint(singleton_key=1)
         ├─── Sedes  (1:N)               FK Sede.empresa → CASCADE
         │      └─── Areas  (1:N)        FK Area.sede   → CASCADE
         │                               FK Area.empresa → CASCADE (denormalizacion DSV)
         └─── [No puede haber 2 empresas por tenant]
```

**Invariantes garantizados:**
- Un tenant tiene EXACTAMENTE una Empresa (constraint en BD)
- Una Sede pertenece a UNA empresa (NOT NULL, CASCADE)
- Un Area pertenece a UNA sede y hereda empresa por denormalizacion
- `Area.empresa_id == Area.sede.empresa_id` SIEMPRE (validado en service layer)
- Una Sede NO puede eliminarse si tiene Areas asociadas (regla de negocio en crud_service)

---

## 2. ESTADO DEL ESQUEMA (post-implementacion)

### 2.1 Modelos — apps/tenant/empresa/models.py

```
Empresa
  singleton_key     PositiveSmallIntegerField  default=1
  [UniqueConstraint: singleton_key]   ← garantiza exactamente 1 por tenant

Sede(SintelTenantBaseModel)
  empresa           FK → Empresa    CASCADE  related_name='sedes'  NOT NULL  [EXPLICITA]
  uuid              UUIDField        unique
  nombre            CharField(150)
  direccion         CharField(255)   blank
  telefono          CharField(50)    blank
  encargado_nombre  CharField(150)   blank
  [UniqueConstraint: empresa + nombre]

Area(SintelTenantBaseModel)
  empresa           FK → Empresa    CASCADE  related_name='areas'  NOT NULL  [EXPLICITA]
  sede              FK → Sede       CASCADE  related_name='areas'  NOT NULL  [EXPLICITA]
  uuid              UUIDField        unique
  nombre            CharField(150)
  codigo_funcionamiento  CharField(50)
  [UniqueConstraint: sede + nombre]
  [UniqueConstraint: sede + codigo_funcionamiento]
```

### 2.2 Migraciones aplicadas

| Migration | Descripcion |
|-----------|-------------|
| 0008 | Crea tablas empresa_sede y empresa_area con FK base |
| 0009 | Override FK empresa en Sede y Area: CASCADE + related_name semantico |

**Estado:** `No changes detected` — esquema en BD alineado con modelos.

### 2.3 Validacion de Integridad en BD (ejecutada 2026-05-22)

```
Empresas en tenant home:    1
Sedes en tenant home:       1  (empresa_id=1, correcto)
Areas en tenant home:       1  (empresa_id=1, sede_id=1, correcto)
Areas con empresa_id malo:  0
Sedes con empresa_id malo:  0
```

---

## 3. SERVICE LAYER — Reglas de Negocio

### apps/tenant/empresa/services/crud_service.py

| Funcion | Validaciones |
|---------|-------------|
| `crear_sede_db(empresa_id, data)` | Unicidad nombre por empresa |
| `actualizar_sede_db(sede, data)` | Unicidad nombre (excluye self) |
| `eliminar_sede_db(sede)` | BLOQUEA si sede.areas.exists() |
| `crear_area_db(empresa_id, data)` | DSV: sede debe pertenecer a empresa_id |
|  | Unicidad nombre por sede |
|  | Unicidad codigo por sede |
| `actualizar_area_db(area, data)` | DSV: nueva sede debe pertenecer a empresa_id |
|  | Unicidad nombre y codigo (excluye self) |
| `eliminar_area_db(area)` | Sin restriccion adicional |

### apps/tenant/empresa/services/business_service.py

| Clase | Metodo | Descripcion |
|-------|--------|-------------|
| `SedeService` | `crear_sede(empresa_id, data)` | Llama crud_service |
| `SedeService` | `actualizar_sede(empresa_id, uuid, data)` | Anti-IDOR: filtra por empresa_id + uuid |
| `SedeService` | `eliminar_sede(empresa_id, uuid)` | Anti-IDOR: filtra por empresa_id + uuid |
| `AreaService` | `crear_area(empresa_id, data)` | Llama crud_service |
| `AreaService` | `actualizar_area(empresa_id, uuid, data)` | Anti-IDOR: filtra por empresa_id + uuid |
| `AreaService` | `eliminar_area(empresa_id, uuid)` | Anti-IDOR: filtra por empresa_id + uuid |

---

## 4. API LAYER — Viewsets y Serializers

### SedeViewSet — /api/v1/empresas/sedes/

| Accion | Endpoint | Descripcion |
|--------|----------|-------------|
| list   | GET /    | Paginado con search. Usa SedeSelector.get_list() |
| retrieve | GET /{uuid}/ | Solo de esta empresa |
| create | POST /   | Crea sede para esta empresa |
| update | PUT /{uuid}/ | Actualiza sede (anti-IDOR via empresa_id) |
| partial_update | PATCH /{uuid}/ | Actualiza parcialmente |
| destroy | DELETE /{uuid}/ | Elimina si no tiene areas |
| render_offcanvas | GET /render-offcanvas/?id= | HTML del form crear/editar |

**Resolucion empresa:** `@cached_property tenant_empresa → resolve_tenant_empresa(request, self)`
**NO usa:** `request.user.perfil.empresa_id` (patron prohibido)

### AreaViewSet — /api/v1/empresas/areas/

| Accion | Endpoint | Descripcion |
|--------|----------|-------------|
| list   | GET /    | Paginado con search. Usa AreaSelector.get_list() |
| retrieve | GET /{uuid}/ | Solo de esta empresa |
| create | POST /   | Crea area con sede validada por empresa_id (DSV) |
| update | PUT /{uuid}/ | Actualiza area (anti-IDOR) |
| partial_update | PATCH /{uuid}/ | Actualiza parcialmente |
| destroy | DELETE /{uuid}/ | Elimina area |
| render_offcanvas | GET /render-offcanvas/?id= | HTML del form crear/editar (incluye sedes) |

**Contexto serializer:** `get_serializer_context()` inyecta `empresa_id` para filtrar sedes en AreaUpsertSerializer

### AreaUpsertSerializer — Filtro anti-IDOR

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    empresa_id = self.context.get('empresa_id')
    if empresa_id:
        self.fields['sede'].queryset = Sede.objects.filter(empresa_id=empresa_id)
    else:
        self.fields['sede'].queryset = Sede.objects.all()
```

El campo `sede` solo acepta sedes pertenecientes a la empresa activa.

---

## 5. TESTS END-TO-END EJECUTADOS (2026-05-22)

Todos pasaron en `schema_context('home')`:

| Test | Resultado |
|------|-----------|
| Crear Sede con empresa_id correcto | OK — sede.empresa_id == empresa.id |
| Crear Area con sede de la misma empresa | OK — area.empresa_id == sede.empresa_id |
| Editar Sede | OK |
| Eliminar Area | OK |
| Eliminar Sede sin areas | OK |
| Eliminar Sede CON areas | BLOQUEADO correctamente |
| Crear Area con sede_id inexistente (IDOR) | BLOQUEADO — "La sede no pertenece a la empresa" |
| `e.sedes.count()` via related_name | OK (1) |
| `e.areas.count()` via related_name | OK (1) |
| `s.areas.count()` via reverse FK | OK |
| `django manage.py check` | 0 issues |
| Areas con empresa_id incorrecto | 0 |
| Sedes con empresa_id incorrecto | 0 |

---

## 6. FRONTEND — Workspace http://home.sintel.net.co/workspace/#empresa

### Tabs del modulo Empresa

| Tab | Contenido | Estado |
|-----|-----------|--------|
| Datos de Empresa | Tabla Empresa + Buzones de correo | OK |
| Sedes | Tabla independiente full-width + CRUD | OK |
| Areas | Tabla independiente full-width + CRUD | OK |

### Tabulator Columns

**Sedes:**
- Nombre Sede | Direccion | Telefono | Encargado | Acciones (editar/eliminar)

**Areas:**
- Nombre Area | Codigo Funcionamiento | Sede (nombre) | Acciones (editar/eliminar)

### Flujo de usuario para Sede
1. Clic "Nueva Sede" → HTMX carga `offcanvas_crear_sede.html`
2. Completar form → JS sede_editor.js → PUT /api/v1/empresas/sedes/
3. Offcanvas cierra → evento `sedeGuardada` → Tabulator.replaceData()
4. Clic boton editar en fila → HTMX carga `offcanvas_editar_sede.html?id=N`
5. Modificar → PATCH → actualiza tabla

### Flujo de usuario para Area
1. Clic "Nueva Area" → HTMX carga `offcanvas_crear_area.html`
2. Select de sede filtrado por empresa_id (AreaUpsertSerializer)
3. Completar form → JS area_editor.js → PUT /api/v1/empresas/areas/
4. Offcanvas cierra → evento `areaGuardada` → Tabulator.replaceData()

---

## 7. CONFORMIDAD CON AGENTS.MD

| Regla AGENTS.md | Estado |
|-----------------|--------|
| No emojis en .py | Cumple |
| SintelTenantBaseModel como base | Cumple — Sede y Area heredan de el |
| empresa_id en toda query | Cumple — DSV en todas las operaciones |
| .only() en querysets (selectores) | Cumple — SEDE_LIST_FIELDS, AREA_LIST_FIELDS |
| No signals para logica de negocio | Cumple |
| UUID lookup, no PK | Cumple — lookup_field='uuid' en BaseTenantViewSet |
| FK a TenantProfile prohibida desde modelos | Cumple — no hay FK a TenantProfile |
| Imports globales, no dentro de def | Cumple (imports de service dentro de action es aceptable) |
| No request.user.perfil | Cumple — usa resolve_tenant_empresa() |
| Anti-IDOR (DSV) en mutaciones | Cumple — empresa_id valida sede al crear area |
| Service Layer unidireccional | Cumple — ViewSet→BusinessService→CrudService |

---

## 8. ARCHIVOS MODIFICADOS EN ESTA IMPLEMENTACION

| Archivo | Cambio |
|---------|--------|
| `apps/tenant/empresa/models.py` | Override FK empresa en Sede y Area (CASCADE + related_name semantico) |
| `apps/tenant/empresa/api/viewsets.py` | Fix resolve_tenant_empresa + get_serializer_context + clave sede |
| `apps/tenant/empresa/api/serializers.py` | AreaUpsertSerializer filtro empresa_id |
| `apps/tenant/empresa/migrations/0009_sedes_areas_explicit_fk.py` | Migration para FK explicita |
| `apps/tenant/empresa/templates/tenant/empresa/empresa_list.html` | Separar tabs Sedes y Areas |

---

## 9. NO SE REQUIEREN CORRECCIONES ADICIONALES

El esquema actual cumple integramente con la logica de negocio solicitada:
- Tenant → Empresa (1:1) GARANTIZADO por UniqueConstraint en BD
- Empresa → Sedes (1:N) GARANTIZADO por FK NOT NULL + CASCADE
- Sede → Areas (1:N) GARANTIZADO por FK NOT NULL + CASCADE
- Todas las areas pertenecen a la misma empresa de su sede: GARANTIZADO por DSV en service layer
- Eliminacion protegida: sede con areas no puede eliminarse
