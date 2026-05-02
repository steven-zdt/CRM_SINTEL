/**
 * facturas.ui.js - Manejo de DOM, Offcanvas y formularios del modulo Facturas
 * SINTEL v2.61.5 - JS-SINTEL Standard
 *
 * Responsabilidades:
 * - Ciclo de vida del Offcanvas Bootstrap (abrir, cerrar, cargar via HTMX)
 * - Formulario de creacion/edicion: recoleccion de payload + DOM Shield
 * - Vista de detalle (solo lectura): poblar DOM con datos de la API
 * - HTMX event handlers: afterSwap, responseError
 * - Formulario dinamico de campos faltantes (respuesta 422 del backend)
 *
 * Exporta: window.Sintel.Factura.ui
 * Dependencias: window.Sintel.Factura.utils, window.Sintel.Factura.api,
 *               window.UIManager, window.SintelFeedback, htmx, bootstrap
 */

(function (w, d) {
    'use strict';

    var MOD = '[facturas.ui]';

    w.Sintel = w.Sintel || {};
    w.Sintel.Factura = w.Sintel.Factura || {};

    var OFFCANVAS_CONTAINER = 'offcanvas-container-facturas';
    var OFFCANVAS_FORM_ID   = 'offcanvas-factura';
    var OFFCANVAS_VER_ID    = 'offcanvas-ver-factura';
    // GESTOR_URL se construye desde el Core API Facade (SSoT en factura_api.js)
    // para evitar duplicar el prefijo. Se resuelve en tiempo de ejecucion tras
    // que factura_api.js haya exportado window.Sintel.Factura.api.CORE_FACTURAS.
    function getGestorUrl() {
        var api = w.Sintel && w.Sintel.Factura && w.Sintel.Factura.api;
        return (api && api.CORE_FACTURAS)
            ? api.CORE_FACTURAS + '/gestor-offcanvas/'
            : '/api/v1/facturas/gestor-offcanvas/'; // fallback seguro
    }

    // Instancia Bootstrap Offcanvas activa
    var _offcanvasInstance = null;

    // ---------------------------------------------------------
    // Seccion: Offcanvas lifecycle
    // ---------------------------------------------------------

    /**
     * Abre el offcanvas de creacion/subida (sin ID = nueva factura).
     */
    async function abrirCrear() {
        await _cargarOffcanvas(null, true);
    }

    /**
     * Abre el offcanvas de detalle (solo lectura) para la factura indicada.
     * @param {number} id
     */
    async function abrirDetalle(id) {
        await _cargarOffcanvas(id, true, true);
    }

    /**
     * Cierra el offcanvas activo.
     */
    function cerrar() {
        if (_offcanvasInstance) {
            try { _offcanvasInstance.hide(); } catch (e) { /* ignorar */ }
        }
    }

    /**
     * Carga el HTML del offcanvas desde el servidor via HTMX e inicializa Bootstrap.
     * @param {number|null} id
     * @param {boolean} simple
     * @param {boolean} [readonly=false]
     */
    async function _cargarOffcanvas(id, simple, readonly) {
        var container = d.getElementById(OFFCANVAS_CONTAINER);
        if (!container) {
            console.error(MOD + ':_cargarOffcanvas contenedor #' + OFFCANVAS_CONTAINER + ' no encontrado');
            if (w.SintelFeedback) w.SintelFeedback.error('Error interno: contenedor de offcanvas no encontrado');
            return;
        }

        var params = 'simple=' + (simple ? 'true' : 'false');
        if (id)       params += '&id=' + id;
        if (readonly) params += '&readonly=true';

        var url = getGestorUrl() + '?' + params;

        await htmx.ajax('GET', url, { target: '#' + OFFCANVAS_CONTAINER, swap: 'innerHTML' });

        // Esperar render
        await new Promise(function (resolve) { setTimeout(resolve, 60); });

        // Intentar el ID correcto segun modo
        var offcanvasId = readonly ? OFFCANVAS_VER_ID : OFFCANVAS_FORM_ID;
        var offcanvasEl = d.getElementById(offcanvasId) || d.getElementById(OFFCANVAS_FORM_ID);

        if (offcanvasEl) {
            _offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
            _offcanvasInstance.show();

            // Si es detalle, poblar datos via API
            if (readonly && id) {
                var api = w.Sintel.Factura.api;
                var res = await api.obtener(id);
                if (res.ok) {
                    poblarDetalle(res.data);
                } else if (res.status === 404) {
                    cerrar();
                    if (w.SintelFeedback) w.SintelFeedback.warning('La factura ya no existe');
                } else {
                    if (w.UIManager) w.UIManager.handleError(res, MOD);
                }
            }
        } else {
            console.warn(MOD + ':_cargarOffcanvas elemento offcanvas no encontrado tras carga HTMX');
        }
    }

    // ---------------------------------------------------------
    // Seccion: Vista detalle (solo lectura)
    // ---------------------------------------------------------

    /**
     * Puebla los elementos del DOM del offcanvas de detalle con los datos de una factura.
     * @param {Object} data - Datos de la factura devueltos por la API
     */
    function poblarDetalle(data) {
        if (!data) return;
        var utils = w.Sintel.Factura.utils || {};
        var fmt   = utils.formatearMoneda || function (v) { return v; };
        var fmtFH = utils.formatearFechaHora || function (v) { return v; };

        function set(id, value, formatter) {
            var el = d.getElementById(id);
            if (!el) return;
            if (formatter) {
                el.innerHTML = formatter(value);
            } else {
                el.textContent = value || '-';
            }
        }

        set('view_numero_factura',       data.numero);
        set('view_estado',               data.estado, utils.badgeEstado);
        set('view_fecha_emision',        data.fecha_emision, fmtFH);
        set('view_moneda',               data.moneda || 'COP');
        set('view_emisor_razon_social',  data.emisor_razon_social);
        set('view_emisor_nit',           data.emisor_nit);
        set('view_receptor_razon_social',data.receptor_razon_social);
        set('view_receptor_nit',         data.receptor_nit);
        set('view_subtotal',             data.subtotal, function (v) { return fmt(v, data.moneda); });
        set('view_impuestos',            data.impuestos, function (v) { return fmt(v, data.moneda); });
        set('view_total',                data.total,    function (v) { return fmt(v, data.moneda); });

        if (data.cufe) {
            var cufeCont = d.getElementById('view_cufe_container');
            if (cufeCont) cufeCont.style.display = 'block';
            set('view_cufe', utils.shortHash ? utils.shortHash(data.cufe) : data.cufe);
        }

        // Items de la factura
        var tbody = d.getElementById('view_detalle_items_body');
        if (tbody) {
            tbody.innerHTML = '';
            var items = (data.items && Array.isArray(data.items)) ? data.items : [];
            if (items.length > 0) {
                items.forEach(function (item) {
                    var valorUnitario = item.valor_unitario || item.precio_unitario || 0;
                    var cantidad = item.cantidad || 0;
                    var total = item.total || (cantidad * valorUnitario);
                    var tr = d.createElement('tr');
                    tr.innerHTML =
                        '<td>' + (utils.escapeHtml ? utils.escapeHtml(item.descripcion || '-') : item.descripcion || '-') + '</td>' +
                        '<td class="text-end">' + cantidad + '</td>' +
                        '<td class="text-end">' + fmt(valorUnitario, data.moneda) + '</td>' +
                        '<td class="text-end">' + fmt(total, data.moneda) + '</td>';
                    tbody.appendChild(tr);
                });
            } else {
                var trVacio = d.createElement('tr');
                trVacio.innerHTML = '<td colspan="4" class="text-center text-muted">Sin items disponibles</td>';
                tbody.appendChild(trVacio);
            }
        }

        console.log(MOD + ':poblarDetalle factura ' + (data.numero || data.id) + ' poblada');
    }

    // ---------------------------------------------------------
    // Seccion: Formulario de creacion/edicion
    // ---------------------------------------------------------

    /**
     * Recolecta los items de la tabla del formulario de factura.
     * @returns {Array}
     */
    function recolectarItems() {
        var tbody = d.querySelector('#tbody-items-factura');
        if (!tbody) return [];

        var rows  = tbody.querySelectorAll('tr[data-item-id]');
        var items = [];

        rows.forEach(function (row, index) {
            var descripcion   = row.querySelector('td:nth-child(3)').textContent.trim();
            var cantidad      = parseFloat((row.querySelector('td:nth-child(4)').textContent || '').replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
            var valorUnitario = parseFloat((row.querySelector('td:nth-child(6)').textContent || '').replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
            var porcentajeIva = parseFloat((row.querySelector('td:nth-child(7)').textContent || '').replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
            var codigo        = row.querySelector('td:nth-child(2)').textContent.trim();
            var unidad        = row.querySelector('td:nth-child(5)').textContent.trim() || 'UND';
            var itemId        = row.getAttribute('data-item-id');

            if (descripcion && cantidad > 0 && valorUnitario > 0) {
                items.push({
                    id: itemId || null,
                    codigo: codigo,
                    descripcion: descripcion,
                    cantidad: cantidad,
                    unidad_medida: unidad,
                    valor_unitario: valorUnitario,
                    porcentaje_iva: porcentajeIva,
                    orden: index + 1
                });
            }
        });
        return items;
    }

    /**
     * Calcula subtotal, impuestos y total a partir de los items del formulario.
     * @returns {{subtotal, impuestos, total}}
     */
    function calcularTotales() {
        var items = recolectarItems();
        var subtotal = 0;
        var impuestos = 0;

        items.forEach(function (item) {
            var sub = item.cantidad * item.valor_unitario;
            subtotal  += sub;
            impuestos += sub * (item.porcentaje_iva / 100);
        });

        return {
            subtotal:  parseFloat(subtotal.toFixed(2)),
            impuestos: parseFloat(impuestos.toFixed(2)),
            total:     parseFloat((subtotal + impuestos).toFixed(2))
        };
    }

    /**
     * Recolecta el payload del formulario de factura aplicando DOM Shield.
     * DOM Shield: elimina temporalmente los atributos 'name' de los <select> visibles
     * para que FormData capture solo los <input hidden> con los IDs reales.
     * @returns {Object|null}
     */
    function recolectarPayload() {
        var form = d.querySelector('#form-factura');
        if (!form) return null;

        var selects    = form.querySelectorAll('select');
        var selectNames = new Map();
        selects.forEach(function (sel) {
            if (sel.hasAttribute('name')) {
                selectNames.set(sel, sel.getAttribute('name'));
                sel.removeAttribute('name');
            }
        });

        // ⚠️ DOM Shield Sync: Sincronizar select-shield con sus hidden inputs antes de FormData
        form.querySelectorAll('select.select-shield').forEach(function(sel) {
            var targetName = sel.getAttribute('data-target');
            if (targetName) {
                var hidden = form.querySelector('input[type="hidden"][name="' + targetName + '"]');
                if (hidden) hidden.value = sel.value;
            }
        });

        var formData = new FormData(form);
        var data     = Object.fromEntries(formData.entries());

        // DOM Shield: restaurar names
        selectNames.forEach(function (name, sel) { sel.setAttribute('name', name); });

        // Limpiar campos vacios
        Object.keys(data).forEach(function (k) {
            if (data[k] === '' || data[k] === null) delete data[k];
        });

        // Agregar items y totales
        data.items = recolectarItems();
        var totales = calcularTotales();
        data.subtotal  = totales.subtotal;
        data.impuestos = totales.impuestos;
        data.total     = totales.total;

        // Normalizar tipos numericos (Zero Trust - AGENTS.md §9)
        if (data.consecutivo) data.consecutivo = parseInt(data.consecutivo, 10) || null;
        if (data.subtotal)    data.subtotal     = parseFloat(data.subtotal)     || 0;
        if (data.impuestos)   data.impuestos    = parseFloat(data.impuestos)    || 0;
        if (data.total)       data.total        = parseFloat(data.total)        || 0;

        return data;
    }

    /**
     * Actualiza las cifras de totales en el DOM del formulario.
     */
    function actualizarTotalesDOM() {
        if (!d.querySelector('#form-factura')) return;

        var utils   = w.Sintel.Factura.utils || {};
        var fmt     = utils.formatearMoneda || function (v) { return v; };
        var totales = calcularTotales();

        var elSub = d.querySelector('#factura-subtotal');
        var elImp = d.querySelector('#factura-impuestos');
        var elTot = d.querySelector('#factura-total');

        if (elSub) elSub.textContent = fmt(totales.subtotal);
        if (elImp) elImp.textContent = fmt(totales.impuestos);
        if (elTot) elTot.textContent = fmt(totales.total);
    }

    /**
     * Muestra errores de formulario en el contenedor local del offcanvas (DOM Shielding).
     * @param {Object} res - Respuesta {ok, status, data} de la API
     */
    function mostrarErroresForm(res) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(res, MOD, { errorContainerSelector: '#form-factura-feedback' });
        } else {
            var cont = d.querySelector('#form-factura-feedback');
            if (cont) {
                cont.classList.remove('d-none');
                cont.textContent = (res.data && res.data.detail) || 'Error al guardar la factura';
            }
        }
    }

    /**
     * Limpia el contenedor de feedback del formulario.
     */
    function limpiarFeedbackForm() {
        var cont = d.querySelector('#form-factura-feedback');
        if (cont) {
            cont.classList.add('d-none');
            cont.textContent = '';
        }
    }

    // ---------------------------------------------------------
    // Seccion: Formulario de campos faltantes (respuesta 422)
    // ---------------------------------------------------------

    /**
     * Valida la calidad de extraccion de un DTO.
     * @param {Object} dto
     * @param {Object} metadata
     * @returns {{calidad: string, advertencias: string[], sugerirXML: boolean}}
     */
    function validarCalidadDTO(dto, metadata) {
        var advertencias = [];
        var sugerirXML   = false;
        var esPDF        = metadata && (metadata.file_type === 'pdf' || (metadata.mime_type && metadata.mime_type.includes('pdf')));

        var numero = dto.numero || (dto.identificadores && dto.identificadores.numero) || '';
        if (numero && numero.length < 3) {
            advertencias.push('El numero de factura parece incompleto');
            sugerirXML = true;
        }

        var total = parseFloat((dto.totales && dto.totales.total) || dto.total || 0);
        if (total === 0 && esPDF) {
            advertencias.push('El total es $0.00 - la extraccion del PDF puede ser incorrecta');
            sugerirXML = true;
        }

        var calidad = advertencias.length === 0 ? 'alta' : (sugerirXML ? 'baja' : 'media');
        return { calidad: calidad, advertencias: advertencias, sugerirXML: sugerirXML, esPDF: esPDF };
    }

    /**
     * Muestra un formulario dinamico para que el usuario complete campos faltantes
     * detectados por el backend (respuesta 422 con missing_fields).
     * @param {Object} dto
     * @param {string[]} campos
     * @param {Object} metadata
     */
    function mostrarFormCamposFaltantes(dto, campos, metadata) {
        var resultDiv = d.getElementById('upload-result');
        if (!resultDiv) return;

        var calidad = validarCalidadDTO(dto, metadata || {});

        var html = '<div class="alert alert-warning mb-3">' +
            '<h6 class="alert-heading"><i class="bi bi-exclamation-triangle me-2"></i>Campos faltantes detectados</h6>' +
            '<p class="mb-0">Complete los siguientes campos para guardar la factura:</p>' +
            '</div>';

        if (calidad.advertencias.length > 0) {
            html += '<div class="alert alert-danger mb-3">' +
                '<ul class="mb-0">' + calidad.advertencias.map(function (a) { return '<li>' + a + '</li>'; }).join('') + '</ul>' +
                (calidad.sugerirXML ? '<p class="mb-0 mt-2"><strong>Recomendacion:</strong> Use el archivo XML UBL 2.1 para mayor precision.</p>' : '') +
                '</div>';
        }

        html += '<form id="form-campos-faltantes" novalidate>';

        var mapaLabels = {
            'numero':              'Numero de Factura',
            'fecha_emision':       'Fecha de Emision',
            'naturaleza':          'Naturaleza (Venta/Compra)',
            'emisor.nit':          'NIT del Emisor',
            'emisor.razon_social': 'Razon Social del Emisor',
            'receptor.nit':        'NIT del Receptor',
            'receptor.razon_social': 'Razon Social del Receptor'
        };

        campos.forEach(function (campo) {
            var label  = mapaLabels[campo] || campo.replace(/[._]/g, ' ');
            var fieldId = 'campo-' + campo.replace(/\./g, '-');

            if (campo === 'naturaleza') {
                var valActual = dto.naturaleza || '';
                html += '<div class="mb-3">' +
                    '<label for="' + fieldId + '" class="form-label">' + label + ' <span class="text-danger">*</span></label>' +
                    '<select class="form-select" id="' + fieldId + '" name="' + campo + '" data-campo="' + campo + '" required>' +
                    '<option value="">Seleccione...</option>' +
                    '<option value="VENTA"' + (valActual === 'VENTA' ? ' selected' : '') + '>Venta (emitida)</option>' +
                    '<option value="COMPRA"' + (valActual === 'COMPRA' ? ' selected' : '') + '>Compra (recibida)</option>' +
                    '</select></div>';
            } else {
                html += '<div class="mb-3">' +
                    '<label for="' + fieldId + '" class="form-label">' + label + ' <span class="text-danger">*</span></label>' +
                    '<input type="text" class="form-control" id="' + fieldId + '" name="' + campo + '" data-campo="' + campo + '" required>' +
                    '</div>';
            }
        });

        html += '<div class="d-flex gap-2">' +
            '<button type="submit" class="btn btn-primary"><i class="bi bi-save me-2"></i>Guardar Factura</button>' +
            '<button type="button" class="btn btn-outline-secondary" id="btn-cancelar-campos">Cancelar</button>' +
            '</div></form>';

        resultDiv.innerHTML = html;

        // Cancelar
        var btnCancelar = d.getElementById('btn-cancelar-campos');
        if (btnCancelar) btnCancelar.addEventListener('click', function () { resultDiv.innerHTML = ''; });

        // Submit: completar DTO y persistir
        var form = d.getElementById('form-campos-faltantes');
        if (form) {
            form.addEventListener('submit', async function (e) {
                e.preventDefault();
                if (!form.checkValidity()) { form.classList.add('was-validated'); return; }

                var dtoCompleto = JSON.parse(JSON.stringify(dto));

                form.querySelectorAll('[data-campo]').forEach(function (input) {
                    var campo = input.getAttribute('data-campo');
                    var valor = input.value.trim();
                    if (!valor) return;
                    // Establecer en ruta anidada (ej: 'emisor.nit')
                    var partes  = campo.split('.');
                    var current = dtoCompleto;
                    for (var i = 0; i < partes.length - 1; i++) {
                        if (!current[partes[i]] || typeof current[partes[i]] !== 'object') current[partes[i]] = {};
                        current = current[partes[i]];
                    }
                    current[partes[partes.length - 1]] = valor;
                });

                var submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...'; }

                var api = w.Sintel.Factura.api;
                var res = await api.crearDesdeDTO(dtoCompleto, true, metadata && metadata.file_content_bytes, metadata && metadata.file_type);

                if (!res.ok) {
                    if (w.UIManager) w.UIManager.handleError(res, MOD, { errorContainerSelector: '#upload-result' });
                    else alert((res.data && res.data.detail) || 'Error al guardar');
                    if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="bi bi-save me-2"></i>Guardar Factura'; }
                    return;
                }

                cerrar();
                if (w.SintelFeedback) w.SintelFeedback.success('Factura guardada correctamente');
                if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.recargar === 'function') {
                    w.Sintel.Factura.recargar();
                }
            });
        }
    }

    // ---------------------------------------------------------
    // Seccion: HTMX handlers
    // ---------------------------------------------------------

    /**
     * Maneja la respuesta exitosa de subida de archivo via HTMX (htmx:afterSwap).
     * @param {Event} event
     */
    async function manejarAfterSwap(event) {
        var target = event.detail && event.detail.target;
        if (!target || target.id !== 'upload-result') return;

        var xhr = event.detail.xhr;
        if (!xhr) return;

        var data;
        try {
            data = typeof xhr.response === 'string' ? JSON.parse(xhr.response) : xhr.response;
        } catch (e) {
            return; // No es JSON; otro handler lo procesa
        }

        var previewMode = (d.getElementById('previewMode') && d.getElementById('previewMode').checked) || false;
        var dto         = data.dto || data;
        var missingFields = data.missing_fields || [];

        // Caso 1: Campos faltantes detectados
        if (!previewMode && missingFields.length > 0 && !data.id) {
            mostrarFormCamposFaltantes(dto, missingFields, data.metadata || {});
            return;
        }

        // Caso 2: Ya fue persistido directamente
        if (data.id || data.persisted) {
            cerrar();
            if (w.SintelFeedback) w.SintelFeedback.success('Factura procesada y guardada');
            if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.recargar === 'function') w.Sintel.Factura.recargar();
            return;
        }

        // Caso 3: Error de negocio
        if (data.error) {
            var resultDiv = d.getElementById('upload-result');
            if (resultDiv) resultDiv.textContent = data.message || data.error || 'Error al procesar';
            if (w.SintelFeedback) w.SintelFeedback.error(data.message || data.error || 'Error al procesar');
            return;
        }

        // Caso 4: Preview mode - mostrar resumen sin persistir
        if (previewMode && dto) {
            var utils = w.Sintel.Factura.utils || {};
            var fmt   = utils.formatearMoneda || function (v) { return v; };
            var resDiv = d.getElementById('upload-result');
            if (resDiv) {
                resDiv.innerHTML = '<div class="alert alert-info">' +
                    '<h6>Vista previa del documento</h6>' +
                    '<p><strong>Numero:</strong> ' + (dto.numero || 'N/A') + '</p>' +
                    '<p><strong>Total:</strong> ' + fmt(dto.total || 0) + '</p>' +
                    '<p class="mb-0 small">Este documento no fue guardado. Desmarque "Modo preview" para guardar.</p>' +
                    '</div>';
            }
            return;
        }

        // Caso 5: DTO sin campos faltantes, persistir automaticamente
        if (!previewMode && dto && !data.id) {
            var api = w.Sintel.Factura.api;
            var res = await api.crearDesdeDTO(dto, true, data.metadata && data.metadata.file_content_bytes, data.metadata && data.metadata.file_type);

            if (!res.ok) {
                if (w.UIManager) w.UIManager.handleError(res, MOD);
                return;
            }

            cerrar();
            if (w.SintelFeedback) w.SintelFeedback.success('Factura guardada correctamente');
            if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.recargar === 'function') w.Sintel.Factura.recargar();
        }
    }

    /**
     * Maneja errores de subida de archivo via HTMX (htmx:responseError).
     * Caso especial: si hay missing_fields (422), muestra formulario dinamico.
     * @param {Event} event
     */
    function manejarErrorSubida(event) {
        var target = event.detail && event.detail.target;
        if (!target || target.id !== 'upload-result') return;

        var xhr = event.detail.xhr;
        if (!xhr) return;

        var errorData;
        try {
            errorData = JSON.parse(xhr.responseText || '');
        } catch (e) {
            return;
        }

        if (errorData && errorData.missing_fields && errorData.missing_fields.length > 0) {
            mostrarFormCamposFaltantes(errorData.dto || {}, errorData.missing_fields, errorData.metadata || {});
        }
        // Otros errores son manejados por el error handler global
    }

    /**
     * Registra los event listeners de HTMX. Debe llamarse una vez.
     */
    function initHTMX() {
        d.body.addEventListener('htmx:afterSwap', manejarAfterSwap);
        d.body.addEventListener('htmx:responseError', manejarErrorSubida);
        console.log(MOD + ':initHTMX handlers registrados');
    }

    // ---------------------------------------------------------
    // Seccion: Event delegation del offcanvas container
    // ---------------------------------------------------------

    /**
     * Registra event delegation en #offcanvas-container-facturas.
     */
    function initEventosOffcanvas() {
        var container = d.getElementById(OFFCANVAS_CONTAINER);
        if (!container) return;

        if (container._facturasUIListener) {
            container.removeEventListener('click', container._facturasUIListener);
        }

        // Sincronizacion en tiempo real para select-shield (DOM Shield)
        container.addEventListener('change', function (e) {
            if (e.target.matches('select.select-shield')) {
                var targetName = e.target.getAttribute('data-target');
                if (targetName) {
                    var form = e.target.closest('form');
                    var hidden = form ? form.querySelector('input[type="hidden"][name="' + targetName + '"]') : null;
                    if (hidden) hidden.value = e.target.value;
                }
            }
        });

        container._facturasUIListener = function (e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;

            var action = btn.getAttribute('data-action');
            var id = btn.getAttribute('data-factura-id') || btn.getAttribute('data-id');

            if (action === 'eliminar-factura' && id) {
                e.preventDefault();
                if (w.Sintel && w.Sintel.Factura && typeof w.Sintel.Factura.eliminar === 'function') {
                    w.Sintel.Factura.eliminar(id);
                }
            }
            // ver-pdf y ver-xml: el href ya maneja la navegacion
        };

        container.addEventListener('click', container._facturasUIListener);
        console.log(MOD + ':initEventosOffcanvas event delegation configurado');
    }

    // -- Exportar --
    w.Sintel.Factura.ui = {
        abrirCrear: abrirCrear,
        abrirDetalle: abrirDetalle,
        cerrar: cerrar,
        poblarDetalle: poblarDetalle,
        recolectarItems: recolectarItems,
        calcularTotales: calcularTotales,
        recolectarPayload: recolectarPayload,
        actualizarTotalesDOM: actualizarTotalesDOM,
        mostrarErroresForm: mostrarErroresForm,
        limpiarFeedbackForm: limpiarFeedbackForm,
        mostrarFormCamposFaltantes: mostrarFormCamposFaltantes,
        validarCalidadDTO: validarCalidadDTO,
        initHTMX: initHTMX,
        initEventosOffcanvas: initEventosOffcanvas
    };

    // Aliases de compatibilidad con codigo heredado
    w.VerDetalleFactura = { ver: function (id) { return abrirDetalle(id); } };
    w.verDetalleFactura = function (id) { return abrirDetalle(id); };
    w.FacturasEditorModule = {
        recolectarItems: recolectarItems,
        calcularTotales: calcularTotales,
        actualizarTotalesEnDOM: actualizarTotalesDOM
    };

})(window, document);
