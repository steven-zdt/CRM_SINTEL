# PLAN DE ACCIÓN — INTER-APP-01
## Estabilización de SSoT, Contratos y Relaciones entre Apps — SINTEL ERP

**Versión:** 1.0.0  
**Fecha:** 2026-10-05  
**Tipo:** Plan ejecutable por IA editora / coding agent  
**Estrategia:** Loop por fases con gates estrictos  
**Objetivo:** garantizar estabilidad de lógica de negocio, relaciones entre apps, propiedad de datos, estados, referencias, aislamiento tenant e integridad inter-app antes de continuar con nuevas funcionalidades de alto impacto.

---

# 0. Propósito

Este plan NO busca agregar nuevas funcionalidades de negocio de manera inmediata.

Busca establecer primero un **baseline inter-app verificable** para que las futuras evoluciones del ERP no continúen acumulando acoplamiento, duplicación de SSoT, reglas duplicadas o relaciones difíciles de mantener.

La arquitectura actual ya dispone de:

- Service Layer con `BusinessService`, `CRUDService` y `selectors`.
- DSV para validación de pertenencia al tenant.
- `SintelTenantBaseModel` como base tenant.
- UUID como lookup público.
- `OrganizationalContext/Scope`.
- `tools/organizational_governance/` y `dependencies.py`.
- Contabilidad bajo modelo Pull.
- Contratos inter-app existentes en varios dominios.
- Máquinas de estados reales en dominios como Cotizaciones, Requisiciones y Proyectos.

La misión debe **consolidar y verificar** estas decisiones, no crear un segundo framework paralelo.

---

# 1. Resultado esperado

Al finalizar el plan debe existir una arquitectura donde, para cada relación entre apps relevante, pueda responderse de forma explícita:

1. ¿Quién es dueño del dato?
2. ¿Quién puede escribirlo?
3. ¿Quién puede leerlo?
4. ¿Qué contrato utiliza la app consumidora?
5. ¿Qué estado pertenece al dominio propietario?
6. ¿La relación es FK, OneToOne, soft-UUID, snapshot o bridge?
7. ¿Qué ocurre al eliminar/anular el origen?
8. ¿Cómo se garantiza tenant isolation?
9. ¿Cómo se garantiza alcance Empresa/Sede/Área?
10. ¿Qué operación es idempotente y qué pasa ante reintento?
11. ¿Qué ocurre si la app origen deja de existir o cambia de estado?
12. ¿Qué test demuestra que la relación sigue estable?

El criterio de éxito no será “el código funciona”, sino:

> **cada dependencia importante entre apps debe tener un propietario, un contrato, una regla de escritura, una regla de lectura y una prueba verificable.**

---

# 2. Reglas obligatorias para la IA editora

## 2.1. SSoT

- Una entidad de negocio tiene un único propietario.
- Una regla de negocio crítica tiene una única fuente de verdad.
- Una app consumidora no replica reglas del propietario.
- No crear modelos duplicados para representar el mismo concepto.
- No crear un segundo mecanismo de gobernanza si ya existe uno.

## 2.2. Service Layer

- `ViewSet` permanece delgado.
- `Serializer` valida forma, tipos y contrato HTTP; no gobierna procesos complejos.
- `BusinessService` contiene reglas, DSV, orquestación, idempotencia y transiciones.
- `CRUDService` concentra persistencia transaccional.
- `Selector` concentra lecturas.
- No introducir lógica de negocio en señales Django.

## 2.3. Relaciones inter-app

Antes de cambiar una relación existente, identificar su uso real en código.

Prohibido:

- Cambiar FK↔UUID masivamente sin análisis de consumidores.
- Eliminar un campo “legacy” solo porque parece redundante.
- Cambiar `CASCADE`, `PROTECT` o `SET_NULL` sin analizar ciclo de vida.
- Crear una relación adicional para resolver un problema que ya tiene contrato existente.
- Hacer consultas directas al modelo de otra app cuando existe un contrato inter-app aprobado.

## 2.4. Contabilidad

Mantener el principio documentado: las apps fuente no escriben directamente `AsientoContable`/`MovimientoContable`; Contabilidad es el propietario del dominio contable y opera por Pull cuando corresponda.

## 2.5. Tenant / DSV

Toda mutación inter-app debe validar como mínimo:

- existencia del objetivo en el tenant actual,
- pertenencia de las referencias al tenant actual,
- membresía/autorización,
- alcance organizacional cuando aplique.

## 2.6. Seguridad de cambio

Cada fase debe ser pequeña y reversible.

No mezclar en una misma fase:

- refactor arquitectónico,
- cambio de modelo,
- rediseño de UI,
- nueva funcionalidad,
- migración masiva de datos,

salvo que la dependencia sea obligatoria para el gate de esa fase.

---

# 3. Patrón LOOP obligatorio por fase

Todas las fases siguen el mismo ciclo:

```text
INSPECT
   ↓
MAP
   ↓
DECIDE
   ↓
IMPLEMENT
   ↓
VERIFY
   ↓
REGRESSION
   ↓
GATE
   ↓
NEXT PHASE
```

## 3.1. INSPECT

Leer primero:

- `AGENTS.md`.
- Arquitectura general vigente.
- Auditoría `.agent/` de cada app afectada.
- ADRs aplicables.
- Tests existentes.
- Servicios y contratos existentes.

La IA debe inspeccionar código real antes de proponer cambios.

## 3.2. MAP

Construir inventario concreto de:

- modelos,
- FKs,
- OneToOne,
- soft-UUID,
- snapshots,
- selectors,
- services,
- endpoints,
- consumers,
- estados,
- señales,
- tareas Celery,
- imports inter-app.

## 3.3. DECIDE

Clasificar cada hallazgo:

```text
KEEP
CONSOLIDATE
REWIRE
DEPRECATE
REMOVE
DEFER
```

Nunca cambiar por preferencia estilística si no existe una razón funcional o arquitectónica demostrable.

## 3.4. IMPLEMENT

Modificar solo lo necesario para cerrar el objetivo de la fase.

## 3.5. VERIFY

Verificar:

- `manage.py check`
- `makemigrations --check --dry-run`
- tests focalizados,
- tests de integración,
- tenant isolation,
- regresiones del dominio afectado.

Usar la estrategia de ejecución de tests definida por el repositorio y mantener consistencia con el baseline vigente.

## 3.6. REGRESSION

Ejecutar las suites de las apps origen y consumidoras.

Una modificación inter-app no puede cerrarse usando solamente la suite de la app modificada.

## 3.7. GATE

No avanzar si existe alguno de estos estados:

```text
CRITICAL_FAILURE
DATA_INTEGRITY_RISK
TENANT_ISOLATION_RISK
SSOT_AMBIGUOUS
UNVERIFIED_CONTRACT
REGRESSION_FAILURE
MIGRATION_RISK_UNASSESSED
```

Todo hallazgo no corregido debe quedar como `DEFERRED` explícito y con razón.

---

# 4. FASE 0 — Baseline y congelamiento de cambios

## Objetivo

Establecer una fotografía verificable del estado real antes de tocar relaciones.

## Trabajo

1. Leer arquitectura general vigente.
2. Leer `AGENTS.md`.
3. Identificar las apps tenant actuales.
4. Identificar las apps public involucradas en bridges.
5. Inventariar contratos ya existentes.
6. Inventariar reglas de gobernanza ya existentes.
7. Registrar el estado inicial de tests/checks.
8. Crear un archivo temporal de trabajo de la misión, no una nueva fuente de verdad de arquitectura.

## Entregable interno

```text
INTER_APP_BASELINE
- apps involucradas
- contratos existentes
- relaciones críticas
- estados críticos
- hallazgos abiertos
- tests disponibles
```

## Gate 0

PASS solamente si:

- se conoce el baseline,
- no se inventaron relaciones,
- no existen contradicciones sin registrar,
- se identificaron apps consumidoras y propietarias.

---

# 5. FASE 1 — Matriz SSoT por dominio

## Objetivo

Definir formalmente quién es propietario de cada dato y cada estado crítico.

## Dominios mínimos

Analizar como mínimo:

```text
Empresa / Sedes / Áreas
Clientes
Proveedores
Cotizaciones
Ventas
Facturas
Proyectos
Gastos
Compras
Requisiciones
Inventario
Bancos
Contabilidad
Empleados / Nómina
Aprobaciones
```

## Para cada dominio

Crear una matriz temporal con:

| Dominio | SSoT | Escritura | Lectura externa | Estado dueño | Histórico | Observación |
|---|---|---|---|---|---|---|
| Cliente | clientes | clientes | contrato/selector | clientes | clientes | validar usos |
| Cotización | cotizaciones | cotizaciones | contrato | cotizaciones | cotizaciones | estados propios |
| Venta | ventas | ventas | contrato | ventas | ventas | revisar FKs |
| Factura | facturas | facturas | `FacturaInterAppAPI` u otro contrato existente | facturas | facturas | fiscal exclusivo |
| Proyecto | proyectos | proyectos | contrato | proyectos | proyectos | lifecycle Fase 0-4 |
| Requisición | requisiciones | requisiciones | compras/proyecto según contrato | requisiciones | requisiciones | workflow propio |
| Orden Compra | compras | compras | contrato | compras | compras | revisar requisito |
| Inventario | inventario | inventario/Kardex | selectors/contrato | inventario | inventario | puerta única |
| Gasto | gastos | gastos | proyectos/contabilidad según contrato | gastos | gastos | revisar integración |
| Contabilidad | contabilidad | contabilidad | pull desde fuentes | contabilidad | contabilidad | no escritura externa |

La tabla anterior es una plantilla de trabajo: **la IA debe verificar cada fila en código antes de marcarla como definitiva.**

## Gate 1

No puede quedar un mismo campo de estado con dos propietarios conceptuales.

No puede existir una regla crítica implementada simultáneamente en dos apps sin justificación documentada.

---

# 6. FASE 2 — Auditoría de relaciones y ciclo de vida

## Objetivo

Determinar si las relaciones actuales representan correctamente el ciclo de vida real.

## Auditar

Buscar repo-wide:

```text
ForeignKey
OneToOneField
ManyToMany
PROTECT
CASCADE
SET_NULL
RESTRICT
DO_NOTHING
uuid
*_uuid
snapshot
historical
legacy
compatibility
```

## Para cada relación

Clasificar:

```text
FK_REAL
ONE_TO_ONE
SOFT_UUID
SNAPSHOT
BRIDGE
DERIVED
LEGACY
```

Y además:

```text
OBLIGATORIA
OPCIONAL
TEMPORAL
HISTORICA
```

## Preguntas obligatorias

### Eliminación

- ¿Puede eliminarse el origen?
- ¿Debe sobrevivir el destino?
- ¿Se necesita `PROTECT`?
- ¿`SET_NULL` representa realmente una referencia opcional?
- ¿`CASCADE` podría destruir histórico?

### Reversión

- ¿Qué pasa cuando el documento origen se anula?
- ¿Qué pasa cuando cambia de estado?
- ¿Qué relaciones quedan congeladas como snapshot?

### Datos históricos

- ¿Debe conservarse el dato aunque el catálogo actual cambie?
- ¿El consumidor necesita una copia histórica o una lectura viva?

## Gate 2

No cambiar relaciones todavía si el ciclo empresarial no está claro.

Si existe incertidumbre, marcar `DEFERRED` y continuar sin alterar esquema.

---

# 7. FASE 3 — Contratos de lectura inter-app

## Objetivo

Sustituir accesos frágiles entre apps por contratos claros allí donde corresponda, sin crear duplicación.

## Trabajo

Identificar patrones como:

```text
App A → import directo de Model App B
App A → `.objects.get()` sobre Model App B
App A → acceso a atributos internos de App B
App A → reimplementación de selector de App B
```

Para cada caso:

1. Verificar si ya existe un contrato.
2. Verificar si ya existe selector reutilizable.
3. Verificar si la dependencia está permitida por gobernanza.
4. Solo crear contrato nuevo cuando no exista uno adecuado.

## Contrato recomendado

Preferir contratos explícitos de lectura del estilo:

```python
class FacturaInterAppAPI:
    @staticmethod
    def get_by_id(...):
        ...
```

El nombre exacto debe reutilizar contratos existentes cuando ya existan.

## Regla

Un contrato inter-app de lectura NO debe permitir accidentalmente escritura.

## Gate 3

- cero contratos duplicados,
- cero acceso directo innecesario al modelo propietario,
- DSV cuando corresponda,
- tests de consumidor y propietario.

---

# 8. FASE 4 — Contratos de escritura y comandos de negocio

## Objetivo

Garantizar que solamente el propietario del dominio modifique sus datos y estados.

## Revisar especialmente

```text
CotizacionService.cambiar_estado()
VentaBusinessService.*
FacturaBusinessService.*
ProyectoWorkflow / cambiar_fase_proyecto()
RequisicionBusinessService.*
OrdenCompraBusinessService.*
KardexService.*
GastoBusinessService.*
Contabilidad extractors / services
```

Los nombres anteriores son puntos de auditoría; la IA debe confirmar su existencia actual antes de editarlos.

## Reglas

Ejemplo conceptual:

```text
Otra app NO hace:
    factura.estado = ...

Otra app DEBE hacer:
    FacturaBusinessService.<operacion_autorizada>(...)
```

Lo mismo para proyectos, ventas, compras, inventario y demás dominios.

## Gate 4

Debe existir una sola puerta válida para cada mutación crítica auditada.

PATCH genérico no debe convertirse en bypass de una máquina de estados.

---

# 9. FASE 5 — Auditoría de estados y máquinas de transición

## Objetivo

Garantizar coherencia de estados entre dominios relacionados.

## Construir mapa

```text
Cotización
BORRADOR → ENVIADA → APROBADA → ...

Venta
BORRADOR → ... → FACTURADA_DIAN / ANULADA

Factura
estado fiscal propio

Requisición
BORRADOR → PENDIENTE_APROBACION → APROBADA → ...

OrdenCompra
workflow propio

Proyecto
BORRADOR → INICIO → PLANEACION → EJECUCION → CIERRE
```

La IA debe usar los nombres reales del código, no asumir nombres históricos.

## Reglas

- Los estados de una app no se sincronizan mediante campos duplicados “espejo” salvo que exista una necesidad explícita.
- Una transición de un dominio consumidor no debe forzar directamente un estado interno de otro dominio.
- Las condiciones inter-app se consultan mediante contrato/selector autorizado.
- Las transiciones críticas son atómicas.
- Los reintentos no deben producir transiciones duplicadas.

## Caso especial: Proyectos

Verificar que el ciclo establecido sea coherente:

```text
FASE 0 Borrador
       ↓
FASE 1 Inicio / Viabilidad / Aprobación
       ↓
FASE 2 Planeación
       ↓
FASE 3 Ejecución
       ↓
FASE 4 Cierre / Consolidación
```

En particular:

- Fase 3 es la fase operativa.
- `porcentaje_avance` pertenece a ejecución.
- `estado_tarea` pertenece a ejecución.
- Fase 4 representa un proyecto ya terminado.
- Fase 4 no debe ser una segunda pantalla operativa.
- El gate de Cierre debe depender de condiciones reales de ejecución y documentos finales.

## Gate 5

No puede existir un camino alterno por PATCH, endpoint secundario, señal o tarea que salte las reglas de transición.

---

# 10. FASE 6 — Idempotencia y atomicidad inter-app

## Objetivo

Evitar duplicados y datos parciales cuando una operación cruza varios dominios.

## Revisar

Especialmente:

```text
Cotizacion → Venta
Venta → Factura
Factura → Bancos
Proyecto → Compras
Proyecto → Gastos
OrdenCompra → RecepcionCompra → Inventario
Inventario → Contabilidad
```

## Para cada flujo

Determinar:

- operación natural de idempotencia,
- clave de idempotencia,
- lock necesario,
- `select_for_update` necesario,
- punto exacto de la transacción,
- comportamiento ante retry,
- comportamiento ante doble click / doble POST / retry Celery.

## Regla

Una operación inter-app crítica debe ser segura ante reintento.

Nunca aceptar como suficiente:

```python
try:
    realizar_operacion()
except Exception:
    return error
```

si la transacción queda potencialmente en estado parcial.

## Gate 6

Para cada flujo crítico:

```text
SUCCESS → exactamente una operación efectiva
RETRY   → resultado estable / idempotente
ERROR   → rollback
```

---

# 11. FASE 7 — Tenant Isolation + Empresa/Sede/Área

## Objetivo

Confirmar que las relaciones inter-app no permitan fuga de información ni violen el alcance organizacional.

## Verificar

- `empresa_id` en toda mutación.
- DSV para relaciones cruzadas.
- Membership activa.
- `OrganizationalContext` / `OrganizationalScope` donde aplique.
- filtros por sede/área cuando correspondan.
- cero acceso indirecto al tenant de otra empresa.

## Casos de prueba mínimos

```text
Tenant A → recurso A = permitido
Tenant A → recurso B = rechazado

Usuario con alcance SEDE → recurso de otra sede = rechazado
Usuario con alcance AREA → recurso fuera de área = rechazado
```

## Gate 7

Cualquier hallazgo de aislamiento es bloqueante.

---

# 12. FASE 8 — Gobernanza automática y grafo de dependencias

## Objetivo

Convertir el conocimiento obtenido en reglas que impidan regresiones futuras.

## NO crear

- segundo grafo,
- segundo sistema de governance,
- segundo catálogo de permisos,
- segundo sistema de SSoT.

## Reutilizar

```text
tools/organizational_governance/
dependencies.py
rules.py
EKG existente cuando corresponda
```

## Extender solo si la evidencia lo exige

Las reglas deben detectar, cuando sea viable:

```text
UNKNOWN dependency
FORBIDDEN dependency
nuevo acceso directo no autorizado
nuevo modelo duplicado
mutación desde app no propietaria
contrato inter-app inexistente
bypass de estado
modelo fuera del patrón tenant
```

## Gate 8

Ejecutar el reporte de gobernanza y confirmar:

```text
FINAL STATUS: PASS
```

o equivalente real del comando vigente.

Si aparece una dependencia legítima nueva, documentarla y registrar la decisión en el mecanismo existente en vez de desactivar la regla.

---

# 13. FASE 9 — Regresión transversal de procesos de negocio

## Objetivo

Demostrar que la arquitectura estabilizada no rompe los flujos principales.

## Flujo A — Comercial

```text
Cliente
 → Cotización
 → Venta
 → Factura externa / fiscal
 → Cartera / Bancos
 → Contabilidad Pull
```

## Flujo B — Proyecto

```text
Cotización
 → Proyecto
 → Inicio / Viabilidad / Aprobación
 → Planeación
 → Ejecución
 → Gastos / Compras / Recursos
 → Cierre
```

## Flujo C — Abastecimiento

```text
Requisición
 → Aprobación
 → OrdenCompra
 → Recepción
 → Inventario / Kardex
 → Contabilidad
```

## Flujo D — Inventario

```text
Compra / Venta / Traslado
 → Kardex
 → Stock por sede
 → Contabilidad Pull
```

## Flujo E — Aprobaciones

```text
Documento
 → SolicitudAprobacion
 → Historial
 → Decisión
 → desbloqueo / rechazo
```

## Gate 9

Ejecutar regresión por dominio propietario + consumidores.

No cerrar por “tests unitarios verdes” si falla un contrato HTTP real o un flujo cruzado.

---

# 14. FASE 10 — Decisiones diferidas y deuda residual

## Objetivo

Separar lo realmente bloqueante de lo que debe quedar intencionalmente pendiente.

## Clasificación obligatoria

```text
P0 — bloquea producción / integridad
P1 — riesgo funcional importante
P2 — deuda técnica no bloqueante
DEFERRED — decisión de negocio pendiente
OUT_OF_SCOPE — fuera de esta misión
```

## Criterio

Un `DEFERRED` no es un fallo.

Debe contener:

- qué se pospuso,
- por qué,
- qué información falta,
- impacto,
- condición para reabrirlo.

Ejemplo aplicable al baseline actual: algunas decisiones de Requisiciones siguen documentadas como diferidas. No deben resolverse arbitrariamente dentro de esta misión si no existe una decisión de negocio suficiente.

## Gate 10

Debe existir una lista final de:

```text
CLOSED
DEFERRED
OUT_OF_SCOPE
BLOCKED
```

sin mezclar estados.

---

# 15. FASE 11 — Preparación para la siguiente misión funcional

## Objetivo

Solo después de cerrar las fases anteriores, seleccionar la siguiente funcionalidad de negocio.

La documentación general identifica como siguiente flujo funcional pendiente **BANCOS-04**, basado en:

```text
Extracto
 → Movimiento
 → Matching
 → Aplicación 1:N
 → Conciliación
```

consumiendo Facturas por el contrato de lectura ya estabilizado cuando corresponda.

## Condición de entrada

BANCOS-04 solo puede comenzar cuando:

```text
INTER-APP BASELINE = PASS
SSOT MATRIX       = PASS
RELATIONS         = PASS
STATE MACHINES    = PASS
ATOMICITY         = PASS
TENANT ISOLATION  = PASS
GOVERNANCE        = PASS
REGRESSION        = PASS
```

---

# 16. FASE 12 — Actualización de documentación — ÚLTIMO PASO

> **Esta fase debe ejecutarse únicamente después de que TODO el código, tests, contratos y gates anteriores estén cerrados.**

No utilizar la documentación para declarar “completado” algo que todavía no fue verificado en código.

## Actualizar al final

### Arquitectura general

Actualizar:

```text
documentacion/arquitectura_general.md
```

y solo las secciones realmente afectadas:

- apps y modelos,
- dependencias,
- contratos inter-app,
- SSoT,
- estados,
- gobernanza,
- endpoints,
- métricas.

### ADRs

Actualizar o crear ADR solamente cuando exista una nueva decisión arquitectónica permanente.

No crear un ADR por cada corrección técnica menor.

### Auditorías por app

Actualizar solamente las auditorías de apps realmente afectadas.

### Documentos de release

Actualizar el release gate correspondiente y los documentos de ejecución que hayan quedado obsoletos.

### Índices

Actualizar índices y referencias rotas:

```text
documentacion/
docs/
AGENTS.md
```

solo cuando corresponda.

## Gate final de documentación

La documentación debe reflejar exactamente el código verificado.

Debe quedar explícitamente indicado:

```text
IMPLEMENTED
VERIFIED
DEFERRED
OUT_OF_SCOPE
```

No usar una etiqueta de “COMPLETED” si la evidencia no existe.

---

# 17. Criterio de aceptación global

La misión se considera completada solamente si todos los siguientes son PASS:

```text
[ ] FASE 0  Baseline
[ ] FASE 1  SSoT
[ ] FASE 2  Relaciones / lifecycle
[ ] FASE 3  Contratos lectura
[ ] FASE 4  Contratos escritura
[ ] FASE 5  Estados / workflow
[ ] FASE 6  Atomicidad / idempotencia
[ ] FASE 7  Tenant / scope
[ ] FASE 8  Gobernanza
[ ] FASE 9  Regresión transversal
[ ] FASE 10 Deuda / deferred
[ ] FASE 11 Siguiente misión habilitada
[ ] FASE 12 Documentación final
```

Y además:

```text
manage.py check                      = PASS
makemigrations --check --dry-run     = PASS
governance report                   = PASS
tests focalizados                    = PASS
regresión inter-app                  = PASS
tenant isolation                     = PASS
```

---

# 18. Principio final para la IA editora

La IA editora debe seguir esta regla durante TODA la misión:

> **Primero descubrir la relación real. Después identificar al propietario. Después identificar el contrato. Después modificar. Finalmente probar. Nunca modificar primero y descubrir la arquitectura después.**

La prioridad no es reducir el número de FKs ni aumentar el número de servicios.

La prioridad es que el ERP tenga una única interpretación operacional de cada dato y de cada proceso.

---

# 19. Orden operativo resumido

```text
INTER-APP-01
│
├── F0  Baseline
├── F1  SSoT
├── F2  Relaciones + Lifecycle
├── F3  Contratos de Lectura
├── F4  Contratos de Escritura
├── F5  Estados + Workflows
├── F6  Atomicidad + Idempotencia
├── F7  Tenant + Empresa/Sede/Área
├── F8  Governance
├── F9  Regresión transversal
├── F10 Deuda + Deferred
├── F11 Habilitación de siguiente funcionalidad
└── F12 DOCUMENTACIÓN FINAL
```

**Regla:** si una fase falla su gate, corregir dentro del mismo loop y repetir la fase antes de avanzar.

**No saltar fases. No agrupar fases críticas para ahorrar tiempo. No inventar modelos o contratos mientras la evidencia del código permita reutilizar los existentes.**
