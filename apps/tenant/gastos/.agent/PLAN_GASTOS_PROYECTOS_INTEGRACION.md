# PLAN.md — Integración Gastos ↔ Proyectos
## Vinculación opcional de gastos y actualización automática de costos del proyecto

**Tipo:** Plan maestro de implementación  
**Estado inicial:** `PENDING`  
**Modo de ejecución:** `INSPECT → BASELINE → PLAN → IMPLEMENT → MIGRATE → TEST → AUDIT → FIX → REGRESSION → VERIFY → DOCUMENT → PASS`  
**Regla de control:** ninguna fase se marca `PASS` sin evidencia verificable.

---

# 0. MISIÓN

Implementar la integración entre:

```text
apps/tenant/gastos/
apps/tenant/proyectos/
```

para que un gasto pueda asociarse opcionalmente a un proyecto.

La regla funcional es:

> **Crear un gasto NO debe exigir proyecto.**

Por lo tanto:

```text
Proyecto = opcional al crear gasto
```

El usuario debe poder:

```text
Crear gasto sin proyecto
Crear gasto con proyecto
Editar un gasto posteriormente y asociarlo a un proyecto
Cambiar el proyecto asociado cuando la regla lo permita
Desvincular un gasto cuando la regla lo permita
```

Cuando un gasto quede asociado a un proyecto:

```text
GASTO
   ↓
PROYECTO
   ↓
COSTOS DEL PROYECTO
```

El sistema debe reflejarlo automáticamente en los costos del proyecto.

La implementación debe conservar:

- arquitectura Service Layer;
- separación de dominios;
- multitenancy;
- DSV;
- UUID;
- ausencia de Django Signals para lógica de negocio;
- atomicidad;
- compatibilidad con el código actual;
- compatibilidad con las funciones existentes de Gastos y Proyectos.

---

# 1. ESTADO PERSISTENTE DE LA MISIÓN

La IA editora debe crear y mantener:

```text
docs/remediation/GASTOS_PROYECTOS_IMPLEMENTATION_STATUS.md
```

Ese archivo será el SSoT del progreso de esta misión.

Debe actualizarse después de cada fase.

## Formato obligatorio

```md
# GASTOS ↔ PROYECTOS — IMPLEMENTATION STATUS

Mission: GASTOS_PROYECTOS_01

Current Phase: PHASE-00
Overall Status: RUNNING

| Phase | Status | Started | Finished | Evidence | Notes |
|---|---|---|---|---|---|
| PHASE-00 | RUNNING | ... | ... | ... | ... |
| PHASE-01 | PENDING | | | | |
...

## Current Blockers
- None

## Decisions
- ...

## Modified Files
- ...

## Tests
- ...

## Last Verified At
- ...
```

Estados permitidos:

```text
PENDING
RUNNING
PASS
FAIL
BLOCKED
DEFERRED
```

No usar:

```text
DONE
OK
COMPLETE
```

como sustitutos informales de `PASS`.

---

# 2. REGLA DEL LOOP

Cada fase debe ejecutarse así:

```text
READ
↓
INSPECT
↓
COMPARE WITH BASELINE
↓
PLAN
↓
IMPLEMENT
↓
TEST
↓
AUDIT
↓
FIX
↓
RETEST
↓
UPDATE STATUS
↓
NEXT PHASE
```

Si una fase falla:

```text
NO AVANZAR
```

Investigar la causa raíz.

---

# 3. OBJETIVO FUNCIONAL DEFINITIVO

## Gastos

En el formulario:

```text
Nuevo Gasto
Editar Gasto
```

agregar:

```text
Proyecto (opcional)
```

El campo debe ser:

- opcional;
- filtrado por tenant;
- basado en UUID;
- compatible con el patrón de búsqueda/autocomplete;
- no bloqueante para crear el gasto.

## Proyectos

En el módulo de proyecto debe existir una sección:

```text
Gastos del Proyecto
```

con acción:

```text
Agregar gasto
```

La sección debe mostrar al menos:

```text
Fecha
Gasto / Documento
Proveedor
Descripción
Valor
Estado
Acciones
```

y un total:

```text
Costo de gastos
```

Cuando el gasto se vincule:

```text
Costo de gastos
```

debe actualizarse automáticamente.

---

# 4. MODELO DE NEGOCIO OBJETIVO

El flujo final debe ser:

```text
                         GASTOS
                           │
                           │ Proyecto opcional
                           ▼
                    DocumentoSoporte
                           │
                           │ proyecto_uuid
                           ▼
                       PROYECTO
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      Costos existentes          Gastos asociados
      Mano de obra               │
      Materiales                │
                                ▼
                         Costo de gastos
                                │
                                ▼
                       Costo real proyecto
                                │
                                ▼
                      Utilidad / margen
```

La asociación no debe crear una segunda copia del gasto.

---

# 5. FASE-00 — CONTROL DE INICIO

## Acciones

1. Crear `GASTOS_PROYECTOS_IMPLEMENTATION_STATUS.md`.
2. Registrar:
   - fecha;
   - commit/hash actual si está disponible;
   - rama;
   - entorno;
   - versión Python/Django;
   - estado inicial.
3. No modificar código todavía.

## Evidencia requerida

```text
git status
git rev-parse --short HEAD
python --version
python manage.py check
```

## Resultado

```text
PHASE-00 = PASS
```

solo con evidencia real.

---

# 6. FASE-01 — AUDITORÍA DE GASTOS

Inspeccionar:

```text
apps/tenant/gastos/models.py
apps/tenant/gastos/services/
apps/tenant/gastos/api/
apps/tenant/gastos/templates/
apps/tenant/gastos/static/
apps/tenant/gastos/tests/
apps/tenant/gastos/migrations/
```

Confirmar la estructura actual.

La auditoría existente documenta:

```text
DocumentoSoporte
ResolucionDIAN
GastoBusinessService
DocumentoCRUDService
DocumentoSelector
GastoViewSet
gasto_editor.js
gasto_list.js
```

No confiar únicamente en el documento: confirmar en código.

## Identificar

```text
DocumentoSoporte.uuid
DocumentoSoporte.empresa_id
DocumentoSoporte.total
DocumentoSoporte.subtotal
DocumentoSoporte.activo
DocumentoSoporte.anulado
DocumentoSoporte.proveedor
DocumentoSoporte.fecha
```

---

# 7. FASE-02 — AUDITORÍA DE PROYECTOS

Inspeccionar:

```text
apps/tenant/proyectos/models.py
apps/tenant/proyectos/services/
apps/tenant/proyectos/api/
apps/tenant/proyectos/templates/
apps/tenant/proyectos/static/
apps/tenant/proyectos/tests/
apps/tenant/proyectos/migrations/
```

Confirmar:

```text
Proyecto.uuid
Proyecto.empresa_id
Proyecto.fase_actual
Proyecto.valor_contrato_proyectado
Proyecto.costo_mano_obra_real
Proyecto.costo_materiales_real
Proyecto.utilidad_estimada
Proyecto.margen_rentabilidad
```

El documento auditado establece que actualmente:

```text
costo_mano_obra_real
costo_materiales_real
```

participan en el cálculo financiero del proyecto.

No asumir que ya existe `costo_gastos`.

---

# 8. FASE-03 — AUDITORÍA DE “AGREGAR GASTO”

Buscar en código real:

```text
Agregar gasto
agregar gasto
Gastos del Proyecto
costos del proyecto
costo_gastos
gasto proyecto
```

Determinar si existe ya:

```text
UI
endpoint
modelo
servicio
selector
```

Si no existe:

```text
NO inventar que existe.
```

Marcar explícitamente:

```text
FEATURE_NEW
```

y continuar con implementación.

---

# 9. FASE-04 — DECISIÓN DE RELACIÓN

Auditar primero si la arquitectura global establece un patrón concreto para referencias entre Gastos y Proyectos.

### Opción preferida

Usar patrón de referencia UUID opaca:

```python
proyecto_uuid = models.UUIDField(
    null=True,
    blank=True,
    db_index=True,
    editable=False?  # decidir según patrón de edición
)
```

No crear una FK directa si eso introduce acoplamiento innecesario entre bounded contexts y contradice el patrón de Pull Model ya utilizado por Gastos.

### Regla

La IA editora debe comparar:

```text
FK directa
vs
UUID opaca / Pull Model
```

contra los patrones reales del proyecto.

Seleccionar una sola alternativa.

Documentar la decisión en:

```text
GASTOS_PROYECTOS_IMPLEMENTATION_STATUS.md
```

---

# 10. FASE-05 — CONTRATO SSoT

Definir:

```text
Gasto = dueño del documento de gasto
Proyecto = dueño de sus indicadores y costos consolidados
```

La relación:

```text
Gasto → Proyecto
```

debe permitir consulta desde ambos dominios sin duplicar registros.

Crear matriz:

| Dato | SSoT | Consumo |
|---|---|---|
| Documento | Gastos | Proyectos |
| Total del gasto | Gastos | Proyectos |
| Fecha | Gastos | Proyectos |
| Proveedor | Gastos | Proyectos |
| Proyecto asociado | Relación Gastos | Gastos/Proyectos |
| Costo total de gastos | Proyectos | Dashboard/P&L |
| Utilidad | Proyectos | UI/Reportes |
| Margen | Proyectos | UI/Reportes |

---

# 11. FASE-06 — DEFINICIÓN DEL MONTO QUE IMPACTA COSTOS

Esta fase es obligatoria antes de tocar el cálculo financiero.

Actualmente `DocumentoSoporte` tiene:

```text
subtotal
retenciones
total
```

El plan NO debe asumir automáticamente que:

```text
costo proyecto = total
```

sin revisar la semántica contable existente.

Determinar en el código/documentación cuál monto representa:

```text
costo real del gasto
```

Posibilidades:

```text
subtotal
total
otro valor derivado
```

Si existe contrato contable global, reutilizarlo.

Si no existe, documentar la decisión explícita.

## Regla

Una vez elegido:

```text
GASTO_COST_AMOUNT_SSoT
```

debe ser único.

No permitir que:

```text
UI
service
serializer
P&L
```

calculen montos diferentes.

---

# 12. FASE-07 — REGLAS DE INCLUSIÓN EN COSTOS

Definir exactamente qué gastos cuentan.

Propuesta a validar contra negocio:

```text
incluye:
activo = True
anulado = False
proyecto_uuid = proyecto.uuid
```

Excluir:

```text
anulado = True
activo = False
```

No sumar gastos de otro tenant.

No sumar registros sin proyecto.

No sumar registros de proyectos diferentes.

---

# 13. FASE-08 — CAMPOS DEL GASTO

Si la decisión de FASE-04 es UUID opaco:

agregar:

```text
DocumentoSoporte.proyecto_uuid
```

como:

```text
nullable
blank=True
db_index=True
```

Esto permite:

```text
Gasto sin proyecto
```

desde el primer momento.

## Regla crítica

Nunca:

```python
null=False
```

en el nuevo campo si eso obliga a todos los gastos históricos a tener proyecto.

---

# 14. FASE-09 — MIGRACIÓN SAFE

Crear migración aditiva.

Secuencia:

```text
AddField nullable
↓
Backfill solamente si existe información verificable
↓
crear índices
↓
migrate tenant schemas
```

No crear backfill por inferencia.

Si no existe una relación histórica fiable:

```text
dejar null
```

---

# 15. FASE-10 — DSV DEL PROYECTO

Toda asociación debe validar:

```text
proyecto.uuid
+
empresa_id
```

Ejemplo conceptual:

```python
Proyecto.objects.filter(
    uuid=proyecto_uuid,
    empresa_id=empresa_id
).first()
```

Si no existe:

```text
ValidationError
```

Nunca guardar la relación solamente porque el UUID tiene formato válido.

---

# 16. FASE-11 — CREAR GASTO CON PROYECTO OPCIONAL

Modificar:

```text
GastoBusinessService.procesar_gasto()
```

para recibir:

```text
proyecto_uuid = nullable
```

Flujo:

```text
POST /api/v1/gastos/
        │
        ▼
procesar_gasto()
        │
        ├── resolver empresa
        ├── validar resolución
        ├── validar proveedor
        ├── validar inventario
        ├── validar proyecto si fue enviado
        │
        ▼
DocumentoCRUDService.crear_documento()
        │
        ▼
DocumentoSoporte
```

Si:

```text
proyecto_uuid = null
```

el gasto debe crearse normalmente.

---

# 17. FASE-12 — EDITAR GASTO Y ASOCIACIÓN POSTERIOR

Modificar:

```text
actualizar_documento()
```

o el servicio equivalente.

Permitir:

```text
null → proyecto A
proyecto A → proyecto B
proyecto A → null
```

solo si las reglas de estado/anulación lo permiten.

Cada cambio debe provocar:

```text
recalcular proyecto anterior
+
recalcular proyecto nuevo
```

cuando corresponda.

Todo dentro de una operación transaccional coherente.

---

# 18. FASE-13 — CREAR SERVICIO DE COSTOS DE GASTOS

Implementar un servicio de lectura/agrupación dedicado.

Ejemplo conceptual:

```python
class GastoProyectoCostService:

    @staticmethod
    def get_costos(
        empresa_id,
        proyecto_uuid,
    ):
        ...
```

Debe:

- filtrar tenant;
- filtrar proyecto;
- excluir anulados;
- excluir inactivos;
- devolver suma;
- permitir listado;
- no duplicar reglas.

La suma debe usar el monto definido en FASE-06.

---

# 19. FASE-14 — EVITAR SIGNALS

NO implementar:

```python
post_save
post_delete
pre_save
```

para sincronizar costos.

El proyecto ya utiliza Service Layer y la auditoría de Gastos confirma la regla de no usar signals para negocio.

La actualización debe ocurrir mediante:

```text
GastoBusinessService
DocumentoCRUDService
GastoProyectoCostService
ProyectoFinancialService
```

según el contrato resultante.

---

# 20. FASE-15 — INTEGRACIÓN CON EL CÁLCULO FINANCIERO DE PROYECTO

Auditar:

```text
calcular_indicadores_financieros()
calcular_costo_mano_obra()
calcular_costo_materiales()
```

Actualmente el cálculo documentado es conceptualmente:

```text
Costo total =
    mano de obra
    +
    materiales
```

La nueva integración debe definir:

```text
Costo total =
    mano de obra
    +
    materiales
    +
    gastos
```

solo cuando la nueva regla haya sido validada.

---

# 21. FASE-16 — NUEVO INDICADOR DE GASTOS

Agregar, si no existe:

```text
costo_gastos_real
```

como caché derivada en `Proyecto`.

Debe seguir la misma filosofía que:

```text
costo_mano_obra_real
costo_materiales_real
```

No guardar manualmente el valor desde frontend.

Debe recalcularse desde la fuente real.

---

# 22. FASE-17 — REVALIDAR UTILIDAD Y MARGEN

Una vez incorporado gasto:

```text
utilidad_estimada
```

deberá utilizar:

```text
valor_contrato_proyectado
-
costo_mano_obra_real
-
costo_materiales_real
-
costo_gastos_real
```

y:

```text
margen_rentabilidad =
utilidad_estimada
/
valor_contrato_proyectado
* 100
```

con protección de:

```text
valor_contrato_proyectado = 0
```

No cambiar otras fórmulas fuera de esta integración.

---

# 23. FASE-18 — RECÁLCULO AUTOMÁTICO

El recálculo debe ocurrir en los siguientes escenarios:

### Escenario 1

```text
Crear gasto con proyecto
→ recalcular proyecto
```

### Escenario 2

```text
Crear gasto sin proyecto
→ NO recalcular ningún proyecto
```

### Escenario 3

```text
Editar gasto
proyecto null → proyecto A
→ recalcular A
```

### Escenario 4

```text
Editar gasto
proyecto A → proyecto B
→ recalcular A
→ recalcular B
```

### Escenario 5

```text
Editar importe de gasto
→ recalcular proyecto asociado
```

### Escenario 6

```text
Anular gasto
→ recalcular proyecto
```

### Escenario 7

```text
Desactivar gasto
→ recalcular proyecto
```

### Escenario 8

```text
Desvincular gasto
→ recalcular proyecto
```

---

# 24. FASE-19 — ATOMICIDAD

Todas las operaciones de mutación relacionadas con:

```text
gasto
proyecto
costos
```

deben preservar consistencia.

Regla:

```text
@transaction.atomic
```

Cuando una mutación afecte dos proyectos:

```text
proyecto anterior
+
proyecto nuevo
```

ambos deben quedar consistentemente recalculados o toda la transacción debe revertirse.

Nunca dejar:

```text
gasto movido
pero costo anterior sin recalcular
```

---

# 25. FASE-20 — SELECTORS DE GASTOS POR PROYECTO

Agregar selector dedicado.

Ejemplo:

```python
DocumentoSelector.get_by_proyecto(
    empresa_id,
    proyecto_uuid,
)
```

Debe:

```text
filter(
    empresa_id=empresa_id,
    proyecto_uuid=proyecto_uuid,
    activo=True,
    anulado=False,
)
```

y aplicar:

```text
.only(...)
```

con campos realmente utilizados.

Agregar índices apropiados.

---

# 26. FASE-21 — ÍNDICES

Evaluar índice:

```text
(empresa, proyecto_uuid)
```

y, si el patrón de consultas lo justifica:

```text
(empresa, proyecto_uuid, activo, anulado)
```

No agregar índices innecesarios.

Verificar plan de consulta antes/después cuando sea relevante.

---

# 27. FASE-22 — API DE GASTOS

Actualizar:

```text
gastos.api.js
GastoViewSet
serializers.py
selectors.py
```

El listado de gastos debe exponer:

```text
proyecto_uuid
proyecto_nombre/codigo
```

solo cuando pueda obtenerse eficientemente.

La creación y edición deben aceptar:

```json
{
  "proyecto_uuid": "..."
}
```

nullable.

---

# 28. FASE-23 — ENDPOINT “AGREGAR GASTO” EN PROYECTOS

Si no existe una operación equivalente:

crear una acción dedicada conceptualmente:

```text
POST /api/v1/proyectos/{uuid}/gastos/
```

o el endpoint equivalente que resulte coherente con la arquitectura actual.

Preferir:

```text
proyecto UUID en URL
```

y:

```text
gasto UUID en payload
```

Ejemplo conceptual:

```json
{
  "gasto_uuid": "..."
}
```

El endpoint debe:

1. validar proyecto;
2. validar gasto;
3. validar empresa;
4. verificar que el gasto no pertenezca a otro tenant;
5. evitar duplicar la relación;
6. asociar;
7. recalcular;
8. devolver resumen actualizado.

---

# 29. FASE-24 — BUSCADOR DE GASTOS EN PROYECTO

En:

```text
Proyecto → Gastos → Agregar gasto
```

crear un buscador.

Filtros recomendados:

```text
Proveedor
Número documento
Fecha
Descripción
Valor
```

Mostrar solo gastos:

```text
del mismo tenant
no anulados
no desactivados
```

Preferentemente mostrar primero:

```text
gastos sin proyecto
```

para reducir errores de doble asignación.

---

# 30. FASE-25 — EVITAR DOBLE ASOCIACIÓN

Un gasto debe tener como máximo un proyecto asociado si el modelo de negocio definido es:

```text
DocumentoSoporte → un proyecto
```

Por lo tanto:

```text
Gasto ya asociado a Proyecto A
```

cuando se intente asociar a:

```text
Proyecto B
```

debe:

```text
rechazar
```

o ejecutar una transferencia explícita:

```text
Mover gasto de A → B
```

Nunca cambiar silenciosamente desde el botón:

```text
Agregar gasto
```

sin informar al usuario.

---

# 31. FASE-26 — UI DE PROYECTOS

Modificar:

```text
templates/tenant/proyectos/offcanvas_form.html
```

siguiendo el patrón existente.

Agregar sección:

```text
GASTOS DEL PROYECTO
```

Mostrar:

```text
Cantidad de gastos
Costo de gastos
```

y:

```text
[ Agregar gasto ]
```

Tabla:

```text
Fecha | Proveedor | Documento | Descripción | Valor | Estado | Acción
```

---

# 32. FASE-27 — FRONTEND DE PROYECTOS

Actualizar:

```text
proyectos.api.js
proyectos_editor.js
```

Crear namespace únicamente si sigue el patrón existente.

No crear framework nuevo.

Ejemplo:

```text
window.Sintel.ProyectosGastos
```

Métodos conceptuales:

```text
list(proyectoUuid)
search()
agregar(gastoUuid, proyectoUuid)
desvincular(gastoUuid)
refresh()
```

No duplicar URLs fuera de:

```text
proyectos.api.js
```

---

# 33. FASE-28 — FRONTEND DE GASTOS

Modificar:

```text
gasto_editor.js
```

Agregar:

```text
Proyecto (opcional)
```

Preferentemente autocomplete:

```text
>= 2 caracteres
debounce
GET proyectos
selección
UUID oculto
```

Patrón equivalente al actual:

```text
initMovimientoSearch()
```

si corresponde.

No reutilizar funciones que mezclen dominios si eso genera acoplamiento incorrecto.

---

# 34. FASE-29 — DETALLE DE GASTO

En:

```text
offcanvas_detalle_gasto.html
```

mostrar:

```text
Proyecto asociado
```

cuando exista.

Ejemplo:

```text
Proyecto:
PRJ-2026-0007 — Instalación CCTV Cliente X
```

Si no existe:

```text
Proyecto:
Sin proyecto
```

---

# 35. FASE-30 — DETALLE DE PROYECTO

En el detalle del proyecto mostrar:

```text
Costos

Mano de obra
Materiales
Gastos
Costo total
Utilidad
Margen
```

Debe quedar claramente separado:

```text
Planeado
Real
```

si la UI actual diferencia esos conceptos.

No mezclar:

```text
ItemPresupuestoProyecto
```

con:

```text
DocumentoSoporte
```

Los primeros siguen siendo presupuesto planeado.

Los segundos son gasto real.

---

# 36. FASE-31 — PRESUPUESTO VS GASTO REAL

Mantener separados:

```text
PRESUPUESTO
ItemPresupuestoProyecto
```

y:

```text
GASTO REAL
DocumentoSoporte asociado al proyecto
```

Nunca sumar el mismo gasto en:

```text
presupuesto
+
gastos reales
```

salvo que exista una regla empresarial explícita.

---

# 37. FASE-32 — ESTADO CIERRE

La auditoría de Proyectos documenta restricciones en `CIERRE`.

Determinar exactamente si:

```text
Agregar gasto
Editar gasto asociado
Desvincular gasto
```

está permitido en `CIERRE`.

No inferirlo.

### Si la regla actual bloquea cambios financieros en CIERRE

respetarla.

### Si negocio requiere corrección posterior

crear una operación explícita y auditada.

Nunca saltarse la protección del proyecto.

---

# 38. FASE-33 — ANULACIÓN Y DESACTIVACIÓN

Verificar el flujo de Gastos:

```text
Anular
Desactivar
Eliminar
```

La auditoría actual indica:

```text
anulado = True
```

y:

```text
activo = False
```

son conceptos diferentes.

Definir exactamente qué ocurre con el costo:

```text
anular → sale de costo
desactivar → sale de costo
eliminar → recalcular
```

según el contrato real del módulo.

Probar cada caso.

---

# 39. FASE-34 — TEST UNITARIO GASTOS

Agregar tests para:

```text
crear gasto sin proyecto
crear gasto con proyecto
editar y asociar proyecto
editar y desasociar proyecto
mover gasto de proyecto
rechazar proyecto de otro tenant
rechazar UUID inexistente
```

---

# 40. FASE-35 — TEST DE COSTOS

Crear tests:

```text
1 gasto asociado
2 gastos asociados
gasto anulado
gasto desactivado
gasto sin proyecto
gastos múltiples proyectos
```

Validar:

```text
costo_gastos_real
costo_total
utilidad
margen
```

---

# 41. FASE-36 — TEST DE RECÁLCULO

Probar secuencia completa:

```text
Proyecto A
costo inicial = X

Crear gasto 100
→ costo = X + 100

Editar gasto 150
→ costo = X + 150

Anular
→ costo = X

Desactivar
→ costo = X

Reactiva/reintegra según regla real
→ costo se actualiza

Mover a Proyecto B
→ A disminuye
→ B aumenta
```

No aceptar resultados calculados solamente sobre el objeto Python en memoria.

Usar:

```text
refresh_from_db()
```

cuando corresponda.

---

# 42. FASE-37 — TEST DE MULTITENANT

Crear:

```text
Tenant A
Tenant B
```

y verificar:

```text
Gasto A
Proyecto A
Proyecto B
Gasto B
```

Casos:

```text
Gasto A → Proyecto A = PASS
Gasto A → Proyecto B = REJECT
Gasto B → Proyecto A = REJECT
```

Nunca revelar datos cross-tenant.

---

# 43. FASE-38 — TEST DE CONCURRENCIA

Probar:

```text
dos usuarios agregando el mismo gasto al mismo proyecto
```

y:

```text
dos usuarios moviendo el mismo gasto entre proyectos
```

No permitir doble asociación inconsistente.

Usar:

```text
select_for_update()
UniqueConstraint
```

solo cuando realmente corresponda.

---

# 44. FASE-39 — TEST DE ATOMICIDAD

Simular:

```text
actualizar gasto
+
fallo durante recálculo
```

Resultado esperado:

```text
ROLLBACK
```

No debe quedar:

```text
gasto actualizado
proyecto desactualizado
```

---

# 45. FASE-40 — TEST DE REGRESIÓN GASTOS

Ejecutar:

```bash
python manage.py test apps.tenant.gastos
```

Luego todas las suites reales relacionadas.

No declarar PASS si aparecen fallas no relacionadas sin clasificación.

---

# 46. FASE-41 — TEST DE REGRESIÓN PROYECTOS

Ejecutar:

```bash
python manage.py test apps.tenant.proyectos
```

La auditoría existente documenta una línea base de:

```text
21/21 PASS
```

La nueva implementación debe conservar esa cobertura y añadir casos específicos de gastos.

---

# 47. FASE-42 — REGRESIÓN CROSS-APP

Ejecutar pruebas de:

```text
gastos
proyectos
proveedores
contabilidad
inventario
```

especialmente:

```text
retenciones
movimientos inventario
P&L
cierre
multitenant
```

---

# 48. FASE-43 — MANAGE.PY CHECK

Ejecutar:

```bash
python manage.py check
```

Debe devolver:

```text
0 issues
```

---

# 49. FASE-44 — MIGRACIONES

Verificar:

```bash
python manage.py makemigrations --check
```

No deben quedar migraciones pendientes.

Luego aplicar:

```bash
python manage.py migrate
```

y el comando real de migración de schemas tenant:

```bash
make migrate-tenants
```

o el mecanismo existente.

---

# 50. FASE-45 — PYCOMPILE

Para todo Python modificado:

```bash
python -m py_compile ...
```

o el mecanismo global del proyecto.

No aceptar:

```text
SyntaxError
```

---

# 51. FASE-46 — FRONTEND VALIDATION

Verificar:

```text
gasto_editor.js
gasto_list.js
gastos.api.js
proyectos.api.js
proyectos_editor.js
```

Comprobar:

```text
sin parseInt(UUID)
sin URLs duplicadas
sin listeners duplicados
sin offcanvas zombies
sin errores de consola
```

---

# 52. FASE-47 — N+1 Y PERFORMANCE

Auditar:

```text
lista gastos
detalle gasto
lista gastos proyecto
detalle proyecto
```

Evitar consultas por fila.

Usar:

```text
select_related
prefetch_related
only
aggregate
```

cuando corresponda.

Medir número de queries si el patrón actual de tests lo permite.

---

# 53. FASE-48 — AUDITORÍA DE SEGURIDAD

Buscar:

```text
IDOR
cross-tenant
UUID lookup
empresa_id
permisos
serializer write fields
```

Confirmar que el frontend nunca sea la única barrera.

---

# 54. FASE-49 — AUDITORÍA DE CÓDIGO MUERTO Y DUPLICACIÓN

Después de implementar:

buscar:

```text
helpers duplicados
selectors duplicados
sumas duplicadas
cálculos P&L duplicados
endpoints duplicados
JS duplicado
```

Eliminar solo código demostrado como muerto.

No refactorizar por estética.

---

# 55. FASE-50 — AUDITORÍA DE CONSISTENCIA FINANCIERA

Comparar:

```text
DocumentoSoporte
Contabilidad
Proyecto
Dashboard
```

y determinar que todos utilizan la misma interpretación del monto del gasto.

No permitir:

```text
Gastos = subtotal
Proyecto = total
Dashboard = otro valor
```

sin una justificación explícita.

---

# 56. FASE-51 — AUDITORÍA DE UX

Verificar flujo:

```text
Nuevo gasto
→ Proyecto opcional
```

Debe quedar claro:

```text
Proyecto (opcional)
```

No mostrar error si está vacío.

Luego:

```text
Proyecto
→ Gastos
→ Agregar gasto
→ Buscar gasto
→ Seleccionar
→ Confirmar
→ Actualización inmediata
```

La UI debe comunicar:

```text
Gasto asociado correctamente
Costo del proyecto actualizado
```

sin prometer una operación que el backend no confirmó.

---

# 57. FASE-52 — UX DE DESASOCIACIÓN

Agregar acción:

```text
Desvincular
```

cuando corresponda.

Confirmar:

```text
¿Desvincular este gasto del proyecto?
```

Después:

```text
recalcular
actualizar lista
actualizar KPI
```

No eliminar el gasto.

---

# 58. FASE-53 — AUDITORÍA DE PROYECTO CERRADO

Probar:

```text
Proyecto CIERRE
```

y verificar si:

```text
Agregar gasto
Mover gasto
Desvincular gasto
```

está:

```text
permitido
```

o:

```text
bloqueado
```

según las reglas actuales.

La nueva feature nunca debe saltarse el bloqueo ya establecido.

---

# 59. FASE-54 — DOCUMENTACIÓN TÉCNICA

Actualizar:

```text
AUDITORIA_FLUJO_GASTOS.md
AUDITORIA_FLUJO_COMPLETO(5).md
```

solo si son documentos activos/SSoT del proyecto.

Preferentemente crear:

```text
docs/remediation/GASTOS_PROYECTOS_INTEGRATION.md
```

con:

```text
modelo
API
Service Layer
SSoT
recálculo
reglas
tests
decisiones
```

---

# 60. FASE-55 — DOCUMENTACIÓN DE ESTADO

Actualizar:

```text
GASTOS_PROYECTOS_IMPLEMENTATION_STATUS.md
```

con:

```text
PHASE
STATUS
FILES CHANGED
MIGRATIONS
TESTS
BLOCKERS
DECISIONS
EVIDENCE
```

---

# 61. FASE-56 — RELEASE GATE

No declarar la misión terminada hasta cumplir:

```text
[ ] Gasto puede crearse sin proyecto
[ ] Gasto puede crearse con proyecto
[ ] Proyecto usa UUID seguro
[ ] DSV empresa/proyecto PASS
[ ] DSV gasto/proyecto PASS
[ ] Vinculación funciona
[ ] Edición funciona
[ ] Desvinculación funciona
[ ] Cambio de proyecto funciona según regla
[ ] Gasto anulado deja de impactar costo
[ ] Gasto desactivado deja de impactar costo según regla
[ ] Costo de gastos se recalcula
[ ] Costo total se recalcula
[ ] Utilidad se recalcula
[ ] Margen se recalcula
[ ] UI Proyecto muestra gastos
[ ] UI muestra "Agregar gasto"
[ ] UI Gasto muestra proyecto opcional
[ ] API documentada
[ ] Sin Django Signals
[ ] Sin duplicación de documentos
[ ] Sin datos cross-tenant
[ ] Migraciones aplicadas
[ ] manage.py check PASS
[ ] tests Gastos PASS
[ ] tests Proyectos PASS
[ ] cross-app regression PASS
[ ] py_compile PASS
[ ] documentación actualizada
[ ] estado persistente actualizado
```

---

# 62. FASE-57 — CRITERIOS DE NO REGRESIÓN

Está prohibido:

- convertir Proyecto en campo obligatorio del gasto;
- romper la creación de Gastos existentes;
- romper proveedores;
- romper retenciones;
- romper Pull Model de inventario;
- modificar la semántica de DocumentoSoporte sin necesidad;
- duplicar DocumentoSoporte;
- crear registros sombra de gasto en Proyectos;
- crear Django Signals;
- mezclar presupuesto planeado con gasto real;
- saltarse CIERRE;
- eliminar DSV;
- exponer PKs secuenciales;
- usar `parseInt()` sobre UUID;
- recalcular costos únicamente en JavaScript;
- almacenar manualmente una cifra de costo que puede obtenerse de los gastos;
- permitir cross-tenant;
- sobrescribir datos fiscales/contables del gasto.

---

# 63. FASE-58 — LOOP FINAL

Ejecutar:

```text
INSPECT
↓
IMPLEMENT
↓
TEST
↓
AUDIT
↓
FIX
↓
TEST AGAIN
↓
REGRESSION
↓
VERIFY
↓
DOCUMENT
↓
RELEASE GATE
```

Después de cada corrección:

```text
TEST LOCAL DEL CAMBIO
+
TEST DE MÓDULO
+
TEST CROSS-APP
```

---

# 64. FORMATO DE REPORTE FINAL DE LA IA EDITORA

La IA deberá terminar actualizando el estado con:

```md
## FINAL REPORT

Mission: GASTOS_PROYECTOS_01
Status: PASS | PASS_WITH_DEFERRED | BLOCKED | FAIL

### Implemented
- ...

### Models
- ...

### Migrations
- ...

### Services
- ...

### APIs
- ...

### Frontend
- ...

### Financial Calculation
- ...

### Tests
- Gastos: X/X
- Proyectos: X/X
- Cross-App: X/X

### Security
- ...

### Performance
- ...

### Deferred
- ...

### Remaining Risks
- ...

### Evidence
- commands
- test outputs
- migration names
```

No inventar resultados.

---

# 65. MODELO FUNCIONAL FINAL

El sistema debe comportarse así:

```text
CASO A
Nuevo gasto
Proyecto = vacío
↓
Gasto creado
↓
Sin impacto en proyectos
```

```text
CASO B
Nuevo gasto
Proyecto = PRJ-A
↓
Gasto creado
↓
PRJ-A recalculado
↓
Costo de gastos actualizado
↓
Costo total actualizado
↓
Utilidad/margen actualizados
```

```text
CASO C
Gasto existente sin proyecto
↓
Editar
↓
Asignar PRJ-A
↓
PRJ-A recalculado
```

```text
CASO D
Gasto PRJ-A
↓
Mover a PRJ-B
↓
PRJ-A recalculado
↓
PRJ-B recalculado
```

```text
CASO E
Gasto PRJ-A
↓
Anular
↓
Gasto excluido del costo
↓
PRJ-A recalculado
```

```text
CASO F
PRJ-A
↓
Agregar gasto existente
↓
Confirmar
↓
Asociación persistida
↓
Costo actualizado
```

---

# 66. PRINCIPIO FINAL

La arquitectura debe terminar respetando:

```text
GASTOS
= dueño del gasto y su evidencia

PROYECTOS
= dueño de los costos consolidados del proyecto

CONTABILIDAD
= dueño de la interpretación contable

PULL MODEL
= mecanismo de consumo entre dominios

SERVICE LAYER
= mecanismo de coordinación de cambios

NO SIGNALS
= regla de negocio

UUID + DSV
= seguridad multitenant

COSTO REAL
= dato derivado de fuentes reales, no captura manual
```

La integración debe ser:

```text
simple
explícita
atómica
auditable
multitenant
idempotente
sin duplicaciones
sin romper el sistema actual
```

# FIN DEL PLAN
