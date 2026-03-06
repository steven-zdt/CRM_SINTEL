# Validación: Foreign Keys a Empresa en Apps de Negocio

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Validación completada

---

## 📋 Resumen Ejecutivo

Se ha validado el estado de las Foreign Keys (FK) a `Empresa` en todas las apps de negocio mencionadas. **Solo `inventario.ActivoFijo` tiene FK a `Empresa`**. Las demás apps **NO tienen FK a `Empresa`** y no se encontraron migraciones que las hayan agregado.

---

## 🔍 Estado Actual por App

### ✅ 1. `inventario.ActivoFijo` - **TIENE FK**

**Ubicación:** `apps/tenant/inventario/models.py`

```python
class ActivoFijo(TimeStampedModel):
    empresa = models.ForeignKey(  # ✅ FK a Empresa presente
        Empresa,
        on_delete=models.PROTECT,
        related_name="activos_fijos",
        help_text="Empresa propietaria del activo (SSoT por tenant)."
    )
    # ... otros campos ...
```

**Migración:** `apps/tenant/inventario/migrations/0001_initial.py`
- ✅ FK creada en migración inicial
- ✅ Campo: `empresa` → `empresa.empresa`
- ✅ `on_delete=models.PROTECT`
- ✅ `related_name="activos_fijos"`

**Estado:** ✅ **CONFORME** - FK ya implementada

---

### ❌ 2. `clientes.Cliente` - **SIN FK**

**Ubicación:** `apps/tenant/clientes/models.py`

**Modelo `Cliente`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Tiene campos propios (tipo_persona, numero_documento, razon_social, etc.)
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Estado:** ❌ **PENDIENTE** - No tiene FK a `Empresa`

---

### ❌ 3. `proveedores.Proveedor` - **SIN FK**

**Ubicación:** `apps/tenant/proveedores/models.py`

**Modelo `Proveedor`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Tiene campos propios (tipo_persona, numero_documento, razon_social, etc.)
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Estado:** ❌ **PENDIENTE** - No tiene FK a `Empresa`

---

### ❌ 4. `gastos.Gasto` - **SIN FK**

**Ubicación:** `apps/tenant/gastos/models.py`

**Modelo `Gasto`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Tiene FK a `empleados.Empleado` y `empleados.Devengo`
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Estado:** ❌ **PENDIENTE** - No tiene FK a `Empresa`

---

### ❌ 5. `facturas.Factura` - **SIN FK**

**Ubicación:** `apps/tenant/facturas/models.py`

**Modelo `Factura`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Usa **snapshot pattern**: almacena datos del emisor en campos propios (`emisor_nit`, `emisor_razon_social`, etc.)
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Nota:** `Factura` usa un patrón de snapshot (almacena datos del emisor al momento de emisión), por lo que **NO requiere FK a `Empresa`** para cumplir su propósito.

**Estado:** ❌ **PENDIENTE** (pero puede ser intencional por snapshot pattern)

---

### ❌ 6. `contabilidad.CuentaContable` - **SIN FK**

**Ubicación:** `apps/tenant/contabilidad/models.py`

**Modelo `CuentaContable`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Tiene FK a `self` (cuenta_padre) para jerarquía
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Estado:** ❌ **PENDIENTE** - No tiene FK a `Empresa`

---

### ❌ 7. `contabilidad.AsientoContable` - **SIN FK**

**Ubicación:** `apps/tenant/contabilidad/models.py`

**Modelo `AsientoContable`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Tiene FK a `facturas.Factura` (opcional)
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Estado:** ❌ **PENDIENTE** - No tiene FK a `Empresa`

---

### ❌ 8. `empleados.Empleado` - **SIN FK**

**Ubicación:** `apps/tenant/empleados/models.py`

**Modelo `Empleado`:**
- ❌ No tiene campo `empresa` o `ForeignKey` a `Empresa`
- ✅ Tiene campos propios (tipo_documento, numero_documento, nombres, etc.)
- ✅ No hay migraciones que agreguen FK a `Empresa`

**Estado:** ❌ **PENDIENTE** - No tiene FK a `Empresa`

---

## 📊 Tabla Resumen

| App | Modelo | FK a Empresa | Migración | Estado |
|-----|--------|--------------|-----------|--------|
| `inventario` | `ActivoFijo` | ✅ **SÍ** | ✅ `0001_initial.py` | ✅ **CONFORME** |
| `clientes` | `Cliente` | ❌ **NO** | ❌ No existe | ❌ **PENDIENTE** |
| `proveedores` | `Proveedor` | ❌ **NO** | ❌ No existe | ❌ **PENDIENTE** |
| `gastos` | `Gasto` | ❌ **NO** | ❌ No existe | ❌ **PENDIENTE** |
| `facturas` | `Factura` | ❌ **NO** | ❌ No existe | ⚠️ **SNAPSHOT** |
| `contabilidad` | `CuentaContable` | ❌ **NO** | ❌ No existe | ❌ **PENDIENTE** |
| `contabilidad` | `AsientoContable` | ❌ **NO** | ❌ No existe | ❌ **PENDIENTE** |
| `empleados` | `Empleado` | ❌ **NO** | ❌ No existe | ❌ **PENDIENTE** |

---

## 🔍 Búsqueda en Migraciones

Se buscó en todas las migraciones de las apps mencionadas:

```bash
# Búsqueda realizada:
grep -r "empresa\.empresa\|ForeignKey.*Empresa\|empresa.*ForeignKey" apps/tenant/*/migrations/*.py
```

**Resultados:**
- ✅ Solo se encontró FK en `inventario/migrations/0001_initial.py` (ya documentado)
- ❌ No se encontraron migraciones que agreguen FK a `Empresa` en las demás apps

---

## 💡 Consideraciones

### 1. **Patrón Singleton de Empresa**

`Empresa` es un **singleton por tenant** (una única instancia por esquema). Esto significa que:
- Si una app necesita referenciar la empresa del tenant, técnicamente **no necesita FK** porque siempre hay una única instancia.
- Sin embargo, una FK puede ser útil para:
  - **Integridad referencial**: Garantizar que los registros pertenecen a la empresa correcta
  - **Queries eficientes**: Filtrar por `empresa_id` es más eficiente que buscar la empresa singleton
  - **Claridad semántica**: Hace explícita la relación entre modelos

### 2. **Patrón Snapshot (Factura)**

`Factura` usa un **patrón de snapshot** donde almacena los datos del emisor al momento de emisión:
- `emisor_nit`, `emisor_razon_social`, `emisor_direccion`, etc.
- Esto permite mantener un registro histórico incluso si la empresa cambia sus datos.
- **No requiere FK a `Empresa`** porque los datos están embebidos.

### 3. **Apps que Podrían Beneficiarse de FK**

Las siguientes apps podrían beneficiarse de una FK a `Empresa`:
- ✅ `clientes.Cliente`: Para filtrar clientes por empresa (si en el futuro se permite multi-empresa)
- ✅ `proveedores.Proveedor`: Similar a clientes
- ✅ `gastos.Gasto`: Para asociar gastos a la empresa
- ✅ `contabilidad.CuentaContable`: Para tener planes de cuentas por empresa
- ✅ `contabilidad.AsientoContable`: Para asociar asientos a la empresa
- ✅ `empleados.Empleado`: Para asociar empleados a la empresa

**Nota:** Si se implementan estas FKs, se requerirán **migraciones con backfill** para poblar el campo `empresa_id` en registros existentes.

---

## ✅ Conclusión

**Estado Actual:**
- ✅ **1 app** (`inventario.ActivoFijo`) **SÍ tiene FK a `Empresa`**
- ❌ **7 apps/modelos** **NO tienen FK a `Empresa`**

**Acción Requerida:**
- ⚠️ **Ninguna acción automática fue ejecutada**
- 📝 Si se requieren FKs en las demás apps, se deben crear **migraciones manuales con backfill**

**Recomendación:**
- Si se decide agregar FKs, crear migraciones que:
  1. Agreguen el campo `empresa` (ForeignKey, nullable inicialmente)
  2. Hagan backfill: `UPDATE tabla SET empresa_id = (SELECT id FROM empresa_empresa LIMIT 1)`
  3. Hagan el campo `NOT NULL` después del backfill
  4. Agreguen índices para performance

---

## 📝 Notas Técnicas

### Backfill Pattern (Ejemplo)

```python
# Ejemplo de migración con backfill para clientes.Cliente
from django.db import migrations, models
import django.db.models.deletion

def backfill_empresa_id(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    Empresa = apps.get_model('empresa', 'Empresa')
    
    # Obtener la empresa singleton del tenant
    empresa = Empresa.objects.first()
    if empresa:
        Cliente.objects.filter(empresa__isnull=True).update(empresa=empresa)

class Migration(migrations.Migration):
    dependencies = [
        ('clientes', '0001_initial'),
        ('empresa', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='empresa',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='clientes',
                to='empresa.empresa'
            ),
        ),
        migrations.RunPython(backfill_empresa_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cliente',
            name='empresa',
            field=models.ForeignKey(
                null=False,  # Ahora NOT NULL
                on_delete=django.db.models.deletion.PROTECT,
                related_name='clientes',
                to='empresa.empresa'
            ),
        ),
        migrations.AddIndex(
            model_name='cliente',
            index=models.Index(fields=['empresa'], name='clientes_cliente_empresa_idx'),
        ),
    ]
```

---

**Validación completada:** ✅  
**Fecha:** 2026-01-XX  
**Versión:** v2.40
