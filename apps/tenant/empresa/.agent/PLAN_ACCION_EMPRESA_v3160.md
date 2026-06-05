# Plan de Accion — Auditoria App Empresa v3.16.0

**Fecha:** 2026-06-01
**Auditor:** Claude Code (auditoria automatica)
**Scope:** `apps/tenant/empresa/` — migraciones, backend, frontend

---

## Resumen Ejecutivo

| Categoria | Critico | Medio | Bajo | Estado |
|---|---|---|---|---|
| Migraciones | 0 | 0 | 0 | OK — sin pendientes |
| Backend | 0 | 2 | 1 | RESUELTO 2026-06-01 |
| Frontend | 2 | 1 | 2 | RESUELTO 2026-06-01 |

---

## Estado de Migraciones

**Ultima migracion aplicada:** `0009_sedes_areas_explicit_fk`

| # | Migracion | Contenido |
|---|---|---|
| 0001 | initial | Modelos base Empresa |
| 0002 | empresa_empresa | FK nullable a si misma |
| 0003 | mailinboxconfig_empresa | Agregado MailInboxConfig |
| 0004 | empresa_activa_ciudad_... | activa, ciudad, departamento, telefono |
| 0005 | alter_empresa_telefono | Modificacion telefono |
| 0006 | alter_empresa_empresa | FK empresa revision |
| 0007 | empresa_owner_email | owner_email (auto-admin elevation) |
| 0008 | sede_area_indices | Sede + Area + indices |
| 0009 | sedes_areas_explicit_fk | FK explicitos + related_names + CASCADE |

**Resultado:** No hay migraciones pendientes. Ninguna accion requerida.

---

## Hallazgos por Item

---

### EMP-BACK-01 — §30 Preventivo: AREA_LIST_FIELDS contiene traversals ORM

**Prioridad:** PREVENTIVO (no falla hoy, pero viola §30)
**Archivo:** [apps/tenant/empresa/services/selectors.py](../services/selectors.py)

**Situacion actual:**
```python
AREA_LIST_FIELDS = (
    "id", "uuid",
    "sede__id",     # traversal ORM — valida en .only() pero NO en Meta.fields
    "sede__uuid",   # traversal ORM
    "sede__nombre", # traversal ORM
    "nombre", "codigo_funcionamiento", "created_at", "updated_at",
)
AREA_DETAIL_FIELDS = AREA_LIST_FIELDS
```

**Por que no falla hoy:** Los serializers `AreaListSerializer` y `AreaDetailSerializer` usan campos declarados explicitamente (`sede_nombre = CharField(source='sede.nombre')`), NO la constante `AREA_LIST_FIELDS` en `Meta.fields`. La constante solo se usa en `.only()`.

**Por que es un riesgo:** Viola §30. Si alguien en el futuro hace `fields = tuple(AREA_LIST_FIELDS)` en un nuevo serializer (patron que ya existe en facturas y proveedores), el error `ImproperlyConfigured: Field name sede__uuid is not valid` aparece en produccion.

**Fix requerido:** Aplicar Zero-Collision Pattern:

```python
# NUEVO — services/selectors.py

AREA_LIST_FIELDS = (
    "id", "uuid",
    "sede_id",              # FK id autogenerado — valido en AMBOS contextos
    "nombre", "codigo_funcionamiento", "created_at", "updated_at",
)
AREA_DETAIL_FIELDS = AREA_LIST_FIELDS  # mismo conjunto

# Traversals ORM — SOLO para .only(), nunca en Meta.fields
_SEDE_AREA_TRAVERSALS = ("sede__id", "sede__uuid", "sede__nombre")

class AreaSelector:
    @staticmethod
    def get_list(empresa_id, search=None):
        qs = Area.objects.filter(
            empresa_id=empresa_id
        ).select_related('sede').only(       # select_related ya existe
            *AREA_LIST_FIELDS,
            *_SEDE_AREA_TRAVERSALS,          # inline — no contaminan Meta.fields
        )
        ...

    @staticmethod
    def get_by_uuid(empresa_id, uuid):
        return Area.objects.filter(
            empresa_id=empresa_id, uuid=uuid
        ).select_related('sede').only(
            *AREA_DETAIL_FIELDS,
            *_SEDE_AREA_TRAVERSALS,
        ).first()
```

---

### EMP-BACK-02 — AreaUpsertSerializer.sede usa PrimaryKeyRelatedField (PK entero)

**Prioridad:** MEDIA
**Archivo:** [apps/tenant/empresa/api/serializers.py](../api/serializers.py) linea 590

**Situacion actual:**
```python
class AreaUpsertSerializer(serializers.ModelSerializer):
    sede = serializers.PrimaryKeyRelatedField(
        queryset=Sede.objects.none(), required=True
    )
```

**Templates (`offcanvas_crear_area.html`, `offcanvas_area.html`):**
```html
<select id="area-sede" name="sede">
  {% for s in sedes %}
    <option value="{{ s.id }}">{{ s.nombre }}</option>  {# envia PK entero #}
  {% endfor %}
</select>
```

**area_editor.js linea 54:**
```javascript
sede: sedeVal ? parseInt(sedeVal, 10) : null,  // envia PK entero al backend
```

**Por que es un problema:** El patron SINTEL es UUID en todas las referencias externas (AGENTS.md §27). Usar PK entero expone IDs internos y crea inconsistencia con el resto del sistema donde `sede` se identifica por UUID.

**Fix requerido — 3 archivos:**

1. **serializers.py** — cambiar a `UUIDOrPKRelatedField` (acepta ambos):
```python
from apps.tenant.empresa.api.serializers import UUIDOrPKRelatedField  # si existe
# o copiar el patron de otros serializers

sede = UUIDOrPKRelatedField(
    queryset=Sede.objects.none(),
    required=True,
    help_text='UUID de la sede'
)
```

2. **Templates** — `value="{{ s.uuid }}"`:
```html
<option value="{{ s.uuid }}">{{ s.nombre }}</option>
```

3. **area_editor.js** — eliminar `parseInt`:
```javascript
sede: sedeVal || null,  // UUID directo — sin parseInt
```

---

### EMP-BACK-03 — empresa.api.js DEPRECATED presente en filesystem

**Prioridad:** BAJA (cleanup)
**Archivo:** [apps/tenant/empresa/static/empresa/js/empresa.api.js](../static/empresa/js/empresa.api.js)

El archivo esta marcado como `DEPRECATED v2.40` y documentado en `INFORME_ESTRUCTURA.md` como archivo de referencia historica. No se carga en ningun template activo.

**Fix requerido:** Eliminar o mover a `static/empresa/js/_deprecated/`.

---

### EMP-FRONT-01 — `parseInt(sedeVal, 10)` en area_editor.js — AGENTS.md §27

**Prioridad:** CRITICO (anti-patron §27)
**Archivo:** [apps/tenant/empresa/static/empresa/js/features/area_editor.js](../static/empresa/js/features/area_editor.js) linea 54
**Dependiente de:** EMP-BACK-02

```javascript
// ACTUAL — PROHIBIDO por §27
sede: sedeVal ? parseInt(sedeVal, 10) : null,

// CORRECTO — despues de cambiar template a {{ s.uuid }}
sede: sedeVal || null,
```

**Nota:** Este fix solo es correcto DESPUES de aplicar EMP-BACK-02 (template a UUID + serializer a UUIDOrPKRelatedField). Si se aplica solo, el backend rompera porque recibira UUID pero el serializer espera PK entero.

**Orden de aplicacion:** EMP-BACK-02 primero, luego EMP-FRONT-01.

---

### EMP-FRONT-02 — `hx-on::after-request` debe ser `hx-on::after-settle`

**Prioridad:** CRITICO (race condition HTMX)
**Archivo:** [apps/tenant/empresa/templates/tenant/empresa/empresa_list.html](../templates/tenant/empresa/empresa_list.html) lineas 77, 167, 195

**Situacion actual (3 botones):**
```html
hx-on::after-request="if(event.detail.successful){ sintelAbrirOffcanvasEmpresa('offcanvas-empresa'); }"
hx-on::after-request="if(event.detail.successful){ sintelAbrirOffcanvasEmpresa('offcanvas-sede'); }"
hx-on::after-request="if(event.detail.successful){ sintelAbrirOffcanvasEmpresa('offcanvas-area'); }"
```

**Problema:** `after-request` se dispara cuando el servidor responde, ANTES de que HTMX aplique el swap al DOM. El elemento `#offcanvas-empresa/sede/area` no existe todavia cuando `sintelAbrirOffcanvasEmpresa()` lo busca → `document.getElementById(id)` retorna `null` → offcanvas no se abre.

**Nota historica:** El `AUDITORIA_FLUJO_EMPRESA.md` listaba este bug como "B6: Cambiado a `hx-on::after-settle`" pero el archivo template nunca fue actualizado.

**Fix requerido (3 lineas):**
```html
hx-on::after-settle="if(event.detail.successful !== false){ sintelAbrirOffcanvasEmpresa('offcanvas-empresa'); }"
hx-on::after-settle="if(event.detail.successful !== false){ sintelAbrirOffcanvasEmpresa('offcanvas-sede'); }"
hx-on::after-settle="if(event.detail.successful !== false){ sintelAbrirOffcanvasEmpresa('offcanvas-area'); }"
```

**Verificacion:** `after-settle` se dispara despues de que HTMX aplica el swap Y estabiliza las animaciones CSS. El DOM esta listo.

---

### EMP-FRONT-03 — `sintelAbrirOffcanvasEmpresa` fuera del patron UIManager

**Prioridad:** MEDIA
**Archivo:** [apps/tenant/empresa/templates/tenant/empresa/empresa_list.html](../templates/tenant/empresa/empresa_list.html) lineas 223-234

**Situacion actual:**
```javascript
window.sintelAbrirOffcanvasEmpresa = function(id) {
    document.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
    document.body.classList.remove('overflow-hidden', 'modal-open');
    var el = document.getElementById(id);
    if (el && window.bootstrap && window.bootstrap.Offcanvas) {
        var prev = bootstrap.Offcanvas.getInstance(el);
        if (prev) prev.dispose();
        new bootstrap.Offcanvas(el).show();   // dispose + create = correcto
    }
};
```

**Analisis:** La implementacion actual es funcionalmente correcta (dispose antes de crear). No usa `getOrCreateInstance().show()` (el anti-patron §26). El riesgo es de mantenimiento: si UIManager cambia su comportamiento de apertura, `sintelAbrirOffcanvasEmpresa` quedara desincronizado.

**Fix recomendado:** Delegar a `UIManager.handleOffcanvas()`:
```javascript
window.sintelAbrirOffcanvasEmpresa = function(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (window.UIManager?.handleOffcanvas) {
        window.UIManager.handleOffcanvas(el, 'show');
    } else {
        // Fallback: dispose + create
        var prev = bootstrap.Offcanvas.getInstance(el);
        if (prev) prev.dispose();
        document.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
        document.body.style.overflow = '';
        new bootstrap.Offcanvas(el).show();
    }
};
```

---

### EMP-FRONT-04 — Templates duplicados legacy vs v4.2

**Prioridad:** BAJA (documentacion/limpieza)

Existen dos versiones de templates para Sede y Area:
- `offcanvas_sede.html` — legacy, usa `{% if is_edit %}` flag
- `offcanvas_crear_sede.html` + `offcanvas_editar_sede.html` — v4.2, templates separados

**Fix recomendado:** Verificar cual version usan los viewsets `render-offcanvas` y archivar los no usados.

---

## Plan de Ejecucion — Orden y Dependencias

```
Iteracion 1 — Backend (sin dependencias entre si):
  EMP-BACK-01  selectors.py  Zero-Collision Pattern (30 min)
  EMP-BACK-02  serializers.py + templates + editor.js (1h — acoplado)
    └─ EMP-FRONT-01  area_editor.js parseInt → UUID (parte del mismo PR)

Iteracion 2 — Frontend HTMX (independiente):
  EMP-FRONT-02  empresa_list.html after-request → after-settle (15 min)
  EMP-FRONT-03  sintelAbrirOffcanvasEmpresa → UIManager (20 min)

Iteracion 3 — Limpieza (baja urgencia):
  EMP-BACK-03  Eliminar empresa.api.js DEPRECATED (5 min)
  EMP-FRONT-04  Documentar/archivar templates duplicados (30 min)
```

---

## Checklist de Verificacion Post-Fix

```bash
# 1. Django check
docker compose exec web python manage.py check

# 2. Sin migraciones pendientes
docker compose exec web python manage.py makemigrations --check

# 3. Smoke test serializers Area
docker compose exec web python -c "
import django; django.setup()
from apps.tenant.empresa.api.serializers import AreaListSerializer, AreaDetailSerializer, AreaUpsertSerializer
for cls in [AreaListSerializer, AreaDetailSerializer, AreaUpsertSerializer]:
    s = cls(); _ = s.fields; print('OK:', cls.__name__)
"

# 4. §30 scanner — verificar que AREA_LIST/DETAIL_FIELDS no tiene traversals
docker compose exec web python -c "
from apps.tenant.empresa.services.selectors import AREA_LIST_FIELDS, AREA_DETAIL_FIELDS
bad = [f for f in (*AREA_LIST_FIELDS, *AREA_DETAIL_FIELDS) if '__' in f]
print('WARN:', bad) if bad else print('OK: sin traversals en constantes')
"

# 5. Prueba manual HTMX:
# - Abrir empresa_list
# - Clic en Nueva Sede → offcanvas debe abrirse (no pantalla negra)
# - Clic en Nueva Area → offcanvas debe abrirse con select de sedes
# - Crear Sede, crear Area, editar ambos
```

---

## Tabla de Riesgos

| ID | Descripcion | Si no se aplica |
|---|---|---|
| EMP-BACK-01 | AREA_LIST_FIELDS con traversals | Falla silenciosa si alguien usa la constante en Meta.fields |
| EMP-BACK-02 | PK entero en sede FK | Inconsistencia con patron UUID-first de todo el sistema |
| EMP-FRONT-01 | parseInt sobre sede select | §27 anti-patron — fragil si template cambia a UUID |
| EMP-FRONT-02 | after-request vs after-settle | Race condition — offcanvas puede no abrirse en cargas lentas |
| EMP-FRONT-03 | UIManager no usado | Desincronizacion con comportamiento centralizado de Bootstrap |
| EMP-BACK-03 | empresa.api.js DEPRECATED | Confusion para futuros desarrolladores |
| EMP-FRONT-04 | Templates duplicados | Confusion sobre que template se sirve via render-offcanvas |
