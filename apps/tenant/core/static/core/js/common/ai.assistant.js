/**
 * ai.assistant.js -- Cliente del Asistente IA global (mision SINTEL-AI-UI-01).
 * Namespace: window.Sintel.AI
 *
 * Primera superficie de producto del AI Engine existente (AI-06, Form
 * Assistant): este modulo NO agrega backend nuevo, NO decide que tool
 * ejecutar, NO genera texto por si mismo -- unicamente llama al endpoint
 * ya real POST /api/v1/ai/ask/ (apps/services/ai/api/viewsets.py) y
 * renderiza la respuesta que ya calcula el orquestador/AIEngine.
 *
 * Vive en core/js/common/ (no en un app.js por app) porque es transversal
 * al ERP -- mismo criterio ya aplicado a reporting.api.js. Requiere
 * Sintel.Core.Http (core-http.js) y Sintel.Core.mostrarOffcanvasSeguro
 * (offcanvas.helper.js) cargados antes (ver assets_core.html).
 *
 * Nunca usa innerHTML con texto del usuario/LLM -- todo se inserta via
 * textContent (XSS). Nunca muestra uuid/id/nombre de tool/stack traces
 * (mismo mandato que Fase 3/8 de la mision: nada tecnico visible).
 */
(function (w, d) {
    'use strict';

    if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
        console.error('[Sintel.AI] Sintel.Core.Http no esta cargado. Revisar orden de <script> en assets_core.html.');
        return;
    }

    var ASK_URL = '/api/v1/ai/ask/';
    var MAX_ITEMS = 10;
    var EXCLUDE_KEYS = ['id', 'uuid', 'empresa_id', 'document_uuid', 'source_id', 'cliente_uuid', 'proveedor_uuid'];
    var FIELD_LABELS = {
        stock_actual: 'Stock actual',
        stock_minimo: 'Stock minimo',
        precio_venta: 'Precio de venta',
        categoria: 'Categoria',
        numero_documento: 'Documento',
        estado: 'Estado',
        total: 'Total',
        saldo: 'Saldo',
        email: 'Correo',
        telefono: 'Telefono',
        fecha_emision: 'Fecha de emision',
        source_type: 'Fuente',
        score: 'Relevancia',
    };

    var enviando = false;
    var els = null;

    function _els() {
        if (els) return els;
        var form = d.getElementById('asistente-ia-form');
        if (!form) return null;
        els = {
            toggle: d.getElementById('btn-asistente-ia-toggle'),
            form: form,
            input: d.getElementById('asistente-ia-input'),
            enviarBtn: d.getElementById('asistente-ia-enviar'),
            spinner: d.getElementById('asistente-ia-enviar-spinner'),
            icono: d.getElementById('asistente-ia-enviar-icono'),
            mensajes: d.getElementById('asistente-ia-mensajes'),
            empty: d.getElementById('asistente-ia-empty'),
            error: d.getElementById('asistente-ia-error'),
        };
        return els;
    }

    function _scrollAbajo(el) {
        el.mensajes.scrollTop = el.mensajes.scrollHeight;
    }

    function _ocultarEmptyState(el) {
        if (el.empty) el.empty.classList.add('d-none');
    }

    function _agregarBurbuja(el, texto, claseExtra) {
        var burbuja = d.createElement('div');
        burbuja.className = 'asistente-ia-msg ' + claseExtra;
        burbuja.textContent = texto;
        el.mensajes.appendChild(burbuja);
        return burbuja;
    }

    function _renderDataList(data) {
        var wrap = d.createElement('div');
        data.slice(0, MAX_ITEMS).forEach(function (item) {
            var row = d.createElement('div');
            row.className = 'mb-2 pb-2 border-bottom';
            if (item && typeof item === 'object' && !Array.isArray(item)) {
                var titulo = item.razon_social || item.nombre || item.codigo || item.numero || 'Registro';
                var tituloEl = d.createElement('div');
                tituloEl.className = 'fw-semibold';
                tituloEl.textContent = String(titulo);
                row.appendChild(tituloEl);
                Object.keys(item).forEach(function (k) {
                    if (EXCLUDE_KEYS.indexOf(k) !== -1) return;
                    var v = item[k];
                    if (v === null || v === undefined || v === '' || v === titulo) return;
                    if (typeof v === 'object') return;
                    var line = d.createElement('div');
                    line.className = 'asistente-ia-campo';
                    line.textContent = (FIELD_LABELS[k] || k) + ': ' + v;
                    row.appendChild(line);
                });
            } else {
                row.textContent = String(item);
            }
            wrap.appendChild(row);
        });
        if (data.length > MAX_ITEMS) {
            var mas = d.createElement('div');
            mas.className = 'text-muted';
            mas.textContent = '+ ' + (data.length - MAX_ITEMS) + ' resultado(s) mas.';
            wrap.appendChild(mas);
        }
        if (data.length === 0) {
            var vacio = d.createElement('div');
            vacio.textContent = 'No encontre resultados para esa pregunta.';
            wrap.appendChild(vacio);
        }
        return wrap;
    }

    function _renderFuentes(data) {
        var wrap = d.createElement('div');
        var intro = d.createElement('div');
        intro.className = 'mb-2';
        intro.textContent = data.length
            ? 'Esto encontre relacionado con tu pregunta:'
            : 'No encontre informacion relacionada con tu pregunta.';
        wrap.appendChild(intro);
        data.slice(0, MAX_ITEMS).forEach(function (hit) {
            var box = d.createElement('div');
            box.className = 'asistente-ia-fuentes';
            var contenido = d.createElement('div');
            contenido.textContent = hit.content || '';
            box.appendChild(contenido);
            wrap.appendChild(box);
        });
        return wrap;
    }

    /** Traduce la respuesta OK del orquestador a un nodo legible -- nunca expone tool_used/uuid crudos. */
    function _renderRespuestaOk(body) {
        if (body.status === 'NO_TOOL') {
            var p = d.createElement('div');
            p.textContent = body.message || 'No tengo una respuesta para esa pregunta.';
            return p;
        }
        if (Array.isArray(body.data)) {
            if (body.tool_used === 'buscar_conocimiento') {
                return _renderFuentes(body.data);
            }
            return _renderDataList(body.data);
        }
        var texto = d.createElement('div');
        texto.textContent = body.message || 'Listo.';
        return texto;
    }

    function _mensajeAmigable(status, body) {
        var msg = body && body.message;
        if (Array.isArray(msg)) msg = msg.join(' ');
        if (typeof msg === 'string' && msg.trim()) return msg;
        var porStatus = {
            400: 'No entendi bien la pregunta. Intenta reformularla.',
            401: 'Tu sesion expiro. Vuelve a iniciar sesion.',
            403: 'El asistente no esta disponible en este momento.',
            404: 'No encontre una herramienta para responder eso.',
            409: 'Esa consulta genero un conflicto. Intenta de nuevo.',
            422: 'No pude procesar esa consulta con los datos disponibles.',
            500: 'Ocurrio un error interno. Intenta de nuevo en unos minutos.',
        };
        return porStatus[status] || 'Ocurrio un error inesperado. Intenta de nuevo.';
    }

    function _setCargando(el, cargando) {
        enviando = cargando;
        el.input.disabled = cargando;
        el.enviarBtn.disabled = cargando;
        el.spinner.classList.toggle('d-none', !cargando);
        el.icono.classList.toggle('d-none', cargando);
    }

    async function _enviar(mensaje) {
        var el = _els();
        if (!el || enviando) return;
        mensaje = (mensaje || '').trim();
        if (!mensaje) return;

        el.error.classList.add('d-none');
        el.error.textContent = '';
        _ocultarEmptyState(el);
        _agregarBurbuja(el, mensaje, 'asistente-ia-msg-usuario');
        el.input.value = '';
        _scrollAbajo(el);
        _setCargando(el, true);

        try {
            var res = await w.Sintel.Core.Http.post(ASK_URL, { message: mensaje });
            var body = res.data || {};
            if (res.ok) {
                var nodo = _renderRespuestaOk(body);
                var burbuja = d.createElement('div');
                burbuja.className = 'asistente-ia-msg asistente-ia-msg-asistente';
                burbuja.appendChild(nodo);
                el.mensajes.appendChild(burbuja);
            } else {
                _agregarBurbuja(el, _mensajeAmigable(res.status, body), 'asistente-ia-msg-error');
            }
        } catch (err) {
            _agregarBurbuja(el, 'No se pudo contactar al asistente. Verifica tu conexion.', 'asistente-ia-msg-error');
        } finally {
            _setCargando(el, false);
            _scrollAbajo(el);
            el.input.focus();
        }
    }

    function abrir() {
        var el = _els();
        if (!el) return;
        if (w.Sintel.Core.mostrarOffcanvasSeguro) {
            w.Sintel.Core.mostrarOffcanvasSeguro('offcanvas-asistente-ia');
        }
        setTimeout(function () { el.input && el.input.focus(); }, 200);
    }

    function _init() {
        var el = _els();
        if (!el) return;

        if (el.toggle) {
            el.toggle.addEventListener('click', abrir);
        }

        el.form.addEventListener('submit', function (ev) {
            ev.preventDefault();
            _enviar(el.input.value);
        });

        d.querySelectorAll('#asistente-ia-empty .asistente-ia-ejemplo').forEach(function (btn) {
            btn.addEventListener('click', function () {
                _enviar(btn.textContent);
            });
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.AI = { open: abrir };

})(window, document);
