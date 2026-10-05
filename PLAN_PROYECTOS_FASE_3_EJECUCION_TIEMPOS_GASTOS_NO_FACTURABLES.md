# PLAN DE ACCIÓN — PROYECTOS · FASE 3 «EJECUCIÓN»

## Rediseño operativo de tiempos, cronograma, tareas y gastos no facturables

**Repositorio:** `steven-zdt/CRM_SINTEL`  
**Rama auditada:** `main`  
**Módulo:** `apps/tenant/proyectos` + integración con `apps/tenant/gastos`  
**Pantalla objetivo:** `http://admin.sintel.net.co/workspace/#proyectos` → **Editar Proyecto** → **3. Ejecución**  
**Objetivo:** convertir la Fase 3 en un centro operativo de seguimiento de ejecución, concentrado en avance, cronograma, tiempos, tareas y gastos no facturables reales asociados al proyecto.

---

# 1. OBJETIVO FUNCIONAL

La Fase 3 debe responder principalmente estas preguntas:

1. ¿En qué estado está la ejecución del proyecto?
2. ¿Cuánto tiempo ha transcurrido y cuánto falta según el cronograma?
3. ¿Qué tareas estaban programadas, cuáles están en proceso y cuáles ya fueron terminadas?
4. ¿Qué tareas están atrasadas o requieren atención?
5. ¿Qué gastos no facturables reales se han generado para este proyecto?
6. ¿Cuánto representan esos gastos y cuáles fueron los últimos movimientos?

La Fase 3 **no debe ser una segunda pantalla de presupuesto, ventas o rentabilidad comercial**.

El criterio operativo será:

```text
FASE 2 · PLANEACIÓN
    ↓
Recursos y costos planeados
    ↓
FASE 3 · EJECUCIÓN
    ├── Avance
    ├── Tiempo
    ├── Cronograma
    ├── Tareas
    └── Gastos no facturables reales
    ↓
FASE 4 · CIERRE
```

---

# 2. HALLAZGOS DE LA REVISIÓN DEL REPOSITORIO

## 2.1 `Proyecto` ya tiene la base de tiempo necesaria

En `apps/tenant/proyectos/models.py`, `Proyecto` ya dispone de:

- `fecha_inicio`
- `fecha_fin_estimada`
- `porcentaje_avance`
- `fase_actual`
- `estado_tarea`
- `cronograma_archivo`
- `responsable_operativo_id`
- `responsable_operativo_nombre`

Por tanto, no es necesario crear un nuevo modelo de cronograma para esta misión.

La Fase 3 debe aprovechar esos campos antes de crear nuevas entidades.

## 2.2 Existe `TareaDiariaProyecto`

El modelo `TareaDiariaProyecto` ya permite registrar:

- fecha de inicio
- fecha de fin
- título
- descripción
- estado
- prioridad
- asignado
- notas de progreso

Los estados actuales son:

```text
PENDIENTE
EN_PROCESO
COMPLETADA
CANCELADA
```

También existen reglas en `TareasDiariasBusinessService` para:

- validar rango de fechas;
- impedir tareas fuera del periodo del proyecto;
- bloquear modificaciones al entrar en `CIERRE`;
- validar DSV de empresa.

Por tanto, **no se debe crear otro sistema de tareas**.

## 2.3 Ya existe una API independiente de tareas

Actualmente existen endpoints equivalentes a:

```text
GET    /api/v1/proyectos/tareas-diarias/?proyecto_uuid=<uuid>
POST   /api/v1/proyectos/tareas-diarias/
PATCH  /api/v1/proyectos/tareas-diarias/<uuid>/
DELETE /api/v1/proyectos/tareas-diarias/<uuid>/
POST   /api/v1/proyectos/tareas-diarias/<uuid>/cambiar-estado/
```

La Fase 3 debe mejorar su consumo y presentación, no duplicar el CRUD.

## 2.4 El bloque financiero actual no está alineado con el nuevo propósito

Actualmente la Fase 3 muestra:

- `Valor del Contrato (base)`;
- Mano de Obra real;
- Materiales reales;
- Total Costos Reales;
- Utilidad Estimada;
- Margen de Rentabilidad.

Este bloque depende de `valor_contrato_proyectado` y de `calcular_indicadores_financieros()`.

Para el nuevo diseño, **ese panel deja de ser contenido principal de Ejecución**.

## 2.5 El repositorio actual de Gastos todavía no tiene relación con Proyecto

En `apps/tenant/gastos/models.py`, el modelo operativo de gasto es `DocumentoSoporte` y actualmente no existe:

```python
proyecto_uuid
proyecto_nombre
facturable
```

Tampoco existe un selector de proyecto en:

- `offcanvas_crear_gasto.html`
- `offcanvas_editar_gasto.html`

Y los serializers actuales de Gastos tampoco exponen esos datos.

### Consecuencia

La automatización solicitada **no puede resolverse solamente modificando Proyectos**.

Primero debe habilitarse en Gastos la capacidad de declarar:

```text
Gasto
 ├── Proyecto asociado (opcional)
 └── Facturable / No facturable
```

Luego Proyectos consumirá esos datos mediante un modelo pull/read-only.

---

# 3. PRINCIPIO ARQUITECTÓNICO

## 3.1 No crear una tabla de gastos dentro de Proyectos

No crear:

```text
ProyectoGasto
ItemGastoProyecto
GastoProyecto
```

como una copia de `DocumentoSoporte`.

El Gasto sigue perteneciendo a la aplicación **Gastos**.

La relación operativa será:

```text
GASTOS
DocumentoSoporte
     │
     ├── empresa
     ├── facturable
     ├── proyecto_uuid
     └── proyecto_nombre (snapshot)
              │
              ▼
PROYECTOS · FASE 3
Consulta automática
```

## 3.2 Proyectos debe leer, no duplicar

La Fase 3 no debe crear un registro adicional cuando aparece un gasto.

Debe consultar el SSoT de Gastos y mostrarlo directamente.

Esto garantiza:

- no duplicación de montos;
- no doble contabilidad;
- cambios en Gastos reflejados automáticamente;
- anulaciones y desactivaciones reflejadas sin procesos manuales;
- menor riesgo de inconsistencias.

## 3.3 La lógica debe estar en service/selector

No implementar reglas de negocio en:

- JavaScript;
- templates;
- signals;
- `save()` del modelo para resolver la integración.

Patrón esperado:

```text
ViewSet
   ↓
Service / Selector
   ↓
SSoT Gastos
   ↓
Serializer / API
   ↓
UI Fase 3
```

---

# 4. NUEVO MODELO OPERATIVO DE GASTOS ASOCIADOS A PROYECTO

## 4.1 Agregar referencia suave a Proyecto en Gastos

Debido al patrón de bajo acoplamiento del repositorio, preferir una referencia UUID suave:

```python
proyecto_uuid = models.UUIDField(
    null=True,
    blank=True,
    db_index=True,
    verbose_name='Proyecto',
)

proyecto_nombre = models.CharField(
    max_length=200,
    blank=True,
    verbose_name='Proyecto (snapshot)',
)
```

### Motivo

`Proyecto` actualmente utiliza UUID público y la app conserva referencias desacopladas en varios dominios.

No introducir una FK fuerte desde Gastos a Proyectos solamente para esta pantalla.

## 4.2 Agregar estado de facturabilidad explícito

Incorporar un campo de SSoT para distinguir gastos facturables y no facturables.

Preferencia de diseño:

```python
facturable = models.BooleanField(
    default=False,
    db_index=True,
    verbose_name='Facturable',
)
```

### Recomendación importante para datos históricos

No ejecutar una migración que cambie silenciosamente el significado comercial de todos los gastos existentes sin revisar los datos.

La implementación debe incluir una estrategia explícita de backfill para registros anteriores.

Una opción segura es:

1. agregar el campo;
2. revisar / documentar el valor por defecto para datos históricos;
3. crear la migración de datos;
4. verificar una muestra real;
5. solo después consolidar el comportamiento.

---

# 5. VALIDACIÓN DEL PROYECTO EN LA APP GASTOS

Cuando se seleccione un proyecto desde Gastos, el Business Service de Gastos debe validar:

1. que el UUID exista;
2. que pertenezca a la misma `empresa_id`;
3. que esté dentro del alcance organizacional del usuario cuando aplique;
4. que el proyecto no esté en una situación que impida modificar gastos según las reglas vigentes;
5. que el snapshot `proyecto_nombre` corresponda al proyecto seleccionado.

No confiar únicamente en el UUID enviado por el navegador.

El backend debe ejecutar DSV.

---

# 6. UI DE GASTOS: ASIGNAR PROYECTO

Modificar:

```text
apps/tenant/gastos/templates/tenant/gastos/offcanvas_crear_gasto.html
apps/tenant/gastos/templates/tenant/gastos/offcanvas_editar_gasto.html
```

Agregar una sección simple:

```text
Proyecto asociado (opcional)
[ Buscar proyecto... ]

[ ] Gasto facturable
```

El flujo debe permitir:

```text
Gasto no facturable + sin proyecto
    → gasto interno general

Gasto no facturable + proyecto
    → gasto operativo asociado a proyecto

Gasto facturable + proyecto
    → gasto facturable asociado a proyecto
```

Solo el segundo caso alimentará el bloque solicitado en Fase 3.

---

# 7. BÚSQUEDA DE PROYECTOS EN GASTOS

No cargar todos los proyectos en el formulario.

Usar búsqueda bajo demanda:

```text
GET /api/v1/proyectos/?search=<texto>
```

El patrón debe seguir `Sintel.Core.Http`.

Debe permitir buscar por:

- código;
- nombre;
- cliente cuando esté disponible.

Después de seleccionar:

```text
proyecto_uuid
proyecto_nombre
```

se envían al backend.

---

# 8. API DE GASTOS PARA CONSUMO DESDE PROYECTOS

Crear una consulta específica para Proyectos, evitando que el frontend conozca la estructura interna de Gastos.

Propuesta:

```text
GET /api/v1/gastos/por-proyecto/?proyecto_uuid=<uuid>&facturable=false
```

La respuesta debería entregar únicamente datos operativos útiles.

Ejemplo conceptual:

```json
{
  "count": 3,
  "total": 485000,
  "results": [
    {
      "uuid": "...",
      "fecha": "2026-10-01",
      "numero_documento": "DS 001234",
      "proveedor_nombre": "Proveedor ABC",
      "categoria_contable": "TRANSPORTE_FLETES",
      "categoria_contable_display": "Transporte y Fletes",
      "descripcion": "Transporte de material",
      "subtotal": 200000,
      "total": 238000,
      "facturable": false,
      "proyecto_uuid": "...",
      "proyecto_nombre": "Proyecto ..."
    }
  ]
}
```

No devolver datos contables sensibles que la pantalla no necesita.

---

# 9. SELECTOR SSoT PARA GASTOS DE PROYECTO

Crear un selector reutilizable, por ejemplo:

```text
apps/tenant/gastos/services/selectors.py
```

o extender el selector existente si la arquitectura actual lo permite:

```python
DocumentoSelector.get_por_proyecto(
    empresa_id=empresa_id,
    proyecto_uuid=proyecto_uuid,
    facturable=False,
    solo_activos=True,
)
```

Filtros mínimos:

```text
empresa_id = tenant actual
proyecto_uuid = proyecto solicitado
facturable = False
activo = True
anulado = False
```

Orden recomendado:

```text
fecha DESC
created_at DESC
```

---

# 10. SCOPE ORGANIZACIONAL

La consulta de gastos debe respetar `OrganizationalScope` / reglas equivalentes del repositorio.

Un usuario con alcance limitado a una sede no debe poder ver gastos de un proyecto fuera de su alcance.

La regla debe aplicarse en backend.

Nunca confiar en ocultar filas solamente mediante JavaScript.

---

# 11. SERVICIO DE INTEGRACIÓN EN PROYECTOS

Crear una capa específica para lectura de gastos, por ejemplo:

```text
apps/tenant/proyectos/services/gastos_proyecto_service.py
```

Responsabilidades:

- obtener resumen de gastos no facturables;
- obtener listado operacional;
- respetar tenant y scope;
- normalizar respuesta para la UI;
- no crear ni modificar gastos.

Métodos conceptuales:

```python
get_gastos_no_facturables(proyecto)
get_resumen_gastos_no_facturables(proyecto)
```

No colocar consultas de Gastos directamente dentro del template ni del JavaScript.

---

# 12. ENDPOINT DE PROYECTO PARA LA FASE 3

Agregar una acción explícita al `ProyectoViewSet`, por ejemplo:

```text
GET /api/v1/proyectos/{uuid}/gastos-no-facturables/
```

Respuesta conceptual:

```json
{
  "visible": true,
  "count": 4,
  "total": 685000,
  "results": []
}
```

Cuando no existan gastos:

```json
{
  "visible": false,
  "count": 0,
  "total": 0,
  "results": []
}
```

Esto permite que el frontend cumpla exactamente la regla solicitada:

> Si el usuario no ha creado gastos no facturables asociados al proyecto desde Gastos, la sección no se muestra.

---

# 13. REGLA CLAVE DE PRESENTACIÓN

## No mostrar una tabla vacía de gastos

No hacer esto:

```text
GASTOS NO FACTURABLES
Sin registros
```

cuando el proyecto no tenga gastos.

La sección completa debe permanecer oculta.

Comportamiento:

```text
count = 0
    ↓
contenedor hidden

count > 0
    ↓
mostrar resumen + detalle
```

Esto mantiene la Fase 3 limpia.

---

# 14. NUEVA ESTRUCTURA VISUAL DE FASE 3

La estructura recomendada del formulario es:

```text
┌──────────────────────────────────────────────┐
│ 3. EJECUCIÓN                                 │
│ Responsable · estado · avance                │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ CONTROL DE TIEMPO                            │
│ Inicio | Fin estimada | Transcurrido | Falta │
│ Avance | Estado del cronograma               │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ CRONOGRAMA / PLAN DE TRABAJO                 │
│ archivo + periodo + indicadores              │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ SEGUIMIENTO DE TAREAS DIARIAS                │
│ filtros · resumen · timeline                  │
│ tareas pendientes / proceso / completas      │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ GASTOS NO FACTURABLES                        │
│ visible solo si existen                      │
│ cantidad · total · últimos gastos             │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ RECURSOS OPERATIVOS                          │
│ equipo asignado · pedidos                    │
│ (bloque secundario)                          │
└──────────────────────────────────────────────┘
```

---

# 15. ELIMINAR `VALOR DEL CONTRATO (BASE)` DE FASE 3

Eliminar de la plantilla de Fase 3:

```text
fin-valor-contrato
fin-costo-personal
fin-costo-materiales
fin-costo-total
fin-utilidad-neta
fin-margen-rentabilidad
```

y la tarjeta:

```text
Valor del Contrato (base)
```

## Importante

Esto es una modificación de presentación y de responsabilidad de la Fase 3.

**No eliminar todavía del modelo `Proyecto`:**

```text
valor_contrato_proyectado
costo_mano_obra_real
costo_materiales_real
utilidad_estimada
margen_rentabilidad
```

Esos datos pueden seguir siendo utilizados por otros procesos o fases.

Tampoco eliminar `calcular_indicadores_financieros()` en esta misión.

Simplemente dejar de cargar ese bloque como parte del formulario de Ejecución.

---

# 16. NUEVO BLOQUE: CONTROL DE TIEMPO

Crear una tarjeta compacta que use los datos existentes del Proyecto.

### Métricas

```text
Inicio real
Fecha fin estimada
Días planificados
Días transcurridos
Días restantes
% avance del proyecto
```

## Fórmulas

```text
Días planificados
= fecha_fin_estimada - fecha_inicio + 1
```

```text
Días transcurridos
= HOY - fecha_inicio + 1
```

con límites razonables para no mostrar valores negativos.

```text
Días restantes
= fecha_fin_estimada - HOY
```

## Estado de cronograma

Crear una clasificación operacional calculada:

```text
SIN FECHAS
EN FECHA
POR VENCER
ATRASADO
FINALIZADO
```

La clasificación debe vivir en el service/serializer, no en JavaScript.

---

# 17. AVANCE DE EJECUCIÓN

Utilizar `Proyecto.porcentaje_avance` como SSoT del avance general del proyecto.

Mostrar:

```text
Avance del proyecto
[██████████░░░░░] 68%
```

El porcentaje no debe duplicarse con otro campo dentro de Fase 3.

No crear `porcentaje_ejecucion` adicional.

---

# 18. MEJORA DE `Seguimiento de Tareas Diarias`

La sección actual v3.5.3 debe evolucionar de una lista simple a un verdadero panel de seguimiento.

## Nueva estructura

```text
Seguimiento de ejecución

[ Todas ] [ Pendientes ] [ En proceso ] [ Completadas ]

Resumen:
  12 tareas
  4 pendientes
  3 en proceso
  5 completadas

Avance de tareas: 41.7%

Timeline / Cronograma operativo
```

---

# 19. MEJORA DEL TIMELINE

La implementación actual agrupa únicamente por `fecha_inicio`.

Mejorar a un timeline operativo que muestre:

- periodo;
- duración en días;
- título;
- estado;
- prioridad;
- asignado;
- notas de progreso;
- indicador de tarea atrasada;
- acciones permitidas.

Ejemplo:

```text
01 OCT ─────────────────────────────────────

● Cableado principal
  01/10 → 03/10 · 3 días
  EN PROCESO
  Técnico: Juan Pérez
  [Cambiar estado]

● Instalación cámaras
  02/10 → 05/10 · 4 días
  PENDIENTE
  Prioridad ALTA
```

---

# 20. ESTADO DE TAREA SIN `prompt()`

Actualmente `mostrarMenuEstado()` usa:

```javascript
prompt(...)
```

Eliminar ese patrón.

Usar un control visual consistente con el resto del panel:

```text
Estado actual: EN PROCESO ▼

Pendiente
En Proceso
Completada
Cancelada
```

Puede ser:

- dropdown inline;
- menú contextual;
- offcanvas/modal pequeño.

Debe seguir utilizando:

```text
POST /cambiar-estado/
```

como SSoT de transición.

---

# 21. FILTROS DE TAREAS

Agregar como mínimo:

```text
Estado
Prioridad
Periodo
```

Los filtros visuales no deben duplicar la API existente.

Para volúmenes pequeños puede filtrarse el dataset ya cargado.

Si el volumen crece, evolucionar a filtros server-side sin cambiar el contrato de negocio.

---

# 22. CÁLCULO DEL AVANCE DE TAREAS

No agregar inicialmente un porcentaje independiente por tarea.

Para mantener la implementación simple, calcular el indicador como:

```text
tareas activas = todas excepto CANCELADA

avance_tareas = COMPLETADAS / tareas_activas * 100
```

Si no existen tareas activas:

```text
avance_tareas = 0%
```

El valor es un **indicador operativo**, no reemplaza `Proyecto.porcentaje_avance`.

---

# 23. DETECCIÓN DE TAREAS ATRASADAS

Una tarea se puede marcar visualmente como atrasada cuando:

```text
fecha_fin < HOY
AND estado != COMPLETADA
AND estado != CANCELADA
```

Ejemplo:

```text
⚠ ATRASADA · venció hace 2 días
```

El criterio debe concentrarse en el service/serializer para no duplicar reglas entre backend y frontend.

---

# 24. EDICIÓN DE TAREAS

La UI de Fase 3 debe permitir mantener las tareas sin salir del Proyecto.

Mantener:

- crear;
- cambiar estado;
- eliminar cuando esté permitido.

Mejorar además:

- edición de descripción;
- notas de progreso;
- prioridad;
- asignado;
- fechas.

La capa de negocio de `TareasDiariasBusinessService.actualizar_tarea()` ya existe y debe seguir siendo la SSoT.

No implementar un segundo `fetch + PATCH` con reglas duplicadas en JS.

---

# 25. NUEVO BLOQUE: GASTOS NO FACTURABLES

El bloque solo aparece cuando existan registros que cumplan:

```text
empresa_id = proyecto.empresa_id
proyecto_uuid = proyecto.uuid
facturable = false
activo = true
anulado = false
```

## Encabezado

```text
GASTOS NO FACTURABLES DEL PROYECTO
```

Subtítulo:

```text
Movimientos registrados desde Gastos
```

---

# 26. RESUMEN DE GASTOS

Mostrar como mínimo:

```text
4 gastos
$ 685.000
```

Opcionalmente:

```text
Último gasto: 01/10/2026
```

No mostrar utilidad, margen o valor del contrato en este bloque.

---

# 27. DETALLE DE GASTOS

Tabla o lista compacta:

| Fecha | Documento | Categoría | Proveedor | Descripción | Total |
|---|---|---|---|---|---:|
| 01/10/2026 | DS 0012 | Transporte | ABC | Transporte material | $238.000 |
| 30/09/2026 | DS 0011 | Viáticos | XYZ | Alimentación técnico | $120.000 |

El total debe venir del SSoT de Gastos.

No recalcular impuestos o retenciones en JavaScript.

---

# 28. GASTOS NO SE CREAN DESDE PROYECTOS

No agregar en Fase 3:

```text
+ Nuevo gasto
Editar gasto
Eliminar gasto
```

La pantalla de Proyecto será solamente de consulta.

El flujo correcto será:

```text
ADMIN → GASTOS
        ↓
Crear gasto
        ↓
Marcar no facturable
        ↓
Asignar proyecto
        ↓
Guardar
        ↓
PROYECTO → FASE 3
        ↓
Aparece automáticamente
```

---

# 29. ANULACIÓN O DESACTIVACIÓN DEL GASTO

La Fase 3 debe reflejar el estado actual del SSoT.

Si un gasto es:

```text
anulado = true
```

o:

```text
activo = false
```

debe dejar de aparecer en el conjunto operativo de gastos no facturables.

No crear procesos de sincronización manual.

---

# 30. CUANDO EL USUARIO CAMBIA EL PROYECTO DEL GASTO

Debe reflejarse naturalmente:

```text
Gasto
Proyecto A
   ↓ cambiar proyecto
Proyecto B

Fase 3 Proyecto A
→ deja de mostrarlo

Fase 3 Proyecto B
→ empieza a mostrarlo
```

Esto demuestra que Proyectos está leyendo el SSoT y no manteniendo una copia.

---

# 31. CUANDO EL USUARIO CAMBIA FACTURABILIDAD

Caso:

```text
Gasto no facturable
Proyecto X
```

aparece.

Si pasa a:

```text
Facturable = true
```

debe desaparecer de la Fase 3 en la siguiente consulta.

No borrar el gasto ni modificar el registro desde Proyectos.

---

# 32. FASE 3 NO DEBE MODIFICAR CONTABILIDAD

Esta misión no debe tocar:

- asientos contables;
- retenciones;
- impuestos;
- CxP;
- facturación;
- inventario;
- Kardex.

La integración de Gastos con Proyectos es de **seguimiento operacional y lectura**.

---

# 33. RESPONSABLE OPERATIVO

Mantener:

```text
Responsable Operativo (Nómina)
```

porque sí pertenece a la ejecución.

Sin embargo, mejorar su presentación:

```text
Responsable de Ejecución
[ Juan Pérez ]
```

y conservar el snapshot actual:

```text
responsable_operativo_id
responsable_operativo_nombre
```

No crear una segunda estructura de responsable.

---

# 34. EQUIPO Y PEDIDOS: PASAR A SEGUNDO NIVEL

Los bloques actuales:

- `Equipo de Trabajo Asignado`;
- `Solicitudes de Materiales / Pedidos`;

siguen siendo útiles en Ejecución.

No eliminarlos en esta misión.

Pero deben bajar de prioridad visual frente a:

1. tiempo;
2. cronograma;
3. tareas;
4. gastos no facturables.

Opcionalmente agruparlos bajo:

```text
Recursos operativos
```

como sección secundaria.

---

# 35. CRONOGRAMA / ARCHIVO DE PLAN DE TRABAJO

El campo existente:

```text
cronograma_archivo
```

debe visualizarse dentro del bloque de cronograma.

Presentación sugerida:

```text
CRONOGRAMA DEL PROYECTO

01 Oct 2026 → 15 Oct 2026

Estado: EN FECHA
Avance: 68%

[ Ver cronograma ]
```

No crear otro campo de archivo.

---

# 36. REFRESCO AUTOMÁTICO AL ABRIR FASE 3

Cada vez que se cargue el detalle del proyecto o se entre a Fase 3:

1. cargar Proyecto;
2. cargar tareas;
3. cargar gastos no facturables;
4. recalcular indicadores de tiempo en backend;
5. renderizar la sección.

No almacenar un snapshot de `total_gastos_no_facturables` en `Proyecto` salvo que en una fase posterior se demuestre una necesidad de performance.

Primera implementación: **pull en tiempo real**.

---

# 37. API FRONTEND

En:

```text
apps/tenant/proyectos/static/proyectos/js/proyectos.api.js
```

agregar un módulo semejante a:

```javascript
gastosNoFacturables: {
    list(proyectoUuid) {
        return w.Sintel.Core.Http.request(
            'GET',
            `${API_BASE}/${proyectoUuid}/gastos-no-facturables/`
        );
    }
}
```

No usar `fetch()` directo.

No crear headers ni manejo CSRF paralelo.

---

# 38. FRONTEND DE FASE 3

En:

```text
apps/tenant/proyectos/static/proyectos/js/features/proyectos_editor.js
```

dividir claramente la responsabilidad en módulos:

```text
ExecutionOverview
ExecutionTimeline
TareasDiarias
GastosNoFacturables
```

No crear un único método gigante que renderice toda la Fase 3.

---

# 39. MODELO DE RENDERIZADO RECOMENDADO

El flujo debe ser:

```text
populateStepDetails()
        │
        ├── renderExecutionOverview()
        ├── TareasDiarias.init()
        └── GastosNoFacturables.init()
```

Cada módulo debe ser independiente y reutilizable.

---

# 40. DATOS DERIVADOS DEL TIEMPO

Agregar al serializer de Proyecto o a un service de lectura:

```json
"ejecucion_tiempo": {
  "fecha_inicio": "2026-10-01",
  "fecha_fin_estimada": "2026-10-15",
  "dias_planificados": 15,
  "dias_transcurridos": 2,
  "dias_restantes": 13,
  "estado_cronograma": "EN_FECHA",
  "porcentaje_avance": 68
}
```

Esto evita que JS replique las mismas fórmulas.

---

# 41. DATOS DERIVADOS DE TAREAS

El endpoint de tareas puede mantener la lista actual y agregar en el resumen:

```json
{
  "total": 12,
  "pendientes": 4,
  "en_proceso": 3,
  "completadas": 5,
  "canceladas": 0,
  "atrasadas": 2,
  "avance": 41.67
}
```

La UI utilizará esos indicadores directamente.

Esto evita recalcular reglas de negocio en múltiples componentes.

---

# 42. DATOS DERIVADOS DE GASTOS

El bloque puede devolver:

```json
{
  "visible": true,
  "count": 4,
  "total": 685000,
  "ultimo_gasto_fecha": "2026-10-01",
  "results": []
}
```

No guardar un total duplicado en `Proyecto`.

---

# 43. SEGURIDAD Y DSV

Todas las lecturas y modificaciones deben cumplir:

```text
Tenant → Empresa
Scope → OrganizationalScope
Identificador público → UUID
```

No aceptar `empresa_id` desde el frontend para decidir el tenant.

El backend debe obtener la empresa desde el contexto del tenant.

---

# 44. MIGRACIÓN DE GASTOS EXISTENTES

Como `DocumentoSoporte` no tiene actualmente relación con Proyecto, no debe inventarse una asociación histórica.

Migración recomendada:

```text
proyecto_uuid = NULL
proyecto_nombre = ''
```

para registros existentes, salvo que exista una fuente confiable de correspondencia.

La asignación histórica puede hacerse después como tarea administrativa separada.

---

# 45. COMPATIBILIDAD CON DATOS EXISTENTES DE PROYECTOS

No eliminar:

```text
valor_contrato_proyectado
costo_mano_obra_real
costo_materiales_real
utilidad_estimada
margen_rentabilidad
```

No eliminar métodos financieros en esta misión.

Solo se retira su dependencia visual de Fase 3.

---

# 46. NO MODIFICAR FASE 2 EN ESTA MISIÓN

La lógica de:

```text
Cotización → recursos → presupuesto planeado
```

del plan de Fase 2 anterior queda intacta.

La separación será:

```text
FASE 2
Qué planeamos gastar / recursos previstos

FASE 3
Qué está pasando realmente durante la ejecución
```

---

# 47. NO MEZCLAR GASTO NO FACTURABLE CON COSTO PLANEADO

No actualizar automáticamente:

```text
ItemPresupuestoProyecto
costo_planeado_total
utilidad_planeada
margen_planeado
```

cuando aparezca un gasto real.

Los gastos no facturables pertenecen al seguimiento real de ejecución, no al presupuesto planeado.

---

# 48. NO ACTUALIZAR `porcentaje_avance` AUTOMÁTICAMENTE DESDE TAREAS

En esta misión no hacer:

```text
5 tareas completas → modificar automáticamente Proyecto.porcentaje_avance
```

Porque `porcentaje_avance` puede ser un avance global del proyecto y no necesariamente equivalente al avance de tareas.

Mostrar ambos conceptos por separado:

```text
Avance del Proyecto: 68%
Avance de Tareas: 42%
```

Esto evita alterar la semántica actual del campo.

---

# 49. ESTRUCTURA FINAL PROPUESTA DEL FORMULARIO

## Fase 3: Ejecución

### A. Cabecera operativa

```text
Responsable de Ejecución
Estado del proyecto
Avance del proyecto
```

### B. Control de tiempo

```text
Fecha inicio
Fecha fin estimada
Días planificados
Días transcurridos
Días restantes
Estado cronograma
```

### C. Cronograma

```text
Archivo / plan de trabajo
Periodo
```

### D. Seguimiento de tareas

```text
Filtros
Resumen
Avance de tareas
Timeline
Tareas atrasadas
```

### E. Gastos no facturables

```text
visible solo cuando existan
cantidad
total
últimos movimientos
```

### F. Recursos operativos

```text
Equipo
Pedidos / solicitudes
```

---

# 50. ARCHIVOS PRINCIPALES A MODIFICAR

## Proyectos

```text
apps/tenant/proyectos/models.py
apps/tenant/proyectos/services/business_service.py
apps/tenant/proyectos/services/tareas_service.py
apps/tenant/proyectos/services/selectors.py
apps/tenant/proyectos/api/serializers.py
apps/tenant/proyectos/api/viewsets.py
apps/tenant/proyectos/api/urls.py
apps/tenant/proyectos/templates/tenant/proyectos/offcanvas_form.html
apps/tenant/proyectos/static/proyectos/js/proyectos.api.js
apps/tenant/proyectos/static/proyectos/js/features/proyectos_editor.js
```

## Gastos

```text
apps/tenant/gastos/models.py
apps/tenant/gastos/services/business_service.py
apps/tenant/gastos/services/selectors.py
apps/tenant/gastos/api/serializers.py
apps/tenant/gastos/api/viewsets.py
apps/tenant/gastos/api/urls.py
apps/tenant/gastos/templates/tenant/gastos/offcanvas_crear_gasto.html
apps/tenant/gastos/templates/tenant/gastos/offcanvas_editar_gasto.html
```

Agregar migraciones de cada app según corresponda.

---

# 51. FASES DE IMPLEMENTACIÓN

## FASE 0 — Línea base

- Revisar estado actual de `main`.
- Confirmar contratos de APIs.
- Identificar serializers y ViewSets afectados.
- Confirmar reglas de `OrganizationalScope`.
- No cambiar UI todavía.

### Resultado

Mapa técnico de la implementación.

---

## FASE 1 — Capacidad de Gastos → Proyecto

Implementar:

- `proyecto_uuid`;
- `proyecto_nombre`;
- `facturable`;
- migración;
- DSV;
- selector;
- serializer;
- API.

### Resultado

Desde Gastos ya es posible registrar formalmente:

```text
Gasto
→ No facturable
→ Proyecto X
```

---

## FASE 2 — UI de Gastos

Modificar formularios de crear/editar:

- selector de Proyecto;
- búsqueda dinámica;
- checkbox facturable;
- precarga del proyecto existente;
- limpieza correcta al cambiar proyecto;
- feedback de validación.

### Resultado

El usuario registra el gasto desde la aplicación correcta.

---

## FASE 3 — API de consulta de gastos desde Proyectos

Crear:

```text
GET /api/v1/proyectos/{uuid}/gastos-no-facturables/
```

o adaptar el diseño final al patrón de rutas vigente.

Implementar:

- selector;
- scope;
- agregaciones;
- ordenamiento;
- filtros activos/no anulados.

### Resultado

Proyectos puede consultar el SSoT de Gastos sin copiar registros.

---

## FASE 4 — Rediseño visual de Ejecución

Eliminar del formulario:

```text
Valor del Contrato (base)
Costos reales
Utilidad
Margen
```

Agregar:

```text
Control de tiempo
Estado cronograma
Avance
```

---

## FASE 5 — Mejora Tareas Diarias

Implementar:

- nuevo resumen;
- filtros;
- timeline mejorado;
- duración;
- atrasadas;
- avance de tareas;
- cambio de estado sin `prompt()`;
- notas de progreso;
- edición consistente.

---

## FASE 6 — Bloque de Gastos no Facturables

Implementar:

- carga automática al abrir Fase 3;
- resumen;
- tabla/lista;
- ocultamiento cuando `count = 0`;
- formato COP;
- enlace de navegación a Gastos si existe patrón de navegación del panel.

---

## FASE 7 — Integración final

Verificar que:

```text
Gastos crea
      ↓
Proyecto recibe automáticamente
      ↓
Sin copiar
      ↓
Sin botón manual
```

Verificar también el flujo inverso al cambiar:

- proyecto;
- facturabilidad;
- anulación;
- activación/desactivación.

---

# 52. PRUEBAS BACKEND

Crear pruebas para:

## Gastos

- crea gasto con proyecto válido;
- rechaza proyecto de otro tenant;
- valida scope;
- guarda `facturable`;
- permite actualizar proyecto;
- permite retirar proyecto;
- mantiene DSV.

## Selector de gastos

- filtra por empresa;
- filtra por proyecto;
- excluye facturables;
- excluye anulados;
- excluye inactivos;
- suma correctamente `total`.

## Proyectos

- endpoint de gastos funciona;
- proyecto sin gastos devuelve `visible=false`;
- proyecto con gastos devuelve `visible=true`;
- scope se respeta;
- otro tenant no puede acceder.

## Tareas

- mantiene validaciones existentes;
- conserva bloqueo de CIERRE;
- cálculo de atrasadas correcto;
- resumen correcto.

---

# 53. PRUEBAS DE MIGRACIÓN

Verificar:

```text
migrate → OK
makemigrations --check → OK
```

Y revisar que los gastos existentes no hayan recibido asociaciones ficticias a proyectos.

---

# 54. PRUEBAS FRONTEND

Verificar que no queden referencias activas a:

```text
fin-valor-contrato
fin-costo-personal
fin-costo-materiales
fin-costo-total
fin-utilidad-neta
fin-margen-rentabilidad
```

dentro de la Fase 3 después del rediseño.

Comprobar que el JavaScript no haga `fetch()` directo fuera de `Sintel.Core.Http`.

---

# 55. PRUEBAS MANUALES E2E — EN ESTE ORDEN

## Caso 1 — Proyecto sin gastos

1. Abrir Proyecto.
2. Ir a Fase 3.
3. Confirmar que el bloque `Gastos No Facturables` no aparece.

## Caso 2 — Crear gasto no facturable sin proyecto

1. Ir a Gastos.
2. Crear gasto.
3. Facturable = No.
4. Proyecto = vacío.
5. Guardar.
6. Abrir Proyecto.
7. Confirmar que no aparece.

## Caso 3 — Crear gasto no facturable asociado al proyecto

1. Ir a Gastos.
2. Crear gasto.
3. Facturable = No.
4. Seleccionar Proyecto X.
5. Guardar.
6. Abrir Proyecto X.
7. Ir a Fase 3.
8. Confirmar aparición automática.

## Caso 4 — Proyecto incorrecto

1. Editar gasto.
2. Cambiar Proyecto X → Proyecto Y.
3. Guardar.
4. Abrir X.
5. Confirmar que desapareció.
6. Abrir Y.
7. Confirmar que apareció.

## Caso 5 — Cambiar facturabilidad

1. Gasto no facturable asociado a X.
2. Cambiar a facturable.
3. Guardar.
4. Fase 3 de X.
5. Confirmar que desaparece.

## Caso 6 — Anular gasto

1. Anular gasto.
2. Abrir Proyecto.
3. Confirmar que no aparece en el bloque operativo.

## Caso 7 — Cronograma

Confirmar:

- inicio;
- fin estimado;
- días transcurridos;
- días restantes;
- estado de cronograma;
- avance.

## Caso 8 — Tareas

Crear:

- pendiente;
- en proceso;
- completada;
- atrasada.

Confirmar que los contadores y timeline se actualizan correctamente.

## Caso 9 — Cierre

1. Pasar proyecto a `CIERRE`.
2. Verificar que las tareas mantienen el bloqueo existente.
3. Verificar que los gastos siguen siendo de solo lectura desde Proyectos.

---

# 56. CRITERIOS DE ACEPTACIÓN

La misión se considera terminada cuando:

### Gastos

- [ ] Gastos permite asociar opcionalmente un proyecto.
- [ ] Gastos permite marcar facturable/no facturable.
- [ ] Backend valida tenant y scope.
- [ ] No se crean copias de gastos en Proyectos.

### Fase 3

- [ ] Ya no muestra `Valor del Contrato (base)`.
- [ ] Ya no muestra utilidad/margen como bloque principal.
- [ ] La primera información visible es avance y tiempo.
- [ ] Existe control de cronograma.
- [ ] Las tareas tienen mejor seguimiento visual.
- [ ] Se identifican tareas atrasadas.
- [ ] Se muestran pendientes / proceso / completadas.
- [ ] Los gastos no facturables aparecen automáticamente cuando existen.
- [ ] La sección de gastos permanece oculta cuando no existen.
- [ ] Los gastos vienen directamente de Gastos.
- [ ] No existe entrada manual de gastos en Proyecto.
- [ ] Un cambio en Gastos se refleja en el siguiente refresh de Proyecto.

### Arquitectura

- [ ] No hay señales para sincronización de gastos.
- [ ] No hay lógica duplicada de negocio en JS.
- [ ] `Sintel.Core.Http` es el cliente HTTP del frontend.
- [ ] Se conserva DSV.
- [ ] Se conserva OrganizationalScope.
- [ ] UUID sigue siendo el identificador público.
- [ ] Los modelos financieros existentes no se eliminan de esta misión.
- [ ] La separación Planeación/Ejecución queda clara.

---

# 57. RESULTADO OPERATIVO ESPERADO

Al finalizar, la Fase 3 debe sentirse como una pantalla de **control de obra/proyecto**, no como una segunda pantalla contable.

El flujo final será:

```text
                 PROYECTO
                    │
          ┌─────────┴─────────┐
          │                   │
       PLANEACIÓN         EJECUCIÓN
          │                   │
   Recursos previstos    ¿Qué está pasando?
   Costos planeados      ├─ Avance
   Cotización            ├─ Tiempo
                         ├─ Cronograma
                         ├─ Tareas
                         └─ Gastos no facturables
                                  │
                                  ▼
                               GASTOS
                         SSoT del gasto real
```

La idea central de esta fase queda resumida así:

> **Planeación define lo previsto. Ejecución muestra lo que realmente está ocurriendo.**

---

# 58. ORDEN RECOMENDADO PARA EL AGENTE DE CODIFICACIÓN

Ejecutar exactamente en este orden:

```text
1. Auditar Gastos actual
2. Agregar referencia de proyecto
3. Agregar facturabilidad
4. Migración segura
5. Business Service + Selector Gastos
6. API Gastos
7. UI Gastos
8. Selector/Service de gastos para Proyectos
9. API Proyectos
10. Rediseñar Fase 3
11. Mejorar Tareas Diarias
12. Integrar Gastos No Facturables
13. Limpiar JS/IDs financieros de Fase 3
14. Tests backend
15. Tests de migración
16. Verificación estática
17. Prueba manual UI/E2E al final
```

No adelantar la fase de pruebas manuales antes de completar la integración backend + frontend.

---

# 59. RESTRICCIONES DE IMPLEMENTACIÓN

No hacer dentro de esta misión:

```text
❌ Crear ProyectoGasto como duplicado
❌ Copiar gastos a Proyecto
❌ Crear signals para sincronizar
❌ Calcular contabilidad en JavaScript
❌ Crear otro sistema de tareas
❌ Crear otro porcentaje global de proyecto
❌ Eliminar campos financieros del modelo sin análisis de dependencias
❌ Modificar contabilidad
❌ Modificar facturación
❌ Modificar CxP
❌ Modificar inventario/Kardex
```

Sí hacer:

```text
✅ Pull model desde Gastos
✅ Selector SSoT
✅ DSV
✅ OrganizationalScope
✅ UUID
✅ Service Layer
✅ API explícita
✅ UI enfocada en ejecución
✅ Gastos ocultos si no existen
```

---

# 60. CONCLUSIÓN

La mejora no consiste en agregar más campos a la Fase 3, sino en cambiar su propósito.

La Fase 3 debe convertirse en el panel operativo del proyecto:

```text
TIEMPO
  +
CRONOGRAMA
  +
TAREAS
  +
AVANCE
  +
GASTOS NO FACTURABLES REALES
```

La información financiera comercial queda en las fases donde corresponde, mientras que los gastos reales se consultan directamente desde Gastos y aparecen en Proyecto solo cuando el usuario realmente los haya asociado a ese proyecto.

**Esta es la arquitectura recomendada para implementar la Fase 3 sin duplicar dominio ni introducir una segunda fuente de verdad.**
