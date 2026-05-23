// @ts-nocheck
/**
 * Devengo Editor Module — Formulario Unificado de Nomina v4.0
 * Feature-Sliced Architecture
 *
 * Flujo unico: selector empleado + periodo + campos completos en un solo paso.
 * Namespace: window.Sintel.Empleados.DevengoEditor
 */
(function(w, d) {
    'use strict';

    const MOD          = '[DevengoEditor]';
    const API_URL      = '/api/v1/empleados/';
    const CONTAINER_ID = 'offcanvas-container-nominas';

    // ── Abrir formulario unificado ────────────────────────────────────────────

    async function open() {
        const url = `${API_URL}devengos/render-offcanvas/crear/`;
        console.log(`${MOD} Abriendo formulario unificado: ${url}`);
        try {
            await htmx.ajax('GET', url, { target: `#${CONTAINER_ID}`, swap: 'innerHTML' });
        } catch (err) {
            console.error(`${MOD} Error cargando formulario:`, err);
            w.UIManager?.notifyError('Error al cargar el formulario de nómina');
        }
    }

    // ── Helpers numéricos seguros (FASE 3) ───────────────────────────────────

    /**
     * Calcula días entre dos fechas ISO (inclusive en ambos extremos).
     * Usa T00:00:00 local para evitar ambigüedad UTC.
     * Math.round absorbe el edge-case de DST (Colombia no tiene DST, pero es defensivo).
     */
    function calcularDias(fi, ff) {
        if (!fi || !ff) return 0;
        const start = new Date(fi + 'T00:00:00');
        const end   = new Date(ff + 'T00:00:00');
        if (isNaN(start) || isNaN(end) || end < start) return 0;
        return Math.round((end - start) / 86400000) + 1;
    }

    /**
     * Parsea horas desde un string de input de usuario.
     * Acepta coma o punto como separador decimal.
     * Devuelve 0 si inválido o negativo.
     * Redondea a 1 decimal (granularidad mínima: media hora).
     */
    function _parseHoras(str) {
        if (!str && str !== 0) return 0;
        const n = parseFloat(String(str).trim().replace(',', '.'));
        if (!isFinite(n) || n < 0) return 0;
        return Math.round(n * 10) / 10;
    }

    /**
     * Formatea un valor numérico de horas como string limpio para envío al backend.
     * Evita que floats imprecisos (0.6000000000000001) lleguen al DRF DecimalField.
     * Usa toFixed(1) → "0.6" en lugar de "0.6000000000000001".
     * Si el valor es entero, omite el decimal: 2 → "2", no "2.0".
     */
    function _fmtHoras(val) {
        if (!val || val === 0) return '0';
        const r = Math.round(val * 10) / 10;
        return Number.isInteger(r) ? String(r) : r.toFixed(1);
    }

    /**
     * Sanitiza un monto monetario en COP para envío como string a DRF DecimalField.
     *
     * Casos soportados:
     *   "1.500.000"    → "1500000"      (puntos como separador de miles colombiano)
     *   "1.500.000,50" → "1500000.50"   (formato colombiano completo)
     *   "1500000,50"   → "1500000.50"   (coma como decimal)
     *   "1500000.50"   → "1500000.50"   (punto como decimal — ya válido para DRF)
     *   "1500000"      → "1500000"      (sin separadores)
     *   ""  / "0"      → "0"
     *
     * Devuelve "0" si el resultado es inválido o negativo.
     */
    function _sanitizarMonto(str) {
        if (!str || str === '') return '0';
        let s = String(str).trim();

        if (s.includes(',')) {
            // Coma presente → es separador decimal colombiano
            // Primero quitar todos los puntos (separadores de miles), luego cambiar coma
            s = s.replace(/\./g, '').replace(',', '.');
        } else {
            // Solo puntos. Heurística: si hay múltiples puntos, son miles.
            // Si hay un solo punto con 3+ dígitos a la derecha, también es miles.
            const partes = s.split('.');
            if (partes.length > 2) {
                s = partes.join('');                          // múltiples puntos → miles
            } else if (partes.length === 2 && partes[1].length >= 3) {
                s = partes.join('');                          // "1.500" → "1500"
            }
            // else: un punto con ≤2 dígitos → es decimal → dejar como está
        }

        const n = parseFloat(s);
        if (!isFinite(n) || n < 0) return '0';
        // Enviar como string exacto: entero sin decimales, o con máximo 2 decimales
        return Number.isInteger(n) ? String(Math.round(n)) : n.toFixed(2);
    }

    function _mostrarOffcanvasSeguro(el) {
        if (!el || !w.bootstrap?.Offcanvas) return;
        d.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
        d.body.classList.remove('overflow-hidden', 'modal-open');
        d.body.style.overflow = '';
        d.body.style.paddingRight = '';
        const prev = bootstrap.Offcanvas.getInstance(el);
        if (prev) { try { prev.dispose(); } catch (_) {} }
        bootstrap.Offcanvas.getOrCreateInstance(el).show();
    }

    // ── Preview calculo (HTMX programatico) ──────────────────────────────────

    function triggerPreviewCalculo() {
        const contrato = d.getElementById('devengo-contrato-id');
        if (!contrato?.value) return;

        const fi = d.getElementById('devengo-fecha_inicio')?.value;
        const ff = d.getElementById('devengo-fecha_fin_field')?.value;
        const fp = d.getElementById('devengo-fecha_pago')?.value;
        if (!fi || !ff || !fp) return;

        const wrapper = d.getElementById('devengo-campos-calculados-wrapper');
        if (!wrapper) return;

        // Sanitización previa al POST (FASE 3):
        // - dias_laborados: si el campo está vacío, calcula desde el período para no enviar "".
        // - monetarios: _sanitizarMonto() elimina puntos de miles colombianos y normaliza
        //   la coma decimal → DRF DecimalField no falla con "1.500.000" o "1.500,50".
        const dlRaw = d.getElementById('devengo-dias_laborados')?.value;
        const diasLaborados = dlRaw && dlRaw !== ''
            ? _fmtHoras(dlRaw)                        // limpia string, redondea a 1 decimal
            : String(calcularDias(fi, ff) || '');     // fallback desde fechas

        htmx.ajax('POST', `${API_URL}devengos/preview-calculo/`, {
            target: '#devengo-campos-calculados-wrapper',
            swap: 'innerHTML',
            headers: {
                'X-CSRFToken': w.getCookie?.('csrftoken')
                    || d.querySelector('[name=csrfmiddlewaretoken]')?.value
            },
            values: {
                contrato:               contrato.value,
                fecha_inicio:           fi,
                fecha_fin:              ff,
                fecha_pago:             fp,
                periodo_mes:            d.getElementById('devengo-periodo_mes')?.value || '',
                dias_laborados:         diasLaborados,
                otros_devengos:         _sanitizarMonto(d.getElementById('devengo-otros_devengos')?.value),
                prestamos:              _sanitizarMonto(d.getElementById('devengo-prestamos')?.value),
                descuentos_operativos:  _sanitizarMonto(d.getElementById('devengo-descuentos_operativos')?.value),
            }
        });
    }

    // ── Setup del formulario unificado ────────────────────────────────────────

    function setupFormUnificado() {
        const fiInput    = d.getElementById('devengo-fecha_inicio');
        const ffInput    = d.getElementById('devengo-fecha_fin_field');
        const fpInput    = d.getElementById('devengo-fecha_pago');
        const pmInput    = d.getElementById('devengo-periodo_mes');
        const dlInput    = d.getElementById('devengo-dias_laborados');
        const empInput   = d.getElementById('devengo-empleado-id');
        const contrInput = d.getElementById('devengo-contrato-id');
        const selectEmp  = d.getElementById('devengo-select-empleado');
        const diasWrap   = d.getElementById('wrapper-dias-estado');
        const infoPanel  = d.getElementById('panel-info-empleado');

        if (!fiInput || !ffInput || !selectEmp) return;

        // ── Actualizar panel de dias (reactivo) ───────────────────────────────
        function actualizarDias() {
            const dias = calcularDias(fiInput.value, ffInput.value);
            if (!fiInput.value || !ffInput.value) { if (diasWrap) diasWrap.innerHTML = ''; return 0; }
            if (dias <= 0) {
                if (diasWrap) diasWrap.innerHTML = `
                    <div class="alert alert-danger py-1 mb-0 small">
                        <i class="bi bi-exclamation-triangle me-1"></i>
                        La fecha fin debe ser posterior o igual a la fecha inicio.</div>`;
                return 0;
            }
            if (diasWrap) diasWrap.innerHTML = `
                <div class="card border-0 bg-primary-subtle rounded-2 px-3 py-2">
                    <span class="small fw-semibold text-primary">
                        <i class="bi bi-calendar-check me-1"></i>
                        Período: <strong>${dias}</strong> día${dias !== 1 ? 's' : ''}
                        <span class="text-muted fw-normal ms-1">(${fiInput.value} → ${ffInput.value})</span>
                    </span>
                </div>`;
            if (pmInput && fiInput.value.length >= 7) pmInput.value = fiInput.value.substring(0, 7);
            return dias;
        }

        // ── Resetear estado empleado al cambiar fechas ────────────────────────
        function resetEmpleado() {
            if (empInput)   empInput.value   = '';
            if (contrInput) contrInput.value = '';
            if (infoPanel)  infoPanel.classList.add('d-none');
            if (dlInput)    dlInput.value    = '';
            selectEmp.innerHTML = '<option value="">Seleccione un empleado...</option>';
            selectEmp.disabled  = true;
        }

        // ── Cargar empleados disponibles para el período ──────────────────────
        async function cargarEmpleados() {
            const dias = actualizarDias();
            if (!fiInput.value || !ffInput.value || dias <= 0) return;

            selectEmp.disabled = true;
            selectEmp.innerHTML = '<option value="">Buscando empleados disponibles...</option>';

            const api = w.Sintel?.Empleados?.API;
            if (!api) return;

            try {
                const url = api.devengos.empleadosDisponibles(fiInput.value, ffInput.value);
                const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
                if (!resp.ok) throw new Error('error_empleados');
                const data = await resp.json();

                if (!data.length) {
                    selectEmp.innerHTML = '<option value="">Sin empleados disponibles en este período</option>';
                    return;
                }

                selectEmp.innerHTML = '<option value="">Seleccione un empleado...</option>';
                data.forEach(emp => {
                    const opt = d.createElement('option');
                    opt.value       = emp.id;
                    opt.textContent = `${emp.nombre_completo} (${emp.numero_documento})`;
                    selectEmp.appendChild(opt);
                });
                selectEmp.disabled = false;

            } catch (err) {
                console.error(`${MOD} Error cargando empleados:`, err);
                selectEmp.innerHTML = '<option value="">Error al cargar empleados</option>';
            }
        }

        // ── Cargar info del empleado seleccionado + contrato activo ──────────
        async function cargarInfoEmpleado() {
            const empId = selectEmp.value;

            if (!empId) {
                if (empInput)   empInput.value   = '';
                if (contrInput) contrInput.value = '';
                if (infoPanel)  infoPanel.classList.add('d-none');
                return;
            }

            const api = w.Sintel?.Empleados?.API;
            if (!api) return;

            try {
                const resp = await fetch(api.devengos.infoEmpleado(empId), {
                    headers: { 'Accept': 'application/json' }
                });

                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    w.SintelFeedback?.error(err.error || 'El empleado no tiene contrato activo');
                    selectEmp.value = '';
                    return;
                }

                const data = await resp.json();

                // Establecer campos ocultos del formulario
                if (empInput)   empInput.value   = data.empleado.id;
                if (contrInput) contrInput.value = data.contrato.id;

                // Actualizar panel de info del empleado
                const setText = (id, val) => {
                    const el = d.getElementById(id);
                    if (el) el.textContent = val || '—';
                };
                setText('info-numero-documento', data.empleado.numero_documento);
                setText('info-eps',              data.empleado.eps_label);
                setText('info-afp',              data.empleado.afp_label);
                setText('info-arl',              data.empleado.arl_label);
                setText('info-cargo',            data.contrato.cargo);
                setText('info-tipo-contrato',    data.contrato.tipo);

                // Actualizar referencia de horas semanales y horas ordinarias del período
                const hs = data.contrato.horas_semanales || 42;
                const hsRef = d.getElementById('he-ref-hs');
                if (hsRef) {
                    hsRef.dataset.hsContrato = hs;
                    hsRef.textContent        = hs;
                }
                const diasPeriodo = calcularDias(fiInput.value, ffInput.value);
                const horasOrd = diasPeriodo > 0 ? (diasPeriodo * hs / 6).toFixed(1) : '—';
                const horasOrdEl = d.getElementById('he-horas-ordinarias');
                if (horasOrdEl) horasOrdEl.textContent = diasPeriodo > 0 ? `${horasOrd} h` : '—';

                // Pre-llenar dias_laborados con los días calculados del período
                const dias = calcularDias(fiInput.value, ffInput.value);
                if (dlInput && dias > 0) dlInput.value = dias;

                if (infoPanel) infoPanel.classList.remove('d-none');

                // Disparar preview con todos los datos disponibles
                setTimeout(triggerPreviewCalculo, 100);

            } catch (err) {
                console.error(`${MOD} Error cargando info empleado:`, err);
                w.SintelFeedback?.error('Error al cargar la información del empleado');
            }
        }

        // ── Event listeners ───────────────────────────────────────────────────
        fiInput.addEventListener('change', () => { resetEmpleado(); cargarEmpleados(); });
        ffInput.addEventListener('change', () => {
            if (ffInput.value && !fpInput?.value) fpInput.value = ffInput.value;
            resetEmpleado();
            cargarEmpleados();
        });
        selectEmp.addEventListener('change', cargarInfoEmpleado);
        setupHorasExtras();
    }

    // ── Gestor de Horas Extras y Recargos ─────────────────────────────────────

    function setupHorasExtras() {
        const btnAgregar   = d.getElementById('btn-agregar-he');
        const tipoSelect   = d.getElementById('he-tipo-select');
        const horasInput   = d.getElementById('he-horas-input');
        const lista        = d.getElementById('he-lista');
        const totalRow     = d.getElementById('he-total-row');
        const totalHoras   = d.getElementById('he-total-horas');

        if (!btnAgregar || !tipoSelect || !horasInput || !lista) return;

        // Mapa tipo → campo oculto acumulador
        const campoMap = {
            diurna:      'hf-he-diurnas',
            nocturna:    'hf-he-nocturnas',
            rec_nocturno:'hf-rec-nocturno',
            festivo:     'hf-rec-festivo',
        };

        // Nombre legible por tipo
        const labelMap = {
            diurna:      'H.E. Diurna (+25%)',
            nocturna:    'H.E. Nocturna (+75%)',
            rec_nocturno:'Recargo Nocturno (+35%)',
            festivo:     'H.E. Festivo (+75%)',
        };

        // Estado acumulado en memoria (sincronizado con campos ocultos)
        const acumulado = { diurna: 0, nocturna: 0, rec_nocturno: 0, festivo: 0 };

        function syncHiddenFields() {
            // _fmtHoras() convierte el float del acumulado a string limpio ("3.3" no "3.3000000000000003")
            // garantizando que DRF reciba un DecimalField válido sin imprecisión de punto flotante.
            const sync = (id, val) => {
                const el = d.getElementById(id);
                if (el) el.value = _fmtHoras(val);
            };
            sync('hf-he-diurnas',    acumulado.diurna);
            sync('hf-he-nocturnas',  acumulado.nocturna);
            sync('hf-rec-nocturno',  acumulado.rec_nocturno);
            sync('hf-rec-festivo',   acumulado.festivo);
        }

        function actualizarTotal() {
            const total = Object.values(acumulado).reduce((s, v) => s + v, 0);
            if (totalRow) totalRow.classList.toggle('d-none', total === 0);
            if (totalHoras) totalHoras.textContent = total % 1 === 0 ? total : total.toFixed(1);
        }

        function renderLista() {
            lista.innerHTML = '';
            let hayEntradas = false;
            for (const [tipo, horas] of Object.entries(acumulado)) {
                if (horas <= 0) continue;
                hayEntradas = true;
                const item = d.createElement('div');
                item.className = 'alert alert-secondary py-1 px-3 mb-1 d-flex justify-content-between align-items-center small';
                item.dataset.tipo = tipo;
                item.innerHTML = `
                    <span>
                        <i class="bi bi-clock me-1 text-primary"></i>
                        <strong>${horas % 1 === 0 ? horas : horas.toFixed(1)} h</strong>
                        — ${labelMap[tipo]}
                    </span>
                    <button type="button" class="btn btn-sm btn-outline-danger py-0 px-1 btn-quitar-he"
                            data-tipo="${tipo}" title="Quitar">
                        <i class="bi bi-x-lg"></i>
                    </button>`;
                lista.appendChild(item);
            }
            if (!hayEntradas) lista.innerHTML = '';
        }

        function refrescarPreview() {
            syncHiddenFields();
            actualizarTotal();
            renderLista();
            // Disparar preview-calculo si hay contrato activo
            setTimeout(triggerPreviewCalculo, 50);
        }

        // Agregar horas
        btnAgregar.addEventListener('click', () => {
            const tipo  = tipoSelect.value;
            // _parseHoras: acepta coma/punto, redondea a 1 decimal, bloquea negativos
            const horas = _parseHoras(horasInput.value);
            if (!tipo || horas <= 0) {
                horasInput.classList.add('is-invalid');
                setTimeout(() => horasInput.classList.remove('is-invalid'), 1500);
                return;
            }
            // Suma con redondeo a 1 decimal para evitar acumulación de error de float
            // Ej: 0.3 + 0.3 = 0.6000000000000001 → Math.round(6) / 10 = 0.6
            acumulado[tipo] = Math.round(((acumulado[tipo] || 0) + horas) * 10) / 10;
            horasInput.value = '';
            refrescarPreview();
        });

        // Quitar horas (delegado)
        lista.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-quitar-he');
            if (!btn) return;
            const tipo = btn.dataset.tipo;
            if (tipo in acumulado) {
                acumulado[tipo] = 0;
                refrescarPreview();
            }
        });
    }

    // ── Listener post-HTMX: activa offcanvas y configura form ────────────────

    function setupOffcanvasLoadListener() {
        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('.offcanvas');
            if (!offcanvasEl) return;

            console.log(`${MOD} Activando offcanvas: ${offcanvasEl.id}`);
            _mostrarOffcanvasSeguro(offcanvasEl);
            setupFormUnificado();
        });
    }

    // ── Listener guardar nomina (exito / error) ───────────────────────────────

    function setupHTMXListeners() {
        d.body.addEventListener('htmx:afterRequest', function(evt) {
            const target = evt.target;
            if (target.id !== 'btn-guardar-devengo') return;

            target.disabled  = false;
            target.innerHTML = '<i class="bi bi-check-lg me-1"></i>Guardar Nómina';

            if (evt.detail.successful) {
                const oc = d.getElementById('offcanvas-devengo');
                if (oc) bootstrap.Offcanvas.getInstance(oc)?.hide();
                w.UIManager?.notifySuccess('Nómina registrada correctamente');
                w.Sintel?.Empleados?.EmpleadoList?.reload();
                w.Sintel?.Empleados?.NominaList?.reload();
            }
        });

        d.body.addEventListener('htmx:responseError', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== 'devengo-campos-calculados-wrapper') return;
            let msg = 'Error al calcular la nómina. Verifique los datos.';
            try { msg = JSON.parse(evt.detail.xhr.responseText).error || msg; } catch (_) {}
            target.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>${msg}
                </div>`;
        });
    }

    // ── Bootstrap ─────────────────────────────────────────────────────────────

    setupHTMXListeners();
    setupOffcanvasLoadListener();

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};
    w.Sintel.Empleados.DevengoEditor = { open, openDevengoOffcanvas: open, triggerPreviewCalculo };
    w.DevengosEditor = w.Sintel.Empleados.DevengoEditor;

})(window, document);
