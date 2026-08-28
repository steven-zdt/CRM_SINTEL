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
      const api = w.Sintel.Inventario.API;
      let res;
      if (api && api.categorias && typeof api.categorias.list === 'function') {
        res = await api.categorias.list({ page_size: 200 });
      } else if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
        res = await w.Sintel.Core.Http.request('GET', '/api/v1/inventario/categorias/?page_size=200');
      } else {
        console.warn(MOD, 'Ni inventario.api ni Sintel.Core.Http disponibles');
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

    // Normalizar selectedId como string para comparacion UUID-safe
    var selId = selectedId ? String(selectedId) : null;

    filtered.forEach(function(cat) {
      var option = d.createElement('option');
      option.value = cat.id;  // cat.id es UUID (del serializer)
      option.textContent = cat.nombre;
      if (selId && String(cat.id) === selId) {
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

  // Exponer en namespace
  w.Sintel.Inventario.Utils = {
    loadCategoriasSelect: loadCategoriasSelect,
    invalidateCache: invalidateCache
  };


})(window, document);
