/**
 * gastos.utils.js - Helpers centralizados para Gastos v2.61.8
 * Namespace: window.Sintel.Gastos.Utils
 *
 * Centraliza la carga de catalogos FK compartidos (proveedores, cuentas contables)
 * con cache en memoria de 5 minutos para evitar llamadas repetidas al endpoint
 * en la misma sesion de trabajo.
 */
(function(w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Gastos = w.Sintel.Gastos || {};

  var MOD = '[Gastos.Utils]';
  var CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos

  // Caches en memoria: { data: [], timestamp: number }
  var _proveedoresCache = null;
  var _cuentasCache = null;

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
      var url = w.Sintel.Gastos.API.proveedores.list;
      var headers = w.Sintel.Gastos.getHeaders();
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
   * Obtiene cuentas contables de gasto desde el API con cache de 5 minutos.
   * @returns {Promise<Array>} Lista de cuentas contables
   */
  async function fetchCuentas() {
    if (_cuentasCache && (Date.now() - _cuentasCache.timestamp < CACHE_TTL_MS)) {
      return _cuentasCache.data;
    }

    var cuentas = [];
    try {
      var url = w.Sintel.Gastos.API.contabilidad.cuentasGasto;
      var headers = w.Sintel.Gastos.getHeaders();
      var res = await fetch(url, { headers: headers });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var json = await res.json();
      cuentas = json.results || json;
      if (!Array.isArray(cuentas)) cuentas = [];
    } catch (err) {
      console.error(MOD, 'Error al cargar cuentas contables:', err);
      return [];
    }

    _cuentasCache = { data: cuentas, timestamp: Date.now() };
    return cuentas;
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
      opt.textContent = p.nombre + ' (' + p.numero_documento + ')';
      if (selectedValue && opt.value === selectedValue) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }

  /**
   * Carga cuentas contables en un <select> del DOM.
   * @param {string} selectSelector - Selector CSS del <select>
   * @param {string|null} selectedValue - UUID a preseleccionar
   * @param {string} placeholderText - Texto del primer <option>
   */
  async function loadCuentasSelect(selectSelector, selectedValue, placeholderText) {
    selectedValue = selectedValue || null;
    placeholderText = placeholderText || 'Seleccione...';

    var select = d.querySelector(selectSelector);
    if (!select) return;

    var cuentas = await fetchCuentas();

    select.innerHTML = '';
    var ph = d.createElement('option');
    ph.value = '';
    ph.textContent = placeholderText;
    select.appendChild(ph);

    cuentas.forEach(function(c) {
      var opt = d.createElement('option');
      opt.value = c.uuid;
      opt.textContent = '[' + c.codigo + '] ' + c.nombre;
      if (selectedValue && opt.value === selectedValue) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }

  /**
   * Invalida todas las caches. Llamar despues de crear/editar/eliminar
   * un proveedor para que la proxima carga haga fetch fresco.
   * @param {string} [which] - 'proveedores', 'cuentas' o undefined (invalida todo)
   */
  function invalidateCache(which) {
    if (!which || which === 'proveedores') _proveedoresCache = null;
    if (!which || which === 'cuentas') _cuentasCache = null;
  }

  w.Sintel.Gastos.Utils = {
    loadProveedoresSelect: loadProveedoresSelect,
    loadCuentasSelect: loadCuentasSelect,
    invalidateCache: invalidateCache
  };

})(window, document);
