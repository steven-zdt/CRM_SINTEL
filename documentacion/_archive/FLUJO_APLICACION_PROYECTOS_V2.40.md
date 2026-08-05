# Flujo de Aplicación SINTEL v2.40 - Documentación Completa

**Fecha de Documentación:** 2026-02-20  
**Versión del Sistema:** v2.40  
**Última Actualización:** Renombramiento Equipos_Dispositivos y Eliminación de Descuentos

---

## 📋 Índice

1. [Arquitectura General](#arquitectura-general)
2. [Módulo de Cotizaciones v2.40](#módulo-de-cotizaciones-v240)
3. [Módulo de Proyectos v3.3](#módulo-de-proyectos-v33)
4. [Flujo de Navegación y Workspace](#flujo-de-navegación-y-workspace)
5. [Cambios Recientes Implementados](#cambios-recientes-implementados)

---

## 🏗️ Arquitectura General

### Principios Fundamentales

1. **Multi-Tenant Estricto (SSoT)**
   - Cada módulo está vinculado a `Empresa` como Single Source of Truth
   - Todas las consultas filtran por `empresa_id`
   - Aislamiento completo de datos entre tenants

2. **Zero Trust Architecture**
   - Normalización robusta en serializadores DRF
   - Validación estricta de entrada de usuario
   - Sanitización de HTML y limpieza de strings
   - Validación de ForeignKeys y campos numéricos

3. **Service Layer Pattern**
   - Lógica de negocio en `services.py`
   - Modelos anémicos (solo estructura de datos)
   - ViewSets delgados que delegan a servicios

4. **API-First Architecture**
   - Backend: Django REST Framework (DRF)
   - Frontend: Tabulator Factory + Vanilla JS
   - Comunicación exclusivamente vía JSON

---

## 📄 Módulo de Cotizaciones v2.40

### Estructura del Módulo

```
apps/tenant/cotizaciones/
├── models.py                    # Modelos: Cotizacion, CotizacionItem, Producto
├── services.py                  # Lógica de negocio (procesar_guardado_masivo, etc.)
├── api/
│   ├── serializers.py          # Serializadores DRF con NormalizationMixin
│   ├── viewsets.py             # CotizacionViewSet, CotizacionItemViewSet
│   └── pdf_viewsets.py         # CotizacionPDFViewSet (módulo independiente)
├── pdf_service.py              # Servicio de generación de PDFs (WeasyPrint)
└── configuracion/
    └── models.py               # ConfiguracionCotizacion (Perfiles de Configuración)
```

### Modelo de Datos

#### Cotizacion
- **Campos principales:**
  - `numero`: Auto-generado (formato: COT-XXXX-YYYY)
  - `estado`: BORRADOR, ENVIADA, ACEPTADA (inmutabilidad)
  - `modelo_tipo`: EQUIPO, MATERIAL, SERVICIO, MIXTO
  - `es_aiu`: Boolean para activar modo AIU (Colombia)
  - `aiu_admin_porcentaje`, `aiu_imprevistos_porcentaje`, `aiu_utilidad_porcentaje`
  - `subtotal`, `iva_valor`, `total_neto` (calculados)

#### CotizacionItem
- **Campos principales:**
  - `seccion_modulo`: "1.0" (Equipos), "2.0" (Accesorios), "3.0" (Mano de Obra)
  - `descripcion`, `marca`, `referencia`, `unidad`
  - `cantidad`, `costo_unitario`, `porcentaje_utilidad`
  - `precio_unitario_venta`, `subtotal_linea` (calculados)

### Flujo de Creación/Edición de Cotizaciones

```
1. Usuario hace clic en "Nueva Cotización" o "Editar"
   ↓
2. Frontend: cotizacion_editor_core.js
   - Abre modal (#modal-cotizacion-editor)
   - Carga perfiles de configuración disponibles
   - Inicializa tablas Tabulator (3 secciones)
   ↓
3. Usuario selecciona Perfil de Configuración
   - Determina visibilidad de secciones (1.0, 2.0, 3.0)
   - Aplica columnas visibles (marca, referencia)
   - Configura porcentajes de utilidad e IVA
   ↓
4. Usuario agrega items en las secciones
   - Sección 1: Equipos y Dispositivos (equipos_dispositivos)
   - Sección 2: Accesorios y Materiales (accesorios)
   - Sección 3: Mano de Obra e Instalación (mano-obra)
   ↓
5. Cálculo de Totales (Frontend)
   - actualizarPanelTotales() suma subtotales de las 3 secciones
   - Si AIU activo: calcula Administración, Imprevistos, Utilidad
   - Calcula IVA sobre Utilidad (si AIU) o IVA sobre items (si no AIU)
   ↓
6. Usuario hace clic en "Guardar"
   - guardarCotizacion() recolecta items de las 3 secciones
   - Normaliza seccion_modulo a formato "1.0", "2.0", "3.0"
   - POST /api/v1/cotizaciones/bulk-save/
   ↓
7. Backend: procesar_guardado_masivo()
   - Valida y normaliza todos los datos (Zero Trust)
   - Crea/actualiza Cotizacion
   - Crea/actualiza CotizacionItem (bulk)
   - Recalcula totales (backend es fuente de verdad)
   ↓
8. Respuesta al Frontend
   - Actualiza ID de cotización
   - Refresca grid principal
   - Cierra modal o muestra mensaje de éxito
```

### Editor Estilo Excel (Frontend)

#### Arquitectura Modular

```
editor_seccion_equipos_dispositivos.js  (Módulo 1.0)
  ├── init()                            # Inicializa Tabulator
  ├── agregarFila()                     # Agrega fila vacía
  ├── obtenerItems()                    # Recolecta items para guardar
  ├── obtenerSubtotal()                 # Calcula subtotal de sección
  └── Registro: window.CotizacionModules.equipos_dispositivos

editor_seccion_accesorios.js            (Módulo 2.0)
  └── (Misma estructura)

editor_seccion_mano_obra.js            (Módulo 3.0)
  └── (Misma estructura)

cotizacion_editor_core.js               (Orquestador)
  ├── abrir(id)                         # Carga cotización existente
  ├── initAllTables()                   # Inicializa las 3 tablas
  ├── guardarCotizacion()               # Guarda vía bulk-save
  ├── actualizarPanelTotales()          # Calcula totales globales
  └── aplicarConfiguracionPerfil()      # Aplica visibilidad de secciones
```

#### Características del Editor

- **Tabulator Factory**: Tablas interactivas estilo Excel
- **Celdas editables**: Descripción, Marca, Referencia (textarea), Cantidad, Costo (number)
- **Cálculo automático**: Precio Unit. Venta = Costo * (1 + Utilidad%)
- **Validación de índices**: Filtra valores "X.0" (solo sección), solo muestra "X.0.N"
- **Clipboard**: Soporte para copiar/pegar desde Excel

### Generación de PDFs

#### Flujo de Generación

```
1. Usuario hace clic en botón "PDF" en grid principal
   ↓
2. Frontend: handlePDF(id)
   - Abre nueva pestaña: /api/v1/cotizaciones/pdf/{id}/
   ↓
3. Backend: CotizacionPDFViewSet.pdf()
   - Obtiene cotización con prefetch_related('items')
   - Llama a pdf_service.preparar_contexto_pdf()
   ↓
4. pdf_service.py
   - Agrupa items por seccion_modulo (1.0, 2.0, 3.0)
   - Filtra por perfil_configuracion (solo secciones activas)
   - Calcula totales (subtotal_items, iva_items, base_calculo_aiu)
   - Calcula AIU si está activo
   ↓
5. Template: cotizacion_template.html
   - Renderiza secciones dinámicamente (solo las activas)
   - Muestra resumen económico con lógica AIU
   - Aplica estilos profesionales (COP, mayúsculas, etc.)
   ↓
6. WeasyPrint genera PDF
   - HTML → PDF con estilos CSS
   - Headers no-cache para evitar caché
   - Marca de agua "Aceptada" si estado = ACEPTADA
```

### Perfiles de Configuración

#### ConfiguracionCotizacion
- **Campos principales:**
  - `nombre_configuracion`: Nombre del perfil
  - `es_activo`: Boolean (solo un activo por empresa)
  - `permitir_modelo_equipos`, `permitir_modelo_materiales`, `permitir_modelo_servicios`, `permitir_modelo_mixto`
  - `porcentaje_utilidad_default`, `iva_porcentaje_default`
  - `tipo_plantilla`: EQUIPO, MATERIAL, SERVICIO, MIXTO

#### Lógica de Visibilidad
- Si `permitir_modelo_mixto = True`: Muestra todas las secciones permitidas
- Si `permitir_modelo_mixto = False`: Muestra solo secciones con flags individuales activos
- El PDF respeta esta misma lógica (solo renderiza secciones activas)

---

## 🏗️ Módulo de Proyectos v3.3

### Arquitectura Stand-Alone

El módulo de Proyectos está diseñado como **módulo completamente independiente** (stand-alone), siguiendo el patrón SSoT estricto.

#### Principios de Diseño

1. **Única Dependencia Externa**: `apps.tenant.empresa.models.Empresa` (SSoT)
2. **Loose Coupling**: No hay ForeignKeys a otras apps de negocio
3. **Snapshots**: Almacena referencias por ID + nombre (snapshots)
4. **Modelo Anémico**: Solo estructura de datos, lógica en `services.py`

### Modelo de Datos

#### Proyecto
- **Campos principales:**
  - `empresa`: ForeignKey a Empresa (SSoT)
  - `nombre`, `codigo`, `tipo_servicio`, `descripcion`
  - `fase_actual`: BORRADOR, INICIO, PLANEACION, EJECUCION, CIERRE
  - `estado_tarea`: PENDIENTE, EN_PROCESO, DETENIDO, COMPLETADO

- **Referencias Desacopladas:**
  - `cliente_id` + `cliente_nombre` (snapshot)
  - `factura_ref` (referencia a facturación)
  - `responsable_comercial_id` + `responsable_comercial_nombre`
  - `responsable_tecnico_id` + `responsable_tecnico_nombre`
  - `responsable_operativo_id` + `responsable_operativo_nombre`
  - `responsable_administrativo_id` + `responsable_administrativo_nombre`
  - `responsable_actual_id` + `responsable_actual_nombre`

- **Indicadores Financieros (Calculados):**
  - `costo_mano_obra_real`: Calculado por services.py
  - `costo_materiales_real`: Calculado por services.py
  - `utilidad_estimada`: Factura - Costos
  - `margen_rentabilidad`: (Utilidad / Factura) * 100

#### AsignacionPersonal
- Registro de talento humano asignado al proyecto
- `empleado_id` + `nombre_colaborador` (snapshot)
- `rol`: TECNICO, AYUDANTE, RESIDENTE, SISOMA
- `horas_totales_registradas`, `costo_hora`, `costo_total_asignacion`

#### PedidoProyecto
- Encabezado de solicitud de recursos
- `tipo_recurso`: MATERIALES, EQUIPOS, HERRAMIENTAS
- `fuente_suministro`: PROVEEDOR, EMPLEADO, ALMACEN
- `proveedor_id` + `proveedor_nombre` (snapshot)

#### ItemPedido
- Detalle de línea de pedido
- `material_ref`, `nombre_material`, `cantidad`, `unidad_medida`, `precio_unitario`

### Workflow de Proyectos

```
1. BORRADOR / Oportunidad
   - Responsable: Comercial
   - Acciones: Crear proyecto, definir cliente, valor proyectado
   ↓
2. INICIO (Comercial y Legal)
   - Responsable: Comercial
   - Acciones: Firmar contrato, subir acta de inicio
   ↓
3. PLANEACION (Diseño y Técnica)
   - Responsable: Técnico
   - Acciones: Crear cronograma, solicitar recursos (pedidos)
   ↓
4. EJECUCION (Operativa)
   - Responsable: Operativo
   - Acciones: Asignar personal, registrar horas, gestionar pedidos
   ↓
5. CIERRE (Administrativa)
   - Responsable: Administrativo
   - Acciones: Generar acta de entrega, informe final, calcular rentabilidad
```

### Cálculo de Rentabilidad

**Fórmula:**
```
Utilidad = Factura Venta - (Costo Materiales + Costo Nómina)
Margen = (Utilidad / Factura) * 100
```

**Fuentes de Costos:**
- **Costo Mano de Obra**: Suma de `costo_total_asignacion` de `AsignacionPersonal`
- **Costo Materiales**: Suma de `precio_unitario * cantidad` de `ItemPedido`

---

## 🧭 Flujo de Navegación y Workspace

### Estructura del Workspace

```
workspace.html
  ├── Sidebar (Navegación)
  │   ├── Empresa (SSoT)
  │   ├── Proyectos
  │   ├── Facturas
  │   ├── Contabilidad
  │   ├── Inventario
  │   ├── Clientes
  │   ├── Proveedores
  │   ├── Empleados
  │   ├── Gastos
  │   └── Cotizaciones
  │
  └── Contenido Principal
      └── Tabs dinámicos (#tab-{modulo})
```

### Navegación por Hash

- **URL Pattern**: `http://home.sintel.net.co/workspace/#cotizaciones`
- **Limpieza Automática**: Elimina parámetros obsoletos (`aplicar_descuento`, `porcentaje_descuento`)
- **Historial**: Soporte para navegación back/forward del navegador

### workspace.js

**Funciones principales:**
- `showTab(tabName)`: Muestra tab específico y oculta los demás
- `limpiarParametrosDescuento()`: Elimina parámetros obsoletos de URL
- `handleLogout()`: Maneja logout del usuario

**Eventos:**
- `DOMContentLoaded`: Inicializa navegación y limpia parámetros
- `popstate`: Maneja navegación back/forward
- `hashchange`: Limpia parámetros cuando cambia el hash

---

## 🔄 Cambios Recientes Implementados

### 1. Renombramiento: Dispositivos → Equipos_Dispositivos

**Motivación:**
- Eliminar colisiones con catálogo de productos
- Identidad única para el módulo 1.0
- Flujo DIAN limpio para cálculos

**Archivos Modificados:**
- ✅ `editor_seccion_dispositivos.js` → `editor_seccion_equipos_dispositivos.js`
- ✅ `tab_dispositivos.html`: IDs actualizados
- ✅ `modal_editor_core.html`: Referencias actualizadas
- ✅ `cotizacion_editor_core.js`: Todas las referencias actualizadas
- ✅ `cotizaciones.styles.css`: Selectores actualizados
- ✅ `assets_cotizaciones.html`: Ruta del script actualizada

**Cambios Específicos:**
- `MOD = 'editor-equipos-dispositivos'`
- `GRID_ID = '#grid-cotizacion-editor-equipos-dispositivos'`
- `SECCION = 'equipos_dispositivos'`
- `window.CotizacionModules.equipos_dispositivos`
- Eliminado alias `seccion_1`

### 2. Eliminación Completa de Descuentos

**Motivación:**
- Funcionalidad no utilizada
- Simplificar código y cálculos
- Eliminar parámetros obsoletos de URL

**Archivos Modificados:**
- ✅ `models.py`: Eliminados campos `aplicar_descuento`, `porcentaje_descuento`
- ✅ `serializers.py`: Eliminadas referencias en NormalizationMixin
- ✅ `services.py`: Eliminada lógica de cálculo de descuento
- ✅ `pdf_service.py`: Eliminada lógica de descuento en PDF
- ✅ `cotizacion_template.html`: Eliminadas filas de descuento
- ✅ `cotizacion_editor_core.js`: Eliminada lógica de descuento
- ✅ `panel_totales.html`: Eliminado botón y campos de descuento
- ✅ `workspace.js`: Función de limpieza de parámetros de URL

**Migración:**
- `0004_remove_descuento_fields.py`: Elimina campos de la base de datos

### 3. Correcciones de Renderizado (Módulo 1.0)

**Problemas Resueltos:**
- Tabla no se pintaba al agregar filas
- Panel oculto por lógica de visibilidad (`d-none`)
- Duplicación de índices (X.0 vs X.0.1)

**Soluciones Implementadas:**
- Remover `d-none` temporalmente en `init()` y `agregarFila()`
- Patrón de redibujo forzado: `table.redraw(true)` + `requestAnimationFrame()`
- Filtrado estricto de índices: Solo mostrar valores "X.0.N" donde N > 0
- Eliminación de estilos CSS con `!important` que interferían con Tabulator

### 4. Validación Backend (Módulo 1.0)

**Hallazgos:**
- ✅ No hay bloqueos ni restricciones para `seccion_modulo = "1.0"`
- ✅ Serializadores aceptan "1.0" sin problemas
- ✅ Service normaliza correctamente a "1.0"
- ✅ ViewSet no valida ni bloquea por `seccion_modulo`

**Conclusión:**
- El problema era exclusivamente frontend (visibilidad/inicialización)
- Backend funcionaba correctamente desde el inicio

---

## 🔐 Seguridad y Validación

### Zero Trust Architecture

**NormalizationMixin (serializers.py):**
- **UPPERCASE_FIELDS**: `marca`, `referencia`, `unidad`, `seccion_modulo`
- **TEXT_FIELDS**: Sanitización HTML con bleach
- **DECIMAL_FIELDS**: Validación estricta a Decimal
- **NON_NEGATIVE_FIELDS**: Validación de rangos

**Validaciones en Services:**
- Validación de existencia de IDs referenciales
- Normalización de `seccion_modulo` a formato "X.0"
- Validación de descripción no vacía
- Validación de rangos numéricos (cantidad > 0, porcentajes 0-100)

---

## 📊 Flujo de Datos Completo

### Crear Nueva Cotización

```
Frontend (JS)
  ↓
POST /api/v1/cotizaciones/bulk-save/
  ↓
Backend: CotizacionViewSet.bulk_save()
  ↓
Service: procesar_guardado_masivo()
  ├── Normalización (Zero Trust)
  ├── Validación de datos
  ├── Crear/Actualizar Cotizacion
  ├── Crear/Actualizar CotizacionItem (bulk)
  └── Recalcular totales
  ↓
Response JSON
  ↓
Frontend: Actualizar UI
```

### Generar PDF

```
Frontend: handlePDF(id)
  ↓
GET /api/v1/cotizaciones/pdf/{id}/
  ↓
Backend: CotizacionPDFViewSet.pdf()
  ↓
Service: pdf_service.preparar_contexto_pdf()
  ├── Agrupar items por seccion_modulo
  ├── Filtrar por perfil_configuracion
  ├── Calcular totales
  └── Preparar contexto para template
  ↓
Template: cotizacion_template.html
  ↓
WeasyPrint: HTML → PDF
  ↓
Response: PDF binary
```

---

## 🎯 Próximos Pasos Recomendados

1. **Integración Proyectos-Cotizaciones**
   - Vincular cotizaciones a proyectos
   - Usar valor de cotización como `valor_contrato_proyectado`

2. **Mejoras de Performance**
   - Optimizar queries con `select_related` y `prefetch_related`
   - Implementar caché para perfiles de configuración

3. **Testing**
   - Tests unitarios para servicios
   - Tests de integración para flujo completo
   - Tests E2E para editor de cotizaciones

---

## 📝 Notas Técnicas

### Convenciones de Nomenclatura

- **Módulos JS**: `editor_seccion_{nombre}.js`
- **Constantes**: `MOD`, `GRID_ID`, `SECCION`, `MODULO`
- **Registro Global**: `window.CotizacionModules.{nombre}`
- **IDs HTML**: `#grid-cotizacion-editor-{nombre}`, `#panel-{nombre}`, `#tab-{nombre}`

### Patrones de Código

- **Promesas Tabulator**: `table.addRow(data, true).then(row => { ... })`
- **Redibujo Forzado**: `table.redraw(true)` + `requestAnimationFrame()`
- **Filtrado de Índices**: `!itemValue.endsWith('.0') && itemValue.split('.').length >= 3`

---

**Documentación generada automáticamente**  
**Última revisión:** 2026-02-20
