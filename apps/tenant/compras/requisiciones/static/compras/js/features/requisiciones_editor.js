/**
 * Feature: Editor de Requisicion de Compra (crear/editar)
 * Mismo patron que apps/tenant/compras/static/compras/js/features/compras_editor.js
 * pero con items propios de RequisicionCompraItem (tipo_item, cantidad_solicitada,
 * valor_unitario_estimado).
 *
 * PLAN_NUEVA_REQUISICION_FORMULARIO.md: Cotizaciones pasa de "1 origen
 * obligatoria" a 0..N (ninguna obligatoria) via un unico widget "Vincular
 * Cotización" (antes habia un <select> obligatorio + un widget separado
 * para "adicionales"); Proyecto pasa de <select> a widget buscador+tabla
 * (0..1); se agrega "Fecha de Solicitud" editable y columna "Origen" en
 * Items Solicitados.
 */
(function(w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Compras = w.Sintel.Compras || {};

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function crearFilaItem(tbody, item) {
        item = item || {};
        var tr = d.createElement('tr');
        tr.className = 'req-item-row';
        var origenLabel = item.cotizacion_numero
            ? escapeHtml(item.cotizacion_numero)
            : (item.cotizacion_uuid ? '<span class="text-muted">Cotización</span>' : '<span class="text-muted">Manual</span>');
        tr.innerHTML =
            '<td>' +
              '<select class="form-select form-select-sm req-item-tipo">' +
                '<option value="BIEN"' + (item.tipo_item === 'BIEN' ? ' selected' : '') + '>Bien</option>' +
                '<option value="SERVICIO"' + (item.tipo_item === 'SERVICIO' ? ' selected' : '') + '>Servicio</option>' +
              '</select>' +
            '</td>' +
            '<td><input type="text" class="form-control form-control-sm req-item-desc" value="' + escapeHtml(item.descripcion || '') + '" placeholder="Descripcion" required></td>' +
            '<td><input type="number" step="0.01" min="0.01" class="form-control form-control-sm text-end req-item-cantidad" value="' + (item.cantidad_solicitada || 1) + '" required></td>' +
            '<td><input type="number" step="0.01" min="0" class="form-control form-control-sm text-end req-item-valor" value="' + (item.valor_unitario_estimado || 0) + '" required></td>' +
            '<td><input type="number" step="0.01" min="0" class="form-control form-control-sm text-end req-item-iva" value="' + (item.porcentaje_iva || 0) + '"></td>' +
            '<td class="req-item-origen small">' + origenLabel + '</td>' +
            '<td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger btn-quitar-item-req"><i class="bi bi-trash"></i></button></td>';
        // Bookkeeping de UI -- de donde vino esta fila (una de las
        // Cotizaciones vinculadas). recolectarItems() nunca lee `dataset`,
        // asi que esto NUNCA viaja en el payload; solo sirve para poder
        // identificar/quitar/re-sincronizar filas al (des)vincular una
        // cotizacion, y para la columna "Origen" (documento #24).
        if (item.cotizacion_uuid) tr.dataset.cotizacionUuid = item.cotizacion_uuid;
        if (item.cotizacion_item_uuid) tr.dataset.cotizacionItemUuid = item.cotizacion_item_uuid;
        // Fase 6 (PLAN_OPTIMIZACION_COMPRAS...): uuid del item ya persistido
        // (modo edicion, ver poblado de tbody mas abajo) -- recolectarItems()
        // lo reenvia para que el backend sincronice por diferencia.
        if (item.uuid) tr.dataset.itemUuid = item.uuid;
        tbody.appendChild(tr);
        return tr;
    }

    // El tipo_item de CotizacionItem tiene 3 valores (PRODUCTO/"Equipo",
    // MATERIAL, SERVICIO -- no existe "Mano de Obra" como tipo propio, se
    // modela como SERVICIO); RequisicionCompraItem.tipo_item solo admite 2
    // (BIEN/SERVICIO). Fail-safe: cualquier valor inesperado cae a BIEN,
    // nunca se deja vacio (es obligatorio en el backend).
    function mapTipoItemCotizacion(tipoItemCotizacion) {
        return tipoItemCotizacion === 'SERVICIO' ? 'SERVICIO' : 'BIEN';
    }

    // ─── Sincronizacion de Items desde una Cotizacion vinculada ────────────────
    // Al vincular una Cotizacion (widget unico "Vincular Cotización", 0..N),
    // se agrega una fila de "Items Solicitados" por cada CotizacionItem, con
    // Val. Unit. Est. <- costo_unitario (decision de negocio: la Requisicion
    // es un documento de COMPRA, estima lo que la empresa paga al proveedor
    // -- nunca precio_unitario_venta, que incluye margen de venta al
    // cliente) y IVA % <- Cotizacion.iva_porcentaje (a nivel de documento,
    // CotizacionItem no tiene IVA por linea). Es una funcion ADICIONAL: el
    // boton "Agregar Item" manual sigue disponible y sin cambios.

    function agregarItemsDesdeCotizacion(form, cotizacionUuid, cotizacionNumero, cotizacionData, opts) {
        var tbody = form.querySelector('#items-req-tbody');
        var items = (cotizacionData && cotizacionData.items) || [];
        if (!tbody || !items.length) return;

        var forzarResync = !!(opts && opts.forzarResync);
        var existentes = tbody.querySelectorAll('.req-item-row[data-cotizacion-uuid="' + cotizacionUuid + '"]');
        if (existentes.length) {
            if (!forzarResync) return;
            existentes.forEach(function(row) { row.remove(); });
        }

        // Limpia la fila inicial en blanco (agregada por defecto al abrir el
        // formulario) SOLO si sigue vacia -- nunca toca una fila que el
        // usuario ya haya empezado a llenar a mano.
        var filas = tbody.querySelectorAll('.req-item-row');
        if (filas.length === 1) {
            var unica = filas[0];
            var desc = unica.querySelector('.req-item-desc')?.value?.trim();
            var valor = parseFloat(unica.querySelector('.req-item-valor')?.value) || 0;
            if (!desc && !valor) unica.remove();
        }

        var ivaDocumento = parseFloat(cotizacionData.iva_porcentaje) || 0;

        items.forEach(function(it) {
            // descripcion es nullable en CotizacionItem, pero .req-item-desc
            // es required -- sin fallback, recolectarItems() descarta la
            // fila silenciosamente (bug real evitable).
            var desc = (it.descripcion && it.descripcion.trim())
                || [it.tipo_item, it.marca, it.referencia].filter(Boolean).join(' ')
                || 'Item de cotización';

            crearFilaItem(tbody, {
                tipo_item: mapTipoItemCotizacion(it.tipo_item),
                descripcion: desc,
                cantidad_solicitada: it.cantidad,
                valor_unitario_estimado: it.costo_unitario,
                porcentaje_iva: ivaDocumento,
                cotizacion_uuid: cotizacionUuid,
                cotizacion_numero: cotizacionNumero,
                cotizacion_item_uuid: it.uuid,
            });
        });
    }

    // Contraparte: al quitar una cotizacion vinculada, remueve solo las
    // filas que se sincronizaron automaticamente desde ella -- las filas
    // cargadas a mano nunca se tocan.
    function quitarItemsDeCotizacion(form, cotizacionUuid) {
        var tbody = form.querySelector('#items-req-tbody');
        if (!tbody) return;
        tbody.querySelectorAll('.req-item-row[data-cotizacion-uuid="' + cotizacionUuid + '"]').forEach(function(row) { row.remove(); });
    }

    function recolectarItems(tbody) {
        var items = [];
        tbody.querySelectorAll('tr').forEach(function(tr) {
            var desc = tr.querySelector('.req-item-desc')?.value?.trim();
            if (!desc) return;
            var item = {
                tipo_item: tr.querySelector('.req-item-tipo')?.value || 'BIEN',
                descripcion: desc,
                cantidad_solicitada: parseFloat(tr.querySelector('.req-item-cantidad')?.value) || 0,
                valor_unitario_estimado: parseFloat(tr.querySelector('.req-item-valor')?.value) || 0,
                porcentaje_iva: parseFloat(tr.querySelector('.req-item-iva')?.value) || 0,
                unidad_medida: 'UND',
            };
            // Fase 6 (PLAN_OPTIMIZACION_COMPRAS...): reenvia el uuid de las
            // filas ya persistidas (ver crearFilaItem) para sincronizacion
            // diferencial en vez de reemplazar toda la coleccion.
            if (tr.dataset.itemUuid) item.uuid = tr.dataset.itemUuid;
            items.push(item);
        });
        return items;
    }

    // ─── Panel "Sincronizar Cotización" (manual, junto a Agregar Item) ─────────
    // Deja buscar/ver las cotizaciones ya vinculadas (0..N, sin distincion de
    // "origen" para el usuario) y disparar/re-disparar la sincronizacion de
    // sus items hacia "Items Solicitados" bajo demanda. Mismo patron que
    // "Sincronizar Requisición" en compras_editor.js.

    function renderPanelSincronizarCotizacion(offcanvasEl, form, q) {
        var lista = offcanvasEl.querySelector('#sincronizar-cotizacion-lista');
        if (!lista) return;

        var todas = form._cotizacionesVinculadas || [];
        if (!todas.length) {
            lista.innerHTML = '<div class="text-muted p-2">Aún no has vinculado ninguna cotización (usa "Vincular Cotización" en Contexto).</div>';
            return;
        }

        var query = (q || '').trim().toLowerCase();
        var items = query ? todas.filter(function(r) { return (r.numero || '').toLowerCase().indexOf(query) !== -1; }) : todas;

        if (!items.length) {
            lista.innerHTML = '<div class="text-muted p-2">Sin resultados.</div>';
            return;
        }

        var tbody = offcanvasEl.querySelector('#items-req-tbody');
        lista.innerHTML = items.map(function(r) {
            var sincronizada = !!(tbody && tbody.querySelector('.req-item-row[data-cotizacion-uuid="' + r.uuid + '"]'));
            return (
                '<div class="d-flex align-items-center justify-content-between border-bottom py-2 px-1">' +
                  '<div>' +
                    '<div class="fw-semibold">' + escapeHtml(r.numero) + '</div>' +
                    (sincronizada ? '<div class="text-success" style="font-size:0.78rem;">Sincronizada</div>' : '') +
                  '</div>' +
                  '<button type="button" class="btn btn-sm ' + (sincronizada ? 'btn-outline-secondary' : 'btn-primary') + ' flex-shrink-0" ' +
                          'data-sincronizar-cotizacion-uuid="' + r.uuid + '" data-sincronizar-cotizacion-numero="' + escapeHtml(r.numero) + '">' +
                    (sincronizada ? 'Re-sincronizar' : 'Sincronizar') +
                  '</button>' +
                '</div>'
            );
        }).join('');
    }

    async function ejecutarSincronizacionCotizacion(offcanvasEl, form, cotizacionUuid, cotizacionNumero) {
        var API = w.Sintel?.Compras?.API;
        var detalle = await API.cotizaciones.get(cotizacionUuid);
        var items = (detalle && detalle.items) || [];
        if (!items.length) {
            w.UIManager?.notifyError?.('Esta cotización no tiene items para sincronizar.');
            return;
        }
        agregarItemsDesdeCotizacion(form, cotizacionUuid, cotizacionNumero, detalle, { forzarResync: true });
        w.UIManager?.notifySuccess?.('Items Solicitados sincronizados desde la cotización.');
    }

    // ─── Widget único "Vincular Cotización" (0..N, PLAN_NUEVA_REQUISICION_ ────
    // FORMULARIO.md #10/#11) ─────────────────────────────────────────────────
    // Reemplaza el <select> obligatorio + el widget separado de
    // "adicionales" de la fase anterior. Busca sobre
    // API.requisiciones.cotizacionesDisponibles() (filtrado en BACKEND --
    // excluye cotizaciones ya vinculadas a CUALQUIER requisicion, documento
    // #12) y se acumulan localmente en `form._cotizacionesVinculadas` (la
    // Requisicion aun no existe) -- se envian TODAS juntas en el payload de
    // creacion (`cotizaciones: [...]`), validadas atomicamente por el
    // backend (exclusividad + coherencia de Cliente, con select_for_update
    // para cerrar la condicion de carrera) -- no hay vinculacion diferida
    // post-creacion para cotizaciones en este formulario.

    function renderCotizacionesVinculadas(offcanvasEl, form) {
        var contenedor = offcanvasEl.querySelector('#req-cotizacion-lista');
        if (!contenedor) return;
        var vinculadas = form._cotizacionesVinculadas || [];
        if (!vinculadas.length) {
            contenedor.innerHTML = '<div class="text-muted small mb-2">Sin cotizaciones vinculadas.</div>';
            return;
        }
        contenedor.innerHTML = vinculadas.map(function(c) {
            return (
                '<div class="d-flex align-items-center justify-content-between border rounded p-2 mb-2">' +
                  '<div>' +
                    '<div class="fw-semibold">' + escapeHtml(c.numero) + '</div>' +
                    '<div class="text-muted small">' + escapeHtml(c.cliente || '') + (c.total ? ' · ' + escapeHtml(c.total) : '') + '</div>' +
                  '</div>' +
                  '<button type="button" class="btn btn-outline-danger btn-sm" data-req-cotizacion-quitar="' + c.uuid + '">' +
                    '<i class="bi bi-x-lg"></i>' +
                  '</button>' +
                '</div>'
            );
        }).join('');
    }

    function renderResultadosCotizacion(offcanvasEl, form, q) {
        // #req-cotizacion-buscar-resultados vive DENTRO del modal, que a
        // proposito esta FUERA de .offcanvas (ver comentario junto al
        // boton que lo abre) -- offcanvasEl.querySelector() no lo
        // encontraria (solo busca descendientes), por eso `d` (document).
        var resultados = d.getElementById('req-cotizacion-buscar-resultados');
        if (!resultados) return;
        var cache = form._cotizacionesDisponiblesCache;
        if (!cache) return; // primera carga aun en curso

        var vinculadasUuids = (form._cotizacionesVinculadas || []).map(function(c) { return c.uuid; });
        var items = cache.filter(function(c) { return vinculadasUuids.indexOf(c.uuid) === -1; });

        q = (q || '').trim().toLowerCase();
        if (q) {
            items = items.filter(function(c) {
                var numero = (c.numero_cotizacion || '').toLowerCase();
                var cliente = (c.cliente_nombre || '').toLowerCase();
                return numero.indexOf(q) !== -1 || cliente.indexOf(q) !== -1;
            });
        }

        if (!items.length) {
            resultados.innerHTML = '<div class="text-muted p-2">' + (cache.length ? 'Sin resultados.' : 'No hay cotizaciones disponibles (todas ya están vinculadas a alguna requisición).') + '</div>';
            return;
        }

        // Seleccion MULTIPLE via checkbox -- el estado marcado/desmarcado
        // vive en form._cotizacionesModalMarcadas (independiente del cache
        // de resultados, asi que sobrevive a un re-render por busqueda).
        var marcadas = form._cotizacionesModalMarcadas || {};
        resultados.innerHTML = items.map(function(c) {
            var cliente = c.cliente_nombre || 'Sin cliente';
            var checked = !!marcadas[c.uuid];
            return (
                '<label class="d-flex align-items-center border-bottom py-2 px-1 mb-0" style="cursor:pointer;">' +
                  '<input type="checkbox" class="form-check-input req-cotizacion-checkbox me-2 flex-shrink-0" ' +
                         'data-uuid="' + c.uuid + '" data-numero="' + escapeHtml(c.numero_cotizacion) + '" ' +
                         'data-cliente="' + escapeHtml(cliente) + '"' + (checked ? ' checked' : '') + '>' +
                  '<span>' +
                    '<span class="fw-semibold d-block">' + escapeHtml(c.numero_cotizacion) + '</span>' +
                    '<span class="text-muted d-block" style="font-size:0.78rem;">' + escapeHtml(cliente) + '</span>' +
                  '</span>' +
                '</label>'
            );
        }).join('');
    }

    // ─── Widget "Vincular Proyecto" (0..1, PLAN_NUEVA_REQUISICION_FORMULARIO ──
    // .md #17-20) ────────────────────────────────────────────────────────────
    // Mismo patron visual/JS que Cotizaciones, pero 0..1 real (FK directa
    // RequisicionCompra.proyecto, sin exclusividad -- el mismo Proyecto
    // puede estar en muchas Requisiciones). Reemplaza el <select> anterior;
    // disponible en creacion Y edicion.

    // Fase 4 (PLAN_OPTIMIZACION_COMPRAS...): busqueda bajo demanda real --
    // antes precargaba UNA vez `/api/v1/proyectos/` (paginado 20 por
    // defecto, StandardResultsSetPagination) y filtraba client-side sobre
    // esa unica pagina -- un Proyecto fuera de los primeros 20 de la
    // empresa era literalmente imposible de seleccionar aqui (mismo bug
    // real ya corregido en offcanvas_crear/editar_compras.html). Ahora cada
    // tecla dispara `?search=` contra el backend (ver wiring en
    // initRequisicionForm, debounce 300ms).
    function renderResultadosProyecto(offcanvasEl, items) {
        var resultados = offcanvasEl.querySelector('#req-proyecto-buscar-resultados');
        if (!resultados) return;

        if (!items.length) {
            resultados.innerHTML = '<div class="text-muted p-2">Sin resultados.</div>';
            return;
        }

        resultados.innerHTML = items.map(function(p) {
            var uuid = p.uuid || p.id;
            return (
                '<div class="d-flex align-items-center justify-content-between border-bottom py-2 px-1">' +
                  '<div class="fw-semibold">' + escapeHtml(p.nombre || p.codigo || '') + '</div>' +
                  '<button type="button" class="btn btn-sm btn-primary flex-shrink-0" ' +
                          'data-req-proyecto-uuid="' + uuid + '" data-req-proyecto-nombre="' + escapeHtml(p.nombre || '') + '">' +
                    'Seleccionar' +
                  '</button>' +
                '</div>'
            );
        }).join('');
    }

    function renderProyectoVinculado(offcanvasEl, uuid, nombre) {
        var lista = offcanvasEl.querySelector('#req-proyecto-lista');
        var hidden = offcanvasEl.querySelector('#req-proyecto-uuid');
        var btnMostrar = offcanvasEl.querySelector('#btn-mostrar-buscador-proyecto');
        if (hidden) hidden.value = uuid || '';
        if (btnMostrar) btnMostrar.classList.toggle('d-none', !!uuid);
        if (!lista) return;
        if (!uuid) {
            lista.innerHTML = '<div class="text-muted small mb-2" id="req-proyecto-vacio">Sin proyecto asociado.</div>';
            return;
        }
        lista.innerHTML =
            '<div class="d-flex align-items-center justify-content-between border rounded p-2 mb-2" data-proyecto-uuid="' + uuid + '">' +
              '<div class="fw-semibold">' + escapeHtml(nombre) + '</div>' +
              '<button type="button" class="btn btn-outline-danger btn-sm" data-req-proyecto-action="quitar">' +
                '<i class="bi bi-x-lg"></i>' +
              '</button>' +
            '</div>';
    }

    function initRequisicionForm(offcanvasEl) {
        var API = w.Sintel?.Compras?.API;
        if (!API) return;

        var form = offcanvasEl.querySelector('#requisicion-crear-form');
        if (!form) return;

        // Idempotencia (bug real encontrado en pruebas manuales, 2026-09-28):
        // requisiciones_list.js llama initRequisicionForm() en cada
        // htmx:afterSettle sobre #offcanvas-container-requisiciones -- ese
        // evento puede disparar mas de una vez para el mismo DOM (patron ya
        // conocido de htmx). Sin este guard, TODOS los listeners de abajo
        // quedaban atados dos veces, y un solo click/seleccion producia
        // filas e items duplicados. Mismo guard ya usado en
        // compras_editor.js::initializeEditor.
        if (form.dataset.editorInitialized) return;
        form.dataset.editorInitialized = 'true';

        var modo = form.getAttribute('data-mode') || 'create';
        var requisicionUuid = form.getAttribute('data-uuid');
        var feedbackEl = offcanvasEl.querySelector('#form-requisicion-crear-feedback');
        var tbody = offcanvasEl.querySelector('#items-req-tbody');
        var btnAgregar = offcanvasEl.querySelector('#btn-agregar-item-req');
        var btnGuardar = offcanvasEl.querySelector('#btn-guardar-requisicion');

        form._cotizacionesVinculadas = form._cotizacionesVinculadas || [];

        // ── Proyecto (0..1, buscador+tabla) -- creacion Y edicion ──────────
        var btnMostrarBuscadorProyecto = offcanvasEl.querySelector('#btn-mostrar-buscador-proyecto');
        var panelBuscadorProyecto = offcanvasEl.querySelector('#req-proyecto-buscador-panel');
        var inputBuscarProyecto = offcanvasEl.querySelector('#req-proyecto-buscar-input');
        var resultadosProyectoEl = offcanvasEl.querySelector('#req-proyecto-buscar-resultados');
        var listaProyectoEl = offcanvasEl.querySelector('#req-proyecto-lista');

        var _proyectoBuscarTimer = null;
        if (btnMostrarBuscadorProyecto && panelBuscadorProyecto) {
            btnMostrarBuscadorProyecto.addEventListener('click', function(e) {
                e.preventDefault();
                panelBuscadorProyecto.classList.remove('d-none');
                if (inputBuscarProyecto) inputBuscarProyecto.focus();
                if (resultadosProyectoEl) {
                    resultadosProyectoEl.innerHTML = '<div class="text-muted p-2">Escribe 2+ caracteres para buscar.</div>';
                }
            });
        }
        if (inputBuscarProyecto && resultadosProyectoEl) {
            inputBuscarProyecto.addEventListener('input', function() {
                var q = inputBuscarProyecto.value.trim();
                if (_proyectoBuscarTimer) clearTimeout(_proyectoBuscarTimer);
                if (q.length < 2) {
                    resultadosProyectoEl.innerHTML = '<div class="text-muted p-2">Escribe 2+ caracteres para buscar.</div>';
                    return;
                }
                _proyectoBuscarTimer = setTimeout(function() {
                    w.Sintel.Compras.Utils.fetchProyectos(q).then(function(items) {
                        renderResultadosProyecto(offcanvasEl, items || []);
                    });
                }, 300);
            });
        }
        if (resultadosProyectoEl) {
            resultadosProyectoEl.addEventListener('click', function(e) {
                var btn = e.target.closest('[data-req-proyecto-uuid]');
                if (!btn) return;
                e.preventDefault();
                var uuid = btn.getAttribute('data-req-proyecto-uuid');
                var nombre = btn.getAttribute('data-req-proyecto-nombre') || uuid;
                renderProyectoVinculado(offcanvasEl, uuid, nombre);
                if (panelBuscadorProyecto) panelBuscadorProyecto.classList.add('d-none');
            });
        }
        if (listaProyectoEl) {
            listaProyectoEl.addEventListener('click', function(e) {
                var btn = e.target.closest('[data-req-proyecto-action="quitar"]');
                if (!btn) return;
                e.preventDefault();
                renderProyectoVinculado(offcanvasEl, null, null);
            });
        }

        if (modo !== 'edit') {
            // Plantilla de Numeración (obligatoria): preview del numero a
            // asignar -- mismo patron que actualizarInfoPlantilla() en
            // compras_editor.js, options ya vienen con
            // data-prefijo/data-actual/data-hasta desde el template.
            var selectPlantillaReq = offcanvasEl.querySelector('#req-plantilla');
            var infoPlantillaReq = offcanvasEl.querySelector('#req-plantilla-info');
            function actualizarInfoPlantillaReq() {
                if (!selectPlantillaReq || !infoPlantillaReq) return;
                if (!selectPlantillaReq.value) {
                    infoPlantillaReq.textContent = '';
                    infoPlantillaReq.className = 'form-text mt-1 text-muted';
                    return;
                }
                var opt = selectPlantillaReq.options[selectPlantillaReq.selectedIndex];
                if (!opt) return;
                var prefijo = opt.getAttribute('data-prefijo') || '';
                var actual = parseInt(opt.getAttribute('data-actual'), 10) || 1;
                var hasta = parseInt(opt.getAttribute('data-hasta'), 10) || 0;
                var proxNum = prefijo ? (prefijo + '-' + actual) : String(actual);
                // Fase 10 (PLAN_OPTIMIZACION_COMPRAS...): "estimado", no "a
                // asignar" -- preview client-side, la reserva real ocurre en
                // el backend compartido (_dsv_y_asignar_plantilla) al guardar.
                var msg = 'Próximo número estimado: ' + proxNum;
                var textClass = 'text-muted';
                if (hasta > 0) {
                    var disponibles = hasta - actual + 1;
                    if (disponibles <= 0) {
                        msg = '¡Plantilla Agotada! Límite: ' + hasta + '.';
                        textClass = 'text-danger fw-bold';
                    } else if (disponibles <= 5) {
                        msg = 'Próximo número estimado: ' + proxNum + ' (Próxima a agotarse, quedan ' + disponibles + ')';
                        textClass = 'text-warning fw-semibold';
                    } else {
                        msg = 'Próximo número estimado: ' + proxNum + ' (Rango hasta ' + hasta + ')';
                    }
                }
                infoPlantillaReq.textContent = msg;
                infoPlantillaReq.className = 'form-text mt-1 ' + textClass;
            }
            if (selectPlantillaReq) {
                selectPlantillaReq.addEventListener('change', actualizarInfoPlantillaReq);
                actualizarInfoPlantillaReq();
            }

            // ── Cotizaciones (0..N, modal de selección múltiple) ────────────
            // Mejora pedida por el usuario (2026-09-28): el buscador ya no es
            // un panel inline -- es un modal Bootstrap real con checkboxes,
            // que deja marcar una o varias cotizaciones y transportarlas
            // TODAS juntas al formulario con "Agregar Seleccionadas" (se
            // cierra solo), o "Cancelar" sin tocar nada.
            // El modal (y todo lo que vive dentro de el: buscador,
            // resultados, contador, boton confirmar) esta a proposito
            // FUERA de .offcanvas -- se busca por `d` (document), nunca
            // por offcanvasEl.querySelector() (solo ve descendientes).
            // Solo el boton disparador y la lista de vinculadas siguen
            // dentro del offcanvas (viven en la seccion "Contexto").
            var modalCotEl = d.getElementById('modal-vincular-cotizacion');
            var btnMostrarModalCot = offcanvasEl.querySelector('#btn-mostrar-modal-cotizacion');
            var inputBuscarCot = d.getElementById('req-cotizacion-buscar-input');
            var resultadosCotEl = d.getElementById('req-cotizacion-buscar-resultados');
            var listaCotEl = offcanvasEl.querySelector('#req-cotizacion-lista');
            var contadorModalCot = d.getElementById('req-cotizacion-modal-contador');
            var btnAgregarSeleccionadas = d.getElementById('btn-agregar-cotizaciones-seleccionadas');

            form._cotizacionesModalMarcadas = form._cotizacionesModalMarcadas || {};

            function actualizarContadorModalCot() {
                var n = Object.keys(form._cotizacionesModalMarcadas).length;
                if (contadorModalCot) contadorModalCot.textContent = n + (n === 1 ? ' seleccionada' : ' seleccionadas');
                if (btnAgregarSeleccionadas) btnAgregarSeleccionadas.disabled = (n === 0);
            }

            if (btnMostrarModalCot && modalCotEl) {
                btnMostrarModalCot.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (!form._cotizacionesDisponiblesCache) {
                        API.requisiciones.cotizacionesDisponibles().then(function(items) {
                            form._cotizacionesDisponiblesCache = items || [];
                            renderResultadosCotizacion(offcanvasEl, form, inputBuscarCot ? inputBuscarCot.value : '');
                        }).catch(function(err) {
                            console.warn('[RequisicionEditor] No se pudo cargar cotizaciones disponibles:', err);
                            if (resultadosCotEl) resultadosCotEl.innerHTML = '<div class="text-danger p-2">Error al cargar cotizaciones disponibles.</div>';
                        });
                    } else {
                        renderResultadosCotizacion(offcanvasEl, form, inputBuscarCot ? inputBuscarCot.value : '');
                    }
                    if (w.bootstrap?.Modal) {
                        w.bootstrap.Modal.getOrCreateInstance(modalCotEl).show();
                    }
                });

                // Al cerrarse el modal (Cancelar, X, backdrop, ESC o tras
                // confirmar) siempre arranca "limpio" la proxima vez -- las
                // marcas no confirmadas se descartan, mismo criterio que
                // cualquier dialogo de seleccion estandar.
                modalCotEl.addEventListener('hidden.bs.modal', function() {
                    form._cotizacionesModalMarcadas = {};
                    if (inputBuscarCot) inputBuscarCot.value = '';
                    actualizarContadorModalCot();
                });
            }

            if (inputBuscarCot) {
                inputBuscarCot.addEventListener('input', function() {
                    renderResultadosCotizacion(offcanvasEl, form, inputBuscarCot.value);
                });
            }

            if (resultadosCotEl) {
                resultadosCotEl.addEventListener('change', function(e) {
                    var chk = e.target.closest('.req-cotizacion-checkbox');
                    if (!chk) return;
                    var uuid = chk.getAttribute('data-uuid');
                    if (chk.checked) {
                        form._cotizacionesModalMarcadas[uuid] = {
                            uuid: uuid,
                            numero: chk.getAttribute('data-numero') || uuid,
                            cliente: chk.getAttribute('data-cliente') || '',
                        };
                    } else {
                        delete form._cotizacionesModalMarcadas[uuid];
                    }
                    actualizarContadorModalCot();
                });
            }

            if (btnAgregarSeleccionadas) {
                btnAgregarSeleccionadas.addEventListener('click', function(e) {
                    e.preventDefault();
                    var marcadas = Object.values(form._cotizacionesModalMarcadas);
                    if (!marcadas.length) return;

                    marcadas.forEach(function(c) {
                        form._cotizacionesVinculadas.push(c);
                        // Sincroniza items de inmediato (best-effort visual --
                        // la validacion real de exclusividad/coherencia ocurre
                        // en el backend al enviar el formulario completo).
                        API.cotizaciones.get(c.uuid).then(function(detalle) {
                            agregarItemsDesdeCotizacion(form, c.uuid, c.numero, detalle);
                        }).catch(function(err) {
                            console.warn('[RequisicionEditor] No se pudo sincronizar items desde la cotización:', err);
                            w.UIManager?.notifyError?.('Cotización "' + c.numero + '" agregada, pero no se pudo sincronizar su detalle de items.');
                        });
                    });
                    renderCotizacionesVinculadas(offcanvasEl, form);
                    // `hidden.bs.modal` (arriba) ya limpia _cotizacionesModalMarcadas.
                    if (w.bootstrap?.Modal) {
                        w.bootstrap.Modal.getInstance(modalCotEl)?.hide();
                    }
                });
            }

            if (listaCotEl) {
                listaCotEl.addEventListener('click', function(e) {
                    var btn = e.target.closest('[data-req-cotizacion-quitar]');
                    if (!btn) return;
                    e.preventDefault();
                    var uuid = btn.getAttribute('data-req-cotizacion-quitar');
                    form._cotizacionesVinculadas = form._cotizacionesVinculadas.filter(function(c) { return c.uuid !== uuid; });
                    renderCotizacionesVinculadas(offcanvasEl, form);
                    quitarItemsDeCotizacion(form, uuid);
                });
            }

            renderCotizacionesVinculadas(offcanvasEl, form);

            // Panel manual "Sincronizar Cotización" (junto a Agregar Item).
            var btnSincronizarCot = offcanvasEl.querySelector('#btn-sincronizar-cotizacion');
            var panelSincronizarCot = offcanvasEl.querySelector('#sincronizar-cotizacion-panel');
            if (btnSincronizarCot && panelSincronizarCot) {
                btnSincronizarCot.addEventListener('click', function(e) {
                    e.preventDefault();
                    var abierto = !panelSincronizarCot.classList.contains('d-none');
                    if (abierto) {
                        panelSincronizarCot.classList.add('d-none');
                    } else {
                        panelSincronizarCot.classList.remove('d-none');
                        renderPanelSincronizarCotizacion(offcanvasEl, form, '');
                    }
                });

                var btnCerrarPanelCot = panelSincronizarCot.querySelector('#btn-cerrar-sincronizar-cotizacion');
                if (btnCerrarPanelCot) {
                    btnCerrarPanelCot.addEventListener('click', function(e) {
                        e.preventDefault();
                        panelSincronizarCot.classList.add('d-none');
                    });
                }

                var inputBuscarSyncCot = panelSincronizarCot.querySelector('#sincronizar-cotizacion-buscar-input');
                if (inputBuscarSyncCot) {
                    inputBuscarSyncCot.addEventListener('input', function() {
                        renderPanelSincronizarCotizacion(offcanvasEl, form, inputBuscarSyncCot.value);
                    });
                }

                panelSincronizarCot.addEventListener('click', function(e) {
                    var btnSync = e.target.closest('[data-sincronizar-cotizacion-uuid]');
                    if (!btnSync) return;
                    e.preventDefault();
                    var uuid = btnSync.getAttribute('data-sincronizar-cotizacion-uuid');
                    var numero = btnSync.getAttribute('data-sincronizar-cotizacion-numero') || uuid;
                    btnSync.disabled = true;
                    ejecutarSincronizacionCotizacion(offcanvasEl, form, uuid, numero).then(function() {
                        renderPanelSincronizarCotizacion(offcanvasEl, form, inputBuscarSyncCot ? inputBuscarSyncCot.value : '');
                    }).catch(function(err) {
                        console.warn('[RequisicionEditor] Error al sincronizar items desde cotizacion:', err);
                        w.UIManager?.notifyError?.('No se pudo sincronizar el detalle de items de la cotización.');
                    }).finally(function() {
                        btnSync.disabled = false;
                    });
                });
            }
        }

        if (modo === 'edit' && tbody.children.length === 0) {
            // Los items existentes llegan via el detalle (fetch) cuando se edita.
            API.requisiciones.detail(requisicionUuid).then(function(data) {
                (data.items || []).forEach(function(item) { crearFilaItem(tbody, item); });
            }).catch(function(err) { console.error('[RequisicionEditor] Error cargando items:', err); });
        } else if (tbody.children.length === 0) {
            crearFilaItem(tbody, {});
        }

        if (btnAgregar) {
            btnAgregar.addEventListener('click', function() { crearFilaItem(tbody, {}); });
        }

        tbody.addEventListener('click', function(e) {
            var btn = e.target.closest('.btn-quitar-item-req');
            if (!btn) return;
            var rows = tbody.querySelectorAll('tr');
            if (rows.length <= 1) return;
            btn.closest('tr').remove();
        });

        function showError(msg) {
            if (!feedbackEl) return;
            feedbackEl.textContent = msg;
            feedbackEl.classList.remove('d-none');
        }
        function hideError() {
            if (!feedbackEl) return;
            feedbackEl.classList.add('d-none');
            feedbackEl.textContent = '';
        }

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            hideError();

            var items = recolectarItems(tbody);
            if (!items.length) { showError('Debe existir al menos un item solicitado.'); return; }

            var esEdicion = (modo === 'edit');

            var payload = {
                fecha_solicitud: offcanvasEl.querySelector('#req-fecha-solicitud')?.value,
                fecha_necesidad: offcanvasEl.querySelector('#req-fecha-necesidad')?.value,
                tipo: offcanvasEl.querySelector('#req-tipo')?.value,
                prioridad: offcanvasEl.querySelector('#req-prioridad')?.value,
                justificacion: offcanvasEl.querySelector('#req-justificacion')?.value?.trim(),
                observaciones: offcanvasEl.querySelector('#req-observaciones')?.value?.trim() || '',
                proyecto: offcanvasEl.querySelector('#req-proyecto-uuid')?.value || null,
                items: items,
            };

            if (!payload.fecha_solicitud) { showError('Debe indicar la fecha de solicitud.'); return; }

            // Cliente: obligatorio en creacion Y edicion (documento #5) --
            // a diferencia de Cotizacion/Plantilla, se puede reemplazar en
            // BORRADOR, asi que siempre se envia.
            var clienteUuid = offcanvasEl.querySelector('#req-cliente')?.value;
            if (!clienteUuid) { showError('Debe seleccionar el cliente.'); return; }
            payload.cliente = clienteUuid;

            if (!esEdicion) {
                // Plantilla: obligatoria SOLO al crear -- nunca se
                // reemplaza en edicion (documento #22, numero_documento
                // readonly).
                var plantillaUuid = offcanvasEl.querySelector('#req-plantilla')?.value;
                if (!plantillaUuid) { showError('Debe seleccionar la plantilla de numeración.'); return; }
                payload.plantilla = plantillaUuid;

                // Cotizaciones: 0..N, ninguna obligatoria (documento #1) --
                // TODAS se envian juntas en el mismo payload de creacion;
                // el backend las valida atomicamente (exclusividad +
                // coherencia de Cliente) -- si alguna falla, no se crea
                // nada (nunca queda una Requisicion parcial).
                payload.cotizaciones = form._cotizacionesVinculadas.map(function(c) { return c.uuid; });
            }
            if (btnGuardar) { btnGuardar.disabled = true; btnGuardar.textContent = esEdicion ? 'Guardando...' : 'Creando...'; }

            try {
                if (esEdicion) {
                    await API.requisiciones.update(requisicionUuid, payload);
                } else {
                    await API.requisiciones.create(payload);
                }
                var bsInstance = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
                if (bsInstance) bsInstance.hide();
                d.body.dispatchEvent(new CustomEvent('requisicion-changed'));
                w.UIManager?.notifySuccess?.(esEdicion ? 'Requisición actualizada correctamente' : 'Requisición creada correctamente');
            } catch (err) {
                var data = err.data || {};
                var msgs = Object.values(data).flat().join(' ') || ('Error ' + (err.status || ''));
                showError(msgs);
                console.error('[RequisicionEditor] Error guardando:', err);
            } finally {
                if (btnGuardar) {
                    btnGuardar.disabled = false;
                    btnGuardar.textContent = esEdicion ? 'Guardar Cambios' : 'Crear Requisición';
                }
            }
        });
    }

    w.Sintel.Compras.initRequisicionForm = initRequisicionForm;

})(window, document);
