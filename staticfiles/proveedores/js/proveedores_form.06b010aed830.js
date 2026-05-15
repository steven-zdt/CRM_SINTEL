/**
 * proveedores_form.js - Gestión de Formularios Proveedores v2.61
 * Responsabilidad: Carga de Offcanvas y Persistencia (Zero Trust).
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:form]';
  const API_URL = '/api/v1/proveedores/';
  const CONTAINER_ID = '#offcanvas-container-proveedores';
  const BOOLEAN_FIELDS = [
    'activo', 'responsable_iva', 'gran_contribuyente', 'autoretenedor',
    'es_retenedor', 'aplica_retefuente', 'aplica_reteica', 'aplica_reteiva'
  ];
  const NUMERIC_FIELDS = [
    'plazo_pago_dias',
    'retefuente_porcentaje',
    'reteica_porcentaje',
    'reteiva_porcentaje'
  ];
  const NULLABLE_FIELDS = [
    'cuenta_contable_uuid'
  ];

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
    if (target && ('#' + target.id) === CONTAINER_ID) {
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

      // v3.5+ - Inicializar búsqueda dinámica de Cuenta Contable con actualización en cascada
      if (typeof Sintel.Proveedores.Utils?.setupCuentaAutocomplete === 'function') {
          Sintel.Proveedores.Utils.setupCuentaAutocomplete({
              inputId: 'proveedor-cuenta_contable_label',
              hiddenId: 'proveedor-cuenta_contable_uuid',
              resultsId: 'proveedor-cuenta-resultados',
              cascadeTriggers: [
                  'proveedor-tipo_persona',       // Tipo persona (NATURAL/JURIDICA)
                  'proveedor-tipo_documento',     // Tipo documento (NIT/CC/CE)
                  'proveedor-regimen_tributario', // Régimen tributario (ORDINARIO/SIMPLIFICADO)
                  'proveedor-responsable_iva',    // Estado fiscal: responsable de IVA
                  'proveedor-gran_contribuyente', // Estado fiscal: gran contribuyente
                  'proveedor-autoretenedor',      // Estado fiscal: autoretenedor
                  'proveedor-es_retenedor'        // Estado fiscal: agente retenedor
              ]
          });
      }
    }
  });

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
        } else if (NULLABLE_FIELDS.includes(key)) {
          payload[key] = null;
        } else {
          payload[key] = '';
        }
        return;
      }

      if (NUMERIC_FIELDS.includes(key)) {
        // v3.5.3: Usar parseFloat para soportar porcentajes decimales (ReteICA, etc)
        payload[key] = parseFloat(value) || 0;
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


    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      await guardar(form);
    });

    const btnGuardar = container.querySelector('#btn-guardar-proveedor');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', () => form.requestSubmit());
    }

    // [v3.5.0] Lógica de Retenciones
    const checkRetenedor = form.querySelector('#proveedor-es_retenedor');
    const contenedorRetenciones = form.querySelector('#contenedor-retenciones');
    
    if (checkRetenedor && contenedorRetenciones) {
      const toggleRetenciones = () => {
        const isRetenedor = checkRetenedor.checked;
        contenedorRetenciones.classList.toggle('d-none', !isRetenedor);
        
        if (!isRetenedor) {
          // Limpiar todo si se apaga el switch (Zero Waste Frontend)
          ['aplica_retefuente', 'aplica_reteica', 'aplica_reteiva'].forEach(f => {
            const cb = form.querySelector(`#proveedor-${f}`);
            if (cb) cb.checked = false;
          });
          ['retefuente_porcentaje', 'reteica_porcentaje', 'reteiva_porcentaje'].forEach(f => {
            const inp = form.querySelector(`#proveedor-${f}`);
            if (inp) inp.value = 0;
          });
        }
      };

      // v3.5.1: Control fino por campo de retención
      ['retefuente', 'reteica', 'reteiva'].forEach(key => {
        const cb = form.querySelector(`#proveedor-aplica_${key}`);
        const inp = form.querySelector(`#proveedor-${key}_porcentaje`);
        if (cb && inp) {
          const syncInput = () => {
            inp.disabled = !cb.checked;
            if (!cb.checked) inp.value = 0;
          };
          cb.addEventListener('change', syncInput);
          syncInput(); // Inicial
        }
      });

      checkRetenedor.addEventListener('change', toggleRetenciones);
      // Ejecutar inicial (para modo edición)
      toggleRetenciones();
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
