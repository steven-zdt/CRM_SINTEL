/**
 * asientos.page.js - Módulo Contabilidad Asientos v2.37
 * 
 * ⚠️ DEPRECADO v2.61: DataTables fue migrado completamente a Tabulator.
 * Este archivo está DEPRECADO y NO debe usarse en producción.
 * 
 * ⚠️ v2.61: Usar asientos_main.js en su lugar (Tabulator Factory v2.40)
 * 
 * ⚠️ v2.61: Cambios en validación de cuadratura:
 * - Los asientos en estado BORRADOR pueden guardarse aunque no cuadren
 * - La validación estricta de partida doble solo aplica para APROBADO/CERRADO
 * - Tolerancia de 0.01 para errores de redondeo
 * - Los totales se calculan desde la BD después de crear los movimientos
 * 
 * ⚠️ v2.37: Alineado con arquitectura SINTEL API-First
 * - Fetch resiliente (índice → colección)
 * - DataTables client-side con datos mínimos (DEPRECADO)
 * - CSRF token en headers para mutaciones
 * - Mapeo exacto a AsientoContableListSerializer
 * - Manejo 401 inteligente
 * - Modales independientes (Ver, Editar, Crear, Eliminar)
 * - CRUD completo
 * - Nota: Los movimientos se muestran en el detalle pero se gestionan por separado
 */

(function () {
  'use strict';

  const MOD = 'asientos';
  const TABLE_ID = '#table-contabilidad-asientos';
  const ROUTES_MODULE = 'contabilidad.asientos';  // ⚠️ v2.37: Usar Routes para descubrir URLs
  
  // Estado del módulo
  let state = {
    initialized: false,
    listenersAttached: false,
    table: null,
    urls: { collection: null }
  };
  
  /**
   * Descubrir URL de colección usando Routes
   * ⚠️ v2.37: Usar Routes helper centralizado
   */
  async function discoverCollectionUrl() {
    if (state.urls.collection) {
      return state.urls.collection;
    }
    
    console.info(`[${MOD}.page] Descubriendo URL de colección usando Routes:`, ROUTES_MODULE);
    
    try {
      // Usar Routes para obtener la URL de colección
      if (window.Routes && typeof window.Routes.collectionUrl === 'function') {
        const collectionUrl = await window.Routes.collectionUrl(ROUTES_MODULE);
        if (collectionUrl) {
          state.urls.collection = collectionUrl;
          console.info(`[${MOD}.page] state.urls.collection descubierta desde Routes:`, state.urls.collection);
          return state.urls.collection;
        }
      }
      
      // Fallback: usar ruta estándar
      const fallbackUrl = '/api/v1/contabilidad/asientos-contables/';
      state.urls.collection = window.API_HELPERS?.withTrailingSlash(fallbackUrl) || fallbackUrl;
      console.warn(`[${MOD}.page] Routes no disponible, usando fallback:`, state.urls.collection);
      return state.urls.collection;
    } catch (err) {
      console.error(`[${MOD}.page] Error descubriendo URL de colección:`, err);
      // Fallback: usar ruta estándar
      const fallbackUrl = '/api/v1/contabilidad/asientos-contables/';
      state.urls.collection = window.API_HELPERS?.withTrailingSlash(fallbackUrl) || fallbackUrl;
      return state.urls.collection;
    }
  }

  /**
   * Construir URL de detalle para un asiento
   * @param {string|number} id - ID del asiento
   * @returns {string} URL de detalle
   */
  async function asientoDetailUrl(id) {
    if (!state.urls.collection) {
      await discoverCollectionUrl();
    }
    if (!state.urls.collection) {
      console.warn(`[${MOD}.page] state.urls.collection no descubierta, usando fallback`);
      const fallbackUrl = '/api/v1/contabilidad/asientos-contables/';
      return window.API_HELPERS?.buildDetailUrl(fallbackUrl, id) || `${fallbackUrl}${id}/`;
    }
    const url = window.API_HELPERS?.buildDetailUrl(state.urls.collection, id) || `${state.urls.collection}${id}/`;
    console.info(`[${MOD}.page] URL de detalle construida:`, url);
    return url;
  }

  /**
   * Fetcher resiliente (índice → colección)
   * Maneja tanto índice HATEOAS como colección directa
   */
  async function fetchAsientoList() {
    // Descubrir URL de colección si no está descubierta
    await discoverCollectionUrl();
    
    const collectionUrl = state.urls.collection;
    if (!collectionUrl) {
      throw new Error('URL de colección no disponible');
    }
    
    console.info(`[${MOD}.page] Fetch colección:`, collectionUrl);
    
    try {
      // ⚠️ v2.37: Usar API_HELPERS.safeFetchJson en lugar de fetch directo
      const colPayload = await window.API_HELPERS.safeFetchJson(collectionUrl, {
        method: 'GET'
      });
      const rows = Array.isArray(colPayload?.results) ? colPayload.results
                 : (Array.isArray(colPayload) ? colPayload : []);
      console.info(`[${MOD}.page] rows.length:`, rows.length);
      return rows;
    } catch (error) {
      console.error(`[${MOD}.page] Error en fetchAsientoList:`, error);
      throw error;
    }
  }

  /**
   * Obtener detalle de asiento
   * ⚠️ v2.37: API-First - usa retrieve con ID
   */
  async function fetchAsientoDetail(id) {
    if (!id) {
      throw new Error('ID de asiento requerido');
    }
    
    console.info(`[${MOD}.page] Fetch detalle ID:`, id);
    
    try {
      const detailUrl = asientoDetailUrl(id);
      console.info(`[${MOD}.page] Usando retrieve con ID:`, detailUrl);
      
      const response = await fetch(detailUrl, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
      });
      
      if (response.status === 401) {
        throw new Error('Sesión expirada');
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`[${MOD}.page] Error en fetchAsientoDetail:`, error);
      throw error;
    }
  }

  /**
   * Helper para leer JSON de respuesta de forma segura
   */
  async function safeReadJson(response) {
    try {
      return await response.json();
    } catch (e) {
      return null;
    }
  }

  /**
   * Helper para mostrar feedback
   */
  function showFeedback(selector, message, type = 'info') {
    const element = document.querySelector(selector);
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

  /**
   * Formatear número como moneda
   */
  function formatCurrency(value) {
    if (!value && value !== 0) return '-';
    const formatter = new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return formatter.format(value);
  }

  /**
   * Limpiar modales (inputs y feedback)
   */
  function limpiarModales() {
    // Limpiar modal Ver
    ['numero', 'fecha', 'descripcion', 'estado', 'total_debe', 'total_haber'].forEach(field => {
      const input = document.getElementById(`asiento-view-${field}`);
      if (input) input.value = '';
    });
    const movimientosTbody = document.getElementById('asiento-view-movimientos-tbody');
    if (movimientosTbody) movimientosTbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Cargando movimientos...</td></tr>';
    const viewFeedback = document.getElementById('asiento-view-feedback');
    if (viewFeedback) {
      viewFeedback.classList.add('d-none');
      viewFeedback.textContent = '';
    }

    // Limpiar modal Editar
    ['numero', 'fecha', 'descripcion', 'estado', 'total_debe', 'total_haber'].forEach(field => {
      const input = document.getElementById(`asiento-edit-${field}`);
      if (input) {
        if (input.tagName === 'SELECT') {
          input.selectedIndex = 0;
        } else {
          input.value = '';
        }
      }
    });
    const editModal = document.getElementById('modal-editar-asiento');
    if (editModal) {
      delete editModal.dataset.id;
    }
    const editFeedback = document.getElementById('asiento-edit-feedback');
    if (editFeedback) {
      editFeedback.classList.add('d-none');
      editFeedback.textContent = '';
    }

    // Limpiar modal Crear
    ['numero', 'fecha', 'descripcion', 'estado'].forEach(field => {
      const input = document.getElementById(`asiento-create-${field}`);
      if (input) {
        if (input.tagName === 'SELECT') {
          input.selectedIndex = 0;
        } else {
          input.value = '';
        }
      }
    });
    const createFeedback = document.getElementById('asiento-create-feedback');
    if (createFeedback) {
      createFeedback.classList.add('d-none');
      createFeedback.textContent = '';
    }

    // Limpiar modal Eliminar
    const deleteInfo = document.getElementById('asiento-delete-info');
    if (deleteInfo) deleteInfo.textContent = '';
    const deleteModal = document.getElementById('modal-eliminar-asiento');
    if (deleteModal) {
      delete deleteModal.dataset.id;
    }
    const deleteFeedback = document.getElementById('asiento-delete-feedback');
    if (deleteFeedback) {
      deleteFeedback.classList.add('d-none');
      deleteFeedback.textContent = '';
    }
  }

  /**
   * Renderizar movimientos en tabla
   */
  function renderMovimientos(movimientos, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    
    if (!movimientos || movimientos.length === 0) {
      // ⚠️ NORMATIVA: Ajustar colspan si se agregan columnas de terceros
      const hasTerceros = false; // Se detectará dinámicamente si hay datos
      const colspan = hasTerceros ? 6 : 4;
      tbody.innerHTML = `<tr><td colspan="${colspan}" class="text-center text-muted">No hay movimientos registrados</td></tr>`;
      return;
    }
    
    // ⚠️ NORMATIVA: Incluir campos de terceros si están disponibles
    tbody.innerHTML = movimientos.map(mov => {
      const cuentaNombre = mov.cuenta_nombre || mov.cuenta?.nombre || `ID: ${mov.cuenta || '-'}`;
      const debe = formatCurrency(mov.debe || 0);
      const haber = formatCurrency(mov.haber || 0);
      // ⚠️ NORMATIVA: Campos de terceros
      const terceroNit = mov.tercero_nit || '---';
      const terceroRazonSocial = mov.tercero_razon_social || '---';
      
      // Si hay campos de terceros, mostrarlos; si no, mantener formato original
      if (mov.tercero_nit || mov.tercero_razon_social) {
        return `
          <tr>
            <td>${cuentaNombre}</td>
            <td>${mov.descripcion || '-'}</td>
            <td class="text-end">${debe}</td>
            <td class="text-end">${haber}</td>
            <td><small class="text-muted">${terceroNit}</small></td>
            <td><small>${terceroRazonSocial}</small></td>
          </tr>
        `;
      } else {
        return `
          <tr>
            <td>${cuentaNombre}</td>
            <td>${mov.descripcion || '-'}</td>
            <td class="text-end">${debe}</td>
            <td class="text-end">${haber}</td>
          </tr>
        `;
      }
    }).join('');
  }

  /**
   * Handle Ver Asiento
   */
  async function handleVerAsiento(id) {
    if (!id) {
      showFeedback('#asiento-view-feedback', 'Error: ID de asiento requerido', 'error');
      return;
    }
    
    try {
      const data = await fetchAsientoDetail(id);
      
      // Llenar inputs del modal (readonly)
      const setValue = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value || '';
      };
      
      setValue('asiento-view-numero', data.numero);
      setValue('asiento-view-fecha', data.fecha);
      setValue('asiento-view-descripcion', data.descripcion);
      setValue('asiento-view-estado', data.estado);
      setValue('asiento-view-total_debe', formatCurrency(data.total_debe || 0));
      setValue('asiento-view-total_haber', formatCurrency(data.total_haber || 0));
      // ⚠️ NORMATIVA: Campos de comprobante para trazabilidad
      setValue('asiento-view-tipo_comprobante', data.tipo_comprobante || '---');
      setValue('asiento-view-numero_comprobante', data.numero_comprobante || '---');
      
      // Renderizar movimientos
      if (data.movimientos && Array.isArray(data.movimientos)) {
        renderMovimientos(data.movimientos, 'asiento-view-movimientos-tbody');
      } else {
        const tbody = document.getElementById('asiento-view-movimientos-tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No hay movimientos registrados</td></tr>';
      }
      
      // Abrir modal
      const modalEl = document.getElementById('modal-ver-asiento');
      if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
      } else {
        console.error(`[${MOD}.page] Modal ver-asiento no encontrado`);
      }
    } catch (error) {
      console.error(`[${MOD}.page] Error en handleVerAsiento:`, error);
      showFeedback('#asiento-view-feedback', `Error cargando asiento: ${error.message}`, 'error');
    }
  }

  /**
   * Handle Editar Asiento
   */
  async function handleEditarAsiento(id) {
    if (!id) {
      showFeedback('#asiento-edit-feedback', 'Error: ID de asiento requerido', 'error');
      return;
    }
    
    try {
      const data = await fetchAsientoDetail(id);
      
      // Llenar inputs del modal editar
      const setValue = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value || '';
      };
      
      setValue('asiento-edit-numero', data.numero);
      setValue('asiento-edit-fecha', data.fecha);
      setValue('asiento-edit-descripcion', data.descripcion);
      setValue('asiento-edit-estado', data.estado);
      setValue('asiento-edit-total_debe', data.total_debe || 0);
      setValue('asiento-edit-total_haber', data.total_haber || 0);
      
      // Set dataset.id en el modal
      const modal = document.getElementById('modal-editar-asiento');
      if (modal) {
        if (data.id) {
          modal.dataset.id = data.id;
          console.info(`[${MOD}.page] ID guardado en modal:`, data.id);
        }
      }
      
      // Abrir modal
      if (modal) {
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        bsModal.show();
      } else {
        console.error(`[${MOD}.page] Modal editar-asiento no encontrado`);
      }
    } catch (error) {
      console.error(`[${MOD}.page] Error en handleEditarAsiento:`, error);
      showFeedback('#asiento-edit-feedback', `Error cargando asiento: ${error.message}`, 'error');
    }
  }

  /**
   * Handle Guardar Asiento (PATCH)
   * ⚠️ v2.37: API-First - usa URL descubierta
   */
  async function handleGuardarAsiento() {
    const modal = document.getElementById('modal-editar-asiento');
    if (!modal) {
      console.error(`[${MOD}.page] Modal editar no encontrado`);
      return;
    }

    const id = modal.dataset.id;
    if (!id) {
      showFeedback('#asiento-edit-feedback', 'Error: ID de asiento no encontrado', 'error');
      return;
    }

    // Recopilar datos del formulario
    const getValue = (id) => {
      const el = document.getElementById(id);
      return el ? el.value.trim() : '';
    };
    
    const payload = {
      numero: getValue('asiento-edit-numero') || null,
      fecha: getValue('asiento-edit-fecha'),
      descripcion: getValue('asiento-edit-descripcion'),
      estado: getValue('asiento-edit-estado'),
    };

    try {
      // Construir URL de PATCH
      const patchUrl = asientoDetailUrl(id);
      console.info(`[${MOD}.page] PATCH URL:`, patchUrl);
      
      const response = await fetch(patchUrl, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF,
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });

      // Manejo estandarizado de respuestas
      if (response.status === 200 || response.status === 201) {
        const data = await response.json().catch(() => ({}));
        console.info(`[${MOD}.page] Asiento actualizado:`, data);
        
        // Mostrar feedback de éxito
        showFeedback('#asiento-edit-feedback', 'Asiento actualizado correctamente', 'success');
        
        // Refrescar DataTable
        if (dtInstance) {
          dtInstance.clear();
          const rows = await fetchAsientoList();
          dtInstance.rows.add(rows).draw();
        } else {
          await initDataTableAsiento();
        }
        
        // Cerrar modal después de un breve delay
        setTimeout(() => {
          const bsModal = bootstrap.Modal.getInstance(modal);
          if (bsModal) {
            bsModal.hide();
          } else {
            const newModal = bootstrap.Modal.getOrCreateInstance(modal);
            newModal.hide();
          }
          limpiarModales();
        }, 1000);
        return;
      }
      
      // Manejo estandarizado de errores (400/409/422)
      if (response.status === 401) {
        showFeedback('#asiento-edit-feedback', 'Sesión expirada. Por favor, recarga la página.', 'error');
        return;
      }
      
      // Leer respuesta de error
      const err = await safeReadJson(response);
      const msg = (err && (err.message || err.detail)) || `Error ${response.status}: ${response.statusText}`;
      
      // Mostrar feedback de error sin cerrar el modal
      showFeedback('#asiento-edit-feedback', msg, 'error');
      console.warn(`[${MOD}.page] PATCH error:`, response.status, err);
      
    } catch (error) {
      console.error(`[${MOD}.page] Error en handleGuardarAsiento:`, error);
      showFeedback('#asiento-edit-feedback', error.message || 'Error inesperado', 'error');
    }
  }

  /**
   * Handle Crear Asiento (POST)
   * ⚠️ v2.37: API-First - usa URL descubierta desde el índice
   */
  async function handleCrearAsiento() {
    // Asegurar que la URL de colección esté descubierta
    await discoverCollectionUrl();
    
    // Recopilar datos del formulario
    const getValue = (id) => {
      const el = document.getElementById(id);
      return el ? el.value.trim() : '';
    };
    
    const payload = {
      numero: getValue('asiento-create-numero') || null,
      fecha: getValue('asiento-create-fecha'),
      descripcion: getValue('asiento-create-descripcion'),
      estado: getValue('asiento-create-estado') || 'BORRADOR',
    };

    try {
      // Usar URL de colección descubierta
      if (!state.urls.collection) {
        await discoverCollectionUrl();
      }
      const createUrl = state.urls.collection;
      if (!createUrl) {
        throw new Error('URL de colección no disponible');
      }
      console.info(`[${MOD}.page] POST URL:`, createUrl);
      
      const response = await fetch(createUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF,
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        throw new Error('Sesión expirada');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      const data = await response.json();
      console.info(`[${MOD}.page] Asiento creado:`, data);

      // Mostrar feedback
      showFeedback('#asiento-create-feedback', 'Asiento creado correctamente', 'success');

      // Refrescar DataTable
      if (dtInstance) {
        dtInstance.clear();
        const rows = await fetchAsientoList();
        dtInstance.rows.add(rows).draw();
      } else {
        await initDataTableAsiento();
      }

      // Cerrar modal después de un breve delay
      setTimeout(() => {
        const modal = document.getElementById('modal-crear-asiento');
        if (modal) {
          const bsModal = bootstrap.Modal.getInstance(modal);
          if (bsModal) {
            bsModal.hide();
          } else {
            const newModal = bootstrap.Modal.getOrCreateInstance(modal);
            newModal.hide();
          }
        }
        limpiarModales();
      }, 1000);
    } catch (err) {
      console.error(`[${MOD}.page] Error en handleCrearAsiento:`, err);
      
      // Manejo de errores específicos
      if (err.status === 422 && err.fields) {
        let msg = err.message || 'Datos inválidos (422). Verifica los campos.';
        showFeedback('#asiento-create-feedback', msg, 'error');
      } else if (err.status === 404) {
        showFeedback('#asiento-create-feedback', 'Endpoint no encontrado. Verifica la configuración del backend.', 'error');
      } else if (err.status === 401) {
        showFeedback('#asiento-create-feedback', 'Sesión expirada. Por favor, recarga la página.', 'error');
      } else {
        const errorMsg = err.message || 'Error inesperado al crear asiento';
        showFeedback('#asiento-create-feedback', errorMsg, 'error');
        if (DEBUG) {
          console.error('[asientos.page] Detalles del error:', {
            status: err.status,
            message: err.message,
            body: err.body,
            stack: err.stack
          });
        }
      }
    }
  }

  /**
   * Handle Eliminar Asiento (DELETE)
   */
  async function handleEliminarAsiento(id) {
    if (!id) {
      showFeedback('#asiento-delete-feedback', 'Error: ID de asiento requerido', 'error');
      return;
    }

    try {
      const detailUrl = asientoDetailUrl(id);
      console.info(`[${MOD}.page] DELETE URL:`, detailUrl);
      
      const response = await fetch(detailUrl, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': CSRF,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      });

      if (response.status === 204 || response.status === 200) {
        // Mostrar feedback de éxito
        showFeedback('#asiento-delete-feedback', 'Asiento eliminado correctamente', 'success');
        
        // Refrescar DataTable
        if (dtInstance) {
          dtInstance.clear();
          const rows = await fetchAsientoList();
          dtInstance.rows.add(rows).draw();
        } else {
          await initDataTableAsiento();
        }
        
        // Cerrar modal después de un breve delay
        setTimeout(() => {
          const modal = document.getElementById('modal-eliminar-asiento');
          if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
              bsModal.hide();
            } else {
              const newModal = bootstrap.Modal.getOrCreateInstance(modal);
              newModal.hide();
            }
          }
          limpiarModales();
        }, 1000);
        return;
      }
      
      // Manejo de errores
      if (response.status === 401) {
        showFeedback('#asiento-delete-feedback', 'Sesión expirada. Por favor, recarga la página.', 'error');
        return;
      }
      
      if (response.status === 409) {
        const err = await safeReadJson(response);
        const msg = (err && (err.message || err.detail)) || 'No se puede eliminar el asiento debido a relaciones existentes.';
        showFeedback('#asiento-delete-feedback', msg, 'error');
        return;
      }
      
      // Otros errores
      const err = await safeReadJson(response);
      const msg = (err && (err.message || err.detail)) || `Error ${response.status}: ${response.statusText}`;
      showFeedback('#asiento-delete-feedback', msg, 'error');
      console.warn(`[${MOD}.page] DELETE error:`, response.status, err);
      
    } catch (error) {
      console.error(`[${MOD}.page] Error en handleEliminarAsiento:`, error);
      showFeedback('#asiento-delete-feedback', error.message || 'Error inesperado', 'error');
    }
  }

  /**
   * Columnas alineadas con AsientoContableListSerializer
   */
  const columns = [
    { 
      data: 'numero',
      title: 'Número',
      render: function (data, type, row) {
        return data || '-';
      }
    },
    { 
      data: 'fecha',
      title: 'Fecha',
      render: function (data, type, row) {
        if (!data) return '-';
        const date = new Date(data);
        return date.toLocaleDateString('es-CO');
      }
    },
    { 
      data: 'descripcion',
      title: 'Descripción',
      render: function (data, type, row) {
        if (!data) return '-';
        // Truncar descripción larga
        return data.length > 50 ? data.substring(0, 50) + '...' : data;
      }
    },
    { 
      data: 'estado',
      title: 'Estado',
      render: function (data, type, row) {
        if (!data) return '-';
        const badges = { 
          'BORRADOR': 'secondary', 
          'APROBADO': 'success', 
          'CERRADO': 'dark'
        };
        const badge = badges[data] || 'secondary';
        return `<span class="badge bg-${badge}">${data}</span>`;
      }
    },
    { 
      data: 'total_debe',
      title: 'Débito',
      className: 'text-end',
      render: function (data, type, row) {
        return formatCurrency(data || 0);
      }
    },
    { 
      data: 'total_haber',
      title: 'Crédito',
      className: 'text-end',
      render: function (data, type, row) {
        return formatCurrency(data || 0);
      }
    },
    {
      data: null,
      title: 'Acciones',
      orderable: false,
      searchable: false,
      className: 'text-end',
      render: function (data, type, row) {
        if (!row || !row.id) return '-';
        const asientoId = row.id || '';
        return `
          <div class="btn-group">
            <button class="btn btn-sm btn-secondary btn-ver" data-id="${asientoId}">Ver</button>
            <button class="btn btn-sm btn-primary btn-editar" data-id="${asientoId}">Editar</button>
            <button class="btn btn-sm btn-danger btn-eliminar" data-id="${asientoId}">Eliminar</button>
          </div>
        `;
      }
    }
  ];

  let dtInstance = null;

  /**
   * Inicialización segura de la DataTable
   */
  async function initDataTableAsiento() {
    const table = $(TABLE_ID);
    
    // Verificar existencia del elemento
    if (table.length === 0) {
      console.warn(`[${MOD}.page] Tabla ${TABLE_ID} no está en el DOM todavía`);
      return null;
    }

    // Verificar que la tabla sea visible
    if (!table.is(':visible')) {
      console.info(`[${MOD}.page] Tabla ${TABLE_ID} está oculta, esperando a que sea visible...`);
      return null;
    }

    // Verificar existencia de <thead><tr><th>
    const thCount = table.find('thead tr th').length;
    if (!thCount) {
      console.error(`[${MOD}.page] El <thead> o <th> faltan. DataTables requiere encabezados.`);
      return null;
    }

    // Validar header vs columnas
    if (thCount !== columns.length) {
      console.warn(`[${MOD}.page] Mismatch entre <th> (${thCount}) y columnas definidas (${columns.length}).`);
    }

    // Destruir instancia previa si existe
    if ($.fn.DataTable.isDataTable(TABLE_ID)) {
      console.warn(`[${MOD}.page] DataTable existente, destruyendo antes de re-crear...`);
      try {
        table.DataTable().clear().destroy();
        table.find('tbody').empty();
        dtInstance = null;
      } catch (e) {
        console.warn(`[${MOD}.page] Error al destruir DataTable existente:`, e);
        table.removeData();
        dtInstance = null;
      }
    }

    // Si hay una inicialización en progreso, no hacer nada
    if (table.data('dt-initializing')) {
      console.info(`[${MOD}.page] Inicialización ya en progreso, esperando...`);
      return dtInstance;
    }

    // Marcar que estamos inicializando
    table.data('dt-initializing', true);

    try {
      // Cargar datos desde API
      const rows = await fetchAsientoList();
      
      // Manejar feedback según datos
      const feedback = document.getElementById('feedback-contabilidad-asientos-list');
      if (rows.length === 0) {
        if (feedback) {
          feedback.className = 'alert alert-info';
          feedback.textContent = 'No hay asientos contables registrados. Use el botón "Crear Asiento" para agregar uno nuevo.';
          feedback.classList.remove('d-none');
        }
      } else {
        if (feedback) {
          feedback.classList.add('d-none');
        }
      }

      // Inicializar DataTable
      dtInstance = table.DataTable({
        data: rows,
        columns: columns,
        paging: true,
        searching: true,
        info: true,
        deferRender: true,
        autoWidth: false,
        responsive: true,
        language: {
          emptyTable: 'Ningún dato disponible en esta tabla',
          url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/es-ES.json'
        },
        order: [[1, 'desc']], // Ordenar por fecha descendente
        drawCallback: function(settings) {
          const recordCount = settings.fnRecordsDisplay();
          console.info(`[${MOD}.page] DataTable dibujado con ${recordCount} registros`);
        }
      });

      console.info(`[${MOD}.page] DataTable inicializado. Filas:`, rows.length);
    } catch (error) {
      console.error(`[${MOD}.page] Error cargando asientos:`, error);
      const feedback = document.getElementById('feedback-contabilidad-asientos-list');
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error cargando asientos: ${error.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
      dtInstance = null;
    } finally {
      // Limpiar flag de inicialización
      table.removeData('dt-initializing');
    }

    return dtInstance;
  }

  /**
   * Inicializar módulo Asientos
   * ⚠️ v2.37: Descubre URL de colección antes de inicializar
   * ⚠️ v2.61: DEPRECADO - Este módulo no debe inicializarse automáticamente
   */
  async function initAsientoModule() {
    // ⚠️ v2.61: Prevenir inicialización automática (archivo deprecado)
    console.warn(`[${MOD}.page] ⚠️ DEPRECADO: Este archivo está deprecado. Use asientos_main.js en su lugar.`);
    console.warn(`[${MOD}.page] Inicialización bloqueada para evitar conflictos con Tabulator.`);
    return;
    
    console.info(`[${MOD}.page] Inicializando módulo Asientos Contables...`);
    
    // Descubrir URL de colección antes de inicializar DataTable
    await discoverCollectionUrl();
    
    // Inicializar DataTable
    await initDataTableAsiento();
    
    // Asociar eventos
    // Botón Ver
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-ver');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id || null;
        if (id) handleVerAsiento(id);
      }
    });

    // Botón Editar
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-editar');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id || null;
        if (id) handleEditarAsiento(id);
      }
    });

    // Botón Eliminar
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-eliminar');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id || null;
        if (id) {
          // Obtener datos del asiento para mostrar en el modal de confirmación
          fetchAsientoDetail(id).then(data => {
            const deleteInfo = document.getElementById('asiento-delete-info');
            if (deleteInfo) {
              deleteInfo.textContent = `${data.numero || 'Asiento'} - ${data.descripcion || ''}`;
            }
            const deleteModal = document.getElementById('modal-eliminar-asiento');
            if (deleteModal) {
              deleteModal.dataset.id = id;
              const bsModal = bootstrap.Modal.getOrCreateInstance(deleteModal);
              bsModal.show();
            }
          }).catch(error => {
            console.error(`[${MOD}.page] Error cargando datos para eliminar:`, error);
            showFeedback('#asiento-delete-feedback', `Error: ${error.message}`, 'error');
          });
        }
      }
    });

    // Botón Crear (toolbar)
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-crear-asiento');
      if (btn) {
        ev.preventDefault();
        ev.stopPropagation();
        console.info(`[${MOD}.page] Botón Crear Asiento clickeado`);
        limpiarModales();
        // Establecer fecha por defecto (hoy)
        const fechaInput = document.getElementById('asiento-create-fecha');
        if (fechaInput && !fechaInput.value) {
          const today = new Date().toISOString().split('T')[0];
          fechaInput.value = today;
        }
        const modalEl = document.getElementById('modal-crear-asiento');
        if (modalEl) {
          const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.show();
        } else {
          console.error(`[${MOD}.page] Modal crear-asiento no encontrado`);
        }
      }
    });

    // Botón Guardar (modal editar)
    const btnGuardar = document.getElementById('btn-guardar-asiento');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', () => {
        handleGuardarAsiento();
      });
    }

    // Botón Crear (modal crear)
    const btnCrearModal = document.getElementById('btn-crear-asiento');
    if (btnCrearModal) {
      btnCrearModal.addEventListener('click', () => {
        handleCrearAsiento();
      });
    }

    // Botón Confirmar Eliminar
    const btnConfirmarEliminar = document.getElementById('btn-confirmar-eliminar-asiento');
    if (btnConfirmarEliminar) {
      btnConfirmarEliminar.addEventListener('click', () => {
        const deleteModal = document.getElementById('modal-eliminar-asiento');
        if (deleteModal && deleteModal.dataset.id) {
          handleEliminarAsiento(deleteModal.dataset.id);
        }
      });
    }

    // Botón Refrescar
    const btnRefrescar = document.getElementById('btn-refrescar-contabilidad-asientos');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', async () => {
        if (dtInstance) {
          dtInstance.clear();
          const rows = await fetchAsientoList();
          dtInstance.rows.add(rows).draw();
        } else {
          await initDataTableAsiento();
        }
      });
    }

    // Limpiar modales al cerrar
    ['modal-ver-asiento', 'modal-editar-asiento', 'modal-crear-asiento', 'modal-eliminar-asiento'].forEach(modalId => {
      const modalEl = document.getElementById(modalId);
      if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
          limpiarModales();
        });
      }
    });
  }

  // Inicializar cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initAsientoModule().catch(error => {
        console.error(`[${MOD}.page] Error inicializando módulo:`, error);
      });
    });
  } else {
    initAsientoModule().catch(error => {
      console.error(`[${MOD}.page] Error inicializando módulo:`, error);
    });
  }

  // Exportar para uso externo
  window.asientosDT = {
    init: initAsientoModule,
    reload: async () => {
      if (dtInstance) {
        dtInstance.clear();
        const rows = await fetchAsientoList();
        dtInstance.rows.add(rows).draw();
      } else {
        await initDataTableAsiento();
      }
    }
  };
})();
