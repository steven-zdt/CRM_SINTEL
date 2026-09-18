# PROMPT MAESTRO — Integración Facturas ↔ Ventas + Gestión Manual de Pago

# MISIÓN

Implementar una ampliación integral del módulo `apps/tenant/ventas/` para consolidar la integración operacional entre `Ventas` y `Facturas`, manteniendo intacta la arquitectura existente, sin duplicar facturas fiscales, sin romper importaciones XML, sin romper el flujo actual de Ventas y sin introducir una arquitectura paralela.

La misión debe ejecutarse mediante un ciclo obligatorio:

**INSPECT → BASELINE → PLAN → IMPLEMENT → MIGRATE → TEST → AUDIT → FIX → REGRESSION → VERIFY → DOCUMENT → PASS**

No asumir que un campo, endpoint, serializer, modelo o función existe únicamente porque aparezca en documentación. Verificar siempre en código real.

---

# OBJETIVO FUNCIONAL

Modificar el flujo de:

`https://admin.sintel.net.co/workspace/#ventas`

especialmente:

**Ventas → Nueva Venta**

para agregar una acción:

**Buscar / Vincular Factura**

La funcionalidad debe permitir localizar facturas ya cargadas y administradas por la app `facturas`, seleccionar una factura válida y vincularla a la Venta actual.

Después de la vinculación:

1. La Venta debe quedar asociada a la factura existente.
2. Deben sincronizarse los datos provenientes de la Factura que sean propiedad comercial/operativa de Ventas.
3. No se debe crear una segunda factura fiscal.
4. No se debe duplicar el XML.
5. No se debe recalcular ni reconstruir artificialmente la factura fiscal.
6. Debe mantenerse el `OneToOne` existente entre `Venta.factura_asociada` y `Factura`.
7. Debe utilizarse el mecanismo de servicio existente o extenderlo correctamente.
8. La operación debe respetar DSV y aislamiento por tenant.
9. La vinculación debe ser idempotente.
10. La vinculación debe ser transaccional.

---

# REGLA ARQUITECTÓNICA FUNDAMENTAL

## Facturas es dueño fiscal

`apps.tenant.facturas` continúa siendo el origen fiscal de la factura.

## Ventas es dueño comercial/operacional

`apps.tenant.ventas` administra:

- Venta.
- Cliente.
- Proyecto.
- Estado comercial.
- Estado de pago.
- Seguimiento de vencimientos.
- Gestión manual del pago.
- Asociación con factura fiscal.

## Prohibición

NO crear en `ventas` otro modelo `Factura` que duplique `facturas.Factura`.

NO copiar el XML completo a un nuevo campo de Ventas salvo que ya exista un contrato explícito.

NO crear una factura fiscal paralela.

NO reemplazar `Venta.factura_asociada`.

---

# FASE 0 — INSPECCIÓN REAL

Antes de modificar código:

Auditar:

```text
apps/tenant/ventas/
apps/tenant/facturas/
```

Inspeccionar al menos:

```text
models.py
services/
api/
templates/
static/
tests/
migrations/
serializers.py
viewsets.py
urls.py
```

Buscar específicamente:

```text
Factura
FacturaBusinessService
FacturaCRUDService
FacturaSerializer
FacturaViewSet
ItemFactura
FacturaAnexos
XML
guardar_desde_dto
vincular_factura
factura_asociada
forma_pago
medio_pago
payment
estado_pago
fecha_pago
fecha_vencimiento
fecha_limite_pago
codigo_medio_pago
```

Crear un inventario de:

```text
ORIGEN → CAMPO FACTURA → CAMPO VENTA → TIPO DE SINCRONIZACIÓN
```

No avanzar hasta conocer exactamente los campos actuales de `Factura`.

---

# FASE 1 — BASELINE DE VENTAS

Confirmar que continúa existiendo:

```python
Venta.factura_asociada
```

como:

```python
OneToOneField(Factura)
```

Confirmar:

```python
related_name='venta_origen'
```

y revisar la implementación actual de:

```python
VentaCRUDService.vincular_factura()
```

La arquitectura documentada actualmente indica:

```text
factura_asociada = Factura
estado = FACTURADA_DIAN
```

Verificar que esto siga siendo cierto en código real.

No reemplazarlo.

---

# FASE 2 — AUDITORÍA DEL MODELO FACTURA

Determinar exactamente cuáles datos ya existen en `Factura`.

Identificar como mínimo:

```text
uuid
numero
numero_factura
cufe
fecha
fecha_emision
fecha_vencimiento
cliente
cliente_documento
estado
forma_pago
medio_pago
codigo_medio_pago
fecha_pago
total
subtotal
impuestos
observaciones
XML
UUID
naturaleza
origen
source_system
```

No asumir que todos existen.

Clasificar cada uno:

### A. Fiscal SSoT

Datos cuya fuente absoluta debe ser `Factura`.

Ejemplos:

```text
número factura
CUFE
fecha de emisión fiscal
XML
datos fiscales
impuestos fiscales
estado DIAN
```

### B. Comercial

Puede proyectarse a Venta:

```text
cliente
fecha vencimiento
totales comerciales
observaciones
```

### C. Gestión manual

Debe residir en Ventas si el modelo de negocio así lo determina:

```text
estado_pago
fecha_pago
fecha_limite_pago
```

### D. Derivado

No almacenar si puede calcularse de forma segura:

```text
saldo
días vencidos
estado vencido
```

siempre que exista información suficiente.

---

# FASE 3 — DISEÑAR EL CONTRATO DE SINCRONIZACIÓN

Crear un contrato explícito:

```text
Factura → Venta
```

No hacer asignaciones indiscriminadas de todos los campos.

Ejemplo conceptual:

```text
Factura.numero
        ↓
Venta.numero_factura / factura asociada

Factura.fecha_vencimiento
        ↓
Venta.fecha_vencimiento

Factura.total
        ↓
Venta.total_neto
```

pero solo después de comprobar los nombres reales.

Cada campo deberá tener:

```text
source
destination
direction
editable
synchronized_on_link
synchronized_on_refresh
```

Ejemplo:

```text
numero_factura
Factura → Venta
read-only

CUFE
Factura → Venta/consulta
read-only

estado_pago
Venta
editable

fecha_pago
Venta
editable

fecha_limite_pago
Venta
editable
```

---

# FASE 4 — NO DUPLICAR EL ESTADO

Mantener:

```text
Venta.estado
```

para el estado documental:

```text
BORRADOR
FACTURADA_DIAN
ANULADA
```

Crear, si no existe, un campo independiente:

```text
estado_pago
```

Nunca reutilizar `Venta.estado` para representar:

```text
PENDIENTE
PARCIAL
PAGADA
VENCIDA
```

Antes de crear choices nuevos:

1. inspeccionar si `Factura` ya dispone de choices;
2. reutilizar el vocabulario existente cuando sea coherente;
3. no crear dos enums para el mismo concepto;
4. documentar cualquier divergencia.

---

# FASE 5 — CAMPOS DE GESTIÓN MANUAL

Agregar al modelo `Venta` únicamente los campos que no existan ya y que sean realmente propiedad de Ventas.

Como mínimo auditar:

```text
estado_pago
fecha_pago
fecha_limite_pago
forma_pago
codigo_medio_pago
```

`fecha_vencimiento` ya existe actualmente en Venta, por lo que NO crear otro campo equivalente sin justificarlo.

Evaluar explícitamente:

```text
fecha_vencimiento
vs
fecha_limite_pago
```

Si representan exactamente el mismo concepto, evitar duplicación.

Si representan conceptos distintos:

```text
fecha_vencimiento = vencimiento de la obligación/factura

fecha_limite_pago = límite operativo definido para gestión manual
```

documentar la diferencia y validarla.

---

# FASE 6 — MIGRACIÓN DE MODELO

Crear migraciones Django únicamente después de terminar el diseño.

Las migraciones deben:

- conservar datos existentes;
- usar defaults seguros;
- permitir null cuando sea necesario para backfill;
- realizar backfill controlado;
- no modificar facturas existentes;
- no crear registros fiscales duplicados.

Ejecutar:

```bash
python manage.py makemigrations
python manage.py migrate
```

y para tenant:

```bash
make migrate-tenants
```

o el mecanismo real utilizado por el proyecto.

Nunca inventar otro proceso de migración.

---

# FASE 7 — SERVICIO DE VINCULACIÓN

Implementar una operación explícita:

```python
vincular_factura_existente(
    venta_uuid,
    factura_uuid,
    empresa
)
```

o reutilizar la existente si ya cumple todos los requisitos.

Debe:

1. localizar Venta por UUID;
2. validar empresa;
3. localizar Factura por UUID;
4. validar empresa/tenant;
5. comprobar que la Factura es elegible;
6. comprobar si ya está asociada a otra Venta;
7. comprobar si la Venta ya tiene Factura;
8. evitar reemplazo silencioso;
9. sincronizar campos autorizados;
10. cambiar el estado documental únicamente según regla existente;
11. ejecutar todo dentro de `transaction.atomic()`.

---

# FASE 8 — IDEMPOTENCIA

Casos obligatorios:

### Caso A

Venta sin factura + Factura sin Venta:

```text
VINCULAR
→ éxito
```

### Caso B

Venta ya vinculada a la misma Factura:

```text
VINCULAR NUEVAMENTE
→ éxito idempotente
→ no duplica
```

### Caso C

Venta vinculada a Factura A y usuario intenta Factura B:

```text
→ rechazar
→ no reemplazar silenciosamente
```

### Caso D

Factura ya vinculada a otra Venta:

```text
→ rechazar
→ explicar claramente
```

### Caso E

Factura de otra empresa:

```text
→ 403/404 según patrón del proyecto
→ jamás revelar existencia de datos cross-tenant
```

---

# FASE 9 — BUSCADOR DE FACTURAS

Agregar al formulario:

```text
Nueva Venta
```

un botón visible:

**Buscar / Vincular Factura**

UX recomendada:

```text
[ Buscar / Vincular Factura ]
```

Abrir modal/offcanvas siguiendo el patrón actual de Ventas.

No crear un componente universal nuevo.

---

# FASE 10 — FILTROS DEL BUSCADOR

El buscador debe permitir localizar por información realmente disponible en Factura.

Priorizar:

```text
Número de factura
CUFE
NIT / documento cliente
Razón social
Fecha
Estado
```

Solo habilitar filtros cuando el backend real los soporte.

El endpoint debe estar filtrado por:

```text
empresa_id
```

y nunca traer facturas de otro tenant.

---

# FASE 11 — RESULTADO DEL BUSCADOR

Mostrar como mínimo:

```text
Factura
Cliente
NIT
Fecha
Vencimiento
Estado
Total
CUFE
```

Agregar acción:

```text
Vincular
```

Antes de vincular:

mostrar confirmación:

```text
¿Vincular la factura FST 359 a esta venta?
```

Mostrar:

```text
Factura
Cliente
Total
Fecha
Vencimiento
```

---

# FASE 12 — SINCRONIZACIÓN POST-VINCULACIÓN

Después de vincular:

actualizar Venta con los datos permitidos.

Ejemplo:

```text
Factura FST 359
↓
Venta
```

Debe quedar visible:

```text
Factura asociada: FST 359
CUFE: ...
Fecha emisión: 20/02/2026
Vencimiento: 22/03/2026
Total: $961.520 COP
```

Usar estos datos solamente como referencia funcional/prueba cuando correspondan al documento real cargado; nunca codificarlos como constantes.

---

# FASE 13 — FORMULARIO “EDITAR FACTURA DE VENTA”

Agregar en la columna:

```text
Acciones
```

una acción nueva:

```text
Editar
```

o:

```text
Gestión manual
```

según el patrón visual actual.

Esta acción abrirá:

```text
offcanvas editar factura de venta
```

No modificar directamente la factura fiscal desde este formulario.

El formulario debe estar claramente dividido:

## Información de la factura

```text
Número de factura
CUFE
Cliente
Fecha de emisión
Fecha de vencimiento
Total
```

estos datos serán preferentemente:

```text
SOLO LECTURA
```

cuando provengan de Factura.

---

# FASE 14 — BLOQUE “GESTIÓN MANUAL”

Crear sección:

```text
GESTIÓN MANUAL
```

con:

```text
Estado de Pago
Fecha de Pago
Fecha Límite de Pago
Forma de Pago
Código Medio de Pago
```

Utilizar los campos existentes si ya están en el modelo.

No duplicar campos.

---

# FASE 15 — ESTADO DE PAGO

Implementar el control con los choices existentes si `Factura` ya los proporciona.

Si no existen y el negocio exige un estado nuevo, definirlo en Ventas con una nomenclatura clara.

Como mínimo contemplar semánticamente:

```text
Pendiente
Parcial
Pagada
Vencida
```

pero NO fijar estos valores ciegamente antes de auditar el código existente.

Reglas:

```text
PAGADA
```

debe requerir:

```text
fecha_pago
```

salvo que el sistema actual tenga otra regla comprobada.

```text
PENDIENTE
```

normalmente no debe tener `fecha_pago`.

```text
VENCIDA
```

debe poder derivarse de vencimiento + saldo/estado real cuando exista esa información.

No permitir estados contradictorios.

---

# FASE 16 — FORMA DE PAGO

La factura de referencia contiene:

```text
Forma de pago: Crédito
```

y:

```text
Medio de pago: Pago a crédito
```

La forma de pago debe poder venir desde Factura/XML.

No inventar valores.

Si el XML trae el dato:

```text
Factura/XML → Venta
```

Si no lo trae:

```text
editable manualmente
```

según la regla de negocio.

---

# FASE 17 — CÓDIGO MEDIO DE PAGO

Agregar:

```text
Código Medio de Pago
```

pero NO inferir el código a partir del texto visual del PDF.

El código exacto debe provenir del dato estructurado del XML o del modelo `Factura` cuando exista.

Si no existe en origen:

```text
permitir captura manual
```

y dejarlo claramente diferenciado como dato manual.

---

# FASE 18 — FECHAS

Mantener:

```text
fecha_emision
fecha_vencimiento
```

y evaluar:

```text
fecha_pago
fecha_limite_pago
```

Reglas mínimas:

```text
fecha_pago >= fecha_emision
fecha_vencimiento >= fecha_emision
fecha_limite_pago >= fecha_emision
```

Cuando `fecha_pago` exista:

```text
fecha_pago <= fecha actual
```

salvo que exista una operación de pago futura explícita.

No modificar `fecha_emision` fiscal de una factura vinculada.

---

# FASE 19 — PROTECCIÓN DE DATOS FISCALES

Una vez vinculada una Factura:

bloquear edición manual de:

```text
número fiscal
CUFE
XML
fecha fiscal
impuestos fiscales
totales fiscales
datos DIAN
```

Los datos fiscales deben seguir teniendo como SSoT a Factura.

La gestión manual de pago no debe alterar la identidad fiscal del documento.

---

# FASE 20 — IMPORTACIÓN XML

Esta fase es CRÍTICA.

Auditar todos los puntos de entrada XML de `facturas`.

Determinar qué sucede cuando llega:

```text
Factura XML
```

después de existir una Venta vinculada.

Garantizar que:

```text
XML importado
```

NO:

- cree una segunda Venta;
- duplique la Factura;
- sobrescriba indiscriminadamente gestión manual;
- borre `estado_pago`;
- borre `fecha_pago`;
- borre `fecha_limite_pago`.

Definir una política explícita:

### Datos fiscales

```text
Factura/XML = autoridad
```

### Datos operativos manuales

```text
Ventas = autoridad
```

No permitir que una importación XML destruya información manual.

---

# FASE 21 — REFRESH / RE-SINCRONIZACIÓN

Crear una función explícita solamente si resulta necesaria:

```text
Sincronizar datos desde Factura
```

Debe actualizar únicamente campos permitidos.

Nunca hacer:

```text
Factura → Venta
```

sobre todos los campos indiscriminadamente.

Especialmente proteger:

```text
estado_pago
fecha_pago
fecha_limite_pago
```

cuando sean datos manuales.

---

# FASE 22 — API

Extender:

```text
apps/tenant/ventas/api/
```

manteniendo:

```text
lookup_field = uuid
```

Nunca usar PK entero como contrato público.

Agregar endpoints/acciones únicamente cuando sean necesarios.

Ejemplo conceptual:

```http
GET  /api/v1/ventas/facturas-disponibles/
POST /api/v1/ventas/{uuid}/vincular-factura/
GET  /api/v1/ventas/{uuid}/gestion-pago/
PATCH /api/v1/ventas/{uuid}/gestion-pago/
```

No crear endpoints duplicados si existe infraestructura equivalente.

---

# FASE 23 — SERIALIZERS

Actualizar:

```text
VentaListSerializer
VentaDetailSerializer
```

para exponer solamente lo necesario.

Agregar:

```text
factura_uuid
factura_numero
factura_cufe
estado_pago
forma_pago
fecha_pago
fecha_limite_pago
codigo_medio_pago
```

solo si realmente existen en el modelo y son necesarios.

Separar:

```text
read_only
editable
derived
```

---

# FASE 24 — SELECTORS

Actualizar `selectors.py`.

Recordar la regla existente:

`LIST_FIELDS` y `DETAIL_FIELDS` no deben contener traversals con `__`.

Las traversals deben permanecer separadas.

Agregar las nuevas relaciones de forma compatible con:

```text
select_related()
prefetch_related()
.only()
```

sin generar N+1.

---

# FASE 25 — SERVICIO DE GESTIÓN MANUAL

Crear o extender el servicio de negocio responsable de:

```text
actualizar_gestion_pago()
```

Debe validar:

```text
empresa
venta
estado actual
factura asociada
roles
consistencia de fechas
consistencia estado_pago/fecha_pago
```

No meter reglas de negocio complejas directamente en:

```text
views.py
```

ni en JavaScript.

---

# FASE 26 — PERMISOS

Verificar:

```text
IsTenantMember
IsTenantAdminOrReadOnly
```

y el sistema real de roles.

Definir quién puede:

```text
buscar factura
vincular factura
editar gestión manual
marcar pagada
registrar fecha de pago
```

No ampliar privilegios globalmente.

---

# FASE 27 — FRONTEND

Mantener:

```text
window.Sintel.Ventas.API
window.Sintel.Ventas.List
window.Sintel.Ventas.Editor
```

No crear namespace paralelo.

`ventas.api.js` continuará siendo SSoT de endpoints.

La UI debe utilizar:

```text
mostrarOffcanvasSeguro()
```

para los offcanvas.

No introducir un segundo patrón de apertura de offcanvas que contradiga el ya establecido.

---

# FASE 28 — NUEVA VENTA

Modificar:

```text
offcanvas_crear_venta.html
```

sin destruir el formulario actual.

Agregar:

```text
[ Buscar / Vincular Factura ]
```

El usuario debe poder:

```text
1. Crear venta manual
2. Buscar factura existente
3. Seleccionar factura
4. Vincular
5. Cargar datos relacionados
6. Guardar
```

También evaluar el flujo inverso:

```text
Buscar factura antes de crear venta
```

si mejora la experiencia, pero sin duplicar pantallas.

---

# FASE 29 — EDICIÓN

Cuando exista Factura asociada:

```text
Acciones → Editar
```

abrirá:

```text
Editar factura de venta
```

Debe mostrar dos bloques:

## Bloque 1 — Factura

```text
Datos fiscales
```

solo lectura.

## Bloque 2 — Gestión manual

```text
Estado de Pago
Fecha de Pago
Fecha Límite de Pago
Forma de Pago
Código Medio de Pago
```

editable según permisos.

---

# FASE 30 — LISTADO DE VENTAS

Actualizar tabla para mostrar, cuando aplique:

```text
Factura
Estado
Estado de Pago
Vencimiento
Total
Acciones
```

No llenar la tabla con demasiadas columnas.

Puede utilizarse:

```text
Estado
Estado Pago
```

como badges independientes.

No mezclar:

```text
FACTURADA_DIAN
```

con:

```text
PAGADA
```

---

# FASE 31 — VALIDACIÓN VISUAL

Mantener el patrón actual de:

```text
django-tables2
HTMX
Bootstrap
Offcanvas
```

No migrar de tecnología ni crear una librería visual nueva solo por esta funcionalidad.

---

# FASE 32 — CASOS DE PRUEBA DE VINCULACIÓN

Crear pruebas para:

1. Factura válida → vinculación correcta.
2. Factura inexistente → error.
3. UUID inválido → error.
4. Factura de otro tenant → rechazo.
5. Factura ya vinculada → rechazo.
6. Venta ya vinculada a otra factura → rechazo.
7. Vinculación repetida de la misma factura → idempotente.
8. Rollback si falla la sincronización.
9. Totales no alterados incorrectamente.
10. CUFE correcto.
11. Número correcto.
12. Fecha de vencimiento correcta.

---

# FASE 33 — PRUEBAS DE GESTIÓN MANUAL

Crear casos:

### PENDIENTE

```text
estado_pago = PENDIENTE
fecha_pago = null
```

### PAGADA

```text
estado_pago = PAGADA
fecha_pago != null
```

### INCONSISTENTE

```text
estado_pago = PAGADA
fecha_pago = null
```

Debe rechazarse si la regla de negocio establecida así lo requiere.

### FECHA INVÁLIDA

```text
fecha_pago < fecha_emision
```

Debe rechazarse.

---

# FASE 34 — TEST DE IMPORTACIÓN XML

Prueba fundamental:

```text
1. Crear/Vincular Venta
2. Establecer gestión manual
3. Importar/reprocesar XML
4. Verificar datos fiscales actualizados
5. Verificar gestión manual intacta
```

Debe quedar demostrado que:

```text
XML no destruye gestión manual.
```

---

# FASE 35 — TEST DE IDEMPOTENCIA XML + VENTA

Escenario:

```text
Factura A
↓
Venta A
↓
Importar XML A nuevamente
```

Resultado:

```text
1 Factura
1 Venta
1 relación
0 duplicados
```

---

# FASE 36 — CONCURRENCIA

Probar dos solicitudes simultáneas:

```text
POST vincular Factura A → Venta A
POST vincular Factura A → Venta B
```

Solo una debe tener éxito.

Validar:

```text
OneToOne
IntegrityError
transaction.atomic()
select_for_update()
```

según el mecanismo realmente existente.

---

# FASE 37 — TEST DE INTEGRIDAD FISCAL

Comprobar que después de la nueva implementación:

```text
CUFE
Número factura
XML
Factura
Venta
```

siguen coherentes.

Nunca modificar directamente:

```text
Factura
ItemFactura
FacturaAnexos
```

desde una edición de gestión manual de Ventas.

---

# FASE 38 — TEST CON FACTURA REAL DE REFERENCIA

Usar como caso funcional la factura adjunta `Factura_359_la_salle.pdf` como referencia de estructura y datos, cuando corresponda:

```text
Factura: FST 359
Cliente: FOCUS ELECTRONIC SECURITY SYSTEM S.A.S
NIT: 900.860.947-3
Fecha: 20/02/2026
Vencimiento: 22/03/2026
Forma de pago: Crédito
Medio de pago: Pago a crédito
Total: $961.520
IVA: $153.520
Subtotal: $808.000
CUFE: disponible
```

No codificar estos valores.

Deben utilizarse únicamente para comprobar que el sistema puede mostrar/procesar datos equivalentes provenientes del documento real.

---

# FASE 39 — SEGURIDAD MULTITENANT

Verificar exhaustivamente:

```text
Factura A tenant A
Venta B tenant B
```

no puede existir vínculo.

Todos los queries deben estar protegidos por:

```text
empresa_id
tenant schema
UUID
DSV
```

No aceptar solamente un UUID enviado desde frontend.

---

# FASE 40 — REGRESIÓN

Ejecutar:

```bash
python manage.py check
```

Después:

```bash
python manage.py test apps.tenant.ventas
```

Luego las suites relacionadas con:

```text
facturas
clientes
inventario
contabilidad
bancos
```

especialmente cualquier prueba que cubra:

```text
Venta → Factura
Factura → Contabilidad
Venta → Inventario
```

No declarar PASS si alguna falla relacionada queda sin explicación.

---

# FASE 41 — REGRESIÓN XML

Ejecutar pruebas específicas de:

```text
UBL
XML
CUFE
Factura
FacturaAnexos
importación
idempotencia
```

La funcionalidad nueva no debe modificar el parser XML salvo para exponer correctamente los datos que ya existen.

---

# FASE 42 — AUDITORÍA DE CÓDIGO MUERTO

Después de implementar:

buscar:

```text
imports
funciones
serializers
templates
JS
endpoints
```

que hayan quedado sin consumidores.

Eliminar únicamente código demostrado como muerto.

No eliminar código por intuición.

---

# FASE 43 — AUDITORÍA DE DUPLICACIÓN

Buscar duplicación entre:

```text
ventas
facturas
```

especialmente:

```text
estado de pago
forma de pago
medio de pago
fecha de vencimiento
fecha de pago
totales
```

Debe existir un SSoT claro para cada dato.

---

# FASE 44 — DOCUMENTACIÓN

Actualizar:

```text
ARQUITECTURA_VENTAS.md
```

Agregar:

```text
Contrato Venta ↔ Factura
Modelo de sincronización
Gestión manual
Estado documental vs estado de pago
Reglas de importación XML
Idempotencia
Permisos
Endpoints
Pruebas
```

Documentar explícitamente qué es:

```text
Factura SSoT
Venta SSoT
Dato sincronizado
Dato manual
Dato derivado
```

---

# FASE 45 — RELEASE GATE

No declarar terminado hasta cumplir:

```text
[ ] No existen facturas fiscales duplicadas
[ ] Venta.factura_asociada funciona
[ ] Vinculación por UUID
[ ] DSV correcto
[ ] OneToOne protegido
[ ] Vinculación idempotente
[ ] Buscador funcional
[ ] Nueva Venta funcional
[ ] Editar Venta funcional
[ ] Gestión Manual funcional
[ ] Estado de pago separado del estado documental
[ ] Fecha de pago funcional
[ ] Fecha límite de pago funcional
[ ] Forma de pago funcional
[ ] Código medio de pago funcional
[ ] XML no destruye gestión manual
[ ] XML no duplica Venta
[ ] XML no duplica Factura
[ ] Totales consistentes
[ ] CUFE consistente
[ ] Seguridad multitenant PASS
[ ] Tests PASS
[ ] Regresión PASS
[ ] Documentación actualizada
```

---

# FASE 46 — LOOP OBLIGATORIO

Después de cada fase:

```text
INSPECT
↓
ENCONTRAR
↓
DOCUMENTAR
↓
IMPLEMENTAR
↓
TEST
↓
AUDIT
↓
FIX
↓
RETEST
```

Si cualquier prueba falla:

```text
NO avanzar.
```

Investigar causa raíz.

No parchear síntomas.

Después de corregir:

```text
RETEST DEL CASO
↓
REGRESIÓN DEL MÓDULO
↓
REGRESIÓN CROSS-APP
```

---

# FASE 47 — REGLAS DE NO REGRESIÓN

Está prohibido:

- romper `Venta.factura_asociada`;
- eliminar `vincular_factura`;
- reactivar emisión fiscal automática no autorizada;
- crear otra entidad fiscal duplicada;
- modificar el parser XML sin necesidad;
- cambiar UUID por PK;
- introducir `parseInt()` sobre UUID;
- crear un nuevo sistema de frontend;
- introducir señales Django para esta lógica;
- mover lógica empresarial al JavaScript;
- escribir lógica de negocio directamente en templates;
- sobrescribir datos manuales con importación automática;
- permitir cross-tenant linking;
- cambiar los estados fiscales existentes solo para acomodar pagos.

---

# FASE 48 — CRITERIO FINAL DE DISEÑO

El flujo final debe quedar conceptualmente así:

```text
                         APP FACTURAS
                              │
                              │
                       Factura fiscal
                              │
                              ▼
                    Buscar / Vincular
                              │
                              ▼
                           VENTA
                              │
             ┌────────────────┴────────────────┐
             │                                 │
             ▼                                 ▼
      Datos fiscales                    Gestión manual
      provenientes de                   administrada en
      Factura                           Ventas
             │                                 │
             │                         Estado de Pago
             │                         Fecha de Pago
             │                         Fecha Límite
             │                         Forma de Pago
             │                         Código Medio Pago
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                       Seguimiento comercial
```

La regla final debe ser:

```text
FACTURA = verdad fiscal
VENTA = verdad comercial
GESTIÓN MANUAL = operación de cartera/pago
XML = fuente fiscal estructurada
```

y ninguna capa debe destruir la información que pertenece a otra.

---

# ENTREGA FINAL OBLIGATORIA DE LA IA EDITORA

Al terminar la misión entregar:

## 1. Resumen de cambios

Archivos modificados.

## 2. Migraciones

Migraciones creadas y propósito.

## 3. API

Endpoints nuevos/modificados.

## 4. Flujo funcional

Descripción:

```text
Nueva Venta
→ Buscar Factura
→ Vincular
→ Sincronizar
→ Editar Gestión Manual
```

## 5. Matriz de campos

```text
Campo | Origen | SSoT | Editable | Sincronización
```

## 6. Tests

Indicar:

```text
tests ejecutados
PASS
FAIL
SKIP
```

sin inventar resultados.

## 7. Regresión

Indicar exactamente qué suites se ejecutaron.

## 8. Riesgos residuales

Todo punto no resuelto debe quedar explícitamente documentado.

## 9. Estado final

Usar solamente:

```text
PASS
PASS_WITH_DEFERRED
BLOCKED
FAIL
```

Nunca declarar:

```text
PRODUCTION READY
```

si existen fallos funcionales no resueltos o pruebas críticas no ejecutadas.

# FIN DE LA MISIÓN
