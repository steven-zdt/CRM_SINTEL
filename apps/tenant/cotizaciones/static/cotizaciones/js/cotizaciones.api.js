/**
 * cotizaciones.api.js - SSoT de URLs y consumo de endpoints
 * Namespace: window.Sintel.Cotizaciones.api
 *
 * Gateway Directo: /api/v1/cotizaciones/
 *
 * F32.6: migrado a Sintel.Core.Http -- ya no reimplementa fetch+CSRF+JWT
 * (violaba el contrato "solo URLs+metodos", F31.3/F32.1). Contrato
 * publico preservado: cada metodo de Configuracion sigue devolviendo una
 * Promise que resuelve con los datos o rechaza con {ok:false,status,data}
 * (objeto plano, no Error -- forma original de este archivo, distinta de
 * ventas/compras/gastos/empleados; se preserva tal cual porque no se
 * encontro ningun consumidor de request() fuera de este archivo -- grep
 * completo, 0 resultados -- pero el shape del rechazo si podria estar
 * siendo inspeccionado por los 3 metodos que si son publicos).
 */
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var BASE = '/api/v1/cotizaciones';

  // getHeaders() se conserva por compatibilidad hacia atras (exportada
  // publicamente como w.Sintel.Cotizaciones.api.getHeaders).
  //
  // Bug real (2026-08-26): faltaba 'Content-Type': 'application/json'.
  // Los 3 consumidores que hacen fetch() crudo con body: JSON.stringify(...)
  // (cotizacion_editor.js, producto_editor.js, servicio_editor.js) mandaban
  // el body como texto plano sin declarar su tipo -- el navegador por
  // defecto NO asume application/json para un body de tipo string, y DRF
  // respondia 415 Unsupported Media Type en cada POST/PATCH, bloqueando
  // por completo la creacion/edicion de Cotizacion/Producto/Servicio. El
  // propio fallback de cotizaciones.ui.js:59 (cuando getHeaders() no esta
  // disponible) ya incluia este header -- confirma que era un olvido, no
  // una decision deliberada.
  function getHeaders() {
    var headers = { 'Content-Type': 'application/json' };
    var csrf = w.Sintel && w.Sintel.Core && w.Sintel.Core.Http && w.Sintel.Core.Http.csrf
      ? w.Sintel.Core.Http.csrf()
      : null;
    if (csrf) headers['X-CSRFToken'] = csrf;
    var token = w.jwtAuth && typeof w.jwtAuth.getAccessToken === 'function'
      ? w.jwtAuth.getAccessToken()
      : null;
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return headers;
  }

  /**
   * request(method, url, data) -- recibe datos crudos (no pre-serializados;
   * antes los 3 llamadores hacian JSON.stringify() ellos mismos y esta
   * funcion recibia options.body ya como string -- ahora Core.Http lo
   * serializa una sola vez, aqui).
   */
  async function request(method, url, data) {
    const res = await w.Sintel.Core.Http.request(method, url, data);
    if (!res.ok) {
      throw { ok: false, status: res.status, data: res.data };
    }
    return res.data;
  }

  w.Sintel.Cotizaciones.api = {
    // URLs Cotizaciones
    listUrl:        BASE + '/',
    createUrl:      BASE + '/',
    detailUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    deleteUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    updateUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    recalcularUrl:  function (uuid) { return BASE + '/' + uuid + '/recalcular/'; },
    exportarPdfUrl: function (uuid) { return BASE + '/' + uuid + '/exportar-pdf/'; },
    estadisticasUrl: BASE + '/estadisticas/',

    // URLs Configuracion
    configuracionUrl: BASE + '/configuracion/',
    configuracionDetailUrl: function (uuid) { return BASE + '/configuracion/' + uuid + '/'; },

    // Métodos Configuracion
    createConfiguracion: function (data) {
      return request('POST', this.configuracionUrl, data);
    },
    updateConfiguracion: function (uuid, data) {
      return request('PATCH', this.configuracionDetailUrl(uuid), data);
    },
    deleteConfiguracion: function (uuid) {
      return request('DELETE', this.configuracionDetailUrl(uuid));
    },

    // URLs Productos
    productosUrl:     BASE + '/productos/',
    productoDetailUrl: function (uuid) { return BASE + '/productos/' + uuid + '/'; },

    // URLs Servicios
    serviciosUrl:     BASE + '/servicios/',
    servicioDetailUrl: function (uuid) { return BASE + '/servicios/' + uuid + '/'; },

    // URLs Items
    itemsUrl:         BASE + '/items/',
    itemDetailUrl:    function (uuid) { return BASE + '/items/' + uuid + '/'; },

    // HTMX Offcanvas URLs (Partials)
    offcanvasCrearUrl:   '/cotizaciones/editor/draft/',
    offcanvasEditarUrl:  function (uuid) { return '/cotizaciones/editor/' + uuid + '/'; },
    offcanvasDetalleUrl: function (uuid) { return '/cotizaciones/partials/ver/' + uuid + '/'; },

    // Headers helper
    getHeaders: getHeaders
  };

})(window);
