# PLAN DE ACCIÓN — VINCULAR FACTURA DE COMPRA EN APP COMPRAS

## OBJETIVO

Implementar en `apps/tenant/compras/` un flujo equivalente al existente en Ventas para **buscar, revisar y vincular Facturas de Compra existentes en `apps/tenant/facturas/`**, manteniendo `Facturas` como dueño fiscal y `Compras` como dueño operacional de la relación de compra.

La experiencia objetivo es:

```text
COMPRAS
   ↓
[ Buscar / Vincular Factura de Compra ]
   ↓
FACTURAS
   ↓
filtrar naturaleza COMPRA
   ↓
buscar
   ↓
seleccionar factura
   ↓
validar proveedor / tenant / estado / duplicidad
   ↓
vincular
   ↓
COMPRAS
   ↓
Factura visible + trazabilidad + CxP
```

La relación debe ser real, auditable, reversible según las reglas de negocio y con CRUD completo de la **relación**, sin convertir Compras en un segundo sistema fiscal.

---

# 1. BASELINE ACTUAL QUE DEBE RESPETARSE

La documentación actual establece que:

- `apps/tenant/facturas/` es el dueño fiscal.
- Compras consume la factura sin duplicar CUFE, XML, IVA, total o estado fiscal.
- Existe ya un modelo `RequisicionFactura` dentro de `apps/tenant/compras/requisiciones/`.
- La API de Requisiciones actualmente documenta una acción `vincular-factura`.
- `CuentasPagar` mantiene `factura_uuid` y `orden_compra_uuid` como soft references y la lectura de Factura se realiza mediante `FacturaInterAppAPI`.
- El patrón de Service Layer del proyecto es:

```text
ViewSet
  ↓
ServiceMixin
  ↓
BusinessService
  ↓
CRUDService
```

Por tanto:

**NO construir desde cero una integración fiscal paralela.**

La primera fase debe determinar qué parte del vínculo Factura→Requisición ya existe realmente y qué parte falta en Compras/OrdenCompra.

---

# 2. FUENTE DE VERDAD

Antes de modificar código:

```text
AGENTS.md
↓
arquitectura_general(20260926-192508).md
↓
apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md
↓
documentación de Requisiciones
↓
apps/tenant/ventas/.agent/ARQUITECTURA_VENTAS.md
↓
documentación/prompt de integración Facturas↔Ventas
↓
código real de apps/tenant/facturas
↓
código real de apps/tenant/compras
```

La documentación es una guía.

Cuando documentación y código real difieran:

```text
CÓDIGO REAL
>
DOCUMENTACIÓN HISTÓRICA
```

La discrepancia debe documentarse y no ocultarse.

---

# 3. FASE 0 — AUDITORÍA REAL

Auditar como mínimo:

```text
apps/tenant/facturas/
apps/tenant/compras/
apps/tenant/compras/requisiciones/
apps/tenant/proveedores/
```

Inspeccionar:

```text
models.py
services/
selectors.py
api/
serializers.py
viewsets.py
urls.py
templates/
static/
migrations/
tests/
```

Buscar:

```text
Factura
FacturaBusinessService
FacturaInterAppAPI
FacturaReadService
RequisicionFactura
vincular_factura
factura_uuid
factura_asociada
orden_compra_uuid
proveedor
naturaleza
origen
source_system
cufe
numero
```

Generar internamente una matriz:

| Elemento | SSoT | Relación actual | Editable desde Compras |
|---|---|---|---|
| Número factura | Facturas | Referencia | No |
| CUFE | Facturas | Referencia | No |
| XML/PDF fiscal | Facturas | Referencia | No |
| Total fiscal | Facturas | Referencia | No |
| Estado fiscal | Facturas | Referencia | No |
| Proveedor | validar contra Compras | Referencia | No desde vínculo |
| Orden de Compra | Compras | Relación operacional | Sí según workflow |
| Requisición | Compras/Requisiciones | Relación documental | Sí según workflow |
| CxP | Proveedores | `factura_uuid` / `orden_compra_uuid` | Según contrato actual |

---

# 4. FASE 1 — DETERMINAR EL OBJETO AL QUE SE VINCULA

No asumir automáticamente que la Factura debe vincularse únicamente a `OrdenCompra` ni únicamente a `RequisicionCompra`.

Auditar el flujo real:

```text
Requisición
→ OrdenCompra
→ Recepción
→ Factura
→ CxP
```

Determinar cuál es el SSoT correcto para el vínculo operacional.

La solución debe permitir como mínimo:

```text
Facturas
   ↓
Compras
```

sin crear dos relaciones independientes que puedan contradecirse.

## Regla

Debe existir:

```text
UNA FUENTE DE VERDAD PARA LA RELACIÓN
```

y luego mostrarla en:

```text
Requisición
OrdenCompra
Recepción
CxP
```

cuando corresponda.

---

# 5. FASE 2 — REUTILIZAR `RequisicionFactura` SI ES EL SSoT ADECUADO

La arquitectura actual ya documenta:

```text
RequisicionFactura
```

como vínculo dentro del submódulo de Requisiciones.

Auditar:

```text
campos
constraints
empresa
requisicion
factura_uuid
tipo_relacion
es_principal
observacion
created_at
```

Determinar si este modelo:

1. ya permite el flujo solicitado;
2. necesita ampliarse;
3. debe coexistir con una relación OC↔Factura;
4. o debe convertirse en la relación documental de compras que luego se proyecta a OC.

No crear un segundo vínculo equivalente sin justificarlo.

---

# 6. FASE 3 — REGLA DE NATURALEZA DE FACTURA

El buscador de Compras debe consultar únicamente Facturas cuya naturaleza real sea:

```text
COMPRA
```

No confiar en:

```text
número de factura
proveedor
usuario
valor
```

como sustitutos de la clasificación.

Usar el SSoT real de:

```text
Factura.naturaleza
```

o su equivalente actual.

La búsqueda debe excluir:

```text
VENTA
NOTA CRÉDITO no compatible
NOTA DÉBITO no compatible
otros tipos no aplicables
```

según las reglas reales de `facturas`.

---

# 7. FASE 4 — BUSCADOR "VINCULAR FACTURA DE COMPRA"

En el módulo:

```text
workspace/#compras
```

agregar, según el objeto de negocio confirmado por la auditoría:

```text
[ Buscar / Vincular Factura de Compra ]
```

El botón debe reutilizar el patrón visual ya implementado para Ventas:

```text
Offcanvas / modal
HTMX
mostrarOffcanvasSeguro(...)
```

NO crear una nueva librería de UI.

El buscador debe ser server-side.

---

# 8. FILTROS DEL BUSCADOR

Permitir:

```text
Número factura
Prefijo
CUFE
NIT proveedor
Proveedor
Fecha emisión
Fecha vencimiento
Estado fiscal
Total
Orden de Compra
```

Solo habilitar filtros que realmente existan en el modelo/API.

Resultados:

```text
Factura
Proveedor
NIT
Número
Fecha
Vencimiento
Estado
Total
CUFE
Orden relacionada
Estado del vínculo
Acción
```

Ejemplo:

```text
FAC-4587
Proveedor XYZ
NIT 900123456

28/09/2026
$8.540.000

CUFE: **************

[ Vincular ]
```

---

# 9. EXCLUIR FACTURAS YA VINCULADAS

El endpoint de búsqueda debe poder diferenciar:

```text
Factura de compra disponible
Factura ya vinculada
Factura vinculada a otra compra
Factura inválida
```

Por defecto:

```text
mostrar disponibles
```

y ofrecer filtro:

```text
[ Todas ]
[ Disponibles ]
[ Vinculadas ]
```

Nunca ocultar una inconsistencia.

Si una factura aparece vinculada a dos documentos incompatibles:

```text
⚠ CONFLICTO DE VINCULACIÓN
```

y no permitir una nueva asociación automática.

---

# 10. VALIDACIÓN DEL PROVEEDOR

Al vincular:

```text
Factura.proveedor
        ↓
debe ser compatible con
        ↓
OrdenCompra.proveedor
```

si el objeto destino tiene proveedor.

Si no coinciden:

```text
NO permitir vincular silenciosamente.
```

Mostrar:

```text
El proveedor de la Factura de Compra no coincide
con el proveedor del documento de Compras.
```

Solo permitir una excepción si ya existe una regla real de negocio documentada.

No crear excepciones ad-hoc.

---

# 11. VALIDACIÓN DE TENANT

Debe cumplirse:

```text
Factura.empresa
     =
Compras.empresa
```

Aplicar:

```text
OrganizationalScope
DSV
```

y las reglas de `FacturaInterAppAPI`.

Nunca aceptar:

```json
{
  "empresa_id": "otro-tenant"
}
```

del frontend.

---

# 12. VINCULACIÓN UNITARIA

Flujo:

```text
[ Vincular ]
     ↓
resolver Factura
     ↓
validar naturaleza COMPRA
     ↓
validar tenant
     ↓
validar proveedor
     ↓
validar estado
     ↓
validar duplicidad
     ↓
transaction.atomic()
     ↓
crear relación
     ↓
actualizar integraciones permitidas
     ↓
resultado
```

Usar `select_for_update()` donde exista riesgo de doble vinculación concurrente.

---

# 13. SERVICIO SSoT

Crear o adaptar un servicio especializado.

Nombre conceptual:

```python
FacturaCompraLinkService
```

ó reutilizar un equivalente real existente.

Métodos conceptuales:

```python
listar_facturas_disponibles(...)
obtener_factura(...)
validar_vinculacion(...)
vincular(...)
desvincular(...)
actualizar_vinculo(...)
obtener_vinculos(...)
```

No copiar la lógica de Ventas literalmente.

Reutilizar el patrón:

```text
facturas
     ↓
service de vinculación
     ↓
Compras
```

adaptándolo al dominio de compras.

---

# 14. NO DUPLICAR LA FACTURA

Compras NO debe crear un modelo fiscal paralelo con campos duplicados como:

```text
numero
cufe
subtotal
iva
total
estado_dian
xml
```

si esos campos ya pertenecen a `Factura`.

Preferir:

```text
factura_uuid
```

o la relación segura existente.

La visualización debe consultar a:

```text
Facturas SSoT
```

---

# 15. DATOS MOSTRADOS EN COMPRAS

Cuando una Factura esté vinculada, mostrar:

```text
Factura de Compra
────────────────────────
Número
CUFE
Fecha emisión
Vencimiento
Proveedor
Subtotal
Impuestos
Total
Estado fiscal
```

Todos los valores fiscales deben provenir de Facturas.

No permitir editar esos datos desde Compras.

---

# 16. CRUD COMPLETO DE LA RELACIÓN

"CRUD completo" significa gestionar la relación, no editar la factura fiscal.

## CREATE

```text
Buscar factura
→ Vincular
```

## READ

Desde Compras:

```text
Ver factura vinculada
```

## UPDATE

Permitir cambiar la asociación únicamente mediante flujo explícito y validado:

```text
Desvincular
→ seleccionar nueva factura
→ validar
→ vincular
```

No permitir cambiar silenciosamente:

```text
factura_uuid
```

con un PATCH genérico.

## DELETE

No eliminar la Factura.

Eliminar únicamente el vínculo:

```text
Desvincular factura
```

y solo cuando el estado del documento lo permita.

Si ya existen:

```text
CxP
Recepción
pagos
asientos
otros efectos fiscales
```

bloquear la desvinculación o exigir el workflow real correspondiente.

Nunca borrar una Factura fiscal desde Compras.

---

# 17. REGLA DE DESVINCULACIÓN

No permitir:

```text
Factura vinculada
+
CxP materializada
+
pago aplicado
→
DELETE vínculo
```

sin evaluar las dependencias.

Primero identificar qué efectos downstream existen.

La IA editora debe construir un mapa:

```text
Factura
├── CxP
├── pagos
├── recepción
├── contabilidad
└── documentos relacionados
```

y determinar las reglas existentes.

---

# 18. FACTURA YA ASOCIADA A OTRA ORDEN

Caso:

```text
Factura F-001
       ↓
OC-001
```

Usuario intenta:

```text
OC-002
       ↓
F-001
```

Por defecto:

```text
BLOQUEAR
```

Mostrar:

```text
Esta factura ya está vinculada a OC-001.
```

Solo permitir múltiples órdenes si la auditoría del dominio demuestra que esa cardinalidad es válida.

No inventar una relación N:N fiscal.

---

# 19. RELACIÓN CON REQUISICIÓN

Como actualmente existe `RequisicionFactura`, resolver explícitamente:

```text
Factura
   ↓
Requisición
   ↓
OrdenCompra
```

y también:

```text
Factura
   ↓
OrdenCompra
```

si la operación requiere asociación directa.

El usuario no debe terminar con dos vínculos independientes contradictorios.

La pantalla debe mostrar una sola trazabilidad:

```text
FACTURA COMPRA
      ↓
ORDEN COMPRA
      ↓
REQUISICIONES
```

o:

```text
FACTURA COMPRA
      ↓
REQUISICIÓN
      ↓
ORDENES DE COMPRA
```

según el SSoT confirmado en FASE 1.

---

# 20. IMPACTO EN CXP

La arquitectura actual de `CuentasPagar` utiliza:

```text
factura_uuid
orden_compra_uuid
```

como soft references.

Por tanto, al vincular una Factura de Compra:

1. revisar si CxP ya existe;
2. revisar si debe materializarse;
3. reutilizar `CuentasPagar` y sus servicios;
4. no crear una segunda cuenta por pagar;
5. no mover la lógica financiera al frontend.

Si el vínculo Factura↔Compra debe actualizar CxP:

```text
FacturaCompraLinkService
      ↓
contrato CxP existente
```

No crear:

```text
nuevo sistema CxP
```

---

# 21. IDEMPOTENCIA

Este flujo debe ser idempotente.

Dos solicitudes:

```text
Vincular Factura F-001 a OC-001
```

no deben crear:

```text
2 vínculos
2 CxP
2 registros
```

Resultado:

```text
1 relación
```

Usar constraints y transacciones.

---

# 22. CONCURRENCIA

Escenario:

```text
Usuario A → vincular F-001
Usuario B → vincular F-001
```

de forma simultánea.

Solo uno puede crear la vinculación válida si la cardinalidad del dominio es 1:1.

Usar:

```python
transaction.atomic()
select_for_update()
```

y constraints DB cuando sea posible.

---

# 23. API

Mantener `config/api_urls.py` como SSoT.

Agregar/adaptar endpoints conceptualmente:

```text
GET  /api/v1/compras/facturas-disponibles/
GET  /api/v1/compras/{uuid}/factura/
POST /api/v1/compras/{uuid}/vincular-factura/
POST /api/v1/compras/{uuid}/desvincular-factura/
PATCH /api/v1/compras/{uuid}/factura-vinculo/
```

Si el vínculo realmente pertenece a Requisición:

```text
/api/v1/compras/requisiciones/{uuid}/...
```

debe seguir siendo el endpoint SSoT.

No duplicar ambos contratos.

---

# 24. ENDPOINT DE BÚSQUEDA

La búsqueda debe retornar únicamente datos necesarios:

```json
{
  "uuid": "...",
  "numero": "...",
  "proveedor": "...",
  "fecha_emision": "...",
  "fecha_vencimiento": "...",
  "total": "...",
  "estado": "...",
  "cufe": "...",
  "vinculada": false
}
```

Nunca enviar XML completo en el listado.

No exponer información fiscal innecesaria.

Paginación server-side.

---

# 25. SERIALIZERS

El serializer solamente valida:

```text
UUID
tipo
formato
payload
```

La regla:

```text
Factura COMPRA
Proveedor correcto
Tenant correcto
No duplicada
Documento compatible
```

debe permanecer en Service Layer.

No permitir:

```json
{
  "factura_uuid": "otro-tenant"
}
```

aunque el UUID tenga formato correcto.

---

# 26. FRONTEND — BOTÓN

En el listado/detalle de Compras:

```text
Factura de Compra
[ Buscar / Vincular Factura ]
```

Cuando ya exista:

```text
Factura F-4587
Proveedor XYZ
$8.540.000
[ Ver ]
[ Desvincular ]
```

En el detalle:

```text
┌───────────────────────────────┐
│ FACTURA DE COMPRA             │
│ F-4587                        │
│ Proveedor XYZ                 │
│ $8.540.000                    │
│ Estado: VALIDADA              │
│                               │
│ [VER FACTURA] [DESVINCULAR]  │
└───────────────────────────────┘
```

---

# 27. BUSCADOR VISUAL

Reutilizar el diseño de Ventas:

```text
Buscar Factura de Compra

[ Número / CUFE / NIT / proveedor ]

Fecha desde [ ] Fecha hasta [ ]

[ Buscar ]
```

Resultados:

```text
┌───────────────────────────────────────────────────────┐
│ F-4587 │ XYZ │ 28/09/26 │ $8.540.000 │ VALIDADA     │
│                                                   │
│ [ Ver ] [ Vincular ]                              │
└───────────────────────────────────────────────────────┘
```

---

# 28. VINCULAR DESDE NUEVA ORDEN DE COMPRA

Evaluar si el flujo de negocio necesita:

```text
Nueva Orden de Compra
   ↓
[ Vincular Factura ]
```

Si todavía no existe OC:

```text
facturaPendienteUuid
```

puede utilizarse durante la creación, como patrón de Ventas, pero:

```text
la vinculación real ocurre después de que exista la OC
```

No guardar relaciones huérfanas.

Si el dominio exige que la Factura se vincule posteriormente a una OC aprobada/recibida, respetar esa regla.

---

# 29. VINCULAR DESDE REQUISICIÓN

Como el API actual de Requisiciones ya documenta la acción:

```text
vincular-factura
```

esta misión debe:

1. localizar su implementación real;
2. verificar si funciona;
3. verificar si filtra COMPRA;
4. verificar si tiene CRUD completo;
5. reutilizarla si cumple;
6. corregirla si está incompleta;
7. evitar crear otra implementación paralela.

---

# 30. TRAZABILIDAD

Mostrar:

```text
COTIZACIÓN
   ↓
REQUISICIÓN
   ↓
ORDEN COMPRA
   ↓
FACTURA COMPRA
   ↓
CXP
   ↓
PAGO
```

No duplicar documentos.

Cada nodo debe permitir:

```text
[Ver]
```

y mostrar datos SSoT.

---

# 31. INTEGRACIÓN CON COTIZACIÓN

Si la Orden/Requisición proviene de una Cotización, mostrar:

```text
Cotización
   ↓
Requisición
   ↓
OrdenCompra
   ↓
Factura Compra
```

La Factura de Compra no debe modificar la Cotización comercial de cliente.

---

# 32. CONTROL DE VALOR

La Factura de Compra puede diferir del valor de la Orden.

No asumir automáticamente:

```text
Factura.total == OC.total
```

Crear un resumen:

```text
OC:       $10.000.000
Factura:  $ 9.850.000
Diferencia: -$150.000
```

y alertar:

```text
🟡 Factura inferior a Orden
```

Si:

```text
Factura > OC
```

mostrar:

```text
🔴 Factura supera Orden de Compra
```

La acción concreta debe depender de reglas reales de CxP/Compras.

No aprobar automáticamente diferencias sin una regla de tolerancia existente.

---

# 33. CONTROL DE CANTIDADES

Si factura y OC tienen detalle confiable:

```text
Item factura
   ↔
Item orden
```

permitir conciliación progresiva.

Pero no inventar matching por descripción textual.

Prioridad:

```text
referencia explícita
UUID
código de producto/servicio
referencia contractual
```

Heurística solo si existe evidencia y queda documentada.

Si no existe mapping:

```text
mostrar advertencia
```

y mantener vinculación a nivel documento.

---

# 34. CRUD DEL WIDGET

El widget debe contemplar:

```text
Estado A — Sin factura
[ Buscar / Vincular ]

Estado B — Seleccionando
Buscador + resultados

Estado C — Vinculada
Datos factura + Ver + Desvincular

Estado D — Conflicto
Factura ya usada / proveedor incompatible

Estado E — Error
Mensaje de dominio
```

No dejar estados de UI imposibles.

---

# 35. PERMISOS

Separar:

```text
ver factura
vincular factura
desvincular factura
```

No asumir que quien puede leer Compras puede modificar relaciones.

Aplicar permisos centrales.

---

# 36. AUDITORÍA

Registrar:

```text
usuario
fecha
factura
documento Compras
acción
resultado
motivo
```

Ejemplos:

```text
VINCULO_FACTURA_COMPRA
DESVINCULO_FACTURA_COMPRA
CAMBIO_FACTURA_COMPRA
```

No utilizar Signals de negocio.

El registro debe salir del Service Layer.

---

# 37. DATOS HISTÓRICOS

Antes de modificar el modelo:

```text
auditar facturas COMPRA
auditar CuentasPagar.factura_uuid
auditar CuentasPagar.orden_compra_uuid
auditar RequisicionFactura
auditar OrdenCompra
```

Construir:

```text
REPORTE DE RECONCILIACIÓN
```

clasificando:

```text
Factura compra vinculada correctamente
Factura compra sin Compra
Factura compra vinculada a CxP
Factura compra ambigua
Factura compra duplicada
```

No crear vínculos históricos automáticamente por:

```text
valor
fecha
proveedor
```

si no existe una coincidencia inequívoca.

---

# 38. NO DUPLICAR FACTURA EN COMPRAS

Está prohibido crear un sistema fiscal paralelo como copia de:

```text
Factura
```

La relación debe ser:

```text
Compras
    └── factura_uuid / relación
           ↓
       Facturas SSoT
```

---

# 39. DOCUMENTOS Y PDF/XML

Si el usuario pulsa:

```text
[ Ver factura ]
```

redirigir o abrir el documento real de Facturas.

No copiar:

```text
XML
PDF
CUFE
QR
```

a Compras.

---

# 40. FASE 5 — INTEGRACIÓN CXP

Verificar:

```text
Factura
   ↓
CuentasPagar
```

y:

```text
OrdenCompra
   ↓
CuentasPagar
```

La vinculación debe evitar duplicar la cuenta.

Si la CxP no existe:

```text
determinar mediante contrato actual
```

si debe materializarse.

No inventar comportamiento financiero.

---

# 41. FASE 6 — DETALLE DE COMPRAS

Agregar en el detalle:

```text
Pestaña / bloque:
FACTURA DE COMPRA
```

Contenido:

```text
Factura
Proveedor
Fecha
Vencimiento
Subtotal
IVA
Total
Estado fiscal
Estado de pago
CxP
```

Acciones:

```text
Ver
Desvincular
```

si están permitidas.

---

# 42. FASE 7 — LISTADO DE FACTURAS DE COMPRA

Evaluar agregar dentro de:

```text
workspace/#compras
```

una pestaña:

```text
Facturas de Compra
```

solo si el flujo del módulo lo justifica.

Debe mostrar:

```text
Factura
Proveedor
OrdenCompra
Requisición
Fecha
Total
Estado
CxP
```

y permitir:

```text
Ver
Vincular
```

No crear un segundo listado general de Facturas; esto sería una vista operacional de Compras sobre la SSoT de Facturas.

---

# 43. FASE 8 — OPENAPI Y DOCUMENTACIÓN

Actualizar:

```text
OpenAPI
docs/compras/
apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md
```

Documentar:

```text
Factura fiscal → Facturas
Relación de compra → Compras
CxP → Proveedores
```

y:

```text
crear vínculo
leer vínculo
cambiar vínculo
eliminar vínculo
```

---

# 44. FASE 9 — MIGRACIONES

Solo después de confirmar el modelo real:

```text
crear migración
```

Si se modifica `RequisicionFactura`, preservar datos.

Si se incorpora una relación a `OrdenCompra`:

```text
migración aditiva
```

primero.

No hacer `DROP` de relaciones existentes sin backfill/auditoría.

---

# 45. FASE 10 — AUTOAUDITORÍA

Antes de dar por terminada la implementación:

### Integridad

```text
[ ] Factura solo COMPRA
[ ] tenant correcto
[ ] proveedor compatible
[ ] no duplicados
[ ] constraints
[ ] concurrencia
```

### Arquitectura

```text
[ ] Facturas sigue siendo SSoT fiscal
[ ] Compras no duplica XML/CUFE/totales
[ ] CxP no se duplica
[ ] no GenericForeignKey innecesario
[ ] Service Layer SSoT
[ ] no Signals
```

### UI

```text
[ ] botón visible
[ ] buscador server-side
[ ] resultados correctos
[ ] vínculo visible
[ ] desvinculación protegida
[ ] UX coherente con Ventas
```

### Integración

```text
[ ] Requisición
[ ] OrdenCompra
[ ] Recepción
[ ] Factura
[ ] CxP
[ ] Proveedor
```

---

# 46. TESTING

No ejecutar tests durante la implementación si el usuario no los ha autorizado.

Preparar al final pruebas para:

```text
buscar factura COMPRA
excluir VENTA
vinculación válida
tenant isolation
proveedor incompatible
factura ya vinculada
doble vinculación
desvinculación válida
desvinculación bloqueada
edición de relación
CRUD completo
idempotencia
concurrencia
CxP
RequisicionFactura
OrdenCompra
regresión Ventas
regresión Facturas
```

La ejecución queda para la fase manual del usuario.

---

# 47. COMANDOS FINALES A ENTREGAR — NO EJECUTAR

Después de implementación y autoauditoría, entregar únicamente los comandos adecuados al repositorio real.

Como base a ajustar:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
pytest apps/tenant/compras/tests
pytest apps/tenant/compras/requisiciones/tests
pytest apps/tenant/facturas/tests
pytest apps/tenant/ventas/tests
```

No ejecutar.

---

# 48. CRITERIOS DE ACEPTACIÓN

La misión estará completa cuando:

1. En Compras exista botón:

```text
[ Buscar / Vincular Factura de Compra ]
```

2. El buscador consulte realmente `Facturas`.
3. Solo muestre Facturas de naturaleza `COMPRA`.
4. Respete tenant.
5. Valide proveedor.
6. Impida duplicidades.
7. Permita vincular.
8. Permita consultar la factura vinculada.
9. Permita modificar el vínculo mediante flujo controlado.
10. Permita desvincular cuando las dependencias lo permitan.
11. No permita borrar la Factura fiscal desde Compras.
12. Mantenga Facturas como SSoT fiscal.
13. Integre correctamente Requisición/OrdenCompra/CxP.
14. Use Service Layer.
15. Use DSV.
16. Tenga auditoría.
17. Sea idempotente.
18. Sea seguro ante concurrencia.
19. Se documente en OpenAPI.
20. Mantenga el patrón UX existente de Ventas.
21. No cree un segundo sistema fiscal.
22. No duplique CxP.

---

# 49. RESULTADO ESPERADO

```text
                    FACTURAS
                 SSoT FISCAL
                       │
             naturaleza = COMPRA
                       │
                       ▼
                ┌─────────────┐
                │    BUSCAR   │
                │   FACTURA    │
                └──────┬──────┘
                       │
                    VALIDAR
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Tenant         Proveedor       Duplicidad
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                   VINCULAR
                       │
             ┌─────────┴──────────┐
             ▼                    ▼
        REQUISICIÓN          ORDEN COMPRA
             │                    │
             └─────────┬──────────┘
                       ▼
                     CXP
                       │
                       ▼
                     PAGO
```

El resultado debe sentirse para el usuario igual de fluido que en Ventas, pero respetando la separación arquitectónica:

```text
FACTURAS = verdad fiscal
COMPRAS = verdad de la operación de compra
PROVEEDORES/CXP = obligación financiera
```

La vinculación debe ser **CRUD completo de la relación**, nunca CRUD fiscal de la Factura.
