# 🧠 Lógica de Negocio: Módulo Cotizaciones

Este documento es la Single Source of Truth (SSoT) para las reglas de dominio y cálculos financieros del módulo de cotizaciones.

---

## 🧬 DNA Inheritance (Herencia Dinámica)

Las cotizaciones no son entidades aisladas; heredan su comportamiento y parámetros financieros de una **Plantilla de Configuración** (`ConfiguracionCotizacion`).

### Reglas de Herencia
Al momento de la creación (`CotizacionService.crear_preforma`):
- **IVA**: Se copia `iva_porcentaje_default` al campo `iva_porcentaje` de la cotización.
- **AIU**: Se copian los porcentajes de Administración, Imprevistos y Utilidad.
- **Tipo**: Se hereda el `tipo_cotizacion_default`.
- **Firma e Imagen**: Se vinculan los assets definidos en el perfil.

> [!IMPORTANT]
> Una vez creada la cotización, los cambios en la plantilla **NO** afectan a las cotizaciones existentes. Esto garantiza la integridad histórica de las ofertas comerciales.

---

## 📸 Snapshot Pattern (Resiliencia de Datos)

Para evitar que cambios en el catálogo de productos o servicios alteren cotizaciones pasadas, se implementa el patrón Snapshot en `CotizacionItem`.

- **Descripción**: Se guarda el nombre/descripción actual del producto.
- **Costos**: El `costo_unitario` y `precio_unitario_venta` se persisten en la fila del item.
- **Referencia**: Se mantiene el ID del producto original solo como referencia (SET_NULL), pero el item sigue siendo válido aunque el producto se elimine.

---

## 🔢 Numeración Atómica y Folios

La generación de códigos únicos (ej. `STS. 0422-2026`) es una operación crítica que previene duplicados en entornos concurrentes.

### Proceso de Generación
1. **Bloqueo de Perfil**: `ConfiguracionCotizacion.objects.select_for_update().get(id=perfil_id)`.
2. **Cálculo de Siguiente**: Se usa `F('ultimo_numero') + 1` para asegurar atomicidad a nivel de DB.
3. **Formateo**:
   - `prefijo`: Definido en el perfil.
   - `número`: Relleno con ceros (ej. 0001).
   - `sufijo`: Definido en el perfil (ej. año actual).

---

## ⚖️ Fórmulas Financieras (SSoT)

### 1. Cálculo por Item (Línea)
- `Precio Venta = Costo Unitario * (1 + (Porcentaje Utilidad / 100))`
- `Subtotal Línea = Cantidad * Precio Venta`

### 2. Totales de Cotización
- `Subtotal General = Σ(Subtotal Línea)`
- `Base AIU (si aplica) = Subtotal General`
- `Valor AIU = Base AIU * (Porcentaje AIU Total / 100)`
- `Base IVA`:
    - Si usa AIU: `Base IVA = Valor Utilidad AIU` (según ley local usualmente) o `AIU Total`. *Nota: En SINTEL, se aplica sobre el total si no se especifica discriminación.*
    - Si NO usa AIU: `Base IVA = Subtotal General`
- `IVA = Base IVA * (Porcentaje IVA / 100)`
- **Total Final = Subtotal General + Valor AIU + Valor IVA**

---

## 🛡️ Seguridad Defensiva (DSV)

Toda mutación en `CotizacionService` aplica **Double Semantic Verification**:
1. **Pertenencia**: Se valida que el `cliente_id` y `configuracion_id` pertenezcan al `empresa_id` del tenant autenticado.
2. **Integridad**: No se permiten items con cantidades negativas o costos nulos.

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/AUDITORIA_FLUJO_COMPLETO.md)
- [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/docs/cotizaciones_microtasks_architecture.md)
- [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/docs/cotizaciones_flow_map.md)
