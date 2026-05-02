/**
 * asientos_cargar_desde_docs.js - Módulo para cargar asientos desde documentos v2.60 Fase 3
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ HTMX Integration: Maneja el Offcanvas de selección de documentos
 * 
 * Responsabilidades:
 * - Cargar lista de facturas y gastos sin asiento
 * - Permitir selección múltiple
 * - Crear asientos desde documentos seleccionados
 * - Integración con error_injector.js
 */
(function(w, d) {
  'use strict';

  const MOD = '[asientos.cargar-docs]';
  const OFFCANVAS_ID = '#offcanvas-cargar-desde-documentos';
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
  function cargarDocumentos() {
    fetch(API_DOCUMENTOS)
      .then(response => response.json())
      .then(data => {
        renderizarFacturas(data.facturas || []);
        renderizarGastos(data.gastos || []);
        actualizarContadores(data.facturas?.length || 0, data.gastos?.length || 0);
      })
      .catch(error => {
        console.error(`${MOD} Error al cargar documentos:`, error);
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(error);
        }
      });
  }

  /**
   * Renderizar lista de facturas
   */
  function renderizarFacturas(facturas) {
    const tbody = d.querySelector('#tbody-facturas-sin-asiento');
    if (!tbody) return;

    if (facturas.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center text-muted">
            No hay facturas sin asiento contable.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = facturas.map(factura => {
      const naturalezaBadge = factura.naturaleza === 'VENTA' 
        ? '<span class="badge bg-success">Venta</span>'
        : '<span class="badge bg-info">Compra</span>';
      
      return `
        <tr>
          <td>
            <input type="checkbox" class="form-check-input checkbox-factura" 
                   data-id="${factura.id}" data-tipo="factura">
          </td>
          <td>${factura.numero || 'N/A'}</td>
          <td>${factura.fecha || 'N/A'}</td>
          <td>
            <small>
              <strong>${factura.naturaleza === 'VENTA' ? 'Cliente' : 'Proveedor'}:</strong><br>
              ${factura.naturaleza === 'VENTA' ? factura.receptor : factura.emisor}
            </small>
          </td>
          <td>${naturalezaBadge}</td>
          <td><span class="badge bg-success">${factura.estado}</span></td>
          <td class="text-end">${fmtMoney(factura.total)}</td>
          <td class="text-center">
            <button class="btn btn-sm btn-outline-primary btn-crear-uno" 
                    data-tipo="factura" data-id="${factura.id}" title="Crear asiento para esta factura">
              <i class="bi bi-plus-circle"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Event listeners para checkboxes
    tbody.querySelectorAll('.checkbox-factura').forEach(cb => {
      cb.addEventListener('change', function() {
        const id = parseInt(this.dataset.id);
        if (this.checked) {
          documentosSeleccionados.facturas.add(id);
        } else {
          documentosSeleccionados.facturas.delete(id);
        }
        actualizarEstadoBoton();
        actualizarContadorSeleccionados();
      });
    });

    // Event listeners para botones de crear uno
    tbody.querySelectorAll('.btn-crear-uno[data-tipo="factura"]').forEach(btn => {
      btn.addEventListener('click', function() {
        const id = parseInt(this.dataset.id);
        crearAsientoDesdeDocumento('factura', id);
      });
    });
  }

  /**
   * Renderizar lista de gastos
   */
  function renderizarGastos(gastos) {
    const tbody = d.querySelector('#tbody-gastos-sin-asiento');
    if (!tbody) return;

    if (gastos.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center text-muted">
            No hay gastos sin asiento contable.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = gastos.map(gasto => {
      return `
        <tr>
          <td>
            <input type="checkbox" class="form-check-input checkbox-gasto" 
                   data-id="${gasto.id}" data-tipo="gasto">
          </td>
          <td>${gasto.numero_documento || 'N/A'}</td>
          <td>${gasto.fecha || 'N/A'}</td>
          <td>
            <small>
              <strong>${gasto.vendedor_nombre || 'N/A'}</strong><br>
              <span class="text-muted">NIT: ${gasto.vendedor_nit || 'N/A'}</span>
            </small>
          </td>
          <td><span class="badge bg-secondary">${gasto.categoria_contable || 'N/A'}</span></td>
          <td>
            ${gasto.anulado 
              ? '<span class="badge bg-danger">Anulado</span>'
              : '<span class="badge bg-success">Activo</span>'
            }
          </td>
          <td class="text-end">${fmtMoney(gasto.total)}</td>
          <td class="text-center">
            <button class="btn btn-sm btn-outline-primary btn-crear-uno" 
                    data-tipo="gasto" data-id="${gasto.id}" title="Crear asiento para este gasto">
              <i class="bi bi-plus-circle"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Event listeners para checkboxes
    tbody.querySelectorAll('.checkbox-gasto').forEach(cb => {
      cb.addEventListener('change', function() {
        const id = parseInt(this.dataset.id);
        if (this.checked) {
          documentosSeleccionados.gastos.add(id);
        } else {
          documentosSeleccionados.gastos.delete(id);
        }
        actualizarEstadoBoton();
        actualizarContadorSeleccionados();
      });
    });

    // Event listeners para botones de crear uno
    tbody.querySelectorAll('.btn-crear-uno[data-tipo="gasto"]').forEach(btn => {
      btn.addEventListener('click', function() {
        const id = parseInt(this.dataset.id);
        crearAsientoDesdeDocumento('gasto', id);
      });
    });
  }

  /**
   * Actualizar contadores de documentos
   */
  function actualizarContadores(countFacturas, countGastos) {
    const badgeFacturas = d.querySelector('#badge-count-facturas');
    const badgeGastos = d.querySelector('#badge-count-gastos');
    
    if (badgeFacturas) badgeFacturas.textContent = countFacturas;
    if (badgeGastos) badgeGastos.textContent = countGastos;
  }

  /**
   * Actualizar contador de seleccionados
   */
  function actualizarContadorSeleccionados() {
    const total = documentosSeleccionados.facturas.size + documentosSeleccionados.gastos.size;
    const contador = d.querySelector('#selected-count');
    if (contador) {
      contador.textContent = total;
    }
  }

  /**
   * Actualizar estado del botón de crear
   */
  function actualizarEstadoBoton() {
    const btn = d.querySelector('#btn-crear-asientos-seleccionados');
    if (!btn) return;
    
    const total = documentosSeleccionados.facturas.size + documentosSeleccionados.gastos.size;
    btn.disabled = total === 0;
  }

  /**
   * Crear asiento desde un documento individual
   */
  function crearAsientoDesdeDocumento(tipo, id) {
    const payload = tipo === 'factura' 
      ? { facturas: [id], gastos: [] }
      : { facturas: [], gastos: [id] };
    
    crearAsientosDesdeDocumentos(payload);
  }

  /**
   * Crear asientos desde documentos seleccionados
   */
  function crearAsientosDesdeDocumentos(payload) {
    const btn = d.querySelector('#btn-crear-asientos-seleccionados');
    if (btn) btn.disabled = true;

    const csrftoken = d.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      d.cookie.match(/csrftoken=([^;]+)/)?.[1];

    fetch(API_CREAR, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    })
    .then(response => {
      return response.json().then(data => ({ response, data }));
    })
    .then(({ response, data }) => {
      if (response.ok) {
        // Mostrar resultado
        const exitosos = data.exitosos || [];
        const errores = data.errores || [];
        
        if (exitosos.length > 0) {
          const mensaje = `${exitosos.length} asiento(s) creado(s) correctamente.`;
          if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success(mensaje);
          }
        }
        
        if (errores.length > 0) {
          const mensaje = `${errores.length} error(es) al crear asiento(s).`;
          if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
            w.SintelFeedback.error(mensaje);
          }
        }
        
        // Recargar lista y refrescar tabla principal
        cargarDocumentos();
        if (w.AppAsientos && typeof w.AppAsientos.refreshGrid === 'function') {
          w.AppAsientos.refreshGrid();
        }
        
        // Limpiar selección
        documentosSeleccionados.facturas.clear();
        documentosSeleccionados.gastos.clear();
        actualizarEstadoBoton();
        actualizarContadorSeleccionados();
        
        // Desmarcar checkboxes
        d.querySelectorAll('.checkbox-factura, .checkbox-gasto').forEach(cb => {
          cb.checked = false;
        });
      } else {
        // Mostrar error
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          w.ErrorHandler.show(data);
        } else {
          console.error(`${MOD} Error al crear asientos:`, data);
        }
      }
    })
    .catch(error => {
      console.error(`${MOD} Error al crear asientos:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(error);
      }
    })
    .finally(() => {
      if (btn) btn.disabled = false;
    });
  }

  /**
   * Inicializar eventos del Offcanvas
   */
  function initOffcanvasEvents() {
    const offcanvas = d.querySelector(OFFCANVAS_ID);
    if (!offcanvas) return;

    // Botón de crear asientos seleccionados
    const btnCrear = d.querySelector('#btn-crear-asientos-seleccionados');
    if (btnCrear) {
      btnCrear.addEventListener('click', function() {
        const payload = {
          facturas: Array.from(documentosSeleccionados.facturas),
          gastos: Array.from(documentosSeleccionados.gastos)
        };
        crearAsientosDesdeDocumentos(payload);
      });
    }

    // Select all para facturas
    const selectAllFacturas = d.querySelector('#select-all-facturas');
    if (selectAllFacturas) {
      selectAllFacturas.addEventListener('change', function() {
        const checkboxes = d.querySelectorAll('.checkbox-factura');
        checkboxes.forEach(cb => {
          cb.checked = this.checked;
          const id = parseInt(cb.dataset.id);
          if (this.checked) {
            documentosSeleccionados.facturas.add(id);
          } else {
            documentosSeleccionados.facturas.delete(id);
          }
        });
        actualizarEstadoBoton();
        actualizarContadorSeleccionados();
      });
    }

    // Select all para gastos
    const selectAllGastos = d.querySelector('#select-all-gastos');
    if (selectAllGastos) {
      selectAllGastos.addEventListener('change', function() {
        const checkboxes = d.querySelectorAll('.checkbox-gasto');
        checkboxes.forEach(cb => {
          cb.checked = this.checked;
          const id = parseInt(cb.dataset.id);
          if (this.checked) {
            documentosSeleccionados.gastos.add(id);
          } else {
            documentosSeleccionados.gastos.delete(id);
          }
        });
        actualizarEstadoBoton();
        actualizarContadorSeleccionados();
      });
    }

    // Búsqueda en facturas
    const searchFacturas = d.querySelector('#search-facturas-sin-asiento');
    if (searchFacturas) {
      searchFacturas.addEventListener('input', function() {
        const term = this.value.toLowerCase();
        const rows = d.querySelectorAll('#tbody-facturas-sin-asiento tr');
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(term) ? '' : 'none';
        });
      });
    }

    // Búsqueda en gastos
    const searchGastos = d.querySelector('#search-gastos-sin-asiento');
    if (searchGastos) {
      searchGastos.addEventListener('input', function() {
        const term = this.value.toLowerCase();
        const rows = d.querySelectorAll('#tbody-gastos-sin-asiento tr');
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(term) ? '' : 'none';
        });
      });
    }

    // Cargar documentos cuando se muestra el Offcanvas
    const bsOffcanvas = new bootstrap.Offcanvas(offcanvas);
    offcanvas.addEventListener('shown.bs.offcanvas', function() {
      cargarDocumentos();
    });
  }

  /**
   * Inicializar módulo
   */
  function init() {
    // Escuchar evento de HTMX para inicializar cuando se carga el Offcanvas
    d.body.addEventListener('htmx:afterSettle', function(evt) {
      if (evt.detail.target.id === 'offcanvas-container-asientos') {
        const offcanvas = d.querySelector(OFFCANVAS_ID);
        if (offcanvas) {
          initOffcanvasEvents();
          // Mostrar Offcanvas
          const bsOffcanvas = new bootstrap.Offcanvas(offcanvas);
          bsOffcanvas.show();
        }
      }
    });
  }

  // Auto-inicializar
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exponer funciones públicas
  if (!w.AppAsientos) {
    w.AppAsientos = {};
  }
  w.AppAsientos.cargarDocumentos = cargarDocumentos;

  console.log(`${MOD} Módulo cargado`);

})(window, document);
