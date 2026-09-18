# PLAN MAESTRO — Bancos: Extractos PDF + Causación/Aplicación de un Pago a Múltiples Facturas

## Misión

Evolucionar `apps/tenant/bancos/` sin romper el flujo actual para soportar simultáneamente:

1. Importación y procesamiento de extractos bancarios en **PDF**, además de los formatos ya soportados.
2. Un único movimiento bancario pueda aplicarse a **múltiples facturas de venta**.
3. Un mismo pago pueda cubrir una factura, varias facturas, pagos parciales, combinaciones de facturas + anticipos o un anticipo sin factura.
4. Mantener la conciliación existente y la compatibilidad con registros históricos.
5. Mantener DSV, UUID, multitenancy, Service Layer, atomicidad e idempotencia.
6. No duplicar la lógica fiscal/contable de `facturas`, `clientes` o `contabilidad`.

---

# 0. REGLA PRINCIPAL DE NEGOCIO

Un movimiento bancario representa el **dinero recibido o debitado**.

Las aplicaciones representan cómo ese dinero se distribuye:

```text
MOVIMIENTO BANCARIO
       │
       ├── Aplicación 1 → Factura venta A → $300.000
       ├── Aplicación 2 → Factura venta B → $450.000
       └── Aplicación 3 → Anticipo         → $250.000
                                      ─────────────
                                      $1.000.000
```

La suma de las aplicaciones no puede superar el monto disponible del movimiento.

Debe existir conceptualmente:

```text
monto_movimiento
monto_aplicado
monto_pendiente
```

con:

```text
monto_pendiente = monto_movimiento - SUM(aplicaciones válidas)
```

Tolerancia monetaria:

```text
Decimal("0.01")
```

---

# 1. SSoT DEL DOMINIO

## Bancos

Es dueño de:

- Cuenta bancaria.
- Extracto.
- Movimiento bancario.
- Aplicaciones del movimiento.
- Estado de conciliación bancaria.

## Facturas

Es dueño de:

- Identidad fiscal.
- Número.
- CUFE.
- XML.
- Totales fiscales.
- Estado fiscal.

## Clientes

Es dueño del tercero.

## Contabilidad

Es dueño de la interpretación contable y asientos.

## Regla

La aplicación bancaria puede referenciar:

```text
Factura
Cliente
Proveedor
DocumentoSoporte
Anticipo
```

pero no debe duplicar su información fiscal/contable.

---

# 2. BASELINE OBLIGATORIO

Antes de tocar código:

```text
INSPECT
```

Auditar el código real de:

```text
apps/tenant/bancos/
apps/tenant/facturas/
apps/tenant/clientes/
apps/tenant/contabilidad/
```

y especialmente:

```text
models.py
services/
api/
templates/
static/
tests/
migrations/
```

La documentación actual de Bancos ya registra `ExtractoBancario`, `TransaccionBancaria`, `MovimientoBancarioAplicacion` y endpoints de aplicaciones 1:N, por lo que **no se debe crear un segundo sistema paralelo**.

La auditoría actual también documenta una relación legacy 1:1 mediante `factura_uuid`. Debe conservarse durante la transición hasta demostrar que puede retirarse de forma segura.

---

# 3. ESTADO PERSISTENTE DE LA MISIÓN

Crear:

```text
docs/remediation/BANCOS_PDF_APLICACIONES_MULTIPLES_STATUS.md
```

Formato mínimo:

```md
# BANCOS PDF + APLICACIONES MÚLTIPLES — STATUS

Mission: BANCOS_PDF_APLICACIONES_01

Current Phase: PHASE-00
Overall Status: RUNNING

| Phase | Status | Evidence | Notes |
|---|---|---|---|
| PHASE-00 | RUNNING | | |
| PHASE-01 | PENDING | | |
...

## Decisions
...

## Blockers
...

## Files Changed
...

## Migrations
...

## Tests
...

## Last Verification
...
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

Actualizar este archivo **después de cada fase**.

---

# 4. LOOP OBLIGATORIO

Cada fase:

```text
READ
↓
INSPECT
↓
COMPARE
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
NEXT
```

Una fase con fallo no puede pasar a la siguiente.

---

# 5. FASE 01 — AUDITORÍA DEL MODELO ACTUAL DE BANCOS

Confirmar en código real:

```text
CuentaBancaria
ExtractoBancario
TransaccionBancaria
MovimientoBancarioAplicacion
```

Confirmar exactamente todos los campos de `MovimientoBancarioAplicacion`, en especial:

```text
uuid
empresa
transaccion
tipo_referencia
referencia_uuid
monto / monto_aplicado / valor
otas
created_at
updated_at
```

Si existe ya un campo de monto, **reutilizarlo**.

Si no existe, determinar el nombre canónico y agregarlo.

No crear dos campos con la misma semántica.

---

# 6. FASE 02 — AUDITORÍA DEL FLUJO ACTUAL DE CONCILIACIÓN

Auditar:

```text
PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
```

Determinar:

```text
qué frontend lo consume;
qué tests lo cubren;
qué integraciones dependen de él;
qué comportamiento histórico debe preservarse.
```

No eliminarlo inicialmente.

---

# 7. FASE 03 — NUEVO SSoT DE APLICACIONES

Para operaciones nuevas:

```text
MovimientoBancarioAplicacion
```

debe ser el SSoT de la distribución del pago.

Modelo lógico:

```text
TransaccionBancaria
        │
        ├── Aplicación Factura A
        ├── Aplicación Factura B
        ├── Aplicación Factura C
        └── Aplicación Anticipo
```

No crear modelos paralelos como `PagoFactura`, `PagoVenta` o similares si el modelo existente puede representar el concepto.

---

# 8. FASE 04 — TIPO DE APLICACIÓN

Auditar `tipo_referencia` existente.

Debe soportar claramente al menos:

```text
FACTURA_VENTA
ANTICIPO_CLIENTE
```

Reutilizar choices existentes.

Si `ANTICIPO_CLIENTE` no existe, agregarlo únicamente después de comprobar que no existe un concepto equivalente.

Para un anticipo sin factura:

```text
referencia_uuid = NULL
```

es válido únicamente si el modelo y contrato real lo soportan.

---

# 9. FASE 05 — MONTO DE CADA APLICACIÓN

Cada aplicación debe registrar un monto explícito.

Ejemplo:

```text
Transacción = $1.000.000

Factura A = $300.000
Factura B = $400.000
Anticipo   = $300.000

Aplicado = $1.000.000
Pendiente = $0
```

Un UUID solo no permite representar la distribución monetaria.

---

# 10. FASE 06 — REGLA DE SOBREAPLICACIÓN

Toda creación o edición debe ejecutar:

```text
monto_aplicado_existente + nuevo_monto <= monto_movimiento
```

con bloqueo transaccional adecuado, preferiblemente:

```text
select_for_update()
```

sobre la transacción bancaria.

Ejemplo:

```text
Movimiento = $500.000
Aplicado = $450.000
Nueva aplicación = $60.000

→ RECHAZAR
```

Mensaje claro con monto disponible y solicitado.

---

# 11. FASE 07 — PAGO PARCIAL DE FACTURA

Debe permitirse:

```text
Factura = $1.000.000
Pago aplicado = $300.000
Saldo factura = $700.000
```

No marcar automáticamente la factura como pagada si existe saldo.

Reutilizar el contrato real de Facturas/Cartera para determinar `PENDIENTE`, `PARCIAL`, `PAGADA`, etc.

---

# 12. FASE 08 — UNA TRANSACCIÓN → MUCHAS FACTURAS

Caso obligatorio:

```text
Pago bancario = $2.000.000

Factura A = $500.000
Factura B = $700.000
Factura C = $400.000
Anticipo   = $400.000
```

Resultado:

```text
Aplicación A = $500.000
Aplicación B = $700.000
Aplicación C = $400.000
Aplicación anticipo = $400.000
```

Total aplicado:

```text
$2.000.000
```

---

# 13. FASE 09 — ANTICIPO SIN FACTURA

Permitir un pago recibido sin factura asociada:

```text
ANTICIPO_CLIENTE
```

Ejemplo:

```text
Movimiento = $1.500.000
Factura A = $1.000.000
Anticipo = $500.000
```

No crear factura ficticia.

No crear factura DIAN.

No inventar número fiscal.

---

# 14. FASE 10 — ANTICIPO PARA FUTURA IMPUTACIÓN

Auditar si ya existe un modelo formal de anticipos en Clientes/Facturas.

Si existe:

```text
reutilizarlo.
```

Si no existe:

No construir un sistema contable completo dentro de esta misión sin evidencia de que sea necesario.

Dejar el anticipo trazable y separar una eventual imputación futura a factura como operación independiente cuando corresponda.

---

# 15. FASE 11 — FACTURA DE VENTA COMO REFERENCIA

Mantener el filtro real documentado:

```python
Factura.objects.filter(naturaleza='VENTA')
```

No usar:

```python
Factura.objects.filter(tipo='VENTA')
```

porque `tipo` representa el tipo de documento fiscal (`FE`, `NC`, `ND`), no la naturaleza VENTA/COMPRA.

---

# 16. FASE 12 — VALIDACIÓN DE SALDO DE FACTURA

Antes de aplicar:

```text
monto_aplicado <= saldo_disponible_factura
```

Obtener el saldo mediante el contrato existente de cartera/facturas.

No duplicar en Bancos una fórmula de saldo que ya tenga otro SSoT.

---

# 17. FASE 13 — API DE APLICACIONES

Mantener y extender los endpoints existentes de aplicaciones:

```http
GET    /api/v1/bancos/transacciones/{uuid}/aplicaciones/
POST   /api/v1/bancos/transacciones/{uuid}/aplicaciones/
PATCH  /api/v1/bancos/aplicaciones/{uuid}/
DELETE /api/v1/bancos/aplicaciones/{uuid}/
```

No crear endpoints paralelos para el mismo concepto.

---

# 18. FASE 14 — SERIALIZER DE APLICACIÓN

Debe permitir al menos:

```text
tipo_referencia
referencia_uuid
monto_aplicado
notas
```

Debe devolver información útil para UI:

```text
uuid
tipo
factura / anticipo
cliente
monto_aplicado
monto_movimiento
monto_pendiente
```

Resolver nombres humanos mediante selectors/services y respetar DSV.

---

# 19. FASE 15 — IDEMPOTENCIA

Evitar doble aplicación por doble click o reintento.

Comprobar el mecanismo actual de idempotencia del proyecto antes de añadir uno nuevo.

Casos:

```text
guardar una vez → 1 aplicación
guar dar dos veces → 1 aplicación efectiva
```

No generar duplicados.

---

# 20. FASE 16 — EDICIÓN DE APLICACIÓN

Permitir editar según reglas:

```text
monto_aplicado
referencia_uuid
notas
```

Siempre:

```text
bloquear transacción
recalcular suma
validar saldo factura
validar disponible del movimiento
guardar
```

Nunca permitir:

```text
monto negativo
monto cero
sobreaplicación
factura de otro tenant
```

---

# 21. FASE 17 — ELIMINAR APLICACIÓN

Quitar una aplicación no debe eliminar:

```text
TransaccionBancaria
Factura
Cliente
```

Después de eliminar:

```text
recalcular monto_aplicado
recalcular monto_pendiente
recalcular estado de conciliación
```

---

# 22. FASE 18 — ESTADO DE LA TRANSACCIÓN

Mantener el campo actual:

```text
conciliado
```

La regla documentada es:

```text
conciliado = True
```

solo cuando el 100% del movimiento quede aplicado mediante el nuevo modelo, sin romper el comportamiento legacy ya existente.

---

# 23. FASE 19 — COMPATIBILIDAD LEGACY

La implementación actual contiene:

```text
factura_uuid
proveedor_uuid
cliente_uuid
```

No eliminarlos de inmediato.

Estrategia:

```text
LEGACY READ
+
NEW APPLICATIONS WRITE
```

Las nuevas operaciones deben usar `MovimientoBancarioAplicacion`.

Evitar que una operación nueva escriba simultáneamente una aplicación nueva y un vínculo legacy sin un propósito explícito.

---

# 24. FASE 20 — MIGRACIÓN LEGACY

No inferir montos históricos si el registro legacy no permite conocerlos con seguridad.

Si el vínculo histórico contiene suficiente evidencia:

```text
migrar → crear aplicación → registrar monto
```

Si no:

```text
preservar legacy
marcar migración pendiente/manual
```

Nunca introducir valores inventados para cuadrar históricos.

---

# 25. FASE 21 — UI DE CAUSACIONES

Auditar la pantalla real:

```text
Bancos → Causaciones
```

Determinar si es el mismo flujo de:

```text
Extracto → Transacción → Conciliación/Aplicaciones
```

Si es la pantalla operativa, evolucionarla para soportar múltiples aplicaciones utilizando el modelo existente.

No construir un segundo sistema.

---

# 26. FASE 22 — FORMULARIO DE CAUSACIÓN

Cambiar conceptualmente:

```text
Una Factura
```

a:

```text
Aplicaciones
```

UX mínima:

```text
Movimiento
$2.000.000

Aplicado: $1.200.000
Pendiente: $800.000

[ + Agregar factura ]
[ + Agregar anticipo ]
```

---

# 27. FASE 23 — LISTA DE APLICACIONES

Mostrar:

```text
Tipo
Referencia
Cliente
Monto aplicado
Saldo
Acciones
```

Ejemplo:

```text
Factura | FST 359 | Cliente A | $500.000 | Parcial
Factura | FST 360 | Cliente A | $400.000 | Pagada
Anticipo | Cliente A | $100.000
```

---

# 28. FASE 24 — RESUMEN EN TIEMPO REAL

Mostrar:

```text
Monto movimiento       $2.000.000
Total aplicaciones     $1.500.000
Disponible             $500.000
```

El cálculo visual es orientativo.

El backend siempre debe recalcular y validar.

---

# 29. FASE 25 — CONTROL BACKEND

La suma definitiva debe calcularse en servidor:

```text
SUM(aplicaciones válidas)
```

No confiar en el frontend.

---

# 30. FASE 26 — SUGERENCIAS DE FACTURAS

Mantener `BankTransactionMatchingService` como servicio de lectura.

Puede sugerir múltiples facturas:

```text
Movimiento $2.000.000

Factura A $500.000
Factura B $700.000
Factura C $400.000
```

El usuario confirma la selección.

No convertir sugerencias en aplicaciones automáticamente sin acción explícita.

---

# 31. FASE 27 — DISTRIBUCIÓN PROPUESTA

Si el código existente permite una propuesta de distribución, evolucionarla para múltiples documentos.

Ejemplo:

```text
$1.000.000

Factura A $300.000
Factura B $500.000
Factura C $400.000
```

Una propuesta puede sugerir:

```text
A $300.000
B $500.000
C $200.000
```

pero debe requerir confirmación.

---

# 32. FASE 28 — EXTRACTO PDF

Agregar:

```text
PDF
```

al conjunto de formatos aceptados:

```text
XLSX
CSV
PDF
```

Mantener XML según su estado real actual: el adapter está preparado pero el parser real puede seguir diferido si no existe un esquema bancario verificable.

---

# 33. FASE 29 — ARQUITECTURA DE IMPORTADORES

Mantener:

```text
BankStatementImporter
    ├── XLSXBankStatementImporter
    ├── CSVBankStatementImporter
    ├── XMLBankStatementImporter
    └── PDFBankStatementImporter
```

`PDFBankStatementImporter` debe producir exactamente:

```text
NormalizedBankStatement
NormalizedBankTransaction
```

para reutilizar el mismo ETL posterior.

---

# 34. FASE 30 — VALIDACIÓN DE ARCHIVO PDF

Antes de parsear:

```text
extensión
MIME
tamaño máximo
archivo legible
archivo no corrupto
archivo no protegido/encriptado
```

Usar la política de carga de archivos que ya tenga el proyecto.

No confiar únicamente en la extensión `.pdf`.

---

# 35. FASE 31 — BIBLIOTECA PDF

Auditar `requirements.txt`/entorno para verificar si ya existe una librería compatible.

Si existe:

```text
reutilizar.
```

Si no existe:

seleccionar una sola dependencia apropiada y documentar:

```text
motivo
compatibilidad
licencia
impacto
riesgos
```

No añadir varias bibliotecas para el mismo propósito.

---

# 36. FASE 32 — PARSER PDF

Intentar detectar:

```text
fecha
descripción/referencia
crédito
débito
saldo
```

mediante patrones robustos.

No asumir posiciones rígidas si el layout bancario no las garantiza.

---

# 37. FASE 33 — MONEDA

Reutilizar `parse_money()` como único punto de normalización.

No crear un segundo parser.

Soportar los formatos monetarios que ya maneja el proyecto.

---

# 38. FASE 34 — PDF CON TEXTO VS ESCANEADO

Detectar si el PDF tiene texto extraíble.

### Texto extraíble

```text
procesar normalmente
```

### PDF escaneado

Si existe OCR en el proyecto:

```text
reutilizar.
```

Si no existe:

```text
NEEDS_OCR / UNSUPPORTED_FORMAT
```

con mensaje controlado.

No introducir un sistema OCR pesado dentro de esta misión sin auditar primero su impacto.

---

# 39. FASE 35 — BALANCE DEL PDF

Después de importar:

```text
saldo_inicial + creditos - debitos == saldo_final
```

con tolerancia:

```text
Decimal("0.01")
```

Si falla:

```text
422
procesado = False
```

Nunca marcar procesado con balance inválido.

---

# 40. FASE 36 — PDF MULTIPÁGINA Y ENCABEZADOS

Soportar, cuando el layout lo permita:

```text
varias páginas
encabezados repetidos
bloques resumen
filas partidas
```

No duplicar filas por encabezados repetidos.

---

# 41. FASE 37 — IDEMPOTENCIA DEL EXTRACTO PDF

Caso:

```text
subir PDF A
procesar
subir PDF A nuevamente
```

No duplicar transacciones.

Reutilizar la estrategia de idempotencia existente, no crear una segunda implementación solo para PDF.

---

# 42. FASE 38 — UI SUBIDA PDF

Modificar:

```text
offcanvas_crear_extracto.html
```

para aceptar:

```text
.xlsx
.csv
.pdf
```

Mostrar los formatos permitidos y el tamaño máximo real configurado.

---

# 43. FASE 39 — ERRORES CONTROLADOS PDF

Casos esperados:

```text
PDF corrupto
PDF vacío
PDF escaneado sin OCR
layout no reconocido
balance inválido
formato desconocido
banco no soportado
```

Todos deben producir:

```text
error controlado
mensaje útil
```

Nunca un 500 por un input esperado.

---

# 44. FASE 40 — TESTS PDF

Crear fixtures reales o representativos de:

```text
PDF válido
PDF multipágina
PDF con saldo
PDF con formato colombiano
PDF corrupto
PDF vacío
PDF escaneado
PDF con encabezados repetidos
```

No declarar soporte universal de bancos solo porque un PDF funcione.

---

# 45. FASE 41 — TESTS DE APLICACIONES MÚLTIPLES

Crear pruebas para:

```text
1 transacción → 1 factura
1 transacción → 2 facturas
1 transacción → 5 facturas
1 transacción → varias facturas parciales
1 transacción → factura + anticipo
1 transacción → solo anticipo
```

---

# 46. FASE 42 — TEST DE SOBREAPLICACIÓN

```text
Movimiento = 1.000.000
Aplicación 1 = 700.000
Aplicación 2 = 300.000
→ PASS
```

```text
Movimiento = 1.000.000
Aplicación 1 = 700.000
Aplicación 2 = 301.000
→ FAIL controlado
```

---

# 47. FASE 43 — TEST DE FACTURA PARCIAL

```text
Factura = 1.000.000
Aplicación = 400.000
```

Verificar que la semántica de cartera permanezca correcta.

No modificar el dominio fiscal desde Bancos.

---

# 48. FASE 44 — TEST DE ANTICIPO

```text
Movimiento = 1.000.000
Anticipo = 1.000.000
```

Resultado:

```text
Aplicado = 1.000.000
Pendiente = 0
```

sin factura ficticia.

---

# 49. FASE 45 — TEST MULTITENANT

Crear:

```text
Tenant A
Tenant B
```

Verificar:

```text
Transacción A + Factura A = PASS
Transacción A + Factura B = REJECT
```

La factura de otro tenant nunca debe aparecer en sugerencias.

---

# 50. FASE 46 — TEST DE CONCURRENCIA

Ejecutar dos solicitudes simultáneas:

```text
Usuario 1 → aplicación $600.000
Usuario 2 → aplicación $500.000
```

sobre:

```text
Movimiento $1.000.000
```

La implementación debe garantizar:

```text
SUM(aplicaciones) <= $1.000.000
```

---

# 51. FASE 47 — TEST DE ATOMICIDAD

Simular:

```text
crear aplicación
+
fallo posterior
```

Resultado:

```text
ROLLBACK
```

Nunca dejar aplicación parcial ni estado inconsistente.

---

# 52. FASE 48 — REGRESIÓN LEGACY

Ejecutar pruebas existentes de:

```text
conciliar_transaccion()
factura_uuid
cliente_uuid
proveedor_uuid
conciliado
notas_conciliacion
```

Los casos históricos deben permanecer funcionales.

---

# 53. FASE 49 — REGRESIÓN COMPLETA DE BANCOS

Ejecutar el comando canónico real del proyecto, por ejemplo:

```bash
pytest apps/tenant/bancos/tests/
```

La documentación actual registra una línea base de:

```text
58 passed
0 failed
```

No asumir que continúa así; volver a ejecutar.

---

# 54. FASE 50 — REGRESIÓN CROSS-APP

Ejecutar pruebas relacionadas con:

```text
facturas
clientes
contabilidad
gastos
ventas
```

Especialmente:

```text
Factura → cartera
Bancos → Factura
Bancos → Cliente
Bancos → Contabilidad
```

---

# 55. FASE 51 — MANAGE.PY CHECK

Ejecutar:

```bash
python manage.py check
```

Resultado esperado:

```text
0 issues
```

---

# 56. FASE 52 — MIGRACIONES

Ejecutar:

```bash
python manage.py makemigrations --check
```

y aplicar las migraciones reales del proyecto.

Verificar todos los schemas tenant.

No introducir cambios destructivos sin estrategia de datos.

---

# 57. FASE 53 — FRONTEND

Auditar:

```text
bancos.api.js
bancos.main.js
extracto_list.js
extracto_editor.js
```

Comprobar:

```text
window.Sintel.Bancos.API
UIManager.handleOffcanvas()
htmx:afterSettle
sin listeners duplicados
sin URLs duplicadas
sin parseInt(UUID)
sin errores de consola
```

---

# 58. FASE 54 — N+1 / PERFORMANCE

Verificar:

```text
lista extractos
detalle extracto
lista transacciones
lista aplicaciones
búsqueda de facturas
```

Evitar consultas por fila.

Usar `select_related`, `prefetch_related`, `only` y `aggregate` donde corresponda.

---

# 59. FASE 55 — AUDITORÍA FINANCIERA

Comprobar siempre:

```text
monto movimiento - SUM(aplicaciones) = monto pendiente
```

No aceptar:

```text
pendiente < 0
aplicaciones > movimiento
```

---

# 60. FASE 56 — AUDITORÍA DE DUPLICADOS

Buscar:

```text
misma aplicación duplicada
misma factura aplicada dos veces al mismo movimiento
mismo anticipo duplicado
doble conteo legacy + nuevo
```

Agregar constraints/guards solo cuando el dominio los soporte.

---

# 61. FASE 57 — DOCUMENTACIÓN

Crear/actualizar:

```text
docs/remediation/BANCOS_PDF_APLICACIONES_MULTIPLES.md
```

Documentar:

```text
arquitectura PDF
contrato NormalizedBankStatement
modelo de aplicaciones
regla 1:N
anticipos
pagos parciales
saldo
idempotencia
legacy
API
UX
tests
decisiones
```

---

# 62. FASE 58 — MATRIZ DE ESTADOS

Determinar, sin duplicar enums innecesarios, cómo representar:

```text
PENDIENTE
PARCIALMENTE_APLICADO
COMPLETAMENTE_APLICADO
```

Si `conciliado + sumas` ya permite representarlo, reutilizarlo.

---

# 63. FASE 59 — RELEASE GATE

No cerrar la misión hasta:

```text
[ ] PDF puede cargarse
[ ] PDF puede procesarse
[ ] PDF devuelve errores controlados
[ ] balance PDF validado
[ ] no se duplican transacciones
[ ] una transacción puede aplicar varias facturas
[ ] se permiten pagos parciales
[ ] se permite factura + anticipo
[ ] se permite anticipo sin factura
[ ] monto aplicado se controla backend
[ ] sobreaplicación bloqueada
[ ] concurrencia controlada
[ ] idempotencia implementada
[ ] legacy preservado
[ ] no doble conteo legacy/nuevo
[ ] Factura de otro tenant bloqueada
[ ] Cliente de otro tenant bloqueado
[ ] UI de Causaciones soporta múltiples aplicaciones
[ ] sugerencias de facturas funcionan
[ ] resumen aplicado/pendiente funciona
[ ] Service Layer respetado
[ ] no Django Signals
[ ] UUID respetado
[ ] DSV respetado
[ ] tests bancos PASS
[ ] regresión cross-app PASS
[ ] manage.py check PASS
[ ] migraciones PASS
[ ] frontend PASS
[ ] documentación actualizada
[ ] STATUS actualizado
```

---

# 64. REGLAS DE NO REGRESIÓN

Está prohibido:

- eliminar `MovimientoBancarioAplicacion`;
- volver al modelo obligatorio 1:1;
- eliminar `factura_uuid` sin plan de compatibilidad;
- duplicar `Factura`;
- modificar XML fiscal;
- modificar CUFE;
- crear estados fiscales dentro de Bancos;
- crear anticipos ficticios como Facturas;
- permitir sobreaplicación;
- permitir cross-tenant;
- mover lógica de negocio al JS;
- implementar la lógica con Signals;
- recalcular cartera manualmente en Bancos si ya existe SSoT;
- aceptar PDFs sin validación;
- devolver 500 por un PDF no soportado;
- asumir que un PDF válido para un banco equivale a soporte universal;
- declarar `PRODUCTION READY` sin pruebas reales.

---

# 65. LOOP FINAL DE REPARACIÓN

Si aparece cualquier fallo:

```text
IDENTIFY ROOT CAUSE
↓
CLASSIFY
  BUG
  REGRESSION
  INFRA
  DATA
  UX
  DOCUMENTATION
↓
FIX ONLY ROOT CAUSE
↓
TARGETED TEST
↓
MODULE TEST
↓
CROSS-APP REGRESSION
↓
UPDATE STATUS
```

No avanzar dejando failures sin clasificar.

---

# 66. REPORTE FINAL OBLIGATORIO

La IA editora debe entregar:

```md
# FINAL REPORT

Mission: BANCOS_PDF_APLICACIONES_01

Status:
PASS | PASS_WITH_DEFERRED | BLOCKED | FAIL

## Implemented
...

## Models
...

## Migrations
...

## Services
...

## APIs
...

## PDF
...

## Multiple Applications
...

## Partial Payments
...

## Advances
...

## Legacy Compatibility
...

## Tests
...

## Cross-App Regression
...

## Security
...

## Performance
...

## Deferred
...

## Blockers
...

## Evidence
...

## Files Changed
...
```

No inventar resultados.

---

# 67. RESULTADO FUNCIONAL ESPERADO

## Escenario A — una factura

```text
Pago bancario $961.520
        ↓
Factura FST 359
        ↓
Aplicación $961.520
        ↓
Pendiente movimiento = $0
```

## Escenario B — múltiples facturas

```text
Pago $2.000.000

Factura 359 → $961.520
Factura 360 → $738.480
Anticipo     → $300.000

TOTAL = $2.000.000
```

## Escenario C — pagos parciales

```text
Pago $500.000

Factura A
Valor = $800.000
Aplicado = $500.000
Saldo = $300.000
```

## Escenario D — factura + anticipo

```text
Pago $1.500.000

Factura A → $1.000.000
Anticipo   → $500.000
```

## Escenario E — pago solo como anticipo

```text
Pago $2.000.000

Anticipo → $2.000.000
```

---

# 68. PRINCIPIO FINAL

El diseño final debe ser:

```text
1 MOVIMIENTO BANCARIO
        ↓
       1:N
        ↓
APLICACIONES DEL PAGO
        ↓
 ┌───────────────┬───────────────┐
 ↓               ↓               ↓
Factura A      Factura B      Anticipo
 ↓               ↓               ↓
$X              $Y              $Z
```

con la regla inmutable:

```text
SUM(X + Y + Z) <= monto_movimiento
```

La aplicación bancaria debe representar **cómo se distribuye un dinero real**, no crear nuevos documentos fiscales.

# FIN DEL PLAN
