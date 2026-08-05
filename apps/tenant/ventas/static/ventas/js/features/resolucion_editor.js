/**
 * resolucion_editor.js — Logica de offcanvas Crear/Editar/Panel para Resoluciones DIAN v3.16.x
 * Namespace: window.Sintel.Ventas.ResolucionEditor
 *
 * Reglas:
 *   - mostrarOffcanvasSeguro(el) para abrir Bootstrap offcanvas (anti-backdrop)
 *   - NUNCA parseInt() sobre UUIDs — rangos son enteros: parseInt valido
 *   - Tras crear/editar/eliminar: recargar el panel via htmx.ajax
 */
(function (w, d) {
    'use strict';

    var MOD = '[ventas.resolucion-editor]';
    var PANEL_URL = '/api/v1/ventas/resoluciones/panel/';
    var PANEL_TARGET = '#offcanvas-container-ventas';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    // ── Utilidades ─────────────────────────────────────────────────────────

    function mostrarOffcanvasSeguro(elOrId) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(elOrId);
    }

    function mostrarFeedback(containerId, mensaje, tipo) {
        var el = d.getElementById(containerId);
        if (!el) return;
        el.className = 'alert alert-' + (tipo || 'danger') + ' mt-2';
        el.textContent = mensaje;
        el.classList.remove('d-none');
    }

    function ocultarFeedback(containerId) {
        var el = d.getElementById(containerId);
        if (el) { el.classList.add('d-none'); el.textContent = ''; }
    }

    function _recargarPanel() {
        if (typeof htmx !== 'undefined') {
            htmx.ajax('GET', PANEL_URL, { target: PANEL_TARGET, swap: 'innerHTML' });
        }
    }

    function recolectarPayload() {
        return {
            numero_resolucion: (d.getElementById('res-numero-resolucion') || {}).value || '',
            prefijo:           (d.getElementById('res-prefijo') || {}).value || '',
            tipo:              (d.getElementById('res-tipo') || {}).value || 'FE',
            fecha_resolucion:  (d.getElementById('res-fecha-resolucion') || {}).value || '',
            rango_desde:       parseInt((d.getElementById('res-rango-desde') || {}).value || '0', 10),
            rango_hasta:       parseInt((d.getElementById('res-rango-hasta') || {}).value || '0', 10),
            fecha_desde:       (d.getElementById('res-fecha-desde') || {}).value || '',
            fecha_hasta:       (d.getElementById('res-fecha-hasta') || {}).value || '',
            vigente:           !!(d.getElementById('res-vigente') || {}).checked,
        };
    }

    function _validarPayload(payload, feedbackId) {
        if (!payload.numero_resolucion) {
            mostrarFeedback(feedbackId, 'El numero de resolucion es obligatorio.', 'danger');
            return false;
        }
        if (!payload.fecha_resolucion || !payload.fecha_desde || !payload.fecha_hasta) {
            mostrarFeedback(feedbackId, 'Todas las fechas son obligatorias.', 'danger');
            return false;
        }
        if (!payload.rango_desde || !payload.rango_hasta || payload.rango_desde > payload.rango_hasta) {
            mostrarFeedback(feedbackId, 'Rango invalido: "Desde" debe ser <= "Hasta" y ambos >= 1.', 'danger');
            return false;
        }
        return true;
    }

    function _msgError(err) {
        if (err && err.data) {
            var msgs = [];
            Object.keys(err.data).forEach(function (k) {
                var v = err.data[k];
                msgs.push(k === 'detail' ? String(v) : k + ': ' + (Array.isArray(v) ? v.join(', ') : String(v)));
            });
            if (msgs.length) return msgs.join(' | ');
        }
        return 'Error al guardar la resolucion.';
    }

    // ── Panel — Listado ────────────────────────────────────────────────────

    function bindPanelBotones(panelEl) {
        panelEl.querySelectorAll('[data-action="eliminar-resolucion"]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var uuid   = btn.getAttribute('data-uuid');
                var numero = btn.getAttribute('data-numero') || uuid;
                if (!uuid) return;
                if (!w.confirm('Eliminar resolucion "' + numero + '"?\nSolo se puede si no tiene ventas asociadas.')) return;

                var API = w.Sintel && w.Sintel.Ventas && w.Sintel.Ventas.API;
                if (!API) { console.error(MOD, 'API no disponible'); return; }

                btn.disabled = true;
                var fila = btn.closest('tr');
                if (fila) fila.style.opacity = '0.4';

                API.resoluciones.eliminar(uuid)
                    .then(function () {
                        _recargarPanel();
                    })
                    .catch(function (err) {
                        btn.disabled = false;
                        if (fila) fila.style.opacity = '';
                        var msg = (err.data && err.data.detail) ? err.data.detail : 'No se pudo eliminar.';
                        var feedEl = d.getElementById('panel-resoluciones-feedback');
                        if (feedEl) {
                            feedEl.className = 'alert alert-danger mb-3';
                            feedEl.textContent = msg;
                            feedEl.classList.remove('d-none');
                        }
                    });
            });
        });
    }

    // ── Crear ──────────────────────────────────────────────────────────────

    function bindFormCrear(offcanvasEl) {
        var btn = d.getElementById('btn-guardar-resolucion');
        if (!btn) return;

        var nuevoBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(nuevoBtn, btn);

        nuevoBtn.addEventListener('click', function () {
            ocultarFeedback('form-resolucion-feedback');
            var payload = recolectarPayload();
            if (!_validarPayload(payload, 'form-resolucion-feedback')) return;

            nuevoBtn.disabled = true;
            nuevoBtn.textContent = 'Guardando...';

            w.Sintel.Ventas.API.resoluciones.create(payload)
                .then(function () {
                    _recargarPanel();
                })
                .catch(function (err) {
                    nuevoBtn.disabled = false;
                    nuevoBtn.innerHTML = '<i class="bi bi-floppy me-1"></i>Guardar Resolucion';
                    mostrarFeedback('form-resolucion-feedback', _msgError(err), 'danger');
                });
        });

        mostrarOffcanvasSeguro(offcanvasEl);
    }

    // ── Editar ─────────────────────────────────────────────────────────────

    function bindFormEditar(offcanvasEl) {
        var btn = d.getElementById('btn-actualizar-resolucion');
        if (!btn) return;

        var nuevoBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(nuevoBtn, btn);

        nuevoBtn.addEventListener('click', function () {
            ocultarFeedback('form-resolucion-editar-feedback');
            var formEl = d.getElementById('resolucion-editar-form');
            var resolucionUUID = formEl ? formEl.getAttribute('data-uuid') : '';

            if (!resolucionUUID) {
                mostrarFeedback('form-resolucion-editar-feedback', 'UUID de resolucion no disponible.', 'danger');
                return;
            }

            var payload = recolectarPayload();
            if (!_validarPayload(payload, 'form-resolucion-editar-feedback')) return;

            nuevoBtn.disabled = true;
            nuevoBtn.textContent = 'Guardando...';

            w.Sintel.Ventas.API.resoluciones.update(resolucionUUID, payload)
                .then(function () {
                    _recargarPanel();
                })
                .catch(function (err) {
                    nuevoBtn.disabled = false;
                    nuevoBtn.innerHTML = '<i class="bi bi-floppy me-1"></i>Guardar Cambios';
                    mostrarFeedback('form-resolucion-editar-feedback', _msgError(err), 'danger');
                });
        });

        mostrarOffcanvasSeguro(offcanvasEl);
    }

    // ── API Publica ────────────────────────────────────────────────────────

    var ResolucionEditor = {

        onPanelLoaded: function () {
            var el = d.getElementById('offcanvas-resoluciones-panel');
            if (!el) {
                console.warn(MOD, 'onPanelLoaded: offcanvas-resoluciones-panel no encontrado');
                return;
            }
            bindPanelBotones(el);
            mostrarOffcanvasSeguro(el);
        },

        onHtmxLoaded: function () {
            var elCrear = d.getElementById('offcanvas-resolucion-crear');
            if (elCrear) {
                bindFormCrear(elCrear);
                return;
            }
            var elEditar = d.getElementById('offcanvas-resolucion-editar');
            if (elEditar) {
                bindFormEditar(elEditar);
                return;
            }
            console.warn(MOD, 'onHtmxLoaded: ningun offcanvas de resolucion encontrado');
        },
    };

    w.Sintel.Ventas.ResolucionEditor = ResolucionEditor;

    d.dispatchEvent(new CustomEvent('sintel:ventas:resolucion-editor:ready'));

})(window, document);
