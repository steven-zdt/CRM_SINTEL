# Plan de Acción — Corrección de Deuda Técnica y Alineamiento con AGENTS.md

**Fecha de elaboración:** 2026-05-29
**Ultima validacion:** 2026-06-01
**Versión del sistema:** v3.16.0
**Referencia AGENTS.md:** v3.16.0 (raíz del proyecto)

---

## Índice de Deuda por App — Estado Actualizado

| ID | App | Severidad | Estado | Fase | Evidencia |
|---|---|---|---|---|---|
| DT-FACT-01 | facturas | ALTA | **PENDIENTE** | 1 | `viewsets.py` sigue en 1136 líneas |
| DT-FACT-02 | facturas | ALTA | **PENDIENTE** | 1 | `facturas_main.js` sigue en 2152 líneas; módulos feature no creados |
| DT-FACT-11 | facturas | MEDIA | **PENDIENTE** | 1 | Sin config `TEST` en `DATABASES` de settings |
| DT-GAST-01 | gastos | MEDIA | **RESUELTO** | 1 | Campos `retefuente*`/`reteica*` eliminados; Pull Model activo |
| DT-FACT-05 | facturas | MEDIA | **PARCIAL** | 2 | `xml_content`/`xml_file_path` aún existen marcados DEPRECADO |
| DT-FACT-06 | facturas | MEDIA | **RESUELTO** | 2 | `MailIngestionConfig` eliminado de `facturas/models.py` |
| DT-GAST-06 | gastos | MEDIA | **PENDIENTE** | 2 | Tests de dominio no existen (`test_gasto_crud`, `test_consecutivos`, etc.) |
| DT-PUB-01 | console | MEDIA | **RESUELTO** | 2 | 56 tests en `apps/public/console/tests/` — 56/56 passed |
| DT-FACT-03 | facturas | MEDIA | **PARCIAL** | 3 | `facturas_list.js` en 750 líneas; sin split columns/actions |
| DT-FACT-04 | facturas | MEDIA | **PARCIAL** | 3 | 398 XMLs aún en `facturas_xml/` |
| DT-FACT-09 | facturas | BAJA | **RESUELTO** | 3 | Template huérfano `list.html` no existe |
| DT-INV-04 | inventario | BAJA | **RESUELTO** | 3 | Endpoints `dt/` eliminados de `urls.py` |
| DT-INV-05 | inventario | BAJA | **RESUELTO** | 3 | `ingesta_service.py` creado; `business_service.py` en 707 líneas |
| DT-GAST-04 | gastos | BAJA | **RESUELTO** | 3 | `gasto_editor.js` en 487 líneas |
| DT-GAST-08 | gastos | BAJA | **RESUELTO** | 3 | `settings` import a nivel global en `viewsets.py` |
| DT-PUB-02 | core | BAJA | **RESUELTO** | 3 | `test_public_index_view.py` existe — 4 tests |
| DT-PUB-03 | tenants | BAJA | **RESUELTO** | 4 | `delete_model()` delega a `hard_delete_tenant()` |
| DT-PUB-04 | accounts/console | BAJA | **RESUELTO** | 4 | `UsersDataTableView.delete()` llama `delete_user_service()` |
| DT-PUB-05 | tenants | BAJA | **RESUELTO** | 4 | Guard `DEBUG=False` en `generar_tenants_prueba` y `analizar_tenants_prueba` |
| DT-INV-08 | inventario | MUY BAJA | **RESUELTO** | 4 | Dead code `initCodigoPrefijo` eliminado; `activos_editor.js` en 312 líneas |
| DT-FACT-10 | facturas | BAJA | **PENDIENTE** | 4 | `test_ubl_parser.py` no existe |
| DT-FACT-12 | facturas | BAJA | **RESUELTO** | 4 | Imports a nivel módulo en `viewsets.py` |
| **DT-ZH-01** | **global** | **ALTA** | **RESUELTO** | 5 | 18 archivos con nombres propios de tenants (`home`,`cliente`,`putito`...) abstraídos; §29 AGENTS.md |
| **DT-ISO-01** | **clientes** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-02** | **proveedores** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-03** | **facturas** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-04** | **inventario** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-05** | **empleados** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-06** | **cotizaciones** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-07** | **proyectos** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |
| **DT-ISO-08** | **contabilidad** | **ALTA** | **PENDIENTE** | 5 | Sin `test_multitenant_isolation.py` — §24.5 AGENTS.md |

---

## Resumen de Estado

| Estado | Cantidad | % |
|---|---|---|
| **RESUELTO** | 15 | 47% |
| **PARCIAL** | 3 | 9% |
| **PENDIENTE** | 13 | 41% |

**Total items: 31**
**Tasa de resolución: 47% (15/31)**

---

## FASE 5 — Normas Nuevas (v3.16.0) — Items Incorporados en Esta Sesión

---

### DT-ZH-01 — Abstracción Zero-Hardcoding §29 AGENTS.md [RESUELTO]

**Norma:** §29 AGENTS.md — ningún script, test o management command puede contener nombres propios de tenants como strings literales.

**Resultado:**
- 18 archivos corregidos (scratch/, scripts/, tests/, apps/tenant/)
- Lista estática `['home', 'cliente']` → `Client.objects.exclude(schema_name='public').filter(is_active=True)`
- Fixtures de test: `schema_name='home'` → `test_schema_01` / `{self.tenant.schema_name}.sintel.local`
- Help texts y docstrings: `'home.sintel.net.co'` → `{schema}.sintel.net.co`
- Enforcement command en `.antigravity/rules/core.md` + `.claude/settings.local.json`

**Verificación:**
```bash
grep -rn "'home'\|'cliente'\|'putito'\|'tupapi'\|home\.sintel\.com\|cliente\.sintel\.com" \
    apps/ tests/ scripts/ scratch/ --include="*.py" \
    | grep -v "__pycache__\|migration\|assertNotIn\|\.sintel\.local\|{schema\|schema_name='public'"
# Esperado: 0 líneas
```

---

### DT-ISO-01..08 — Tests de Aislamiento Multi-Tenant por App §24.5 AGENTS.md [PENDIENTES]

**Norma:** §24.5 AGENTS.md — toda app tenant con modelos propios DEBE tener `test_multitenant_isolation.py` con los 3 niveles de seguridad.

**Canon:** `apps/tenant/gastos/tests/test_multitenant_isolation.py` ← único existente, patrón a replicar.

**Los 3 niveles obligatorios:**

| Nivel | Qué valida | Assert mínima |
|---|---|---|
| **1 — Listado** | `GET /api/v1/{app}/` desde tenant1 no expone datos de tenant2 | `assert obj_t2.campo not in results` |
| **2 — IDOR directo** | `GET /api/v1/{app}/{uuid_t2}/` desde tenant1 → 404 | `assert resp.status_code == 404` |
| **3 — IDOR en FKs** | `POST` con FK de tenant2 desde tenant1 → 400/403/404 | `assert resp.status_code in (400,403,404)` |

**Apps pendientes (8 de 9 apps con modelos):**

| ID | App | Modelos clave | Endpoint base |
|---|---|---|---|
| DT-ISO-01 | clientes | `Cliente`, `ContactoCliente` | `/api/v1/clientes/` |
| DT-ISO-02 | proveedores | `Proveedor` | `/api/v1/proveedores/` |
| DT-ISO-03 | facturas | `Factura`, `ItemFactura`, `NotaCredito` | `/api/v1/facturas/` |
| DT-ISO-04 | inventario | `Producto`, `Servicio`, `ActivoFijo`, `MovimientoInventario` | `/api/v1/inventario/productos/` |
| DT-ISO-05 | empleados | `Empleado`, `Contrato`, `Devengo` | `/api/v1/empleados/` |
| DT-ISO-06 | cotizaciones | `Cotizacion`, `CotizacionItem` | `/api/v1/cotizaciones/` |
| DT-ISO-07 | proyectos | `Proyecto`, `TareaCorta` | `/api/v1/proyectos/` |
| DT-ISO-08 | contabilidad | `CuentaContable`, `AsientoContable`, `Retencion` | `/api/v1/contabilidad/cuentas-contables/` |

**Template de conftest a reutilizar** (basado en `apps/tenant/gastos/tests/conftest.py`):
```python
# apps/tenant/{app}/tests/conftest.py
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa


def _make_test_tenant(schema: str, nombre: str, nit: str):
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.create(schema_name=schema, nombre=nombre)
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.net.co', is_primary=True)
    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)
    with schema_context(schema):
        if not Empresa.objects.exists():
            Empresa.objects.create(nit=nit, razon_social=f'Empresa {nombre}', direccion='Test')
    return tenant_obj


@pytest.fixture
def tenant1(db):
    return _make_test_tenant('tenant1', 'Tenant 1', '111111111')


@pytest.fixture
def tenant2(db):
    return _make_test_tenant('tenant2', 'Tenant 2', '222222222')
```

---

## Items PENDIENTES (originales) — Acción Requerida

---

### DT-FACT-01 — Fragmentar `facturas/api/viewsets.py` (1136 líneas) [ALTA]

`apps/tenant/facturas/api/mixins/` existe pero vacío. Crear 3 mixins y reducir viewsets.py < 600 líneas:
- `factura_ubl_mixin.py` — `parse_xml_ubl()`, `render_pdf()`, `enviar_dian()`
- `factura_mail_mixin.py` — `ingest_mail()`, `configure_mailbox()`
- `factura_xml_mixin.py` — `get_xml_content()`, `download_xml()`

---

### DT-FACT-02 — Fragmentar `facturas_main.js` (2152 líneas) [ALTA]

Crear en `static/js/facturas/features/`:
- `facturas_xml_viewer.js`, `facturas_retenciones.js`, `facturas_pago.js`

Objetivo: `facturas_main.js` < 600 líneas.

---

### DT-FACT-11 — Config TEST en DATABASES [MEDIA]

Agregar en `config/settings.py`:
```python
DATABASES['default']['TEST'] = {'NAME': 'test_sintel'}
```

---

### DT-GAST-06 — Tests de dominio para gastos [MEDIA]

Crear en `apps/tenant/gastos/tests/`:
- `conftest.py`, `test_gasto_crud.py`, `test_consecutivos.py`, `test_dsv.py`, `test_pull_model.py`

**Nota:** `test_multitenant_isolation.py` ya existe (DT-ISO para gastos = RESUELTO).

---

### DT-FACT-10 — Tests unitarios `utils/ubl_parser.py` [BAJA]

Crear `apps/tenant/facturas/tests/test_ubl_parser.py`.

---

## Items PARCIALES — Completar

---

### DT-FACT-05 — Eliminar `xml_content`/`xml_file_path` DEPRECATED [PARCIAL]

Campos existen marcados DEPRECADO. Verificar 0 lecturas activas y generar migración de remoción.

---

### DT-FACT-03 — Completar split `facturas_list.js` (750 líneas) [PARCIAL]

Extraer `facturas_list_columns.js` y `facturas_list_actions.js`. Objetivo: < 400 líneas.

---

### DT-FACT-04 — Mover 398 XMLs fuera del source tree [PARCIAL]

Mover a `apps/tenant/facturas/tests/fixtures/xml/` o excluir via `.gitignore`.

---

## Verificaciones de Estado

```bash
# Items RESUELTOS — validar que siguen resueltos
python manage.py check                                          # 0 errores
python -m pytest apps/public/console/tests/ -q                # 56/56 passed
grep -n "retefuente\|reteica" apps/tenant/gastos/models.py     # solo @property
grep -c "MailIngestionConfig" apps/tenant/facturas/models.py   # 0
wc -l apps/tenant/gastos/static/gastos/js/features/gasto_editor.js  # < 600
grep -n "from django.conf import settings" apps/tenant/gastos/api/viewsets.py  # línea global

# Zero-Hardcoding §29 — enforcement
grep -rn "'home'\|'cliente'\|'putito'\|'tupapi'\|home\.sintel\.com" \
    apps/ tests/ scripts/ scratch/ --include="*.py" \
    | grep -v "__pycache__\|migration\|assertNotIn\|\.sintel\.local\|{schema\|schema_name='public'"
# Esperado: 0 líneas

# Items PENDIENTES — medir progreso
wc -l apps/tenant/facturas/api/viewsets.py                    # debe ser < 600
wc -l apps/tenant/facturas/static/js/facturas/facturas_main.js # debe ser < 600
ls apps/tenant/gastos/tests/                                  # debe tener 5 archivos
find apps/tenant -name "test_multitenant_isolation.py"        # debe ser 9 apps
```
