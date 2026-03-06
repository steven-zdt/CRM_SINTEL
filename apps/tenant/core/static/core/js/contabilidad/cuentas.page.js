/**
 * cuentas.page.js - Módulo Contabilidad Cuentas v3.3 - Migrado a Tabulator
 * 
 * ⚠️ v3.3: Migrado de DataTables a Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 */

(function (w, d) {
  'use strict';

  const NS = '[cuentas.page]';
  const MOD = 'cuentas';
  const TABLE_ID = '#table-contabilidad-cuentas';
  const API_BASE = '/api/v1/contabilidad/cuentas-contables/';
  
  // Estado del módulo
  let state = {
    initialized: false,
    listenersAttached: false,
    table: null,
    routes: null
  };

  // Logger TOLERANTE
  const DEBUG = (w?.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true) || false;
  function log(...args) { if (DEBUG) console.debug(NS, ...args); }
  function error(...args) { console.error(NS, ...args); }
  function warn(...args) { console.warn(NS, ...args); }

  // ========= Utils =========

  function getEl(id) {
    return d.getElementById(id);
  }

  function getValueOrNull(id) {
    const el = getEl(id);
    const v = el?.value?.trim();
    return v && v.length > 0 ? v : null;
  }

  function formatDateTime(isoStr) {
    if (!isoStr) return '-';
    try {
      const dt = new Date(isoStr);
      if (Number.isNaN(dt.getTime())) return '-';
      return dt.toLocaleString('es-CO');
    } catch {
      return '-';
    }
  }

  function showFeedback(selector, message, type = 'info') {
    const element = w.DOMUtils?.getEl(selector) || d.querySelector(selector);
    if (element) {
      const classes = {
        'success': 'alert alert-success',
        'error': 'alert alert-danger',
        'warning': 'alert alert-warning',
        'info': 'alert alert-info'
      };
      element.className = classes[type] || classes['info'];
      element.textContent = message;
      element.classList.remove('d-none');
    }
  }

  // ========= Limpieza de modales =========

  function limpiarModales() {
    // Ver
    ['codigo', 'nombre', 'tipo', 'activa', 'descripcion', 'cuenta_padre'].forEach(field => {
      const input = getEl(`cuenta-view-${field}`);
      if (input) input.value = '';
    });
    const viewFeedback = getEl('cuenta-view-feedback');
    if (viewFeedback) { viewFeedback.classList.add('d-none'); viewFeedback.textContent = ''; }

    // Editar
    ['codigo', 'nombre', 'tipo', 'activa', 'descripcion', 'cuenta_padre'].forEach(field => {
      const input = getEl(`cuenta-edit-${field}`);
      if (input) {
        if (input.tagName === 'SELECT') input.selectedIndex = 0;
        else input.value = '';
      }
    });
    const editModal = getEl('modal-editar-cuenta');
    if (editModal) { delete editModal.dataset.id; }
    const editFeedback = getEl('cuenta-edit-feedback');
    if (editFeedback) { editFeedback.classList.add('d-none'); editFeedback.textContent = ''; }

    // Crear
    ['codigo', 'nombre', 'tipo', 'activa', 'descripcion', 'cuenta_padre'].forEach(field => {
      const input = getEl(`cuenta-create-${field}`);
      if (input) {
        if (input.tagName === 'SELECT') input.selectedIndex = 0;
        else input.value = '';
      }
    });
    const createFeedback = getEl('cuenta-create-feedback');
    if (createFeedback) { createFeedback.classList.add('d-none'); createFeedback.textContent = ''; }

    // Eliminar
    const deleteInfo = getEl('cuenta-delete-info');
    if (deleteInfo) deleteInfo.textContent = '';
    const deleteModal = getEl('modal-eliminar-cuenta');
    if (deleteModal) { delete deleteModal.dataset.id; }
    const deleteFeedback = getEl('cuenta-delete-feedback');
    if (deleteFeedback) { deleteFeedback.classList.add('d-none'); deleteFeedback.textContent = ''; }
  }

  // ========= Fetchers =========

  async function fetchCuentaDetail(id) {
    if (!id) throw new Error('ID de cuenta requerido');
    
    log('Fetch detalle ID:', id);
    try {
      const detailUrl = await w.Routes?.detailUrl('contabilidad.cuentas', id);
      const url = detailUrl || `${API_BASE}${id}/`;
      log('Usando retrieve con ID:', url);
      return await w.API_HELPERS.safeFetchJson(url, { method: 'GET' });
    } catch (err) {
      error('Error en fetchCuentaDetail:', err);
      throw err;
    }
  }

  // ========= Handlers UI =========

  async function handleVerCuenta(id) {
    if (!id) {
      showFeedback('#cuenta-view-feedback', 'Error: ID de cuenta requerido', 'error');
      return;
    }
    
    try {
      const data = await fetchCuentaDetail(id);
      
      const fields = {
        codigo: data.codigo || '',
        nombre: data.nombre || '',
        tipo: data.tipo || '',
        activa: data.activa ? 'Activa' : 'Inactiva',
        descripcion: data.descripcion || '',
        cuenta_padre: data.cuenta_padre ? `ID: ${data.cuenta_padre}` : 'Ninguna'
      };

      Object.keys(fields).forEach(field => {
        const input = getEl(`cuenta-view-${field}`);
        if (input) input.value = fields[field];
      });

      const modalEl = getEl('modal-ver-cuenta');
      if (modalEl) {
        // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
        if (w.bootstrap && w.bootstrap.Modal) {
          const modal = w.bootstrap.Modal.getOrCreateInstance(modalEl);
          modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
            const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) {
              firstInput.focus();
            }
            modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
          }, { once: true });
          modal.show();
        } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          // Fallback: usar UIManager si Bootstrap no está disponible
          const modalId = modalEl.id ? `#${modalEl.id}` : null;
          if (modalId) {
            w.UIManager.handleModal(modalId, 'show');
          }
        }
      } else {
        error('Modal ver-cuenta no encontrado');
      }
    } catch (err) {
      error('Error en handleVerCuenta:', err);
      showFeedback('#cuenta-view-feedback', `Error cargando cuenta: ${err.message}`, 'error');
    }
  }

  async function handleEditarCuenta(id) {
    if (!id) {
      showFeedback('#cuenta-edit-feedback', 'Error: ID de cuenta requerido', 'error');
      return;
    }
    
    try {
      const data = await fetchCuentaDetail(id);
      
      const fields = {
        codigo: data.codigo || '',
        nombre: data.nombre || '',
        tipo: data.tipo || '',
        activa: data.activa ? 'true' : 'false',
        descripcion: data.descripcion || '',
        cuenta_padre: data.cuenta_padre || ''
      };

      Object.keys(fields).forEach(field => {
        const input = getEl(`cuenta-edit-${field}`);
        if (input) input.value = fields[field];
      });

      const modal = getEl('modal-editar-cuenta');
      if (modal) {
        if (data.id) modal.dataset.id = data.id;
        else delete modal.dataset.id;
        bootstrap.Modal.getOrCreateInstance(modal).show();
      } else {
        error('Modal editar-cuenta no encontrado');
      }
    } catch (err) {
      error('Error en handleEditarCuenta:', err);
      showFeedback('#cuenta-edit-feedback', `Error cargando cuenta: ${err.message}`, 'error');
    }
  }

  // ========= Guardar (PATCH) =========

  async function handleGuardarCuenta() {
    const modal = getEl('modal-editar-cuenta');
    if (!modal) { error('Modal editar no encontrado'); return; }

    const id = modal.dataset.id;
    if (!id) {
      showFeedback('#cuenta-edit-feedback', 'Error: ID de cuenta no encontrado', 'error');
      return;
    }

    const payload = {
      codigo: getValueOrNull('cuenta-edit-codigo') || '',
      nombre: getValueOrNull('cuenta-edit-nombre') || '',
      tipo: getValueOrNull('cuenta-edit-tipo') || '',
      activa: getValueOrNull('cuenta-edit-activa') === 'true',
      descripcion: getValueOrNull('cuenta-edit-descripcion'),
      cuenta_padre: (() => {
        const v = getValueOrNull('cuenta-edit-cuenta_padre');
        return v ? parseInt(v) : null;
      })()
    };

    try {
      let result;
      if (w.CRUD?.update) {
        result = await w.CRUD.update('contabilidad.cuentas', id, payload);
      } else {
        const detailUrl = await w.Routes?.detailUrl('contabilidad.cuentas', id);
        const url = detailUrl || `${API_BASE}${id}/`;
        await w.API_HELPERS.safeFetchJson(url, { method: 'PATCH', body: JSON.stringify(payload) });
        result = { ok: true, status: 200 };
      }

      if (!result?.ok) throw new Error(result.data?.detail || 'Error actualizando cuenta');

      log('Cuenta actualizada correctamente');
      showFeedback('#cuenta-edit-feedback', 'Cuenta actualizada correctamente', 'success');

      // Recargar tabla Tabulator
      if (state.table && typeof state.table.replaceData === 'function') {
        state.table.replaceData();
      }

      setTimeout(() => {
        // ⚠️ v2.60: Usar UIManager para cerrar modal
        if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          const modalId = modal.id ? `#${modal.id}` : null;
          if (modalId) {
            w.UIManager.handleModal(modalId, 'hide');
          }
        }
        limpiarModales();
      }, 800);
    } catch (err) {
      error('Error en handleGuardarCuenta:', err);
      if (err.status === 422 && err.fields) {
        let msg = err.message || 'Datos inválidos (422). Verifica los campos.';
        showFeedback('#cuenta-edit-feedback', msg, 'error');
      } else if (err.status === 401) {
        showFeedback('#cuenta-edit-feedback', 'Sesión expirada. Por favor, recarga la página.', 'error');
      } else {
        showFeedback('#cuenta-edit-feedback', err.message || 'Error inesperado', 'error');
      }
    }
  }

  // ========= Crear (POST) =========

  async function handleCrearCuenta() {
    const payload = {
      codigo: getValueOrNull('cuenta-create-codigo') || '',
      nombre: getValueOrNull('cuenta-create-nombre') || '',
      tipo: getValueOrNull('cuenta-create-tipo') || '',
      activa: getValueOrNull('cuenta-create-activa') === 'true',
      descripcion: getValueOrNull('cuenta-create-descripcion'),
      cuenta_padre: (() => {
        const v = getValueOrNull('cuenta-create-cuenta_padre');
        return v ? parseInt(v) : null;
      })()
    };

    try {
      let result;
      if (w.CRUD?.create) {
        result = await w.CRUD.create('contabilidad.cuentas', payload);
      } else {
        const collectionUrl = await w.Routes?.collectionUrl('contabilidad.cuentas');
        const url = collectionUrl || API_BASE;
        await w.API_HELPERS.safeFetchJson(url, { method: 'POST', body: JSON.stringify(payload) });
        result = { ok: true, status: 201 };
      }

      if (!result?.ok) throw new Error(result.data?.detail || 'Error creando cuenta');

      log('Cuenta creada correctamente');
      showFeedback('#cuenta-create-feedback', 'Cuenta creada correctamente', 'success');

      // Recargar tabla Tabulator
      if (state.table && typeof state.table.replaceData === 'function') {
        state.table.replaceData();
      }

      setTimeout(() => {
        const modal = getEl('modal-crear-cuenta');
        if (modal) {
          // ⚠️ v2.60: Usar UIManager para cerrar modal
        if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          const modalId = modal.id ? `#${modal.id}` : null;
          if (modalId) {
            w.UIManager.handleModal(modalId, 'hide');
          }
        }
        }
        limpiarModales();
      }, 800);
    } catch (err) {
      error('Error en handleCrearCuenta:', err);
      if (err.status === 422 && err.fields) {
        let msg = err.message || 'Datos inválidos (422). Verifica los campos.';
        showFeedback('#cuenta-create-feedback', msg, 'error');
      } else if (err.status === 404) {
        showFeedback('#cuenta-create-feedback', 'Endpoint no encontrado. Verifica la configuración del backend.', 'error');
      } else if (err.status === 401) {
        showFeedback('#cuenta-create-feedback', 'Sesión expirada. Por favor, recarga la página.', 'error');
      } else {
        showFeedback('#cuenta-create-feedback', err.message || 'Error inesperado al crear cuenta', 'error');
      }
    }
  }

  // ========= Eliminar (DELETE) =========

  async function handleEliminarCuenta(id) {
    if (!id) {
      showFeedback('#cuenta-delete-feedback', 'Error: ID de cuenta requerido', 'error');
      return;
    }

    try {
      let result;
      if (w.CRUD?.delete) {
        result = await w.CRUD.delete('contabilidad.cuentas', id);
      } else {
        const detailUrl = await w.Routes?.detailUrl('contabilidad.cuentas', id);
        const url = detailUrl || `${API_BASE}${id}/`;
        const response = await fetch(url, {
          method: 'DELETE',
          headers: w.API_HELPERS.authHeaders(),
          credentials: 'same-origin'
        });
        result = { ok: response.ok, status: response.status };
      }

      if (!result?.ok) {
        const msg = result?.data?.detail || `Error ${result?.status || 'unknown'}`;
        throw new Error(msg);
      }

      showFeedback('#cuenta-delete-feedback', 'Cuenta eliminada correctamente', 'success');

      // Recargar tabla Tabulator
      if (state.table && typeof state.table.replaceData === 'function') {
        state.table.replaceData();
      }

      setTimeout(() => {
        const modal = getEl('modal-eliminar-cuenta');
        if (modal) {
          // ⚠️ v2.60: Usar UIManager para cerrar modal
        if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          const modalId = modal.id ? `#${modal.id}` : null;
          if (modalId) {
            w.UIManager.handleModal(modalId, 'hide');
          }
        }
        }
        limpiarModales();
      }, 800);
    } catch (err) {
      error('Error en handleEliminarCuenta:', err);
      if (err.status === 401) {
        showFeedback('#cuenta-delete-feedback', 'Sesión expirada. Por favor, recarga la página.', 'error');
      } else if (err.status === 409) {
        showFeedback('#cuenta-delete-feedback', 'No se puede eliminar la cuenta debido a relaciones existentes.', 'error');
      } else {
        showFeedback('#cuenta-delete-feedback', err.message || 'Error inesperado', 'error');
      }
    }
  }

  // ========= Tabulator Columns =========

  function getColumns() {
    return [
      {
        title: "Código",
        field: "codigo",
        headerFilter: "input",
        headerFilterPlaceholder: "Buscar código...",
        formatter: function(cell) {
          const value = cell.getValue();
          return value || '-';
        }
      },
      {
        title: "Nombre",
        field: "nombre",
        headerFilter: "input",
        headerFilterPlaceholder: "Buscar nombre...",
        formatter: function(cell) {
          const value = cell.getValue();
          return value || '-';
        }
      },
      {
        title: "Tipo",
        field: "tipo",
        formatter: function(cell) {
          const data = cell.getValue();
          if (!data) return '-';
          const badges = {
            'ACTIVO': 'primary',
            'PASIVO': 'danger',
            'PATRIMONIO': 'success',
            'INGRESO': 'info',
            'GASTO': 'warning'
          };
          const badge = badges[data] || 'secondary';
          return `<span class="badge bg-${badge}">${data}</span>`;
        }
      },
      {
        title: "Estado",
        field: "activa",
        formatter: function(cell) {
          const data = cell.getValue();
          if (data === true || data === 'true') {
            return '<span class="badge bg-success">Activa</span>';
          } else {
            return '<span class="badge bg-secondary">Inactiva</span>';
          }
        },
        headerSort: false
      },
      {
        title: "Creado",
        field: "created_at",
        formatter: function(cell) {
          return formatDateTime(cell.getValue());
        }
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const cuentaId = rowData.id || '';
          if (!cuentaId) return '-';
          return `
            <div class="btn-group">
              <button class="btn btn-sm btn-secondary btn-ver" data-id="${cuentaId}">Ver</button>
              <button class="btn btn-sm btn-primary btn-editar" data-id="${cuentaId}">Editar</button>
              <button class="btn btn-sm btn-danger btn-eliminar" data-id="${cuentaId}">Eliminar</button>
            </div>
          `;
        },
        headerSort: false,
        hozAlign: "right",
        width: 200
      }
    ];
  }

  // ========= Inicializar Tabulator =========

  function initTabulator() {
    if (!w.TabulatorFactory) {
      error('TabulatorFactory no está disponible');
      return;
    }

    const tableEl = d.querySelector(TABLE_ID);
    if (!tableEl) {
      error('Tabla no encontrada:', TABLE_ID);
      return null;
    }

    // ⚠️ v3.3: Usar TabulatorFactory en lugar de DataTablesUtils
    state.table = w.TabulatorFactory.create(
      TABLE_ID,
      API_BASE,
      getColumns(),
      {
        searchInputSelector: '#search-contabilidad-cuentas',
        paginationSize: 10
      }
    );

    // Botón refrescar
    const btnReload = getEl('btn-refrescar-contabilidad-cuentas');
    if (btnReload && state.table) {
      btnReload.addEventListener('click', () => {
        if (state.table && typeof state.table.replaceData === 'function') {
          state.table.replaceData();
        }
      });
    }

    return state.table;
  }

  // ========= Listeners =========

  function attachListenersOnce() {
    if (state.listenersAttached) { log('Listeners ya adjuntados'); return; }

    // Ver
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-ver');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id || null;
        if (id) handleVerCuenta(id);
      }
    });

    // Editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-editar');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id || null;
        if (id) handleEditarCuenta(id);
      }
    });

    // Eliminar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-eliminar');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id || null;
        if (id) {
          fetchCuentaDetail(id).then(data => {
            const deleteInfo = getEl('cuenta-delete-info');
            if (deleteInfo) {
              deleteInfo.textContent = `${data.codigo || 'Cuenta'} - ${data.nombre || ''}`;
            }
            const deleteModal = getEl('modal-eliminar-cuenta');
            if (deleteModal) {
              deleteModal.dataset.id = id;
              bootstrap.Modal.getOrCreateInstance(deleteModal).show();
            }
          }).catch(err => {
            error('Error cargando datos para eliminar:', err);
            showFeedback('#cuenta-delete-feedback', `Error: ${err.message}`, 'error');
          });
        }
      }
    });

    // Crear (toolbar)
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-crear-cuenta');
      if (btn) {
        ev.preventDefault();
        ev.stopPropagation();
        log('Botón Crear Cuenta');
        limpiarModales();
        const modalEl = getEl('modal-crear-cuenta');
        if (modalEl) {
          // ⚠️ v2.60: Usar UIManager para manejo de modales
        // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
        if (w.bootstrap && w.bootstrap.Modal) {
          const modal = w.bootstrap.Modal.getOrCreateInstance(modalEl);
          modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
            const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) {
              firstInput.focus();
            }
            modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
          }, { once: true });
          modal.show();
        } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          // Fallback: usar UIManager si Bootstrap no está disponible
          const modalId = modalEl.id ? `#${modalEl.id}` : null;
          if (modalId) {
            w.UIManager.handleModal(modalId, 'show');
          }
        }
        } else {
          error('Modal crear-cuenta no encontrado');
        }
      }
    });

    // Guardar (modal editar)
    const btnGuardar = getEl('btn-guardar-cuenta');
    if (btnGuardar) btnGuardar.addEventListener('click', () => handleGuardarCuenta());

    // Crear (modal crear)
    const btnCrearModal = getEl('btn-crear-cuenta-modal');
    if (btnCrearModal) btnCrearModal.addEventListener('click', () => handleCrearCuenta());

    // Confirmar Eliminar
    const btnConfirmarEliminar = getEl('btn-confirmar-eliminar-cuenta');
    if (btnConfirmarEliminar) {
      btnConfirmarEliminar.addEventListener('click', () => {
        const deleteModal = getEl('modal-eliminar-cuenta');
        if (deleteModal && deleteModal.dataset.id) {
          handleEliminarCuenta(deleteModal.dataset.id);
        }
      });
    }

    // Limpiar al cerrar modales
    ['modal-ver-cuenta', 'modal-editar-cuenta', 'modal-crear-cuenta', 'modal-eliminar-cuenta'].forEach(modalId => {
      const modalEl = getEl(modalId);
      if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => limpiarModales());
        modalEl.querySelectorAll('[data-bs-dismiss="modal"], .btn-close').forEach(btn => {
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl)).hide();
          });
        });
      }
    });

    state.listenersAttached = true;
  }

  // ========= Init =========

  function requireCore() {
    if (!w.API_HELPERS) throw new Error('API_HELPERS no está disponible.');
    if (!w.TabulatorFactory) throw new Error('TabulatorFactory no está disponible.');
    if (!w.Routes) {
      warn('Routes no está disponible. Usando URLs directas como fallback.');
      // Fallback: usar URLs directas si Routes no está disponible
      state.routes = {
        detailUrl: (name, id) => Promise.resolve(`${API_BASE}${id}/`),
        collectionUrl: (name) => Promise.resolve(API_BASE)
      };
    }
    if (!w.CRUD) throw new Error('CRUD no está disponible.');
    if (!w.DOMUtils) throw new Error('DOMUtils no está disponible.');
  }

  async function init() {
    try {
      requireCore();
      if (state.initialized) { log('Módulo ya inicializado'); return; }

      log('Inicializando módulo Cuentas Contables...');
      
      if (w.Routes?.get) {
        state.routes = await w.Routes.get('contabilidad');
        log('Rutas cargadas:', state.routes);
      }

      attachListenersOnce();
      
      // ⚠️ v3.3: Lazy INIT con Tabulator
      if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
        w.DOMUtils.onVisibleOnce('#pane-contabilidad-cuentas', async () => {
          try {
            state.table = initTabulator();
            log('Tabulator Cuentas Contables inicializado (lazy)');
          } catch (err) {
            error('Error inicializando Tabulator Cuentas Contables (lazy):', err);
          }
        });
      } else {
        warn('DOMUtils.onVisibleOnce no está disponible, inicializando inmediatamente');
        state.table = initTabulator();
      }
      
      state.initialized = true;
      log('Módulo Cuentas Contables inicializado');
    } catch (e) {
      error('Error inicializando módulo:', e);
    }
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', () => { init().catch(err => error('Error inicializando módulo:', err)); }, { once: true });
  } else {
    init().catch(err => error('Error inicializando módulo:', err));
  }

  if (typeof w !== 'undefined') {
    w.cuentasDT = Object.freeze({
      init,
      reload: async () => {
        if (state.table && typeof state.table.replaceData === 'function') {
          state.table.replaceData();
        } else {
          await init();
        }
      }
    });
  }
})(window, document);
