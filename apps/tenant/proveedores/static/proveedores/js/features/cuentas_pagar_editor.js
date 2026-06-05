/**
 * cuentas_pagar_editor.js - Submodulo Cuentas por Pagar Editor v3.16.1
 * Feature-Sliced Design: Responsable del Ciclo de Vida del Formulario y Abonos de Cuentas por Pagar.
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:cuentas-pagar:editor]';
  const API_URL = '/api/v1/proveedores/cuentas-pagar/';
  const CONTAINER_ID = '#offcanvas-container-cuentas-pagar';
  let listEventsBound = false;

  /**
   * Abre offcanvas de gestion de Cuentas por Pagar para registrar abono
   */
  async function openOffcanvas(uuid) {
    let container = d.querySelector(CONTAINER_ID);
    if (!container) {
      container = d.createElement('div');
      container.id = CONTAINER_ID.substring(1);
      d.body.appendChild(container);
    }

    const url = `${API_URL}render-offcanvas/?uuid=${uuid}`;
    console.log(`${MOD} Cargando panel de abono Cuentas por Pagar desde: ${url}`);
    return htmx.ajax('GET', url, { target: CONTAINER_ID, swap: 'innerHTML' });
  }

  /**
   * Guarda un abono por API
   */
  async function registrarAbono(uuid, monto, observaciones) {
    if (!uuid) return;
    
    const url = `${API_URL}${uuid}/registrar-abono/`;
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': w.Sintel?.CSRFToken || d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        },
        body: JSON.stringify({
          monto: parseFloat(monto) || 0,
          observaciones: observaciones || ''
        })
      });

      const data = await response.json();
      if (response.ok) {
        if (w.UIManager?.notifySuccess) {
          w.UIManager.notifySuccess("Abono registrado correctamente.");
        } else {
          alert("Abono registrado correctamente.");
        }

        // Refrescar tabla de Cuentas por Pagar
        if (w.Sintel.Proveedores.CuentasPagarList?.refresh) {
          w.Sintel.Proveedores.CuentasPagarList.refresh();
        }

        // Cerrar offcanvas
        const offcanvasEl = d.querySelector(`${CONTAINER_ID} .offcanvas`);
        if (offcanvasEl) {
          if (w.UIManager?.handleOffcanvas) {
            w.UIManager.handleOffcanvas(offcanvasEl, 'hide');
          } else {
            bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
          }
        }
      } else {
        if (w.UIManager?.notifyError) {
          w.UIManager.notifyError(data.error || "Error al registrar abono.");
        } else {
          alert(data.error || "Error al registrar abono.");
        }
      }
    } catch (err) {
      console.error(`${MOD} Error de red:`, err);
      if (w.UIManager?.notifyError) {
        w.UIManager.notifyError("Error de conexion de red.");
      }
    }
  }

  /**
   * Eventos globales
   */
  function initListEvents() {
    if (listEventsBound) return;

    d.addEventListener('click', function (e) {
      // Evento click para abrir Offcanvas
      const btnAbono = e.target.closest('.btn-abono-cuentas-pagar');
      if (btnAbono) {
        e.stopPropagation();
        const uuid = btnAbono.getAttribute('data-uuid');
        if (uuid) openOffcanvas(uuid);
      }

      // Evento click para guardar Abono
      const btnGuardarAbono = e.target.closest('#btn-guardar-abono-cuentas-pagar');
      if (btnGuardarAbono) {
        e.preventDefault();
        const form = d.querySelector('#form-abono-cuentas-pagar');
        if (!form) return;
        
        const uuid = form.dataset.cxpUuid;
        const inputMonto = form.querySelector('#monto_abono_cuentas_pagar');
        const inputObservaciones = form.querySelector('#observaciones_abono_cuentas_pagar');
        
        if (inputMonto && uuid) {
          if (!form.reportValidity()) return;
          registrarAbono(uuid, inputMonto.value, inputObservaciones ? inputObservaciones.value : '');
        }
      }
    });

    listEventsBound = true;
  }

  // Exportar al Namespace
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.CuentasPagarEditor = {
    openOffcanvas: openOffcanvas,
    registrarAbono: registrarAbono
  };

  // Delegar eventos al cargar
  initListEvents();

})(window, document);
