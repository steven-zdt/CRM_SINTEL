/**
 * asiento_cargar_desde_docs.js - Módulo para cargar asientos desde documentos v2.60 Fase 3
 * ⚠️ v3.5 Architecture: Nucleus implemented (moved from core to contabilidad)
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ HTMX Integration: Maneja el Offcanvas de selección de documentos
 */
(function(w, d) {
  'use strict';

  const MOD = '[asiento.cargar-docs]';
  const OFFCANVAS_ID = '#offcanvas-asiento-cargar-desde-documentos';
  const API_DOCUMENTOS = '/api/v1/contabilidad/asientos-contables/documentos-sin-asiento/';
  const API_CREAR = '/api/v1/contabilidad/asientos-contables/crear-desde-documentos/';
  
  let documentosSeleccionados = {
    facturas: new Set(),
    gastos: new Set()
  };

  /**
   * Helper: Formatear dinero
   */
  function fmtMoney(v) {
    if (w.DOMUtils && typeof w.DOMUtils.fmtMoney === 'function') {
      return w.DOMUtils.fmtMoney(v);
    }
    const num = parseFloat(v) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  /**
   * Cargar lista de documentos sin asiento
   */
  async function cargarDocumentos() {
    try {
      const response = await fetch(API_DOCUMENTOS);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      
      renderizarFacturas(data.facturas || []);
      renderizarGastos(data.gastos || []);
      actualizarContadores(data.facturas?.length || 0, data.gastos?.length || 0);
    } catch (error) {
      console.error(MOD, 'Error al cargar documentos:', error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(error, MOD);
      }
    }
  }

  /**
   * Renderizar lista de facturas
   */
  function renderizarFacturas(facturas) {
    const tbody = d.querySelector('#tbody-facturas-sin-asiento');
    if (!tbody) return;

    if (facturas.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No hay facturas sin asiento contable.</td></tr>';
      return;
    }

    tbody.innerHTML = facturas.map(factura => {
      const naturalezaBadge = factura.naturaleza === 'VENTA' 
        ? '<span class="badge bg-success">Venta</span>'
        : '<span class="badge bg-info">Compra</span>';
      
      return `
        <tr>
          <td><input type="checkbox" class="form-check-input checkbox-factura" data-id="${factura.id}"></td>
          <td>${factura.numero || 'N/A'}</td>
          <td>${factura.fecha || 'N/A'}</td>
          <td><small><strong>${factura.naturaleza === 'VENTA' ? 'Cliente' : 'Proveedor'}:</strong><br>${factura.naturaleza === 'VENTA' ? (factura.receptor || 'N/A') : (factura.emisor || 'N/A')}</small></td>
          <td>${naturalezaBadge}</td>
          <td><span class="badge bg-success">${factura.estado}</span></td>
          <td class="text-end">${fmtMoney(factura.total)}</td>
          <td class="text-center">
            <button class="btn btn-sm btn-outline-primary btn-crear-uno" data-tipo="factura" data-id="${factura.id}">
              <i class="bi bi-plus-circle"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Event listeners
    tbody.querySelectorAll('.checkbox-factura').forEach(cb => {
      cb.addEventListener('change', function() {
        const id = parseInt(this.dataset.id);
        if (this.checked) documentosSeleccionados.facturas.add(id);
        else documentosSeleccionados.facturas.delete(id);
        actualizarUI();
      });
    });

    tbody.querySelectorAll('.btn-crear-uno[data-tipo="factura"]').forEach(btn => {
      btn.addEventListener('click', () => crearAsientoDesdeDocumento('factura', parseInt(btn.dataset.id)));
    });
  }

  /**
   * Renderizar lista de gastos
   */
  function renderizarGastos(gastos) {
    const tbody = d.querySelector('#tbody-gastos-sin-asiento');
    if (!tbody) return;

    if (gastos.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No hay gastos sin asiento contable.</td></tr>';
      return;
    }

    tbody.innerHTML = gastos.map(gasto => `
      <tr>
        <td><input type="checkbox" class="form-check-input checkbox-gasto" data-id="${gasto.id}"></td>
        <td>${gasto.numero_documento || 'N/A'}</td>
        <td>${gasto.fecha || 'N/A'}</td>
        <td><small><strong>${gasto.vendedor_nombre || 'N/A'}</strong><br><span class="text-muted">NIT: ${gasto.vendedor_nit || 'N/A'}</span></small></td>
        <td><span class="badge bg-secondary">${gasto.categoria_contable || 'N/A'}</span></td>
        <td>${gasto.anulado ? '<span class="badge bg-danger">Anulado</span>' : '<span class="badge bg-success">Activo</span>'}</td>
        <td class="text-end">${fmtMoney(gasto.total)}</td>
        <td class="text-center">
          <button class="btn btn-sm btn-outline-primary btn-crear-uno" data-tipo="gasto" data-id="${gasto.id}">
            <i class="bi bi-plus-circle"></i>
          </button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('.checkbox-gasto').forEach(cb => {
      cb.addEventListener('change', function() {
        const id = parseInt(this.dataset.id);
        if (this.checked) documentosSeleccionados.gastos.add(id);
        else documentosSeleccionados.gastos.delete(id);
        actualizarUI();
      });
    });

    tbody.querySelectorAll('.btn-crear-uno[data-tipo="gasto"]').forEach(btn => {
      btn.addEventListener('click', () => crearAsientoDesdeDocumento('gasto', parseInt(btn.dataset.id)));
    });
  }

  function actualizarContadores(countFacturas, countGastos) {
    const bf = d.querySelector('#badge-count-facturas');
    const bg = d.querySelector('#badge-count-gastos');
    if (bf) bf.textContent = countFacturas;
    if (bg) bg.textContent = countGastos;
  }

  function actualizarUI() {
    const total = documentosSeleccionados.facturas.size + documentosSeleccionados.gastos.size;
    const contador = d.querySelector('#selected-count');
    if (contador) contador.textContent = total;
    
    const btn = d.querySelector('#btn-crear-asientos-seleccionados');
    if (btn) btn.disabled = total === 0;
  }

  function crearAsientoDesdeDocumento(tipo, id) {
    const payload = tipo === 'factura' 
      ? { facturas: [id], gastos: [] }
      : { facturas: [], gastos: [id] };
    crearAsientos(payload);
  }

  async function crearAsientos(payload) {
    const btn = d.querySelector('#btn-crear-asientos-seleccionados');
    if (btn) btn.disabled = true;

    const csrftoken = d.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      d.cookie.match(/csrftoken=([^;]+)/)?.[1];

    try {
      const response = await fetch(API_CREAR, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      
      if (response.ok) {
        if (data.exitosos?.length > 0) {
          if (w.SintelFeedback) w.SintelFeedback.success(`${data.exitosos.length} asiento(s) creado(s) correctamente.`);
        }
        if (data.errores?.length > 0) {
          if (w.SintelFeedback) w.SintelFeedback.error(`${data.errores.length} error(es) al crear asiento(s).`);
        }
        
        cargarDocumentos();
        if (w.AsientoList && typeof w.AsientoList.reload === 'function') w.AsientoList.reload();
        
        documentosSeleccionados.facturas.clear();
        documentosSeleccionados.gastos.clear();
        actualizarUI();
        d.querySelectorAll('.checkbox-factura, .checkbox-gasto').forEach(cb => cb.checked = false);
      } else {
        if (w.UIManager) w.UIManager.handleError({ ok: false, status: response.status, data }, MOD);
      }
    } catch (error) {
      console.error(MOD, 'Error al crear asientos:', error);
      if (w.UIManager) w.UIManager.handleError(error, MOD);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function init() {
    // Escuchar evento de HTMX para inicializar cuando se carga el Offcanvas
    d.body.addEventListener('htmx:afterSettle', function(evt) {
      if (evt.detail.target.id === 'offcanvas-container-asiento') {
        const offcanvas = d.querySelector(OFFCANVAS_ID);
        if (offcanvas) {
          cargarDocumentos();
          
          d.querySelector('#btn-crear-asientos-seleccionados')?.addEventListener('click', () => {
            crearAsientos({
              facturas: Array.from(documentosSeleccionados.facturas),
              gastos: Array.from(documentosSeleccionados.gastos)
            });
          });

          d.querySelector('#select-all-facturas')?.addEventListener('change', function() {
            d.querySelectorAll('.checkbox-factura').forEach(cb => {
              cb.checked = this.checked;
              const id = parseInt(cb.dataset.id);
              if (this.checked) documentosSeleccionados.facturas.add(id);
              else documentosSeleccionados.facturas.delete(id);
            });
            actualizarUI();
          });

          // (Otros listeners de búsqueda omitidos por brevedad, se pueden agregar luego si es crítico)
        }
      }
    });
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', init);
  else init();

})(window, document);
