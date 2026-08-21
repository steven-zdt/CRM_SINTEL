/**
 * Sintel.UserContext (mision Access Context, 2026-08-21) — cliente frontend
 * delgado del contexto de acceso del usuario. NO reimplementa nada: combina
 * en memoria las 2 fuentes ya existentes y probadas del backend:
 *
 *   GET /api/v1/perfil/perfiles/me/     -- identidad + permissions_context
 *                                          (gestion de usuarios, PerfilViewSet)
 *   GET /api/v1/core/contexto/          -- OrganizationalContext + OrganizationalScope
 *                                          (tenant/empresa/sede/area/rol/alcance)
 *
 * Regla de nomenclatura (ORGANIZATIONAL_CONTRACT.md): este modulo NO es un
 * tercer sistema de contexto/autorizacion -- es un cache de lectura de los
 * dos ya existentes. Nunca decide permisos por si mismo; el backend sigue
 * siendo la autoridad (Regla Absoluta #3 de la mision).
 *
 * Una sola carga inicial (Promise.all en paralelo), cacheada en memoria
 * hasta el proximo reload de pagina -- ver documentacion/ux/UX_ACCESS_CONTEXT_AUDIT.md.
 */
(function (w, d) {
  'use strict';

  const STATES = Object.freeze({
    LOADING: 'loading',
    READY: 'ready',
    INCOMPLETE: 'incomplete',
    UNAUTHORIZED: 'unauthorized',
    ERROR: 'error',
  });

  let _state = STATES.LOADING;
  let _data = null;
  let _error = null;
  const _listeners = [];

  function _notify() {
    _listeners.splice(0).forEach((fn) => {
      try {
        fn(_state, _data);
      } catch (err) {
        console.error('[UserContext] Error en listener', err);
      }
    });
  }

  /**
   * Suscribe fn(state, data) cuando el contexto termine de resolverse
   * (READY, INCOMPLETE, UNAUTHORIZED o ERROR). Si ya esta resuelto, invoca
   * de inmediato -- evita condiciones de carrera con quien se suscribe tarde.
   */
  function onReady(fn) {
    if (_state !== STATES.LOADING) {
      fn(_state, _data);
      return;
    }
    _listeners.push(fn);
  }

  async function _fetchJson(url) {
    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      const data = resp.ok ? await resp.json() : null;
      return { status: resp.status, ok: resp.ok, data };
    } catch (err) {
      return { status: 0, ok: false, data: null };
    }
  }

  async function init() {
    _state = STATES.LOADING;
    _error = null;

    const [meRes, ctxRes] = await Promise.all([
      _fetchJson('/api/v1/perfil/perfiles/me/'),
      _fetchJson('/api/v1/core/contexto/'),
    ]);

    if (meRes.status === 401 || meRes.status === 403 || ctxRes.status === 401 || ctxRes.status === 403) {
      _state = STATES.UNAUTHORIZED;
      _data = null;
      _notify();
      return;
    }

    if (!meRes.ok || !ctxRes.ok) {
      _state = STATES.ERROR;
      _error = 'No se pudo cargar el contexto del usuario.';
      _data = null;
      _notify();
      return;
    }

    const me = meRes.data || {};
    const ctx = ctxRes.data || {};
    const scope = ctx.scope || {};

    _data = {
      // Identidad
      userId: me.user_id,
      nombre: me.user_full_name || me.user_email || '',
      email: me.user_email || '',
      cargo: me.cargo || '',
      avatarUrl: me.avatar_url || null,
      // Organizacion (OrganizationalContext -- posicion activa)
      tenantSchema: ctx.tenant_schema,
      tenantId: ctx.tenant_id,
      empresaId: ctx.empresa_id,
      // Rol y alcance
      rol: me.rol || ctx.rol,
      alcance: ctx.alcance,
      // Sede/Area activa (singular, ejecucion) -- ver ADR-003
      sedeActivaId: ctx.sede_id,
      areaActivaId: ctx.area_id,
      // Alcance total permitido (OrganizationalScope -- plural, autorizacion)
      sedeIdsPermitidas: scope.sede_ids,
      areaIdsPermitidas: scope.area_ids,
      // Capacidades de gestion de usuarios (Perfil, no un permiso general de modulos)
      permissionsContext: me.permissions_context || {},
      // Preferencias
      timezone: ctx.timezone || null,
      configuracion: ctx.configuracion || {},
    };

    _state = (_data.userId != null && _data.empresaId != null) ? STATES.READY : STATES.INCOMPLETE;
    _notify();
  }

  function get() {
    return _data;
  }

  function getState() {
    return _state;
  }

  function getError() {
    return _error;
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Core = w.Sintel.Core || {};
  w.Sintel.Core.UserContext = { STATES, onReady, get, getState, getError, init };
})(window, document);
