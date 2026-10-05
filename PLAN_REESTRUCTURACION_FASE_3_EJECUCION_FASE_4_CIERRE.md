# PLAN DE ACCIÓN
# REESTRUCTURACIÓN DE FASE 3 EJECUCIÓN Y FASE 4 CIERRE

**Repositorio:** `steven-zdt/CRM_SINTEL`  
**Rama auditada:** `main`  
**Módulo:** `apps/tenant/proyectos`  
**Fecha:** 2026-10-05  
**Documento base:** `AUDITORIA_FLUJO_COMPLETO(8).md`  
**Estado:** propuesta de implementación incremental

---

## 1. OBJETIVO

Reordenar el ciclo funcional para que cada fase tenga una responsabilidad inequívoca:

```text
0. BORRADOR
   Definición inicial de la oportunidad

1. INICIO
   Comercial + contractual + viabilidad + aprobación

2. PLANEACIÓN
   Diseño + recursos + presupuesto + cronograma

3. EJECUCIÓN
   Avance + estado + tareas + tiempos + gastos

4. CIERRE
   Consolidado final + rentabilidad + tiempos + documentos
```

La frontera clave será:

```text
FASE 3 = el proyecto todavía se está ejecutando.
FASE 4 = el proyecto ya terminó y se formaliza el resultado.
```

---

## 2. VALIDACIÓN DE LA AUDITORÍA ADJUNTA

La auditoría adjunta documenta históricamente la máquina de fases, los bloqueos de CIERRE, Presupuesto, Tareas y la evolución de Fase 3. También registra como diseño que Cierre fuese principalmente un informe y que Ejecución manejara tiempo, tareas y gastos.

Sin embargo, el `main` actual revisado todavía conserva dentro del template de Cierre los campos:

```text
Configuración de Cierre
Porcentaje de Avance
Estado de la Tarea
Fecha de Cierre Real
Acta de Entrega
Informe Final
```

Además, la auditoría histórica describe `porcentaje_avance` y `estado_tarea` como campos permitidos en CIERRE. Por tanto, esta misión corrige esa responsabilidad funcional y debe tomar `main` como fuente técnica real, usando la auditoría como antecedente. fileciteturn430file0L248-L312 fileciteturn430file4L715-L768

---

# 3. DISEÑO FUNCIONAL DEFINITIVO

## 3.1 Fase 0 — Borrador

Se mantiene esencialmente como está.

## 3.2 Fase 1 — Inicio

Queda orientada a:

- responsables;
- contratista/proveedor;
- valor real vendido;
- facturas de venta;
- cotizaciones de costo;
- inversiones;
- viabilidad;
- aprobación administrativa.

El acceso a Planeación queda condicionado a la aprobación definida en el plan anterior.

## 3.3 Fase 2 — Planeación

Queda orientada a:

- diseño;
- recursos;
- cotización comercial;
- presupuesto planeado;
- cronograma.

## 3.4 Fase 3 — Ejecución

Queda orientada exclusivamente a:

- porcentaje de avance;
- estado operativo global;
- tareas;
- seguimiento temporal;
- adelanto/retraso;
- equipo operativo;
- pedidos/recursos;
- gastos no facturables automáticos.

## 3.5 Fase 4 — Cierre

Queda orientada exclusivamente a:

- consolidar lo ocurrido;
- presentar rentabilidad final;
- presentar tiempos;
- presentar tareas;
- presentar gastos;
- presentar desglose administrativo;
- adjuntar documentación final;
- formalizar el cierre.

---

# 4. MIGRAR PORCENTAJE DE AVANCE A FASE 3

El campo existente:

```text
Proyecto.porcentaje_avance
```

permanece en el modelo, pero su responsabilidad funcional se mueve a Fase 3.

### En Ejecución

```text
Porcentaje de avance
0% ───────────── 100%
```

Debe poder actualizarse mientras el proyecto está en ejecución, según permisos y las reglas existentes.

### En Cierre

Debe mostrarse solamente como resultado final:

```text
100%
```

o el valor final aceptado por la política del negocio, siempre como `read-only`.

---

# 5. MIGRAR ESTADO DE LA TAREA A FASE 3

El campo existente:

```text
Proyecto.estado_tarea
```

pasa funcionalmente a Ejecución.

Valores actuales:

```text
PENDIENTE
EN_PROCESO
DETENIDO
COMPLETADO
```

No debe volver a aparecer como selector operativo en Cierre.

---

# 6. DIFERENCIA ENTRE ESTADO DEL PROYECTO Y ESTADO DE CADA TAREA

Mantener dos niveles:

```text
Proyecto.estado_tarea
    = estado operativo global

TareaDiariaProyecto.estado
    = estado de una tarea individual
```

No reutilizar uno para reemplazar el otro.

---

# 7. SEMÁNTICA DEL ESTADO GLOBAL

Propuesta:

```text
PENDIENTE   → ejecución aún no iniciada
EN_PROCESO  → ejecución activa
DETENIDO    → ejecución bloqueada temporalmente
COMPLETADO  → ejecución operativa terminada
```

La transición a Cierre no debe aceptar un estado operativo incompatible con proyecto terminado.

---

# 8. FASE 3: CONTROL DE AVANCE

El bloque superior debe responder inmediatamente:

```text
¿Cuánto del proyecto está ejecutado?
```

Mostrar:

```text
% avance
Estado
Fecha de actualización
```

La fuente de verdad es backend. JavaScript solo representa el valor recibido.

---

# 9. FASE 3: CONTROL DE TIEMPO

Mantener el cálculo derivado desde las fechas existentes:

```text
fecha_inicio
fecha_fin_estimada
hoy
fecha_cierre_real
```

Mostrar:

```text
Días planificados
Días transcurridos
Días restantes
Estado cronograma
```

No crear campos redundantes si el dato se puede derivar.

---

# 10. ESTADO DEL CRONOGRAMA

Valores derivados:

```text
SIN_FECHAS
EN_FECHA
POR_VENCER
ATRASADO
FINALIZADO
```

La regla debe residir en Service Layer, no en JS.

---

# 11. ADELANTO / RETRASO

La Fase 3 debe mostrar una lectura explícita:

```text
En fecha
Adelantado 3 días
Retrasado 5 días
```

El valor debe derivarse, no almacenarse manualmente como otro contador.

---

# 12. TAREAS DIARIAS: PAPEL EN EJECUCIÓN

`TareaDiariaProyecto` ya existe y contiene:

- periodo;
- título;
- descripción;
- estado;
- prioridad;
- asignación;
- notas de progreso.

Debe mantenerse como la herramienta operativa central de seguimiento diario.

---

# 13. TAREAS: AVANCE DE EJECUCIÓN

En Fase 3 mostrar:

```text
Total tareas
Pendientes
En proceso
Completadas
Canceladas
Atrasadas
% completitud
```

La métrica de avance de tareas es complementaria y no debe reemplazar `Proyecto.porcentaje_avance`.

---

# 14. TAREAS ATRASADAS

Usar una sola regla SSoT:

```text
fecha_fin < hoy
AND
estado NOT IN (COMPLETADA, CANCELADA)
```

El backend calcula:

```text
atrasada
 días_atraso
```

El frontend solamente pinta el resultado.

---

# 15. GASTOS NO FACTURABLES

En Fase 3 debe mantenerse la integración automática con Gastos:

```text
Gasto asignado al proyecto
AND
No Facturable
        ↓
aparece automáticamente en Ejecución
```

No debe existir captura manual del gasto desde Proyectos.

La app Gastos sigue siendo SSoT del gasto.

---

# 16. NO DUPLICAR GASTOS

No crear una copia de cada gasto dentro de Proyectos.

Proyectos debe consultar y resumir:

```text
cantidad de gastos
monto total
monto por categoría
```

mediante Pull Model.

---

# 17. FASE 3: BLOQUE ECONÓMICO

Eliminar del bloque principal de Ejecución:

```text
Valor del Contrato
Utilidad
Margen
```

Ese análisis pertenece al contexto económico y al consolidado final.

La Fase 3 debe enfocarse en ejecutar.

---

# 18. FASE 3: RESPONSABLE OPERATIVO

Mantener el concepto:

```text
Responsable Operativo
```

en Fase 3.

No mezclarlo con:

```text
Supervisor de Fase 1
Responsable Técnico de Fase 2
Responsable Administrativo de Fase 4
```

---

# 19. FASE 3: ESTRUCTURA DE UI RECOMENDADA

```text
FASE 3 — EJECUCIÓN

[ Avance 68% ] [ EN PROCESO ]

CONTROL DE TIEMPO
Inicio | Fin estimada | Transcurridos | Restantes
Estado: ATRASADO 4 días

TAREAS DEL PROYECTO
[Estado] [Prioridad] [Periodo]

Completadas  14
En proceso    3
Pendientes    2
Atrasadas     1

EQUIPO OPERATIVO
...

PEDIDOS / RECURSOS
...

GASTOS NO FACTURABLES
Total: $...
...

[ Guardar ]
[ Finalizar Ejecución ]
```

---

# 20. NUEVA SEMÁNTICA PARA “FINALIZAR EJECUCIÓN”

La acción no debe llamarse simplemente “Avanzar fase” en términos de negocio.

Recomendación de UX:

```text
[ Finalizar Ejecución y preparar Cierre ]
```

El backend ejecuta una validación completa.

---

# 21. TRANSICIÓN EJECUCIÓN → CIERRE

Debe ser una acción de dominio explícita.

No debe ser un `PATCH` genérico.

Conceptualmente:

```text
POST /api/v1/proyectos/{uuid}/cerrar/
```

o una acción equivalente según las convenciones actuales del módulo.

---

# 22. PRECONDICIONES DE CIERRE

La transición debe validar, como mínimo:

```text
fase_actual == EJECUCION
```

```text
estado_tarea == COMPLETADO
```

```text
porcentaje_avance >= 100
```

```text
acta_entrega presente
```

```text
informe_final presente
```

y debe verificar las reglas finales de tareas definidas por negocio.

---

# 23. TAREAS ABIERTAS

Recomendación inicial:

Si existen tareas:

```text
PENDIENTE
EN_PROCESO
```

bloquear el cierre.

Mensaje:

```text
No se puede cerrar el proyecto porque existen tareas pendientes de finalizar.
```

Si se desea permitir excepciones, deben existir como acción administrativa explícita, no como bypass del CRUD.

---

# 24. ESTADO FINAL COHERENTE

Al completar la transición a Cierre, el estado global debe quedar coherente:

```text
fase_actual = CIERRE
estado_tarea = COMPLETADO
porcentaje_avance = 100
```

La actualización debe ser transaccional.

---

# 25. FECHA DE CIERRE REAL

`fecha_cierre_real` debe representar el momento final del proyecto.

Recomendación:

```text
se asigna al confirmar el cierre
```

La fecha no debe ser utilizada como campo libre para falsificar la transición.

Si requiere corrección posterior, debe existir permiso administrativo y auditoría.

---

# 26. FASE 4 DEJA DE SER UN FORMULARIO OPERATIVO

Eliminar del bloque actual:

```text
Configuración de Cierre
Porcentaje de Avance editable
Estado de la Tarea editable
```

Reemplazar por:

```text
Resumen Final del Proyecto
```

más:

```text
Documentación Final
Desglose Administrativo
```

---

# 27. CIERRE COMO CONSOLIDADO

Fase 4 debe consumir datos de todas las fases anteriores.

```text
FASE 1 → venta + viabilidad + aprobación
FASE 2 → cotización + presupuesto + recursos + cronograma
FASE 3 → avance + tareas + tiempos + gastos
```

Cierre solamente consolida.

---

# 28. RESUMEN EJECUTIVO FINAL

Mostrar:

```text
Proyecto
Código
Cliente
Supervisor
Contratista
Fecha Inicio
Fecha Fin Estimada
Fecha Cierre Real
Estado Final
```

Read-only.

---

# 29. RESUMEN DE FASE 1

Mostrar:

```text
Estado de aprobación
Valor real vendido
Facturas de venta
Costos cotizados
Inversiones iniciales
Viabilidad
```

No permitir edición desde Cierre.

---

# 30. RESUMEN DE FASE 2

Mostrar:

```text
Cotización comercial asociada
Presupuesto planeado
Mano de Obra
Materiales
Equipos
Recursos/pedidos
Cronograma
```

Todos como datos consolidados.

---

# 31. RESUMEN DE FASE 3

Mostrar:

```text
Avance final
Estado final
Tareas
Tareas completadas
Tareas atrasadas
Tiempo real
Adelanto/retraso
Gastos no facturables
Equipo operativo
```

---

# 32. RESUMEN DE TIEMPO EN CIERRE

Debe mostrar:

```text
Fecha inicio
Fecha fin planificada
Fecha cierre real
Duración planificada
Duración real
Variación
```

Resultado:

```text
A tiempo
Adelantado X días
Retrasado X días
```

---

# 33. RESUMEN DE TAREAS EN CIERRE

Mostrar como consolidado:

```text
Total
Completadas
Canceladas
Pendientes históricas
Atrasadas
% completitud
```

No debe existir:

```text
Agregar tarea
Eliminar tarea
Cambiar estado
```

---

# 34. RESUMEN DE GASTOS EN CIERRE

Mostrar automáticamente:

```text
Gastos no facturables
Cantidad
Total
Desglose por categoría
```

La fuente sigue siendo Gastos.

---

# 35. RENTABILIDAD FINAL

La rentabilidad debe ser una salida calculada del consolidado.

Mostrar, según las SSoT económicas definidas en Fase 1:

```text
Valor vendido
Costo planeado
Costo real
Gastos no facturables
Resultado
Margen %
```

No permitir editar ninguno de estos valores desde Cierre.

---

# 36. NO USAR JAVASCRIPT COMO MOTOR FINANCIERO

El backend debe devolver el resumen económico.

El frontend solo representa:

```json
{
  "valor_vendido": 0,
  "costo_planeado": 0,
  "costo_real": 0,
  "gastos_no_facturables": 0,
  "resultado": 0,
  "margen": 0
}
```

No duplicar las fórmulas en JS.

---

# 37. DESGLOSE ADMINISTRATIVO

Crear una sección de consulta:

```text
DESGLOSE ADMINISTRATIVO

Facturas de venta
Compras / Órdenes de compra
Cotizaciones
Presupuesto
Inversiones
Gastos
Documentos
```

Debe mostrar enlaces/contadores/resúmenes, no convertirse en otra pantalla de edición.

---

# 38. DOCUMENTOS OBLIGATORIOS

Para cerrar el proyecto deben existir obligatoriamente:

```text
Acta de Entrega
Informe Final del Proyecto
```

Si falta cualquiera:

```text
Cierre bloqueado
```

---

# 39. DOCUMENTOS ADICIONALES

Mantener disponibles:

```text
Contrato
Acta de Inicio
Cronograma
Otros documentos
```

No convertirlos automáticamente en obligatorios sin definición de negocio.

---

# 40. CIERRE READ-ONLY

Al estar en:

```text
fase_actual == CIERRE
```

no permitir cambios operativos sobre:

```text
Cliente
Proveedor
Cotización
Presupuesto
Asignaciones
Pedidos
Tareas
Gastos
Porcentaje de avance
Estado operativo
```

Las únicas modificaciones deben ser las administrativas explícitamente autorizadas para documentación de cierre.

---

# 41. NO PERMITIR CAMBIOS DE ESTADO POR PATCH

No aceptar:

```http
PATCH /proyectos/{uuid}/
{
  "fase_actual": "CIERRE",
  "estado_tarea": "COMPLETADO"
}
```

Las transiciones son comandos de dominio.

---

# 42. SERVICIO SSoT DE WORKFLOW

La lógica debe centralizarse en un servicio de workflow de Proyectos, por ejemplo:

```text
ProyectoWorkflowService
```

o integrarse en la estructura existente de `business_service.py` si esa es la convención final.

Debe concentrar:

```text
validar_transicion()
puede_ir_a_planeacion()
puede_ir_a_ejecucion()
puede_cerrar()
finalizar_ejecucion()
confirmar_cierre()
```

---

# 43. MATRIZ DEFINITIVA DE TRANSICIONES

| Desde | Hacia | Regla |
|---|---|---|
| BORRADOR | INICIO | condiciones de Inicio |
| INICIO | PLANEACION | aprobación administrativa válida |
| PLANEACION | EJECUCION | Planeación válida |
| EJECUCION | CIERRE | ejecución completa + documentos |
| CIERRE | cualquiera | bloqueado por defecto |

No permitir saltos.

---

# 44. REGLA DE CIERRE EN BACKEND

La validación conceptual será:

```python
if proyecto.fase_actual != "EJECUCION":
    reject()

if proyecto.estado_tarea != "COMPLETADO":
    reject()

if proyecto.porcentaje_avance < 100:
    reject()

if not proyecto.acta_entrega_archivo:
    reject()

if not proyecto.informe_final_archivo:
    reject()
```

Este bloque es conceptual y debe implementarse dentro del Service Layer, no pegarse literalmente al ViewSet.

---

# 45. API DE RESUMEN DE CIERRE

Agregar un endpoint de lectura especializado, por ejemplo:

```http
GET /api/v1/proyectos/{uuid}/cierre/
```

La respuesta debe consolidar:

```text
proyecto
inicio
planeacion
ejecucion
tiempo
tareas
gastos
rentabilidad
administrativo
documentos
bloqueos
```

Esto evita que el navegador arme el cierre con múltiples consultas independientes.

---

# 46. API DE CIERRE

Crear una acción dedicada:

```http
POST /api/v1/proyectos/{uuid}/cerrar/
```

Debe:

1. verificar tenant;
2. verificar scope;
3. validar permisos;
4. validar fase;
5. validar estado;
6. validar avance;
7. validar tareas;
8. validar documentos;
9. establecer fecha de cierre;
10. persistir la transición en una transacción.

---

# 47. PERMISOS

La transición final debe exigir los permisos definidos para cerrar proyectos.

Recomendación inicial:

```text
ADMIN
```

o el rol administrativo que SINTEL defina posteriormente.

No confiar en que el botón esté oculto.

---

# 48. SEGURIDAD MULTITENANT

Toda consulta y comando debe validar:

```text
empresa_id
UUID
OrganizationalScope
permisos
```

No aceptar objetos de otro tenant aunque el UUID sea conocido.

---

# 49. REAPERTURA

Por defecto:

```text
CIERRE → EJECUCION
```

debe estar bloqueado.

Si negocio requiere reapertura, implementar después como comando extraordinario:

```text
reabrir_proyecto
```

con:

- ADMIN;
- motivo obligatorio;
- auditoría;
- nueva transición controlada.

No utilizar PATCH genérico.

---

# 50. CAMBIO DE FRONTEND

## En Step 3

Mover:

```text
#proyecto-porcentaje-avance
#porcentaje-avance-display
#proyecto-estado-tarea
```

## En Step 4

Eliminar esos inputs.

Mostrarlos únicamente como indicadores read-only.

---

# 51. CAMBIO DE `renderStepLocks()`

Actualmente el frontend determina bloqueo principalmente por posición del índice de fase.

La nueva lógica debe combinar:

```text
fase_actual
+
capacidades de transición devueltas por backend
+
motivos de bloqueo
```

Ejemplo:

```json
{
  "fase_actual": "EJECUCION",
  "puede_cerrar": false,
  "bloqueos_cierre": [
    "Falta Acta de Entrega",
    "Falta Informe Final"
  ]
}
```

El frontend no calcula las reglas.

---

# 52. COMPONENTE DE BLOQUEOS

En Fase 3 mostrar antes del botón de cierre:

```text
LISTO PARA CIERRE
✅ Avance 100%
✅ Estado Completado
✅ Sin tareas abiertas
✅ Acta de Entrega
✅ Informe Final
```

o:

```text
NO LISTO PARA CIERRE
❌ Falta Acta de Entrega
❌ 2 tareas pendientes
```

Esto mejora la UX y evita que el usuario descubra todos los errores después de pulsar el botón.

---

# 53. MODELO DE CIERRE: NO DUPLICAR TODO EL PROYECTO

No crear una copia completa:

```text
CierreProyecto
```

que replique todos los datos de las fases anteriores.

Preferir un:

```text
ProyectoClosureSummaryService
```

como read model.

Solo persistir lo que sea verdaderamente histórico:

```text
fecha_cierre_real
usuario de cierre
timestamp
estado final
```

y documentos finales.

---

# 54. FUENTES SSoT DEL CONSOLIDADO

El resumen debe respetar:

```text
Valor vendido
→ Facturas de Venta / dominio económico de Inicio

Cotización comercial
→ Cotizaciones

Presupuesto planeado
→ ItemPresupuestoProyecto

Tareas
→ TareaDiariaProyecto

Gastos
→ Gastos

Tiempo
→ fechas del Proyecto + reglas de workflow
```

No duplicar estas fuentes.

---

# 55. NO TOCAR INNECESARIAMENTE OTRAS APPS

La misión se limita a Proyectos y bridges mínimos de lectura.

No reescribir:

```text
Facturas
Ventas
Compras
Gastos
Inventario
Contabilidad
Nómina
```

Solo adaptar contratos de lectura donde sea indispensable.

---

# 56. TESTS DE FASE 3

Crear/ajustar pruebas para:

```text
porcentaje editable en EJECUCION
estado_tarea editable en EJECUCION
tareas operables
gastos no facturables visibles
tiempo correcto
adelanto correcto
retraso correcto
```

---

# 57. TESTS DE CIERRE

Debe fallar:

```text
sin acta
sin informe
avance < 100
estado != COMPLETADO
tareas abiertas
```

Debe funcionar:

```text
avance 100
estado COMPLETADO
sin tareas abiertas
acta presente
informe presente
```

---

# 58. TEST DE PERSISTENCIA

Después de cerrar:

```text
refresh_from_db()
```

debe mostrar:

```text
fase_actual = CIERRE
estado_tarea = COMPLETADO
porcentaje_avance = 100
fecha_cierre_real != null
```

La prueba debe validar la BD real, no únicamente el objeto de memoria de la request.

---

# 59. TEST DE BYPASS

Intentar por API:

```text
PLANEACION → CIERRE
```

Debe fallar.

Intentar:

```text
PATCH fase_actual = CIERRE
```

Debe fallar.

Intentar modificar en CIERRE:

```text
porcentaje_avance
estado_tarea
```

Debe fallar.

---

# 60. TEST DE TAREAS EN CIERRE

Una vez cerrado:

```text
POST crear tarea
PATCH tarea
DELETE tarea
POST cambiar estado
```

deben quedar bloqueados.

---

# 61. TEST DE GASTOS EN CIERRE

Cierre solo consulta.

La creación/modificación de gastos continúa ocurriendo en Gastos.

El módulo Proyectos no debe crear un gasto nuevo desde Cierre.

---

# 62. TEST DE TIEMPO

Caso adelantado:

```text
fecha_cierre_real < fecha_fin_estimada
```

Resultado:

```text
Adelantado X días
```

Caso retrasado:

```text
fecha_cierre_real > fecha_fin_estimada
```

Resultado:

```text
Retrasado X días
```

Caso exacto:

```text
En fecha
```

---

# 63. TEST E2E MANUAL

1. Abrir proyecto en Ejecución.
2. Cambiar porcentaje.
3. Cambiar estado operativo.
4. Crear tarea.
5. Completar tarea.
6. Verificar control temporal.
7. Registrar gasto no facturable desde Gastos.
8. Verificar que aparece automáticamente en Ejecución.
9. Completar todas las tareas.
10. Llevar avance a 100%.
11. Adjuntar Acta de Entrega.
12. Adjuntar Informe Final.
13. Ejecutar cierre.
14. Verificar que el proyecto queda en CIERRE.
15. Abrir nuevamente el proyecto.
16. Verificar que Cierre es principalmente read-only.
17. Verificar resumen de Fases 1–3.
18. Verificar rentabilidad.
19. Verificar tiempo final.
20. Verificar que no se puede modificar el estado operativo desde Cierre.

---

# 64. UI FINAL PROPUESTA — FASE 3

```text
┌──────────────────────────────────────────────┐
│ 3. EJECUCIÓN                                 │
│                                              │
│ AVANCE              ESTADO                   │
│ 68%                 EN PROCESO               │
│                                              │
│ CONTROL DE TIEMPO                             │
│ Inicio      Fin estimada    Restante         │
│ 01/10       30/10           12 días          │
│ Estado: EN FECHA                             │
│                                              │
│ TAREAS                                        │
│ 19 total | 14 completas | 1 atrasada         │
│                                              │
│ EQUIPO OPERATIVO                              │
│ ...                                          │
│                                              │
│ PEDIDOS / RECURSOS                            │
│ ...                                          │
│                                              │
│ GASTOS NO FACTURABLES                         │
│ $ 4.250.000 · 6 registros                    │
│                                              │
│ [ Finalizar Ejecución ]                      │
└──────────────────────────────────────────────┘
```

---

# 65. UI FINAL PROPUESTA — FASE 4

```text
┌──────────────────────────────────────────────┐
│ 4. CIERRE                                    │
│ ✅ PROYECTO TERMINADO                        │
│                                              │
│ RESUMEN EJECUTIVO                            │
│ Cliente · Supervisor · Contratista          │
│ Fechas · Estado Final                        │
│                                              │
│ RESUMEN DE FASES 1–3                         │
│ Inicio      Planeación       Ejecución       │
│ Aprobado    Completada       Completada      │
│                                              │
│ TIEMPOS                                      │
│ Duración planificada / real                  │
│ Adelanto / Retraso                           │
│                                              │
│ TAREAS                                       │
│ Total / Completadas / Atrasadas              │
│                                              │
│ GASTOS                                       │
│ No facturables / Total                       │
│                                              │
│ RENTABILIDAD                                 │
│ Venta / Costos / Resultado / Margen          │
│                                              │
│ DESGLOSE ADMINISTRATIVO                      │
│ Facturas / Compras / Presupuesto / Gastos    │
│                                              │
│ DOCUMENTACIÓN FINAL                          │
│ ✅ Acta de Entrega                           │
│ ✅ Informe Final                              │
│                                              │
│ PROYECTO CERRADO                             │
└──────────────────────────────────────────────┘
```

---

# 66. ORDEN DE IMPLEMENTACIÓN

## Fase A — Workflow

1. Definir matriz de transiciones.
2. Implementar validación SSoT.
3. Bloquear saltos.
4. Bloquear PATCH de `fase_actual`.

## Fase B — Ejecución

1. Mover porcentaje a Step 3.
2. Mover estado operativo a Step 3.
3. Integrar control temporal.
4. Mantener tareas.
5. Mantener gastos no facturables.
6. Crear gate de cierre.

## Fase C — Cierre

1. Eliminar Configuración de Cierre.
2. Construir Closure Summary.
3. Hacerlo read-only.
4. Agregar desglose administrativo.
5. Validar documentos obligatorios.

## Fase D — API

1. GET resumen cierre.
2. POST cierre.
3. Respuestas de bloqueo.

## Fase E — Tests

1. Unit tests.
2. API tests.
3. Persistencia.
4. Seguridad.
5. E2E manual.

## Fase F — Documentación

Actualizar auditoría, índice documental y matriz de trazabilidad.

---

# 67. PRIORIZACIÓN

## P0

```text
Gate EJECUCION → CIERRE
Porcentaje a Ejecución
Estado a Ejecución
Cierre read-only
Acta obligatoria
Informe obligatorio
Sin bypass API
Estado final coherente
```

## P1

```text
Closure Summary API
Resumen de tiempo
Resumen de tareas
Resumen de gastos
Rentabilidad consolidada
Desglose administrativo
```

## P2

```text
Reapertura auditada
Snapshots históricos avanzados
Indicadores de gestión adicionales
```

---

# 68. CRITERIOS DE ACEPTACIÓN

```text
✅ Fase 3 controla la operación.
✅ Porcentaje de avance se gestiona en Fase 3.
✅ Estado global de ejecución se gestiona en Fase 3.
✅ Tareas se gestionan en Fase 3.
✅ Tiempos se gestionan/calculan en Fase 3.
✅ Gastos no facturables aparecen automáticamente.
✅ Fase 4 no permite editar avance.
✅ Fase 4 no permite editar estado operativo.
✅ Fase 4 no permite modificar tareas.
✅ Fase 4 consolida Fases 1–3.
✅ Fase 4 muestra rentabilidad.
✅ Fase 4 muestra adelanto/retraso.
✅ Fase 4 muestra tareas ejecutadas.
✅ Fase 4 muestra gastos.
✅ Acta de Entrega es obligatoria.
✅ Informe Final es obligatorio.
✅ No se puede cerrar con ejecución incompleta.
✅ No se puede saltar fases.
✅ No se puede cerrar mediante PATCH genérico.
✅ El cierre persiste en BD.
✅ El estado final queda coherente.
```

---

# 69. REGLA FUNDAMENTAL DEL NUEVO CICLO

```text
FASE 3 = OPERAR

FASE 4 = CONSOLIDAR Y FORMALIZAR
```

Y la frontera debe ser inequívoca:

```text
EJECUCIÓN COMPLETADA
        ↓
VALIDACIÓN DE CIERRE
        ↓
CIERRE
        ↓
PROYECTO TERMINADO
```

Cierre no es una segunda pantalla de ejecución. Es el registro final de lo que realmente ocurrió.

---

# FIN DEL PLAN
