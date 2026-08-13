/**
 * plantilla_applicator.js - Aplicador de Plantillas al Offcanvas Contabilizar v3.17.1
 *
 * Cambios v3.17.1:
 *   - getPlantillaLineas(uuid): lazy-fetch del detalle (lineas no estan en el list endpoint)
 *   - calcularMonto acepta objeto montos con cantidades individuales por tipo de impuesto
 *   - previsualizarLineas(): genera HTML de preview de lineas con montos calculados
 *   - aplicarPlantilla() usa montos granulares (iva_generado, retefuente, reteica, reteiva)
 *
 * Namespace: window.PlantillaApplicator (compatibilidad) + window.Sintel.Contabilidad.PlantillaApplicator
 */
(function (w, d) {
  'use strict';

  const MOD = '[plantilla.applicator]';
  const API_PLANTILLAS = '/api/v1/contabilidad/plantillas-contables/';

  // Mapeo app_label → tipo_transaccion para filtrar plantillas disponibles
  const APP_TIPO_MAP = {
    facturas:  'VENTA',
    gastos:    'COMPRA',
    empleados: 'NOMINA',
    inventario: 'GASTO',
  };

  // Labels amigables para origen_valor
  const ORIGEN_LABELS = {
    SALDO_BASE:      'Subtotal / Base',
    TOTAL_DOCUMENTO: 'Total Documento',
    IVA_GENERADO:    'IVA Generado',
    IVA_DESCONTABLE: 'IVA Descontable',
    RETEFUENTE:      'Retencion en la Fuente',
    RETEICA:         'Reteica',
    RETEIVA:         'Reteiva',
  };

  function _jwt() { return w.jwtAuth?.getAccessToken?.() || ''; }
  function _headers(extra) {
    const h = { 'Accept': 'application/json', ...(extra || {}) };
    const t = _jwt();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }

  // ─────────────────────────────────── fetch plantillas activas (solo lista)
  async function loadPlantillas(appLabel) {
    const tipoTx = APP_TIPO_MAP[appLabel] || '';
    if (!tipoTx) return [];
    try {
      const url = API_PLANTILLAS + '?tipo_transaccion=' + tipoTx + '&activo=true&page_size=100';
      const res = await w.Sintel.Core.Http.request('GET', url);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.data.results || [];
    } catch (e) {
      console.error(MOD, 'loadPlantillas error:', e);
      return [];
    }
  }

  // ─────────────────────── lazy-fetch del detalle (con lineas completas)
  let _detailCache = {};

  async function getPlantillaLineas(uuid) {
    if (_detailCache[uuid]) return _detailCache[uuid];
    try {
      const res = await w.Sintel.Core.Http.request('GET', API_PLANTILLAS + uuid + '/');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const lineas = res.data.lineas || [];
      _detailCache[uuid] = lineas;
      return lineas;
    } catch (e) {
      console.error(MOD, 'getPlantillaLineas error:', e);
      return [];
    }
  }

  // ─────────────────────────────── calcular monto segun origen_valor
  // montos: { subtotal, total, impuestos, iva_generado, iva_descontable,
  //           retefuente, reteica, reteiva }
  function calcularMonto(origenValor, montos, porcentaje) {
    // Soporta signatura legacy (origenValor, subtotal, impuestos, total, porcentaje)
    if (typeof montos === 'number') {
      const subtotalLeg = montos;
      const impuestosLeg = porcentaje;
      const totalLeg = arguments[3];
      const porcLeg = arguments[4];
      montos = { subtotal: subtotalLeg, impuestos: impuestosLeg, total: totalLeg };
      porcentaje = porcLeg;
    }
    const m = montos || {};
    let base = 0;
    switch (origenValor) {
      case 'SALDO_BASE':      base = parseFloat(m.subtotal  || 0); break;
      case 'TOTAL_DOCUMENTO': base = parseFloat(m.total     || 0); break;
      case 'IVA_GENERADO':    base = parseFloat(m.iva_generado    || m.impuestos || 0); break;
      case 'IVA_DESCONTABLE': base = parseFloat(m.iva_descontable || m.impuestos || 0); break;
      case 'RETEFUENTE':      base = parseFloat(m.retefuente || m.impuestos || 0); break;
      case 'RETEICA':         base = parseFloat(m.reteica   || m.impuestos || 0); break;
      case 'RETEIVA':         base = parseFloat(m.reteiva   || m.impuestos || 0); break;
      default:                base = 0;
    }
    const monto = base * ((parseFloat(porcentaje) || 100) / 100);
    return Math.round(monto * 100) / 100;
  }

  // ──────────────────────────────── preview HTML de lineas con montos
  function previsualizarLineas(lineas, montos) {
    if (!lineas || !lineas.length) {
      return '<p class="text-muted small mb-0">Esta plantilla no tiene lineas configuradas.</p>';
    }
    const filas = lineas.map(function (l) {
      const monto = calcularMonto(l.origen_valor, montos, l.porcentaje_aplicar || 100);
      const montoFmt = monto.toLocaleString('es-CO', { minimumFractionDigits: 2 });
      const badgeCls = l.naturaleza === 'DEBE' ? 'bg-danger' : 'bg-success';
      return [
        '<tr>',
        '  <td class="py-1"><span class="badge ' + badgeCls + ' me-1">' + (l.naturaleza || '?') + '</span></td>',
        '  <td class="py-1 font-monospace small">' + (l.cuenta_codigo || '-') + '</td>',
        '  <td class="py-1 small text-truncate" style="max-width:160px">' + (l.cuenta_nombre || '') + '</td>',
        '  <td class="py-1 small text-muted">' + (ORIGEN_LABELS[l.origen_valor] || l.origen_valor) + '</td>',
        '  <td class="py-1 text-end small fw-semibold">$ ' + montoFmt + '</td>',
        '</tr>',
      ].join('');
    }).join('');
    return [
      '<table class="table table-xs table-bordered mb-0" style="font-size:.78rem">',
      '<thead class="table-light"><tr>',
      '<th class="py-1">Tipo</th><th class="py-1">Cuenta</th>',
      '<th class="py-1">Nombre</th><th class="py-1">Origen</th>',
      '<th class="py-1 text-end">Monto</th>',
      '</tr></thead>',
      '<tbody>' + filas + '</tbody>',
      '</table>',
    ].join('');
  }

  // ─────────────────────────── aplicar plantilla a la tabla de asiento
  // config: { lineas, montos, addLineCallback, recalcCallback }
  function aplicarPlantilla(config) {
    const { lineas, montos, addLineCallback, recalcCallback } = config;
    if (!Array.isArray(lineas) || !lineas.length) return false;

    lineas.forEach(function (linea) {
      const monto = calcularMonto(
        linea.origen_valor,
        montos,
        linea.porcentaje_aplicar || 100
      );
      if (addLineCallback) {
        addLineCallback({
          codigo:      linea.cuenta_codigo || '',
          nombre:      linea.cuenta_nombre || '',
          debe:        linea.naturaleza === 'DEBE'  ? monto : 0,
          haber:       linea.naturaleza === 'HABER' ? monto : 0,
          descripcion: linea.descripcion || (ORIGEN_LABELS[linea.origen_valor] || linea.origen_valor),
        });
      }
    });

    if (recalcCallback) recalcCallback();
    return true;
  }

  // ───────────────────────────────────────────── API publica
  w.Sintel = w.Sintel || {};
  w.Sintel.Contabilidad = w.Sintel.Contabilidad || {};

  const pub = Object.freeze({
    loadPlantillas:      loadPlantillas,
    getPlantillaLineas:  getPlantillaLineas,
    calcularMonto:       calcularMonto,
    previsualizarLineas: previsualizarLineas,
    aplicarPlantilla:    aplicarPlantilla,
    APP_TIPO_MAP:        APP_TIPO_MAP,
    ORIGEN_LABELS:       ORIGEN_LABELS,
  });

  w.PlantillaApplicator = pub;
  w.Sintel.Contabilidad.PlantillaApplicator = pub;

  console.log(MOD, 'Modulo cargado v3.17.1');
})(window, document);
