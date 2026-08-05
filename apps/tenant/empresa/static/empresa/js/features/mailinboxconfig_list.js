// @ts-nocheck
/**
 * Feature: Listado y Tabulator — MailInboxConfig v4.2
 * FSD §7.2: modulo independiente por modelo
 * Namespace: window.MailInboxConfigListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[mailinboxconfig.list]';
    const API_URL = '/api/v1/empresas/mail-inbox-config/';
    const CONTAINER_ID = 'offcanvas-container-mailinbox';
    let table = null;

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(el);
    }

    if (!w.SintelEmpresaTables) w.SintelEmpresaTables = {};

    // ── Columnas Tabulator ────────────────────────────────────────────────────

    function getColumns() {
        return [
            {
                title: 'Nombre',
                field: 'nombre',
                minWidth: 160,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const prov = data.provider === 'gmail'
                        ? '<span class="badge bg-danger-subtle text-danger border border-danger-subtle ms-1 small">Gmail</span>'
                        : '<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle ms-1 small">IMAP</span>';
                    return `<span class="fw-semibold">${cell.getValue() || '—'}</span>${prov}`;
                }
            },
            {
                title: 'Email',
                field: 'email_address',
                minWidth: 180,
                formatter: (cell) => cell.getValue() || '—'
            },
            {
                title: 'Servidor IMAP',
                field: 'imap_host',
                minWidth: 160,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const host = cell.getValue() || '—';
                    const port = data.imap_port ? `:${data.imap_port}` : '';
                    const ssl  = data.imap_ssl
                        ? '<span class="badge bg-success-subtle text-success border border-success-subtle ms-1 small">SSL</span>'
                        : '';
                    return `<code class="small">${host}${port}</code>${ssl}`;
                }
            },
            {
                title: 'Estado',
                field: 'is_active',
                width: 90,
                hozAlign: 'center',
                formatter: (cell) => cell.getValue()
                    ? '<span class="badge bg-success">Activa</span>'
                    : '<span class="badge bg-secondary">Inactiva</span>'
            },
            {
                title: 'Acciones',
                width: 120,
                hozAlign: 'center',
                headerSort: false,
                formatter: (cell) => {
                    const row = cell.getRow().getData();
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary btn-edit-mailinbox" data-id="${row.id}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-delete-mailinbox" data-id="${row.id}" title="Eliminar">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>`;
                }
            }
        ];
    }

    // ── Tabulator ─────────────────────────────────────────────────────────────

    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error(`${MOD} TabulatorFactory no disponible`);
            return;
        }
        const gridEl = d.querySelector('#grid-mailinboxconfig');
        if (!gridEl) {
            console.warn(`${MOD} #grid-mailinboxconfig no encontrado`);
            return;
        }
        if (w.SintelEmpresaTables['mailinboxconfig']) {
            try { w.SintelEmpresaTables['mailinboxconfig'].destroy(); } catch (_) {}
        }
        table = w.TabulatorFactory.create('#grid-mailinboxconfig', API_URL, getColumns(), {
            searchInputSelector: '#search-mailinboxconfig'
        });
        if (table) w.SintelEmpresaTables['mailinboxconfig'] = table;
        return table;
    }

    // ── Eventos de lista (editar / eliminar) ──────────────────────────────────

    function initListEvents() {
        const gridEl = d.querySelector('#grid-mailinboxconfig');
        if (!gridEl) return;

        gridEl.addEventListener('click', async (e) => {
            const btnEdit   = e.target.closest('.btn-edit-mailinbox');
            const btnDelete = e.target.closest('.btn-delete-mailinbox');

            if (btnEdit) {
                e.preventDefault();
                const id = btnEdit.dataset.id;
                btnEdit.disabled = true;
                const prev = btnEdit.innerHTML;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/empresas/mail-inbox-config/render-offcanvas/?id=${id}`, {
                        target: `#${CONTAINER_ID}`,
                        swap: 'innerHTML'
                    });
                    const el = d.getElementById('offcanvas-mailinbox');
                    if (el && w.bootstrap?.Offcanvas) {
                        mostrarOffcanvasSeguro(el);
                    }
                } catch (err) {
                    console.error(`${MOD} Error abriendo editor:`, err);
                    w.SintelFeedback?.error?.('Error al cargar el formulario');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = prev;
                }
            }

            if (btnDelete) {
                e.preventDefault();
                const id = btnDelete.dataset.id;
                if (!id || !confirm('Eliminar esta configuracion de buzon?')) return;
                btnDelete.disabled = true;
                const prev = btnDelete.innerHTML;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.http('DELETE', `/api/v1/empresas/mail-inbox-config/${id}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Configuracion eliminada');
                        d.dispatchEvent(new Event('mailinboxConfigGuardado'));
                    } else {
                        w.SintelFeedback?.error?.(res.data?.error || 'Error al eliminar');
                    }
                } catch (err) {
                    console.error(`${MOD} Error eliminando:`, err);
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = prev;
                }
            }
        });
    }

    // ── Evento: recargar tras guardado ────────────────────────────────────────

    function initEventListeners() {
        d.addEventListener('mailinboxConfigGuardado', () => {
            table?.replaceData?.();
        });
    }

    // ── Abrir offcanvas crear ──────────────────────────────────────────────────

    function abrirCrear() {
        htmx.ajax('GET', '/api/v1/empresas/mail-inbox-config/render-offcanvas/', {
            target: `#${CONTAINER_ID}`,
            swap: 'innerHTML'
        }).then(() => {
            const el = d.getElementById('offcanvas-mailinbox');
            if (el && w.bootstrap?.Offcanvas) {
                mostrarOffcanvasSeguro(el);
            }
        }).catch((err) => console.error(`${MOD} Error abriendo crear:`, err));
    }

    // ── Init ──────────────────────────────────────────────────────────────────

    function init() {
        initTabulator();
        initListEvents();
        initEventListeners();

        const btnCrear = d.getElementById('btn-nuevo-mailinboxconfig');
        if (btnCrear) {
            btnCrear.addEventListener('click', abrirCrear);
        }
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    w.MailInboxConfigListModule = {
        init,
        refresh: () => table?.replaceData?.(),
        abrirCrear,
        getTable: () => table
    };

})(window, document);
