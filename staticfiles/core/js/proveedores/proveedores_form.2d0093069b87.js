/**
 * proveedores_form.js - Gestión de Formularios Proveedores v2.61
 * Responsabilidad: Carga de Offcanvas y Persistencia (Zero Trust).
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:form]';
  const API_URL = '/api/v1/proveedores/';
  const CONTAINER_ID = '#offcanvas-container-proveedor';
  const BOOLEAN_FIELDS = ['activo', 'responsable_iva', 'gran_contribuyente', 'autoretenedor'];
  const NUMERIC_FIELDS = ['plazo_pago_dias'];

  /**
   * Abrir Offcanvas vía HTMX
   */
  async function openOffcanvas(id) {
    const url = id 
      ? `${API_URL}render-offcanvas/editar/?id=${id}` // ⚠️ Regla 6.1: render-offcanvas/
      : `${API_URL}render-offcanvas/crear/`;

    await htmx.ajax('GET', url, {
      target: CONTAINER_ID,
      swap: 'innerHTML'
    });

    const offcanvasEl = d.querySelector('.offcanvas');
    if (offcanvasEl) {
      const instance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      instance.show();
      configurarEventos(offcanvasEl);
      await cargarCuentasNIIF(offcanvasEl);
    }
  }

  /**
   * Carga dinámica de cuentas de Pasivo desde el catálogo contable
   */
  async function cargarCuentasNIIF(container) {
    const select = container.querySelector('#proveedor-codigo_contable');
    if (!select) return;

    const res = await w.http('GET', '/api/v1/contabilidad/cuentas-contables/cuentas-proveedor/');
    if (!res.ok) return;

    const cuentas = await res.json();
    if (!Array.isArray(cuentas) || cuentas.length === 0) return;

    const valorActual = select.dataset.valorSeleccionado || '';
    
    // Limpiar pero mantener la opción por defecto
    select.innerHTML = '<option value="">-- Autodetectar (Régimen/Tipo) --</option>';

    cuentas.forEach(c => {
      const opt = d.createElement('option');
      opt.value = c.codigo;
      opt.textContent = `${c.codigo} - ${c.nombre}`;
      if (c.codigo === valorActual) opt.selected = true;
      select.appendChild(opt);
    });

    if (!select.value && valorActual) {
      select.value = valorActual;
    }
  }

  function buildPayload(form) {
    const payload = {};

    form.querySelectorAll('input, select, textarea').forEach((field) => {
      const key = field.name;
      if (!key || field.disabled) return;

      if (field.type === 'checkbox') {
        payload[key] = field.checked;
        return;
      }

      let value = field.value;
      if (typeof value === 'string') {
        value = value.trim();
      }

      if (value === '') {
        if (BOOLEAN_FIELDS.includes(key)) {
          payload[key] = false;
        } else if (NUMERIC_FIELDS.includes(key)) {
          payload[key] = 0;
        } else {
          payload[key] = '';
        }
        return;
      }

      if (NUMERIC_FIELDS.includes(key)) {
        payload[key] = parseInt(value, 10) || 0;
        return;
      }

      payload[key] = value;
    });

    delete payload.id;
    return payload;
  }

  /**
   * Configurar eventos del formulario inyectado
   */
  function configurarEventos(container) {
    const form = container.querySelector('form');
    if (!form) return;

    // Guardar referencia del valor actual para el select dinámico
    const selectNIIF = form.querySelector('#proveedor-codigo_contable');
    if (selectNIIF) {
      const initialValue = selectNIIF.getAttribute('data-value') || '';
      selectNIIF.dataset.valorSeleccionado = initialValue;
    }

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      await guardar(form);
    });

    const btnGuardar = container.querySelector('#btn-guardar-proveedor');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', () => form.requestSubmit());
    }
  }

  /**
   * Persistencia Garantizada (Zero Trust + DOM Shield)
   */
  async function guardar(form) {
    if (!form.checkValidity()) return form.reportValidity();

    const id = form.querySelector('#proveedor-id')?.value || '';
    const method = id ? 'PATCH' : 'POST';
    const url = id ? `${API_URL}${id}/` : API_URL;

    const payload = buildPayload(form);

    const res = await w.http(method, url, payload);

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD, {
        errorContainerSelector: '#form-feedback'
      });
    }

    // Éxito
    w.SintelFeedback?.success(id ? 'Proveedor actualizado' : 'Proveedor creado');
    bootstrap.Offcanvas.getInstance(form.closest('.offcanvas'))?.hide();
    w.AppProveedor?.refresh();
  }

  /**
   * Acción de eliminación
   */
  async function eliminar(id) {
    if (!confirm('¿Seguro que desea eliminar este proveedor?')) return;

    const res = await w.http('DELETE', `${API_URL}${id}/`);
    if (!res.ok) return w.UIManager?.handleError(res, MOD);

    w.SintelFeedback?.success('Proveedor eliminado');
    w.AppProveedor?.refresh();
  }

  // Registro en Namespace Global
  w.AppProveedor = w.AppProveedor || {};
  w.AppProveedor.openOffcanvas = openOffcanvas;
  w.AppProveedor.eliminar = eliminar;

})(window, document);
