"""
Guía de Implementación: Herencia SSoT v2.61.4

Este documento orquesta la implentación COMPLETA de la herencia SSoT en SINTEL.

ESTADO:
  ✅ PASO 1: Modelo base SintelTenantBaseModel creado en apps/tenant/core/models.py
  ✅ PASO 2: Test de introspección creado en apps/tenant/core/tests/test_ssot_integrity.py
  ✅ PASO 3: 3 modelos refactorizados manualmente (Cliente, Proveedor, Factura)
  ⏳ PASO 4: Script de refactorización automática creado (tools/refactor_ssot_inheritance.py)
  ⏳ PASO 5: Refactorizar REST DE MODELOS (ItemFactura, NotaCredito, etc.)
  ⏳ PASO 6: Crear migraciones para cada app
  ⏳ PASO 7: Refactorizar services.py para que empresa sea primer parámetro
  ⏳ PASO 8: Ejecutar test de introspección (FINAL VALIDATION)

============================================================================
PASO 1: SintelTenantBaseModel
============================================================================

✅ COMPLETADO:

Archivo: apps/tenant/core/models.py
Contenidо:
  - Clase abstracta SintelTenantBaseModel(models.Model)
  - Campo: empresa FK obligatoria a Empresa (null=False, blank=False)
  - Campo: created_at (auto_now_add=True)
  - Campo: updated_at (auto_now=True)
  - Método save() overridden para garantizar empresa != NULL
  - Meta.indexes con [empresa] y [empresa, -created_at]

Ventajas:
  - Herencia de campos de auditoría automática
  - Protección contra NULL empresa_id en tiempo de código
  - Consistencia de índices en todos los modelos
  - DRY principle aplicado

============================================================================
PASO 2: Test de Introspección
============================================================================

✅ COMPLETADO:

Archivo: apps/tenant/core/tests/test_ssot_integrity.py
6 Tests incluidos:

1. test_tenant_models_have_empresa_fk()
   - Verifica que TODO modelo en TENANT_APPS tenga empresa FK
   - Verifica que NOT NULL (null=False)
   - Verifica que es ForeignKey

2. test_tenant_models_inherit_from_base()
   - Verifica que heredan de SintelTenantBaseModel
   - Excepto modelos EXEMPT_MODELS (Empresa, MailInboxConfig, etc.)

3. test_tenant_models_no_duplicate_empresa_field()
   - Verifica que NO redefinen empresa (herencia, no redefinición)

4. test_tenant_models_have_created_updated_audit_fields()
   - Verifica que tengan created_at y updated_at
   - Como herencia, no duplicados

5. test_empresa_field_has_index()
   - Verifica que campo empresa esté indexado
   - Performance check

6. test_no_null_empresa_in_database()
   - Auditoría en vivo: verifica DB sin NULL empresa_id
   - Integridad de datos

Ejecutar:
  pytest apps/tenant/core/tests/test_ssot_integrity.py -v

============================================================================
PASO 3: Refactorización Manual de Modelos Clave
============================================================================

✅ COMPLETADO (3 modelos):

1. apps/tenant/clientes/models.py - Cliente
   Cambios:
   - class Cliente(models.Model) → class Cliente(SintelTenantBaseModel)
   - Removido: empresa FK field definition
   - Removido: created_at y updated_at field definitions
   - Agregado: comentario "# [v2.61.4] created_at y updated_at heredados"

2. apps/tenant/proveedores/models.py - Proveedor
   Cambios: identical a Cliente

3. apps/tenant/facturas/models.py - Factura
   Cambios: identical a Cliente

Patrón para refactorizar CUALQUIER modelo:

BEFORE:
```python
class MiModelo(models.Model):
    """Descripción"""
    empresa = models.ForeignKey('empresa.Empresa', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

AFTER:
```python
from apps.tenant.core.models import SintelTenantBaseModel

class MiModelo(SintelTenantBaseModel):
    """Descripción"""
    # [v2.61.4] empresa FK heredada de SintelTenantBaseModel
    nombre = models.CharField(max_length=255)
    # [v2.61.4] created_at y updated_at heredados de SintelTenantBaseModel
```

============================================================================
PASO 4: Script de Refactorización Automática
============================================================================

✅ COMPLETADO:

Archivo: tools/refactor_ssot_inheritance.py
Características:
  - Busca todo models.py en TENANT_APPS
  - Cambia class declarations (models.Model → SintelTenantBaseModel)
  - Remueve empresa FK redundantes
  - Remueve created_at/updated_at redundantes
  - Agrega imports necesarios
  - Modo DRY-RUN (default) y EXECUTE

Ejecutar:
  # Ver cambios (sin aplicar)
  python tools/refactor_ssot_inheritance.py --dry-run
  
  # Aplicar cambios
  python tools/refactor_ssot_inheritance.py --execute

Nota: El script es completamente seguro - solo modifica class declarations y
      remover campos redundantes que serán heredados.

============================================================================
PASO 5: Refactorizar REST DE MODELOS
============================================================================

⏳ TODO:

Modelos aún no refactorizados (según inventario):

contabilidad/
  - CuentaContable
  - AsientoContable
  - MovimientoContable (transitive via AsientoContable - OK)

facturas/ (resto)
  - ItemFactura
  - NotaCredito
  - MailIngestionRun (considerar agregar empresa FK)
  - FacturaAnexos, MailInboxState (transitive - OK)

gastos/
  - ResolucionDIAN
  - DocumentoSoporte
  - Gasto

cotizaciones/
  - Producto
  - Servicio
  - Cotizacion
  - ConfiguracionCotizacion
  - CotizacionItem (transitive - OK)

empleados/
  - Empleado
  - Contrato
  - Devengo

inventario/
  - CategoriaItem
  - ActivoFijo
  - Producto
  - Servicio
  - MovimientoInventario
  - HistorialServicio

proyectos/
  - Proyecto
  - AsignacionPersonal
  - PedidoProyecto
  - ItemPedido (transitive - OK)

perfil/
  - TenantProfile

landing/ dashboard/ core (sin modelos)

Total: 28 modelos to refactor

OPCIÓN A: Refactorización automática (Recomendado)
  BENEFICIO: Rápido, consistente, menos errores
  RIESGO: Script bugs (mitigation: DRY-RUN primero)
  PASOS:
    1. python tools/refactor_ssot_inheritance.py --dry-run
    2. Revisar cambios propuestos
    3. python tools/refactor_ssot_inheritance.py --execute
    4. git diff para ver cambios
    5. pytest para validar

OPCIÓN B: Refactorización manual
  BENEFICIO: Control total, educar al equipo
  RIESGO: Errores, lentitud
  PASOS:
    1. Para cada modelo:
       - class X(models.Model) → class X(SintelTenantBaseModel)
       - Remove empresa FK field
       - Remove created_at/updated_at fields
    2. Add import: from apps.tenant.core.models import SintelTenantBaseModel

Recomendación: OPCIÓN A + verificación manual de 3-5 modelos críticos

============================================================================
PASO 6: Crear Migraciones para Cada App
============================================================================

⏳ TODO:

Para cada app con modelos modificados, necesita migración.

Patrón:
```bash
Python manage.py makemigrations apps.tenant.clientes
python manage.py makemigrations apps.tenant.proveedores
python manage.py makemigrations apps.tenant.facturas
# ... etc
```

Migración será "no-op" (sin cambios en BD) porque:
  - SintelTenantBaseModel es abstract
  - Los campos ya existían en los modelos previos
  - Solo estamos refactorizando la definición del código

Pero Django requiere la migración para realizar track de cambios de modelo.

Esperar hasta que PASO 5 esté completo.

============================================================================
PASO 7: Refactorizar services.py para Patrón enterprise
============================================================================

⏳ TODO:

Patrón ACTUAL (incorrecto):
```python
def crear_cliente(empresa_id, **datos):
    cliente = Cliente.objects.create(
        empresa_id=empresa_id,
        **datos
    )
    return cliente
```

Patrón REQUERIDO (garantía SSoT):
```python
def crear_cliente(empresa, **datos):
    """
    Crea un cliente asignando automáticamente empresa.
    
    [SHIELD] empresa es garantía SSoT - nunca permite NULL
    """
    if not empresa:
        raise ValueError("[ERROR] empresa requerida")
    
    cliente = Cliente.objects.create(
        empresa=empresa,  # Object, no ID
        **datos
    )
    return cliente
```

Beneficios:
  - Tipo checking automático (objeto, no ID)
  - Previene NULL empresa_id
  - Patrón consistente en toda la codebase

Afecta servicios en:
  - apps/tenant/clientes/services.py
  - apps/tenant/proveedores/services.py
  - apps/tenant/facturas/services.py
  - ... (todas las apps)

Hacer después de refactorización de modelos estar confirmad.

============================================================================
PASO 8: VALIDACIÓN FINAL
============================================================================

⏳ TODO - Aquí es donde se ejecuta el test de introspección

Ejecutar:
```bash
pytest apps/tenant/core/tests/test_ssot_integrity.py -v --tb=short
```

Salida esperada:
```
test_tenant_models_have_empresa_fk PASSED
test_tenant_models_inherit_from_base PASSED
test_tenant_models_no_duplicate_empresa_field PASSED
test_tenant_models_have_created_updated_audit_fields PASSED
test_empresa_field_has_index PASSED
test_no_null_empresa_in_database PASSED

============ 6 passed in 1.23s ============
```

Si alguno falla:
  - Revisar el mensaje de error
  - Consultar qué modelo no cumple
  - Refactorizar ese modelo específico
  - Re-ejecutar test

============================================================================
TIMELINE ESTIMADO
============================================================================

Asumiendo refactorización con script (OPCIÓN A):

1. Ejecutar script:                    5 min
2. Revisar cambios (git diff):         10 min
3. Crear migraciones:                  5 min
4. Ejecutar migraciones (test DB):     2 min
5. Ejecutar test suite:                3 min
6. Refactorizar services.py:           20 min (iterativo, app by app)
7. Validación final:                   5 min

TOTAL: ~50 min

Si hay errores: +10-20 min debugging

============================================================================
PRÓXIMOS PASOS INMEDIATOS
============================================================================

1. Lee este documento completamente
2. Ejecuta: pytest apps/tenant/core/tests/test_ssot_integrity.py -v
   (Fallará con algunos modelos - ESO es esperado)
3. Ejecuta: python tools/refactor_ssot_inheritance.py --dry-run
   (Revisa output)
4. Si todo se ve bien: python tools/refactor_ssot_inheritance.py --execute
5. Crea migraciones: python manage.py makemigrations
6. Ejecuta migraciones: python manage.py migrate
7. Re-ejecuta test para verificar
8. Continúa con services.py si es necesario

============================================================================
DOCUMENTACIÓN Y REFERENCIAS
============================================================================

Modelos Base:
  - SintelTenantBaseModel: apps/tenant/core/models.py

Test de Validación:
  - SSoT Integrity: apps/tenant/core/tests/test_ssot_integrity.py

Herramientas:
  - Auto-refactor: tools/refactor_ssot_inheritance.py

Ejemplos de Refactorización:
  - Cliente: apps/tenant/clientes/models.py ✅
  - Proveedor: apps/tenant/proveedores/models.py ✅
  - Factura: apps/tenant/facturas/models.py ✅

Arquitectura:
  - Documentación: documentacion/arquitectura_general.md
  - AGENTS.md: Reglas de desarrollo

============================================================================
v2.61.4 HERENCIA SSoT - ARQUITECTURA COMPLETA
============================================================================
"""

__all__ = []
