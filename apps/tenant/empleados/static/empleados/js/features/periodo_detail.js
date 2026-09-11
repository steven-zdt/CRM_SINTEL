// @ts-nocheck
/**
 * Periodo Detail — panel de gestion de un Periodo de Nomina (offcanvas
 * estatico #offcanvas-periodo-detalle, contenido renderizado por JS a partir
 * de GET .../resumen/). Muestra el estado actual, los totales agregados y
 * SOLO las acciones validas desde el estado actual (backend es la autoridad
 * real via HasTenantRole/TRANSICIONES_VALIDAS -- este mapa es unicamente
 * para que el usuario entienda que puede hacer ahora, nunca la unica
 * verificacion).
 * Namespace: window.Sintel.Empleados.PeriodoDetail
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[PeriodoDetail]';
    const OC_ID   = 'offcanvas-periodo-detalle';
    const BODY_ID = 'periodo-detalle-body';
    const TITLE_ID = 'periodo-detalle-titulo';

    const ESTADO_BADGE = {
        ABIERTO:      ['bg-primary', 'bi-unlock'],
        PRELIQUIDADO: ['bg-info text-dark', 'bi-calculator'],
        EN_REVISION:  ['bg-warning text-dark', 'bi-eye'],
        APROBADO:     ['bg-info text-dark', 'bi-hand-thumbs-up'],
        PAGADO:       ['bg-success', 'bi-cash-coin'],
        CERRADO:      ['bg-secondary', 'bi-lock'],
        ANULADO:      ['bg-danger', 'bi-x-circle'],
        BLOQUEADO:    ['bg-dark', 'bi-slash-circle'],
    };

    // Acciones ofrecidas por estado -- cada una referencia un builder de URL
    // ya definido en empleados.api.js (SSoT de endpoints).
    const ACCIONES_POR_ESTADO = {
        ABIERTO:      [
            { key: 'preliquidar',      label: 'Preliquidar',          cls: 'btn-primary',        icon: 'bi-calculator' },
            { key: 'bloquear',         label: 'Bloquear',             cls: 'btn-outline-secondary', icon: 'bi-slash-circle' },
            { key: 'anular',           label: 'Anular período',       cls: 'btn-outline-danger', icon: 'bi-x-circle', confirm: '¿Anular este período? Esta acción no se puede deshacer.' },
        ],
        PRELIQUIDADO: [
            { key: 'enviarRevision',   label: 'Enviar a revisión',    cls: 'btn-primary',        icon: 'bi-send' },
            { key: 'bloquear',         label: 'Bloquear',             cls: 'btn-outline-secondary', icon: 'bi-slash-circle' },
            { key: 'anular',           label: 'Anular período',       cls: 'btn-outline-danger', icon: 'bi-x-circle', confirm: '¿Anular este período? Esta acción no se puede deshacer.' },
        ],
        EN_REVISION:  [
            { key: 'aprobar',          label: 'Aprobar',              cls: 'btn-success',        icon: 'bi-hand-thumbs-up' },
            { key: 'rechazarRevision', label: 'Rechazar (volver a preliquidado)', cls: 'btn-outline-warning', icon: 'bi-arrow-counterclockwise' },
            { key: 'bloquear',         label: 'Bloquear',             cls: 'btn-outline-secondary', icon: 'bi-slash-circle' },
            { key: 'anular',           label: 'Anular período',       cls: 'btn-outline-danger', icon: 'bi-x-circle', confirm: '¿Anular este período? Esta acción no se puede deshacer.' },
        ],
        APROBADO:     [
            { key: 'marcarPagado',     label: 'Marcar como pagado',   cls: 'btn-success',        icon: 'bi-cash-coin' },
            { key: 'bloquear',         label: 'Bloquear',             cls: 'btn-outline-secondary', icon: 'bi-slash-circle' },
            { key: 'anular',           label: 'Anular período',       cls: 'btn-outline-danger', icon: 'bi-x-circle', confirm: '¿Anular este período? Esta acción no se puede deshacer.' },
        ],
        PAGADO:       [
            { key: 'cerrar',           label: 'Cerrar período',       cls: 'btn-secondary',      icon: 'bi-lock' },
        ],
        CERRADO:      [],
        ANULADO:      [],
        BLOQUEADO:    [], // manejado aparte -- requiere elegir estado destino
    };

    // mision auditoria nomina "correccion arquitectonica" (2026-09-10):
    // tabs Pendientes/Liquidados (FASE 9-17) -- backend es la UNICA autoridad
    // de quien esta pendiente (EmpleadoSelector.get_empleados_pendientes_
    // para_periodo()), este modulo nunca calcula eso localmente.
    let _periodoActualUuid = null;

    function _money(v) {
        const n = Number(v || 0);
        return n.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
    }

    function _esc(s) {
        return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    async function _cargarTablasEmpleados(uuid) {
        const pendWrap = d.getElementById('periodo-pendientes-body');
        const liqWrap = d.getElementById('periodo-liquidados-body');
        if (!pendWrap || !liqWrap) return;

        const api = w.Sintel.Empleados.API.periodos;
        const [resPend, resLiq] = await Promise.all([
            w.Sintel.Core.Http.request('GET', api.empleadosPendientes(uuid)),
            w.Sintel.Core.Http.request('GET', api.empleadosLiquidados(uuid)),
        ]);

        const countPend = d.getElementById('periodo-tab-pendientes-count');
        const countLiq = d.getElementById('periodo-tab-liquidados-count');

        if (resPend.ok) {
            const rows = resPend.data || [];
            if (countPend) countPend.textContent = rows.length;
            pendWrap.innerHTML = rows.length ? `
                <table class="table table-sm table-hover mb-0">
                  <thead><tr>
                    <th>Empleado</th><th>Documento</th><th>Cargo</th>
                    <th>Tipo contrato</th><th>Fecha ingreso</th><th class="text-end">Acción</th>
                  </tr></thead>
                  <tbody>
                    ${rows.map(e => `
                      <tr>
                        <td>${_esc(e.nombre_completo)}</td>
                        <td>${_esc(e.numero_documento)}</td>
                        <td>${_esc(e.cargo) || '<span class="text-muted">—</span>'}</td>
                        <td>${_esc(e.contrato_tipo)}</td>
                        <td>${_esc(e.fecha_ingreso)}</td>
                        <td class="text-end">
                          <button type="button" class="btn btn-sm btn-primary btn-liquidar-pendiente"
                            data-empleado-uuid="${_esc(e.uuid)}" data-empleado-nombre="${_esc(e.nombre_completo)}">
                            <i class="bi bi-cash-coin me-1"></i>Liquidar
                          </button>
                        </td>
                      </tr>`).join('')}
                  </tbody>
                </table>` : '<p class="text-muted small p-3 mb-0">No hay empleados pendientes en este período.</p>';
        } else {
            pendWrap.innerHTML = '<div class="alert alert-danger m-3">No se pudo cargar la lista de pendientes.</div>';
        }

        if (resLiq.ok) {
            const rows = resLiq.data || [];
            if (countLiq) countLiq.textContent = rows.length;
            liqWrap.innerHTML = rows.length ? `
                <table class="table table-sm table-hover mb-0">
                  <thead><tr>
                    <th>Empleado</th><th>Documento</th><th class="text-end">Días</th>
                    <th class="text-end">Devengado</th><th class="text-end">Deducciones</th><th class="text-end">Neto</th>
                  </tr></thead>
                  <tbody>
                    ${rows.map(dv => `
                      <tr>
                        <td>${_esc(dv.empleado_nombre)}</td>
                        <td>${_esc(dv.empleado_documento)}</td>
                        <td class="text-end">${_esc(dv.dias_laborados)}</td>
                        <td class="text-end">${_money(dv.total_devengado)}</td>
                        <td class="text-end">${_money(dv.total_deducciones)}</td>
                        <td class="text-end fw-semibold text-success">${_money(dv.neto_pagar)}</td>
                      </tr>`).join('')}
                  </tbody>
                </table>` : '<p class="text-muted small p-3 mb-0">Aún no hay empleados liquidados en este período.</p>';
        } else {
            liqWrap.innerHTML = '<div class="alert alert-danger m-3">No se pudo cargar la lista de liquidados.</div>';
        }
    }

    async function refrescarListas(uuid) {
        // mision "correccion arquitectonica" (2026-09-10), FASE 16/29: refresco
        // SELECTIVO del panel (re-fetch + re-render), nunca location.reload()
        // de la pagina completa. Reusa open() -- reabre el offcanvas (se oculto
        // al abrir "Liquidar", ver btn-liquidar-pendiente abajo) ya con datos
        // frescos: contadores Pendientes/Liquidados + ambas tablas.
        const target = uuid || _periodoActualUuid;
        if (!target) return;
        open(target);
    }

    function _mostrar() {
        const el = d.getElementById(OC_ID);
        if (!el) return;
        if (w.UIManager?.handleOffcanvas) {
            w.UIManager.handleOffcanvas(el, 'show');
        } else {
            w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
        }
    }

    function _renderAcciones(periodo) {
        const api = w.Sintel.Empleados.API.periodos;
        const uuid = periodo.uuid;

        if (periodo.estado === 'BLOQUEADO') {
            return `
              <div class="border-top pt-3 mt-3">
                <label class="form-label small fw-semibold text-muted">Desbloquear hacia</label>
                <div class="d-flex gap-2">
                  <select class="form-select form-select-sm" id="periodo-desbloquear-destino" style="max-width:220px;">
                    <option value="ABIERTO">Abierto</option>
                    <option value="PRELIQUIDADO">Preliquidado</option>
                    <option value="EN_REVISION">En revisión</option>
                    <option value="APROBADO">Aprobado</option>
                  </select>
                  <button type="button" class="btn btn-sm btn-primary btn-accion-periodo" data-accion="desbloquear" data-uuid="${uuid}">
                    <i class="bi bi-unlock me-1"></i>Desbloquear
                  </button>
                </div>
              </div>`;
        }

        const acciones = ACCIONES_POR_ESTADO[periodo.estado] || [];
        if (!acciones.length) {
            return '<p class="text-muted small mb-0 mt-3">No hay acciones disponibles desde este estado.</p>';
        }
        const botones = acciones.map(a => `
            <button type="button" class="btn btn-sm ${a.cls} btn-accion-periodo" data-accion="${a.key}" data-uuid="${uuid}"
              ${a.confirm ? `data-confirm="${a.confirm.replace(/"/g, '&quot;')}"` : ''}>
              <i class="bi ${a.icon} me-1"></i>${a.label}
            </button>
        `).join('');
        return `<div class="d-flex flex-wrap gap-2 border-top pt-3 mt-3">${botones}</div>`;
    }

    function _render(data) {
        const periodo = data.periodo;
        const [badgeCls, badgeIcon] = ESTADO_BADGE[periodo.estado] || ['bg-secondary', 'bi-question-circle'];

        d.getElementById(TITLE_ID).textContent = `Período ${periodo.periodo_mes}`;

        const body = d.getElementById(BODY_ID);
        body.innerHTML = `
          <div class="d-flex align-items-center justify-content-between mb-3">
            <span class="badge ${badgeCls} fs-6"><i class="bi ${badgeIcon} me-1"></i>${periodo.estado_display}</span>
            <span class="text-muted small"><i class="bi bi-calendar-range me-1"></i>${periodo.fecha_inicio} → ${periodo.fecha_fin}</span>
          </div>

          <div class="row g-2 mb-3">
            <div class="col-6 col-md-3">
              <div class="border rounded p-2 text-center h-100">
                <div class="text-muted small">Empleados</div>
                <div class="fw-bold">${data.empleados_incluidos ?? 0}</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="border rounded p-2 text-center h-100">
                <div class="text-muted small">Pendientes</div>
                <div class="fw-bold ${data.pendientes ? 'text-warning' : ''}">${data.pendientes ?? 0}</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="border rounded p-2 text-center h-100">
                <div class="text-muted small">Devengado</div>
                <div class="fw-bold">${_money(data.total_devengado)}</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="border rounded p-2 text-center h-100">
                <div class="text-muted small">Neto</div>
                <div class="fw-bold text-success">${_money(data.total_neto)}</div>
              </div>
            </div>
          </div>

          <div class="small mb-3">
            <div><span class="text-muted">Fecha de pago planeada:</span> ${periodo.fecha_pago}</div>
            ${periodo.creado_por_nombre ? `<div><span class="text-muted">Creado por:</span> ${periodo.creado_por_nombre}</div>` : ''}
            ${periodo.aprobado_por_nombre ? `<div><span class="text-muted">Aprobado por:</span> ${periodo.aprobado_por_nombre}</div>` : ''}
            ${periodo.pagado_por_nombre ? `<div><span class="text-muted">Pagado por:</span> ${periodo.pagado_por_nombre}</div>` : ''}
            ${periodo.observaciones ? `<div class="mt-1"><span class="text-muted">Observaciones:</span> ${periodo.observaciones}</div>` : ''}
          </div>

          <ul class="nav nav-tabs nav-tabs-sm" role="tablist">
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-periodo-pendientes" type="button">
              Pendientes <span class="badge bg-warning text-dark ms-1" id="periodo-tab-pendientes-count">…</span>
            </button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-periodo-liquidados" type="button">
              Liquidados <span class="badge bg-success ms-1" id="periodo-tab-liquidados-count">…</span>
            </button></li>
          </ul>
          <div class="tab-content border border-top-0 rounded-bottom mb-3" style="max-height:320px; overflow-y:auto;">
            <div class="tab-pane fade show active" id="tab-periodo-pendientes">
              <div id="periodo-pendientes-body">
                <div class="text-center text-muted p-3 small"><span class="spinner-border spinner-border-sm me-1"></span>Cargando...</div>
              </div>
            </div>
            <div class="tab-pane fade" id="tab-periodo-liquidados">
              <div id="periodo-liquidados-body">
                <div class="text-center text-muted p-3 small"><span class="spinner-border spinner-border-sm me-1"></span>Cargando...</div>
              </div>
            </div>
          </div>

          <div id="periodo-detalle-feedback" class="alert d-none mt-3 mb-0" role="alert"></div>

          ${_renderAcciones(periodo)}
        `;
        body.dataset.uuid = periodo.uuid;
    }

    async function _cargar(uuid) {
        const body = d.getElementById(BODY_ID);
        body.innerHTML = `
          <div class="d-flex flex-column align-items-center justify-content-center py-5 text-muted">
            <i class="bi bi-hourglass-split" style="font-size:1.6rem;"></i>
            <p class="mt-2 small mb-0">Cargando...</p>
          </div>`;
        const res = await w.Sintel.Core.Http.request('GET', w.Sintel.Empleados.API.periodos.resumen(uuid));
        if (res.ok) {
            _render(res.data);
            _cargarTablasEmpleados(uuid);
        } else {
            body.innerHTML = `<div class="alert alert-danger">No se pudo cargar el período: ${res.data?.detail || 'error desconocido'}</div>`;
        }
    }

    function open(uuid) {
        if (!uuid) return;
        _periodoActualUuid = uuid;
        _mostrar();
        _cargar(uuid);
    }

    function _feedback(msg, tipo) {
        const fb = d.getElementById('periodo-detalle-feedback');
        if (!fb) return;
        fb.textContent = msg;
        fb.classList.remove('d-none', 'alert-success', 'alert-danger');
        fb.classList.add(tipo === 'ok' ? 'alert-success' : 'alert-danger');
    }

    async function _ejecutarAccion(accion, uuid, btn) {
        const api = w.Sintel.Empleados.API.periodos;
        const urlBuilder = api[accion];
        if (!urlBuilder) { console.error(`${MOD} Acción desconocida: ${accion}`); return; }

        let payload = undefined;
        if (accion === 'desbloquear') {
            const sel = d.getElementById('periodo-desbloquear-destino');
            payload = { estado_destino: sel?.value };
        }

        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Procesando...';

        try {
            const res = await w.Sintel.Core.Http.request('POST', urlBuilder(uuid), payload);
            if (res.ok) {
                w.UIManager?.notifySuccess('Acción aplicada correctamente');
                w.Sintel.Empleados.PeriodoList?.reload();
                await _cargar(uuid);
            } else {
                const msg = res.data?.detail
                    || (res.data?.estado ? String(res.data.estado) : null)
                    || Object.values(res.data || {}).flat().join(' | ')
                    || 'No se pudo aplicar la acción';
                _feedback(msg, 'error');
                btn.disabled = false;
                btn.innerHTML = original;
            }
        } catch (err) {
            console.error(`${MOD} Error ejecutando ${accion}:`, err);
            _feedback('Error de conexión. Inténtelo nuevamente.', 'error');
            btn.disabled = false;
            btn.innerHTML = original;
        }
    }

    function _attach() {
        const body = d.getElementById(BODY_ID);
        if (!body) return;
        body.addEventListener('click', async (ev) => {
            const btnAccion = ev.target.closest('.btn-accion-periodo');
            if (btnAccion) {
                ev.preventDefault();
                const accion = btnAccion.dataset.accion;
                const uuid = btnAccion.dataset.uuid;
                if (btnAccion.dataset.confirm) {
                    if (!(await w.UIManager?.confirm(btnAccion.dataset.confirm))) return;
                }
                _ejecutarAccion(accion, uuid, btnAccion);
                return;
            }

            // mision "correccion arquitectonica" (2026-09-10), FASE 12: abrir
            // liquidacion individual con empleado + periodo preseleccionados.
            // Se oculta este offcanvas (dos offcanvas .offcanvas-end
            // superpuestos producen backdrops en conflicto) -- se reabre
            // automaticamente al guardar (ver htmx:afterRequest en
            // devengo_editor.js) con los datos ya refrescados.
            const btnLiquidar = ev.target.closest('.btn-liquidar-pendiente');
            if (btnLiquidar) {
                ev.preventDefault();
                const empUuid = btnLiquidar.dataset.empleadoUuid;
                const empNombre = btnLiquidar.dataset.empleadoNombre;
                const periodoUuid = _periodoActualUuid;
                const ocInst = w.bootstrap?.Offcanvas?.getInstance(d.getElementById(OC_ID));
                if (ocInst) ocInst.hide();
                w.Sintel?.Empleados?.DevengoEditor?.openParaEmpleado?.(empUuid, empNombre, periodoUuid);
            }
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', _attach);
    } else {
        _attach();
    }

    w.Sintel.Empleados.PeriodoDetail = { open, refrescarListas };

})(window, document);
