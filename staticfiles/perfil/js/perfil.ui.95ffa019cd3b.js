// Compatibility wrapper for perfil UI helpers (migrated from core)
(function (w) {
  'use strict';

  w.perfilUI = w.perfilUI || {
    renderPerfilSection: function (data) {
      if (w.perfilBundle && typeof w.perfilBundle.renderPerfil === 'function') {
        return w.perfilBundle.renderPerfil(data);
      }
      console.warn('[perfil.ui] perfilBundle.renderPerfil not available');
      return null;
    }
  };

})(window);
