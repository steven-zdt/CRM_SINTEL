/**
 * retencion_list.js - Feature List para Retencion
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#retenciones-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_retenciones.html).
 * Solo lectura -- las retenciones son generadas via Pull Model (RetencionesService),
 * no hay acciones de fila que delegar aqui. Columnas/orden/paginacion/filtros
 * viven en tables.py/views.py (server-side).
 */
(function (w, d) {
  'use strict';

  // Sin acciones de fila (solo lectura) -- nada que inicializar por ahora.
  // Se expone reload() por consistencia con el resto de modulos de contabilidad,
  // por si algun flujo futuro necesita refrescar la tabla desde otro modulo.
  w.RetencionList = Object.freeze({
    reload: () => d.body.dispatchEvent(new CustomEvent('retencion-updated')),
  });
})(window, document);
