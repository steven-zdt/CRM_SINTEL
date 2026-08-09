/**
 * compras.utils.js - Helpers centralizados para Compras
 * Namespace: window.Sintel.Compras.Utils
 *
 * Centraliza la carga de catalogos FK compartidos (proveedores, proyectos)
 * con cache en memoria de 5 minutos para evitar llamadas repetidas al endpoint
 * en la misma sesion de trabajo.
 */
(function(w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Compras = w.Sintel.Compras || {};

  var MOD = '[Compras.Utils]';
  var CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos

  // Caches en memoria: { data: [], timestamp: number }
  var _proveedoresCache = null;
  var _proyectosCache = null;

  /**
   * Obtiene proveedores desde el API con cache de 5 minutos.
   * @returns {Promise<Array>} Lista de proveedores
   */
  async function fetchProveedores() {
    if (_proveedoresCache && (Date.now() - _proveedoresCache.timestamp < CACHE_TTL_MS)) {
      return _proveedoresCache.data;
    }

    var proveedores = [];
    try {
      var url = w.Sintel.Compras.API.proveedores.list;
      var headers = await window.Sintel.Compras.getHeaders();
      var res = await fetch(url, { headers: headers });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var json = await res.json();
      proveedores = json.results || json;
      if (!Array.isArray(proveedores)) proveedores = [];
    } catch (err) {
      console.error(MOD, 'Error al cargar proveedores:', err);
      return [];
    }

    _proveedoresCache = { data: proveedores, timestamp: Date.now() };
    return proveedores;
  }

  /**
   * Obtiene proyectos desde el API con cache de 5 minutos.
   * @returns {Promise<Array>} Lista de proyectos
   */
  async function fetchProyectos() {
    if (_proyectosCache && (Date.now() - _proyectosCache.timestamp < CACHE_TTL_MS)) {
      return _proyectosCache.data;
    }

    var proyectos = [];
    try {
      var url = w.Sintel.Compras.API.proyectos.list;
      var headers = await window.Sintel.Compras.getHeaders();
      var res = await fetch(url, { headers: headers });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var json = await res.json();
      proyectos = json.results || json;
      if (!Array.isArray(proyectos)) proyectos = [];
    } catch (err) {
      console.error(MOD, 'Error al cargar proyectos:', err);
      return [];
    }

    _proyectosCache = { data: proyectos, timestamp: Date.now() };
    return proyectos;
  }

  /**
   * Carga proveedores en un <select> del DOM.
   * @param {string} selectSelector - Selector CSS del <select>
   * @param {string|null} selectedValue - UUID a preseleccionar
   * @param {string} placeholderText - Texto del primer <option>
   */
  async function loadProveedoresSelect(selectSelector, selectedValue, placeholderText) {
    selectedValue = selectedValue || null;
    placeholderText = placeholderText || 'Seleccione...';

    var select = d.querySelector(selectSelector);
    if (!select) return;

    var proveedores = await fetchProveedores();

    select.innerHTML = '';
    var ph = d.createElement('option');
    ph.value = '';
    ph.textContent = placeholderText;
    select.appendChild(ph);

    proveedores.forEach(function(p) {
      var opt = d.createElement('option');
      opt.value = p.uuid || p.id;
      opt.dataset.nombre = p.razon_social || p.nombre || p.nombre_comercial || '';
      opt.dataset.numeroDocumento = p.numero_documento || p.nit || '';
      opt.textContent = opt.dataset.nombre + ' (' + opt.dataset.numeroDocumento + ')';
      if (selectedValue && opt.value === selectedValue) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }

  /**
   * Carga proyectos en un <select> del DOM.
   * @param {string} selectSelector - Selector CSS del <select>
   * @param {string|null} selectedValue - UUID a preseleccionar
   * @param {string} placeholderText - Texto del primer <option>
   */
  async function loadProyectosSelect(selectSelector, selectedValue, placeholderText) {
    selectedValue = selectedValue || null;
    placeholderText = placeholderText || 'Seleccione... (Opcional)';

    var select = d.querySelector(selectSelector);
    if (!select) return;

    var proyectos = await fetchProyectos();

    select.innerHTML = '';
    var ph = d.createElement('option');
    ph.value = '';
    ph.textContent = placeholderText;
    select.appendChild(ph);

    proyectos.forEach(function(p) {
      var opt = d.createElement('option');
      opt.value = p.uuid || p.id;
      opt.textContent = p.nombre || p.codigo || '';
      if (selectedValue && opt.value === selectedValue) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }

  /**
   * Invalida todas las caches.
   */
  function invalidateCache(which) {
    if (!which || which === 'proveedores') _proveedoresCache = null;
    if (!which || which === 'proyectos') _proyectosCache = null;
  }

  // Remediacion cache-no-invalidada (auditoria 2026-08-06): un Proveedor creado
  // o editado en el modulo Proveedores no se reflejaba en el selector de
  // "Nueva Orden de Compra" hasta recargar toda la pagina, porque nada invalidaba
  // esta cache de 5 minutos al cambiar el catalogo de proveedores en otro modulo
  // de la misma sesion del Workspace. proveedores_form.js dispara este evento
  // sobre document.body tras crear/editar/eliminar un proveedor.
  d.body.addEventListener('proveedor-updated', function() {
    invalidateCache('proveedores');
  });

  w.Sintel.Compras.Utils = {
    loadProveedoresSelect: loadProveedoresSelect,
    loadProyectosSelect: loadProyectosSelect,
    invalidateCache: invalidateCache
  };

})(window, document);
