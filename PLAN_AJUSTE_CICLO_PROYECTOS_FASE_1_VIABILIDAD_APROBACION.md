# PLAN DE ACCIÓN INICIAL
# REESTRUCTURACIÓN DEL CICLO FUNCIONAL DE PROYECTOS
## Fases 0. Borrador → 1. Inicio → 2. Planeación → 3. Ejecución → 4. Cierre

**Repositorio:** `steven-zdt/CRM_SINTEL`  
**Rama de referencia:** `main`  
**Módulo:** `apps/tenant/proyectos`  
**Documento base revisado:** `AUDITORIA_FLUJO_COMPLETO(8).md`  
**Auditoría base:** v3.12.0 / actualización 2026-10-05  
**Tipo de documento:** Plan inicial de arquitectura + implementación incremental  
**Estado:** PROPUESTA INICIAL — requiere cerrar decisiones funcionales señaladas como `[DECISIÓN]` antes de convertirlas en implementación definitiva.

---

# 1. PROPÓSITO

Reestructurar el ciclo funcional del módulo Proyectos para que las cinco fases representen un proceso real de negocio:

```text
0. BORRADOR
      ↓
1. INICIO
   Comercial + contractual + supervisor + contratista/proveedor
   + facturas de venta
   + cotizaciones de costos
   + inversiones reales
   + análisis de viabilidad
      ↓
   ENVIAR A APROBACIÓN
      ↓
   ADMINISTRADOR APRUEBA
      ↓
2. PLANEACIÓN
   Diseño + recursos + presupuesto + cronograma
      ↓
3. EJECUCIÓN
   Tiempos + tareas + cronograma + gastos no facturables
      ↓
4. CIERRE
   Resultados + documentos + cierre administrativo
```

La modificación principal es que **Fase 1 deja de ser solamente una etapa informativa y se convierte en el filtro económico/comercial que autoriza la entrada a Planeación**.

La aprobación administrativa no debe ser un simple campo visual ni un botón que cambie colores. Debe constituir una **regla de negocio persistida y auditada** que el backend utilice para decidir si Fase 2 puede desbloquearse.

---

# 2. VALIDACIÓN DEL DOCUMENTO ADJUNTO

## 2.1 Resultado de la revisión

La auditoría adjunta está correctamente estructurada como auditoría histórica/técnica de v3.12.0 y documenta:

- Proyecto como entidad maestra.
- máquina de estados de las fases;
- integración Compras → Proyectos;
- integración Cotización → Planeación;
- Tareas Diarias;
- Control de Tiempo;
- Gastos No Facturables;
- DSV;
- bloqueo de Cierre;
- service layer;
- UUID;
- pruebas existentes.

La propia auditoría registra que v3.12.0 implementó la Fase 3 con Control de Tiempo, Gastos No Facturables y Tareas. También establece que los gastos se leen desde Gastos mediante Pull Model. Esto debe conservarse. 

## 2.2 La auditoría ya no debe considerarse la definición funcional final

La sección de Integración de Cotización documenta actualmente una Cotización asociada a Planeación y una única relación histórica con Factura. La nueva solicitud cambia el concepto: la Fase 1 debe administrar **varias Facturas de Venta**, además de **cotizaciones de costo** e **inversiones reales**. 

Por tanto:

```text
AUDITORIA v3.12.0
        ↓
BASE TÉCNICA
        ↓
NUEVA DEFINICIÓN FUNCIONAL
        ↓
PLAN vNext DEL CICLO DE PROYECTOS
```

No se recomienda parchear la lógica anterior sin redefinir primero el dominio.

---

# 3. DECISIÓN ARQUITECTÓNICA CENTRAL

## 3.1 Fase 0 permanece prácticamente intacta

El usuario indica expresamente que:

> 0. Borrador está OK.

Por tanto no se debe introducir una reingeniería innecesaria en Fase 0.

Fase 0 seguirá siendo:

- creación inicial;
- oportunidad;
- datos básicos;
- cliente;
- descripción;
- identificación;
- documentos iniciales;
- relaciones operativas que ya existen.

Solamente debe modificarse el comportamiento de transición para que el ingreso a Fase 1 no permita saltarse las nuevas reglas posteriores.

---

# 4. NUEVA DEFINICIÓN DE FASE 1

## 4.1 Nuevo nombre funcional recomendado

Cambiar visualmente:

```text
1. Inicio (Comercial y Legal)
```

por:

```text
1. Inicio (Comercial, Contractual y Viabilidad)
```

o:

```text
1. Inicio (Validación Comercial y Viabilidad)
```

`[DECISIÓN]` Elegir el nombre definitivo antes del ajuste visual.

---

# 5. OBJETIVO DE FASE 1

Fase 1 debe responder cuatro preguntas:

### Pregunta A
¿Quién será responsable de supervisar internamente el proyecto?

### Pregunta B
¿Quién ejecutará o suministrará el proyecto?

### Pregunta C
¿Por cuánto se vendió realmente el proyecto?

El sistema debe obtener este valor de las **Facturas de Venta vinculadas**, no de un valor digitado manualmente.

### Pregunta D
¿Cuánto cuesta realmente ejecutar o invertir en el proyecto?

La respuesta debe construirse con:

- cotizaciones de costos;
- inversiones reales;
- categorías:
  - Mano de Obra
  - Materiales
  - Equipos.

Con estos datos el sistema puede presentar una evaluación de viabilidad antes de permitir Planeación.

---

# 6. SUPERVISOR DEL PROYECTO

Actualmente Proyecto dispone de responsables por fase, incluyendo responsables comerciales, técnicos, operativos y administrativos.

La nueva necesidad introduce explícitamente:

```text
Supervisor del Proyecto
```

## 6.1 Propuesta inicial

Agregar un concepto propio:

```text
supervisor_id
supervisor_nombre
```

mediante snapshot, siguiendo el patrón ya usado por Proyecto.

El selector debería consultar solamente empleados pertenecientes al mismo `empresa_id` y respetar `OrganizationalScope`.

## 6.2 No mezclar Supervisor con Responsable Operativo

No se recomienda reutilizar silenciosamente:

```text
responsable_operativo_id
```

porque conceptualmente:

```text
Supervisor
≠
Responsable Operativo
≠
Responsable Técnico
```

Cada uno representa una función diferente.

## 6.3 `[DECISIÓN]` origen del Supervisor

Confirmar:

```text
¿Supervisor proviene de apps.tenant.empleados
y debe seleccionarse desde empleados activos?
```

La propuesta inicial es **sí**, pero no se debe codificar hasta confirmar esta decisión.

---

# 7. CONTRATISTA / PROVEEDOR

Proyecto ya posee:

```text
proveedor_id
proveedor_nombre
```

y la auditoría registra este patrón de snapshot.

## 7.1 Propuesta

Reutilizar estos campos para:

```text
Contratista / Proveedor Principal
```

sin crear inmediatamente otra FK redundante.

UI:

```text
Contratista / Proveedor Principal
[ Buscar proveedor... ]
```

## 7.2 Regla

La selección debe:

- pertenecer al mismo `empresa_id`;
- respetar OrganizationalScope cuando corresponda;
- conservar snapshot del nombre;
- no permitir IDOR;
- no depender de datos de otro tenant.

## 7.3 `[DECISIÓN]`

Confirmar si el proyecto puede tener:

```text
1 contratista/proveedor principal
```

o:

```text
varios contratistas/proveedores
```

La solicitud actual parece indicar uno principal. El plan inicial usa **uno principal** y no amplía el dominio hasta recibir esa decisión.

---

# 8. FACTURAS DE VENTA DEL PROYECTO

## 8.1 Problema actual

El Proyecto tiene actualmente un campo:

```text
factura_costo
```

que conceptualmente funciona como una única factura/centro de costos.

Eso no debe utilizarse para resolver el nuevo requisito.

El nuevo requisito dice:

> se podrán vincular varias facturas al proyecto solo con el fin de saber su valor real con el cual se vendió

Por tanto, se necesita una relación:

```text
Proyecto 1 ─── N Facturas de Venta
```

---

# 9. NO REPURPOSEAR `factura_costo`

No convertir:

```text
factura_costo
```

en:

```text
facturas_venta
```

porque son conceptos diferentes.

`factura_costo` debe mantenerse por compatibilidad histórica mientras se define su eventual retiro.

La nueva relación debe ser explícita.

---

# 10. MODELO PROPUESTO PARA FACTURAS DE VENTA

Crear en Proyectos un modelo puente, por ejemplo:

```python
class ProyectoFacturaVenta(SintelTenantBaseModel):
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="facturas_venta_proyecto",
    )

    factura_uuid = models.UUIDField(
        db_index=True,
    )

    factura_numero = models.CharField(
        max_length=200,
        blank=True,
    )

    fecha_vinculacion = models.DateTimeField(
        auto_now_add=True,
    )
```

El nombre definitivo puede adaptarse a las convenciones reales del proyecto.

## 10.1 Razón del UUID

Factura ya posee UUID.

Por tanto:

```text
Proyecto
   ↓
ProyectoFacturaVenta
   ↓
factura_uuid
   ↓
Facturas
```

Permite mantener Proyectos como consumidor de datos y evita convertir la nueva funcionalidad en otra dependencia ORM innecesaria.

## 10.2 Constraint

Debe existir:

```text
UNIQUE(proyecto, factura_uuid)
```

Así una misma factura no puede ser vinculada dos veces al mismo proyecto.

---

# 11. QUÉ FACTURAS SE PUEDEN VINCULAR

Solo deben aceptarse documentos que realmente sean ventas del tenant.

La Factura actual posee:

```text
naturaleza = VENTA / COMPRA
estado = BORRADOR / ENVIADA / ACEPTADA / RECHAZADA / ERROR_TRANSMISION / ANULADA
tipo = FE / NC / ND
```

## 11.1 Regla inicial propuesta

Para el valor vendido debe utilizarse una factura de venta válida según las reglas del dominio Facturas.

NO duplicar las reglas fiscales dentro de Proyectos.

Debe crearse un selector que consuma Facturas respetando su SSoT.

## 11.2 `[DECISIÓN CRÍTICA]`

Definir qué estados pueden vincularse:

```text
¿Solo ACEPTADA?
¿ENVIADA + ACEPTADA?
¿También BORRADOR?
```

Recomendación inicial:

```text
solo Factura de Venta ACEPTADA
```

porque representa una venta fiscalmente aceptada y evita utilizar documentos todavía provisionales.

Esta recomendación debe confirmarse antes de implementación.

---

# 12. NOTAS DE CRÉDITO Y NOTAS DÉBITO

No debe asumirse que todas las Facturas de Venta tienen efecto positivo.

Existe:

```text
FE
NC
ND
```

Por tanto el servicio que calcula el valor vendido debe definir explícitamente:

```text
FE  → suma
ND  → suma
NC  → resta
```

o aplicar la regla que ya tenga Facturas como SSoT.

## `[DECISIÓN]`

Confirmar si el valor real vendido debe ser:

```text
Facturas FE
+ ND
- NC
```

Esta decisión es importante para que el valor comercial histórico no quede inflado.

---

# 13. VALOR REAL DE VENTA DEL PROYECTO

El nuevo concepto debe ser:

```text
VALOR REAL VENDIDO
```

y no:

```text
Valor Contrato Proyectado
```

La fuente SSoT será:

```text
SUM(importe de las facturas de venta vinculadas)
```

No se debe permitir:

```text
usuario escribe $100.000.000
```

y luego:

```text
facturas dicen $87.000.000
```

mientras ambos valores son tratados como fuente de verdad.

---

# 14. `valor_contrato_proyectado`

No eliminar inmediatamente este campo.

Actualmente otros componentes lo consumen y la auditoría documenta cálculos financieros sobre él.

La estrategia recomendada es:

```text
valor_contrato_proyectado
        ↓
LEGACY / COMPATIBILIDAD

valor_real_vendido
        ↓
DERIVADO DE FACTURAS
        ↓
NUEVA SSoT COMERCIAL
```

No duplicar el valor real en BD salvo que exista un requisito de snapshot/aprobación.

Los servicios y serializers deberán poder presentar el valor derivado.

---

# 15. COTIZACIONES DE COSTOS DE FASE 1

Este concepto NO debe confundirse con:

```text
Cotizacion
```

de la app `cotizaciones`, que representa la oferta comercial al cliente.

Aquí se necesita:

```text
Cotización de Costo del Proyecto
```

para analizar cuánto cuesta ejecutarlo.

Son dos conceptos distintos:

```text
Cotización Comercial
        ↓
cliente
        ↓
venta

Cotización de Costo
        ↓
proveedor / contratista
        ↓
inversión necesaria
```

---

# 16. MODELO PROPUESTO: COTIZACIONES DE COSTO

Crear una entidad similar a:

```python
class CotizacionCostoProyecto(SintelTenantBaseModel):
```

Campos mínimos propuestos:

```text
uuid
empresa
proyecto
categoria
descripcion
proveedor_id
proveedor_nombre
fecha
numero_documento
valor
moneda
archivo_pdf
observaciones
activo
created_at
updated_at
```

## 16.1 Categorías

```text
MANO_OBRA
MATERIALES
EQUIPOS
```

Estas son las categorías oficiales para Fase 1.

No crear categorías duplicadas en JS.

---

# 17. VARIAS COTIZACIONES POR CATEGORÍA

Debe permitirse:

```text
Proyecto
 ├── Mano de Obra
 │    ├── Cotización 1
 │    └── Cotización 2
 │
 ├── Materiales
 │    ├── Cotización 1
 │    └── Cotización 2
 │
 └── Equipos
      ├── Cotización 1
      └── Cotización 2
```

El sistema no debe obligar inicialmente a una única cotización.

Esto permite comparar diferentes proveedores.

---

# 18. PDF DE CADA COTIZACIÓN

Cada registro de `CotizacionCostoProyecto` podrá tener un PDF propio.

Ejemplo:

```text
Cotización proveedor A
$ 12.500.000
MANO DE OBRA
[ Ver PDF ]

Cotización proveedor B
$ 13.200.000
MANO DE OBRA
[ Ver PDF ]
```

## Reglas

- solo PDF;
- validación de extensión;
- tamaño máximo definido;
- almacenamiento mediante FileField;
- link de consulta/descarga;
- ningún procesamiento OCR obligatorio en esta primera versión.

La carga del PDF es evidencia documental, no una fuente automática de valores.

---

# 19. NO EXTRAER AUTOMÁTICAMENTE EL VALOR DEL PDF EN ESTA FASE

El primer alcance debe ser:

```text
usuario registra valor
usuario carga PDF
```

No:

```text
PDF → OCR → IA → valor automático
```

Esto puede convertirse en una futura funcionalidad de IA, pero no debe mezclarse con el primer ciclo.

---

# 20. INVERSIONES REALES DEL PROYECTO

El usuario solicita poder registrar valores reales de inversión en Fase 1.

Esto es diferente a una cotización.

## Diferencia

```text
Cotización de costo
= cuánto se espera pagar según propuesta

Inversión real
= cuánto realmente se ha invertido/comprometido
```

No deben guardarse en la misma entidad.

---

# 21. MODELO PROPUESTO: INVERSION DEL PROYECTO

Crear:

```python
class InversionProyectoInicio(SintelTenantBaseModel):
```

Campos iniciales:

```text
uuid
empresa
proyecto
categoria
descripcion
fecha
valor
proveedor_id
proveedor_nombre
documento_referencia
observaciones
activo
created_at
updated_at
```

Categorías:

```text
MANO_OBRA
MATERIALES
EQUIPOS
```

---

# 22. NO CREAR CAMPOS FIJOS

No hacer:

```text
valor_mano_obra
valor_materiales
valor_equipos
```

como única solución.

Eso limita el dominio y obliga a modificar el modelo cuando aparezcan nuevas líneas.

La estructura debe ser:

```text
Proyecto
   ↓
1:N inversiones
```

y:

```text
SUM(inversiones por categoria)
```

---

# 23. RESUMEN ECONÓMICO DE FASE 1

La UI debe mostrar un bloque central:

```text
ANÁLISIS ECONÓMICO DEL PROYECTO
```

con:

```text
VALOR REAL VENDIDO
$ XXX.XXX.XXX

COTIZACIONES DE COSTO
Mano de Obra     $ XX.XXX.XXX
Materiales       $ XX.XXX.XXX
Equipos          $ XX.XXX.XXX
Total            $ XX.XXX.XXX

INVERSIÓN REAL
Mano de Obra     $ XX.XXX.XXX
Materiales       $ XX.XXX.XXX
Equipos          $ XX.XXX.XXX
Total            $ XX.XXX.XXX
```

---

# 24. CRUCE DE VIABILIDAD

El sistema debe permitir comparar:

```text
VALOR VENDIDO
      ↓
COSTO COTIZADO
      ↓
INVERSIÓN REAL
```

Ejemplo conceptual:

```text
Valor vendido                    $100.000.000
Costo cotizado                    $70.000.000
Inversión real acumulada          $35.000.000
```

Indicadores posibles:

```text
Viabilidad según cotizaciones
= Valor vendido - Costo cotizado

Margen estimado
= Viabilidad / Valor vendido × 100

Resultado actual
= Valor vendido - Inversión real

Margen actual
= Resultado actual / Valor vendido × 100
```

Estas fórmulas son la **propuesta inicial**.

---

# 25. `[DECISIÓN CRÍTICA] IVA EN EL CRUCE

No debe asumirse que:

```text
Factura.total
```

es comparable directamente con:

```text
CotizaciónCosto.valor
```

si las cotizaciones fueron registradas antes de IVA.

La UI podría mostrar:

```text
Valor facturado total
Valor facturado antes de IVA
```

y utilizar una base comparable para los cálculos.

## Recomendación inicial

Mostrar ambos:

```text
VENTA FACTURADA TOTAL
VENTA BASE SIN IMPUESTOS
```

y definir cuál será la base oficial de viabilidad.

Esta decisión debe cerrarse antes de implementar el cálculo financiero definitivo.

---

# 26. ESTADO DE APROBACIÓN DE FASE 1

No usar:

```text
estado_tarea
```

para aprobación.

No usar:

```text
fase_actual
```

como sustituto de aprobación.

Son conceptos distintos.

Debe existir un estado de aprobación dedicado.

---

# 27. MODELO PROPUESTO DE APROBACIÓN

Se recomienda una entidad de auditoría:

```python
class AprobacionInicioProyecto(SintelTenantBaseModel):
```

con datos similares a:

```text
uuid
empresa
proyecto
estado
enviado_at
enviado_por
revisado_at
revisado_por
comentario
version
```

Estados propuestos:

```text
PENDIENTE
EN_REVISION
APROBADO
RECHAZADO
```

Opcionalmente:

```text
REQUIERE_CAMBIOS
```

`[DECISIÓN]` definir nombre final de estados.

---

# 28. POR QUÉ NO SOLO AGREGAR `aprobado=True`

Un booleano:

```text
aprobado = True
```

no permite saber:

- quién aprobó;
- cuándo;
- qué versión estaba revisando;
- por qué fue rechazada;
- qué ocurrió antes;
- si después se modificaron los valores.

La aprobación tiene impacto sobre el ciclo del proyecto y por eso debe quedar auditada.

---

# 29. SNAPSHOT DE LA APROBACIÓN

Cuando el administrador apruebe:

```text
guardar versión aprobada
```

debería existir trazabilidad del conjunto económico utilizado.

Como mínimo se deben conservar:

```text
valor vendido evaluado
total cotizaciones evaluadas
total inversión evaluada
fecha
usuario administrador
versión
```

Esto evita que una aprobación histórica pierda significado si posteriormente cambian registros.

No implica necesariamente duplicar todas las líneas; se puede resolver con una estructura de snapshot adecuada.

---

# 30. FLUJO NUEVO DE APROBACIÓN

```text
Fase 1 abierta
     ↓
Usuario completa datos
     ↓
Factura(s) de venta
Cotización(es) de costo
Inversión(es)
Supervisor
Contratista/proveedor
     ↓
Sistema calcula resumen
     ↓
Usuario:
[ Enviar a aprobación ]
     ↓
Estado = EN_REVISION
     ↓
Admin:
[ Aprobar ]
   o
[ Rechazar ]
```

---

# 31. APROBACIÓN RECHAZADA

Si el administrador rechaza:

```text
Fase actual = INICIO
Planeación = BLOQUEADA
```

Debe mostrarse:

```text
RECHAZADO
Motivo:
...
```

El usuario podrá corregir información y volver a enviar.

---

# 32. `[DECISIÓN] QUÉ OCURRE AL MODIFICAR DATOS DESPUÉS DE APROBADO

Esta es una regla crítica.

Se recomienda inicialmente:

```text
APROBADO
   ↓
si cambian datos económicos críticos
   ↓
requiere nueva aprobación
```

Datos críticos:

- facturas vinculadas;
- facturas desvinculadas;
- cotizaciones de costo;
- inversiones reales;
- supervisor;
- contratista/proveedor si afecta la aprobación.

Esto impide que:

```text
Admin aprueba $70M de costos
↓
usuario cambia a $110M
↓
Planeación permanece aprobada
```

---

# 33. RECOMENDACIÓN SOBRE EDICIÓN DESPUÉS DE APROBACIÓN

Propuesta:

```text
APROBADO
   ↓
datos económicos bloqueados
   ↓
[Solicitar cambios]
   ↓
REQUIERE_REAPROBACION
```

Otra posibilidad es permitir edición y automáticamente invalidar aprobación.

`[DECISIÓN]` elegir una estrategia.

Recomendación:

```text
invalidar aprobación y exigir nueva aprobación
```

porque es más sencillo y seguro.

---

# 34. REGLA DE DESBLOQUEO DE FASE 2

Este es el cambio principal del ciclo.

Actualmente:

```text
POST /avanzar-fase/
```

permite avanzar según la máquina de fases.

La nueva regla será:

```text
INICIO → PLANEACION
```

solo si:

```text
AprobacionInicio.estado == APROBADO
```

---

# 35. NO PERMITIR BYPASS DESDE EL FRONTEND

Ocultar:

```text
botón Planeación
```

no es suficiente.

Un usuario podría llamar:

```http
POST /api/v1/proyectos/{uuid}/avanzar-fase/
```

directamente.

Por eso:

```text
Frontend
    ↓
Service Layer
    ↓
regla can_enter_planeacion()
```

La validación debe existir en backend.

---

# 36. SERVICIO SSoT RECOMENDADO

Crear un servicio especializado, por ejemplo:

```text
ProyectoInicioBusinessService
```

o dividir por responsabilidades:

```text
ProyectoInicioService
ProyectoAprobacionService
ProyectoFacturasVentaService
ProyectoCostosService
ProyectoInversionService
```

La elección final debe seguir el patrón actual del repositorio.

Evitar un servicio monolítico gigantesco.

---

# 37. RESPONSABILIDADES DEL SERVICIO

Debe centralizar:

```text
validar_supervisor()
validar_proveedor()
vincular_factura_venta()
desvincular_factura_venta()
crear_cotizacion_costo()
crear_inversion()
calcular_resumen_inicio()
calcular_viabilidad()
enviar_aprobacion()
aprobar_inicio()
rechazar_inicio()
validar_desbloqueo_planeacion()
```

No distribuir estas reglas entre:

```text
ViewSet
JS
Template
Signal
Serializer
```

---

# 38. SELECTORS

Crear selectors especializados para consultas:

```text
ProyectoInicioSelector
ProyectoFacturaVentaSelector
ProyectoCotizacionCostoSelector
ProyectoInversionSelector
ProyectoAprobacionSelector
```

o integrarlos en selectors existentes según el estándar actual.

Responsabilidades:

```text
read only
Zero Waste
select_related
prefetch_related
empresa_id
OrganizationalScope
```

---

# 39. FRONTEND DE FASE 1

La estructura recomendada del formulario:

```text
┌──────────────────────────────────────────────┐
│ 1. INICIO                                   │
│ Comercial · Contractual · Viabilidad       │
└──────────────────────────────────────────────┘

RESPONSABLE COMERCIAL
[........................]

SUPERVISOR DEL PROYECTO
[........................]

CONTRATISTA / PROVEEDOR
[........................]

FACTURAS DE VENTA
[ Buscar factura ]
[ FA-001 ] [ $... ] [ quitar ]
[ FA-002 ] [ $... ] [ quitar ]

Valor vendido
$ XXX.XXX.XXX

COTIZACIONES DE COSTO
------------------------------------------------
Categoría | Proveedor | Valor | PDF | Acciones
MO
Material
Equipo

[ Nueva cotización de costo ]

INVERSION REAL
------------------------------------------------
Categoría | Descripción | Valor | Fecha | Acciones

[ Nueva inversión ]

ANÁLISIS DE VIABILIDAD
------------------------------------------------
Valor vendido
Costos cotizados
Inversión real
Resultado
Margen

ESTADO DE APROBACIÓN
[ Borrador / En revisión / Aprobado / Rechazado ]

[ ENVIAR A APROBACIÓN ]
```

---

# 40. FACTURAS: UX

No usar un `<select>` enorme con todas las facturas.

Debe utilizarse:

```text
buscador server-side
```

Ejemplo:

```text
[ Buscar por número, cliente... ]
```

Resultado:

```text
FA-2026-001
Cliente XYZ
Aceptada
$40.000.000

[Agregar]
```

---

# 41. FACTURAS YA VINCULADAS

Mostrar inmediatamente:

```text
FACTURAS DE VENTA DEL PROYECTO

Factura     Estado       Cliente       Total       Acción
---------------------------------------------------------
FE-001      Aceptada     Cliente A     $50M        Quitar
FE-002      Aceptada     Cliente A     $25M        Quitar
```

Resumen:

```text
2 facturas
Valor vendido: $75.000.000
```

---

# 42. NO CREAR FACTURAS DESDE PROYECTOS

La Fase 1 solamente:

```text
vincula
consulta
resume
```

No debe crear Facturas.

Factura sigue siendo SSoT de Facturas.

---

# 43. COTIZACIONES DE COSTO: UX

Diseñar un bloque independiente:

```text
Cotizaciones de Costos
```

con filtros por categoría:

```text
[ Todas ] [ Mano de Obra ] [ Materiales ] [ Equipos ]
```

Acción:

```text
[ + Nueva Cotización ]
```

Formulario:

```text
Categoría *
Proveedor
Descripción *
Fecha
Valor *
PDF *
Observaciones
```

---

# 44. INVERSIONES: UX

Bloque:

```text
Inversión Real del Proyecto
```

Formulario:

```text
Categoría *
Descripción *
Fecha *
Valor *
Proveedor
Documento / referencia
Observaciones
```

Sin relación manual con Fase 3.

La inversión registrada en Fase 1 representa análisis inicial/económico.

Los gastos operativos de Fase 3 siguen siendo consumidos desde Gastos.

---

# 45. DIFERENCIA ENTRE INVERSIÓN Y GASTO NO FACTURABLE

No mezclarlos.

```text
FASE 1
Inversión inicial
→ análisis de viabilidad / aprobación

FASE 3
Gasto no facturable
→ costo operativo real durante ejecución
```

Más adelante podrán compararse, pero no deben escribir sobre la misma tabla.

---

# 46. IMPACTO SOBRE FASE 2

La nueva lógica afecta directamente Fase 2.

Actualmente Fase 2 tiene:

```text
Cotización cliente
Recursos
Presupuesto
```

La futura relación será:

```text
Fase 1
   ↓
valor real vendido
cotizaciones de costo
inversión inicial
viabilidad
aprobación
   ↓
Fase 2 desbloqueada
   ↓
Cotización comercial aprobada
   ↓
Planeación técnica
```

La Cotización Comercial y las Cotizaciones de Costos permanecen separadas.

---

# 47. NO ELIMINAR LA COTIZACIÓN COMERCIAL DE FASE 2

La nueva Cotización de Costos no reemplaza:

```text
Cotizacion
```

de la app de cotizaciones.

Son funciones diferentes.

```text
Cotizacion comercial
= cuánto se le vendió al cliente / oferta comercial

Cotizacion de costo
= cuánto podría costar ejecutar / contratar
```

---

# 48. IMPACTO SOBRE FASE 3

La Fase 3 v3.12.0 ya tiene implementados:

- Control de Tiempo;
- Tareas Diarias;
- detección de tareas atrasadas;
- Gastos No Facturables.

Eso debe conservarse.

Sin embargo, después de modificar el gate de Planeación se debe repetir una revisión de integración porque:

```text
Fase 1
   ↓
Aprobación
   ↓
Fase 2
   ↓
Fase 3
```

ahora tendrá una dependencia funcional nueva.

La Fase 3 no debe volver a introducir:

```text
Valor del Contrato
```

como bloque operativo.

---

# 49. IMPACTO SOBRE FASE 4

Fase 4 seguirá siendo:

```text
Cierre administrativo
```

y podrá aprovechar datos derivados del ciclo:

```text
valor vendido
inversión
costos
avance
tareas
gastos
```

Pero no debe ser modificada en esta primera misión salvo para evitar inconsistencias con los nuevos datos.

---

# 50. MÁQUINA DE ESTADOS PROPUESTA

La máquina de fases mantiene:

```text
BORRADOR
INICIO
PLANEACION
EJECUCION
CIERRE
```

pero las transiciones deberán tener precondiciones.

## Transición

```text
BORRADOR → INICIO
```

Precondiciones existentes.

## Transición

```text
INICIO → PLANEACION
```

Nueva precondición:

```text
aprobacion_inicio == APROBADO
```

## Transición

```text
PLANEACION → EJECUCION
```

Mantener reglas existentes.

## Transición

```text
EJECUCION → CIERRE
```

Mantener reglas existentes.

---

# 51. DESBLOQUEO VISUAL

El frontend debe poder mostrar:

```text
2. Planeación 🔒
```

y:

```text
Planeación bloqueada.
Pendiente de aprobación administrativa.
```

Cuando el admin apruebe:

```text
2. Planeación ✅ DISPONIBLE
```

La aprobación debe venir desde backend.

---

# 52. BOTONES

En Fase 1:

```text
[Guardar cambios]
[Enviar a aprobación]
```

Para administrador:

```text
[ Aprobar Inicio ]
[ Rechazar ]
```

Después de aprobar:

```text
[ Avanzar a Planeación ]
```

o el comportamiento que se decida para el avance automático.

---

# 53. `[DECISIÓN] APROBACIÓN VS AVANCE AUTOMÁTICO

Recomendación inicial:

```text
Admin aprueba
      ↓
Planeación se DESBLOQUEA
      ↓
usuario pulsa "Avanzar a Planeación"
```

No mover automáticamente `fase_actual`.

Esto conserva la semántica actual de las fases:

```text
Aprobación = autorización
Avance = transición operativa
```

Si el negocio prefiere que aprobar implique automáticamente:

```text
INICIO → PLANEACION
```

esa regla debe definirse explícitamente.

---

# 54. CAMBIOS EN `ProyectoViewSet`

No crear lógica económica dentro del ViewSet.

Agregar acciones explícitas de dominio:

```http
GET    /api/v1/proyectos/{uuid}/inicio/
GET    /api/v1/proyectos/{uuid}/facturas-venta/
POST   /api/v1/proyectos/{uuid}/facturas-venta/vincular/
DELETE /api/v1/proyectos/{uuid}/facturas-venta/{factura_uuid}/

GET    /api/v1/proyectos/{uuid}/cotizaciones-costos/
POST   /api/v1/proyectos/{uuid}/cotizaciones-costos/
PATCH  /api/v1/proyectos/{uuid}/cotizaciones-costos/{uuid}/
DELETE /api/v1/proyectos/{uuid}/cotizaciones-costos/{uuid}/

GET    /api/v1/proyectos/{uuid}/inversiones/
POST   /api/v1/proyectos/{uuid}/inversiones/
PATCH  /api/v1/proyectos/{uuid}/inversiones/{uuid}/
DELETE /api/v1/proyectos/{uuid}/inversiones/{uuid}/

GET    /api/v1/proyectos/{uuid}/viabilidad/
POST   /api/v1/proyectos/{uuid}/enviar-aprobacion/
POST   /api/v1/proyectos/{uuid}/aprobar-inicio/
POST   /api/v1/proyectos/{uuid}/rechazar-inicio/
```

Los nombres definitivos pueden ajustarse al router existente.

---

# 55. NO USAR PATCH GENÉRICO PARA APROBACIÓN

No:

```http
PATCH /proyectos/{uuid}
{
    "aprobado": true
}
```

Sí:

```http
POST /proyectos/{uuid}/aprobar-inicio/
```

La aprobación es una acción de dominio.

---

# 56. PERMISOS

El endpoint:

```text
aprobar-inicio
```

debe exigir:

```text
rol ADMIN
```

y:

```text
empresa_id actual
```

además de:

```text
OrganizationalScope
```

cuando aplique.

Un usuario comercial u operativo no puede aprobar.

---

# 57. DSV

Toda referencia debe validar:

```text
empresa_id
```

Ejemplos:

```text
Supervisor
Proveedor
Factura
Cotización
Inversión
Aprobador
```

Nunca aceptar un UUID válido de otro tenant.

---

# 58. SCOPE ORGANIZACIONAL

Si Proyecto está asociado a una Sede, los selectores de:

```text
Proyecto
Factura
Proveedor
Empleado
```

deben respetar el alcance organizacional vigente.

No basta con:

```python
filter(empresa_id=empresa.id)
```

cuando la arquitectura ya exige `OrganizationalScope`.

---

# 59. AUDITORÍA

Las acciones:

```text
vincular factura
desvincular factura
crear costo
modificar costo
crear inversión
modificar inversión
enviar aprobación
aprobar
rechazar
invalidar aprobación
```

deben poder rastrearse.

No depender de logs de frontend.

---

# 60. MIGRACIÓN HISTÓRICA

Debe existir un plan específico para:

```text
factura_costo
factura_costo_numero
```

y los vínculos históricos:

```text
Proyecto
 ↓
Factura
 ↓
Cotizacion
```

No migrar silenciosamente.

---

# 61. BACKFILL PROPUESTO PARA FACTURAS

La migración debe:

1. Identificar proyectos con `factura_costo`.
2. Validar que sea una factura de venta válida.
3. Crear el vínculo en `ProyectoFacturaVenta`.
4. Mantener el campo legacy.
5. Reportar proyectos no migrables.
6. No alterar facturas.

Comando recomendado:

```bash
python manage.py backfill_proyecto_facturas_venta
```

con:

```bash
--dry-run
```

---

# 62. MIGRACIÓN DE DATOS HISTÓRICOS DE APROBACIÓN

No inventar aprobaciones para proyectos históricos.

Un proyecto antiguo no debe convertirse artificialmente en:

```text
APROBADO
```

porque no existe evidencia de esa aprobación.

Los proyectos históricos podrán quedar como:

```text
LEGACY / SIN_APROBACION_HISTORICA
```

según la estrategia que se determine.

---

# 63. COMPATIBILIDAD CON PROYECTOS EXISTENTES

No romper:

- clientes;
- proveedores;
- facturas históricas;
- cotizaciones existentes;
- pedidos;
- presupuesto;
- tareas;
- gastos;
- cierre.

Las nuevas relaciones deben ser aditivas inicialmente.

---

# 64. NO TOCAR EN ESTA MISIÓN

No modificar como parte del primer ciclo:

```text
Contabilidad
Inventario
Kardex
Nómina
Facturación fiscal
Ventas
Compras
Gastos operativos de Fase 3
```

salvo los bridges mínimos necesarios para lectura/validación.

---

# 65. RELACIÓN CON COMPRAS

Compras ya tiene integración con Proyecto.

Debe mantenerse:

```text
OrdenCompra.proyecto
```

sin inventar otra relación paralela.

La Fase 1 puede mostrar información de compras posteriormente, pero no debe convertirse en una segunda app de Compras.

---

# 66. RELACIÓN CON GASTOS

Gastos sigue siendo SSoT del gasto.

Fase 1:

```text
InversionProyectoInicio
```

Fase 3:

```text
Gasto / DocumentoSoporte
```

No utilizar la tabla de Gastos para representar inversiones preliminares, salvo que negocio decida posteriormente que conceptualmente son el mismo fenómeno.

---

# 67. FRONTEND: NO CALCULAR VIABILIDAD EN JS

El frontend solo debe recibir:

```json
{
  "valor_vendido": "...",
  "cotizaciones_costo": "...",
  "inversion_real": "...",
  "resultado": "...",
  "margen": "...",
  "estado_aprobacion": "..."
}
```

El navegador no debe decidir:

```text
valor_vendido - costo
```

como regla de negocio.

Debe pintar lo que devuelve el backend.

---

# 68. SERVICIO DE RESUMEN

Crear una respuesta SSoT:

```text
ProyectoInicioSummary
```

que entregue:

```text
supervisor
proveedor
facturas
valor vendido
cotizaciones agrupadas
inversiones agrupadas
totales
viabilidad
aprobación
puede_avanzar_planeacion
```

Esto evita múltiples GET dispersos al abrir el offcanvas.

---

# 69. ZERO-WASTE / PERFORMANCE

La apertura de Fase 1 debe evitar:

```text
GET factura x factura
GET proveedor x proveedor
GET cotizacion x cotizacion
```

Debe utilizar:

```text
select_related
prefetch_related
aggregate
annotate
only
```

cuando sea aplicable.

Las facturas disponibles deben buscarse bajo demanda con server-side search.

---

# 70. ARCHIVOS PRINCIPALES A REVISAR

## Proyectos

```text
apps/tenant/proyectos/models.py
apps/tenant/proyectos/api/serializers.py
apps/tenant/proyectos/api/viewsets.py
apps/tenant/proyectos/services/business_service.py
apps/tenant/proyectos/services/crud_service.py
apps/tenant/proyectos/services/selectors.py
apps/tenant/proyectos/static/proyectos/js/proyectos.api.js
apps/tenant/proyectos/static/proyectos/js/features/proyectos_editor.js
apps/tenant/proyectos/templates/tenant/proyectos/offcanvas_form.html
apps/tenant/proyectos/tests/*
```

## Facturas

```text
apps/tenant/facturas/models.py
apps/tenant/facturas/services/business_service.py
apps/tenant/facturas/services/selectors.py
apps/tenant/facturas/api/*
```

## Proveedores

```text
apps/tenant/proveedores/*
```

## Empleados

```text
apps/tenant/empleados/*
```

---

# 71. FASES DE IMPLEMENTACIÓN

## FASE 0 — Línea Base

Antes de modificar:

- confirmar hash/branch;
- ejecutar `manage.py check`;
- revisar migraciones;
- revisar pruebas actuales de Proyectos;
- validar estado real de v3.12.0.

### Resultado

Una línea base reproducible.

---

# 72. FASE 1 — Modelo del Nuevo Dominio

Implementar:

```text
Proyecto supervisor
ProyectoFacturaVenta
CotizacionCostoProyecto
InversionProyectoInicio
AprobacionInicioProyecto
```

solo después de cerrar `[DECISIÓN]`.

Crear migraciones generadas por Django.

No editar dependencies manualmente.

---

# 73. FASE 2 — Servicios + Selectors

Implementar:

```text
vínculo de facturas
cotizaciones
inversiones
resumen
viabilidad
aprobación
gate de Planeación
```

con:

```text
transaction.atomic
DSV
OrganizationalScope
permissions
```

---

# 74. FASE 3 — API

Agregar endpoints explícitos.

Todas las acciones financieras importantes deben pasar por Service Layer.

No permitir:

```text
PUT directo para aprobar.
```

---

# 75. FASE 4 — REESTRUCTURACIÓN VISUAL DE FASE 1

Eliminar el bloque actual de:

```text
Factura de Venta Vinculada
```

que representa una única factura.

Reemplazarlo por:

```text
Facturas de Venta del Proyecto
```

multiregistro.

Agregar:

```text
Supervisor
Contratista/Proveedor
Cotizaciones de Costos
Inversiones
Viabilidad
Estado de Aprobación
```

---

# 76. FASE 5 — GATE FASE 2

Modificar:

```text
ProyectoBusinessService.cambiar_fase_proyecto()
```

para impedir:

```text
INICIO → PLANEACION
```

sin:

```text
AprobacionInicioProyecto == APROBADO
```

Debe existir prueba backend específica.

---

# 77. FASE 6 — FRONTEND DE APROBACIÓN

El formulario debe reflejar:

```text
Bloqueado
En revisión
Aprobado
Rechazado
```

y renderizar correctamente:

```text
puede_avanzar_planeacion
```

Nunca confiar solamente en CSS/JS para seguridad.

---

# 78. FASE 7 — MIGRACIÓN HISTÓRICA

Ejecutar primero:

```bash
python manage.py ... --dry-run
```

Revisar reporte.

Después aplicar migración real.

No corregir silenciosamente casos ambiguos.

---

# 79. FASE 8 — REVISIÓN DEL CICLO COMPLETO

Validar:

```text
0 → 1
1 → aprobación
aprobación → 2
2 → 3
3 → 4
```

y también:

```text
rechazo
reaprobación
cambio económico posterior
```

---

# 80. TESTS BACKEND MÍNIMOS

## Supervisor

```text
supervisor del mismo tenant = OK
supervisor de otro tenant = RECHAZADO
```

## Facturas

```text
factura válida = OK
factura de compra = RECHAZADO
factura de otro tenant = RECHAZADO
misma factura dos veces = RECHAZADO
```

## Cotizaciones de costo

```text
categoría válida = OK
PDF válido = OK
archivo inválido = RECHAZADO
otro tenant = RECHAZADO
```

## Inversiones

```text
crear = OK
actualizar = OK
eliminar = según estado del proyecto
otro tenant = RECHAZADO
```

---

# 81. TESTS DE VIABILIDAD

Casos:

```text
valor venta > costos
valor venta = costos
valor venta < costos
valor venta = 0
sin cotizaciones
sin inversiones
solo inversiones
solo cotizaciones
```

Proteger:

```text
division by zero
Decimal
redondeos
```

---

# 82. TESTS DE APROBACIÓN

```text
usuario no admin no puede aprobar
admin del mismo tenant puede aprobar
admin de otro tenant no puede aprobar
rechazo conserva motivo
aprobación queda persistida
refresh_from_db() conserva aprobación
```

---

# 83. TESTS DEL GATE DE PLANEACIÓN

### Debe fallar

```text
INICIO
aprobación pendiente
→ PLANEACION
```

### Debe fallar

```text
INICIO
rechazado
→ PLANEACION
```

### Debe funcionar

```text
INICIO
APROBADO
→ PLANEACION
```

---

# 84. TEST DE INVALIDACIÓN

Caso:

```text
Admin aprueba
↓
usuario modifica factura/costo/inversión
↓
aprobación debe invalidarse o bloquear modificación
↓
Planeación debe volver a quedar condicionada
```

Esta prueba es obligatoria antes de producción.

---

# 85. TEST E2E MANUAL

## Caso 1
Crear proyecto.

## Caso 2
Abrir Fase 1.

## Caso 3
Asignar Supervisor.

## Caso 4
Asignar Contratista/Proveedor.

## Caso 5
Vincular Factura de Venta 1.

## Caso 6
Vincular Factura de Venta 2.

## Caso 7
Verificar suma del valor vendido.

## Caso 8
Crear cotización de Mano de Obra.

## Caso 9
Crear cotización de Materiales.

## Caso 10
Crear cotización de Equipos.

## Caso 11
Subir PDF individual para cada una.

## Caso 12
Registrar inversiones reales.

## Caso 13
Verificar cálculo económico.

## Caso 14
Enviar a aprobación.

## Caso 15
Como usuario no admin intentar aprobar.

Debe fallar.

## Caso 16
Como ADMIN aprobar.

## Caso 17
Verificar que Fase 2 se desbloquee.

## Caso 18
Intentar modificar un dato económico aprobado.

Verificar la política definida.

## Caso 19
Comprobar que el proyecto no pueda saltarse el gate usando directamente el endpoint.

---

# 86. RESULTADO OPERATIVO ESPERADO

La experiencia final debe transmitir:

```text
BORRADOR
“Estamos definiendo el proyecto”

↓

INICIO
“Estamos comprobando que el negocio existe,
quién lo supervisa, a quién se contrata,
por cuánto se vendió y cuánto cuesta.”

↓

APROBACIÓN
“El administrador autoriza continuar.”

↓

PLANEACIÓN
“Ahora sí diseñamos cómo vamos a ejecutarlo.”

↓

EJECUCIÓN
“Controlamos tiempos, tareas y gastos no facturables.”

↓

CIERRE
“Comprobamos resultado y cerramos.”
```

---

# 87. REGLA DE ORO DEL NUEVO CICLO

```text
NO HAY PLANEACIÓN
SIN APROBACIÓN DEL INICIO ECONÓMICO.
```

En backend:

```python
if proyecto.fase_actual == "INICIO":
    if not proyecto.aprobacion_inicio_es_valida:
        raise ValidationError(
            "El proyecto debe tener aprobación administrativa "
            "antes de pasar a Planeación."
        )
```

El código anterior es conceptual. No copiar literalmente sin adaptar al patrón actual.

---

# 88. PRINCIPIOS QUE DEBEN CONSERVARSE

1. Service Layer como SSoT.
2. Selectors para lectura.
3. CRUD services para persistencia.
4. ViewSets delgados.
5. Sin business logic en signals.
6. DSV por `empresa_id`.
7. OrganizationalScope.
8. UUID en APIs públicas.
9. PostgreSQL como SSoT.
10. No duplicar Facturas, Gastos, Proveedores o Cotizaciones comerciales dentro de Proyectos.
11. No crear tablas espejo sin necesidad.
12. Las acciones de aprobación son comandos de dominio.
13. Los cálculos deben residir en backend.
14. Frontend solo presenta estado.
15. Las migraciones históricas deben ser auditables.

---

# 89. DECISIONES PENDIENTES ANTES DE CODIFICAR

Estas decisiones se dejan deliberadamente abiertas para NO asumir comportamiento.

## `[DECISIÓN 01] Supervisor`

¿El Supervisor debe venir exclusivamente de `apps.tenant.empleados`, limitado a empleados activos?

## `[DECISIÓN 02] Contratista`

¿Existe un único Contratista/Proveedor Principal por proyecto o pueden existir varios?

## `[DECISIÓN 03] Facturas válidas`

¿Qué estados de Factura de Venta pueden vincularse?

Recomendación:

```text
ACEPTADA
```

## `[DECISIÓN 04] Notas Crédito`

¿El valor real vendido debe calcularse como:

```text
FE + ND - NC
```

?

## `[DECISIÓN 05] Base de IVA`

Para viabilidad:

```text
¿usar total de factura?
¿usar subtotal antes de IVA?
```

Recomendación:

```text
mostrar ambos y definir una base comparable.
```

## `[DECISIÓN 06] Inversión Real`

¿La inversión real representa:

```text
dinero efectivamente pagado
```

o:

```text
costo/compromiso ya incurrido aunque no esté pagado
```

Esto cambia totalmente el significado del indicador.

## `[DECISIÓN 07] Aprobación`

¿Los datos económicos quedan bloqueados después de aprobar?

Recomendación:

```text
un cambio posterior invalida aprobación
y obliga a nueva revisión.
```

## `[DECISIÓN 08] Avance`

Después de aprobar:

```text
¿Fase 2 solo se desbloquea?
```

o:

```text
¿Admin aprobar = mover automáticamente a Planeación?
```

Recomendación:

```text
solo desbloquear.
```

## `[DECISIÓN 09] Múltiples cotizaciones`

¿Debe ser posible seleccionar cuál cotización ganó/queda como referencia?

Esta función no debe inventarse en la primera versión si no es necesaria.

## `[DECISIÓN 10] Viabilidad`

¿Qué indicador quiere utilizar negocio como criterio oficial?

Opciones iniciales:

```text
Margen basado en cotización
Margen basado en inversión real
Ambos
```

---

# 90. ORDEN RECOMENDADO PARA EL AGENTE DE CODIFICACIÓN

Ejecutar exactamente en este orden:

```text
1. Auditoría final del estado actual
2. Resolver decisiones funcionales
3. Diseño de modelos
4. Migraciones
5. Selectors
6. Business services
7. CRUD services
8. API
9. Gate de transición
10. Frontend Fase 1
11. Migración histórica
12. Tests backend
13. Tests API
14. Tests frontend
15. E2E manual
16. Actualizar documentación
```

No empezar por el HTML.

---

# 91. CRITERIO PARA NO CREAR DUPLICACIÓN

Antes de crear cualquier nuevo campo, modelo o servicio el agente debe responder:

```text
¿Esta información ya existe en otra app?
```

Si existe:

```text
leer desde la SSoT existente.
```

Si la relación es específica de Proyecto:

```text
crear bridge/context model.
```

Si se trata de una aprobación:

```text
crear entidad de auditoría.
```

---

# 92. DIFERENCIA ENTRE FUENTES

La arquitectura final debe distinguir:

```text
FACTURA
→ fuente de verdad del valor vendido

COTIZACION COMERCIAL
→ fuente comercial de la propuesta

COTIZACION DE COSTO
→ fuente de estimación de costos

INVERSION
→ fuente de costo real registrado en el proceso inicial

GASTO
→ fuente de gasto operativo durante ejecución

CONTABILIDAD
→ fuente contable
```

No mezclar estos conceptos.

---

# 93. IMPACTO EN DOCUMENTACIÓN

Después de implementar esta fase deberán actualizarse:

```text
AUDITORIA_FLUJO_COMPLETO.md
DOCUMENTATION_INDEX.md
TRACEABILITY_MATRIX.md
documentación del módulo Proyectos
documentación API
```

La auditoría debe dejar de describir como regla principal:

```text
INICIO → PLANEACION
```

y describir:

```text
INICIO
→ validación económica
→ aprobación
→ desbloqueo Planeación
```

---

# 94. CAMBIO DE VERSIÓN PROPUESTO

No asignar todavía una versión definitiva en código.

Propuesta conceptual:

```text
v3.12.x
   ↓
v3.13.0
```

si la organización considera esta modificación como cambio funcional mayor del módulo.

La versión final debe decidirse después de cerrar el alcance.

---

# 95. DEFINICIÓN DE HECHO PARA ESTA MISIÓN

La implementación se considerará correcta cuando:

```text
Fase 0 funciona como hoy
        +
Fase 1 permite supervisor
        +
Fase 1 permite contratista/proveedor
        +
Fase 1 permite varias facturas de venta
        +
Fase 1 calcula valor vendido desde Facturas
        +
Fase 1 permite múltiples cotizaciones de costo
        +
cada cotización puede tener PDF
        +
Fase 1 permite inversiones reales
        +
el sistema cruza venta vs costos/inversión
        +
el usuario puede enviar a aprobación
        +
solo ADMIN puede aprobar
        +
la aprobación queda auditada
        +
Planeación queda bloqueada hasta aprobación
        +
no existe bypass por API
        +
Fase 2 conserva su función técnica
        +
Fase 3 conserva tiempos/tareas/gastos
        +
Fase 4 conserva cierre
```

---

# 96. CONCLUSIÓN

La modificación solicitada no debe implementarse como otro conjunto de campos dentro del formulario.

Es una **redefinición del ciclo de vida del Proyecto**.

La arquitectura recomendada pasa de:

```text
Borrador
→ Inicio
→ Planeación
```

a:

```text
Borrador
→ Inicio
   → validar quién ejecuta
   → registrar cómo se vendió
   → registrar cuánto cuesta
   → registrar inversión
   → calcular viabilidad
   → enviar
   → aprobación administrativa
→ Planeación
→ Ejecución
→ Cierre
```

La condición fundamental queda establecida:

> **Planeación no debe desbloquearse simplemente porque alguien pulse “Avanzar fase”; debe existir una aprobación administrativa válida basada en la información económica registrada en Inicio.**

Las decisiones marcadas `[DECISIÓN]` deben cerrarse antes de convertir este documento en un plan de implementación definitivo. El resto del diseño debe tratarse como arquitectura propuesta y no como hechos asumidos del negocio.

---

# FIN DEL PLAN
