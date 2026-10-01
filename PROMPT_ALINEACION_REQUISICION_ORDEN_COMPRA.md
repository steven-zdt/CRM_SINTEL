# PROMPT — ALINEACIÓN OBLIGATORIA REQUISICIÓN → ORDEN DE COMPRA

## OBJETIVO

Implementa y corrige el flujo de **Compras** para que exista una relación obligatoria, trazable y consistente entre:

**Cotización ACEPTADA → Requisición → una o varias Órdenes de Compra**

La **Orden de Compra nunca puede existir sin una Requisición válida** y nunca puede comprometer un valor superior al saldo disponible de su Requisición.

La relación correcta es:

- Una Cotización ACEPTADA puede originar una única Requisición.
- Una Requisición puede originar múltiples Órdenes de Compra.
- Cada Orden de Compra pertenece obligatoriamente a una Requisición.
- El valor acumulado de las Órdenes de Compra activas vinculadas a una Requisición **nunca puede superar el valor total de la Requisición**.
- Una Orden de Compra puede ser parcial respecto de la Requisición.
- Cuando una Requisición ya no tenga saldo disponible, no se debe permitir crear otra Orden de Compra sobre ella.

> IMPORTANTE: en el código actual la condición de cotización aceptada es `Cotizacion.Estado.ACEPTADA`. No renombrar este estado a `APROBADA` salvo que una inspección real del repositorio demuestre que el código ya fue cambiado.

---

# 1. SSoT Y REGLAS EXISTENTES

Antes de modificar código:

1. Inspecciona el repositorio real.
2. Usa como fuente de verdad la implementación actual y la documentación existente.
3. No inventes nuevos flujos que dupliquen lógica ya existente.
4. Mantén el Service Layer como SSoT de reglas de negocio.
5. No implementar lógica de negocio mediante Django Signals.
6. Mantener `OrganizationalContext`, `OrganizationalScope`, DSV y aislamiento por tenant.
7. Preservar el flujo existente:
   - Cotización ACEPTADA
   - Conversión a Venta
   - Facturación
8. No romper las integraciones actuales de Compras, Gastos, CxP, Recepciones e Inventario.

La arquitectura actual documenta que `OrdenCompra` utiliza `SedeAwareModel`, Selectors y Business Services, y que la creación/actualización debe mantenerse alineada con ese patrón. También existe integración de CxP cuando la OC pasa a `APROBADA`. No reemplaces ese comportamiento; intégrale la validación de Requisición.

---

# 2. REGLA CENTRAL: TODA OC DEBE TENER REQUISICIÓN

## Regla obligatoria

Una nueva Orden de Compra:

- DEBE seleccionar una Requisición.
- NO puede crearse manualmente sin Requisición.
- NO puede guardarse con `requisicion = null`.
- NO puede recibir una Requisición inválida.
- NO puede apuntar a una Requisición de otro tenant.
- NO puede utilizar una Requisición inexistente.
- NO puede vincularse a una Requisición que no tenga estado que permita generar/consumir Órdenes de Compra, según la máquina de estados real del repositorio.
- No debe permitirse saltarse esta relación mediante API, frontend, importación o llamadas directas al service.

La relación debe existir como referencia persistente en la Orden de Compra.

Preferentemente:

```text
OrdenCompra.requisicion -> Requisicion
```

La FK debe ser obligatoria (`null=False`) para nuevas Órdenes de Compra, salvo que la auditoría del repositorio demuestre una necesidad real de compatibilidad histórica. No crear excepciones nuevas para órdenes futuras.

---

# 3. NUEVA OC: BOTÓN "BUSCAR REQUISICIÓN"

Modificar la pantalla de creación de Orden de Compra.

## UX requerida

En **Nueva Orden de Compra** debe existir un control explícito:

**[ Buscar Requisición ]**

Ese botón debe abrir un selector/buscador de Requisiciones.

No mostrar un campo libre donde el usuario tenga que escribir arbitrariamente un UUID, ID o número.

El selector debe soportar:

- búsqueda por número/código de Requisición;
- búsqueda por Cotización;
- búsqueda por proveedor cuando aplique;
- búsqueda por proyecto cuando exista;
- estado;
- disponibilidad/saldo;
- paginación server-side;
- ordenamiento;
- filtrado por tenant actual.

Mostrar como mínimo:

```text
Requisición
Origen / Cotización
Proyecto
Valor total
Valor comprometido
Saldo disponible
Estado
Acción: Seleccionar
```

---

# 4. SOLO MOSTRAR REQUISICIONES APTAS PARA COMPRA

El endpoint/selector de búsqueda debe devolver únicamente Requisiciones:

1. Del tenant actual.
2. Que puedan generar una Orden de Compra según la lógica de negocio.
3. Con saldo disponible > 0.
4. Que no estén anuladas/canceladas/cerradas de forma incompatible, respetando los estados reales del modelo.
5. Que tengan su Cotización obligatoria válida.
6. Que no estén bloqueadas por una regla existente del dominio.

No confiar únicamente en los filtros del frontend.

El backend debe volver a validar todo al seleccionar/crear.

---

# 5. VALOR DE LA REQUISICIÓN VS ÓRDENES DE COMPRA

Implementar explícitamente tres conceptos:

```text
valor_total_requisicion
valor_comprometido
saldo_disponible
```

Regla:

```text
valor_comprometido = SUM(valor_de_OC_validas_vinculadas)
saldo_disponible = valor_total_requisicion - valor_comprometido
```

Y siempre:

```text
valor_comprometido <= valor_total_requisicion
```

Por lo tanto:

```text
valor_nueva_OC <= saldo_disponible
```

Nunca permitir:

```text
valor_nueva_OC > saldo_disponible
```

ni:

```text
SUM(OC vinculadas) > valor_total_requisicion
```

---

# 6. MULTIPLES ÓRDENES DE COMPRA POR UNA REQUISICIÓN

Mantener explícitamente la relación:

```text
1 Requisición
   ├── OC 1
   ├── OC 2
   ├── OC 3
   └── OC N
```

Ejemplo:

```text
REQ-00008
Valor total: $10.000.000

OC-00031 = $4.000.000
OC-00032 = $3.500.000
OC-00033 = $2.500.000

Comprometido = $10.000.000
Saldo = $0
```

En ese momento:

```text
NO permitir otra OC
```

Otro ejemplo:

```text
REQ-00008 = $10.000.000

OC-00031 = $4.000.000
OC-00032 = $2.000.000

Comprometido = $6.000.000
Saldo = $4.000.000
```

Una nueva OC puede ser de hasta:

```text
$4.000.000
```

Pero nunca:

```text
$4.000.001
```

---

# 7. NO DUPLICAR "VALOR COMPROMETIDO" SIN NECESIDAD

Antes de crear un campo como:

```text
Requisicion.valor_comprometido
```

verifica si la arquitectura actual prefiere calcularlo mediante consultas agregadas.

La fuente de verdad debe ser clara.

Si el valor se persiste para rendimiento:

- definir quién lo actualiza;
- mantener una única vía de actualización;
- verificar consistencia;
- evitar que se convierta en un segundo SSoT divergente.

Preferencia:

```text
Ordenes de Compra válidas
        ↓
SUM()
        ↓
valor comprometido
        ↓
saldo disponible
```

Centralizar ese cálculo en un Selector/Service reutilizable.

Ejemplo conceptual:

```python
RequisicionSelector.obtener_resumen_financiero(requisicion)
```

o equivalente según la estructura existente.

No crear una segunda implementación del mismo cálculo en:

- serializer;
- view;
- JS;
- template;
- model;
- service.

El frontend solo muestra; el backend decide.

---

# 8. LÍNEAS DE LA ORDEN Y ALINEACIÓN CON LA REQUISICIÓN

No limitar la validación solamente al total de cabecera si la Requisición tiene detalle.

Inspecciona si existe un modelo tipo:

```text
RequisicionItem
```

y si la Orden de Compra tiene:

```text
ItemOrdenCompra
```

Si existen ambos:

- validar correspondencia de líneas;
- evitar comprar conceptos inexistentes en la Requisición;
- controlar cantidades máximas cuando la Requisición las defina;
- controlar valor máximo por línea cuando sea posible sin inventar reglas no soportadas;
- permitir compras parciales por cantidad/valor;
- calcular correctamente el total de la OC.

NO inventar mapeos contra Inventario si la arquitectura actual no tiene una referencia confiable.

La documentación actual indica que no debe inventarse una vinculación heurística de `CotizacionItem` con el catálogo de Inventario. Mantener esa restricción.

---

# 9. RESTRICCIÓN DE VALOR: NIVEL CABECERA + CONCURRENCIA

La validación debe ejecutarse en el Service Layer.

Usar:

```python
transaction.atomic()
select_for_update()
```

La secuencia conceptual debe ser:

```text
BEGIN
  bloquear Requisición
  recalcular compromiso actual
  calcular saldo disponible
  validar total nueva OC
  crear OC
COMMIT
```

Esto es obligatorio para evitar carreras como:

```text
Saldo = $5.000.000

Usuario A crea OC por $5.000.000
Usuario B simultáneamente crea OC por $5.000.000

Resultado incorrecto:
$10.000.000 comprometidos
```

El diseño debe impedirlo.

La protección debe vivir en el backend, no depender de JavaScript.

---

# 10. SERVICIO SSoT PARA CREAR LA ORDEN

Centralizar la creación de OC vinculada a Requisición.

Crear o adaptar un método equivalente a:

```python
OrdenCompraBusinessService.crear_desde_requisicion(...)
```

Este método debe:

1. validar tenant/OrganizationalScope;
2. validar Requisición;
3. verificar que está habilitada para compra;
4. bloquearla con `select_for_update()`;
5. recalcular el valor comprometido;
6. calcular saldo;
7. validar total de la nueva OC;
8. validar líneas;
9. crear la Orden de Compra;
10. asociar la Requisición;
11. recalcular/refrescar el estado financiero de la Requisición;
12. devolver la OC creada.

No permitir que ViewSet o Serializer reproduzcan la misma lógica.

---

# 11. CREACIÓN DIRECTA DE ORDEN DE COMPRA

Auditar todos los caminos de creación:

- API POST;
- ViewSet;
- serializers;
- formularios;
- HTMX;
- acciones administrativas;
- imports;
- comandos;
- scripts;
- servicios internos;
- MCP;
- cualquier endpoint usado por frontend.

Todos deben converger al Service Layer.

Resultado deseado:

```text
Cualquier entrada
      ↓
OrdenCompraBusinessService
      ↓
validación Requisición
      ↓
validación saldo
      ↓
creación segura
```

Debe ser imposible crear una OC saltándose la validación simplemente llamando otro endpoint.

---

# 12. EDICIÓN DE UNA ORDEN DE COMPRA EXISTENTE

La regla de valor también aplica al editar.

Al actualizar una OC:

```text
nuevo_total_OC
```

debe compararse contra:

```text
saldo_disponible + valor_actual_de_la_OC
```

Ejemplo:

```text
Requisición = $10.000.000
Otras OC     = $6.000.000
OC actual    = $2.000.000

Saldo real excluyendo la OC actual = $4.000.000
Máximo nuevo total de esta OC = $6.000.000
```

Por lo tanto:

```text
OC actual -> $6.000.000     válido
OC actual -> $6.000.001     inválido
```

La edición tampoco debe permitir superar el límite acumulado.

No crear una lógica separada para update; reutilizar el mismo componente de dominio.

---

# 13. CANCELACIÓN / ANULACIÓN DE OC

Auditar la máquina de estados real de `OrdenCompra`.

Cuando una OC pase a un estado que implique que deja de comprometer presupuesto de la Requisición, debe liberar automáticamente su valor dentro del cálculo de saldo.

Ejemplo conceptual:

```text
REQ = $10M

OC1 = $4M
OC2 = $3M

Comprometido = $7M
Saldo = $3M
```

Si OC2 queda `ANULADA` según la semántica real del proyecto:

```text
Comprometido = $4M
Saldo = $6M
```

No inventes estados nuevos.

Determina con el código actual qué estados siguen siendo financieramente comprometidos y documenta esa decisión.

---

# 14. ESTADO FINANCIERO DE LA REQUISICIÓN

Si el dominio ya posee estado para Requisición, adaptar su lógica.

Conceptualmente:

```text
PENDIENTE
PARCIALMENTE_COMPRADA
COMPRADA
ANULADA / CERRADA
```

Pero NO agregar estados únicamente por estética.

Inspeccionar primero los estados existentes.

La lógica debe permitir distinguir:

```text
sin OC
OC parcial
saldo agotado
```

Como mínimo, el sistema debe poder conocer de forma determinística:

```text
valor total
valor comprometido
saldo disponible
```

---

# 15. FRONTEND DE NUEVA ORDEN DE COMPRA

En `panel/compras` reutilizar la arquitectura de tabs/offcanvas/componentes existente.

No crear una pantalla paralela.

Al abrir:

**Nueva Orden de Compra**

mostrar primero:

```text
Requisición *
[ Buscar Requisición ]
```

Una vez seleccionada:

```text
Requisición: REQ-00008
Cotización: COT-00015
Valor Requisición: $10.000.000
Comprometido: $6.000.000
Saldo disponible: $4.000.000
```

Luego permitir capturar la OC.

Mostrar permanentemente:

```text
Total OC: $____________
Saldo permitido: $4.000.000
```

Si el usuario excede:

```text
El valor de la Orden de Compra supera el saldo disponible de la Requisición.
```

Pero incluso si el frontend falla, el backend debe rechazarlo.

---

# 16. BOTÓN "BUSCAR REQUISICIÓN" EN LISTADO/CREACIÓN

Agregar la acción solicitada:

```text
Nueva Orden de Compra
        ↓
[ Buscar Requisición ]
```

El buscador debe utilizar endpoint/selector server-side.

No cargar todas las Requisiciones al navegador.

El resultado debe mostrar solamente las que tienen saldo y son utilizables.

Al seleccionar una:

```text
POST /.../ordenes-compra/
{
    "requisicion": "<uuid>",
    ...
}
```

El backend vuelve a resolver y validar la Requisición.

Nunca aceptar como autoridad:

```text
valor_requisicion
saldo_disponible
valor_comprometido
```

enviados por el cliente.

Esos datos deben calcularse en servidor.

---

# 17. API Y SERIALIZERS

Modificar serializers para que:

```text
requisicion = required
```

en creación.

Utilizar el mecanismo DSV/`UUIDOrPKRelatedField` ya existente donde corresponda.

No permitir:

```json
{
  "requisicion": null
}
```

No permitir que un cliente envíe:

```json
{
  "saldo_disponible": 5000000
}
```

para modificar el criterio de negocio.

El serializer valida formato/entrada.

El Service Layer valida la regla de negocio.

---

# 18. ERRORES DE NEGOCIO

Crear errores consistentes y reutilizables.

Como mínimo:

```text
REQUISICION_REQUIRED
REQUISICION_NOT_FOUND
REQUISICION_NOT_PURCHASABLE
REQUISICION_NO_AVAILABLE_BALANCE
ORDEN_COMPRA_EXCEEDS_REQUISICION
ORDEN_COMPRA_LINE_NOT_ALLOWED
TENANT_SCOPE_VIOLATION
```

Usar las convenciones de errores existentes del proyecto en lugar de crear un formato paralelo.

---

# 19. MIGRACIONES Y DATOS HISTÓRICOS

Antes de convertir una FK existente en obligatoria:

1. inspeccionar las Órdenes de Compra existentes;
2. obtener conteo de OC sin Requisición;
3. identificar fechas/estados;
4. identificar si existe evidencia confiable para relacionarlas;
5. NO inventar Requisiciones;
6. NO crear vínculos heurísticos sin evidencia.

Si existen Órdenes históricas sin Requisición:

- diseñar estrategia de compatibilidad histórica separada;
- mantener trazabilidad;
- no falsear datos;
- no romper la integridad de los documentos históricos.

Para NUEVAS Órdenes de Compra la obligatoriedad sí debe quedar aplicada.

Si la arquitectura permite una migración segura de todas las filas existentes, hacerla solo con evidencia verificable y documentada.

---

# 20. INTEGRACIÓN CON CXP

La lógica existente indica que cuando una OC pasa a `APROBADA` puede sincronizar una Cuenta por Pagar.

Mantener esta integración.

La validación Requisición → OC debe ocurrir antes de cualquier efecto financiero posterior.

Flujo:

```text
Requisición válida
      ↓
Crear OC válida
      ↓
Estados normales de OC
      ↓
APROBADA
      ↓
Sincronización CxP existente
```

No duplicar creación de CxP.

---

# 21. INTEGRACIÓN CON RECEPCIÓN E INVENTARIO

No alterar innecesariamente el flujo existente:

```text
OrdenCompra
   ↓
RecepcionCompra
   ↓
Inventario / Kardex
```

La Requisición se convierte en el antecedente comercial/procurement de la OC.

La recepción no debe volver a crear una OC ni modificar el presupuesto de Requisición por fuera de la lógica SSoT.

---

# 22. TRAZABILIDAD COMPLETA

Debe ser posible navegar:

```text
Cotización ACEPTADA
        ↓
Requisición
        ↓
Órdenes de Compra
        ↓
Recepciones
        ↓
CxP / Gastos
        ↓
Inventario
```

Desde la Requisición mostrar:

```text
Órdenes de Compra relacionadas
```

Con:

```text
Número
Fecha
Proveedor
Estado
Valor
```

Y resumen:

```text
Valor Requisición
Valor comprometido
Saldo disponible
```

Desde cada OC mostrar:

```text
Requisición origen
Cotización origen
```

---

# 23. SEGURIDAD MULTITENANT

Nunca aceptar un `empresa_id` arbitrario enviado por el cliente para resolver la Requisición.

La Requisición debe resolverse dentro del tenant/OrganizationalScope actual.

Validar siempre:

```text
request tenant
    =
Requisición tenant
    =
OrdenCompra tenant
```

y respetar las reglas de `SedeAwareModel` cuando correspondan.

---

# 24. TESTS QUE DEBEN PREPARARSE

No ejecutes los tests todavía.

Primero implementa todo y realiza auditoría propia.

Después prepara tests para:

### Creación válida

```text
REQ = $10M
OC = $4M
=> permitido
```

### Creación parcial

```text
REQ = $10M
OC1 = $4M
OC2 = $3M
OC3 = $3M
=> permitido
```

### Exceso individual

```text
REQ = $10M
OC = $10.000.001
=> rechazado
```

### Exceso acumulado

```text
REQ = $10M
OC1 = $6M
OC2 = $4.000.001
=> rechazado
```

### Sin requisición

```text
OC.requisicion = null
=> rechazado
```

### Requisición sin saldo

```text
REQ = $10M
Comprometido = $10M
Nueva OC
=> rechazado
```

### Edición

Validar que modificar una OC tampoco permita superar el límite acumulado.

### Anulación

Validar que el estado que libera compromiso realmente libere el saldo.

### Concurrencia

Dos transacciones simultáneas intentando consumir el mismo saldo.

El resultado final nunca debe superar:

```text
SUM(OC válidas) <= REQ total
```

### Tenant isolation

Una OC no puede usar una Requisición de otro tenant.

### API

Intentar crear OC directamente sin Requisición.

### Frontend

Validar que el botón **Buscar Requisición** funcione y que la selección muestre el saldo real.

---

# 25. ORDEN DE IMPLEMENTACIÓN

## FASE 0 — AUDITORÍA

Inspecciona:

- `apps/tenant/compras/models.py`
- `apps/tenant/compras/services/`
- `apps/tenant/compras/api/`
- frontend de Compras
- modelo/servicios actuales de Requisición
- estados de OC
- cálculos financieros
- integración CxP
- recepción
- migraciones
- documentación de arquitectura

Entrega internamente un mapa de impacto antes de modificar.

## FASE 1 — MODELO

Agregar/adaptar relación obligatoria:

```text
OrdenCompra -> Requisicion
```

y sus índices/constraints necesarios.

## FASE 2 — DOMAIN / SERVICE LAYER

Implementar:

- creación desde Requisición;
- cálculo de comprometido;
- cálculo de saldo;
- validación acumulada;
- validación de edición;
- control de concurrencia;
- estados que liberan o mantienen compromiso.

## FASE 3 — API

Actualizar:

- selectors;
- serializers;
- viewsets;
- endpoints de búsqueda;
- endpoints de creación/edición;
- contratos OpenAPI.

## FASE 4 — FRONTEND

Agregar:

```text
[ Buscar Requisición ]
```

y mostrar:

```text
Valor
Comprometido
Saldo
```

Reutilizar componentes existentes.

## FASE 5 — INTEGRACIONES

Verificar:

- CxP;
- Recepciones;
- Inventario;
- Proyectos;
- Facturas;
- Gastos.

No duplicar SSoT.

## FASE 6 — DOCUMENTACIÓN

Actualizar:

- arquitectura;
- flujo de Compras;
- Requisiciones;
- API;
- OpenAPI;
- trazabilidad;
- reglas de valor;
- estados.

## FASE 7 — AUTOAUDITORÍA

Antes de ejecutar tests, revisar:

- duplicación de lógica;
- bypass de validaciones;
- problemas de concurrencia;
- inconsistencias de tenant;
- edición;
- cancelación/anulación;
- cálculos de saldo;
- endpoints alternativos;
- frontend vs backend;
- migraciones;
- documentación.

Corregir primero todo lo encontrado.

---

# 26. REGLA INNEGOCIABLE DE NEGOCIO

La implementación final debe garantizar:

```text
NO REQUISICIÓN
      ↓
NO ORDEN DE COMPRA
```

y:

```text
OC nueva <= saldo disponible de la Requisición
```

y para múltiples OC:

```text
SUM(OC válidas de una Requisición)
        <=
VALOR TOTAL DE LA REQUISICIÓN
```

Esta regla debe ser verdadera incluso:

- usando API;
- usando frontend;
- usando admin;
- usando MCP;
- en concurrencia;
- modificando una OC;
- cambiando estados.

No depender únicamente de JavaScript.

---

# 27. CRITERIO DE ACEPTACIÓN

La implementación estará completa cuando:

1. Nueva OC tenga botón **Buscar Requisición**.
2. Una OC no pueda crearse sin Requisición.
3. La Requisición sea obligatoria y pertenezca al tenant actual.
4. Una Requisición pueda generar múltiples OC.
5. El sistema calcule el compromiso acumulado real.
6. Ninguna OC pueda exceder el saldo disponible.
7. El acumulado nunca supere el valor de la Requisición.
8. Las ediciones respeten el mismo límite.
9. La anulación/liberación respete los estados reales.
10. Exista protección contra concurrencia.
11. Los datos mostrados en frontend provengan del backend.
12. Se conserve el flujo actual de CxP, Recepción e Inventario.
13. No se introduzcan Signals de negocio.
14. No se duplique lógica entre frontend, serializer, ViewSet y Service.
15. Se actualicen API, OpenAPI y documentación.
16. Se preserve la trazabilidad Cotización → Requisición → OC.

---

# 28. GATE FINAL PARA EJECUTAR TESTS

NO ejecutes los tests al comenzar ni durante las primeras fases.

Primero completa:

```text
implementación
→ revisión
→ autoauditoría
→ correcciones
→ documentación
```

Solo cuando todo esté implementado y auditado, detén el proceso y solicita autorización explícita con este mensaje exacto:

> **“IMPLEMENTACIÓN Y AUTOAUDITORÍA COMPLETADAS. ¿AUTORIZAS EJECUTAR LOS TESTS?”**

Solo después de una respuesta afirmativa ejecuta la batería de tests y corrige los fallos encontrados.

---

# RESULTADO ESPERADO

El módulo de Compras debe operar así:

```text
COTIZACIÓN ACEPTADA
        ↓
REQUISICIÓN
        │
        ├── OC 1 ──┐
        ├── OC 2 ──┤
        ├── OC 3 ──┤
        └── OC N ──┘
                  ↓
        SUMA OC <= REQUISICIÓN
                  ↓
        SALDO DISPONIBLE
                  ↓
        RECEPCIÓN / CxP / INVENTARIO
```

La Requisición se convierte en el límite de autorización de compra y en el antecedente obligatorio de toda nueva Orden de Compra.
