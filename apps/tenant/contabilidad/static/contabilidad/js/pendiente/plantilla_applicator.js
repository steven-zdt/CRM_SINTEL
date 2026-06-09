/**
 * plantilla_applicator.js - Aplicador de Plantillas al Offcanvas Contabilizar v3.16.2
 * Módulo standalone para futuro refactoring del inline script.
 * Dependencias globales: w.http, w.jwtAuth
 */
(function (w, d) {
  'use strict';

  const MOD = '[plantilla.applicator]';
  const API_PLANTILLAS = '/api/v1/contabilidad/plantillas-contables/';

  // Mapeo app_label → tipo_transaccion
  const APP_TIPO_MAP = {
    facturas: 'VENTA',
    gastos: 'COMPRA',
    empleados: 'NOMINA',
    inventario: 'GASTO',
  };

  /**
   * Carga plantillas activas para un tipo de transaccion
   * @param {string} appLabel - app_label del documento
   * @returns {Promise<Array>} Lista de plantillas disponibles
   */
  async function loadPlantillas(appLabel) {
    const tipoTx = APP_TIPO_MAP[appLabel] || '';
    if (!tipoTx) return [];

    const jwt = w.jwtAuth?.getAccessToken?.() || '';
    try {
      const url = new URL(API_PLANTILLAS, w.location.origin);
      url.searchParams.append('tipo_transaccion', tipoTx);
      url.searchParams.append('activo', 'true');
      url.searchParams.append('page_size', '100');

      const res = await w.http('GET', url.pathname + url.search);
      if (!res.ok) throw new Error('Error ' + res.status);
      return res.data.results || [];
    } catch (e) {
      console.error(MOD, 'loadPlantillas error:', e);
      return [];
    }
  }

  /**
   * Calcula el monto según origen_valor y datos del documento
   * @param {string} origenValor - Tipo de origen (SALDO_BASE, IVA_GENERADO, etc.)
   * @param {number} subtotal - Subtotal del documento
   * @param {number} impuestos - Total impuestos/retenciones
   * @param {number} total - Total del documento
   * @param {number} porcentaje - Porcentaje a aplicar (0-100)
   * @returns {number} Monto calculado
   */
  function calcularMonto(origenValor, subtotal, impuestos, total, porcentaje) {
    let base = 0;
    switch (origenValor) {
      case 'SALDO_BASE': base = subtotal; break;
      case 'TOTAL_DOCUMENTO': base = total; break;
      case 'IVA_GENERADO':
      case 'IVA_DESCONTABLE':
      case 'RETEFUENTE':
      case 'RETEICA':
      case 'RETEIVA':
        base = impuestos;
        break;
      default: base = 0;
    }
    const monto = base * (porcentaje / 100);
    return Math.round(monto * 100) / 100;
  }

  /**
   * Aplica plantilla a la tabla de asiento
   * @param {Object} config - {lineas, subtotal, impuestos, total, addLineCallback, recalcCallback}
   */
  function aplicarPlantilla(config) {
    const { lineas, subtotal, impuestos, total, addLineCallback, recalcCallback } = config;
    if (!Array.isArray(lineas) || !lineas.length) return false;

    // Iterar lineas y agregar a tabla
    lineas.forEach(linea => {
      const monto = calcularMonto(
        linea.origen_valor,
        parseFloat(subtotal) || 0,
        parseFloat(impuestos) || 0,
        parseFloat(total) || 0,
        linea.porcentaje_aplicar || 100
      );

      const initialData = {
        codigo: linea.cuenta_codigo || '',
        nombre: linea.cuenta_nombre || '',
        debe: linea.naturaleza === 'DEBE' ? monto : 0,
        haber: linea.naturaleza === 'HABER' ? monto : 0,
        descripcion: linea.descripcion || `${linea.origen_valor}`,
      };

      if (addLineCallback) addLineCallback(initialData);
    });

    if (recalcCallback) recalcCallback();
    return true;
  }

  // Exportar API pública
  if (typeof w !== 'undefined') {
    w.PlantillaApplicator = Object.freeze({
      loadPlantillas,
      calcularMonto,
      aplicarPlantilla,
      APP_TIPO_MAP,
    });
  }
})(window, document);
