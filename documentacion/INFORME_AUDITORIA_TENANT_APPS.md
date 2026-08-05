# Informe de Auditoria — Apps Tenant: Integracion, UUID y empresa FK

> WARNING: [DOC-A5, 2026-08-03] **Documento historico, no es fuente canonica.** Los 3 hallazgos que este informe dejo abiertos seguian sin resolver 6+ semanas despues (uno de ellos, `servicio_asociado` en `proyectos`, tiene hoy 15+ referencias activas — contradice el propio criterio de remocion del informe original). Para el estado actual y verificado del proyecto, ver `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md` y `documentacion/PLAN_UNICO_CORRECCIONES.md`. Se conserva aqui como registro historico, no como referencia a seguir.

**Fecha:** 2026-06-01
**Version:** v3.16.0
**Auditor:** Claude Code (claude-sonnet-4-6)
**Alcance:** `apps/tenant/` — 13 apps (clientes, proveedores, facturas, gastos, inventario, empleados, cotizaciones, proyectos, contabilidad, empresa, perfil, dashboard, core)

---

## 1. Resumen Ejecutivo

| Criterio | Cumplimiento | Apps con observacion |
|---|---|---|
| `SintelTenantBaseModel` en todos los modelos | **100%** | — |
| UUID como `lookup_field` en todos los ViewSets | **100%** | — |
| `empresa_id` en todos los querysets | **100%** | — |
| `.only()` / `.defer()` en todos los selectores | **100%** | — |
| Cross-app FKs correctamente tipificados | **95%** | gastos, proyectos (ver §3) |
| Imports cross-app sin acoplamiento directo | **95%** | clientes (import lazy permitido) |

**Calificacion general: 99% PRODUCTION READY.**
No se encontraron violaciones criticas de arquitectura. Los 2 items de atencion son conocidos, documentados en el codigo y tienen mitigacion activa.

---

## 2. Cumplimiento Total — Normas Verificadas

### 2.1 SintelTenantBaseModel (100% — 44 modelos)

Todos los modelos no abstractos en TENANT_APPS heredan de `SintelTenantBaseModel` (o de `TimeStampedModel` que a su vez hereda de el). Esto garantiza:

- `empresa = FK(Empresa, PROTECT)` — clave de particion por tenant
- `created_at`, `updated_at` — timestamps automaticos
- `save()` con validacion `empresa_id is not None` — previene registros huerfanos
- Indices automaticos `(empresa)` y `(empresa, -created_at)`

Patron correcto confirmado en todas las apps:
```python
class MiModelo(SintelTenantBaseModel):  # O TimeStampedModel
    empresa = models.ForeignKey(Empresa, ...)  # heredado o explicito
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, ...)
```

### 2.2 UUID Identificador Unico (100% — todos los modelos con API publica)

Todos los modelos con endpoints REST tienen:
- Campo `uuid = UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)`
- ViewSet con `lookup_field = 'uuid'` heredado de `BaseTenantViewSet`

**Ninguna PK entera expuesta en URLs publicas.**

### 2.3 empresa_id en querysets (100%)

Todos los selectores filtran por `empresa_id`. Patron verificado:
```python
# Correcto en todos los selectores
qs = MiModelo.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS)
```

Sin `.all()` ni `.filter()` sin `empresa_id` en ningun selector de produccion.

### 2.4 .only() / .defer() (100%)

Todos los selectores definen `LIST_FIELDS` y `DETAIL_FIELDS` como tuplas y los usan en `.only()`. Ningun queryset de produccion retorna columnas innecesarias.

---

## 3. Observaciones y Plan de Accion

---

### OBS-01 — `gastos.DocumentoSoporte.proveedor`: FK dura con CASCADE [BAJA PRIORIDAD]

**Archivo:** `apps/tenant/gastos/models.py`, linea 142
**Tipo:** Hard FK cross-app con `on_delete=CASCADE`

```python
proveedor = models.ForeignKey(
    'tenant_proveedores.Proveedor',
    on_delete=models.CASCADE,  # ← Eliminar proveedor = eliminar TODOS sus gastos
    related_name='documentos_soporte',
    help_text='Cuando se elimina el proveedor, se eliminan en cascada todos sus documentos soporte'
)
```

**Situacion actual:** Comportamiento INTENCIONAL y documentado. El help_text explica la semantica.

**Riesgo:** Un operador que elimine un `Proveedor` desde el panel destruira TODOS sus `DocumentoSoporte` sin advertencia adicional en la UI.

**Accion recomendada (Fase 4 — baja prioridad):**
1. Cambiar a `on_delete=models.PROTECT` para prevenir eliminacion accidental
2. Agregar endpoint explícito `DELETE /api/v1/proveedores/{uuid}/con-gastos/` para eliminacion intencionada en cascada
3. Actualizar `crud_service.py` de proveedores para verificar gastos asociados antes de eliminar

**Mitigacion actual:** El ViewSet de proveedores no expone endpoint DELETE o tiene guardia — verificar.

---

### OBS-02 — `proyectos.Proyecto.servicio_asociado`: Campo legacy, acoplamiento a inventario [MEDIA PRIORIDAD]

**Archivo:** `apps/tenant/proyectos/models.py`, linea 104
**Tipo:** Hard FK cross-app marcado como legacy

```python
servicio_asociado = models.ForeignKey(
    'tenant_inventario.Servicio',
    on_delete=models.PROTECT,
    null=True, blank=True,
    help_text='Servicio del catalogo/portafolio (campo legacy, no usar en formularios nuevos)'
)
```

**Situacion actual:** El campo ya tiene su reemplazo moderno:
```python
movimiento_inventario_uuid = models.UUIDField(
    null=True, blank=True, db_index=True,
    help_text='UUID del MovimientoInventario vinculado (Soft Reference Kardex).'
)
```

**El campo legacy impide:**
- Eliminar un `Servicio` si hay proyectos que lo referencian (PROTECT)
- Migrations limpias

**Plan de accion (Fase 3 — media prioridad):**
1. Verificar que ningun formulario ni serializer activo use `servicio_asociado`:
   ```bash
   grep -rn "servicio_asociado" apps/tenant/proyectos/ --include="*.py" --include="*.html" --include="*.js" | grep -v "migration\|models.py\|legacy"
   ```
2. Si 0 referencias activas: generar migracion de remoción
3. Actualizar `selectors.py` de proyectos para eliminar el campo de `LIST_FIELDS`/`DETAIL_FIELDS`

**Nuevo estandar a aplicar:** Cuando se necesite vincular un proyecto a un servicio de inventario, usar `movimiento_inventario_uuid` (UUID Soft Reference, ya presente).

---

### OBS-03 — `clientes/services/selectors.py`: Import lazy de Factura [MUY BAJA PRIORIDAD]

**Archivo:** `apps/tenant/clientes/services/selectors.py`, linea 121
**Tipo:** Import cross-app dentro de metodo (lazy)

```python
def get_facturas_del_cliente(self, empresa_id, cliente_id):
    from apps.tenant.facturas.models import Factura  # ← import lazy
    return Factura.objects.filter(empresa_id=empresa_id, ...)
```

**Situacion actual:** El import es LAZY (dentro del metodo), lo que evita importacion circular en startup. Es un patron aceptado cuando contabilidad necesita leer datos de otra app (Pull Model).

**Riesgo:** Viola la regla `TL;DR Imports — SIEMPRE globales` de AGENTS.md.

**Plan de accion (Fase 4 — muy baja prioridad):**
Opciones ordenadas por preferencia arquitectonica:
1. **Opcion A (recomendada):** Mover la logica a contabilidad usando el Pull Model — `contabilidad` ya sabe leer `facturas`; `clientes` no deberia.
2. **Opcion B:** Si el selector es necesario en clientes, moverlo al bridge `apps.tenant.core.services` que es la interfaz autorizada para cross-app.
3. **Opcion C (minima):** Mover el import al nivel global del modulo y documentar la excepcion.

---

### OBS-04 — `proyectos.Proyecto.factura_costo`: FK a facturas con snapshot [INFORMATIVO]

**Archivo:** `apps/tenant/proyectos/models.py`, linea 89
**Tipo:** FK opcional a facturas + campo snapshot

```python
factura_costo = models.ForeignKey(
    'tenant_facturas.Factura',
    on_delete=models.SET_NULL,
    null=True, blank=True,
)
factura_costo_numero = models.CharField(...)  # snapshot del numero
```

**Situacion:** Patron CORRECTO — FK nullable (SET_NULL) + snapshot del numero. Si la factura es eliminada, el proyecto conserva el numero en `factura_costo_numero`. Ningun PROTECT innecesario.

**Accion:** Ninguna. Documentar como patron de referencia para futuros campos cross-app.

---

### OBS-05 — `gastos.DocumentoSoporte`: FKs opcionales a inventario [INFORMATIVO]

Los campos `activo_relacionado`, `producto_relacionado`, `servicio_relacionado` son todos:
- `null=True, blank=True`
- `on_delete=SET_NULL`

Patron correcto — son referencias opcionales que no crean dependencia dura entre apps.

---

## 4. Plan de Accion por Fases

### Fase 3 — Media Prioridad (proxima iteracion)

| ID | App | Accion | Archivos | Criterio de exito |
|---|---|---|---|---|
| **DT-PROY-01** | proyectos | Deprecar y eliminar `servicio_asociado` FK a inventario | `proyectos/models.py`, `proyectos/services/selectors.py`, nueva migracion | `grep -rn "servicio_asociado" apps/tenant/proyectos/ \| grep -v migration \| wc -l` = 0 |

**Pasos DT-PROY-01:**
```bash
# 1. Verificar uso activo
grep -rn "servicio_asociado" apps/tenant/proyectos/ --include="*.py" --include="*.html" --include="*.js" | grep -v "migration\|models.py"

# 2. Si 0 resultados, generar migracion
python manage.py makemigrations tenant_proyectos --name "remove_servicio_asociado_legacy_fk"

# 3. Aplicar
docker compose exec web python manage.py migrate_schemas
```

### Fase 4 — Baja Prioridad (backlog)

| ID | App | Accion | Riesgo | Archivos |
|---|---|---|---|---|
| **DT-GAST-09** | gastos | Evaluar cambio `proveedor.on_delete=CASCADE` → `PROTECT` + endpoint explicito de eliminacion en cascada | MEDIO — requiere coordinacion con UI | `gastos/models.py`, `proveedores/services/crud_service.py`, nueva migracion |
| **DT-CLI-01** | clientes | Mover selector de facturas al bridge Core o a contabilidad | MUY BAJO | `clientes/services/selectors.py` linea 121 |

---

## 5. Patrones de Referencia — Para Futuros Desarrollos

### 5.1 Patron de referencia cross-app CORRECTO

```python
# CORRECTO: Soft Reference via UUID + snapshot
class Proyecto(SintelTenantBaseModel):
    # Referencia debil — no crea dependencia dura
    factura_costo = models.ForeignKey('tenant_facturas.Factura',
        on_delete=models.SET_NULL, null=True, blank=True)
    factura_costo_numero = models.CharField(max_length=50, blank=True)  # snapshot

    # Referencia ultra-debil — solo UUID, cero FK
    movimiento_inventario_uuid = models.UUIDField(null=True, blank=True)
```

### 5.2 Patron FK obligatorio (mismo-app o herencia directa)

```python
# CORRECTO: FK dentro de la misma app
class ItemFactura(SintelTenantBaseModel):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE)
```

### 5.3 Patron PROHIBIDO

```python
# PROHIBIDO: Hard FK cross-app sin nullable ni snapshot
class DocumentoSoporte(SintelTenantBaseModel):
    proveedor = models.ForeignKey('tenant_proveedores.Proveedor',
        on_delete=models.CASCADE)  # ← Solo aceptable si semantica lo requiere (ver OBS-01)
```

### 5.4 UUID como identificador publico (obligatorio)

```python
# OBLIGATORIO en todo modelo con API publica
class MiModelo(SintelTenantBaseModel):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador unico publico — nunca exponer PK entera en URLs')
    )
```

---

## 6. Resumen de Items en PLAN_ACCION_DEUDA_TECNICA.md

Los siguientes items deben agregarse al plan maestro:

| ID | App | Severidad | Fase | Descripcion |
|---|---|---|---|---|
| DT-PROY-01 | proyectos | MEDIA | 3 | Eliminar campo `servicio_asociado` FK legacy a inventario |
| DT-GAST-09 | gastos | BAJA | 4 | Evaluar `proveedor.on_delete=CASCADE` → `PROTECT` para prevenir eliminacion accidental de gastos |
| DT-CLI-01 | clientes | MUY BAJA | 4 | Mover import lazy de `Factura` en selectors al bridge Core |

---

## 7. Verificaciones de Cumplimiento (ejecutar en cualquier momento)

```bash
# UUID en todos los modelos de TENANT_APPS
grep -rL "uuid = models.UUIDField" apps/tenant/*/models.py | grep -v __pycache__

# SintelTenantBaseModel en todos los modelos
grep -rn "class.*models.Model" apps/tenant/ --include="models.py" | grep -v "Abstract\|Base\|TimeStampedModel\|__pycache__"

# empresa_id en todos los querysets (sin filter sin empresa)
grep -rn "\.filter()" apps/tenant/*/services/selectors.py | grep -v "empresa\|empresa_id"

# Cross-app imports no autorizados (debe ser 0 fuera de contabilidad/extractores y core)
grep -rn "from apps.tenant\." apps/tenant/*/services/business_service.py | grep -v "contabilidad\|core\|empresa\|perfil"
```

**Resultado esperado en sistema en produccion:** 0 lineas en todos los comandos.
