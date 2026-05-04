/**
 * proveedores_form.js - Gestión de Formularios Proveedores v2.61
 * Responsabilidad: Carga de Offcanvas y Persistencia (Zero Trust).
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:form]';
  const API_URL = '/api/v1/proveedores/';
  const CONTAINER_ID = '#containerOffcanvasProveedor';
  const BOOLEAN_FIELDS = ['activo', 'responsable_iva', 'gran_contribuyente', 'autoretenedor'];
  const NUMERIC_FIELDS = ['plazo_pago_dias'];

  /**
   * Abrir Offcanvas vía HTMX (v2.61.7 - Resiliente)
   */
  async function openOffcanvas(id) {
    let container = d.querySelector(CONTAINER_ID);
    
    // Auto-healing: Si el contenedor no existe, lo creamos
    if (!container) {
      console.warn(`${MOD} Contenedor ${CONTAINER_ID} no encontrado. Creando...`);
      container = d.createElement('div');
      container.id = CONTAINER_ID.substring(1);
      d.body.appendChild(container);
    }

    const url = id 
      ? `${API_URL}render-offcanvas/editar/?id=${id}` 
      : `${API_URL}render-offcanvas/crear/`;

    console.log(`${MOD} Cargando formulario desde: ${url}`);
    
    return htmx.ajax('GET', url, {
      target: CONTAINER_ID,
      swap: 'innerHTML'
    });
  }

  /**
   * Listener centralizado para inicializar el Offcanvas tras el swap de HTMX
   */
  d.body.addEventListener('htmx:afterSettle', async (e) => {
    const target = e.detail.target;
    if (target && target.id === CONTAINER_ID.substring(1)) {
      const offcanvasEl = target.querySelector('.offcanvas');
      if (!offcanvasEl) return;

      console.log(`${MOD} DOM Settle detectado, activando offcanvas...`);

      // 1. Mostrar Offcanvas vía UIManager
      if (w.UIManager?.handleOffcanvas) {
        w.UIManager.handleOffcanvas(offcanvasEl, 'show');
      } else {
        bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
      }

      // 2. Configurar validaciones y eventos
      configurarEventos(offcanvasEl);

      // 3. Cargar datos dinámicos
      await cargarCuentasNIIF(offcanvasEl);
    }
  });

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
    const payload = buildPayload(form);
    const api = w.Sintel.Proveedores.API;

    if (!api) {
        console.error(`${MOD} Sintel.Proveedores.API no disponible`);
        return;
    }

    const res = id ? await api.update(id, payload) : await api.create(payload);

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD, {
        errorContainerSelector: '#form-proveedor-feedback'
      });
    }

    // Éxito
    if (w.UIManager?.showSuccess) {
        w.UIManager.showSuccess(id ? 'Proveedor actualizado' : 'Proveedor creado');
    } else {
        w.SintelFeedback?.success(id ? 'Proveedor actualizado' : 'Proveedor creado');
    }

    // ⚠️ v2.62.3: Cerrar Offcanvas usando el orquestador central
    const offcanvasEl = form.closest('.offcanvas');
    if (offcanvasEl && w.UIManager?.handleOffcanvas) {
        w.UIManager.handleOffcanvas(offcanvasEl, 'hide');
    } else {
        bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
    }
    w.Sintel.Proveedores.Main?.refresh();
  }

  /**
   * Acción de eliminación
   */
  async function eliminar(id) {
    if (!confirm('¿Seguro que desea eliminar este proveedor?')) return;

    const api = w.Sintel.Proveedores.API;
    if (!api) return;

    const res = await api.delete(id);
    if (!res.ok) return w.UIManager?.handleError(res, MOD);

    w.SintelFeedback?.success('Proveedor eliminado');
    w.Sintel.Proveedores.Main?.refresh();
  }

  // Registro en Namespace Global v2.61.4
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.Form = {
    openOffcanvas: openOffcanvas,
    eliminar: eliminar
  };

})(window, document);
