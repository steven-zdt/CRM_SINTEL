# 🧠 Lógica de Negocio: Módulo Inventario (SSoT)

Este documento centraliza las reglas de integridad, invariantes de stock y políticas de inmutabilidad del Kardex.

---

## 1. Invariantes del Motor Kardex

- **Desnormalización Segura**: El campo `Producto.stock_actual` es un sumario desnormalizado de todos los `MovimientoInventario`. Nunca debe actualizarse sin un movimiento de respaldo.
- **Atomicidad de Recálculo**: El método `recalcular_stock_producto` utiliza `select_for_update()` para bloquear la fila del producto en la base de datos, garantizando que movimientos concurrentes no generen inconsistencias en el saldo final.
- **Prohibición de Stock Negativo**: Todo movimiento de salida (`SALIDA_VENTA`, `SALIDA_BAJA`, etc.) debe validar que el `stock_actual` sea suficiente. El sistema bloquea transacciones que resulten en saldos negativos.

---

## 2. Inmutabilidad del Registro Histórico

- **Kardex Append-Only**: Los modelos `MovimientoInventario` e `HistorialServicio` son de solo lectura tras su creación. No se permite la edición o eliminación de registros históricos.
- **Correcciones de Errores**: Si un movimiento fue registrado con datos erróneos, se debe realizar un movimiento de compensación (ej. una Entrada para anular una Salida errónea) con las observaciones pertinentes.

---

## 3. Jerarquía y Tipología de Ítems

- **Productos (Tangibles)**: Control estricto de stock y costo promedio.
- **Servicios (Intangibles)**: Sin control de existencias físicas. Su historial se registra en un modelo independiente para métricas de venta.
- **Activos Fijos (Uso Interno)**: No destinados a la venta regular. Tienen estados operativos (`Mantenimiento`, `Baja`, `Vendido`) y control de ubicación/responsable.

---

## 4. Gestión de Categorías

- **Aislamiento por Aplicación**: Las categorías pueden restringirse a un tipo de ítem (Productos, Servicios o Activos) o ser generales (`TODO`).
- **Eliminación Segura (SET_NULL)**: Al eliminar una categoría, los ítems asociados **no** se eliminan; su referencia de categoría se establece en `null` (SET_NULL) para preservar el catálogo operativo.

---

## 5. Ingesta e Idempotencia

- **Clave de Idempotencia**: El `codigo` (SKU/Placa) es el identificador único por tenant.
- **Silent Success**: En cargas masivas, si un código ya existe, el sistema actualiza los datos descriptivos (`nombre`, `precio`) en lugar de generar un error, garantizando que el proceso sea re-ejecutable sin duplicados.
- **Stock Inicial**: Solo se registra un movimiento de ajuste de entrada en la **primera** creación del producto para evitar inflar el stock en actualizaciones posteriores.
