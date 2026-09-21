/**
 * sincronizar_facturas.js — Offcanvas "Sincronizar y validar facturas"
 * Namespace: window.Sintel.Ventas.SincronizarFacturas
 *
 * PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES: vincula (o crea) la Venta
 * comercial de cada Factura electronica (naturaleza VENTA) que aun no
 * tiene una Venta asociada. Nunca crea/emite una Factura nueva.
 *
 * Reglas:
 *   - mostrarOffcanvasSeguro(el) para abrir Bootstrap offcanvas (anti-backdrop)
 *   - NUNCA parseInt() sobre UUIDs
 *   - Tras sincronizar: dispara 'venta-updated' en body para que la tabla
 *     de Ventas (hx-trigger="load, venta-updated from:body") se refresque.
 */
(function (w, d) {
    'use strict';

    var MOD = '[ventas.sincronizar-facturas]';
    var PANEL_ID = 'offcanvas-sincronizar-facturas';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    function mostrarOffcanvasSeguro(elOrId) {
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(elOrId);
    }

    function mostrarFeedback(mensaje, tipo) {
        var el = d.getElementById('sincronizar-facturas-feedback');
        if (!el) return;
        el.className = 'alert alert-' + (tipo || 'danger') + ' mb-3';
        el.textContent = mensaje;
        el.classList.remove('d-none');
    }

    function ocultarFeedback() {
        var el = d.getElementById('sincronizar-facturas-feedback');
        if (el) { el.classList.add('d-none'); el.textContent = ''; }
    }

    var ESTADO_LABEL = {
        VINCULADA: { texto: 'Vinculada', clase: 'success' },
        YA_VINCULADA: { texto: 'Ya vinculada', clase: 'secondary' },
        AMBIGUA: { texto: 'Ambigua', clase: 'warning' },
        INVALIDA: { texto: 'Invalida', clase: 'danger' },
        ERROR: { texto: 'Error', clase: 'danger' },
    };

    function _notificarVentasActualizadas() {
        d.body.dispatchEvent(new CustomEvent('venta-updated'));
    }

    function _actualizarContador(panelEl) {
        var seleccionadas = panelEl.querySelectorAll('.chk-factura-pendiente:checked').length;
        var contador = d.getElementById('contador-seleccionadas');
        var btnBulk = d.getElementById('btn-sincronizar-seleccionadas');
        if (contador) contador.textContent = String(seleccionadas);
        if (btnBulk) btnBulk.disabled = seleccionadas === 0;
    }

    function _mostrarResumen(resultados, resumen) {
        var el = d.getElementById('sincronizar-facturas-resumen');
        if (!el) return;
        var partes = [];
        Object.keys(resumen || {}).forEach(function (estado) {
            var count = resumen[estado];
            if (!count) return;
            var meta = ESTADO_LABEL[estado] || { texto: estado, clase: 'secondary' };
            partes.push('<span class="badge bg-' + meta.clase + '-subtle text-' + meta.clase + ' border border-' + meta.clase + '-subtle me-1">' + meta.texto + ': ' + count + '</span>');
        });
        var detalles = (resultados || [])
            .filter(function (r) { return r.estado !== 'VINCULADA' && r.estado !== 'YA_VINCULADA'; })
            .map(function (r) {
                var detalle = typeof r.detalle === 'string' ? r.detalle : JSON.stringify(r.detalle || '');
                return '<div class="small text-muted">' + (r.numero || r.factura_uuid) + ': ' + detalle + '</div>';
            })
            .join('');
        el.innerHTML = '<div class="p-2 border rounded bg-light">' + partes.join(' ') + '</div>' + detalles;
        el.classList.remove('d-none');
    }

    function _marcarFilaResultado(panelEl, resultado) {
        var fila = panelEl.querySelector('tr[data-factura-uuid="' + resultado.factura_uuid + '"]');
        if (!fila) return;
        if (resultado.estado === 'VINCULADA' || resultado.estado === 'YA_VINCULADA') {
            fila.style.opacity = '0.35';
            var celdaAccion = fila.querySelector('td:last-child');
            if (celdaAccion) {
                celdaAccion.innerHTML = '<i class="bi bi-check2-circle text-success"></i>';
            }
            var chk = fila.querySelector('.chk-factura-pendiente');
            if (chk) { chk.checked = false; chk.disabled = true; }
        } else {
            var btn = fila.querySelector('.btn-vincular-factura');
            if (btn) btn.disabled = false;
            fila.classList.add('table-danger');
        }
    }

    async function _sincronizar(panelEl, facturaUuids, botonOrigen) {
        var API = w.Sintel && w.Sintel.Ventas && w.Sintel.Ventas.API;
        if (!API) { console.error(MOD, 'API no disponible'); return; }
        ocultarFeedback();
        if (botonOrigen) botonOrigen.disabled = true;

        try {
            var resp = await API.sincronizarFacturas(facturaUuids);
            var resultados = resp.resultados || [];
            var resumen = resp.resumen || {};
            resultados.forEach(function (r) { _marcarFilaResultado(panelEl, r); });
            _mostrarResumen(resultados, resumen);
            _actualizarContador(panelEl);
            if (resultados.some(function (r) { return r.estado === 'VINCULADA'; })) {
                _notificarVentasActualizadas();
            }
        } catch (err) {
            var msg = (err.data && err.data.detail) ? err.data.detail : 'No se pudo sincronizar la(s) factura(s) seleccionada(s).';
            mostrarFeedback(msg, 'danger');
            if (botonOrigen) botonOrigen.disabled = false;
        }
    }

    function bindPanel(panelEl) {
        var chkTodas = d.getElementById('chk-seleccionar-todas');
        if (chkTodas) {
            chkTodas.addEventListener('change', function () {
                panelEl.querySelectorAll('.chk-factura-pendiente:not(:disabled)').forEach(function (chk) {
                    chk.checked = chkTodas.checked;
                });
                _actualizarContador(panelEl);
            });
        }

        panelEl.querySelectorAll('.chk-factura-pendiente').forEach(function (chk) {
            chk.addEventListener('change', function () { _actualizarContador(panelEl); });
        });

        panelEl.querySelectorAll('.btn-vincular-factura').forEach(function (btn) {
            btn.addEventListener('click', async function () {
                var uuid = btn.getAttribute('data-uuid');
                if (!uuid) return;
                var confirmado = await w.UIManager?.confirm('Sincronizar esta Factura y vincularla (o crear) su Venta comercial?');
                if (!confirmado) return;
                await _sincronizar(panelEl, [uuid], btn);
            });
        });

        var btnBulk = d.getElementById('btn-sincronizar-seleccionadas');
        if (btnBulk) {
            btnBulk.addEventListener('click', async function () {
                var seleccionadas = Array.prototype.map.call(
                    panelEl.querySelectorAll('.chk-factura-pendiente:checked'),
                    function (chk) { return chk.value; }
                );
                if (!seleccionadas.length) return;
                var confirmado = await w.UIManager?.confirm('Sincronizar ' + seleccionadas.length + ' factura(s) seleccionada(s)?');
                if (!confirmado) return;
                await _sincronizar(panelEl, seleccionadas, btnBulk);
            });
        }

        _actualizarContador(panelEl);
    }

    var SincronizarFacturas = {
        onPanelLoaded: function () {
            var el = d.getElementById(PANEL_ID);
            if (!el) {
                console.warn(MOD, 'onPanelLoaded: ' + PANEL_ID + ' no encontrado');
                return;
            }
            bindPanel(el);
            mostrarOffcanvasSeguro(el);
        },
    };

    w.Sintel.Ventas.SincronizarFacturas = SincronizarFacturas;

    d.dispatchEvent(new CustomEvent('sintel:ventas:sincronizar-facturas:ready'));

})(window, document);
