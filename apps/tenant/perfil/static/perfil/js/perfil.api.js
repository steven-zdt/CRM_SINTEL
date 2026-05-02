// perfil.api.js - Gateway Directo SSoT para la app perfil
// [RULE 2] Unica fuente de verdad para URLs y endpoints de esta app.
// Namespace: window.Sintel.Perfil.API
(function (w, d) {
  'use strict';

  var BASE = '/api/v1/perfil/perfiles/';

  function getCsrf() {
    var el = d.querySelector('[name=csrfmiddlewaretoken]');
    if (el) return el.value;
    var match = d.cookie.split(';').find(function (c) {
      return c.trim().startsWith('csrftoken=');
    });
    return match ? match.split('=')[1].trim() : '';
  }

  var API = {
    BASE: BASE,
    // Endpoints de listado / creacion
    list: BASE,
    create: BASE,
    me: BASE + 'me/',
    renderCrear: BASE + 'render-offcanvas/crear/',
    // Endpoints de instancia (requieren id)
    retrieve: function (id) { return BASE + id + '/'; },
    update: function (id) { return BASE + id + '/'; },
    destroy: function (id) { return BASE + id + '/'; },
    assignRol: function (id) { return BASE + id + '/assign-rol/'; },
    renderEditar: function (id) { return BASE + id + '/render-offcanvas/editar/'; },
    renderDetalle: function (id) { return BASE + id + '/render-offcanvas/detalle/'; },
    // Helper CSRF
    getCsrf: getCsrf,
  };

  w.Sintel = w.Sintel || {};
  w.Sintel.Perfil = w.Sintel.Perfil || {};
  w.Sintel.Perfil.API = Object.freeze(API);

  // Compatibilidad hacia atras con w.perfilAPI
  w.perfilAPI = w.perfilAPI || API;

})(window, document);
