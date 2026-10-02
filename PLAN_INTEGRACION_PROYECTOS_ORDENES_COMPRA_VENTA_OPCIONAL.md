# PLAN DE INTEGRACION: PROYECTOS + ORDENES DE COMPRA + VENTA OPCIONAL

## 0. Objetivo

Evolucionar el flujo de `apps/tenant/proyectos` para que el **Proyecto sea el eje funcional primordial** del ciclo operativo, permitiendo que una **Orden de Compra creada y aprobada** sea incorporada explícitamente a un Proyecto mientras este se encuentra en la fase **`0. BORRADOR / OPORTUNIDAD`**.

La `app ventas` debe permanecer **opcional**: un Proyecto puede existir, avanzar de fase y operar con Ordenes de Compra sin tener una Venta asociada. La Venta, cuando exista, se conecta al Proyecto como información comercial complementaria.

### Resultado funcional esperado

```text
PROYECTO
  |
  +-- 0. BORRADOR / OPORTUNIDAD
  |      |
  |      +-- Datos base del proyecto
  |      +-- Presupuesto / planeacion inicial
  |      +-- Asociar Ordenes de Compra APROBADAS
  |      +-- Venta opcional
  |
  +-- 1. INICIO
  |
  +-- 2. PLANEACION
  |
  +-- 3. EJECUCION
  |      |
  |      +-- Recepciones de compras
  |      +-- Inventario
  |      +-- Mano de obra
  |
  +-- 4. CIERRE
```

---

# 1. Auditoria confirmada sobre `main`

Repositorio validado:

- `steven-zdt/CRM_SINTEL`
- Rama: `main`
- Estado consultado: 2026-10-02

## 1.1 La relacion OrdenCompra -> Proyecto ya existe

En `apps/tenant/compras/models.py`, `OrdenCompra` ya contiene:

```python
proyecto = models.ForeignKey(
    'tenant_proyectos.Proyecto',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='ordenes_compra',
)
```

Esto significa que **no estamos creando desde cero la relacion de base de datos**. Ya existe una relacion N:1:

```text
Proyecto 1 ---- N OrdenCompra
```

El problema actual es de **flujo, reglas, permisos, UX, lectura optimizada y orquestacion**, no de ausencia de FK.

## 1.2 La asociacion actual es demasiado abierta

`OrdenCompraBusinessService` ya valida que el `proyecto` pertenezca a la misma empresa, pero actualmente la Orden de Compra puede recibir un Proyecto como dato de creacion/actualizacion sin una regla de negocio especifica que exija:

- que la Orden de Compra este `APROBADA` para vincularla desde el flujo del Proyecto;
- que el Proyecto este en `BORRADOR` para realizar la vinculacion;
- que la asociacion se haga desde un flujo explicito del Proyecto;
- que exista una accion dedicada de `Asociar Orden de Compra`;
- que el Proyecto pueda consultar eficientemente sus Ordenes de Compra aprobadas y su estado de recepcion.

## 1.3 Proyecto ya define la fase `0. BORRADOR`

`Proyecto.FASES` contiene:

- `BORRADOR` = `0. Borrador / Oportunidad`
- `INICIO`
- `PLANEACION`
- `EJECUCION`
- `CIERRE`

La transicion de fase actual se realiza en `proyectos/services/business_service.py` mediante `cambiar_fase_proyecto()`.

Actualmente esta funcion valida solamente que la fase exista; el plan debe agregar las reglas especificas necesarias para proteger la nueva operacion de asociacion.

## 1.4 Proyecto ya expone reverse relation de Ordenes de Compra

Gracias al `related_name='ordenes_compra'`, Django ya permite navegar desde el Proyecto hacia las ordenes asociadas sin agregar un FK inverso al modelo Proyecto.

Esto permite mantener la direccion de dependencia:

```text
compras -> proyectos
ventas  -> proyectos
```

sin convertir `Proyecto` en una entidad que importe estructuralmente todos los modulos de negocio.

## 1.5 Venta ya es opcional respecto al Proyecto

En `apps/tenant/ventas/models.py`, `Venta.proyecto` ya es:

- `null=True`
- `blank=True`
- `on_delete=models.SET_NULL`

Por tanto:

```text
Venta -> Proyecto = opcional
```

No es necesario convertir Ventas en prerequisito para crear, aprobar o asociar una Orden de Compra a un Proyecto.

## 1.6 Proyecto tiene actualmente una arquitectura de desacoplamiento

El encabezado de `apps/tenant/proyectos/models.py` declara como principio que el modulo de Proyectos debe mantener bajo acoplamiento con otros modulos y usar referencias/snapshots para varias relaciones.

Por ello, la solucion **no debe agregar FK desde Proyecto hacia OrdenCompra ni desde Proyecto hacia Venta** solamente para poder mostrar informacion.

La relacion que ya posee OrdenCompra hacia Proyecto es suficiente para el vinculo persistente.

---

# 2. Decision arquitectonica objetivo

## 2.1 Proyecto como eje funcional

El usuario operara el proceso desde el Proyecto:

```text
Proyecto
  -> fase 0. Borrador
  -> bloque "Compras del Proyecto"
  -> "Agregar Orden de Compra"
  -> seleccionar Ordenes de Compra APROBADAS
  -> asociar
  -> visualizar total comprometido
  -> seguir ciclo del proyecto
```

## 2.2 OrdenCompra como dueño de la transaccion

La Orden de Compra mantiene la responsabilidad de:

- numeracion;
- proveedor;
- items;
- impuestos;
- total;
- estado;
- aprobacion;
- recepcion;
- sincronizacion con CxP;
- integracion con inventario mediante recepciones.

Proyecto solamente controla el **contexto operativo** al que pertenece la compra.

## 2.3 Venta como modulo opcional

Venta se mantendra como una relacion comercial complementaria:

```text
Proyecto 0..N Ventas
```

Una venta puede existir o no.

Regla:

> Ninguna operacion del flujo Orden de Compra -> Proyecto debe exigir la existencia de una Venta.

---

# 3. Modelo funcional objetivo

## 3.1 Reglas de asociacion

### Regla A - Orden aprobada

Solo una Orden de Compra con estado:

```text
APROBADA
```

puede ser incorporada por el flujo `Proyecto -> Compras`.

No se deben permitir en esta accion:

- `BORRADOR`
- `PENDIENTE`
- `PARCIAL`
- `RECIBIDA`
- `ANULADA`

La unica excepcion futura seria una operacion administrativa explicitamente diseñada para migraciones/correcciones, fuera de este plan.

### Regla B - Proyecto en fase 0

La accion `Asociar Orden de Compra` estara disponible unicamente cuando:

```text
Proyecto.fase_actual == BORRADOR
```

### Regla C - Tenant

Orden y Proyecto deben pertenecer a la misma `empresa`.

### Regla D - Alcance organizacional

La Orden de Compra debe respetar el mismo alcance de sede/area que ya aplica a Compras cuando el usuario tenga alcance restringido.

No se puede asociar una Orden que el usuario no pueda consultar por alcance organizacional.

### Regla E - Idempotencia

Asociar una Orden ya asociada al mismo Proyecto debe ser una operacion idempotente o rechazada con mensaje funcional claro; no debe crear duplicidades porque la relacion es una FK N:1.

### Regla F - Una Orden, un Proyecto

La Orden de Compra conserva un solo `proyecto_id`.

Por tanto:

```text
Una Orden de Compra no puede pertenecer simultaneamente a dos Proyectos.
```

Si la Orden ya pertenece a otro Proyecto, la accion `Asociar` no debe sobrescribirla silenciosamente.

Debe existir una accion explicita de `Reasignar` solamente si el negocio desea permitirla.

### Regla G - No borrar trazabilidad

Nunca se deben borrar Ordenes de Compra porque cambie el Proyecto.

La Orden conserva su historial, estado, proveedor, numeracion, CxP y recepciones.

---

# 4. Politica recomendada para reasignacion

No habilitar `Reasignar Proyecto` en la primera implementacion.

Primera version:

```text
SIN PROYECTO -> PROYECTO
```

permitido bajo reglas.

```text
PROYECTO A -> PROYECTO B
```

bloqueado hasta implementar un flujo administrativo separado.

Esto evita alterar accidentalmente costos, indicadores y trazabilidad del proyecto original.

---

# 5. Nuevo flujo operativo

## FASE 1 - Crear Proyecto

Se crea normalmente:

```text
Proyecto
fase = BORRADOR
```

No se requiere Venta.

No se requiere Orden de Compra.

## FASE 2 - Crear Orden de Compra

La Orden se crea desde Compras.

Inicialmente:

```text
BORRADOR
```

Se completa:

- Plantilla de numeracion
- proveedor
- sede
- area si aplica
- items
- totales
- observaciones

El Proyecto puede quedar vacio en esta etapa.

## FASE 3 - Aprobar Orden

La Orden pasa a:

```text
BORRADOR -> PENDIENTE -> APROBADA
```

segun el flujo existente.

Al llegar a `APROBADA` se mantiene el comportamiento actual de sincronizacion con CxP.

## FASE 4 - Asociar al Proyecto

Desde el Proyecto en `BORRADOR`:

```text
Compras del Proyecto
    + Agregar Orden de Compra
```

El buscador debe mostrar solamente Ordenes elegibles.

Filtro conceptual:

```text
empresa = empresa_actual
AND estado = APROBADA
AND (proyecto IS NULL OR proyecto = proyecto_actual)
AND dentro_del_alcance_organizacional
```

La asociacion se realiza en una operacion transaccional.

## FASE 5 - Visualizacion dentro del Proyecto

El Proyecto debe mostrar un bloque de compras con:

- Numero de Orden
- proveedor
- fecha
- fecha de entrega
- estado
- subtotal
- impuestos
- total
- total recibido
- saldo pendiente de recepcion

Y un total agregado:

```text
Compras aprobadas asociadas
```

## FASE 6 - Paso de fase

Cuando el Proyecto abandona `BORRADOR`, la accion `Agregar Orden de Compra` deja de estar disponible en la UI.

El backend tambien debe rechazar la operacion.

Esto evita que la restriccion exista solamente en frontend.

---

# 6. Tratamiento financiero recomendado

No mezclar inmediatamente:

```text
Orden aprobada
```

con:

```text
Costo real ejecutado
```

## 6.1 Costo comprometido

Una Orden `APROBADA` asociada al Proyecto representa:

```text
Costo comprometido de compras
```

## 6.2 Costo real

El costo real debe continuar asociado al flujo de recepcion/consumo que ya utiliza el proyecto/inventario.

Por tanto:

```text
APROBADA       -> Comprometido
RECEPCIONADA   -> Real/ejecutado segun reglas existentes
```

No se debe reinterpretar `costo_materiales_real` solamente por asociar una Orden.

## 6.3 Nuevos indicadores sugeridos

Agregar, preferiblemente como KPI calculado antes que como cache persistente:

- `compras_comprometidas`
- `compras_recibidas`
- `compras_pendientes`
- `cantidad_ordenes_compra`

La fuente debe ser `OrdenCompra` y `RecepcionCompra`, no duplicar montos manualmente dentro de Proyecto.

---

# 7. Cambios Backend

## Paso 7.1 - Crear servicio de asociacion de compras al proyecto

No colocar la regla en `models.py`.

Crear un servicio especializado dentro de la capa autorizada, preferiblemente en Compras por ser la app dueña de la Orden:

```text
apps/tenant/compras/services/project_assignment_service.py
```

Responsabilidad propuesta:

```python
asociar_orden_a_proyecto(
    *,
    orden_uuid,
    proyecto_uuid,
    empresa_id,
    request=None,
)
```

El servicio debe:

1. cargar Orden por UUID + empresa;
2. cargar Proyecto por UUID + empresa;
3. validar alcance organizacional;
4. validar `orden.estado == APROBADA`;
5. validar `proyecto.fase_actual == BORRADOR`;
6. validar que Orden no este asociada a otro Proyecto;
7. validar consistencia de sede cuando aplique;
8. asignar `orden.proyecto = proyecto`;
9. guardar en `transaction.atomic()`;
10. devolver Orden optimizada.

## Paso 7.2 - No duplicar DSV

Reutilizar el patron existente de:

- `empresa_id`
- UUID
- `OrganizationalScope`
- `SintelDSVMixin`

No crear una segunda capa paralela de seguridad.

## Paso 7.3 - Endpoint explicito

Agregar una accion de API orientada al contexto de Proyecto o de Orden.

Recomendacion:

```text
POST /api/v1/proyectos/{proyecto_uuid}/ordenes-compra/asociar/
```

Body:

```json
{
  "orden_compra_uuid": "..."
}
```

La accion debe delegar al servicio anterior.

Opcionalmente, una accion complementaria de consulta:

```text
GET /api/v1/proyectos/{proyecto_uuid}/ordenes-compra/
```

Esta consulta debe usar Selector optimizado.

## Paso 7.4 - Selector de Ordenes elegibles

Agregar selector especifico:

```text
OrdenCompraSelector.get_disponibles_para_proyecto(...)
```

Debe utilizar:

- `empresa_id`
- `estado=APROBADA`
- `proyecto__isnull=True` para nuevas asociaciones
- alcance de sede/area
- `.select_related('proveedor', 'proyecto')`
- `.only(...)`
- ordenamiento estable

Nunca descargar todas las Ordenes de Compra al navegador.

## Paso 7.5 - Selector de compras del Proyecto

Agregar:

```text
OrdenCompraSelector.get_by_proyecto(...)
```

Debe devolver solamente los campos necesarios para el panel del Proyecto.

---

# 8. Cambios en `apps/tenant/proyectos`

## Paso 8.1 - Mantener Proyecto sin FK a Compras

No agregar:

```python
orden_compra = models.ForeignKey(...)
```

ni relaciones directas nuevas a Venta.

La relacion ya esta en `OrdenCompra.proyecto` y `Venta.proyecto`.

## Paso 8.2 - Exponer resumen de compras

En `ProyectoDetailSerializer`, agregar una representacion liviana del bloque de compras.

La implementacion recomendada es una lectura especializada, no incrustar un serializer completo de Compras si eso provoca cargas innecesarias.

Ejemplo conceptual:

```json
"compras": {
  "cantidad": 3,
  "comprometido": "12500000.00",
  "recibido": "8000000.00",
  "pendiente": "4500000.00",
  "ordenes": [
    {
      "uuid": "...",
      "numero_documento": "OC-101",
      "proveedor": "Proveedor X",
      "estado": "APROBADA",
      "total": "5000000.00"
    }
  ]
}
```

La informacion detallada de recepciones puede continuar en endpoints propios de Compras.

## Paso 8.3 - No duplicar Venta

El detalle del Proyecto puede exponer una seccion comercial opcional:

```text
Venta(s): 0..N
```

Pero no debe impedir el funcionamiento del Proyecto si no existe ninguna Venta.

---

# 9. Cambios en fase del Proyecto

## Regla de salida de BORRADOR

No se recomienda bloquear el avance de fase solamente porque no haya Orden de Compra.

Debe ser posible tener:

```text
Proyecto sin Venta
Proyecto sin Orden de Compra
Proyecto -> INICIO
```

Esto mantiene la Venta y Compras como modulos opcionales.

## Regla de operacion de compras

La asociacion de nuevas Ordenes se permite solamente mientras:

```text
fase_actual == BORRADOR
```

Una vez el proyecto esta en `INICIO`, `PLANEACION`, `EJECUCION` o `CIERRE`, las Ordenes ya asociadas se siguen mostrando y recibiendo normalmente, pero no se agregan nuevas mediante este flujo.

---

# 10. Cambios de UI del Proyecto

La interfaz del Proyecto debe convertirse en el centro de consulta.

## Bloque 1 - Resumen

Mostrar:

- Proyecto
- codigo
- fase
- cliente
- responsable
- valor proyectado

## Bloque 2 - Compras

Nueva seccion:

```text
ORDENES DE COMPRA DEL PROYECTO
```

Con:

```text
[ + Agregar Orden de Compra ]
```

El boton aparece solamente si:

```text
fase = BORRADOR
```

## Selector de Ordenes

Offcanvas/modal de busqueda server-side:

```text
Buscar numero / proveedor

Orden     Proveedor       Fecha       Total       Estado
OC-1001   Hikvision       02/10/2026  $...        APROBADA
OC-1002   Bosch           02/10/2026  $...        APROBADA
```

Accion:

```text
[ Asociar ]
```

## Confirmacion

Mostrar:

```text
La Orden OC-1001 sera asociada al Proyecto PR-001.
Esta operacion no cambia el proveedor ni los valores de la Orden.
```

## Resultado

Al finalizar:

- cerrar offcanvas;
- refrescar bloque de compras;
- refrescar KPIs;
- no recargar toda la aplicacion.

---

# 11. UX de Venta opcional

Agregar una seccion separada:

```text
VENTA / FACTURACION
```

Estado posible:

```text
Sin Venta asociada
```

u:

```text
Venta #...
Factura #...
Estado...
Total...
```

No mostrar Venta como requisito para:

- crear Proyecto;
- avanzar fase;
- crear Orden de Compra;
- aprobar Orden de Compra;
- asociar Orden de Compra al Proyecto.

---

# 12. Cambios en Compras

## 12.1 Crear Orden sin Proyecto

Debe seguir siendo valido:

```text
Orden de Compra APROBADA
Proyecto = NULL
```

Esto es importante para compras generales.

## 12.2 Asignar Proyecto desde la Orden

La edicion directa del campo Proyecto en el formulario de Orden no debe continuar siendo la unica via de vinculacion.

Recomendacion:

- permitir seleccionar Proyecto al crear si el proceso empresarial lo necesita;
- pero para el flujo solicitado, la accion principal debe ser `Proyecto -> Agregar Orden`;
- el backend debe aplicar las mismas reglas cuando una Orden intente recibir un `proyecto` por API.

## 12.3 Evitar doble fuente de verdad

La regla de negocio de asociacion debe existir una sola vez:

```text
ProjectOrderAssignmentService
```

El formulario de Compras y la UI de Proyecto deben llamar al mismo servicio/endpoint.

---

# 13. Cambios en Ventas

No hacer una refactorizacion grande de Venta en esta fase.

Solo validar que:

- `Venta.proyecto` continue opcional;
- el filtro por Proyecto funcione;
- Proyecto pueda visualizar Ventas cuando existan;
- no se introduzcan FK nuevas en Proyecto;
- una ausencia de Venta no genere errores de UI/serializer.

---

# 14. Indicadores del Proyecto

Agregar al contexto del Proyecto:

### Compras

```text
OC Aprobadas
Valor comprometido
Valor recibido
Saldo por recibir
```

### Venta

```text
Ventas asociadas
Valor facturado
```

La seccion Venta debe poder estar en cero.

### Margen

No recalcular margen usando una nueva formula improvisada.

Debe respetarse la logica financiera existente y, cuando sea necesario, incorporar las nuevas compras mediante un Selector/BusinessService SSoT.

---

# 15. Reglas de sincronizacion de recepcion

Cuando una Orden asociada al Proyecto pasa por:

```text
RecepcionCompra CONFIRMADA
```

el Proyecto debe poder reflejar el nuevo acumulado de compras recibidas.

No agregar logica financiera en signals.

La actualizacion de inventario continua en:

```text
RecepcionCompraBusinessService
  -> KardexService
```

El Proyecto consulta el resultado; no debe duplicar el movimiento de inventario.

---

# 16. Performance

## 16.1 Nunca cargar todas las Ordenes

La pantalla del Proyecto debe usar consultas server-side.

## 16.2 Evitar N+1

El detalle de Proyecto debe utilizar:

```text
prefetch_related('ordenes_compra')
```

solo cuando el detalle realmente necesite la coleccion completa.

Para listados generales de Proyectos no se debe precargar toda la coleccion.

## 16.3 Selector especifico

Crear un selector de lectura de Ordenes por Proyecto para que la optimizacion quede centralizada.

## 16.4 KPIs

Calcular indicadores con agregaciones SQL y no iterando cada Orden en Python.

---

# 17. Seguridad y aislamiento tenant

Todas las operaciones deben verificar:

```text
empresa_id Orden == empresa_id Proyecto == empresa_id contexto
```

Nunca confiar solamente en:

```text
orden.proyecto_id = proyecto_id
```

El endpoint debe usar UUID publicamente y aplicar DSV antes de actualizar.

Debe respetarse el alcance organizacional ya usado por Compras.

---

# 18. Base de datos / migraciones

La relacion `OrdenCompra.proyecto` ya existe en `main`.

Por tanto, el objetivo inicial es:

```text
NO crear una FK duplicada
```

La migracion solo sera necesaria para cambios reales, por ejemplo:

- nuevos indices especializados;
- nuevos campos de cache/KPI si se comprueba que son indispensables;
- restricciones adicionales que realmente se decidan persistir.

## Indices recomendados

Verificar el indice de consultas:

```text
(empresa_id, proyecto_id, estado)
```

sobre `OrdenCompra` si el volumen lo justifica.

Antes de agregarlo, revisar los indices existentes para no duplicarlos.

---

# 19. Documentacion SSoT

Actualizar:

```text
apps/tenant/proyectos/.agent/
apps/tenant/compras/.agent/
```

y los documentos de arquitectura correspondientes.

Debe documentarse explicitamente:

```text
Proyecto = eje funcional
OrdenCompra = transaccion de compra asociable
Venta = modulo comercial opcional
```

Eliminar contradicciones documentales como:

- Proyecto declarado como totalmente desacoplado mientras documenta flujos que dependen de Ventas;
- Compras permitiendo asociacion directa sin regla de fase;
- documentos de Compras que no mencionen el contexto de Proyecto.

---

# 20. Secuencia de implementacion recomendada

## FASE 0 - Baseline

- Congelar el comportamiento actual de Compras y Proyectos.
- Confirmar que `OrdenCompra.proyecto` y `Venta.proyecto` son las unicas relaciones persistentes requeridas.
- No introducir cambios funcionales todavia.

## FASE 1 - Dominio de asociacion

Crear:

```text
ProjectOrderAssignmentService
```

Implementar:

- DSV
- tenant
- estado APROBADA
- fase BORRADOR
- idempotencia
- bloqueo de reasignacion silenciosa
- transaction.atomic

## FASE 2 - Selectors

Crear:

```text
get_disponibles_para_proyecto()
get_by_proyecto()
```

Optimizar con:

- `.only()`
- `.select_related()`
- filtro organizacional
- agregaciones

## FASE 3 - API Proyecto -> Compras

Crear endpoint de asociacion y endpoint de consulta.

La respuesta debe devolver informacion suficiente para refrescar la UI.

## FASE 4 - Integracion en Proyecto

Agregar bloque:

```text
Ordenes de Compra
```

al detalle del Proyecto.

Agregar boton:

```text
+ Agregar Orden de Compra
```

solo en BORRADOR.

## FASE 5 - Selector server-side

Construir offcanvas/modal de busqueda de Ordenes APROBADAS.

No cargar colecciones completas.

## FASE 6 - Integracion de KPIs

Agregar:

- cantidad;
- comprometido;
- recibido;
- pendiente.

Mantener costos reales bajo las reglas actuales de recepcion.

## FASE 7 - Compras

Asegurar que el mismo servicio se use si se intenta asociar Proyecto desde Compras.

Eliminar cualquier validacion duplicada de negocio.

## FASE 8 - Venta opcional

Revisar solo lectura y UI.

Garantizar que:

```text
Proyecto sin Venta = escenario valido
```

## FASE 9 - Documentacion

Actualizar `.agent`, arquitectura y trazabilidad.

## FASE 10 - Limpieza

Eliminar:

- queries duplicadas;
- endpoints duplicados;
- serializers duplicados;
- logica frontend duplicada;
- imports circulares innecesarios.

---

# 21. Archivos principales a revisar/modificar

## Compras

```text
apps/tenant/compras/models.py
apps/tenant/compras/services/business_service.py
apps/tenant/compras/services/selectors.py
apps/tenant/compras/services/crud_service.py
apps/tenant/compras/api/serializers.py
apps/tenant/compras/api/viewsets.py
apps/tenant/compras/static/compras/js/*
apps/tenant/compras/templates/*
apps/tenant/compras/.agent/*
```

## Proyectos

```text
apps/tenant/proyectos/models.py
apps/tenant/proyectos/services/business_service.py
apps/tenant/proyectos/services/selectors.py
apps/tenant/proyectos/api/serializers.py
apps/tenant/proyectos/api/viewsets.py
apps/tenant/proyectos/static/*
apps/tenant/proyectos/templates/tenant/proyectos/*
apps/tenant/proyectos/.agent/*
```

## Ventas

```text
apps/tenant/ventas/models.py
apps/tenant/ventas/services/*
apps/tenant/ventas/api/*
apps/tenant/ventas/static/*
```

La intervencion de Ventas debe ser minima en esta fase.

---

# 22. Reglas que NO se deben romper

1. No introducir logica de negocio en `models.py`.
2. No usar Django signals para sincronizar Proyecto con OrdenCompra.
3. No crear una FK inversa desde Proyecto hacia OrdenCompra.
4. No volver obligatoria la Venta.
5. No crear una segunda entidad paralela para representar la asociacion Proyecto-Orden.
6. No duplicar la numeracion de Ordenes.
7. No alterar la SSoT de calculos financieros de OrdenCompra.
8. No romper CxP al aprobar una Orden.
9. No romper RecepcionCompra ni Kardex.
10. No sobrescribir silenciosamente el Proyecto de una Orden ya asignada.
11. No utilizar PK secuencial en URLs publicas.
12. Mantener UUID + `empresa_id` + DSV.
13. Mantener Service Layer como SSoT.

---

# 23. Resultado UX final esperado

El usuario debe poder pensar el proceso asi:

```text
1. Creo Proyecto
        |
        v
2. Proyecto queda en 0. Borrador
        |
        v
3. Creo Orden de Compra
        |
        v
4. Apruebo Orden de Compra
        |
        v
5. Abro Proyecto
        |
        v
6. "Agregar Orden de Compra"
        |
        v
7. Selecciono OC aprobada
        |
        v
8. La OC aparece dentro del Proyecto
        |
        +--> Comprometido
        +--> Recibido
        +--> Pendiente
        |
        v
9. Avanzo Proyecto a siguiente fase
        |
        v
10. Las compras permanecen visibles durante la ejecucion
```

La Venta puede entrar en cualquier momento compatible con su propio flujo, pero no debe ser un requisito para completar los pasos anteriores.

---

# 24. Validacion manual final

La validacion funcional debe realizarse al final y unicamente sobre la interfaz, respetando el criterio actual del proyecto de no añadir una fase de pruebas automatizadas en esta mision.

## Caso 1 - Proyecto sin Venta

- Crear Proyecto.
- Mantenerlo en `0. Borrador`.
- No crear Venta.
- Confirmar que funciona normalmente.

## Caso 2 - Orden aprobada sin Proyecto

- Crear Orden.
- Aprobarla.
- Confirmar que puede existir sin Proyecto.

## Caso 3 - Asociar Orden aprobada

- Abrir Proyecto en `0. Borrador`.
- Agregar Orden aprobada.
- Confirmar que aparece en la lista.
- Confirmar total comprometido.

## Caso 4 - Rechazo de Orden no aprobada

- Intentar agregar una Orden `BORRADOR`.
- Confirmar rechazo funcional.

## Caso 5 - Proyecto fuera de BORRADOR

- Avanzar Proyecto a `INICIO`.
- Confirmar que `Agregar Orden de Compra` no aparece.
- Intentar por API manual si es necesario.
- Confirmar que backend rechaza la operacion.

## Caso 6 - Orden ya asociada

- Intentar volver a asociarla al mismo Proyecto.
- Confirmar idempotencia o mensaje funcional claro.

## Caso 7 - Orden perteneciente a otro Proyecto

- Intentar asociarla a un segundo Proyecto.
- Confirmar que el backend no sobrescribe silenciosamente el Proyecto original.

## Caso 8 - Recepcion

- Registrar recepcion confirmada.
- Volver al Proyecto.
- Confirmar incremento del valor recibido y reduccion del pendiente.

## Caso 9 - Venta opcional

- Crear Proyecto sin Venta.
- Crear Proyecto con Venta.
- Confirmar que ambos escenarios son validos.

## Caso 10 - Seguridad tenant

- Verificar que una Orden de otra empresa no aparece ni puede asociarse.

---

# 25. Criterios de terminado

La implementacion se considera completa cuando:

- `Proyecto` es el punto principal de consulta y asociacion de Compras.
- Una Orden `APROBADA` puede asociarse a un Proyecto en `BORRADOR`.
- Una Orden no puede ser asociada a un Proyecto de otra empresa.
- Una Orden ya asociada no puede ser reasignada silenciosamente.
- El Proyecto muestra Ordenes asociadas sin N+1.
- Los indicadores de compras se calculan desde las fuentes reales.
- La Venta sigue siendo opcional.
- No existen FK nuevas innecesarias desde Proyecto hacia Compras o Ventas.
- No existe logica duplicada entre Proyecto y Compras.
- No se utilizan signals para resolver esta integracion.
- El backend protege las mismas reglas que la UI.
- El flujo existente de CxP e Inventario permanece operativo.
- La interfaz permite operar el ciclo completo sin salir del contexto del Proyecto.

---

# 26. Decision SSoT final

```text
                    +------------------+
                    |     PROYECTO     |
                    |  Eje funcional   |
                    +---------+--------+
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
    +--------------------+             +----------------+
    |   ORDEN COMPRA     |             |     VENTA      |
    | Transaccion propia |             |    Opcional    |
    +---------+----------+             +--------+-------+
              |                                 |
              v                                 v
       Recepcion / CxP                    Facturacion DIAN
       Inventario                         Comercial
```

La clave del diseño es que **Proyecto sea el eje de contexto y navegacion**, mientras **OrdenCompra siga siendo el SSoT transaccional de Compras** y **Venta permanezca opcional**.
