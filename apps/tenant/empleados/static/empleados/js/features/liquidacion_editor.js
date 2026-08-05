// @ts-nocheck
/**
 * Liquidacion Editor — CRUD Liquidaciones de Prestaciones Sociales
 * Namespace: window.Sintel.Empleados.LiquidacionEditor
 * Skills: htmx.md §2 | vanilla-js.md §1, §2 | ui-management.md §26
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD        = '[LiquidacionEditor]';
    const API_BASE   = '/api/v1/empleados/liquidaciones-prestaciones/';
    const API_INFO   = '/api/v1/empleados/devengos/info-empleado/';
    const CONTAINER  = '#offcanvas-container-liquidaciones';
    const OC_ID      = 'offcanvas-liquidacion-crear';
    const FORM_ID    = 'form-liquidacion-crear';
    const BTN_ID     = 'btn-guardar-liquidacion-crear';
    const FEEDBACK   = 'form-liquidacion-crear-feedback';

    const COP = (v) => new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', minimumFractionDigits: 0,
    }).format(parseFloat(v) || 0);

    // ── Abrir offcanvas crear ─────────────────────────────────────────────────
    function open(empleadoUuid) {
        let url = `${API_BASE}render-offcanvas/crear/`;
        if (empleadoUuid) url += `?empleado_uuid=${empleadoUuid}`;
        htmx.ajax('GET', url, { target: CONTAINER, swap: 'innerHTML' });
    }

    // ── Abrir offcanvas detalle (solo lectura) ────────────────────────────────
    function openDetail(uuid) {
        const url = `${API_BASE}${uuid}/render-offcanvas/detalle/`;
        htmx.ajax('GET', url, { target: CONTAINER, swap: 'innerHTML' });
    }

    // ── UIManager (skill: ui-management.md §26) ───────────────────────────────
    function _mostrar(el) {
        if (w.UIManager?.handleOffcanvas) {
            w.UIManager.handleOffcanvas(el, 'show');
        } else {
            d.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
            d.body.classList.remove('overflow-hidden', 'modal-open');
            d.body.style.overflow = '';
            new bootstrap.Offcanvas(el).show();
        }
    }

    function _cerrar() {
        const el = d.getElementById(OC_ID);
        if (!el) return;
        if (w.UIManager?.handleOffcanvas) w.UIManager.handleOffcanvas(el, 'hide');
        else bootstrap.Offcanvas.getInstance(el)?.hide();
    }

    function _mostrarError(msg) {
        const fb = d.getElementById(FEEDBACK);
        if (!fb) return;
        fb.textContent = msg;
        fb.classList.remove('d-none', 'alert-success');
        fb.classList.add('alert-danger');
    }

    // ── Cargar info del empleado seleccionado (skill: vanilla-js.md §2) ───────
    // info-empleado devuelve: { empleado: {id, ...}, contrato: {id, cargo, salario_mensual, ...} }
    async function cargarInfoEmpleado(empleadoId, offcanvasEl) {
        const colInfo = offcanvasEl.querySelector('#col-contrato-info');
        const txtCargo = offcanvasEl.querySelector('#txt-contrato-cargo');
        const txtValores = offcanvasEl.querySelector('#txt-contrato-valores');
        const inputContratoId = offcanvasEl.querySelector('#liquidacion-crear-contrato-id');

        if (!empleadoId) {
            colInfo?.classList.add('d-none');
            if (inputContratoId) inputContratoId.value = '';
            return;
        }

        try {
            // window.http inyecta JWT + CSRF (skill: vanilla-js.md §2)
            const res = await w.http('GET', `${API_INFO}?empleado=${empleadoId}`);
            if (!res.ok) throw new Error(res.data?.error || 'Empleado sin contrato activo');

            const data = res.data;
            const contrato = data.contrato || {};

            // Guardar ID del contrato para POST y UUID para simular
            if (inputContratoId) inputContratoId.value = contrato.id || '';

            // Guardar UUID del contrato como data-attr para simular
            if (inputContratoId) inputContratoId.dataset.uuid = contrato.uuid || '';

            if (txtCargo) txtCargo.textContent = `${contrato.cargo || '—'} (${contrato.tipo || '—'})`;
            if (txtValores) txtValores.textContent = `Salario: ${COP(contrato.salario_mensual)}`;
            colInfo?.classList.remove('d-none');
        } catch (err) {
            console.error(`${MOD} cargarInfoEmpleado:`, err);
            colInfo?.classList.add('d-none');
            if (inputContratoId) { inputContratoId.value = ''; inputContratoId.dataset.uuid = ''; }
            w.UIManager?.notifyError('El empleado seleccionado no tiene un contrato activo.');
        }
    }

    // ── Simular liquidación (skill: vanilla-js.md §2) ─────────────────────────
    async function simularLiquidacion(offcanvasEl) {
        const inputContratoId = offcanvasEl.querySelector('#liquidacion-crear-contrato-id');
        const contratoId  = inputContratoId?.value;
        const contratoUuid = inputContratoId?.dataset?.uuid || '';
        const fechaCorte  = offcanvasEl.querySelector('#liquidacion-crear-fecha-corte')?.value;
        const tipoLiq     = offcanvasEl.querySelector('#liquidacion-crear-tipo')?.value;

        // Nuevos campos
        const diasSalario = offcanvasEl.querySelector('#liquidacion-crear-dias-salario')?.value || 0;
        const indemnizacion = offcanvasEl.querySelector('#liquidacion-crear-indemnizacion')?.value || 0;

        if (!contratoId && !contratoUuid) {
            w.UIManager?.notifyError('Seleccione un empleado con contrato activo.');
            return;
        }
        if (!fechaCorte) {
            w.UIManager?.notifyError('Ingrese la fecha de corte.');
            return;
        }

        const loader  = offcanvasEl.querySelector('#sim-loader-msg');
        const content = offcanvasEl.querySelector('#sim-data-content');

        if (loader) {
            loader.innerHTML = '<span class="spinner-border spinner-border-sm text-info mb-2"></span><span class="text-info"> Calculando...</span>';
            loader.classList.remove('d-none');
        }
        content?.classList.add('d-none');

        try {
            // Preferir UUID (AGENTS.md §14), fallback a ID entero
            const param = contratoUuid ? `contrato_uuid=${contratoUuid}` : `contrato_id=${contratoId}`;
            const url = `${API_BASE}simular/?${param}&fecha_corte=${fechaCorte}&tipo_liquidacion=${tipoLiq}&dias_salario_pendiente=${diasSalario}&indemnizacion=${indemnizacion}`;
            const res = await w.http('GET', url);

            if (!res.ok) throw new Error(res.data?.error || 'Error al calcular simulación');

            const data = res.data;
            const r    = data.resultados || {};

            const set = (id, val) => { const el = offcanvasEl.querySelector(id); if (el) el.textContent = val; };
            set('#sim-val-primas',      COP(r.valor_primas));
            set('#sim-dias-primas',     `${r.dias_primas || 0} días`);
            set('#sim-val-cesantias',   COP(r.valor_cesantias));
            set('#sim-dias-cesantias',  `${r.dias_cesantias || 0} días`);
            set('#sim-val-intereses',   COP(r.valor_intereses));
            set('#sim-dias-intereses',  `${r.dias_intereses || 0} días`);
            set('#sim-val-vacaciones',  COP(r.valor_vacaciones));
            set('#sim-dias-vacaciones', `${r.dias_vacaciones || 0} días`);
            
            // Campos de la liquidación definitiva
            set('#sim-val-salario-base', COP(data.base_salarial));
            set('#sim-val-total-prestaciones', COP(r.total_prestaciones));
            set('#sim-val-total-neto',   COP(r.total_neto));

            // Desglose granular
            set('#sim-dias-salario-pend', `${r.dias_salario_pendiente || 0} días`);
            set('#sim-val-salario-pend', COP(r.salario_pendiente));
            set('#sim-val-indemnizacion', COP(r.indemnizacion));
            set('#sim-val-prestamos-deducidos', COP(r.prestamos_deducidos));

            // Rangos y bases
            set('#sim-rango-primas', r.fecha_inicio_primas && r.fecha_corte ? `${r.fecha_inicio_primas} a ${r.fecha_corte}` : '—');
            set('#sim-rango-cesantias', r.fecha_inicio_cesantias && r.fecha_corte ? `${r.fecha_inicio_cesantias} a ${r.fecha_corte}` : '—');
            set('#sim-rango-intereses', r.fecha_inicio_cesantias && r.fecha_corte ? `${r.fecha_inicio_cesantias} a ${r.fecha_corte}` : '—');
            set('#sim-rango-vacaciones', r.fecha_inicio_vacaciones && r.fecha_corte ? `${r.fecha_inicio_vacaciones} a ${r.fecha_corte}` : '—');

            set('#sim-base-primas', COP(data.base_salarial));
            set('#sim-base-cesantias', COP(data.base_salarial));
            set('#sim-base-intereses', COP(r.valor_cesantias));
            
            // Vacaciones base: salario ordinario únicamente (sin auxilio de transporte si lo tiene)
            // Se calcula restando el auxilio de transporte proporcional o se estima a partir del salario
            const baseSalarial = parseFloat(data.base_salarial) || 0;
            const auxTransporte = baseSalarial > 2000000 ? 0 : 162000; // Estimación o valor base
            set('#sim-base-vacaciones', COP(Math.max(0, baseSalarial - auxTransporte)));

            // Alerta de deudas
            const deudas = parseFloat(r.prestamos_deducidos) || 0;
            const alertDeudas = offcanvasEl.querySelector('#sim-alert-deudas');
            if (deudas > 0) {
                set('#sim-val-deudas-alerta', COP(deudas));
                alertDeudas?.classList.remove('d-none');
            } else {
                alertDeudas?.classList.add('d-none');
            }

            loader?.classList.add('d-none');
            content?.classList.remove('d-none');
        } catch (err) {
            console.error(`${MOD} simularLiquidacion:`, err);
            if (loader) loader.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-danger fs-3 mb-2"></i><span class="text-danger">${err.message}</span>`;
            w.UIManager?.notifyError(err.message || 'Error al calcular simulación.');
        }
    }

    // ── Guardar via window.http (skill: vanilla-js.md §2) ───────────────────
    async function _guardar(offcanvasEl) {
        const form = offcanvasEl.querySelector(`#${FORM_ID}`);
        const btn  = offcanvasEl.querySelector(`#${BTN_ID}`);
        if (!form || !btn) return;
        if (!form.checkValidity()) { form.reportValidity(); return; }

        const fd = new FormData(form);
        const payload = {};
        fd.forEach((val, key) => {
            if (key === 'csrfmiddlewaretoken') return;
            if (val !== '') payload[key] = val;
        });

        // Validacion pre-envio: contrato_id es obligatorio en el backend
        if (!payload.contrato_id) {
            _mostrarError('Debe seleccionar un empleado con contrato activo antes de registrar la liquidación.');
            return;
        }
        if (!payload.fecha_corte) {
            _mostrarError('La fecha de corte es obligatoria.');
            return;
        }

        console.debug(`${MOD} _guardar payload:`, payload);

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

        try {
            const res = await w.http('POST', API_BASE, payload);
            if (res.ok) {
                w.UIManager?.notifySuccess('Liquidación registrada correctamente');
                _cerrar();
                w.Sintel.Empleados.LiquidacionList?.reload();
            } else {
                const errData = res.data || {};
                const msg = errData.detail
                    || Object.values(errData).flat().join(' | ')
                    || 'Error al guardar la liquidación';
                _mostrarError(msg);
                console.error(`${MOD} _guardar 400/error:`, errData);
            }
        } catch (err) {
            console.error(`${MOD} _guardar:`, err);
            _mostrarError('Error de conexión. Inténtelo nuevamente.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Registrar Liquidación';
        }
    }

    // ── Setup del offcanvas recién cargado ────────────────────────────────────
    function _setupOffcanvas(offcanvasEl) {
        // Selector de empleado
        const selectEmp = offcanvasEl.querySelector('#liquidacion-crear-empleado-select');
        if (selectEmp && !selectEmp.dataset.bound) {
            selectEmp.dataset.bound = '1';
            selectEmp.addEventListener('change', (e) => cargarInfoEmpleado(e.target.value, offcanvasEl));
        }

        // Botón simular
        const btnSim = offcanvasEl.querySelector('#btn-simular-liquidacion');
        if (btnSim && !btnSim.dataset.bound) {
            btnSim.dataset.bound = '1';
            btnSim.addEventListener('click', () => simularLiquidacion(offcanvasEl));
        }

        // Botón guardar — reemplaza hx-post por window.http
        const btnGuardar = offcanvasEl.querySelector(`#${BTN_ID}`);
        if (btnGuardar && !btnGuardar.dataset.bound) {
            btnGuardar.dataset.bound = '1';
            btnGuardar.removeAttribute('hx-post');
            btnGuardar.removeAttribute('hx-include');
            btnGuardar.removeAttribute('hx-swap');
            btnGuardar.removeAttribute('hx-target');
            btnGuardar.addEventListener('click', () => _guardar(offcanvasEl));
        }

        // Si el empleado ya viene preseleccionado desde el template Django, cargar su info
        const inputEmpId = offcanvasEl.querySelector('#liquidacion-crear-empleado-id');
        if (inputEmpId?.value) {
            cargarInfoEmpleado(inputEmpId.value, offcanvasEl);
        }
    }

    // ── Escuchar carga HTMX (skill: htmx.md §2) ──────────────────────────────
    // Guard: registrado en `document.body` (persiste entre recargas HTMX del
    // modulo "empleados") — sin este guard, cada recarga del script duplica
    // el listener y `_mostrar`/`_setupOffcanvas` se disparan N veces (FE-A1/A2).
    if (!d.body.dataset.liquidacionEditorInitialized) {
        d.body.dataset.liquidacionEditorInitialized = 'true';

        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail?.target;
            if (!target || target.id !== CONTAINER.replace('#', '')) return;
            const el = target.querySelector('.offcanvas');
            if (!el) return;
            _mostrar(el);
            _setupOffcanvas(el);
        });
    }

    w.Sintel.Empleados.LiquidacionEditor = { open, openDetail };

})(window, document);
