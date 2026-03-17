/**
 * clientes.contactos.js - Módulo de Contactos v2.61
 * Lógica modularizada para la gestión de contactos de clientes.
 * 
 * Sincronizado con:
 * - apps/tenant/core/api/v1/clientes/urls.py (Endpoint base: /api/v1/core/v1/clientes/contactos/)
 * - apps/tenant/core/api/v1/clientes/viewsets.py (ContactoClienteCoreViewSet)
 */
(function (w, d) {
  'use strict';
  const MOD = '[clientes.contactos]';
  const API_URL = '/api/v1/core/v1/clientes/contactos/';

  /**
   * Inicializa la lógica del editor de contactos dentro del offcanvas.
   * @param {Object} detail - Event detail que incluye cliente_id
   */
  async function initContactosEditor(detail) {
      const clienteId = detail?.cliente_id;
      const btnGuardar = d.querySelector('#btn-guardar-contacto');
      
      if (!btnGuardar) return;

      // Limpiar listeners previos para evitar duplicados
      const newBtn = btnGuardar.cloneNode(true);
      btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);

      newBtn.addEventListener('click', async () => {
          const form = d.querySelector('#form-contacto');
          if (!form) return;
          
          const payload = Object.fromEntries(new FormData(form).entries());
          if (clienteId) payload.cliente = clienteId;

          // Petición al endpoint CORE (facade)
          const res = await w.http('POST', API_URL, payload);
          
          if (res.ok) {
              w.SintelFeedback.success('Contacto agregado correctamente');
              d.dispatchEvent(new CustomEvent('contactoGuardado'));
              
              const offcanvasEl = d.getElementById('offcanvas-contactos');
              if (offcanvasEl) {
                  bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).hide();
              }
          } else {
              w.UIManager.handleError(res, MOD);
          }
      });
  }

  d.addEventListener('initContactosEditor', initContactosEditor);
})(window, document);
