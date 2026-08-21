/**
 * welcome_context.js (mision Access Context, 2026-08-21) — pinta la linea de
 * bienvenida de #workspace-welcome usando Sintel.Core.UserContext. No hace
 * ninguna llamada a red propia: consume el contexto ya cargado por
 * user_context.js, y lee el nombre de sede ya renderizado por el servidor
 * en el selector del header (evita una tercera fuente/llamada para un dato
 * que el propio header ya resolvio).
 *
 * FASE 5 (estados del contexto): si el contexto no esta listo o falla, el
 * banner simplemente no se muestra -- nunca se pinta "undefined"/"null"/IDs
 * tecnicos, se prefiere no decir nada a decir algo incorrecto.
 */
(function (w, d) {
  'use strict';

  const ROL_LABELS = {
    ADMIN: 'Administrador',
    OPERADOR: 'Operador',
    VISOR: 'Visor',
  };

  function nombreSedeActiva() {
    const el = d.querySelector('#sede-dropdown-toggle span.small');
    return el ? el.textContent.trim() : null;
  }

  function render(state, data) {
    const banner = d.getElementById('welcome-context-banner');
    const nombreEl = d.getElementById('welcome-context-nombre');
    const detalleEl = d.getElementById('welcome-context-detalle');
    if (!banner || !nombreEl || !detalleEl) return;

    const UserContext = w.Sintel && w.Sintel.Core && w.Sintel.Core.UserContext;
    if (!UserContext || state !== UserContext.STATES.READY || !data) return;

    const primerNombre = (data.nombre || '').split(' ')[0] || data.nombre;
    nombreEl.textContent = primerNombre ? `Hola, ${primerNombre}` : 'Bienvenido';

    const rolLabel = ROL_LABELS[data.rol] || data.rol || '';
    const sedeLabel = nombreSedeActiva();
    const partes = [rolLabel, sedeLabel].filter(Boolean);
    detalleEl.textContent = partes.length ? partes.join(' · ') : '';

    banner.classList.remove('d-none');
  }

  function init() {
    const UserContext = w.Sintel && w.Sintel.Core && w.Sintel.Core.UserContext;
    if (!UserContext) return;
    UserContext.onReady(render);
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
