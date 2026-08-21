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

    function _money(v) {
        const n = Number(v || 0);
        return n.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
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
                <div class="text-muted small">Devengado</div>
                <div class="fw-bold">${_money(data.total_devengado)}</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="border rounded p-2 text-center h-100">
                <div class="text-muted small">Deducciones</div>
                <div class="fw-bold">${_money(data.total_deducciones)}</div>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <div class="border rounded p-2 text-center h-100">
                <div class="text-muted small">Neto</div>
                <div class="fw-bold text-success">${_money(data.total_neto)}</div>
              </div>
            </div>
          </div>

          <div class="small">
            <div><span class="text-muted">Fecha de pago planeada:</span> ${periodo.fecha_pago}</div>
            ${periodo.creado_por_nombre ? `<div><span class="text-muted">Creado por:</span> ${periodo.creado_por_nombre}</div>` : ''}
            ${periodo.aprobado_por_nombre ? `<div><span class="text-muted">Aprobado por:</span> ${periodo.aprobado_por_nombre}</div>` : ''}
            ${periodo.pagado_por_nombre ? `<div><span class="text-muted">Pagado por:</span> ${periodo.pagado_por_nombre}</div>` : ''}
            ${periodo.observaciones ? `<div class="mt-1"><span class="text-muted">Observaciones:</span> ${periodo.observaciones}</div>` : ''}
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
        } else {
            body.innerHTML = `<div class="alert alert-danger">No se pudo cargar el período: ${res.data?.detail || 'error desconocido'}</div>`;
        }
    }

    function open(uuid) {
        if (!uuid) return;
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
            const btn = ev.target.closest('.btn-accion-periodo');
            if (!btn) return;
            ev.preventDefault();
            const accion = btn.dataset.accion;
            const uuid = btn.dataset.uuid;
            if (btn.dataset.confirm) {
                if (!(await w.UIManager?.confirm(btn.dataset.confirm))) return;
            }
            _ejecutarAccion(accion, uuid, btn);
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', _attach);
    } else {
        _attach();
    }

    w.Sintel.Empleados.PeriodoDetail = { open };

})(window, document);
