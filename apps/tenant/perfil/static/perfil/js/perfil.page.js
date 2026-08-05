// apps/tenant/perfil/static/perfil/js/perfil.page.js
/**
 * perfil.page.js - Orquestador del modulo Perfil
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#perfiles-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list.html). Columnas,
 * orden y permisos por fila (incluyendo el guard [SEG-5] de auto-eliminacion)
 * viven en tables.py/views.py (server-side).
 */
(function (w, d) {
  'use strict';

  const MOD = 'perfil';
  const CONTAINER_ID = '#tab-perfil';

  // Contexto de permisos del usuario autenticado actual (cargado desde /me/),
  // usado unicamente para gobernar la visibilidad del boton "Nuevo Perfil".
  let requestorContext = {};

  async function loadRequestorContext() {
    // DSV: el endpoint /me/ ya aplica aislamiento por tenant activo.
    try {
      var url = (w.Sintel && w.Sintel.Perfil && w.Sintel.Perfil.API)
        ? w.Sintel.Perfil.API.me
        : '/api/v1/perfil/perfiles/me/';
      var headers = { 'Accept': 'application/json' };
      if (w.jwtAuth && typeof w.jwtAuth.getValidAccessToken === 'function') {
        try {
          var token = await w.jwtAuth.getValidAccessToken();
          if (token) headers['Authorization'] = 'Bearer ' + token;
        } catch (e) {}
      }
      var res = await fetch(url, { credentials: 'same-origin', headers: headers });
      if (!res.ok) return;
      var myProfile = await res.json();
      requestorContext = myProfile.permissions_context || {};
      requestorContext.user_id = myProfile.user_id || null;
      w.Sintel = w.Sintel || {};
      w.Sintel.Perfil = w.Sintel.Perfil || {};
      w.Sintel.Perfil.requestorContext = requestorContext;
    } catch (e) {
      console.warn('[' + MOD + '.page] loadRequestorContext:', e.message || e);
    }
  }

  function bindActionsDelegation() {
    d.body.addEventListener('click', function (e) {
      const btn = e.target.closest('#perfiles-panel button[data-action]');
      if (!btn) return;

      e.preventDefault();
      e.stopPropagation();

      const action = btn.getAttribute('data-action');
      const id = btn.getAttribute('data-id');  // [RULE 3] UUID string — prohibido parseInt() en UUIDs

      if (!id) {
        console.warn(`[${MOD}.page] ID no valido:`, id);
        return;
      }

      switch (action) {
        case 'ver':
          if (w.perfilModals && typeof w.perfilModals.showDetail === 'function') {
            w.perfilModals.showDetail(id);
          }
          break;
        case 'editar':
          if (w.perfilModals && typeof w.perfilModals.showEdit === 'function') {
            w.perfilModals.showEdit(id);
          }
          break;
        case 'asignar-rol':
          // Reutiliza el offcanvas de edicion: la seccion de rol aparece para ADMIN
          if (w.perfilModals && typeof w.perfilModals.showEdit === 'function') {
            w.perfilModals.showEdit(id);
          }
          break;
        case 'eliminar':
          if (w.perfilModals && typeof w.perfilModals.deletePerfil === 'function') {
            w.perfilModals.deletePerfil(id);
          }
          break;
        default:
          console.warn('[' + MOD + '.page] Accion no reconocida:', action);
      }
    });
  }

  function configurarEventos() {
    // Controlar visibilidad de 'Nuevo Perfil' segun permissions_context.
    // NO clonar/reemplazar el boton: preserva atributos HTMX (hx-get, hx-target).
    var btnCrear = d.getElementById('btn-perfil-crear');
    if (btnCrear) {
      btnCrear.style.display = requestorContext.can_create_profiles ? '' : 'none';
    }

    var btnRefrescar = d.getElementById('btn-refrescar-perfil');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', function () {
        w.refreshPerfilTable();
      });
    }
  }

  // Funcion global de refresco: dispara el evento que el panel HTMX escucha
  // via hx-trigger="load, perfil-updated from:body" (ver list.html).
  w.refreshPerfilTable = function () {
    d.body.dispatchEvent(new CustomEvent('perfil-updated'));
  };

  async function inicializarModulo() {
    console.log('[' + MOD + '.page] Inicializando modulo...');
    await loadRequestorContext();
    configurarEventos();
  }

  bindActionsDelegation();

  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(CONTAINER_ID, function () {
      inicializarModulo().catch(err => console.error(err));
    });
  } else {
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      inicializarModulo().catch(err => console.error(err));
    }
    initFallback();
  }

})(window, document);
