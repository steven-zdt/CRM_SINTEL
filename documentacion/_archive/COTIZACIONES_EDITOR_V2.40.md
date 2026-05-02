# 📋 Editor de Cotizaciones Estilo Excel v2.40 - Documentación Completa

**Fecha:** 2026-01-XX  
**Estado:** ✅ **COMPLETADO Y FUNCIONAL**  
**Versión:** 2.40

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Modular](#arquitectura-modular)
3. [Estructura de Archivos](#estructura-de-archivos)
4. [Funcionalidades Principales](#funcionalidades-principales)
5. [Visibilidad Dinámica de Secciones](#visibilidad-dinámica-de-secciones)
6. [API Pública](#api-pública)
7. [Flujos de Trabajo](#flujos-de-trabajo)
8. [Configuración y Uso](#configuración-y-uso)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Resumen Ejecutivo

El Editor de Cotizaciones Estilo Excel v2.40 es una refactorización completa del sistema de cotizaciones que implementa:

- ✅ **Arquitectura Modular en Cascada**: Separación de responsabilidades en módulos independientes
- ✅ **Visibilidad Dinámica**: Pestañas se muestran/ocultan según permisos del perfil de configuración
- ✅ **Cálculo AIU Corregido**: IVA solo sobre Utilidad según normativa colombiana
- ✅ **AIU Universal**: Aplicación de AIU en modelos MIXTO con cálculo integral sobre todas las secciones
- ✅ **Gestión de Perfiles**: Sistema CRUD completo de perfiles de configuración
- ✅ **Rendimiento Optimizado**: Tablas Tabulator independientes por sección
- ✅ **Generación de PDF Dinámico**: PDFs profesionales con WeasyPrint, reflejando exactamente el editor

### Principales Mejoras

1. **Modularidad**: Código fragmentado en módulos reutilizables y mantenibles
2. **Escalabilidad**: Fácil agregar nuevas secciones o funcionalidades
3. **Estabilidad**: Errores de `ReferenceError` y `hasAttribute` resueltos
4. **UX Mejorada**: Activación automática de pestañas visibles

---

## 🏗️ Arquitectura Modular

### Diagrama de Arquitectura

```
cotizacion_editor_core.js (Orquestador Principal)
    │
    ├── Gestión de Perfiles de Configuración
    ├── Cálculo de Totales (AIU + IVA)
    ├── API bulk-save
    └── Coordinación de Módulos de Sección
         │
         ├── editor_seccion_dispositivos.js (Módulo 1.0)
         │    ├── Tabla Tabulator independiente
         │    ├── Columnas específicas (Marca, Referencia, etc.)
         │    └── Métodos: agregarFila(), obtenerSubtotal(), obtenerItems()
         │
         ├── editor_seccion_accesorios.js (Módulo 2.0)
         │    ├── Tabla Tabulator independiente
         │    ├── Columnas específicas (Referencia, etc.)
         │    └── Métodos: agregarFila(), obtenerSubtotal(), obtenerItems()
         │
         └── editor_seccion_mano_obra.js (Módulo 3.0)
              ├── Tabla Tabulator independiente
              ├── Columnas específicas (Servicios)
              └── Métodos: agregarFila(), obtenerSubtotal(), obtenerItems()
```

### Responsabilidades por Módulo

#### `cotizacion_editor_core.js` (Core Manager)
- ✅ Ciclo de vida del modal
- ✅ Carga de perfiles de configuración
- ✅ Cálculo de totales globales (AIU + IVA)
- ✅ Envío bulk-save a la API
- ✅ Coordinación de módulos de sección
- ✅ Gestión de visibilidad dinámica

#### Módulos de Sección (dispositivos, accesorios, mano-obra)
- ✅ Instancia Tabulator independiente
- ✅ Columnas específicas por sección
- ✅ Método `agregarFila()` asíncrono
- ✅ Método `obtenerSubtotal(esAiuActivo)`
- ✅ Método `obtenerItems()` para guardado
- ✅ Método `actualizarColumnas(tipoPlantilla)`
- ✅ Método `redraw()` para pestañas ocultas

---

## 📂 Estructura de Archivos

### JavaScript (Módulos)

```
apps/tenant/core/static/core/js/cotizaciones/
├── cotizacion_editor_core.js          # Orquestador principal
├── editor_seccion_dispositivos.js     # Módulo 1.0 (Equipos)
├── editor_seccion_accesorios.js       # Módulo 2.0 (Materiales)
├── editor_seccion_mano_obra.js        # Módulo 3.0 (Mano de Obra)
├── cotizaciones.api.js                # API wrapper (dependencia)
└── cotizaciones.page.js               # Página principal (dependencia)
```

### Templates HTML (Modulares)

```
apps/tenant/core/templates/tenant/core/partials/cotizaciones/
├── modal_editor_core.html             # Estructura principal del modal
├── tab_dispositivos.html              # Partial: Pestaña dispositivos
├── tab_accesorios.html                # Partial: Pestaña accesorios
├── tab_mano_obra.html                 # Partial: Pestaña mano de obra
└── panel_totales.html                 # Partial: Panel de totales
```

### Assets (Orden de Carga)

```
apps/tenant/core/templates/tenant/core/partials/cotizaciones/
└── assets_cotizaciones.html           # Orden crítico de scripts
```

**⚠️ ORDEN CRÍTICO DE CARGA:**
1. Módulos de sección (dispositivos, accesorios, mano-obra)
2. Core Manager (cotizacion_editor_core.js)

---

## ⚙️ Funcionalidades Principales

### 1. Gestión de Perfiles de Configuración

#### Cargar Perfiles Disponibles
```javascript
await w.CotizacionEditorCore.cargarPerfilesConfiguracion();
```

#### Cargar Detalle de Perfil
```javascript
await w.CotizacionEditorCore.cargarDetallePerfil(perfilId);
```

#### Aplicar Configuración del Perfil
```javascript
await w.CotizacionEditorCore.aplicarConfiguracionPerfil();
```

**Efectos:**
- Actualiza IVA desde el perfil
- Inicializa valores AIU (si aplica)
- Gestiona visibilidad de secciones
- Actualiza columnas en módulos de sección
- Recalcula totales

### 2. Cálculo de Totales

#### Modo Estándar
- **Subtotal**: Suma de `subtotal_linea` de todas las secciones visibles
- **IVA**: `subtotal * (iva_porcentaje / 100)`
- **Total**: `subtotal + iva`

#### Modo AIU (Administración, Imprevistos, Utilidad) - Universal

⚠️ **v2.40 - AIU Universal**: El cálculo AIU se aplica sobre **TODOS los ítems** de **TODAS las secciones**, independientemente del `modelo_tipo` (incluyendo MIXTO).

**Secuencia de Cálculo Universal:**

1. **Subtotal Global**: Suma de `subtotal_linea` de **TODAS las secciones** (Dispositivos + Accesorios + Mano de Obra)
2. **IVA Global**: `subtotal_global * (iva_porcentaje / 100)`
3. **Base AIU (Total Neto)**: `subtotal_global + iva_global` ⚠️ **Punto de partida del servicio**
4. **Administración**: `base_aiu * (aiu_admin_porcentaje / 100)`
5. **Imprevistos**: `base_aiu * (aiu_imprevistos_porcentaje / 100)`
6. **Utilidad**: `base_aiu * (aiu_utilidad_porcentaje / 100)`
7. **IVA sobre Utilidad**: `utilidad * (iva_porcentaje / 100)` ⚠️ **Solo sobre Utilidad (normativa colombiana - cumplimiento DIAN)**
8. **Gran Total**: `base_aiu + administracion + imprevistos + utilidad + iva_sobre_utilidad`

**Compatibilidad con Modelos:**
- ✅ **MIXTO**: AIU funciona con modelos MIXTO (aplicación universal)
- ✅ **SERVICIO**: Compatible con AIU
- ✅ **MATERIAL**: Compatible con AIU
- ✅ **EQUIPOS**: Compatible con AIU (si se activa manualmente)

**Alineación con Backend:**
- Si el backend rechaza MIXTO con AIU, se envía `modelo_tipo = "SERVICIO"` pero se mantienen **todos los items** de todas las secciones.

### 3. Inicialización de Valores AIU

La función `inicializarValoresAIUDesdePerfil()` se ejecuta automáticamente al aplicar un perfil:

- ✅ Si el perfil es `SERVICIO` o `MATERIAL`: Carga valores AIU del perfil
- ✅ Si el perfil es `MIXTO`: Permite activar AIU manualmente (aplicación universal)
- ✅ Si el perfil NO es `SERVICIO` o `MATERIAL`: Fuerza valores AIU a `0.00` (a menos que se active manualmente)

**⚠️ v2.40 - AIU Universal:**
- El usuario puede activar AIU en cualquier tipo de perfil, incluyendo MIXTO
- Cuando AIU está activo, el cálculo se aplica sobre **todas las secciones** simultáneamente
- Todas las pestañas (Dispositivos, Accesorios, Mano de Obra) se muestran cuando AIU está activo

### 4. Redraw Dinámico

Los módulos de sección implementan `redraw()` que se ejecuta automáticamente cuando:
- Se cambia de pestaña (evento `shown.bs.tab`)
- Se necesita corregir renderizado en pestañas ocultas

---

## 👁️ Visibilidad Dinámica de Secciones

### Función Principal

`gestionarVisibilidadSecciones()` se ejecuta automáticamente en `aplicarConfiguracionPerfil()`.

### Lógica de Visibilidad

#### Flags del Perfil
- `permitir_modelo_equipos`: Controla visibilidad de "Dispositivos y Equipos"
- `permitir_modelo_materiales`: Controla visibilidad de "Accesorios y Materiales"
- `permitir_modelo_servicios`: Controla visibilidad de "Mano de Obra e Instalación"
- `permitir_modelo_mixto`: Si está activo, muestra todas las secciones (a menos que flags individuales indiquen lo contrario)

#### Tabla de Comportamiento

| Perfil | Flags Activos | Pestañas Visibles |
|--------|---------------|-------------------|
| **Solo Equipos** | `equipos: true`, `materiales: false`, `servicios: false` | 1. Dispositivos y Equipos (única visible) |
| **Mantenimiento** | `equipos: false`, `materiales: true`, `servicios: true` | 2. Accesorios y 3. Mano de Obra |
| **Proyecto Integral** | `mixto: true` (o todos en `true`) | Las 3 secciones disponibles |

### Activación Automática

Tras actualizar la visibilidad:
1. Se desactivan todas las pestañas
2. Se busca la primera pestaña visible
3. Se activa automáticamente usando `new bootstrap.Tab(elemento).show()`
4. Se actualiza el panel correspondiente

### Sincronización con Guardado

**Modo Estándar:**
- ✅ `guardarCotizacion()` solo recolecta items de secciones visibles
- ✅ `recalcularTodo()` solo suma subtotales de secciones visibles
- ✅ Función helper `esSeccionVisible(seccion)` valida visibilidad

**Modo AIU Universal (v2.40):**
- ✅ `guardarCotizacion()` recolecta items de **TODAS las secciones** (sin filtrar por visibilidad)
- ✅ `recalcularTodo()` suma subtotales de **TODAS las secciones** (cálculo integral)
- ✅ Todas las pestañas se muestran automáticamente cuando AIU está activo
- ✅ El cálculo AIU se aplica sobre la suma global de todos los ítems

---

## 🔌 API Pública

### `w.CotizacionEditorCore`

#### Métodos Principales

```javascript
// Inicialización
w.CotizacionEditorCore.init()

// Gestión de Perfiles
w.CotizacionEditorCore.cargarPerfilesConfiguracion()
w.CotizacionEditorCore.cargarDetallePerfil(perfilId)
w.CotizacionEditorCore.poblarSelectorPerfiles()
w.CotizacionEditorCore.aplicarConfiguracionPerfil()

// Visibilidad
w.CotizacionEditorCore.gestionarVisibilidadSecciones()
w.CotizacionEditorCore.esSeccionVisible(seccion)

// Totales
w.CotizacionEditorCore.actualizarPanelTotales()
w.CotizacionEditorCore.recalcularTodo()

// Estado
w.CotizacionEditorCore.getConfiguracionActiva()
w.CotizacionEditorCore.getEsAiuActivo()
w.CotizacionEditorCore.setEsAiuActivo(valor)
w.CotizacionEditorCore.getSectionModules()
```

### Módulos de Sección

Cada módulo expone:

```javascript
// Dispositivos
w.CotizacionEditorDispositivos.init()
w.CotizacionEditorDispositivos.agregarFila()
w.CotizacionEditorDispositivos.obtenerSubtotal(esAiuActivo)
w.CotizacionEditorDispositivos.obtenerItems()
w.CotizacionEditorDispositivos.actualizarColumnas(tipoPlantilla)
w.CotizacionEditorDispositivos.redraw()

// Accesorios
w.CotizacionEditorAccesorios.init()
// ... (mismos métodos)

// Mano de Obra
w.CotizacionEditorManoObra.init()
// ... (mismos métodos)
```

---

## 🔄 Flujos de Trabajo

### Flujo 1: Abrir Editor y Seleccionar Perfil

```
Usuario abre modal
    ↓
initAllTables() - Inicializa módulos de sección
    ↓
aplicarConfiguracionPerfil()
    ├── Actualiza IVA
    ├── Inicializa valores AIU
    ├── gestionarVisibilidadSecciones()
    │    ├── Lee flags del perfil
    │    ├── Oculta/muestra pestañas
    │    └── Activa primera pestaña visible
    ├── Actualiza columnas
    └── actualizarPanelTotales()
```

### Flujo 2: Cambiar Perfil de Configuración

```
Usuario selecciona nuevo perfil
    ↓
Event listener en #cotizacion-modelo-tipo
    ↓
cargarDetallePerfil(perfilId)
    ↓
aplicarConfiguracionPerfil()
    ├── gestionarVisibilidadSecciones()
    │    └── Oculta/muestra pestañas según nuevo perfil
    └── actualizarPanelTotales()
```

### Flujo 3: Agregar Fila a Sección

```
Usuario hace click en "Agregar Fila"
    ↓
Event delegation captura click
    ↓
sectionModules[seccion].agregarFila()
    ├── Calcula nextItemNumber
    ├── Crea nueva fila con datos vacíos
    ├── Scroll a nueva fila
    └── Edita celda de descripción
```

### Flujo 4: Guardar Cotización

```
Usuario hace click en "Guardar Cotización"
    ↓
guardarCotizacion()
    ├── Valida campos obligatorios
    ├── Recolecta items:
    │    ├── Modo Estándar: Solo de secciones visibles
    │    └── Modo AIU: De TODAS las secciones (universal)
    ├── Valida compatibilidad AIU (si aplica):
    │    └── Si modelo_tipo = MIXTO y AIU activo:
    │         └── Envía como "SERVICIO" pero mantiene todos los items
    ├── Construye payload
    ├── Envía POST a /api/v1/cotizaciones/bulk-save/
    └── Muestra resultado
```

### Flujo 5: Recalcular Totales

```
Usuario edita cantidad o costo unitario
    ↓
cellEdited callback en módulo de sección
    ↓
recalcularSubtotalLinea()
    ├── Calcula precio_unitario_venta
    ├── Calcula subtotal_linea
    └── actualizarPanelTotales()
        └── recalcularTodo()
            ├── Suma subtotales de secciones visibles
            ├── Calcula AIU (si aplica)
            ├── Calcula IVA
            └── Actualiza UI
```

---

## ⚙️ Configuración y Uso

### Requisitos Previos

1. **Dependencias Globales:**
   - Tabulator (CDN)
   - Bootstrap 5
   - w.notyf (Notificaciones)

2. **Orden de Carga de Scripts:**
   ```html
   <!-- 1. Módulos de sección -->
   <script src="editor_seccion_dispositivos.js"></script>
   <script src="editor_seccion_accesorios.js"></script>
   <script src="editor_seccion_mano_obra.js"></script>
   
   <!-- 2. Core Manager -->
   <script src="cotizacion_editor_core.js"></script>
   ```

### Inicialización Automática

El módulo se inicializa automáticamente cuando el DOM está listo:

```javascript
if (d.readyState === 'loading') {
  d.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
```

### Uso Manual

```javascript
// Inicializar manualmente
await w.CotizacionEditorCore.init();

// Cargar perfiles
await w.CotizacionEditorCore.cargarPerfilesConfiguracion();

// Aplicar perfil
await w.CotizacionEditorCore.cargarDetallePerfil(1);
await w.CotizacionEditorCore.aplicarConfiguracionPerfil();
```

---

## 🐛 Troubleshooting

### Problema: Pestañas no se muestran/ocultan

**Solución:**
1. Verificar que `gestionarVisibilidadSecciones()` se ejecuta en `aplicarConfiguracionPerfil()`
2. Verificar flags del perfil en consola: `w.CotizacionEditorCore.getConfiguracionActiva()`
3. Verificar que los elementos del DOM existen: `resolveElement('#tab-dispositivos')`

### Problema: Error "hasAttribute is not a function"

**Solución:**
- Usar `resolveElement()` en lugar de `d.querySelector()` directamente
- Validar que el elemento es `HTMLElement` antes de usar métodos

### Problema: Totales incorrectos

**Solución:**
1. Verificar que `recalcularTodo()` solo suma secciones visibles
2. Verificar modo AIU: `w.CotizacionEditorCore.getEsAiuActivo()`
3. Verificar valores AIU en inputs o perfil

### Problema: Tabla no se renderiza en pestaña oculta

**Solución:**
- El método `redraw()` se ejecuta automáticamente al cambiar de pestaña
- Si persiste, llamar manualmente: `w.CotizacionEditorDispositivos.redraw()`

### Problema: Items de secciones ocultas se guardan

**Solución:**
- **Modo Estándar**: Verificar que `guardarCotizacion()` usa `esSeccionVisible()` antes de recolectar items
- **Modo AIU**: En modo AIU universal, se incluyen items de todas las secciones (comportamiento esperado)
- Verificar logs en consola: `[cotizacion-editor-core] ⚠️ Omitiendo items de sección...`

---

## 🎯 AIU Universal en Modelos MIXTO (v2.40)

### Descripción

El sistema ahora permite aplicar AIU (Administración, Imprevistos, Utilidad) en cotizaciones de tipo **MIXTO**, calculando sobre **todos los ítems** de **todas las secciones** simultáneamente.

### Justificación Legal (Colombia)

**Módulos Integrados:**
- Al aplicar AIU sobre "Dispositivos", "Accesorios" y "Mano de Obra" simultáneamente, se trata la cotización como un **contrato de Obra o Servicio Integral**.

**Base Imponible:**
- Al sumar el IVA de los dispositivos a la base del AIU, se protege el margen, ya que se calcula la administración sobre el **costo real de adquisición** (que incluye IVA).

**Cumplimiento DIAN:**
- El único IVA que se reporta como "impuesto por servicios" es el calculado sobre la utilidad.
- El IVA de los dispositivos se trata como un mayor valor del costo de los insumos.

### Implementación Técnica

#### Cálculo Universal

```javascript
// 1. Subtotal Global (TODAS las secciones)
subtotal_global = suma(dispositivos + accesorios + mano_obra)

// 2. IVA Global
iva_global = subtotal_global * (iva_porcentaje / 100)

// 3. Base AIU (Total Neto)
base_aiu = subtotal_global + iva_global

// 4. Valores AIU
administracion = base_aiu * (aiu_admin_porcentaje / 100)
imprevistos = base_aiu * (aiu_imprevistos_porcentaje / 100)
utilidad = base_aiu * (aiu_utilidad_porcentaje / 100)

// 5. IVA sobre Utilidad (único impuesto del servicio)
iva_sobre_utilidad = utilidad * (iva_porcentaje / 100)

// 6. Gran Total
gran_total = base_aiu + administracion + imprevistos + utilidad + iva_sobre_utilidad
```

#### Visibilidad de Secciones

Cuando `esAiuActivo = true`:
- ✅ Todas las pestañas (Dispositivos, Accesorios, Mano de Obra) se muestran automáticamente
- ✅ El usuario puede agregar items en cualquier sección
- ✅ El cálculo incluye todos los items independientemente de la sección

#### Alineación con Backend

Si el backend rechaza `modelo_tipo = "MIXTO"` con `es_aiu = true`:
- Se envía `modelo_tipo = "SERVICIO"` en el payload
- Se mantienen **todos los items** de todas las secciones
- El backend recibe todos los items pero con un tipo compatible

### Resumen Económico

El panel de totales muestra:

**Modo AIU Universal:**
```
1. Subtotal Todos los Ítems: $XXX,XXX
2. IVA Ítems: $XX,XXX
3. Base de Cotización (Subtotal Neto): $XXX,XXX
4. Costos Operativos (A.I.U):
   - Administración: $XX,XXX
   - Imprevistos: $XX,XXX
   - Utilidad: $XX,XXX
5. IVA sobre Utilidad (19%): $XX,XXX
6. TOTAL A PAGAR: $XXX,XXX
```

### Cambios Implementados

1. ✅ **Eliminación de Restricción**: AIU funciona con cualquier `modelo_tipo`, incluyendo MIXTO
2. ✅ **Cálculo Integral**: Suma de todas las secciones en modo AIU (sin filtrar por visibilidad)
3. ✅ **Recolección Universal**: Items de todas las secciones se incluyen cuando AIU está activo
4. ✅ **Visibilidad Automática**: Todas las pestañas se muestran cuando AIU está activo
5. ✅ **Alineación Backend**: Envío de tipo compatible manteniendo todos los items

---

## 📝 Notas de Implementación

### Correcciones Aplicadas

1. ✅ **Función faltante**: `inicializarValoresAIUDesdePerfil()` implementada
2. ✅ **Cálculo AIU**: IVA solo sobre Utilidad (normativa colombiana)
3. ✅ **AIU Universal**: Aplicación de AIU en modelos MIXTO con cálculo integral
4. ✅ **Cálculo Integral**: Suma de todas las secciones en modo AIU
5. ✅ **ReferenceError**: Variables correctamente definidas en ámbito
6. ✅ **hasAttribute error**: Uso de `resolveElement()` para validación
7. ✅ **Redraw en pestañas**: Listener `shown.bs.tab` implementado
8. ✅ **Eliminación optimizada**: Un solo clic para eliminar items
9. ✅ **Resumen Económico**: Estructura lineal y secuencial sin redundancias
10. ✅ **Error 422 corregido**: Validación previa de compatibilidad AIU con modelo_tipo
11. ✅ **MultipleObjectsReturned corregido**: Refactorización de `get_configuracion_cotizacion` para soportar catálogo de perfiles
12. ✅ **Zero Trust aplicado**: Normalización y validación estricta en obtención de configuración
13. ✅ **Excepción personalizada**: `ConfiguracionNoEncontrada` implementada para manejo de errores
14. ✅ **Soporte perfil_id**: Funciones aceptan `perfil_id` opcional para buscar perfiles específicos
15. ✅ **Generación de PDF Dinámico**: Implementación completa con WeasyPrint, agrupación modular, resumen económico secuencial
16. ✅ **Infraestructura WeasyPrint**: Dependencias de sistema optimizadas, corrección de errores de librerías
17. ✅ **Filtro de Moneda COP**: Formateo profesional de valores monetarios en formato colombiano
18. ✅ **Sanitización de Texto**: Limpieza de caracteres problemáticos para evitar errores en WeasyPrint
19. ✅ **Limpieza de Estilos CSS**: Eliminación de propiedades no soportadas (`pointer-events`, `box-shadow`, `:hover`)

### Mejoras de Rendimiento

1. ✅ Tablas independientes por sección (mejor procesamiento DOM)
2. ✅ Redraw solo cuando es necesario (cambio de pestaña)
3. ✅ Cálculo de totales optimizado (filtrado por visibilidad en modo estándar, universal en modo AIU)
4. ✅ Payload optimizado (solo campos necesarios según modo)

### Mejoras de UX

1. ✅ Activación automática de primera pestaña visible
2. ✅ Ocultación limpia de pestañas no permitidas
3. ✅ Feedback visual claro de secciones disponibles

---

## 🔗 Referencias

- **Arquitectura General**: `documentacion/arquitectura_general.md`
- **Tabulator Documentation**: https://tabulator.info/
- **Bootstrap 5 Tabs**: https://getbootstrap.com/docs/5.0/components/navs-tabs/

---

**Última Actualización:** 2026-02-XX  
**Versión:** 2.40 (AIU Universal + PDF Dinámico)  
**Estado:** ✅ Funcional y Documentado

### Changelog v2.40 (AIU Universal + Zero Trust + PDF Dinámico)

- ✅ **2026-02-XX**: Implementación de AIU Universal en modelos MIXTO
- ✅ **2026-02-XX**: Cálculo integral sobre todas las secciones
- ✅ **2026-02-XX**: Eliminación de restricciones de validación
- ✅ **2026-XX**: Resumen Económico reestructurado (estructura lineal)
- ✅ **2026-XX**: Corrección de error 422 en guardado con AIU
- ✅ **2026-XX**: Optimización de eliminación de items (un solo clic)
- ✅ **2026-XX**: Corrección de error `MultipleObjectsReturned` en obtención de configuración
- ✅ **2026-XX**: Refactorización de `get_configuracion_cotizacion` para soportar catálogo de perfiles
- ✅ **2026-XX**: Implementación de excepción `ConfiguracionNoEncontrada` para manejo de errores
- ✅ **2026-XX**: Aplicación de Zero Trust en normalización de configuración (validación estricta, normalización de Decimales)
- ✅ **2026-XX**: Soporte para `perfil_id` opcional en funciones de configuración
- ✅ **2026-XX**: **Generación de PDF Dinámico v2.40** - Implementación completa con WeasyPrint
  - Endpoint `/api/v1/cotizaciones/{id}/pdf/` para generación de PDFs
  - Agrupación dinámica de items por `seccion_modulo` (1.0, 2.0, 3.0)
  - Renderizado condicional de secciones (solo muestra tablas con datos)
  - Resumen económico secuencial alineado con el editor
  - Formateo de moneda COP con filtro personalizado `currency_cop`
  - Sanitización de texto para evitar errores en WeasyPrint
  - Normalización de valores (Decimal) para evitar errores de tipo
  - Marca de agua para cotizaciones ACEPTADAS
  - Campos obligatorios `atencion_a` y `asunto` en cabecera
- ✅ **2026-XX**: **Infraestructura WeasyPrint** - Dependencias de sistema optimizadas
  - Actualización de Dockerfiles con dependencias WeasyPrint (Debian Trixie/Bookworm)
  - Versiones sincronizadas: `weasyprint>=61.0` y `pydyf>=0.10.0`
  - Corrección de error `OSError: cannot load library 'gobject-2.0-0'`
  - Corrección de error `'super' object has no attribute 'transform'`
  - Limpieza de estilos CSS (eliminación de `pointer-events`, `box-shadow`, `:hover`)
  - Filtro personalizado `currency_cop` para formateo de moneda colombiana