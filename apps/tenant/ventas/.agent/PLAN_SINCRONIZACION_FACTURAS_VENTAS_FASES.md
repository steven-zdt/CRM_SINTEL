# PLAN DE IMPLEMENTACIÓN — SINCRONIZACIÓN DE FACTURAS EN VENTAS

**Proyecto:** Sintel Technology  
**Módulo:** `apps/tenant/ventas/`  
**Origen fiscal:** `apps/tenant/facturas/`  
**Pantalla:** `http://admin.sintel.net.co/workspace/#ventas`  
**Documento revisado:** `ARQUITECTURA_VENTAS(1).md`  
**Fecha:** 2026-09-18

## 1. Objetivo

Agregar en **Ventas** un botón funcional:

> **Sincronizar y validar facturas**

Al ejecutarlo, el sistema debe consultar las facturas de venta existentes en **Facturas**, excluir las que ya estén vinculadas a una Venta y mostrar las pendientes para revisión y vinculación.

El usuario podrá:

- revisar cada factura;
- vincular una factura individualmente;
- seleccionar varias;
- vincularlas masivamente;
- conocer el resultado individual de cada operación;
- repetir la sincronización sin generar duplicados.

Flujo:

```text
FACTURAS
   ↓
Sincronizar y validar
   ↓
Facturas de venta no vinculadas
   ↓
Revisar
   ├── Vincular una
   └── Seleccionar varias → Vincular seleccionadas
                         ↓
                       VENTAS
```

---

## 2. Hallazgos de la documentación actual

La arquitectura revisada ya contempla:

- `Venta.factura_asociada` como `OneToOneField` hacia `facturas.Factura`.
- `VentaCRUDService.vincular_factura()`.
- `GET /api/v1/facturas/buscar-para-movimiento/?naturaleza=VENTA`.
- Widget `#venta-factura-widget`.
- Vinculación desde Nueva Venta, Editar Venta y Detalle.
- Validación DSV por `empresa_id`.
- imports cross-domain de Facturas dentro de métodos.

Por tanto, **NO reconstruir la integración desde cero**. La nueva funcionalidad debe extender el mecanismo existente. fileciteturn4file0L1-L8

La documentación también advierte que algunas secciones históricas están desactualizadas; para cualquier contradicción debe prevalecer el código real actual. fileciteturn4file0L1-L8

---

# FASE 0 — INSPECCIÓN Y BASELINE

## Objetivo

Auditar primero el código real.

Revisar:

```text
apps/tenant/ventas/
apps/tenant/facturas/
models.py
services/
api/
templates/
static/
tests/
urls.py
```

Localizar exactamente:

```text
Venta.factura_asociada
VentaCRUDService.vincular_factura()
vincular-factura
buscar-para-movimiento
venta_editor.js
venta_list.js
list_ventas.html
offcanvas_crear_venta.html
offcanvas_detalle_venta.html
```

Confirmar:

```text
campo naturaleza
campo estado
empresa_id
related_name de Factura → Venta
serializers
permisos
```

### Entregable

```text
docs/remediation/FACTURAS_VENTAS_SYNC_BASELINE.md
```

### Estado

```text
PASS / FAIL / BLOCKED
```

No avanzar con `FAIL`.

---

# FASE 1 — DEFINIR QUÉ ES "SINCRONIZADA"

Una factura estará sincronizada cuando:

```text
Factura → Venta.factura_asociada
```

exista y ambas pertenezcan a la misma empresa.

Pendiente:

```text
Factura de naturaleza VENTA
+
factura sin Venta asociada
+
factura elegible
```

No elegibles:

```text
factura de compra
nota crédito
nota débito
factura inválida
factura de otro tenant
factura ya vinculada
factura ambigua
```

Los valores exactos de `naturaleza` y `estado` deben obtenerse del código real.

---

# FASE 2 — MAPEO FACTURA → VENTA

Crear matriz campo por campo:

| Factura | Venta | Tratamiento |
|---|---|---|
| cliente | cliente | DSV |
| fecha emisión | fecha_emision | copiar |
| vencimiento | fecha_vencimiento | copiar si existe |
| subtotal | subtotal | fiscal |
| impuestos | impuestos | fiscal |
| total | total_neto | normalizar |
| observaciones | observaciones | copiar si corresponde |
| número | factura_asociada | referencia |
| CUFE | factura asociada | NO duplicar |
| items | ItemVenta | snapshot compatible |

También mapear:

```text
ItemFactura
→
ItemVenta
```

No asumir nombres de campos sin inspeccionarlos.

---

# FASE 3 — AUDITAR Y REUTILIZAR API EXISTENTE

Probar:

```text
GET /api/v1/facturas/buscar-para-movimiento/?naturaleza=VENTA
```

Determinar si ya permite:

```text
excluir vinculadas
paginación
búsqueda
cliente
NIT
número
CUFE
fecha
total
estado
tenant
```

Si es suficiente:

> reutilizarlo.

Si no es suficiente:

> extenderlo o crear una acción específica únicamente donde sea necesario.

No crear endpoints duplicados.

---

# FASE 4 — SELECTOR DE FACTURAS PENDIENTES

Implementar o extender selector server-side.

Conceptualmente:

```python
Factura
.filter(
    empresa_id=empresa_id,
    naturaleza=VENTA,
)
.exclude(
    venta_origen__isnull=False
)
```

**No copiar literalmente este código**: primero identificar los nombres reales.

Debe devolver solamente:

```text
facturas elegibles y no vinculadas
```

La exclusión debe realizarse en backend, no solamente en JavaScript.

---

# FASE 5 — BOTÓN EN VENTAS

En:

```text
#/ventas
```

agregar:

```text
[ Sincronizar y validar facturas ]
```

Ubicarlo junto a las acciones existentes de:

```text
Nueva Venta
Resoluciones
Actualizar
```

Reutilizar estilos e iconografía existentes.

No agregar nueva librería UI.

El botón debe:

```text
click
→ bloquear doble click
→ spinner
→ consultar API
→ abrir panel
```

---

# FASE 6 — PANEL DE SINCRONIZACIÓN

Reutilizar el patrón Offcanvas existente.

ID conceptual:

```text
#offcanvas-sincronizar-facturas
```

Debe utilizar:

```text
mostrarOffcanvasSeguro()
```

Cabecera:

```text
Sincronizar y validar facturas
```

Resumen:

```text
Pendientes: X
Seleccionadas: 0
Ya vinculadas: X
No elegibles: X
```

---

# FASE 7 — LISTADO DE PENDIENTES

Tabla:

```text
[✓] | Factura | Cliente | NIT | Fecha | Vencimiento | Total | Estado | Acción
```

Cada fila debe permitir:

```text
[Vincular]
```

Opcional:

```text
[Ver]
```

Mostrar como mínimo:

```text
número
cliente
NIT
fecha
total
estado
CUFE
```

---

# FASE 8 — VINCULACIÓN UNITARIA

Flujo:

```text
[Vincular]
↓
validar factura
↓
buscar Venta compatible
↓
si existe → reutilizar
si no existe → crear Venta
↓
vincular factura
↓
actualizar UI
```

Confirmación:

```text
¿Desea vincular esta factura y crear/reutilizar la Venta correspondiente?
```

Nunca realizar un match ambiguo automáticamente.

---

# FASE 9 — REUTILIZAR VENTA EXISTENTE

Antes de crear una Venta:

```text
buscar coincidencia inequívoca
```

Prioridad:

```text
vínculo existente
CUFE
número + prefijo + empresa
cliente + número + fecha
```

Si existen múltiples candidatas:

```text
AMBIGUA
```

No vincular.

No crear otra Venta automáticamente.

---

# FASE 10 — VINCULACIÓN MASIVA

Agregar:

```text
checkbox por fila
checkbox maestro
contador
[Vincular seleccionadas]
```

Ejemplo:

```text
Seleccionadas: 8
```

Confirmación:

```text
Se procesarán 8 facturas.

Las ya vinculadas, inválidas o ambiguas serán omitidas.

¿Continuar?
```

---

# FASE 11 — ENDPOINT MASIVO

Solo si la arquitectura actual no tiene uno equivalente, crear una operación como:

```text
POST /api/v1/ventas/sincronizar-facturas/
```

Payload conceptual:

```json
{
  "facturas": [
    "uuid-1",
    "uuid-2",
    "uuid-3"
  ]
}
```

Validar server-side:

```text
usuario
permisos
tenant
naturaleza
existencia
estado
vínculo existente
```

Nunca confiar en que el frontend diga que una factura está pendiente.

---

# FASE 12 — SERVICE LAYER

Crear o extender un servicio especializado, por ejemplo:

```text
FacturaVentaSyncService
```

Responsabilidades:

```text
listar_pendientes()
validar_factura()
buscar_venta_candidata()
crear_venta_desde_factura()
vincular()
vincular_masivo()
```

Reutilizar:

```text
FacturaBusinessService
VentaCRUDService
selectors
validators
```

No duplicar lógica fiscal.

---

# FASE 13 — TRANSACCIONES

Operación individual:

```python
transaction.atomic()
```

Operación masiva:

preferir procesamiento seguro por factura si el dominio permite resultados parciales:

```text
Factura 1 → PASS
Factura 2 → PASS
Factura 3 → ERROR
Factura 4 → PASS
```

Cada error debe quedar identificado.

La IA editora debe documentar la estrategia escogida.

---

# FASE 14 — RESULTADO MASIVO

Mostrar:

```text
Proceso completado

Vinculadas: 8
Ya vinculadas: 2
Ambiguas: 1
Inválidas: 1
Errores: 0
```

Cada registro debe quedar clasificado:

```text
VINCULADA
YA_VINCULADA
AMBIGUA
INVALIDA
ERROR
```

Nunca ocultar errores.

---

# FASE 15 — IDEMPOTENCIA

Ejecutar:

```text
Sincronizar
```

Primera vez:

```text
10 pendientes
→ 10 vinculadas
```

Segunda vez:

```text
0 pendientes
```

Tercera vez:

```text
0 pendientes
```

No crear:

```text
ventas duplicadas
facturas duplicadas
XML duplicados
CUFE duplicados
vínculos duplicados
```

La relación `OneToOne` existente debe continuar siendo una barrera estructural.

---

# FASE 16 — CONCURRENCIA

Probar:

```text
Usuario A sincroniza
Usuario B sincroniza
```

simultáneamente.

Y:

```text
Usuario A vincula FST 375
Usuario B vincula FST 375
```

Resultado:

```text
1 Factura
1 Venta
1 vínculo
```

Usar locks/constraints adecuados al código real.

---

# FASE 17 — SEGURIDAD Y TENANT

Probar:

```text
Tenant A → Factura A = permitido
Tenant A → Factura B = rechazado
```

Probar:

```text
usuario autorizado
usuario no autorizado
UUID inexistente
UUID manipulado
```

Respetar:

```text
IsTenantMember
IsTenantAdminOrReadOnly
DSV
empresa_id
```

La documentación confirma que DSV es una regla crítica del módulo. fileciteturn4file0L1018-L1031

---

# FASE 18 — NO DUPLICAR DATOS FISCALES

La sincronización NO debe:

```text
crear Factura
crear XML
crear CUFE
editar CUFE
duplicar autorización
duplicar representación fiscal
```

Debe:

```text
Factura existente
↓
Venta
↓
Venta.factura_asociada
```

Facturas continúa siendo SSoT fiscal.

Ventas continúa siendo SSoT comercial.

---

# FASE 19 — REGRESIÓN DE VENTAS

Después de implementar probar:

```text
Nueva Venta
Ver Venta
Editar Venta
Anular Venta
Vincular Factura
Gestión Manual de Pago
Resoluciones
Actualizar listado
Buscar
Filtros
```

La arquitectura actual documenta explícitamente el mecanismo de vinculación y la gestión manual de pago; esta funcionalidad no debe romperlos. fileciteturn4file0L1-L8

---

# FASE 20 — REGRESIÓN DE FACTURAS

Probar desde Facturas:

```text
cargar factura
procesar XML
consultar factura
consultar detalle
editar campos permitidos
gestión de pago
reimportar XML
```

Confirmar que sincronizar desde Ventas no modifica la factura fiscal.

---

# FASE 21 — PRUEBAS CON DATOS REALES

Usar facturas reales ya existentes en Facturas.

Mínimo:

```text
1 factura sin vínculo
1 factura ya vinculada
1 factura con varios items
1 factura con IVA
1 factura crédito
1 factura con datos incompletos
```

Usar también:

```text
FST 375
```

si está disponible en el entorno.

---

# FASE 22 — PRUEBA MASIVA

Tomar snapshot:

```text
Facturas antes = X
Ventas antes = Y
```

Ejecutar sincronización.

Después:

```text
Facturas = X
Ventas = Y + N
```

La cantidad de Facturas no debe aumentar por sincronizar.

Validar:

```text
N = facturas nuevas efectivamente vinculadas
```

---

# FASE 23 — SUPERVISIÓN DE ESTADO

Crear:

```text
docs/remediation/FACTURAS_VENTAS_SYNC_STATUS.md
```

Contenido obligatorio:

```markdown
# Estado — Sincronización Facturas ↔ Ventas

STATUS: IN_PROGRESS

| Fase | Estado | Evidencia |
|---|---|---|
| 0 Baseline | PASS | ... |
| 1 Definición | PASS | ... |
| 2 Mapeo | PASS | ... |
| 3 API | PASS | ... |
| 4 Selector | ... | ... |
| 5 Botón | ... | ... |
| 6 Panel | ... | ... |
| 7 Listado | ... | ... |
| 8 Unitario | ... | ... |
| 9 Match Venta | ... | ... |
| 10 Masivo | ... | ... |
| 11 API masiva | ... | ... |
| 12 Service | ... | ... |
| 13 Transacciones | ... | ... |
| 14 Resultado | ... | ... |
| 15 Idempotencia | ... | ... |
| 16 Concurrencia | ... | ... |
| 17 Seguridad | ... | ... |
| 18 Integridad fiscal | ... | ... |
| 19 Regresión Ventas | ... | ... |
| 20 Regresión Facturas | ... | ... |
| 21 Datos reales | ... | ... |
| 22 Prueba masiva | ... | ... |
| 23 Documentación | ... | ... |
```

Estados permitidos:

```text
PENDING
IN_PROGRESS
PASS
FAIL
BLOCKED
```

---

# FASE 24 — REGLA DE GATES

Después de cada fase:

```text
1. implementar
2. ejecutar pruebas
3. inspeccionar resultado
4. registrar evidencia
5. actualizar STATUS
6. corregir FAIL
7. repetir
8. avanzar
```

Nunca marcar:

```text
PASS
```

sin evidencia.

Nunca avanzar con:

```text
FAIL
```

---

# FASE 25 — CHECKLIST FINAL

La implementación será PASS cuando:

```text
[ ] Existe botón Sincronizar y validar facturas.
[ ] El botón funciona desde #ventas.
[ ] Consulta Facturas reales.
[ ] Solo muestra facturas VENTA elegibles.
[ ] Excluye facturas ya vinculadas.
[ ] El filtrado es server-side.
[ ] Usuario puede revisar datos.
[ ] Existe vinculación unitaria.
[ ] Existe selección múltiple.
[ ] Existe vinculación masiva.
[ ] Existe confirmación.
[ ] Existe spinner.
[ ] Existe estado vacío.
[ ] Existe manejo de errores.
[ ] Existe resultado por factura.
[ ] No hay facturas duplicadas.
[ ] No hay Ventas duplicadas.
[ ] No hay CUFE duplicados.
[ ] No hay XML duplicados.
[ ] Se mantiene OneToOne.
[ ] Facturas sigue siendo SSoT fiscal.
[ ] Ventas sigue siendo SSoT comercial.
[ ] DSV funciona.
[ ] Tenant isolation funciona.
[ ] Permisos funcionan.
[ ] Idempotencia funciona.
[ ] Concurrencia funciona.
[ ] Nueva Venta funciona.
[ ] Editar funciona.
[ ] Ver funciona.
[ ] Anular funciona.
[ ] Gestión manual de pago funciona.
[ ] Facturas continúa funcionando.
[ ] Tests pasan.
[ ] Documentación queda alineada con código.
```

---

# REGLAS ABSOLUTAS

NO:

```text
duplicar Factura
duplicar XML
duplicar CUFE
crear segunda FK de Factura
crear ManyToMany
crear un modelo paralelo de sincronización sin necesidad
hacer matching solo por total
hacer matching ambiguo automáticamente
filtrar pendientes solo en JavaScript
ignorar tenant
ignorar permisos
silenciar errores
duplicar FacturaBusinessService
duplicar VentaCRUDService
reactivar emisión fiscal DIAN automática si está bloqueada
reintroducir arquitectura histórica descrita como obsoleta
```

La documentación actual indica que `Venta.factura_asociada` ya es `OneToOneField` y que existe un mecanismo de búsqueda/vinculación; la nueva función debe aprovechar ese contrato y concentrarse en **descubrir pendientes + revisión + vinculación unitaria/masiva**. fileciteturn4file0L154-L175 fileciteturn4file0L14-L24

---

# ARQUITECTURA OBJETIVO

```text
                    FACTURAS
                  SSoT FISCAL
                       │
                       │
             SINCRONIZAR Y VALIDAR
                       │
                       ▼
              PENDIENTES DE VÍNCULO
                       │
              ┌────────┴────────┐
              │                 │
           UNITARIA           MASIVA
              │                 │
              └────────┬────────┘
                       ▼
                 VALIDACIÓN DSV
                       │
                       ▼
              BUSCAR VENTA EXISTENTE
                       │
                ┌──────┴──────┐
                │             │
              existe        no existe
                │             │
                │        crear Venta
                │             │
                └──────┬──────┘
                       ▼
             Venta.factura_asociada
                       │
                       ▼
                     VENTAS
                 SSoT COMERCIAL
```

## DEFINICIÓN FINAL

**Sincronizar facturas** significa:

```text
DESCUBRIR
+
VALIDAR
+
REVISAR
+
VINCULAR
```

No significa:

```text
COPIAR
+
DUPLICAR
+
REIMPORTAR
```

## FIN DEL PLAN
