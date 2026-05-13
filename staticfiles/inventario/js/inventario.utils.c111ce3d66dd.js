/**
 * inventario.utils.js - Helpers centralizados para Inventario v2.61.8
 * Namespace: window.Sintel.Inventario.Utils
 *
 * Centraliza la carga de catalogos FK compartidos entre productos, servicios
 * y activos (categorias) con cache en memoria de 5 minutos para evitar
 * llamadas repetidas al endpoint en la misma sesion de trabajo.
 */
(function(w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Inventario = w.Sintel.Inventario || {};

  const MOD = '[Inventario.Utils]';
  const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos

  // Cache en memoria: { data: [], timestamp: number }
  let _categoriasCache = null;

  /**
   * Obtiene las categorias desde el API con cache de 5 minutos.
   * Usa inventario.api.js si esta disponible, sino fallback directo.
   * @returns {Promise<Array>} Lista de categorias
   */
  async function fetchCategorias() {
    // Retornar cache si es valido
    if (_categoriasCache && (Date.now() - _categoriasCache.timestamp < CACHE_TTL_MS)) {
      return _categoriasCache.data;
    }

    let categorias = [];
    try {
      const api = w.Sintel.Inventario.Api;
      let res;
      if (api && api.categorias && typeof api.categorias.list === 'function') {
        res = await api.categorias.list({ page_size: 200 });
      } else if (w.http && typeof w.http === 'function') {
        res = await w.http('GET', '/api/v1/inventario/categorias/?page_size=200');
      } else {
        console.warn(MOD, 'Ni inventario.api ni w.http disponibles');
        return [];
      }

      if (res && res.ok && res.data) {
        categorias = Array.isArray(res.data) ? res.data : (res.data.results || []);
      }
    } catch (err) {
      console.error(MOD, 'Error al cargar categorias:', err);
      return [];
    }

    _categoriasCache = { data: categorias, timestamp: Date.now() };
    return categorias;
  }

  /**
   * Carga categorias filtradas en un <select> del DOM.
   *
   * @param {string} selectSelector - Selector CSS del <select> (ej. '#producto-categoria')
   * @param {string|null} aplicacionFilter - Filtro de aplicacion: 'PRODUCTO', 'SERVICIO', 'ACTIVO' o null (todas)
   * @param {number|string|null} selectedId - ID de la categoria a preseleccionar
   * @param {string} placeholderText - Texto del primer <option> vacio
   */
  async function loadCategoriasSelect(selectSelector, aplicacionFilter, selectedId, placeholderText) {
    selectedId = selectedId || null;
    placeholderText = placeholderText || 'Seleccione...';

    const select = d.querySelector(selectSelector);
    if (!select) return;

    const categorias = await fetchCategorias();

    // Limpiar y poner placeholder
    select.innerHTML = '';
    const phOpt = d.createElement('option');
    phOpt.value = '';
    phOpt.textContent = placeholderText;
    select.appendChild(phOpt);

    if (categorias.length === 0) {
      const empty = d.createElement('option');
      empty.value = '';
      empty.textContent = 'No hay categorias disponibles';
      empty.disabled = true;
      select.appendChild(empty);
      return;
    }

    // Filtrar por aplicacion si se especifica
    const filtered = aplicacionFilter
      ? categorias.filter(function(cat) {
          return cat.aplicacion === aplicacionFilter || cat.aplicacion === 'TODO';
        })
      : categorias;

    var selId = selectedId ? parseInt(selectedId, 10) : null;

    filtered.forEach(function(cat) {
      var option = d.createElement('option');
      option.value = cat.id;
      option.textContent = cat.nombre;
      if (selId && cat.id === selId) {
        option.selected = true;
      }
      select.appendChild(option);
    });
  }

  /**
   * Invalida la cache de categorias. Llamar despues de crear/editar/eliminar
   * una categoria para que el proximo loadCategoriasSelect() haga fetch fresco.
   */
  function invalidateCache() {
    _categoriasCache = null;
  }

  /**
   * Configura la búsqueda autocompletada de cuentas contables.
   * ⚠️ v3.5: Integración con Contabilidad
   * 
   * @param {Object} config - Configuración { inputSelector, resultsSelector, uuidSelector }
   */
  function setupCuentaAutocomplete(config) {
    const input = d.querySelector(config.inputSelector);
    const results = d.querySelector(config.resultsSelector);
    const uuidInput = d.querySelector(config.uuidSelector);
    
    if (!input || !results || !uuidInput) return;

    let timeout = null;

    input.addEventListener('input', function() {
      const query = this.value.trim();
      clearTimeout(timeout);

      if (query.length < 2) {
        results.classList.add('d-none');
        results.innerHTML = '';
        return;
      }

      timeout = setTimeout(async () => {
        try {
          const res = await w.Sintel.Inventario.API.searchCuentas(query);
          if (res.ok && res.data) {
            const data = Array.isArray(res.data) ? res.data : (res.data.results || []);
            renderResultados(data);
          }
        } catch (err) {
          console.error(MOD, 'Error buscando cuentas:', err);
        }
      }, 300);
    });

    function renderResultados(cuentas) {
      if (cuentas.length === 0) {
        results.innerHTML = '<div class="list-group-item text-muted">No se encontraron cuentas</div>';
        results.classList.remove('d-none');
        return;
      }

      results.innerHTML = cuentas.map(cta => `
        <button type="button" class="list-group-item list-group-item-action py-2" 
                data-uuid="${cta.uuid}" data-label="${cta.codigo} - ${cta.nombre}">
          <div class="d-flex w-100 justify-content-between">
            <h6 class="mb-1 fw-bold">${cta.codigo}</h6>
          </div>
          <small class="text-muted">${cta.nombre}</small>
        </button>
      `).join('');
      
      results.classList.remove('d-none');

      // Evento de clic para seleccion
      results.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', function() {
          input.value = this.dataset.label;
          uuidInput.value = this.dataset.uuid;
          results.classList.add('d-none');
          results.innerHTML = '';
          
          // Disparar evento de cambio para que otros listeners lo capten
          input.dispatchEvent(new Event('change'));
        });
      });
    }

    // Cerrar resultados al hacer clic fuera
    d.addEventListener('click', function(e) {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        results.classList.add('d-none');
      }
    });
  }

  // Exponer en namespace
  w.Sintel.Inventario.Utils = {
    loadCategoriasSelect: loadCategoriasSelect,
    setupCuentaAutocomplete: setupCuentaAutocomplete,
    invalidateCache: invalidateCache
  };


})(window, document);
