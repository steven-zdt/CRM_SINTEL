/**
 * facturas.table.js - Configuracion de Tabulator para el modulo Facturas
 * SINTEL v2.61.5 - JS-SINTEL Standard
 *
 * Define columnas, inicializa Tabulator y maneja eventos de la tabla.
 * Las acciones de fila usan data-action + event delegation: sin onclick inline.
 * Anti-zombie: destruye instancias previas antes de crear nuevas.
 *
 * Exporta: window.Sintel.Facturas.table
 * Dependencias: window.Sintel.Facturas.utils, window.TabulatorFactory (opcional)
 */

(function (w, d) {
    'use strict';

    var MOD = '[facturas.table]';

    w.Sintel = w.Sintel || {};
    w.Sintel.Factura = w.Sintel.Factura || {};

    // Referencia a la instancia activa de Tabulator
    var _table = null;

    // Registro global anti-zombie (compatibilidad con codigo heredado)
    w.SintelFacturasTables = w.SintelFacturasTables || {};

    /**
     * Retorna la definicion de columnas de la tabla de facturas.
     * Las columnas de acciones usan data-action y data-id, sin logica inline.
     * @returns {Array}
     */
    function getColumnas() {
        var utils = w.Sintel && w.Sintel.Factura && w.Sintel.Factura.utils;

        function fmtMoneda(cell) {
            return utils ? utils.formatearMoneda(cell.getValue()) : cell.getValue() || '---';
        }
        function fmtFecha(cell) {
            return utils ? utils.formatearFecha(cell.getValue()) : cell.getValue() || '---';
        }
        function fmtValorOFallback(cell) {
            return cell.getValue() || '---';
        }

        return [
            {
                title: 'Nro. Factura',
                field: 'numero',
                formatter: fmtValorOFallback,
                minWidth: 150
            },
            {
                title: 'Naturaleza',
                field: 'naturaleza',
                width: 120,
                formatter: function (cell) {
                    return utils ? utils.badgeNaturaleza(cell.getValue())
                        : cell.getValue() || '---';
                },
                headerFilter: 'select',
                headerFilterParams: {
                    values: { '': 'Todas', 'VENTA': 'VENTA', 'COMPRA': 'COMPRA' }
                }
            },
            {
                title: 'Cliente / Proveedor',
                field: 'cliente_nombre',
                formatter: fmtValorOFallback,
                minWidth: 220
            },
            {
                title: 'Fecha Emision',
                field: 'fecha_emision',
                formatter: fmtFecha,
                width: 130
            },
            {
                title: 'Vencimiento',
                field: 'fecha_vencimiento',
                formatter: fmtFecha,
                width: 130
            },
            {
                title: 'Estado',
                field: 'estado',
                width: 120,
                formatter: function (cell) {
                    if (!utils) return cell.getValue() || '---';
                    var estadoPago = utils.determinarEstadoPago(cell.getRow().getData());
                    return '<span class="badge ' + estadoPago.clase + '">' + estadoPago.texto + '</span>';
                }
            },
            {
                title: 'Total',
                field: 'total',
                formatter: fmtMoneda,
                hozAlign: 'right',
                width: 150
            },
            {
                title: 'Acciones',
                field: 'id',
                headerSort: false,
                hozAlign: 'center',
                width: 110,
                formatter: function (cell) {
                    var id = cell.getValue();
                    return '<div class="btn-group btn-group-sm" role="group">' +
                        '<button type="button" class="btn btn-outline-primary" ' +
                            'data-action="ver" data-id="' + id + '" title="Ver detalle">' +
                            '<i class="bi bi-eye"></i>' +
                        '</button>' +
                        '<button type="button" class="btn btn-outline-danger" ' +
                            'data-action="eliminar" data-id="' + id + '" title="Eliminar">' +
                            '<i class="bi bi-trash"></i>' +
                        '</button>' +
                    '</div>';
                }
            }
        ];
    }

    /**
     * Inicializa Tabulator en el elemento #grid-facturas.
     * Destruye la instancia previa si existe (anti-zombie).
     * Conecta rowClick al flujo de ver detalle.
     * @returns {Object|null} Instancia de Tabulator o null
     */
    function init() {
        var gridEl = d.querySelector('#grid-facturas');
        if (!gridEl) {
            console.warn(MOD + ':init #grid-facturas no encontrado');
            return null;
        }

        // Anti-zombie: destruir instancia previa
        if (_table && typeof _table.destroy === 'function') {
            try { _table.destroy(); } catch (e) { /* ignorar */ }
            _table = null;
            // w.SintelFacturasTables.main = null; // o borrar
        }

        var url = '/api/v1/facturas/';

        // Usar TabulatorFactory si esta disponible
        if (w.TabulatorFactory && typeof w.TabulatorFactory.create === 'function') {
            _table = w.TabulatorFactory.create(
                '#grid-facturas',
                url,
                getColumnas(),
                { searchInputSelector: '#search-factura' }
            );
        } else if (typeof Tabulator !== 'undefined') {
            _table = new Tabulator('#grid-facturas', {
                ajaxURL: url,
                ajaxFiltering: true,
                layout: 'fitColumns',
                columns: getColumnas(),
                placeholder: 'No hay facturas registradas',
                paginationSize: 25,
                pagination: 'remote'
            });
        } else {
            console.error(MOD + ':init Tabulator no disponible');
            return null;
        }

        if (_table) {
            w.SintelFacturasTables.main = _table;

            // Cargar resumen cuando se carguen los datos
            _table.on('dataLoaded', function () {
                _cargarResumen();
            });

            // Evento rowClick: delegar a Sintel.Facturas.ver evitando botones
            _table.on('rowClick', function (e, row) {
                var target = e.target || (e.originalEvent && e.originalEvent.target);
                if (target && target.closest && target.closest('button, a')) return;
                var id = row.getData().id;
                if (id && w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.ver === 'function') {
                    w.Sintel.Factura.ver(id);
                }
            });

            console.log(MOD + ':init Tabulator inicializado');
        }

        return _table;
    }

    /**
     * Recarga los datos de la tabla sin destruir la instancia.
     */
    function refresh() {
        if (_table && typeof _table.replaceData === 'function') {
            _table.replaceData();
        } else {
            console.warn(MOD + ':refresh tabla no inicializada');
        }
    }

    /**
     * Retorna la instancia activa de Tabulator.
     * @returns {Object|null}
     */
    function getInstance() {
        return _table;
    }

    /**
     * Registra event delegation para los botones data-action en el grid.
     * Se debe llamar una vez tras init().
     */
    function initEventos() {
        var gridEl = d.querySelector('#grid-facturas');
        if (!gridEl) return;

        // Evitar listeners duplicados
        if (gridEl._facturasTableListener) {
            gridEl.removeEventListener('click', gridEl._facturasTableListener);
        }

        gridEl._facturasTableListener = function (e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;

            e.preventDefault();
            e.stopPropagation();

            var action = btn.getAttribute('data-action');
            var rawId  = btn.getAttribute('data-id');

            var utils = w.Sintel && w.Sintel.Factura && w.Sintel.Factura.utils;
            var id    = utils ? utils.validarId(rawId) : parseInt(rawId, 10);

            if (!id) {
                console.error(MOD + ':initEventos ID invalido:', rawId);
                return;
            }

            if (action === 'ver') {
                if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.ver === 'function') {
                    w.Sintel.Factura.ver(id);
                }
            } else if (action === 'eliminar') {
                if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.eliminar === 'function') {
                    w.Sintel.Factura.eliminar(id);
                }
            }
        };

        gridEl.addEventListener('click', gridEl._facturasTableListener);
        console.log(MOD + ':initEventos event delegation configurado');
    }

    // Carga el resumen financiero y actualiza el DOM (delegacion interna)
    function _cargarResumen() {
        if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.recargarResumen === 'function') {
            w.Sintel.Factura.recargarResumen();
        }
    }

    /**
     * Registra el listener HTMX OOB para HX-Trigger: listaFacturasChanged.
     * El backend lo emite en destroy / create-from-dto / upload-ubl exitosos.
     * Se registra una sola vez en document.body.
     */
    function initHXTrigger() {
        if (d.body._facturasHXTriggerRegistered) return;
        d.body._facturasHXTriggerRegistered = true;
        d.body.addEventListener('listaFacturasChanged', function () {
            console.log(MOD + ':listaFacturasChanged -> recargando tabla');
            refresh();
        });
        console.log(MOD + ':initHXTrigger registrado');
    }

    // -- Exportar --
    w.Sintel.Factura.table = {
        init: init,
        refresh: refresh,
        getInstance: getInstance,
        initEventos: initEventos,
        initHXTrigger: initHXTrigger,
        getColumnas: getColumnas
    };

    // Alias de compatibilidad con codigo heredado
    w.FacturasListModule = {
        init: init,
        refresh: refresh,
        getTable: getInstance
    };

})(window, document);
