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
  const NULLABLE_FIELDS = [];

  /**
   * Abrir Offcanvas vía HTMX (v2.61.7 - Resiliente)
   */
  async function openOffcanvas(id) {
    let container = d.querySelector(CONTAINER_ID);

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
    return htmx.ajax('GET', url, { target: CONTAINER_ID, swap: 'innerHTML' });
  }

  /**
   * Abrir Offcanvas en modo detalle (con tabs Información + Facturas de Compra).
   */
  async function openDetalle(id) {
    let container = d.querySelector(CONTAINER_ID);
    if (!container) {
      container = d.createElement('div');
      container.id = CONTAINER_ID.substring(1);
      d.body.appendChild(container);
    }
    const url = `${API_URL}render-offcanvas/detalle/?id=${id}`;
    console.log(`${MOD} Cargando detalle desde: ${url}`);
    return htmx.ajax('GET', url, { target: CONTAINER_ID, swap: 'innerHTML' });
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
        // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
      }

      // 2. Detectar modo: detalle (data-proveedor-uuid presente) vs crear/editar
      const isDetalle = !!offcanvasEl.dataset.proveedorUuid;

      if (isDetalle) {
        // Modo detalle: inicializar tabs de historial
        initHistorialCompras(offcanvasEl);
        initRepresentantes(offcanvasEl);
      } else {
        // Modo crear/editar: configurar formulario
        configurarEventos(offcanvasEl);
      }
    }
  });

  // ── Historial Facturas de Compra ─────────────────────────────────────────

  /**
   * Inicializa el tab de Facturas de Compra (lazy: carga al mostrar el tab).
   */
  function initHistorialCompras(offcanvasEl) {
    const uuid = offcanvasEl.dataset.proveedorUuid;
    if (!uuid) return;

    const tabBtn = offcanvasEl.querySelector('#tab-compras-btn');
    if (!tabBtn || tabBtn.dataset.historialBound) return;
    tabBtn.dataset.historialBound = 'true';

    // Filtros de estado (chips)
    const filtroContainer = offcanvasEl.querySelector('#historial-compras-filtros-estado');
    if (filtroContainer) {
      filtroContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-compras-estado]');
        if (!btn) return;
        filtroContainer.querySelectorAll('[data-compras-estado]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        _cargarHistorialCompras(uuid, btn.dataset.comprasEstado);
      });
    }

    // Carga lazy al activar el tab
    tabBtn.addEventListener('shown.bs.tab', () => {
      const estadoActivo = filtroContainer?.querySelector('[data-compras-estado].active')?.dataset.comprasEstado || '';
      _cargarHistorialCompras(uuid, estadoActivo);
    });
  }

  /**
   * Carga (o recarga) la grilla de Facturas de Compra filtrando por proveedor_uuid.
   */
  function _cargarHistorialCompras(uuid, estado) {
    let url = `/api/v1/facturas/?proveedor_uuid=${uuid}&naturaleza=COMPRA`;
    if (estado) url += `&estado=${encodeURIComponent(estado)}`;

    if (w.SintelProveedoresTables?.historialCompras) {
      try { w.SintelProveedoresTables.historialCompras.destroy(); } catch (_) {}
      w.SintelProveedoresTables.historialCompras = null;
    }

    const COLS = [
      {
        title: 'Número', field: 'numero', width: 130,
        formatter: (cell) => `<span class="fw-semibold small">${cell.getValue() || '—'}</span>`,
      },
      {
        title: 'Fecha', field: 'fecha_emision', width: 100,
        formatter: (cell) => {
          const v = cell.getValue();
          return v ? new Date(v).toLocaleDateString('es-CO') : '—';
        },
      },
      {
        title: 'Estado', field: 'estado', width: 110, hozAlign: 'center',
        formatter: (cell) => {
          const MAP = { ACEPTADA: 'success', ENVIADA: 'warning', ANULADA: 'danger', BORRADOR: 'secondary', RECHAZADA: 'danger' };
          const v = cell.getValue() || '';
          return `<span class="badge bg-${MAP[v] || 'secondary'}">${v}</span>`;
        },
      },
      {
        title: 'Emisor', field: 'emisor_razon_social', minWidth: 180,
        formatter: (cell) => `<span class="small">${cell.getValue() || '—'}</span>`,
      },
      {
        title: 'Total', field: 'total', width: 140, hozAlign: 'right',
        formatter: (cell) => {
          const v = parseFloat(cell.getValue()) || 0;
          return `<span class="fw-semibold text-success small">${v.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })}</span>`;
        },
      },
    ];

    if (!w.TabulatorFactory) {
      console.error(`${MOD} TabulatorFactory no disponible`);
      return;
    }

    const t = w.TabulatorFactory.create('#historial-compras-grid', url, COLS, { ajaxSorting: true });
    if (!w.SintelProveedoresTables) w.SintelProveedoresTables = {};
    w.SintelProveedoresTables.historialCompras = t;

    t.on('dataLoaded', (data) => _actualizarKPIsCompras(data));
  }

  /**
   * Actualiza los KPI cards del historial con los datos de la página cargada.
   */
  function _actualizarKPIsCompras(rows) {
    const total = rows.length;
    const monto = rows.reduce((s, r) => s + (parseFloat(r.total) || 0), 0);
    const pendiente = rows
      .filter(r => r.estado === 'ENVIADA' || r.estado === 'BORRADOR')
      .reduce((s, r) => s + (parseFloat(r.total) || 0), 0);

    const fmt = (v) => v.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
    const el = (id) => d.getElementById(id);
    if (el('ckpi-total'))    el('ckpi-total').textContent    = total;
    if (el('ckpi-monto'))    el('ckpi-monto').textContent    = fmt(monto);
    if (el('ckpi-pendiente')) el('ckpi-pendiente').textContent = fmt(pendiente);
  }

  // ── Representantes (v3.17.0) ──────────────────────────────────────────────

  /**
   * Inicializa el tab de Representantes (lazy: carga al mostrar el tab).
   * Carga la tabla de representantes cuando el usuario abre la pestaña.
   */
  function initRepresentantes(offcanvasEl) {
    const uuid = offcanvasEl.dataset.proveedorUuid;
    if (!uuid) return;

    const tabBtn = offcanvasEl.querySelector('#tab-representantes-btn');
    if (!tabBtn || tabBtn.dataset.representantesBound) return;
    tabBtn.dataset.representantesBound = 'true';

    // Carga lazy al activar el tab
    tabBtn.addEventListener('shown.bs.tab', () => {
      // Cargar tabla de representantes
      if (w.Sintel?.Proveedores?.Representante?.cargarTabla) {
        w.Sintel.Proveedores.Representante.cargarTabla(uuid);
      }
    });
  }

  // ── Formulario ───────────────────────────────────────────────────────────

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

    // Guard: evitar registrar listeners duplicados si htmx:afterSettle dispara múltiples veces
    if (form.dataset.configured === 'true') return;
    form.dataset.configured = 'true';

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

    // Notificar a otros modulos (p.ej. Compras.Utils cachea proveedores por 5min)
    // que el catalogo de proveedores cambio, para que invaliden su cache local.
    d.body.dispatchEvent(new Event('proveedor-updated'));
  }

  /**
   * Acción de eliminación
   */
  async function eliminar(id) {
    if (!(await w.UIManager?.confirm('¿Seguro que desea eliminar este proveedor?'))) return;

    const api = w.Sintel.Proveedores.API;
    if (!api) return;

    const res = await api.delete(id);
    if (!res.ok) return w.UIManager?.handleError(res, MOD);

    w.SintelFeedback?.success('Proveedor eliminado');
    w.Sintel.Proveedores.Main?.refresh();
    d.body.dispatchEvent(new Event('proveedor-updated'));
  }

  // Registro en Namespace Global v2.61.4
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.Form = {
    openOffcanvas: openOffcanvas,
    openDetalle: openDetalle,
    eliminar: eliminar,
  };

})(window, document);
