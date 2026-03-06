/**
 * contabilidad.page.js - Módulo Contabilidad v2.37 (OLA 3)
 * 
 * ⚠️ OLA 3: Migrado a helpers centralizados
 * - Routes para discovery de URLs (con subclaves cuentas/asientos)
 * - DataTablesUtils.initServerSide para inicialización
 * - DOMUtils para visibilidad
 * - API_HELPERS/CRUD para HTTP unificado
 * - Acciones CRUD completas
 */

(function () {
  'use strict';

  const MOD = 'contabilidad';
  const TABLE_CUENTAS_ID = '#table-contabilidad-cuentas';
  const TABLE_ASIENTOS_ID = '#table-contabilidad-asientos';
  
  let dtInstanceCuentas = null;
  let dtInstanceAsientos = null;
  let routes = null;

  // Columnas para Cuentas Contables
  const COLUMNS_CUENTAS = [
    { data: 'id', visible: false },
    { data: 'codigo' },
    { data: 'nombre' },
    { 
      data: 'tipo',
      render: function (data, type, row) {
        const badges = { 'ACTIVO': 'success', 'PASIVO': 'warning', 'PATRIMONIO': 'info', 'INGRESO': 'primary', 'GASTO': 'danger' };
        const badge = badges[data] || 'secondary';
        return `<span class="badge bg-${badge}">${data || '-'}</span>`;
      }
    },
    { 
      data: 'activa',
      render: function (data, type, row) {
        const badge = data ? 'success' : 'secondary';
        const text = data ? 'Activa' : 'Inactiva';
        return `<span class="badge bg-${badge}">${text}</span>`;
      }
    },
    {
      data: null,
      orderable: false,
      searchable: false,
      className: 'text-end',
      render: function (data, type, row) {
        return `
          <button data-action="view" data-id="${row.id}" 
                  class="btn btn-sm btn-outline-primary">Ver</button>
          <button data-action="edit" data-id="${row.id}" 
                  class="btn btn-sm btn-outline-secondary">Editar</button>
          <button data-action="delete" data-id="${row.id}" 
                  class="btn btn-sm btn-danger">Eliminar</button>
        `;
      },
    },
  ];

  // Columnas para Asientos Contables
  const COLUMNS_ASIENTOS = [
    { data: 'id', visible: false },
    { data: 'numero' },
    { 
      data: 'fecha',
      render: function (data, type, row) {
        if (!data) return '-';
        const date = new Date(data);
        return date.toLocaleDateString('es-CO');
      }
    },
    { data: 'descripcion' },
    { 
      data: 'estado',
      render: function (data, type, row) {
        const badges = { 'BORRADOR': 'secondary', 'APROBADO': 'success', 'CERRADO': 'info' };
        const badge = badges[data] || 'secondary';
        return `<span class="badge bg-${badge}">${data || '-'}</span>`;
      }
    },
    { 
      data: 'total_debe',
      className: 'text-end',
      render: function (data, type, row) {
        const formatter = new Intl.NumberFormat('es-CO', {
          style: 'currency',
          currency: 'COP',
        });
        return formatter.format(data || 0);
      }
    },
    { 
      data: 'total_haber',
      className: 'text-end',
      render: function (data, type, row) {
        const formatter = new Intl.NumberFormat('es-CO', {
          style: 'currency',
          currency: 'COP',
        });
        return formatter.format(data || 0);
      }
    },
    {
      data: null,
      orderable: false,
      searchable: false,
      className: 'text-end',
      render: function (data, type, row) {
        return `
          <button data-action="view" data-id="${row.id}" 
                  class="btn btn-sm btn-outline-primary">Ver</button>
          <button data-action="edit" data-id="${row.id}" 
                  class="btn btn-sm btn-outline-secondary">Editar</button>
          <button data-action="delete" data-id="${row.id}" 
                  class="btn btn-sm btn-danger">Eliminar</button>
        `;
      },
    },
  ];

  /**
   * Construir URL de detalle usando Routes (con subclave)
   */
  async function getDetailUrl(resource, id) {
    if (window.Routes && typeof window.Routes.get === 'function') {
      const moduleRoutes = await window.Routes.get(`${MOD}.${resource}`);
      if (moduleRoutes?.detail) {
        return moduleRoutes.detail.replace('{id}', String(id));
      }
    }
    // Fallback temporal
    return `/api/v1/contabilidad/${resource}-contables/${id}/`;
  }

  /**
   * Inicializa DataTable para Cuentas Contables usando initServerSide
   * ⚠️ OLA 3: Usa DataTablesUtils.initServerSide con Routes
   */
  async function initDataTableCuentas() {
    try {
      // Cargar rutas del módulo si no están cargadas
      if (!routes && window.Routes && typeof window.Routes.get === 'function') {
        routes = await window.Routes.get(MOD);
      }
      
      // Obtener endpoint de DataTable desde Routes (subclave cuentas)
      const endpoint = routes?.cuentas?.datatable || '/api/v1/contabilidad/dt/cuentas-contables/'; // TODO: eliminar fallback
      
      // Esperar visibilidad usando DOMUtils
      await window.DOMUtils.waitForVisible(TABLE_CUENTAS_ID, { timeout: 10000 });
      
      // Inicializar DataTable usando helper centralizado
      dtInstanceCuentas = await window.DataTablesUtils.initServerSide({
        table: TABLE_CUENTAS_ID,
        endpoint: endpoint,
        columns: COLUMNS_CUENTAS,
        options: {
          order: [[1, 'asc']],
          searching: false,
          autoWidth: false,
          data: function (d) {
            const searchValue = document.querySelector(`#txt-buscar-${MOD}-cuentas`)?.value || '';
            d.search = { value: searchValue };
            return d;
          },
          error: function (xhr, error, thrown) {
            console.error(`[${MOD}.page] Error en ajax cuentas:`, error, thrown);
            const feedback = document.getElementById(`feedback-${MOD}-cuentas-list`);
            if (feedback) {
              feedback.className = 'alert alert-danger';
              feedback.textContent = `Error cargando cuentas: ${error || 'Error desconocido'}`;
              feedback.classList.remove('d-none');
            }
          }
        }
      });
      
      console.debug(`[${MOD}.page] DataTable cuentas inicializado correctamente`);
      
      // Exportar para uso global
      window[`initDataTable_${MOD.toUpperCase()}_CUENTAS`] = initDataTableCuentas;
      window[`reloadDT_${MOD.toUpperCase()}_CUENTAS`] = function() {
        if (dtInstanceCuentas) {
          dtInstanceCuentas.ajax.reload(null, false);
        }
      };
      
      return dtInstanceCuentas;
    } catch (err) {
      console.error(`[${MOD}.page] Error inicializando DataTable cuentas:`, err);
      const feedback = document.getElementById(`feedback-${MOD}-cuentas-list`);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error inicializando tabla: ${err.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
      dtInstanceCuentas = null;
      return null;
    }
  }

  /**
   * Inicializa DataTable para Asientos Contables usando initServerSide
   * ⚠️ OLA 3: Usa DataTablesUtils.initServerSide con Routes
   */
  async function initDataTableAsientos() {
    try {
      // Cargar rutas del módulo si no están cargadas
      if (!routes && window.Routes && typeof window.Routes.get === 'function') {
        routes = await window.Routes.get(MOD);
      }
      
      // Obtener endpoint de DataTable desde Routes (subclave asientos)
      const endpoint = routes?.asientos?.datatable || '/api/v1/contabilidad/dt/asientos-contables/'; // TODO: eliminar fallback
      
      // Esperar visibilidad usando DOMUtils
      await window.DOMUtils.waitForVisible(TABLE_ASIENTOS_ID, { timeout: 10000 });
      
      // Inicializar DataTable usando helper centralizado
      dtInstanceAsientos = await window.DataTablesUtils.initServerSide({
        table: TABLE_ASIENTOS_ID,
        endpoint: endpoint,
        columns: COLUMNS_ASIENTOS,
        options: {
          order: [[2, 'desc']],
          searching: false,
          autoWidth: false,
          data: function (d) {
            const searchValue = document.querySelector(`#txt-buscar-${MOD}-asientos`)?.value || '';
            d.search = { value: searchValue };
            return d;
          },
          error: function (xhr, error, thrown) {
            console.error(`[${MOD}.page] Error en ajax asientos:`, error, thrown);
            const feedback = document.getElementById(`feedback-${MOD}-asientos-list`);
            if (feedback) {
              feedback.className = 'alert alert-danger';
              feedback.textContent = `Error cargando asientos: ${error || 'Error desconocido'}`;
              feedback.classList.remove('d-none');
            }
          }
        }
      });
      
      console.debug(`[${MOD}.page] DataTable asientos inicializado correctamente`);
      
      // Exportar para uso global
      window[`initDataTable_${MOD.toUpperCase()}_ASIENTOS`] = initDataTableAsientos;
      window[`reloadDT_${MOD.toUpperCase()}_ASIENTOS`] = function() {
        if (dtInstanceAsientos) {
          dtInstanceAsientos.ajax.reload(null, false);
        }
      };
      
      return dtInstanceAsientos;
    } catch (err) {
      console.error(`[${MOD}.page] Error inicializando DataTable asientos:`, err);
      const feedback = document.getElementById(`feedback-${MOD}-asientos-list`);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error inicializando tabla: ${err.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
      dtInstanceAsientos = null;
      return null;
    }
  }

  /**
   * Bind eventos de toolbar y acciones
   */
  function bindEvents() {
    // Cuentas
    const btnBuscarCuentas = document.getElementById(`btn-buscar-${MOD}-cuentas`);
    const btnRefrescarCuentas = document.getElementById(`btn-refrescar-${MOD}-cuentas`);
    const txtBuscarCuentas = document.getElementById(`txt-buscar-${MOD}-cuentas`);
    if (btnBuscarCuentas) {
      btnBuscarCuentas.addEventListener('click', () => {
        if (dtInstanceCuentas) {
          dtInstanceCuentas.ajax.reload(null, false);
        }
      });
    }
    if (btnRefrescarCuentas) {
      btnRefrescarCuentas.addEventListener('click', () => {
        if (dtInstanceCuentas) {
          dtInstanceCuentas.ajax.reload(null, false);
        }
      });
    }
    if (txtBuscarCuentas) {
      txtBuscarCuentas.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && dtInstanceCuentas) {
          dtInstanceCuentas.ajax.reload(null, false);
        }
      });
    }

    // Asientos
    const btnBuscarAsientos = document.getElementById(`btn-buscar-${MOD}-asientos`);
    const btnRefrescarAsientos = document.getElementById(`btn-refrescar-${MOD}-asientos`);
    const txtBuscarAsientos = document.getElementById(`txt-buscar-${MOD}-asientos`);

    if (btnBuscarAsientos) {
      btnBuscarAsientos.addEventListener('click', () => {
        if (dtInstanceAsientos) {
          dtInstanceAsientos.ajax.reload(null, false);
        }
      });
    }
    if (btnRefrescarAsientos) {
      btnRefrescarAsientos.addEventListener('click', () => {
        if (dtInstanceAsientos) {
          dtInstanceAsientos.ajax.reload(null, false);
        }
      });
    }
    if (txtBuscarAsientos) {
      txtBuscarAsientos.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && dtInstanceAsientos) {
          dtInstanceAsientos.ajax.reload(null, false);
        }
      });
    }

    // Delegación de eventos para acciones
    document.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('button[data-action]');
      if (!btn) return;
      
      const action = btn.dataset.action;
      const id = parseInt(btn.dataset.id);
      
      if (btn.closest(TABLE_CUENTAS_ID)) {
        if (action === 'view' || action === 'edit') {
          ev.preventDefault();
          const detailUrl = await getDetailUrl('cuentas', id);
          window.location.href = detailUrl;
        } else if (action === 'delete') {
          ev.preventDefault();
          if (confirm('¿Está seguro de eliminar esta cuenta contable?')) {
            try {
              let result;
              if (window.CRUD && typeof window.CRUD.delete === 'function') {
                result = await window.CRUD.delete(`${MOD}.cuentas`, id);
              } else {
                // Fallback a API_HELPERS
                const detailUrl = await getDetailUrl('cuentas', id);
                await window.API_HELPERS.safeFetchJson(detailUrl, {
                  method: 'DELETE'
                });
                result = { ok: true, status: 204 };
              }
              
              if (result.ok || result.status === 204 || result.status === 200) {
                if (dtInstanceCuentas) {
                  dtInstanceCuentas.ajax.reload(null, false);
                }
                const feedback = document.getElementById(`feedback-${MOD}-cuentas-list`);
                if (feedback) {
                  feedback.className = 'alert alert-success';
                  feedback.textContent = 'Cuenta contable eliminada correctamente';
                  feedback.classList.remove('d-none');
                  setTimeout(() => feedback.classList.add('d-none'), 3000);
                }
              } else {
                throw new Error(result.data?.detail || 'Error al eliminar cuenta');
              }
            } catch (error) {
              console.error(`[${MOD}.page] Error eliminando cuenta:`, error);
              const feedback = document.getElementById(`feedback-${MOD}-cuentas-list`);
              if (feedback) {
                feedback.className = 'alert alert-danger';
                feedback.textContent = error.message || 'Error al eliminar cuenta contable';
                feedback.classList.remove('d-none');
              }
            }
          }
        }
      } else if (btn.closest(TABLE_ASIENTOS_ID)) {
        if (action === 'view' || action === 'edit') {
          ev.preventDefault();
          const detailUrl = await getDetailUrl('asientos', id);
          window.location.href = detailUrl;
        } else if (action === 'delete') {
          ev.preventDefault();
          if (confirm('¿Está seguro de eliminar este asiento contable?')) {
            try {
              let result;
              if (window.CRUD && typeof window.CRUD.delete === 'function') {
                result = await window.CRUD.delete(`${MOD}.asientos`, id);
              } else {
                // Fallback a API_HELPERS
                const detailUrl = await getDetailUrl('asientos', id);
                await window.API_HELPERS.safeFetchJson(detailUrl, {
                  method: 'DELETE'
                });
                result = { ok: true, status: 204 };
              }
              
              if (result.ok || result.status === 204 || result.status === 200) {
                if (dtInstanceAsientos) {
                  dtInstanceAsientos.ajax.reload(null, false);
                }
                const feedback = document.getElementById(`feedback-${MOD}-asientos-list`);
                if (feedback) {
                  feedback.className = 'alert alert-success';
                  feedback.textContent = 'Asiento contable eliminado correctamente';
                  feedback.classList.remove('d-none');
                  setTimeout(() => feedback.classList.add('d-none'), 3000);
                }
              } else {
                throw new Error(result.data?.detail || 'Error al eliminar asiento');
              }
            } catch (error) {
              console.error(`[${MOD}.page] Error eliminando asiento:`, error);
              const feedback = document.getElementById(`feedback-${MOD}-asientos-list`);
              if (feedback) {
                feedback.className = 'alert alert-danger';
                feedback.textContent = error.message || 'Error al eliminar asiento contable';
                feedback.classList.remove('d-none');
              }
            }
          }
        }
      }
    });
  }

  /**
   * Inicializa el módulo cuando el DOM está listo
   * ⚠️ OLA 3: Usa DOMUtils.waitForVisible y initServerSide
   */
  document.addEventListener('DOMContentLoaded', () => {
    (async () => {
      console.debug(`[${MOD}.page] Inicializando módulo...`);
      
      try {
        // Verificar que jQuery y DataTables estén disponibles
        if (typeof $ === 'undefined' || !$.fn || !$.fn.DataTable) {
          throw new Error('jQuery/DataTables no están disponibles');
        }

        // Cargar rutas del módulo
        if (window.Routes && typeof window.Routes.get === 'function') {
          routes = await window.Routes.get(MOD);
          console.debug(`[${MOD}.page] Rutas cargadas:`, routes);
        }

        // Inicializar tabla de cuentas si existe
        if (document.getElementById('table-contabilidad-cuentas')) {
          await initDataTableCuentas();
        }

        // Inicializar tabla de asientos si existe
        if (document.getElementById('table-contabilidad-asientos')) {
          await initDataTableAsientos();
        }

        // Bind eventos
        bindEvents();
        
        console.debug(`[${MOD}.page] Módulo inicializado correctamente`);
      } catch (err) {
        console.error(`[${MOD}.page] Error inicializando módulo:`, err);
        // No fallar silenciosamente si las tablas no existen (pueden estar en otro tab)
        if (err.message && !err.message.includes('no encontrada')) {
          console.warn(`[${MOD}.page] Tablas no disponibles aún`);
        }
      }
    })().catch(err => {
      console.error(`[${MOD}.page] Error en inicialización:`, err);
    });
  });

  // Exportar para uso global (router)
  if (typeof window !== 'undefined') {
    window[`init${MOD.charAt(0).toUpperCase() + MOD.slice(1)}Page`] = async function() {
      await initDataTableCuentas();
      await initDataTableAsientos();
      bindEvents();
    };
  }
})();
