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
  var _cotizacionesCache = null;

  /**
   * GET contra el API de Compras via el unico transporte oficial
   * (Sintel.Core.Http, el mismo motor interno de compras.api.js::_fetch) --
   * Fase 5 (PLAN_OPTIMIZACION_COMPRAS...): elimina el segundo sistema HTTP
   * (fetch()+getHeaders()) que vivia solo en este archivo.
   * @returns {Promise<Array>} Lista de resultados (paginados o no)
   */
  async function _getLista(url) {
    var res = await w.Sintel.Core.Http.request('GET', url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var data = res.data;
    var lista = (data && data.results) || data;
    return Array.isArray(lista) ? lista : [];
  }

  /**
   * Obtiene proveedores desde el API con cache de 5 minutos.
   * @param {string} [search] - Texto de busqueda bajo demanda (Fase 4)
   * @returns {Promise<Array>} Lista de proveedores
   */
  async function fetchProveedores(search) {
    var query = (search || '').trim();
    // La cache de 5 min solo aplica al catalogo sin filtro (combo inicial);
    // una busqueda con texto siempre golpea el backend (resultados acotados
    // por `?search=`, nunca el catalogo completo -- Fase 4).
    if (!query && _proveedoresCache && (Date.now() - _proveedoresCache.timestamp < CACHE_TTL_MS)) {
      return _proveedoresCache.data;
    }

    var url = w.Sintel.Compras.API.proveedores.list;
    if (query) url += '?search=' + encodeURIComponent(query);

    var proveedores;
    try {
      proveedores = await _getLista(url);
    } catch (err) {
      console.error(MOD, 'Error al cargar proveedores:', err);
      return [];
    }

    if (!query) _proveedoresCache = { data: proveedores, timestamp: Date.now() };
    return proveedores;
  }

  /**
   * Obtiene proyectos desde el API con cache de 5 minutos.
   * @param {string} [search] - Texto de busqueda bajo demanda (Fase 4)
   * @returns {Promise<Array>} Lista de proyectos
   */
  async function fetchProyectos(search) {
    var query = (search || '').trim();
    if (!query && _proyectosCache && (Date.now() - _proyectosCache.timestamp < CACHE_TTL_MS)) {
      return _proyectosCache.data;
    }

    var url = w.Sintel.Compras.API.proyectos.list;
    if (query) url += '?search=' + encodeURIComponent(query);

    var proyectos;
    try {
      proyectos = await _getLista(url);
    } catch (err) {
      console.error(MOD, 'Error al cargar proyectos:', err);
      return [];
    }

    if (!query) _proyectosCache = { data: proyectos, timestamp: Date.now() };
    return proyectos;
  }

  var _requisicionesDisponiblesCache = null;

  /**
   * Obtiene Requisiciones disponibles para consolidar en una Orden de
   * Compra, con saldo real por fila (Fase 10 de
   * PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md, #32) -- ya filtradas y
   * calculadas server-side por RequisicionCompraSelector.
   * get_available_for_purchase() + ProcurementBudgetControlService (unico
   * calculo de saldo, #20 del plan). Reemplaza el fetch-todas+filtro
   * client-side que usaba esta funcion antes del N:N.
   * @returns {Promise<Array>} Lista de requisiciones disponibles con saldo
   */
  async function fetchRequisicionesDisponibles() {
    if (_requisicionesDisponiblesCache && (Date.now() - _requisicionesDisponiblesCache.timestamp < CACHE_TTL_MS)) {
      return _requisicionesDisponiblesCache.data;
    }

    var requisiciones = [];
    try {
      requisiciones = await w.Sintel.Compras.API.requisiciones.disponiblesParaOrden();
      if (!Array.isArray(requisiciones)) requisiciones = [];
    } catch (err) {
      console.error(MOD, 'Error al cargar requisiciones disponibles:', err);
      return [];
    }

    _requisicionesDisponiblesCache = { data: requisiciones, timestamp: Date.now() };
    return requisiciones;
  }

  /**
   * Obtiene cotizaciones desde el API con cache de 5 minutos. Requerido por
   * el formulario de creacion de RequisicionCompra -- Requisicion.cotizacion
   * es obligatoria desde 2026-09-26 (decision del usuario).
   * @param {string} [search] - Texto de busqueda bajo demanda (Fase 4)
   * @returns {Promise<Array>} Lista de cotizaciones
   */
  async function fetchCotizaciones(search) {
    var query = (search || '').trim();
    if (!query && _cotizacionesCache && (Date.now() - _cotizacionesCache.timestamp < CACHE_TTL_MS)) {
      return _cotizacionesCache.data;
    }

    var url = w.Sintel.Compras.API.cotizaciones.list;
    if (query) url += '?search=' + encodeURIComponent(query);

    var cotizaciones;
    try {
      cotizaciones = await _getLista(url);
    } catch (err) {
      console.error(MOD, 'Error al cargar cotizaciones:', err);
      return [];
    }

    if (!query) _cotizacionesCache = { data: cotizaciones, timestamp: Date.now() };
    return cotizaciones;
  }

  /**
   * Combo de busqueda bajo demanda (texto + resultados), Fase 4
   * (PLAN_OPTIMIZACION_COMPRAS...): reemplaza los <select> que descargaban
   * el catalogo completo de proveedores/proyectos -- 3+ caracteres disparan
   * una busqueda real al servidor (`?search=`, debounce 300ms), mismo
   * criterio UX que los buscadores ya existentes en Compras (Vincular
   * requisición / Buscar Factura).
   *
   * @param {HTMLFormElement} form
   * @param {Object} cfg
   * @param {string} cfg.inputSelector - input de texto visible
   * @param {string} cfg.hiddenSelector - input hidden con el uuid real (es el
   *   campo que efectivamente viaja en el payload, ver recolectarDatos())
   * @param {string} cfg.resultsSelector - contenedor de resultados
   * @param {function(string): Promise<Array>} cfg.fetchFn
   * @param {function(Object): string} cfg.getValue
   * @param {function(Object): string} cfg.getLabel
   * @param {number} [cfg.minChars=3]
   */
  function initBuscadorAsync(form, cfg) {
    var inputBuscar = form.querySelector(cfg.inputSelector);
    var inputHidden = form.querySelector(cfg.hiddenSelector);
    var resultados = form.querySelector(cfg.resultsSelector);
    if (!inputBuscar || !inputHidden || !resultados) return;

    var minChars = cfg.minChars || 3;
    var timer = null;

    function ocultarResultados() {
      resultados.classList.add('d-none');
      resultados.innerHTML = '';
    }

    function seleccionar(item) {
      inputHidden.value = cfg.getValue(item);
      inputBuscar.value = cfg.getLabel(item);
      ocultarResultados();
    }

    function renderResultados(lista) {
      resultados.innerHTML = '';
      if (!lista.length) {
        var vacio = d.createElement('div');
        vacio.className = 'list-group-item text-muted small';
        vacio.textContent = 'Sin resultados.';
        resultados.appendChild(vacio);
        resultados.classList.remove('d-none');
        return;
      }
      lista.forEach(function(item) {
        var btn = d.createElement('button');
        btn.type = 'button';
        btn.className = 'list-group-item list-group-item-action small';
        btn.textContent = cfg.getLabel(item);
        btn.addEventListener('click', function() { seleccionar(item); });
        resultados.appendChild(btn);
      });
      resultados.classList.remove('d-none');
    }

    inputBuscar.addEventListener('input', function() {
      var q = inputBuscar.value.trim();
      // Editar el texto invalida la seleccion previa hasta elegir un
      // resultado nuevo -- evita enviar un uuid que ya no corresponde al
      // texto visible en pantalla.
      inputHidden.value = '';
      if (timer) clearTimeout(timer);
      if (q.length < minChars) { ocultarResultados(); return; }
      timer = setTimeout(function() {
        cfg.fetchFn(q).then(renderResultados);
      }, 300);
    });

    inputBuscar.addEventListener('focus', function() {
      if (resultados.children.length) resultados.classList.remove('d-none');
    });

    d.addEventListener('click', function(e) {
      if (e.target !== inputBuscar && !resultados.contains(e.target)) ocultarResultados();
    });

    var btnLimpiar = cfg.clearSelector ? form.querySelector(cfg.clearSelector) : null;
    if (btnLimpiar) {
      btnLimpiar.addEventListener('click', function(e) {
        e.preventDefault();
        inputHidden.value = '';
        inputBuscar.value = '';
        ocultarResultados();
      });
    }
  }

  /**
   * Invalida todas las caches.
   */
  function invalidateCache(which) {
    if (!which || which === 'proveedores') _proveedoresCache = null;
    if (!which || which === 'proyectos') _proyectosCache = null;
    if (!which || which === 'cotizaciones') _cotizacionesCache = null;
    if (!which || which === 'requisiciones') _requisicionesDisponiblesCache = null;
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
    // Fase 4 (PLAN_OPTIMIZACION_COMPRAS...): combo de busqueda bajo demanda
    // -- reemplaza loadProveedoresSelect/loadProyectosSelect/
    // loadCotizacionesSelect (retirados, sin otro consumidor real -- ver
    // compras_editor.js::initializeEditor).
    initBuscadorAsync: initBuscadorAsync,
    fetchProveedores: fetchProveedores,
    // Expuesta para el widget "Vincular Proyecto" (PLAN_NUEVA_REQUISICION_
    // FORMULARIO.md #17-20) en requisiciones_editor.js.
    fetchProyectos: fetchProyectos,
    // Expuesta para el widget "Vincular Cotización" en
    // requisiciones_editor.js -- reutiliza la misma cache de 5 min, en vez
    // de duplicar el fetch.
    fetchCotizaciones: fetchCotizaciones,
    invalidateCache: invalidateCache
  };

})(window, document);
