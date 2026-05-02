/**
 * Mutators para Tabulator v2.60
 * ⚠️ Alineados con CotizacionService.calcular_linea (Costo -> Utilidad -> Venta)
 * ⚠️ Modular: Exportado como objeto global para reutilización
 */
(function(w) {
  'use strict';

  const CotizacionMutators = {
    /**
     * Calcula Precio Venta: Costo * (1 + Utilidad/100)
     * ⚠️ Alineado con fórmula del backend: precio_venta = costo * (1 + utilidad/100)
     * ⚠️ FASE 3: Compatibilidad con aliases - acepta costo_unitario o precio_unitario_venta
     */
    precioVenta: function(value, data, type, params, component) {
      // ⚠️ FASE 3: Aceptar costo_unitario o precio_unitario_venta (alias)
      const costo = parseFloat(data.costo_unitario || data.precio_unitario_venta) || 0;
      // ⚠️ FASE 3: Aceptar porcentaje_utilidad o utilidad_porcentaje (alias)
      const utilidad = parseFloat(data.porcentaje_utilidad || data.utilidad_porcentaje) || 0;
      const precioVenta = costo * (1 + (utilidad / 100));
      return precioVenta.toFixed(2);
    },

    /**
     * Calcula Subtotal: Cantidad * Precio Venta
     * ⚠️ Alineado con fórmula del backend: subtotal = cantidad * precio_venta
     * ⚠️ FASE 3: Usa CotizacionService.calcular_linea como referencia
     */
    subtotalLinea: function(value, data, type, params, component) {
      const cantidad = parseFloat(data.cantidad) || 0;
      const precioVenta = parseFloat(this.precioVenta(null, data)) || 0;
      const subtotal = cantidad * precioVenta;
      return subtotal.toFixed(2);
    }
  };

  // Exportar como objeto global
  w.CotizacionMutators = CotizacionMutators;
})(window);
