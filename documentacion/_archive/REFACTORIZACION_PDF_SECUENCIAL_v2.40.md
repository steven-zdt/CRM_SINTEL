# 🔄 Refactorización de Mapeo Secuencial PDF v2.40

**Fecha:** 2026-02-XX  
**Estado:** ✅ **COMPLETADO**  
**Versión:** 2.40 (Mapeo Secuencial con Perfil de Configuración)

---

## 📋 Resumen Ejecutivo

Se refactorizó el módulo de generación de PDF para respetar la secuencia del Perfil de Configuración y mostrar las tablas por separado, incluso si no tienen datos, siempre que el perfil lo permita.

### Cambios Principales

1. ✅ **Diccionario Estático Ordenado**: Reemplazado bucle genérico por diccionario estático con llaves "1.0", "2.0", "3.0"
2. ✅ **Filtrado Explícito**: Items filtrados explícitamente por `seccion_modulo` usando `startswith()`
3. ✅ **Cruce con Perfil**: Visibilidad de secciones determinada por `permitir_modelo_equipos`, `permitir_modelo_materiales`, `permitir_modelo_servicios`
4. ✅ **Eliminación de Fallback**: Items sin módulo se reportan como ERROR DE INTEGRIDAD (WARNING), NO se asignan automáticamente
5. ✅ **Template Actualizado**: Usa `secciones_render` con iteración ordenada y verificación de `mostrar`

---

## 🔧 Cambios Técnicos

### 1. Nueva Función: `obtener_secciones_render()`

**Ubicación:** `apps/tenant/cotizaciones/pdf_service.py`

**Antes:**
```python
def agrupar_items_por_seccion(items: List[CotizacionItem]) -> Tuple[...]:
    # Bucle genérico sobre items
    # Fallback automático a Sección 1
```

**Después:**
```python
def obtener_secciones_render(
    items: List[CotizacionItem],
    perfil_configuracion
) -> Dict[str, Dict]:
    """
    Obtiene las secciones para renderizar usando diccionario estático ordenado.
    
    Estructura retornada:
    {
        "1.0": {
            "titulo": "Dispositivos y Equipos",
            "items": [...],
            "mostrar": bool  # Según permitir_modelo_equipos
        },
        "2.0": {
            "titulo": "Accesorios y Materiales",
            "items": [...],
            "mostrar": bool  # Según permitir_modelo_materiales
        },
        "3.0": {
            "titulo": "Mano de Obra e Instalación",
            "items": [...],
            "mostrar": bool  # Según permitir_modelo_servicios
        }
    }
    """
```

**Características:**
- ✅ Diccionario estático ordenado con llaves "1.0", "2.0", "3.0"
- ✅ Filtrado explícito por `seccion_modulo` usando `startswith()`
- ✅ Cruce con permisos del perfil (`permitir_modelo_*`)
- ✅ Items sin módulo reportados como ERROR DE INTEGRIDAD (WARNING)
- ✅ NO hay fallback automático a Sección 1

### 2. Refactorización: `preparar_contexto_pdf()`

**Cambios:**
- ✅ Ahora acepta `perfil_id` opcional
- ✅ Obtiene perfil de configuración usando `get_configuracion_cotizacion()`
- ✅ Usa `obtener_secciones_render()` en lugar de `agrupar_items_por_seccion()`
- ✅ Incluye `secciones_render` en el contexto
- ✅ Mantiene compatibilidad con `seccion_1`, `seccion_2`, `seccion_3` (deprecated)

**Firma:**
```python
def preparar_contexto_pdf(
    cotizacion: Cotizacion,
    empresa: Empresa,
    request: Optional[HttpRequest] = None,
    perfil_id: Optional[int] = None  # ⚠️ NUEVO
) -> Dict:
```

### 3. Actualización: `CotizacionPDFViewSet.retrieve()`

**Cambios:**
- ✅ Extrae `perfil_id` de `request.query_params` (opcional)
- ✅ Pasa `perfil_id` a `preparar_contexto_pdf()`

**Código:**
```python
# ⚠️ v2.40: Obtener perfil_id del request si está disponible (opcional)
perfil_id = request.query_params.get('perfil_id', None)
if perfil_id:
    try:
        perfil_id = int(perfil_id)
    except (ValueError, TypeError):
        perfil_id = None
        logger.warning(f"[PDF ViewSet] perfil_id inválido en query params: {request.query_params.get('perfil_id')}")

# Preparar contexto para el template
context = preparar_contexto_pdf(cotizacion, empresa, request, perfil_id=perfil_id)
```

### 4. Actualización: Template HTML

**Ubicación:** `apps/tenant/cotizaciones/templates/tenant/cotizaciones/pdf/cotizacion_template.html`

**Antes:**
```django
{% if seccion_1 %}
<div class="seccion-items">
    <div class="seccion-header">1. Dispositivos y Equipos</div>
    ...
</div>
{% endif %}
```

**Después:**
```django
{% for seccion_key, seccion_data in secciones_render.items %}
    {% if seccion_data.mostrar %}
    <div class="seccion-items">
        <div class="seccion-header">{{ seccion_key|slice:":1" }}. {{ seccion_data.titulo }}</div>
        {% if seccion_data.items %}
        <table class="items-table">
            ...
        </table>
        {% else %}
        <!-- Sección vacía pero visible según perfil -->
        <div style="padding: 10px; text-align: center; color: #999; font-style: italic;">
            No hay ítems en esta sección
        </div>
        {% endif %}
    </div>
    {% endif %}
{% endfor %}
```

**Características:**
- ✅ Itera sobre `secciones_render.items()` (orden garantizado: 1.0, 2.0, 3.0)
- ✅ Verifica `seccion_data.mostrar` (según perfil)
- ✅ Muestra tabla si hay items
- ✅ Muestra mensaje "No hay ítems en esta sección" si está vacía pero visible

---

## 🎯 Lógica de Visibilidad

### Mapeo de Secciones a Permisos

| Sección | Llave | Permiso del Perfil | Título |
|---------|-------|-------------------|--------|
| Dispositivos | "1.0" | `permitir_modelo_equipos` | "Dispositivos y Equipos" |
| Accesorios | "2.0" | `permitir_modelo_materiales` | "Accesorios y Materiales" |
| Mano de Obra | "3.0" | `permitir_modelo_servicios` | "Mano de Obra e Instalación" |

### Reglas de Visibilidad

1. **Si `permitir_modelo_equipos = True`**: Sección 1.0 se muestra (aunque esté vacía)
2. **Si `permitir_modelo_materiales = True`**: Sección 2.0 se muestra (aunque esté vacía)
3. **Si `permitir_modelo_servicios = True`**: Sección 3.0 se muestra (aunque esté vacía)
4. **Si no hay perfil**: Todas las secciones se muestran por defecto (compatibilidad)

---

## ⚠️ Manejo de Items sin Módulo

### Antes (Fallback Automático)
```python
# Items sin módulo se asignaban automáticamente a Sección 1
if seccion_prefijo is None:
    seccion_1.append(item)  # ❌ Fallback automático
```

### Después (Error de Integridad)
```python
# Items sin módulo se reportan como ERROR DE INTEGRIDAD
if not seccion_modulo:
    items_sin_modulo.append(item)
    logger.warning(
        f"[PDF Service] ⚠️ ERROR DE INTEGRIDAD: Item {item.id} sin seccion_modulo asignado. "
        f"Descripción: '{item.descripcion[:50] if item.descripcion else 'N/A'}'"
    )
    # ❌ NO se incluyen en el PDF
```

**Resultado:**
- ✅ Items sin módulo NO se incluyen en el PDF
- ✅ Se registran en logs como ERROR DE INTEGRIDAD (WARNING)
- ✅ Forza corrección de datos en el editor

---

## 📊 Flujo de Generación Actualizado

```
1. Request → GET /api/v1/cotizaciones/pdf/{id}/?perfil_id=X
   │
2. CotizacionPDFViewSet.retrieve()
   │   ├── Extrae perfil_id (opcional)
   │   └── Obtiene cotización optimizada
   │
3. preparar_contexto_pdf()
   │   ├── Obtiene perfil de configuración (get_configuracion_cotizacion)
   │   └── Llama a obtener_secciones_render()
   │
4. obtener_secciones_render()
   │   ├── Crea diccionario estático ordenado {"1.0": {...}, "2.0": {...}, "3.0": {...}}
   │   ├── Cruza con permisos del perfil (permitir_modelo_*)
   │   ├── Filtra items explícitamente por seccion_modulo
   │   └── Reporta items sin módulo como ERROR DE INTEGRIDAD
   │
5. Template HTML
   │   ├── Itera sobre secciones_render.items() (orden garantizado)
   │   ├── Verifica seccion_data.mostrar (según perfil)
   │   └── Renderiza tabla o mensaje "No hay ítems"
   │
6. PDF generado con secciones ordenadas y visibles según perfil
```

---

## ✅ Validaciones Realizadas

- [x] Sintaxis de Python válida
- [x] Imports correctos
- [x] Función `obtener_secciones_render()` implementada
- [x] Función `preparar_contexto_pdf()` refactorizada
- [x] ViewSet actualizado para aceptar `perfil_id`
- [x] Template actualizado para usar `secciones_render`
- [x] Lógica de fallback eliminada
- [x] Items sin módulo reportados como ERROR DE INTEGRIDAD
- [x] Compatibilidad mantenida con `seccion_1`, `seccion_2`, `seccion_3` (deprecated)

---

## 🔗 Archivos Modificados

1. **`apps/tenant/cotizaciones/pdf_service.py`**
   - ✅ Nueva función: `obtener_secciones_render()`
   - ✅ Refactorizada: `preparar_contexto_pdf()`
   - ❌ Eliminada: `agrupar_items_por_seccion()` (reemplazada)

2. **`apps/tenant/cotizaciones/api/pdf_viewsets.py`**
   - ✅ Actualizado: `retrieve()` para aceptar `perfil_id`

3. **`apps/tenant/cotizaciones/templates/tenant/cotizaciones/pdf/cotizacion_template.html`**
   - ✅ Actualizado: Usa `secciones_render` con iteración ordenada

---

## 🚀 Resultado Esperado

Un PDF donde:
- ✅ Se ven tres tablas claramente diferenciadas y tituladas
- ✅ Orden secuencial: 1.0 → 2.0 → 3.0
- ✅ Secciones visibles según perfil de configuración (aunque estén vacías)
- ✅ Items sin módulo NO aparecen (reportados como ERROR DE INTEGRIDAD)
- ✅ Alineado perfectamente con el Editor de Cotizaciones Estilo Excel

---

**Última Actualización:** 2026-02-XX  
**Versión:** 2.40 (Mapeo Secuencial)  
**Estado:** ✅ COMPLETADO Y VALIDADO
