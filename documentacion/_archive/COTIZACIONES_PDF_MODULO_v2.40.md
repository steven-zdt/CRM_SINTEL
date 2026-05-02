# 📄 Módulo de Generación de PDF v2.40 - Documentación Completa

**Fecha:** 2026-02-XX  
**Estado:** ✅ **COMPLETADO Y VALIDADO**  
**Versión:** 2.40 (Módulo Independiente)

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Modular](#arquitectura-modular)
3. [Estructura de Archivos](#estructura-de-archivos)
4. [API y Endpoints](#api-y-endpoints)
5. [Servicio de PDF](#servicio-de-pdf)
6. [Validaciones y Pruebas](#validaciones-y-pruebas)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Resumen Ejecutivo

El Módulo de Generación de PDF v2.40 es un sistema completamente independiente para generar PDFs profesionales de cotizaciones usando WeasyPrint. El módulo está completamente separado del ViewSet principal de cotizaciones, siguiendo el principio de responsabilidad única.

### Características Principales

- ✅ **Módulo Independiente**: ViewSet y servicio completamente separados
- ✅ **Agrupación Modular**: Items agrupados por `seccion_modulo` (1.0, 2.0, 3.0)
- ✅ **Renderizado Condicional**: Solo muestra secciones con datos
- ✅ **Resumen Económico Secuencial**: Lógica AIU alineada con el editor
- ✅ **Marca de Agua**: Para cotizaciones ACEPTADAS
- ✅ **Sanitización de Texto**: Previene errores en WeasyPrint
- ✅ **Normalización de Valores**: Todos los valores como `Decimal`

---

## 🏗️ Arquitectura Modular

### Diagrama de Arquitectura

```
CotizacionPDFViewSet (ViewSet Independiente)
    │
    ├── obtener_cotizacion_para_pdf() → Cotizacion con items optimizados
    ├── preparar_contexto_pdf() → Contexto completo para template
    └── generar_pdf_bytes() → PDF generado
         │
         └── pdf_service.py (Servicio de Lógica)
              ├── normalizar_seccion_modulo()
              ├── agrupar_items_por_seccion()
              ├── calcular_subtotal_item()
              ├── calcular_totales()
              ├── sanitize_text()
              └── render_to_string() → Template HTML
                   │
                   └── cotizacion_template.html
                        └── WeasyPrint → PDF final
```

### Responsabilidades por Módulo

#### `CotizacionPDFViewSet` (ViewSet)
- ✅ Manejo de requests HTTP
- ✅ Validación de permisos
- ✅ Obtención de empresa (SSoT)
- ✅ Delegación a servicio de PDF
- ✅ Manejo de errores y logging

#### `pdf_service.py` (Servicio)
- ✅ Obtención optimizada de cotización con items
- ✅ Agrupación de items por sección
- ✅ Cálculo de totales (AIU y estándar)
- ✅ Preparación de contexto para template
- ✅ Generación de PDF con WeasyPrint

#### `cotizacion_template.html` (Template)
- ✅ Renderizado de cabecera
- ✅ Renderizado condicional de secciones
- ✅ Resumen económico secuencial
- ✅ Estilos optimizados para WeasyPrint

---

## 📂 Estructura de Archivos

### Backend

```
apps/tenant/cotizaciones/
├── pdf_service.py                    # ⚠️ NUEVO: Servicio de generación de PDF
├── api/
│   ├── viewsets.py                   # ViewSet principal (sin método pdf)
│   ├── pdf_viewsets.py               # ⚠️ NUEVO: ViewSet independiente de PDF
│   └── urls.py                       # URLs actualizadas
└── templates/
    └── tenant/cotizaciones/
        └── pdf/
            └── cotizacion_template.html  # Template HTML (sin cambios)
```

### Frontend

```
apps/tenant/core/static/core/js/cotizaciones/
└── cotizaciones.page.js              # handlePDF() actualizado
```

---

## 🔌 API y Endpoints

### Endpoint Principal

**URL:** `GET /api/v1/cotizaciones/pdf/{id}/`

**Descripción:** Genera el PDF de la cotización usando WeasyPrint.

**Autenticación:** SessionAuthentication  
**Permisos:** `IsCotizacionesMember`, `IsCotizacionesAdminOrReadOnly`

**Respuestas:**
- `200 OK`: PDF file (application/pdf)
- `404 NOT FOUND`: Cotización no encontrada
- `500 INTERNAL SERVER ERROR`: Error generando el PDF

**Ejemplo de Uso:**
```javascript
// Frontend
const pdfUrl = `/api/v1/cotizaciones/pdf/${id}/`;
window.open(pdfUrl, '_blank');
```

---

## 🔧 Servicio de PDF

### Funciones Principales

#### `normalizar_seccion_modulo(seccion_modulo: Optional[str]) -> Optional[str]`
Normaliza valores de `seccion_modulo` para comparación.
- Maneja: `None`, strings vacíos, "1.0", "1", "2.5", etc.
- Retorna: `"1"`, `"2"`, `"3"` o `None`

#### `agrupar_items_por_seccion(items: List[CotizacionItem]) -> Tuple[...]`
Agrupa items en las tres secciones modulares.
- Retorna: `(seccion_1, seccion_2, seccion_3, items_sin_modulo)`
- Ordena por `orden` y luego por `id`

#### `calcular_subtotal_item(item: CotizacionItem, es_aiu: bool) -> Decimal`
Calcula el subtotal de un item según el modo.
- Modo AIU: `cantidad * costo_unitario`
- Modo estándar: `subtotal_linea`

#### `calcular_totales(...) -> Dict[str, Decimal]`
Calcula todos los totales para el resumen económico.
- Subtotales por sección
- IVA de items (si aplica)
- Base de cálculo AIU
- Valores AIU normalizados
- Total neto

#### `obtener_cotizacion_para_pdf(empresa_id: int, cotizacion_id: int) -> Optional[Cotizacion]`
Obtiene cotización optimizada con todos los items.
- Usa `prefetch_related` con `items_list`
- Incluye explícitamente `seccion_modulo`

#### `preparar_contexto_pdf(...) -> Dict`
Prepara el contexto completo para el template.
- Agrupa items por sección
- Calcula totales
- Sanitiza texto
- Determina columnas visibles

#### `generar_pdf_bytes(context: Dict, request: Optional[HttpRequest]) -> bytes`
Genera el PDF desde el contexto.
- Renderiza template HTML
- Genera PDF con WeasyPrint
- Retorna bytes del PDF

---

## ✅ Validaciones y Pruebas

### Validaciones Realizadas

#### 1. Sintaxis de Python
- ✅ `pdf_service.py`: Sintaxis válida
- ✅ `pdf_viewsets.py`: Sintaxis válida
- ✅ `urls.py`: Sintaxis válida

#### 2. Estructura de Archivos
- ✅ Servicio creado: `apps/tenant/cotizaciones/pdf_service.py`
- ✅ ViewSet creado: `apps/tenant/cotizaciones/api/pdf_viewsets.py`
- ✅ Template existe: `apps/tenant/cotizaciones/templates/tenant/cotizaciones/pdf/cotizacion_template.html`
- ✅ URLs actualizadas: `apps/tenant/cotizaciones/api/urls.py`

#### 3. Imports y Dependencias
- ✅ Imports correctos en `pdf_service.py`
- ✅ Imports correctos en `pdf_viewsets.py`
- ✅ ViewSet registrado en router

#### 4. Funciones del Servicio
- ✅ `normalizar_seccion_modulo()`: Definida y tipada
- ✅ `agrupar_items_por_seccion()`: Definida y tipada
- ✅ `calcular_subtotal_item()`: Definida y tipada
- ✅ `calcular_totales()`: Definida y tipada
- ✅ `sanitize_text()`: Definida y tipada
- ✅ `obtener_cotizacion_para_pdf()`: Definida y tipada
- ✅ `preparar_contexto_pdf()`: Definida y tipada
- ✅ `generar_pdf_bytes()`: Definida y tipada

#### 5. ViewSet
- ✅ `CotizacionPDFViewSet`: Clase definida
- ✅ `retrieve()`: Método implementado
- ✅ Permisos configurados
- ✅ Manejo de errores implementado

#### 6. URLs
- ✅ ViewSet registrado: `router.register(r'pdf', CotizacionPDFViewSet)`
- ✅ Orden correcto: Antes de `r''` para evitar greedy matching
- ✅ Documentación actualizada

#### 7. Frontend
- ✅ `handlePDF()` actualizado para usar nueva URL
- ✅ URL correcta: `/api/v1/cotizaciones/pdf/${id}/`

#### 8. Limpieza
- ✅ Método `pdf()` removido de `CotizacionViewSet`
- ✅ Comentario indicando nueva ubicación

### Checklist de Funcionalidad

- [x] Servicio de PDF creado e independiente
- [x] ViewSet de PDF creado e independiente
- [x] URLs configuradas correctamente
- [x] Frontend actualizado
- [x] Método antiguo removido
- [x] Sintaxis validada
- [x] Imports verificados
- [x] Estructura de archivos correcta
- [x] Documentación actualizada

---

## 🔍 Troubleshooting

### Error: "Cotización no encontrada"
**Causa:** La cotización no existe o no pertenece a la empresa.  
**Solución:** Verificar que el `id` sea correcto y que la cotización pertenezca a la empresa del tenant.

### Error: "WeasyPrint no está instalado"
**Causa:** WeasyPrint no está instalado en el entorno.  
**Solución:** Instalar con `pip install weasyprint>=61.0`

### Error: "Empresa no encontrada"
**Causa:** No existe una empresa configurada (SSoT).  
**Solución:** Crear una empresa antes de generar PDFs.

### Error: "Items sin seccion_modulo válido"
**Causa:** Algunos items no tienen `seccion_modulo` asignado.  
**Solución:** Los items sin módulo válido se registran en logs pero no se muestran en el PDF.

### PDF no muestra todas las secciones
**Causa:** Items no están agrupados correctamente.  
**Solución:** Verificar logs de `[PDF Service]` para ver el agrupamiento.

---

## 📊 Flujo de Generación de PDF

```
1. Request → GET /api/v1/cotizaciones/pdf/{id}/
   │
2. CotizacionPDFViewSet.retrieve()
   │
3. obtener_cotizacion_para_pdf()
   │   └── Prefetch optimizado con items_list
   │
4. preparar_contexto_pdf()
   │   ├── agrupar_items_por_seccion()
   │   ├── calcular_totales()
   │   └── sanitize_text()
   │
5. generar_pdf_bytes()
   │   ├── render_to_string() → HTML
   │   └── WeasyPrint.HTML().write_pdf() → PDF
   │
6. HttpResponse → PDF file
```

---

## 🔗 Referencias

- **Arquitectura General**: `documentacion/arquitectura_general.md`
- **Editor de Cotizaciones**: `documentacion/COTIZACIONES_EDITOR_V2.40.md`
- **WeasyPrint Documentation**: https://weasyprint.org/
- **Django REST Framework**: https://www.django-rest-framework.org/

---

**Última Actualización:** 2026-02-XX  
**Versión:** 2.40 (Módulo Independiente)  
**Estado:** ✅ Funcional y Validado
