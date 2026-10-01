# PLAN DE ACCIÓN — OPTIMIZACIÓN DEL MÓDULO COMPRAS Y BASE EFICIENTE PARA NUEVA REQUISICIÓN

**Repositorio auditado:** `steven-zdt/CRM_SINTEL`
**Rama auditada:** `main`
**Fecha:** 2026-09-30
**Alcance:** Optimización integral del flujo actual de Compras y preparación de una base eficiente para `Nueva Requisición de Compra`.
**Principio rector:** mejorar eficiencia sin alterar la lógica de negocio vigente.
**Pruebas:** únicamente pruebas manuales de UI y exclusivamente como último paso.

---

## 1. Objetivo

Aplicar de forma controlada todas las recomendaciones obtenidas durante la auditoría estática del código real de `main`, reduciendo:

- consultas innecesarias a PostgreSQL;
- carga inicial de catálogos completos;
- llamadas HTTP duplicadas;
- escrituras redundantes;
- reemplazos destructivos de Items;
- cálculos duplicados en frontend;
- código HTML/JS duplicado;
- mecanismos paralelos de numeración;
- rutas de lectura ORM fuera de Selectors;
- diferencias entre documentación y código vigente.

La optimización debe preservar:

- Service Layer;
- DSV / anti-IDOR;
- aislamiento multi-tenant;
- estados actuales de Orden de Compra;
- cálculo financiero backend como SSoT;
- integración Compras → Proveedores/CxP;
- comportamiento actual de creación, edición, aprobación, recepción y anulación;
- APIs existentes, salvo endpoints obsoletos que se eliminen de forma controlada y documentada.

---

## 2. Evidencia de partida

La auditoría de `main` confirmó que Compras contiene actualmente:

```text
apps/tenant/compras/
├── models.py
├── services/
│   ├── api_mixins.py
│   ├── business_service.py
│   ├── crud_service.py
│   └── selectors.py
├── api/
│   ├── serializers.py
│   ├── urls.py
│   └── viewsets.py
├── templates/tenant/compras/
├── static/compras/js/
└── .agent/AUDITORIA_FLUJO_COMPRAS.md
```

La rama `main` auditada todavía no expone `apps/tenant/compras/requisiciones/`. Por ello este plan optimiza primero la base real existente de Compras y define los patrones que deberá reutilizar la futura Requisición, sin afirmar que la implementación de Requisiciones ya exista en esa rama.

---

# 3. PRINCIPIOS NO NEGOCIABLES

## 3.1 No cambiar la lógica de negocio

No modificar sin justificación funcional:

- estados de OrdenCompra;
- reglas de proveedor obligatorio;
- relaciones de proyecto/documento soporte;
- cálculo financiero final;
- sincronización de CxP;
- recepción de inventario;
- permisos y DSV.

La optimización debe cambiar el **cómo**, no el **qué**.

## 3.2 Una sola fuente de verdad

Especialmente para:

- numeración;
- cálculos monetarios definitivos;
- consultas optimizadas;
- endpoints;
- permisos de tenant.

## 3.3 Nada de lógica de negocio en frontend

El frontend puede:

- mostrar previews;
- validar UX inmediata;
- manejar estado temporal;
- construir payloads.

El backend conserva la decisión definitiva.

## 3.4 No crear un segundo motor para Requisiciones

El motor de numeración existente debe generalizarse para soportar más de un tipo documental, evitando crear otra implementación paralela.

## 3.5 Sin señales de Django

Toda mutación dependiente debe permanecer explícita en Service Layer.

## 3.6 Pruebas únicamente al final

No ejecutar pytest, suites automáticas ni pruebas parciales durante las fases de implementación de este plan.

El último paso de la misión será una batería manual de UI.

---

# 4. FASE 0 — BASELINE Y PROTECCIÓN DEL COMPORTAMIENTO ACTUAL

## Objetivo

Documentar exactamente el estado funcional antes de tocarlo.

## Acciones

1. Registrar commit SHA de `main` usado como baseline.
2. Leer nuevamente:
   - `AGENTS.md`;
   - `CLAUDE.md`;
   - `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md`.
3. Identificar todos los endpoints utilizados por Compras.
4. Identificar todos los consumidores de:
   - `get_siguiente_consecutivo()`;
   - `getHeaders()`;
   - `compras.utils.js`;
   - `PlantillaOrdenCompra`.
5. Confirmar que no existen consumidores externos de APIs/funciones que se planea retirar.
6. Crear un inventario de archivos modificables.

## Criterio de salida

Existe una matriz clara:

```text
archivo → símbolo → consumidor → decisión
```

Sin modificar todavía comportamiento.

---

# 5. FASE 1 — UNIFICAR Y ENDURECER EL MOTOR DE NUMERACIÓN

## Objetivo

Eliminar conceptos paralelos de numeración y establecer una SSoT reutilizable por Orden de Compra y Requisición.

## Evidencia actual

La numeración real de OrdenCompra utiliza:

```text
PlantillaOrdenCompra
→ consecutivo_actual
→ formar_numero()
→ numero_documento
```

Mientras existe además:

```text
OrdenCompraSelector.get_siguiente_consecutivo()
→ MAX(consecutivo) + 1
```

## Acciones

### 5.1 Identificar todos los usos de `get_siguiente_consecutivo()`

Si solo sirve para preview o compatibilidad, documentar y retirar progresivamente.

### 5.2 Separar claramente

```text
numero_documento
```

de:

```text
consecutivo auxiliar/interno
```

No utilizar `MAX(consecutivo)+1` como fuente de verdad del documento numerado por plantilla.

### 5.3 Generalizar el concepto de plantilla

La implementación debe permitir conceptualmente:

```text
Plantilla de numeración
├── ORDEN_COMPRA
└── REQUISICION
```

sin duplicar clases o motores si el diseño actual permite una extensión segura.

### 5.4 Conservar asignación atómica

Mantener:

```python
select_for_update()
```

sobre la plantilla durante la reserva del número.

### 5.5 Mantener incremento atómico

Conservar el patrón SQL con `F()` + `update()` cuando corresponda.

### 5.6 Hacer inmutable el número documental una vez asignado

Una edición normal no debe permitir:

```text
numero_documento
consecutivo
```

salvo mecanismos administrativos expresamente controlados.

### 5.7 Proteger `consecutivo_actual`

Revisar y retirar de la edición CRUD normal la posibilidad de manipular libremente `consecutivo_actual`.

El contador debe ser gestionado por el motor de numeración, no por un PATCH ordinario.

### 5.8 Mantener la unicidad de BD

Conservar/validar la garantía de unicidad por tenant para `numero_documento`.

Para futura Requisición debe existir una garantía equivalente y compatible con la misma SSoT.

## Resultado esperado

```text
Usuario selecciona plantilla
        ↓
Backend asigna número
        ↓
Número único e inmutable
        ↓
Nunca se reutiliza
```

## No hacer

- no crear otro contador para Requisición;
- no generar números finales desde JS;
- no usar `MAX()+1` como numeración documental definitiva.

---

# 6. FASE 2 — OPTIMIZAR SELECTORS Y LECTURAS ORM

## Objetivo

Consolidar el acceso de lectura por Selectors y evitar N+1 o consultas redundantes.

## Archivos principales

- `apps/tenant/compras/services/selectors.py`
- `apps/tenant/compras/api/viewsets.py`
- `apps/tenant/compras/views.py`
- templates de detalle/edición.

## Acciones

### 6.1 Mantener `LIST_FIELDS` y `DETAIL_FIELDS` como SSoT

No introducir `.only()` ad-hoc en ViewSets.

### 6.2 Auditar todos los `select_related()`

Cada campo usado por serializer/template debe estar cubierto por traversal adecuado.

### 6.3 Auditar todos los `prefetch_related()`

Especialmente:

```text
OrdenCompra → items
```

### 6.4 Eliminar ORM directo en renderizadores

Evitar patrones como:

```python
get_object_or_404(OrdenCompra, ...)
```

cuando el mismo dato puede venir desde un Selector optimizado.

La ruta de edición/detalle debe consumir un QuerySet preparado con:

```text
empresa_id
+ select_related
+ prefetch_related
+ only
```

### 6.5 No tocar seguridad

Toda consulta seguirá filtrada por `empresa_id` y scope organizacional.

---

# 7. FASE 3 — OPTIMIZAR KPIs DE LA VISTA DE COMPRAS

## Problema actual

La vista HTML calcula varios KPIs con consultas independientes sobre el mismo QuerySet.

## Acciones

Consolidar en una sola operación de agregación cuando sea compatible con el código existente:

```text
count total
sum monto
count aprobadas
count pendientes
```

Preferentemente mediante un único `aggregate()` con expresiones condicionadas.

## Criterio

Reducir round-trips al motor PostgreSQL sin cambiar números mostrados.

---

# 8. FASE 4 — OPTIMIZAR CARGA DE PROVEEDORES Y PROYECTOS

## Objetivo

Eliminar carga masiva de catálogos al abrir el formulario.

## Problema actual

`compras.utils.js` descarga listas completas y las mantiene cinco minutos en memoria.

## Diseño objetivo

Migrar progresivamente a búsqueda bajo demanda.

```text
Abrir formulario
    ↓
No cargar todo el catálogo

Usuario escribe 3+ caracteres
    ↓
GET búsqueda
    ↓
10-20 resultados
    ↓
Selección
```

## Acciones

1. Identificar endpoints actuales de proveedores/proyectos.
2. Verificar si ya soportan `search`/filtros eficientes.
3. Reutilizar endpoints existentes cuando sea viable.
4. Crear únicamente la lógica necesaria dentro de las estructuras autorizadas.
5. Evitar nuevos `.py` fuera del Service Layer.
6. Mantener cache solo para datos pequeños o respuestas de búsqueda si aporta valor real.
7. Eliminar la dependencia de descargar catálogos completos.

## Resultado

El formulario inicial debe abrirse sin esperar a descargar todo el catálogo.

---

# 9. FASE 5 — UNIFICAR TRANSPORTE HTTP FRONTEND

## Objetivo

Eliminar el segundo sistema de HTTP existente en Compras.

## Estado actual

`compras.api.js` usa `Sintel.Core.Http`, mientras `compras.utils.js` conserva `fetch()` directo.

## Acciones

1. Crear/reutilizar métodos adecuados dentro del namespace API existente.
2. Hacer que utilidades consuman `window.Sintel.Compras.API` o `Sintel.Core.Http` mediante la capa SSoT del módulo.
3. Eliminar progresivamente:

```javascript
getHeaders()
```

si la auditoría de consumidores demuestra que ya no es necesario.

4. No duplicar CSRF/JWT.
5. Mantener el contrato actual de errores.

## Resultado

```text
Frontend Compras
       ↓
Compras API SSoT
       ↓
Core.Http
       ↓
HTTP
```

---

# 10. FASE 6 — OPTIMIZAR CRUD DE ITEMS SIN BORRADO MASIVO

## Objetivo

Eliminar el patrón:

```text
DELETE todos los Items
INSERT todos los Items
```

durante una edición.

## Diseño objetivo

Sincronización diferencial por UUID.

```text
Payload enviado
      │
      ├── UUID existente
      │       ├── sin cambios → no-op
      │       └── cambios → UPDATE
      │
      ├── sin UUID → INSERT
      │
      └── UUID existente no enviado → DELETE
```

## Acciones

1. Mantener UUID público de cada Item.
2. El frontend debe enviar UUID cuando edita un Item existente.
3. El CRUD debe identificar Items actuales de la Orden.
4. Construir conjuntos:

```text
existentes
entrantes
eliminados
nuevos
modificados
```

5. Ejecutar únicamente los cambios necesarios.
6. Mantener la operación completa dentro de `transaction.atomic()`.
7. Recalcular totales solamente con el conjunto final.

## Beneficios

- menos DELETE;
- menos INSERT;
- menos locks;
- preservación de UUID;
- mejor auditoría futura;
- mejor base para Items de Requisición.

---

# 11. FASE 7 — REDUCIR ESCRITURAS REDUNDANTES EN CREACIÓN

## Objetivo

Evitar crear la cabecera con totales cero para inmediatamente actualizarla.

## Diseño

Antes de crear la cabecera:

```text
Items DTO
   ↓
calcular subtotal/IVA/total
   ↓
crear cabecera con totales definitivos
   ↓
bulk_create Items
```

## Acciones

1. Reutilizar la misma fórmula backend que ya existe.
2. No mover la SSoT financiera al frontend.
3. Mantener Decimal y redondeo actual.
4. Evitar segunda escritura de cabecera cuando no sea necesaria.

---

# 12. FASE 8 — REDUCIR VALIDACIÓN REDUNDANTE POR ITEM

## Objetivo

Revisar el uso de `full_clean()` dentro del loop de Items.

## Acciones

1. Inventariar qué validaciones aporta actualmente el modelo.
2. Identificar cuáles ya están cubiertas por:

```text
Serializer
Business Service
DB constraints
```

3. Mantener solo las validaciones que agreguen protección real.
4. No retirar validaciones críticas solamente por ganar rendimiento.
5. Cuando sea seguro, sustituir validaciones repetitivas por garantías a nivel de DTO/servicio/DB.

## Criterio

Menor costo de CPU/ORM sin reducir integridad.

---

# 13. FASE 9 — CENTRALIZAR CÁLCULO DE PREVIEW EN JAVASCRIPT

## Objetivo

Eliminar duplicación entre:

- `actualizarFilaTotal()`;
- `actualizarTotales()`.

## Diseño

Crear una función interna única:

```text
calcularItem(cantidad, valorUnitario, porcentajeIva)
```

y reutilizar su resultado para:

```text
fila
subtotal acumulado
IVA acumulado
total acumulado
```

## Regla

El cálculo JS es exclusivamente visual.

El cálculo final del backend continúa siendo la SSoT.

---

# 14. FASE 10 — AJUSTAR PREVIEW DE NUMERACIÓN EN UI

## Objetivo

Evitar que el usuario interprete el `consecutivo_actual` mostrado en HTML como número definitivamente reservado.

## Cambios

Cambiar textos como:

```text
Número a asignar
```

por conceptos más precisos como:

```text
Próximo número estimado
```

cuando todavía no ha ocurrido la asignación transaccional.

Después de crear:

```text
mostrar número realmente asignado por backend
```

---

# 15. FASE 11 — CONSOLIDAR TEMPLATES CREAR/EDITAR

## Objetivo

Reducir duplicación entre:

- `offcanvas_crear_compras.html`;
- `offcanvas_editar_compras.html`.

## Diseño sugerido

```text
templates/tenant/compras/partials/
├── formulario_estilos.html
├── informacion_general.html
├── items_table.html
├── totales_observaciones.html
└── acciones_footer.html
```

No crear un template monolítico.

Crear/editar deben reutilizar componentes pequeños y conservar sus diferencias explícitas.

## Criterio

Una modificación visual de un campo común debe hacerse una sola vez.

---

# 16. FASE 12 — PREPARAR BASE PARA NUEVA REQUISICIÓN

Esta fase no pretende implementar toda la Requisición si su código aún no está presente en `main`; prepara los patrones correctos.

## 16.1 Numeración

Reutilizar la SSoT de numeración definida en FASE 1.

La futura Requisición debe poder utilizar:

```text
Plantilla de Numeración
      ↓
REQUISICION
      ↓
numero_documento único
```

## 16.2 Búsqueda de Cliente

No descargar todo el catálogo.

Usar búsqueda bajo demanda.

## 16.3 Búsqueda de Cotizaciones

La UI debe trabajar de esta forma:

```text
Usuario pulsa "Vincular Cotización"
          ↓
Buscar
          ↓
solo cotizaciones elegibles
          ↓
seleccionar
          ↓
agregar al formulario
```

La consulta debe excluir cotizaciones que ya estén asociadas a una requisición cuando la regla funcional así lo requiera.

## 16.4 Cotizaciones múltiples

La requisición debe manejar una relación `1:N` con cotizaciones mediante la relación de dominio existente/prevista, no duplicando datos de la cotización en la requisición.

## 16.5 Proyecto opcional

Mismo patrón de búsqueda bajo demanda.

## 16.6 Items

El formulario debe permitir:

```text
Cotización seleccionada
        ↓
Items importados
        ↓
edición manual
        ↓
sincronización diferencial
```

No copiar ciegamente la estrategia destructiva de OrdenCompra.

---

# 17. FASE 13 — ACTUALIZAR DOCUMENTACIÓN SSoT

## Objetivo

Eliminar documentation drift.

## Acciones

Actualizar:

```text
apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md
```

para que refleje el código real actual, especialmente:

- HTMX + django-tables2 vs. documentación histórica de Tabulator;
- flujo actual de carga de assets;
- numeración vigente;
- optimización de Selectors;
- comportamiento de Items;
- transporte HTTP final;
- nuevos patrones de búsqueda bajo demanda.

No documentar funcionalidad futura como si ya estuviera implementada.

---

# 18. FASE 14 — LIMPIEZA CONTROLADA DE CÓDIGO MUERTO

Solo después de las fases funcionales anteriores.

## Candidatos iniciales

Auditar referencias antes de eliminar:

- `OrdenCompraSelector.get_siguiente_consecutivo()`;
- `window.Sintel.Compras.getHeaders()`;
- helpers reemplazados del transporte HTTP;
- lógica duplicada de cálculo JS;
- imports que queden huérfanos;
- funciones antiguas asociadas al patrón Tabulator si ya no tienen consumidor real.

## Regla

No eliminar por inferencia.

Eliminar únicamente cuando la búsqueda del repositorio demuestre ausencia de consumidores activos.

---

# 19. FASE 15 — VERIFICACIÓN ESTÁTICA FINAL SIN TEST AUTOMÁTICO

Antes de las pruebas UI:

1. Revisar imports.
2. Revisar referencias de funciones eliminadas.
3. Revisar URLs.
4. Revisar templates usados por cada endpoint HTMX.
5. Revisar nombres de IDs DOM.
6. Revisar payload JSON.
7. Revisar que ningún número documental se genere definitivamente en JavaScript.
8. Revisar aislamiento `empresa_id`.
9. Revisar que cada QuerySet respete `.only()`/`.defer()` según las reglas del proyecto.
10. Revisar que no se hayan introducido signals.

No ejecutar todavía pruebas automáticas.

---

# 20. FASE 16 — PRUEBAS MANUALES DE UI — ÚLTIMO PASO

Esta es la única fase de pruebas de la misión.

## 20.1 Nueva Orden de Compra

### Crear

1. Abrir `/workspace/#compras`.
2. Abrir Nueva Orden.
3. Confirmar que el formulario aparece sin descargar indiscriminadamente catálogos completos.
4. Seleccionar plantilla.
5. Confirmar preview de numeración.
6. Buscar proveedor.
7. Buscar proyecto opcional.
8. Agregar dos Items.
9. Editar cantidades/valores/IVA.
10. Confirmar actualización instantánea de totales.
11. Guardar.
12. Verificar que el número devuelto por backend sea el mostrado en el resultado.
13. Verificar que el listado se actualice sin recarga completa.

### Editar

1. Abrir una Orden en BORRADOR.
2. Cambiar solamente un Item.
3. Guardar.
4. Confirmar que el documento permanece íntegro.
5. Confirmar que los Items restantes siguen existiendo.
6. Confirmar que la numeración no cambia.

### Eliminar Item

1. Eliminar una línea.
2. Guardar.
3. Confirmar que solo esa línea desapareció.

### Agregar Item

1. Agregar una línea nueva.
2. Guardar.
3. Confirmar que se crea únicamente la línea nueva.

## 20.2 Numeración concurrente funcional

Sin pruebas automatizadas, realizar una verificación manual con dos sesiones del sistema usando la misma plantilla:

```text
Sesión A
Sesión B
```

Crear una Orden desde cada sesión.

Verificar que no reciban el mismo número.

## 20.3 Plantilla

Verificar:

- creación;
- activación/desactivación;
- rango;
- preview;
- imposibilidad de manipular el número documental de una Orden existente.

## 20.4 Performance UI percibida

Verificar que:

- el formulario abra rápidamente;
- proveedores no se carguen masivamente al abrir;
- proyectos no se carguen masivamente al abrir;
- búsqueda responda bajo demanda;
- no haya loaders duplicados;
- no haya backdrop acumulado;
- no haya ejecución doble de JS;
- consola del navegador no reporte errores.

## 20.5 Regresión funcional

Confirmar manualmente:

```text
Crear → Editar → Aprobar → Recepcionar
```

y que la sincronización existente con CxP/inventario no se vea alterada.

---

# 21. CRITERIOS DE ACEPTACIÓN

La misión solo se considera finalizada cuando se cumplan todos:

## Numeración

- Existe una única SSoT de numeración.
- No se utiliza `MAX()+1` para generar el número documental final.
- El número se reserva transaccionalmente.
- El número es único por tenant.
- El número no cambia durante una edición ordinaria.
- El contador no es libremente editable.

## Consultas

- No se cargan catálogos completos innecesariamente.
- Lecturas de detalle/listado pasan por Selectors optimizados.
- No existe N+1 introducido por los cambios.
- Los KPIs usan menos round-trips cuando la consolidación es viable.

## HTTP

- Existe un único camino oficial de transporte frontend.
- No hay duplicación de CSRF/JWT.

## Items

- Editar un Item no elimina/recrea toda la colección.
- Se preservan UUIDs existentes.
- Solo se escriben las líneas que cambiaron.
- Totales finales siguen calculándose en backend.

## Frontend

- La fórmula JS de preview no está duplicada innecesariamente.
- Crear/editar comparten componentes visuales donde corresponde.
- No se generan números finales de negocio en JS.

## Requisición

La base queda preparada para:

- plantilla obligatoria;
- cliente obligatorio;
- número por plantilla;
- cotizaciones múltiples;
- búsqueda bajo demanda;
- proyecto opcional;
- Items importados y editables;
- sincronización diferencial.

---

# 22. ORDEN EXACTO DE EJECUCIÓN

```text
FASE 0  Baseline
  ↓
FASE 1  Motor de numeración
  ↓
FASE 2  Selectors / ORM
  ↓
FASE 3  KPIs
  ↓
FASE 4  Búsqueda bajo demanda
  ↓
FASE 5  HTTP único
  ↓
FASE 6  Sincronización diferencial de Items
  ↓
FASE 7  Reducción de escrituras
  ↓
FASE 8  Validación redundante
  ↓
FASE 9  Cálculo JS único
  ↓
FASE 10 Preview de numeración
  ↓
FASE 11 Partials crear/editar
  ↓
FASE 12 Base Nueva Requisición
  ↓
FASE 13 Documentación SSoT
  ↓
FASE 14 Limpieza código muerto
  ↓
FASE 15 Verificación estática
  ↓
FASE 16 PRUEBAS MANUALES UI
```

---

# 23. REGLA FINAL PARA LA IA EDITORA

No realizar una reescritura masiva de Compras.

Aplicar cambios quirúrgicos, uno por fase, verificando después de cada bloque que:

```text
SSoT actual
      ↓
se conserva
      ↓
la lógica de negocio
      ↓
se conserva
      ↓
solo se reduce trabajo innecesario
```

No introducir frameworks nuevos.

No crear una arquitectura paralela.

No duplicar servicios.

No crear un segundo motor de numeración para Requisiciones.

No mover reglas financieras al frontend.

No eliminar código por intuición: cada eliminación debe estar respaldada por búsqueda de consumidores.

No ejecutar pruebas automáticas durante las fases anteriores.

**La única validación de esta misión será la prueba manual de UI de la FASE 16, ejecutada como último paso.**
