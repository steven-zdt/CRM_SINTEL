/**
 * Feature: Editor - Proyectos v3.5.1
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - Sintel.Core.Http (F32.7, core-http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 */
(function(w, d) {
    'use strict';

    const MOD = '[proyectos.editor]';
    let currentProyecto = null;
    let currentStep = 0;
    let presupuestoListenersInitialized = false;
    let editorEventsInitialized = false;
    const phaseMap = {
        'BORRADOR': 0,
        'INICIO': 1,
        'PLANEACION': 2,
        'EJECUCION': 3,
        'CIERRE': 4
    };

    /**
     * Recolectar datos del formulario del Offcanvas
     * @returns {FormData} Datos del proyecto para mutación multipart/form-data
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-proyecto');
        if (!form) {
            console.error(`${MOD} Formulario #form-proyecto no encontrado`);
            return null;
        }

        // Pre-sync: asegurar que el select de factura esté reflejado en el input hidden ANTES de FormData
        const facturaSelect      = form.querySelector('#proyecto-factura-venta-select');
        const facturaIdInput     = form.querySelector('#proyecto-factura-costo-id');
        const facturaNumeroInput = form.querySelector('#proyecto-factura-costo-numero');
        if (facturaSelect && facturaIdInput) {
            facturaIdInput.value = facturaSelect.value || '';
            if (facturaSelect.value && facturaNumeroInput && !facturaNumeroInput.value) {
                const opt = facturaSelect.options[facturaSelect.selectedIndex];
                if (opt) facturaNumeroInput.value = opt.getAttribute('data-numero') || opt.text.trim();
            }
        }

        const formData = new FormData(form);

        // ⚠️ DOM Shield: Remover campos vacíos, "undefined" string, None, null
        for (const [key, value] of Array.from(formData.entries())) {
            if (key === 'factura_costo') continue; // manejado explícitamente abajo
            // Limpiar: '', null, 'undefined', 'None', etc.
            if (value === '' || value === null || value === 'undefined' || value === 'None') {
                formData.delete(key);
            }
        }

        // FK factura_costo: enviar solo si tiene valor; si vacío, no enviar (PATCH parcial no altera el FK)
        if (!formData.get('factura_costo')) {
            formData.delete('factura_costo');
        }

        // Phase-based field cleanup: remove responsable fields that are empty
        // (prevents "invalid integer" validation errors for unselected responsables)
        // PLAN_PROYECTOS_FASE_2_COTIZACION_RECURSOS_PRESUPUESTO Fase 22/23:
        // responsable_tecnico_* ya no tiene input en el formulario -- FormData
        // simplemente no lo incluye (no hace falta borrarlo explicitamente),
        // pero se retira de esta lista por higiene (el backend lo conserva
        // por compatibilidad historica, solo deja de enviarse desde aqui).
        const responsableFields = [
            'responsable_comercial_id', 'responsable_comercial_nombre',
            'responsable_operativo_id', 'responsable_operativo_nombre',
            'responsable_administrativo_id', 'responsable_administrativo_nombre',
        ];
        responsableFields.forEach(field => {
            const value = formData.get(field);
            if (value === '' || value === null) {
                formData.delete(field);
            }
        });

        // Limpiar file inputs vacíos
        const fileFields = ['contrato_archivo', 'acta_inicio_archivo', 'cronograma_archivo', 'acta_entrega_archivo', 'informe_final_archivo'];
        fileFields.forEach(field => {
            const input = form.querySelector(`[name="${field}"]`);
            if (input && (!input.files || input.files.length === 0)) {
                formData.delete(field);
            }
        });

        formData.delete('uuid');
        return formData;
    }

    /**
     * Guardar proyecto
     * @param {Boolean} silent Si es true, no cierra el Offcanvas tras éxito
     */
    async function guardarProyecto(silent = false) {
        const data = recolectarDatosFormulario();
        if (!data) {
            return false;
        }

        const uuid = d.querySelector('#proyecto-uuid')?.value;
        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        const historialUuid = d.querySelector('#proyecto-historial-uuid')?.value;
        const isCreation = !uuid;

        // Error Boundary: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-wizard-save');
        const btnOriginalText = btnGuardar?.innerHTML || '';

        // Error Boundary: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        let res;
        if (uuid) {
            res = await w.Sintel.Core.Http.request('PATCH', `/api/v1/proyectos/${uuid}/`, data);
        } else {
            // T-9: delega a la SSoT de endpoints (proyectos.api.js).
            res = await w.proyectosAPI.create(data);
        }

        // Error Boundary: Restaurar estado del botón
        if (btnGuardar) {
            btnGuardar.disabled = false;
            btnGuardar.innerHTML = btnOriginalText;
        }

        if (!res.ok) {
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, MOD, {
                    errorContainerSelector: '#form-proyecto-feedback'
                });
            } else {
                const errorContainer = d.querySelector('#form-proyecto-feedback');
                if (errorContainer) {
                    errorContainer.classList.remove('d-none');
                    errorContainer.textContent = res.data?.detail || 'Error al guardar el proyecto';
                }
            }
            return false;
        }

        // Guardar estado actual
        currentProyecto = res.data;

        // Vinculación automática si es creación y viene de historial de servicio (v3.9.7)
        if (isCreation && currentProyecto?.uuid && historialUuid) {
            console.log(`${MOD} Vinculando nuevo proyecto ${currentProyecto.uuid} con historial ${historialUuid}`);
            const vincularRes = await w.Sintel.Core.Http.request('POST', '/api/v1/proyectos/vincular-proyecto/', {
                proyecto_uuid: currentProyecto.uuid,
                historial_uuid: historialUuid
            });
            if (vincularRes.ok) {
                console.log(`${MOD} Vinculación exitosa`);
                if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                    w.SintelFeedback.success('Proyecto creado y vinculado al historial de servicio correctamente');
                }
            } else {
                console.error(`${MOD} Error al vincular proyecto:`, vincularRes);
                if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                    w.SintelFeedback.error('Proyecto creado, pero falló la vinculación automática');
                }
            }
        }

        // Limpiar errores si el guardado es exitoso
        const errorContainer = d.querySelector('#form-proyecto-feedback');
        if (errorContainer) {
            errorContainer.classList.add('d-none');
            errorContainer.textContent = '';
        }

        // Si no es silencioso, cerrar Offcanvas y dar feedback
        if (!silent) {
            if (offcanvasEl && w.UIManager?.handleOffcanvas) {
                w.UIManager.handleOffcanvas(offcanvasEl, 'hide');
            } else if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                const offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (offcanvasInstance) {
                    offcanvasInstance.hide();
                }
            }

            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                w.SintelFeedback.success('Proyecto guardado correctamente');
            }
        }

        // Actualizar datos del formulario en el DOM tras persistencia
        if (currentProyecto) {
            const uuidInput = d.querySelector('#proyecto-uuid');
            if (uuidInput) uuidInput.value = currentProyecto.uuid;

            const codigoInput = d.querySelector('#proyecto-codigo');
            if (codigoInput && currentProyecto.codigo) {
                codigoInput.value = currentProyecto.codigo;
            }

            // Re-sync factura select: la respuesta del PATCH contiene 'factura_costo' (PK)
            const selFactura   = d.querySelector('#proyecto-factura-venta-select');
            const inpFacturaId = d.querySelector('#proyecto-factura-costo-id');
            const inpFacturaNo = d.querySelector('#proyecto-factura-costo-numero');
            if (selFactura) {
                const fkVal = currentProyecto.factura_costo || '';
                selFactura.value = fkVal;
                if (inpFacturaId) inpFacturaId.value = fkVal;
                if (fkVal && inpFacturaNo && !inpFacturaNo.value) {
                    const opt = selFactura.options[selFactura.selectedIndex];
                    if (opt) inpFacturaNo.value = opt.getAttribute('data-numero') || '';
                }
                actualizarPanelCotizacion(selFactura);
            }

            renderStepLocks();
            populateStepDetails();
        }

        // Disparar recarga reactiva del grid
        d.dispatchEvent(new Event('proyectoGuardado'));
        console.log(`${MOD} Proyecto guardado correctamente`);
        return true;
    }

    /**
     * Avanzar la fase del proyecto
     */
    async function avanzarFaseProyecto(targetFase) {
        const uuid = d.querySelector('#proyecto-uuid')?.value;
        if (!uuid) return;

        // Buscar botón de acción correspondiente para feedback de carga
        const btnAvanzar = d.querySelector(`.btn-avanzar-fase-action[data-target-fase="${targetFase}"]`);
        const btnOriginalText = btnAvanzar?.innerHTML || '';
        if (btnAvanzar) {
            btnAvanzar.disabled = true;
            btnAvanzar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Avanzando...';
        }

        // Llamar endpoint API avanzar-fase sin responsables iniciales (se configuran tras desbloquear)
        const res = await w.proyectosAPI.avanzarFase(uuid, targetFase, null, null);

        if (btnAvanzar) {
            btnAvanzar.disabled = false;
            btnAvanzar.innerHTML = btnOriginalText;
        }

        if (!res.ok) {
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, MOD, {
                    errorContainerSelector: '#form-proyecto-feedback'
                });
            } else {
                const errorContainer = d.querySelector('#form-proyecto-feedback');
                if (errorContainer) {
                    errorContainer.classList.remove('d-none');
                    errorContainer.textContent = res.data?.detail || 'Error al avanzar fase';
                }
            }
            return;
        }

        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success(`Proyecto avanzado exitosamente a ${targetFase}`);
        }

        // Actualizar datos
        currentProyecto = res.data;
        renderStepLocks();
        populateStepDetails();

        // Ir al step correspondiente
        const targetStep = phaseMap[targetFase] || 0;
        irAStep(targetStep);

        // Disparar recarga reactiva del grid
        d.dispatchEvent(new Event('proyectoGuardado'));
    }

    /**
     * Moverse visualmente a un Step específico
     */
    function irAStep(stepIdx) {
        currentStep = stepIdx;

        // Phase 0 cleanup: clear all responsable fields ONLY when creating a new project
        if (stepIdx === 0 && !currentProyecto) {
            const responsableSelects = [
                'proyecto-responsable-comercial-select',
                'proyecto-responsable-operativo-select',
                'proyecto-responsable-administrativo-select',
            ];
            const responsableFields = [
                'proyecto-responsable-comercial-id', 'proyecto-responsable-comercial-nombre',
                'proyecto-responsable-operativo-id', 'proyecto-responsable-operativo-nombre',
                'proyecto-responsable-administrativo-id', 'proyecto-responsable-administrativo-nombre',
            ];

            // Clear selects
            responsableSelects.forEach(selectId => {
                const select = d.querySelector(`#${selectId}`);
                if (select) select.value = '';
            });

            // Clear hidden inputs
            responsableFields.forEach(fieldId => {
                const input = d.querySelector(`#${fieldId}`);
                if (input) input.value = '';
            });
        }

        // Actualizar visualización de las pestañas de contenido
        const panes = d.querySelectorAll('#offcanvas-proyecto .step-pane');
        panes.forEach((pane, idx) => {
            if (idx === stepIdx) {
                pane.classList.add('active');
            } else {
                pane.classList.remove('active');
            }
        });

        // Actualizar estilo del nodo en el Stepper header
        const nodes = d.querySelectorAll('#offcanvas-proyecto .step-node');
        nodes.forEach((node, idx) => {
            node.classList.remove('active');
            if (idx === stepIdx) {
                node.classList.add('active');
            }
        });

        // Actualizar botones de navegación
        const btnBack = d.querySelector('#btn-wizard-back');
        const btnNext = d.querySelector('#btn-wizard-next');
        const btnSave = d.querySelector('#btn-wizard-save');

        if (btnBack) {
            btnBack.disabled = (stepIdx === 0);
        }

        // Si es proyecto nuevo o estamos en el último paso (Cierre), mostrar "Guardar Todo"
        const isNew = !currentProyecto;
        if (btnNext && btnSave) {
            if (stepIdx === 4 || isNew) {
                btnNext.classList.add('d-none');
                btnSave.classList.remove('d-none');
            } else {
                btnNext.classList.remove('d-none');
                btnSave.classList.add('d-none');
            }
        }

        // Actualizar la línea de progreso visual
        const progressBar = d.querySelector('#wizard-progress-bar');
        if (progressBar) {
            const pct = (stepIdx / 4) * 100;
            progressBar.style.width = `${pct}%`;
        }
    }

    /**
     * Aplicar atributo readonly a todos los inputs de una fase específica
     * @param {number} stepIdx - Índice del step (0-4)
     * @param {boolean} readOnly - true para read-only, false para editable
     */
    function applyReadOnlyToStep(stepIdx, readOnly) {
        // Seleccionar el pane específico por índice
        const panes = d.querySelectorAll('#offcanvas-proyecto .step-pane');
        if (!panes || panes.length <= stepIdx) return;

        const pane = panes[stepIdx];

        // Seleccionar todos los inputs, selects, textareas en el step
        const inputs = pane.querySelectorAll('input, select, textarea, [contenteditable]');
        inputs.forEach(input => {
            if (readOnly) {
                input.setAttribute('readonly', 'readonly');
                input.setAttribute('disabled', 'disabled');
                input.style.cursor = 'not-allowed';
                input.style.opacity = '0.6';
            } else {
                input.removeAttribute('readonly');
                input.removeAttribute('disabled');
                input.style.cursor = 'auto';
                input.style.opacity = '1';
            }
        });

        // Desactivar botones de acción en fases anteriores (cuando están en read-only)
        if (readOnly) {
            const buttons = pane.querySelectorAll('button:not(.btn-wizard-back):not(.btn-wizard-next):not([data-bs-dismiss])');
            buttons.forEach(btn => {
                btn.disabled = true;
                btn.style.opacity = '0.5';
            });
        } else {
            // Reactivar botones cuando se habilita edición
            const buttons = pane.querySelectorAll('button:not([data-bs-dismiss])');
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.style.opacity = '1';
            });
        }
    }

    /**
     * Renderizar candados y habilitar/deshabilitar fases en el stepper.
     * Todas las fases accesibles (actuales y anteriores) son siempre editables.
     */
    function renderStepLocks() {
        const currentFase = currentProyecto?.fase_actual || 'BORRADOR';
        const activeFaseIdx = phaseMap[currentFase] || 0;

        // Marcar visualmente fases completadas en el header del stepper
        const nodes = d.querySelectorAll('#offcanvas-proyecto .step-node');
        nodes.forEach((node, idx) => {
            node.classList.remove('locked', 'completed');
            if (idx < activeFaseIdx) {
                node.classList.add('completed');
            } else if (idx > activeFaseIdx) {
                node.classList.add('locked');
            }
        });

        // Mostrar fases alcanzadas (editable), bloquear fases futuras
        for (let idx = 1; idx <= 4; idx++) {
            const lockedContainer = d.querySelector(`#locked-step-${idx}`);
            const unlockedContent = d.querySelector(`#unlocked-step-${idx}`);

            if (idx > activeFaseIdx) {
                // Fase futura: mostrar candado
                if (lockedContainer) lockedContainer.classList.remove('d-none');
                if (unlockedContent) unlockedContent.classList.add('d-none');
            } else {
                // Fase alcanzada: siempre editable, sin restricciones
                if (lockedContainer) lockedContainer.classList.add('d-none');
                if (unlockedContent) unlockedContent.classList.remove('d-none');
                applyReadOnlyToStep(idx - 1, false);
            }
        }

        // Sincronizar badge de fase actual en el header del offcanvas
        const badgeFase = d.querySelector('#proyecto-badge-fase-actual');
        if (badgeFase) {
            const labelMap = {
                'BORRADOR': '0. Borrador',
                'INICIO': '1. Inicio',
                'PLANEACION': '2. Planeación',
                'EJECUCION': '3. Ejecución',
                'CIERRE': '4. Cierre'
            };
            badgeFase.textContent = labelMap[currentFase] || currentFase;
            
            // Color según fase
            badgeFase.className = 'badge ms-3 ';
            if (currentFase === 'BORRADOR') badgeFase.classList.add('bg-secondary');
            else if (currentFase === 'INICIO') badgeFase.classList.add('bg-info', 'text-dark');
            else if (currentFase === 'PLANEACION') badgeFase.classList.add('bg-primary');
            else if (currentFase === 'EJECUCION') badgeFase.classList.add('bg-warning', 'text-dark');
            else if (currentFase === 'CIERRE') badgeFase.classList.add('bg-success');
        }

        // PLAN_AJUSTE_CICLO_PROYECTOS_FASE_1_VIABILIDAD_APROBACION: candado
        // especifico de "2. Planeacion" cuando el Inicio todavia no tiene
        // aprobacion vigente -- distinto del candado generico de fase futura
        // (ese ya lo maneja el bloque de arriba via .locked). `puede_avanzar_
        // planeacion` viene calculado del backend (serializer), nunca se
        // recalcula aqui (Seccion 67 del plan).
        const iconoPlaneacionBloqueada = d.getElementById('icono-planeacion-bloqueada');
        const bloqueadaPorAprobacion = currentFase === 'INICIO' && !currentProyecto?.puede_avanzar_planeacion;
        if (iconoPlaneacionBloqueada) {
            iconoPlaneacionBloqueada.classList.toggle('d-none', !bloqueadaPorAprobacion);
        }

        // El overlay de "#locked-step-2" ya queda visible por el bucle de
        // arriba (idx=2 > activeFaseIdx=1 mientras fase_actual=='INICIO') --
        // aqui solo se decide CUAL de los 2 mensajes internos mostrar, para
        // que el usuario entienda la causa real (pendiente de aprobacion)
        // en vez de un candado generico "avance de fase" que termina en un
        // error de sorpresa al hacer clic.
        const overlayGenerico = d.getElementById('locked-step-2-generico');
        const overlayPendiente = d.getElementById('locked-step-2-pendiente-aprobacion');
        if (overlayGenerico && overlayPendiente) {
            overlayGenerico.classList.toggle('d-none', bloqueadaPorAprobacion);
            overlayPendiente.classList.toggle('d-none', !bloqueadaPorAprobacion);
            if (bloqueadaPorAprobacion) {
                const textos = {
                    'SIN_ENVIAR': 'Complete la información económica y envíela a revisión en la Fase 1.',
                    'PENDIENTE': 'Ya fue enviado a revisión y está esperando la decisión de un administrador.',
                    'RECHAZADA': 'La última solicitud fue rechazada. Revise el motivo en la Fase 1 y envíela de nuevo.',
                    'CANCELADA': 'Los datos económicos cambiaron después de la aprobación, así que quedó anulada. Envíela de nuevo desde la Fase 1.'
                };
                const estado = currentProyecto?.estado_aprobacion_inicio || 'SIN_ENVIAR';
                const textoEl = d.getElementById('locked-step-2-estado-texto');
                if (textoEl) textoEl.textContent = textos[estado] || textos['SIN_ENVIAR'];
            }
        }
    }

    /**
     * Helper para actualizar los badges y links de descarga de archivos existentes
     */
    function updateFileBadge(fieldName, existingContainerId, downloadLinkId) {
        const url = currentProyecto?.[fieldName];
        const container = d.querySelector(`#${existingContainerId}`);
        const downloadLink = d.querySelector(`#${downloadLinkId}`);
        if (container && downloadLink) {
            if (url) {
                container.classList.remove('d-none');
                downloadLink.href = url;
            } else {
                container.classList.add('d-none');
                downloadLink.href = '#';
            }
        }
    }

    /**
     * Inicializar Informe Ejecutivo de Cierre (Fase 4).
     * Lee desde currentProyecto (API) para evitar race condition con _items async.
     *
     * FORMULAS:
     *   BASE              = valor_contrato_proyectado
     *   costo_plan        = costo_planeado_total  (sum ItemPresupuestoProyecto)
     *   costo_real        = costo_mano_obra_real + costo_materiales_real
     *   utilidad_plan     = BASE - costo_plan
     *   utilidad_real     = BASE - costo_real
     *   margen_plan %     = utilidad_plan / BASE * 100
     *   margen_real %     = utilidad_real / BASE * 100
     *   variacion_costo   = costo_plan - costo_real  (+ bajo presupuesto / - sobrecosto)
     */
    function initInformeCierre() {
        if (!currentProyecto) return;

        // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
        const fmt    = (n) => (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(n || 0, { minimumFractionDigits: 0 })
            : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n || 0);
        const fmtPct = (n) => `${(n || 0).toFixed(1)}%`;
        const setEl  = (id, text) => { const el = d.querySelector(`#${id}`); if (el) el.textContent = text; };

        // Contexto (Fase 1)
        const clienteNombre = currentProyecto.cliente_info?.nombre
            || currentProyecto.cliente_nombre
            || (currentProyecto.cliente_id ? `Cliente ID: ${currentProyecto.cliente_id}` : 'Sin cliente asignado');
        const facturaNumero = currentProyecto.factura_costo_numero || currentProyecto.factura_ref || 'Sin factura';
        const ctx1 = d.querySelector('#contexto-cliente-nombre');
        const ctx2 = d.querySelector('#contexto-factura-costo-numero');
        if (ctx1) ctx1.value = clienteNombre;
        if (ctx2) ctx2.value = facturaNumero;

        // Numeros base desde API (campos de modelo)
        const BASE        = parseFloat(currentProyecto.valor_contrato_proyectado) || 0;
        const costoPlan   = parseFloat(currentProyecto.costo_planeado_total)      || 0;
        const costoMO     = parseFloat(currentProyecto.costo_mano_obra_real)      || 0;
        const costoMat    = parseFloat(currentProyecto.costo_materiales_real)     || 0;
        const costoGastos = parseFloat(currentProyecto.costo_gastos_real)         || 0;
        const costoReal   = costoMO + costoMat + costoGastos;

        // Presupuesto planeado por categoria (Fase 2 _items como fallback si ya estan cargados)
        const items = w.Sintel?.ProyectosPresupuesto?._items || [];
        const sumCat = (cat) => items.filter(i => i.categoria === cat)
                                     .reduce((s, i) => s + (parseFloat(i.subtotal) || 0), 0);
        const planMO       = sumCat('MANO_OBRA');
        const planEquipos  = sumCat('EQUIPOS');
        const planMat      = sumCat('MATERIALES');
        // Si _items esta vacio (race condition), usar costo_planeado_total del modelo
        const costoPlanUI  = (planMO + planEquipos + planMat) > 0
                             ? (planMO + planEquipos + planMat)
                             : costoPlan;

        const utilPlan   = BASE - costoPlanUI;
        const utilReal   = BASE - costoReal;
        const margenPlan = BASE > 0 ? (utilPlan  / BASE * 100) : 0;
        const margenReal = BASE > 0 ? (utilReal  / BASE * 100) : 0;
        const variacion  = costoPlanUI - costoReal;   // + bajo presupuesto, - sobrecosto
        const varPct     = costoPlanUI > 0 ? (variacion / costoPlanUI * 100) : 0;

        // Encabezado: Valor Contrato
        setEl('dash-valor-contrato', fmt(BASE));

        // Desglose costos planeados (Fase 2 presupuesto)
        setEl('dash-mano-obra',   fmt(planMO       > 0 ? planMO      : costoPlan));
        setEl('dash-equipos',     fmt(planEquipos  > 0 ? planEquipos : 0));
        setEl('dash-materiales',  fmt(planMat      > 0 ? planMat     : 0));
        setEl('dash-costo-total', fmt(costoPlanUI));

        // Utilidad planeada
        setEl('dash-utilidad', fmt(utilPlan));
        const pctEl = d.querySelector('#dash-porcentaje-utilidad');
        if (pctEl) {
            pctEl.textContent = fmtPct(margenPlan);
            pctEl.className = 'badge px-2 py-1 mt-1';
            pctEl.classList.add(utilPlan > 0 ? 'bg-success' : utilPlan < 0 ? 'bg-danger' : 'bg-secondary');
        }

        // Panel comparativo Planeado vs Real (IDs agregados en Fase 4 template)
        setEl('dash-real-costo-total', fmt(costoReal));
        setEl('dash-real-utilidad',    fmt(utilReal));
        setEl('dash-real-margen',      fmtPct(margenReal));

        const varEl = d.querySelector('#dash-variacion-badge');
        if (varEl) {
            if (variacion > 0) {
                varEl.className = 'badge bg-success';
                varEl.textContent = `Bajo presupuesto ${fmtPct(varPct)}`;
            } else if (variacion < 0) {
                varEl.className = 'badge bg-danger';
                varEl.textContent = `Sobrecosto ${fmtPct(varPct)}`;
            } else {
                varEl.className = 'badge bg-secondary';
                varEl.textContent = 'En presupuesto 0%';
            }
        }

        // Porcentaje Avance
        const pctAvanceEl = d.querySelector('#porcentaje-avance-display');
        if (pctAvanceEl) pctAvanceEl.textContent = `${parseInt(currentProyecto.porcentaje_avance) || 0}%`;
    }

    /**
     * Rellenar todos los componentes dinámicos de las fases unlocked
     */
    function populateStepDetails() {
        if (!currentProyecto) return;

        // 1. Actualizar badges de archivos
        updateFileBadge('contrato_archivo', 'contrato-archivo-existing', 'contrato-archivo-download');
        updateFileBadge('acta_inicio_archivo', 'acta-inicio-archivo-existing', 'acta-inicio-archivo-download');
        updateFileBadge('cronograma_archivo', 'cronograma-archivo-existing', 'cronograma-archivo-download');
        updateFileBadge('acta_entrega_archivo', 'acta-entrega-archivo-existing', 'acta-entrega-archivo-download');
        updateFileBadge('informe_final_archivo', 'informe-final-archivo-existing', 'informe-final-archivo-download');

        // 1.5. Presupuesto Planeado (v3.5.2 - Fase 2)
        if (currentProyecto?.uuid) {
            const enCierre = currentProyecto.fase_actual === 'CIERRE';
            w.Sintel.ProyectosPresupuesto.init(currentProyecto.uuid, enCierre);
        }

        // 1.55. Cotización de Planeación (PLAN_PROYECTOS_FASE_2_COTIZACION_RECURSOS_PRESUPUESTO - Fase 2)
        if (currentProyecto?.uuid) {
            w.Sintel.ProyectosCotizacionPlaneacion.init(currentProyecto.uuid);
        }

        // 1.6. Tareas Diarias (v3.5.3 - Fase 3)
        if (currentProyecto?.uuid) {
            const enCierre = currentProyecto.fase_actual === 'CIERRE';
            w.Sintel.TareasDiarias.init(currentProyecto.uuid, currentProyecto, enCierre);
        }

        // 1.7. Gastos del Proyecto (GASTOS_PROYECTOS_01 - Fase 3)
        if (currentProyecto?.uuid) {
            w.Sintel.ProyectosGastos.init(currentProyecto.uuid);
        }

        // 1.75. Ordenes de Compra del Proyecto (PLAN_INTEGRACION_PROYECTOS_ORDENES_COMPRA_VENTA_OPCIONAL - Fase 0 Borrador)
        if (currentProyecto?.uuid) {
            w.Sintel.ProyectosOrdenesCompra.init(currentProyecto.uuid, currentProyecto.fase_actual);
        }

        // 1.78. Fase 1 (Inicio): Viabilidad y Aprobacion (PLAN_AJUSTE_CICLO_
        // PROYECTOS_FASE_1_VIABILIDAD_APROBACION)
        if (currentProyecto?.uuid) {
            w.Sintel.ProyectoInicio.init(currentProyecto.uuid, currentProyecto);
        }

        // 2. Equipo de Trabajo (Fase 3)
        const equipoList = d.querySelector('#equipo-trabajo-list');
        if (equipoList) {
            const equipo = currentProyecto.equipo_trabajo || [];
            if (equipo.length === 0) {
                equipoList.innerHTML = `
                    <div class="text-center text-muted py-3 bg-light rounded border border-dashed">
                        No hay personal operativo asignado a este proyecto.
                    </div>`;
            } else {
                let html = '';
                equipo.forEach(colab => {
                    const statusBadge = colab.activo 
                        ? '<span class="badge bg-success">Activo</span>' 
                        : '<span class="badge bg-secondary">Inactivo</span>';
                    html += `
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <strong class="text-dark">${colab.nombre_colaborador || 'Colaborador'}</strong>
                                <div class="text-muted small">${colab.rol_display || colab.rol || 'Operativo'} | Asignado el: ${colab.fecha_asignacion || 'N/A'}</div>
                            </div>
                            <div class="text-end">
                                <div class="fw-bold text-primary">${w.proyectosAPI.formatCurrency(colab.costo_total_asignacion)}</div>
                                <div class="small text-muted">${colab.horas_totales_registradas || 0} hrs a ${w.proyectosAPI.formatCurrency(colab.costo_hora)}/hr</div>
                                <div class="mt-1">${statusBadge}</div>
                            </div>
                        </div>`;
                });
                equipoList.innerHTML = html;
            }
        }

        // 3. Pedidos de Recursos (Fase 3)
        const pedidosList = d.querySelector('#pedidos-list');
        if (pedidosList) {
            const pedidos = currentProyecto.pedidos || [];
            if (pedidos.length === 0) {
                pedidosList.innerHTML = `
                    <div class="text-center text-muted py-3 bg-light rounded border border-dashed">
                        No hay solicitudes de recursos/materiales para este proyecto.
                    </div>`;
            } else {
                let html = '';
                pedidos.forEach(p => {
                    let stateClass = 'bg-warning text-dark';
                    if (p.estado === 'COMPLETADO' || p.estado === 'ENTREGADO') stateClass = 'bg-success';
                    else if (p.estado === 'RECHAZADO' || p.estado === 'CANCELADO') stateClass = 'bg-danger';

                    html += `
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <strong class="text-dark">${p.tipo_recurso_display || p.tipo_recurso || 'Recurso'}</strong>
                                <div class="text-muted small">Suministro: ${p.fuente_suministro_display || p.fuente_suministro} | Encargado: ${p.empleado_encargado_nombre || 'N/A'}</div>
                                <div class="text-muted small fst-italic mt-1">"${p.observaciones || 'Sin observaciones'}"</div>
                            </div>
                            <div class="text-end">
                                <span class="badge ${stateClass}">${p.estado_display || p.estado}</span>
                                <div class="text-muted small mt-1">Solicitado: ${p.fecha_solicitud || 'N/A'}</div>
                                ${p.proveedor_nombre ? `<div class="small text-secondary">Prov: ${p.proveedor_nombre}</div>` : ''}
                            </div>
                        </div>`;
                });
                pedidosList.innerHTML = html;
            }
        }

        // 4. Indicadores Financieros REALES (Fase 3)
        // BASE: valor_contrato es la base de todos los calculos
        // ind.real.* viene del serializer get_indicadores_financieros
        const valContrato    = parseFloat(currentProyecto.valor_contrato_proyectado) || 0;
        const costPersonal   = parseFloat(currentProyecto.costo_mano_obra_real) || 0;
        const costMateriales = parseFloat(currentProyecto.costo_materiales_real) || 0;
        const costGastos     = parseFloat(currentProyecto.costo_gastos_real) || 0;
        const costTotal      = costPersonal + costMateriales + costGastos;
        // utilidad_real = valor_contrato - costo_total_real
        const utilidad = valContrato - costTotal;
        // margen_real % = utilidad_real / valor_contrato * 100
        const margen = valContrato > 0 ? (utilidad / valContrato * 100) : 0;

        const setElementText = (id, text) => {
            const el = d.querySelector(`#${id}`);
            if (el) el.textContent = text;
        };

        setElementText('fin-valor-contrato',   w.proyectosAPI.formatCurrency(valContrato));
        setElementText('fin-costo-personal',   w.proyectosAPI.formatCurrency(costPersonal));
        setElementText('fin-costo-materiales', w.proyectosAPI.formatCurrency(costMateriales));
        setElementText('fin-costo-gastos',     w.proyectosAPI.formatCurrency(costGastos));
        setElementText('fin-costo-total',      w.proyectosAPI.formatCurrency(costTotal));
        setElementText('fin-utilidad-neta',    w.proyectosAPI.formatCurrency(utilidad));

        // Badge margen con color dinamico segun rentabilidad
        const margenBadge = d.querySelector('#fin-margen-rentabilidad');
        if (margenBadge) {
            margenBadge.textContent = `${margen.toFixed(2)}%`;
            margenBadge.className   = 'badge';
            margenBadge.classList.add(utilidad > 0 ? 'bg-success' : utilidad < 0 ? 'bg-danger' : 'bg-secondary');
        }

        // 5. Informe Ejecutivo de Cierre (Fase 4)
        initInformeCierre();
    }

    /**
     * Rellena el panel de cotizacion con datos completos (v3.9.6).
     * Acepta el dict cotizacion_info de la API o un objeto construido desde data-* attrs.
     */
    function renderizarCotizacionInfo(info) {
        const ESTADO_BADGE = {
            'ACEPTADA':  'bg-success',
            'ENVIADA':   'bg-primary',
            'BORRADOR':  'bg-secondary',
            'CANCELADA': 'bg-danger',
        };
        const estadoBadge = d.getElementById('cot-estado-badge');
        const numEl       = d.getElementById('cot-numero');
        const totalEl     = d.getElementById('cot-total');
        const clienteEl   = d.getElementById('cot-cliente');
        const fechaEmEl   = d.getElementById('cot-fecha-emision');
        const fechaVenEl  = d.getElementById('cot-fecha-vencimiento');
        const uuidEl      = d.getElementById('cotizacion-uuid-display');

        if (!info) {
            [estadoBadge, numEl, totalEl, clienteEl, fechaEmEl, fechaVenEl].forEach(el => {
                if (el) el.textContent = '---';
            });
            return;
        }

        if (estadoBadge) {
            estadoBadge.textContent = info.estado || '---';
            estadoBadge.className   = `badge ${ESTADO_BADGE[info.estado] || 'bg-secondary'}`;
        }
        if (numEl)    numEl.textContent    = info.numero_cotizacion || info.cotizacion_numero || '---';
        if (totalEl) {
            const total = (info.total_con_impuestos != null) ? info.total_con_impuestos : info.total;
            totalEl.textContent = (total != null && total !== '' && !isNaN(total))
                // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
                ? ((w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
                    ? w.DOMUtils.formatCurrency(total, { maximumFractionDigits: 0 })
                    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(total))
                : '---';
        }
        if (clienteEl)  clienteEl.textContent  = info.cliente_razon_social || info.cliente || '---';
        if (fechaEmEl)  fechaEmEl.textContent   = info.fecha_emision  || '---';
        if (fechaVenEl) fechaVenEl.textContent  = info.fecha_vencimiento || '---';
        if (uuidEl)     uuidEl.textContent      = info.uuid || info.cotizacion_uuid || '';
    }

    /**
     * Lee los data-cot-* de la <option> seleccionada y renderiza el panel completo (v3.9.6).
     */
    function actualizarPanelCotizacion(selectEl) {
        const panelVinculada = d.querySelector('#panel-cotizacion-vinculada');
        const panelSin       = d.querySelector('#panel-sin-cotizacion');

        if (!panelVinculada || !panelSin) return;

        panelVinculada.classList.add('d-none');
        panelSin.classList.add('d-none');

        if (!selectEl || !selectEl.value) return;

        const opt             = selectEl.options[selectEl.selectedIndex];
        const cotizacionUuid  = opt ? (opt.getAttribute('data-cotizacion-uuid')   || '') : '';
        const cotizacionNumero= opt ? (opt.getAttribute('data-cotizacion-numero') || '') : '';

        if (cotizacionUuid || cotizacionNumero) {
            renderizarCotizacionInfo({
                uuid:              cotizacionUuid,
                cotizacion_numero: cotizacionNumero,
                estado:            opt.getAttribute('data-cot-estado')            || '',
                total:             parseFloat(opt.getAttribute('data-cot-total')  || '0'),
                cliente:           opt.getAttribute('data-cot-cliente')           || '',
                fecha_emision:     opt.getAttribute('data-cot-fecha-emision')     || '',
                fecha_vencimiento: opt.getAttribute('data-cot-fecha-vencimiento') || '',
            });
            panelVinculada.classList.remove('d-none');
        } else {
            panelSin.classList.remove('d-none');
        }
    }

    /**
     * Cargar centros de costos de forma asincrona (Fase 4 - legacy)
     */
    async function cargarCentrosCostos(selectElement) {
        if (!w.proyectosAPI || typeof w.proyectosAPI.fetchCentrosCostos !== 'function') {
            console.error(`${MOD} proyectosAPI.fetchCentrosCostos no disponible`);
            return;
        }

        const initialValue = selectElement.getAttribute('data-initial-value');

        const res = await w.proyectosAPI.fetchCentrosCostos();
        if (!res.ok) {
            console.error(`${MOD} Error al cargar centros de costos:`, res);
            selectElement.innerHTML = '<option value="">Error al cargar facturas</option>';
            return;
        }

        const facturas = res.data || [];
        let html = '<option value="">-- Seleccionar Factura (Opcional) --</option>';

        facturas.forEach(f => {
            const selected = (initialValue && (initialValue == f.id || initialValue == f.uuid)) ? 'selected' : '';
            html += `<option value="${f.id}" data-numero="${f.numero}" ${selected}>${f.numero} - ${f.receptor_nombre || 'S/N'}</option>`;
        });

        selectElement.innerHTML = html;
        console.log(`${MOD} ${facturas.length} centros de costos cargados`);
    }

    /**
     * Buscador de movimientos de inventario (Pull Model v3.8+).
     * Reemplaza cargarServicios() y el select de servicio_asociado.
     */
    function initMovimientoSearch() {
        const searchInput = d.querySelector('#proyecto-movimiento-inventario-search');
        const uuidInput = d.querySelector('#proyecto-movimiento-inventario-uuid');
        const suggestions = d.querySelector('#proyecto-movimiento-inventario-suggestions');

        if (!searchInput || !uuidInput || !suggestions) return;

        const currentLabel = searchInput.dataset.currentLabel;
        if (currentLabel && uuidInput.value && !searchInput.value) {
            searchInput.value = currentLabel;
        }

        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();
            if (query.length < 2) {
                suggestions.classList.add('d-none');
                return;
            }
            debounceTimer = setTimeout(async () => {
                try {
                    const url = w.proyectosAPI.searchMovimientos(query);
                    const res = await w.Sintel.Core.Http.request('GET', url);
                    const items = (res.data && res.data.results) ? res.data.results : [];
                    renderMovimientoSuggestions(items, suggestions, searchInput, uuidInput);
                } catch (err) {
                    console.error(`${MOD} Error buscando movimientos:`, err);
                }
            }, 300);
        });

        searchInput.addEventListener('change', () => {
            if (!searchInput.value.trim()) uuidInput.value = '';
        });

        d.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });
    }

    function renderMovimientoSuggestions(items, container, searchInput, uuidInput) {
        if (items.length === 0) {
            container.innerHTML = '<div class="list-group-item small text-muted">No se encontraron movimientos</div>';
        } else {
            container.innerHTML = items.map(m => {
                const label = `${m.item_tipo || ''}: ${m.item_nombre || ''} (${m.tipo_display || m.tipo || ''})`;
                const sub = m.item_codigo ? `Cod: ${m.item_codigo} · Cant: ${m.cantidad || ''}` : `Cant: ${m.cantidad || ''}`;
                return `<button type="button" class="list-group-item list-group-item-action small py-2"
                            data-uuid="${m.id}" data-label="${label}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><strong>${m.item_nombre || ''}</strong> — ${m.tipo_display || m.tipo || ''}</span>
                        <span class="badge bg-light text-muted">${m.item_tipo || ''}</span>
                    </div>
                    <small class="text-muted">${sub}</small>
                </button>`;
            }).join('');
        }
        container.classList.remove('d-none');
        container.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                searchInput.value = btn.dataset.label;
                uuidInput.value = btn.dataset.uuid;
                container.classList.add('d-none');
            });
        });
    }

    /**
     * Carga todos los detalles del proyecto vía API GET (para poblar el wizard tras el renderizado de la UI)
     */
    async function cargarDetallesProyecto(uuid) {
        if (!uuid) return;

        console.log(`${MOD} Cargando detalles completos para proyecto: ${uuid}`);

        const res = await w.proyectosAPI.get(uuid);
        if (!res.ok) {
            console.error(`${MOD} Error al cargar detalles del proyecto`, res);
            return;
        }

        currentProyecto = res.data;

        // Configurar porcentaje avance bubble
        const slider = d.querySelector('#proyecto-porcentaje-avance');
        const bubble = d.querySelector('#porcentaje-avance-bubble');
        if (slider && bubble) {
            slider.value = currentProyecto.porcentaje_avance || 0;
            bubble.textContent = `${slider.value}%`;
        }

        // Sincronizar selectores de personas con sus IDs iniciales
        const syncSelectInitial = (selectId, value) => {
            const select = d.querySelector(`#${selectId}`);
            if (select && value) {
                select.value = value;
            }
        };

        syncSelectInitial('proyecto-cliente-select', currentProyecto.cliente_id);
        syncSelectInitial('proyecto-responsable-comercial-select', currentProyecto.responsable_comercial_id);
        syncSelectInitial('proyecto-responsable-operativo-select', currentProyecto.responsable_operativo_id);
        syncSelectInitial('proyecto-responsable-administrativo-select', currentProyecto.responsable_administrativo_id);

        // Sincronizar buscador de Movimiento de Inventario (Pull Model v3.8+)
        const movSearchInput = d.querySelector('#proyecto-movimiento-inventario-search');
        const movUuidInput = d.querySelector('#proyecto-movimiento-inventario-uuid');
        if (movSearchInput && movUuidInput) {
            const movUuid = currentProyecto.movimiento_inventario_uuid;
            const movRef = currentProyecto.movimiento_referencia;
            if (movUuid && typeof movUuid === 'string' && movUuid.length === 36) {
                movUuidInput.value = movUuid;
                if (movRef && !movSearchInput.value) {
                    movSearchInput.value = `${movRef.item_tipo || ''}: ${movRef.item_nombre || ''} (${movRef.tipo_display || ''})`;
                }
            } else {
                movUuidInput.value = '';
                movSearchInput.value = '';
            }
        }

        // Sincronizar selector de Factura de Venta — API retorna 'factura_costo' (sin _id)
        const facturaVentaSelectEl = d.querySelector('#proyecto-factura-venta-select');
        const facturaIdInput       = d.querySelector('#proyecto-factura-costo-id');
        const facturaNumeroInput   = d.querySelector('#proyecto-factura-costo-numero');
        const facturaCostaVal      = currentProyecto.factura_costo; // integer PK o null
        if (facturaVentaSelectEl && facturaCostaVal) {
            facturaVentaSelectEl.value = facturaCostaVal;
            // Sync hidden inputs desde la opción seleccionada
            const opt = facturaVentaSelectEl.options[facturaVentaSelectEl.selectedIndex];
            if (opt && opt.value) {
                if (facturaIdInput)     facturaIdInput.value     = opt.value;
                if (facturaNumeroInput && !facturaNumeroInput.value)
                    facturaNumeroInput.value = opt.getAttribute('data-numero') || '';
            }
            actualizarPanelCotizacion(facturaVentaSelectEl);
        }

        // Si la API retorna cotizacion_info completa (v3.9.6), usar datos enriquecidos
        if (currentProyecto.cotizacion_info) {
            const panelVinculada = d.getElementById('panel-cotizacion-vinculada');
            const panelSin       = d.getElementById('panel-sin-cotizacion');
            if (panelVinculada) panelVinculada.classList.add('d-none');
            if (panelSin)       panelSin.classList.add('d-none');
            renderizarCotizacionInfo(currentProyecto.cotizacion_info);
            if (panelVinculada) panelVinculada.classList.remove('d-none');
        }

        // Renderizar candados y navegar al Step de la fase actual
        renderStepLocks();
        
        const currentFase = currentProyecto.fase_actual || 'BORRADOR';
        const targetStep = phaseMap[currentFase] || 0;
        irAStep(targetStep);

        // Rellenar información dinámica de los steps
        populateStepDetails();
    }

    /**
     * Aplica los valores de pre-llenado provenientes del historial del servicio (v3.9.7)
     */
    function aplicarPrefill(prefill) {
        if (!prefill) return;
        console.log(`${MOD} Aplicando prefill desde historial de servicio:`, prefill);
        
        const nombreInput = d.querySelector('#proyecto-nombre');
        if (nombreInput) nombreInput.value = prefill.nombre || '';
        
        const valorInput = d.querySelector('#proyecto-valor-contrato-proyectado');
        if (valorInput) {
            valorInput.value = prefill.valor_contrato || '0';
        } else {
            const valorInputAlt = d.querySelector('#proyecto-valor');
            if (valorInputAlt) valorInputAlt.value = prefill.valor_contrato || '0';
        }

        const historialInput = d.querySelector('#proyecto-historial-uuid');
        if (historialInput) historialInput.value = prefill.historial_uuid || '';
    }

    /**
     * Configurar todos los event listeners del editor
     * ⚠️ Ejecuta una ÚNICA VEZ para evitar acumulación de listeners
     */
    function initEditorEvents() {
        if (editorEventsInitialized) {
            console.log(`${MOD} Listeners ya inicializados, saltando...`);
            return;
        }
        editorEventsInitialized = true;

        // Inicializar buscador de movimientos de inventario (Pull Model v3.8+)
        initMovimientoSearch();

        const form = d.querySelector('#form-proyecto');
        if (!form) {
            console.warn(`${MOD} Formulario #form-proyecto no encontrado`);
            return;
        }

        // 1. Submit del formulario
        // Guard adicional (FE-A2): `editorEventsInitialized` se resetea al
        // cerrar el offcanvas para permitir reinicializar en la siguiente
        // apertura, pero si el offcanvas/form NO se recrea (mismo nodo DOM
        // reutilizado), ese reset permitia volver a registrar el submit sobre
        // el mismo <form> -> doble POST confirmado en produccion (auditoria
        // 2026-07-26). Este guard ata la proteccion al nodo <form> real, no
        // solo al flag de modulo que ya se demostro insuficiente.
        if (!form.dataset.submitBound) {
            form.dataset.submitBound = 'true';
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                guardarProyecto();
            });
        }

        // 2. Sincronización dinámica de selectores bajo el principio "DOM Shield"
        const setupSelectorSync = (selectId, idInputId, nameInputId, extractNamePattern = null) => {
            const select = form.querySelector(`#${selectId}`);
            const idInput = form.querySelector(`#${idInputId}`);
            const nameInput = form.querySelector(`#${nameInputId}`);

            if (select && idInput && nameInput) {
                select.addEventListener('change', (e) => {
                    if (e.target.value) {
                        const selectedOption = e.target.options[e.target.selectedIndex];
                        if (selectedOption) {
                            idInput.value = e.target.value;
                            
                            let valName = selectedOption.text.trim();
                            if (extractNamePattern) {
                                const match = valName.match(extractNamePattern);
                                if (match) {
                                    valName = match[1].trim();
                                }
                            }
                            nameInput.value = valName;
                        }
                    } else {
                        idInput.value = '';
                        nameInput.value = '';
                    }
                });
            }
        };

        // Clientes
        setupSelectorSync('proyecto-cliente-select', 'proyecto-cliente-id', 'proyecto-cliente-nombre', /^(.+?)\s*\(/);

        // Responsables por fases
        setupSelectorSync('proyecto-responsable-comercial-select', 'proyecto-responsable-comercial-id', 'proyecto-responsable-comercial-nombre');
        setupSelectorSync('proyecto-responsable-operativo-select', 'proyecto-responsable-operativo-id', 'proyecto-responsable-operativo-nombre');
        setupSelectorSync('proyecto-responsable-administrativo-select', 'proyecto-responsable-administrativo-id', 'proyecto-responsable-administrativo-nombre');

        // === Servicio Asociado (UUID-Safe) — Fase 0 ===
        const servicioSelect = form.querySelector('#proyecto-servicio-asociado-select');
        const servicioInput = form.querySelector('#proyecto-servicio-asociado');
        if (servicioSelect && servicioInput) {
            // Inicializar correctamente en caso de que servicioInput tenga "undefined"
            const initialValue = servicioInput.value;
            if (!initialValue || initialValue === 'undefined' || initialValue === 'None') {
                servicioInput.value = '';
            }

            servicioSelect.addEventListener('change', (e) => {
                // ⚠️ UUID-Safe: solo asignar UUID válido, NUNCA "undefined"
                const selectedValue = e.target.value || '';
                if (selectedValue && selectedValue !== 'undefined') {
                    servicioInput.value = selectedValue;
                } else {
                    servicioInput.value = '';
                }
            });
        }

        // === Sincronizar estado_tarea (Step 0 y Step 4 comparten el mismo campo) ===
        const estadoStep0 = form.querySelector('#proyecto-estado');
        const estadoStep4 = form.querySelector('#proyecto-estado-tarea');
        if (estadoStep0 && estadoStep4) {
            estadoStep0.addEventListener('change', () => { estadoStep4.value = estadoStep0.value; });
            estadoStep4.addEventListener('change', () => { estadoStep0.value = estadoStep4.value; });
        }

        // === Factura de Venta (Fase 1) — DOM Shield + Panel Cotizacion ===
        const facturaVentaSelect = form.querySelector('#proyecto-factura-venta-select');
        const facturaIdInput = form.querySelector('#proyecto-factura-costo-id');
        const facturaNumeroInput = form.querySelector('#proyecto-factura-costo-numero');

        if (facturaVentaSelect) {
            // Inicializar panel al cargar (si hay factura preseleccionada)
            actualizarPanelCotizacion(facturaVentaSelect);

            facturaVentaSelect.addEventListener('change', (e) => {
                const selectedOption = e.target.options[e.target.selectedIndex];
                if (e.target.value && selectedOption) {
                    if (facturaIdInput) facturaIdInput.value = e.target.value;
                    const numero = selectedOption.getAttribute('data-numero') || selectedOption.text.trim();
                    if (facturaNumeroInput) facturaNumeroInput.value = numero;
                } else {
                    if (facturaIdInput) facturaIdInput.value = '';
                    if (facturaNumeroInput) facturaNumeroInput.value = '';
                }
                actualizarPanelCotizacion(e.target);
            });
        }

        // Factura legacy Fase 4 (Centro de Costos)
        const CCSelect = form.querySelector('#proyecto-factura-costo:not(#proyecto-factura-venta-select)');
        if (CCSelect) {
            cargarCentrosCostos(CCSelect);
            CCSelect.addEventListener('change', (e) => {
                const selectedOption = e.target.options[e.target.selectedIndex];
                if (e.target.value && selectedOption) {
                    if (facturaIdInput) facturaIdInput.value = e.target.value;
                    const numero = selectedOption.getAttribute('data-numero');
                    if (numero && facturaNumeroInput) facturaNumeroInput.value = numero;
                } else {
                    if (facturaIdInput) facturaIdInput.value = '';
                    if (facturaNumeroInput) facturaNumeroInput.value = '';
                }
            });
        }

        // 3. Slider de avance (Fase 4 - Informe Ejecutivo)
        const slider = form.querySelector('#proyecto-porcentaje-avance');
        const bubble = form.querySelector('#porcentaje-avance-bubble');
        const display = form.querySelector('#porcentaje-avance-display');
        if (slider) {
            slider.addEventListener('input', (e) => {
                if (bubble) bubble.textContent = `${e.target.value}%`;
                if (display) display.textContent = `${e.target.value}%`;
            });
        }

        // 3.5. Presupuesto Manual (v3.5.2) - Botones y listeners (delegados para evitar duplicados)

        // 4. Stepper click nodes (SOLO permitir si NO está locked)
        const nodes = d.querySelectorAll('#offcanvas-proyecto .step-node');
        nodes.forEach(node => {
            node.addEventListener('click', () => {
                const stepIdx = parseInt(node.getAttribute('data-step'));
                // Validación: solo permitir navegar a fases UNLOCKED (no tienen clase 'locked')
                if (node.classList.contains('locked')) {
                    if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                        w.SintelFeedback.warning(`Fase ${stepIdx} bloqueada. Completa la fase anterior primero.`);
                    }
                    return;
                }
                irAStep(stepIdx);
            });
        });

        // 5. Botones de Navegación del Wizard
        const btnBack = d.querySelector('#btn-wizard-back');
        if (btnBack) {
            btnBack.addEventListener('click', () => {
                if (currentStep > 0) {
                    irAStep(currentStep - 1);
                }
            });
        }

        const btnNext = d.querySelector('#btn-wizard-next');
        if (btnNext) {
            btnNext.addEventListener('click', async () => {
                if (currentStep >= 4) return;

                // Validar campos requeridos del step actual
                if (currentStep === 0) {
                    const nombre = d.querySelector('#proyecto-nombre')?.value?.trim();
                    if (!nombre) {
                        const fb = d.querySelector('#form-proyecto-feedback');
                        if (fb) {
                            fb.classList.remove('d-none');
                            fb.textContent = 'El nombre del proyecto es obligatorio para continuar.';
                        }
                        d.querySelector('#proyecto-nombre')?.focus();
                        return;
                    }
                }

                // Guardar silenciosamente antes de avanzar al siguiente paso
                const uuid = d.querySelector('#proyecto-uuid')?.value;
                if (uuid) {
                    btnNext.disabled = true;
                    btnNext.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
                    const saved = await guardarProyecto(true);
                    btnNext.disabled = false;
                    btnNext.innerHTML = 'Continuar<i class="bi bi-arrow-right ms-1"></i>';
                    if (saved === false) return; // Detener si el guardado falló
                }

                irAStep(currentStep + 1);
            });
        }

        // Submit button "Guardar Todo"
        const btnSave = d.querySelector('#btn-wizard-save');
        if (btnSave) {
            btnSave.addEventListener('click', (e) => {
                e.preventDefault();
                guardarProyecto();
            });
        }

        // 6. Event listeners centralizados en offcanvas (delegados para evitar duplicados)
        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        if (offcanvasEl && !presupuestoListenersInitialized) {
            // Click delegado: Presupuesto agregar botón (ejecuta solo UNA VEZ globalmente)
            // [FIX] el boton solo contiene un <i> (icono bi-plus) -- un click
            // sobre el icono (100% del area visible del boton) pone
            // e.target = <i>, nunca el <button> con el id, asi que
            // `e.target?.id === ...` nunca coincidia (bug real reportado:
            // el "+" no agregaba nada). `.closest()` matchea el click tanto
            // sobre el boton como sobre cualquier hijo suyo (el icono).
            offcanvasEl.addEventListener('click', (e) => {
                if (e.target?.closest?.('#btn-agregar-presupuesto')) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    w.Sintel.ProyectosPresupuesto.agregar();
                }
            });

            offcanvasEl.addEventListener('keypress', (e) => {
                if (['pres-categoria', 'pres-descripcion', 'pres-cantidad', 'pres-valor-unitario'].includes(e.target?.id) && e.key === 'Enter') {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    w.Sintel.ProyectosPresupuesto.agregar();
                }
            });

            // Click delegado: Tareas Diarias agregar botón
            // [FIX] mismo bug que btn-agregar-presupuesto arriba -- el
            // icono <i class="bi bi-plus"> dentro del boton hacia que un
            // click sobre el icono nunca coincidiera con el id exacto.
            offcanvasEl.addEventListener('click', (e) => {
                if (e.target?.closest?.('#btn-agregar-tarea')) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    w.Sintel.TareasDiarias.agregar();
                }
            });

            // Limpieza al cerrar offcanvas
            offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
                const errorContainer = d.querySelector('#form-proyecto-feedback');
                if (errorContainer) {
                    errorContainer.classList.add('d-none');
                    errorContainer.textContent = '';
                }
                // Reset flags para siguiente apertura
                editorEventsInitialized = false;
                presupuestoListenersInitialized = false;
            });

            presupuestoListenersInitialized = true;
        }

        console.log(`${MOD} Event listeners del editor configurados`);
    }

    // Inicialización principal del módulo
    function init() {
        console.log(`${MOD} Inicializando módulo de editor...`);

        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        if (offcanvasEl) {
            initEditorEvents();
            const uuid = d.querySelector('#proyecto-uuid')?.value;
            if (uuid) {
                cargarDetallesProyecto(uuid);
            } else {
                currentProyecto = null;
                irAStep(0);
                renderStepLocks();
                if (window._proyectoPrefill) {
                    aplicarPrefill(window._proyectoPrefill);
                    window._proyectoPrefill = null;
                }
            }
        } else {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1 && node.id === 'offcanvas-proyecto') {
                            initEditorEvents();
                            const uuid = d.querySelector('#proyecto-uuid')?.value;
                            if (uuid) {
                                cargarDetallesProyecto(uuid);
                            } else {
                                currentProyecto = null;
                                irAStep(0);
                                renderStepLocks();
                                if (window._proyectoPrefill) {
                                    aplicarPrefill(window._proyectoPrefill);
                                    window._proyectoPrefill = null;
                                }
                            }
                            observer.disconnect();
                        }
                    });
                });
            });

            const container = d.querySelector('#offcanvas-container-proyectos');
            if (container) {
                observer.observe(container, { childList: true, subtree: true });
            }
        }
    }

    // Escuchar el evento de click en avanzar fase en todo el documento
    // Guard: registrado en `document`, persiste entre recargas HTMX del
    // modulo "proyectos" — sin este guard, cada recarga del script duplica
    // el listener global (FE-A1/A2).
    if (!d.body.dataset.avanzarFaseListenerInitialized) {
        d.body.dataset.avanzarFaseListenerInitialized = 'true';
        d.addEventListener('click', async (e) => {
            const btn = e.target.closest('.btn-avanzar-fase-action');
            if (btn) {
                const targetFase = btn.getAttribute('data-target-fase');
                // ⚠️ Guardar cambios sucios del formulario de forma silenciosa antes de avanzar de fase
                const guardadoExitoso = await guardarProyecto(true);
                if (guardadoExitoso) {
                    await avanzarFaseProyecto(targetFase);
                }
            }
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // htmx:afterSettle garantiza DOM estable — no usar afterSwap (AGENTS.md §26 + skill htmx.md §12)
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSettle', (event) => {
            const targetId = event.detail.target.id;
            if (targetId === 'offcanvas-container-proyectos' || targetId === 'offcanvas-container-movimientos') {
                const offcanvasEl = d.getElementById('offcanvas-proyecto');
                if (offcanvasEl) {
                    initEditorEvents();

                    const uuid = d.querySelector('#proyecto-uuid')?.value;
                    if (uuid) {
                        cargarDetallesProyecto(uuid);
                    } else {
                        currentProyecto = null;
                        irAStep(0);
                        renderStepLocks();
                        if (window._proyectoPrefill) {
                            aplicarPrefill(window._proyectoPrefill);
                            window._proyectoPrefill = null;
                        }
                    }

                    if (w.UIManager?.handleOffcanvas) {
                        w.UIManager.handleOffcanvas(offcanvasEl, 'show');
                    } else if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (NUNCA getOrCreateInstance — §26)
                        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                    }
                }
            }
        });
    }

    // ============================================================================
    // MÓDULO: Presupuesto Manual (v3.5.2)
    // ============================================================================
    const ProyectosPresupuesto = {
        _items: [],
        _proyectoUuid: null,

        async init(proyectoUuid, enCierre = false) {
            if (!proyectoUuid) return;
            this._proyectoUuid = proyectoUuid;

            // Cargar items desde API
            const resp = await w.proyectosAPI.presupuesto.list(proyectoUuid);
            if (!resp.ok) {
                console.error(`${MOD} Error al cargar presupuesto:`, resp);
                this._items = [];
            } else {
                this._items = resp.data.results || resp.data || [];
            }

            this._render(enCierre);
            this._refreshResumen();
        },

        _render(enCierre = false) {
            const tbody = d.getElementById('tbody-presupuesto');
            if (!tbody) return;

            if (this._items.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center text-muted py-3">
                            <small><i class="bi bi-info-circle me-1"></i>Sin ítems aún. Agrega costos planeados.</small>
                        </td>
                    </tr>
                `;
                return;
            }

            let html = '';
            this._items.forEach(item => {
                const categDisplay = item.categoria_display || item.categoria;
                // El Desglose de Costos Planeados es editable/borrable
                // libremente de forma manual por defecto, sin importar el
                // origen (MANUAL o COTIZACION) -- decision explicita del
                // usuario, reemplaza la restriccion original de "item de
                // cotización = solo sincronizable". "Sincronizar costos de
                // cotización" sigue siendo solo una conveniencia opcional:
                // si se borra una línea sincronizada y se vuelve a
                // sincronizar, se re-crea desde la cotización (esperado).
                const esCotizacion = item.origen === 'COTIZACION';
                const origenBadge = esCotizacion
                    ? '<span class="badge bg-info-subtle text-info-emphasis" title="Creado por Sincronizar costos de cotización"><i class="bi bi-arrow-repeat"></i> Cotización</span>'
                    : '<span class="badge bg-secondary-subtle text-secondary-emphasis">Manual</span>';
                const btnEliminar = enCierre ? '' : `
                    <button type="button" class="btn btn-xs btn-outline-danger"
                            onclick="window.Sintel.ProyectosPresupuesto.eliminar('${item.uuid}')"
                            title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                html += `
                    <tr data-uuid="${item.uuid}">
                        <td>${origenBadge}</td>
                        <td>${categDisplay}</td>
                        <td><small>${item.descripcion || '—'}</small></td>
                        <td style="text-align: center;"><small>${item.cantidad}</small></td>
                        <td style="text-align: right;"><small>${w.proyectosAPI.formatCurrency(item.valor_unitario)}</small></td>
                        <td style="text-align: right;"><strong>${w.proyectosAPI.formatCurrency(item.subtotal)}</strong></td>
                        <td>${btnEliminar}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        },

        async agregar() {
            const categoria = d.getElementById('pres-categoria')?.value;
            const descripcion = d.getElementById('pres-descripcion')?.value || '';
            const cantidad = parseFloat(d.getElementById('pres-cantidad')?.value || 1);
            const valorUnitario = parseFloat(d.getElementById('pres-valor-unitario')?.value || 0);

            if (!categoria) {
                w.SintelFeedback?.error('Selecciona una categoría');
                return;
            }
            if (valorUnitario <= 0) {
                w.SintelFeedback?.error('El valor unitario debe ser mayor a 0');
                return;
            }

            const data = {
                proyecto_uuid: this._proyectoUuid,
                categoria: categoria,
                descripcion: descripcion,
                cantidad: cantidad,
                valor_unitario: valorUnitario
            };

            const resp = await w.proyectosAPI.presupuesto.create(data);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al agregar ítem de presupuesto');
                return;
            }

            w.SintelFeedback?.success('Ítem agregado');
            await this.init(this._proyectoUuid, currentProyecto?.fase_actual === 'CIERRE');

            // Limpiar formulario
            d.getElementById('pres-descripcion').value = '';
            d.getElementById('pres-cantidad').value = '1';
            d.getElementById('pres-valor-unitario').value = '';
            d.getElementById('pres-categoria').value = '';
        },

        async eliminar(itemId) {
            if (!(await w.UIManager?.confirm('¿Eliminar este ítem de presupuesto?'))) return;

            const resp = await w.proyectosAPI.presupuesto.delete(itemId);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al eliminar ítem');
                return;
            }

            w.SintelFeedback?.success('Ítem eliminado');
            await this.init(this._proyectoUuid, currentProyecto?.fase_actual === 'CIERRE');
        },

        _refreshResumen() {
            // BASE: valor_contrato_proyectado es la base de todos los calculos
            const total    = this._items.reduce((sum, item) => sum + (parseFloat(item.subtotal) || 0), 0);
            const contrato = parseFloat(currentProyecto?.valor_contrato_proyectado || 0);
            // utilidad_planeada = valor_contrato - costo_planeado_total
            const utilidad = contrato - total;
            // margen_planeado % = utilidad_planeada / valor_contrato * 100
            const margen   = contrato > 0 ? (utilidad / contrato * 100) : 0;

            const setResumen = (id, val) => { const el = d.getElementById(id); if (el) el.textContent = val; };
            setResumen('pres-resumen-contrato', w.proyectosAPI.formatCurrency(contrato));
            setResumen('pres-resumen-costos',   w.proyectosAPI.formatCurrency(total));
            setResumen('pres-resumen-utilidad', w.proyectosAPI.formatCurrency(utilidad));

            // Margen % con color dinamico
            const margenEl = d.getElementById('pres-resumen-margen');
            if (margenEl) {
                margenEl.textContent = `${margen.toFixed(1)}%`;
                margenEl.className   = 'fw-bold';
                margenEl.classList.add(utilidad > 0 ? 'text-success' : utilidad < 0 ? 'text-danger' : 'text-muted');
            }

            // Sincronizar Fase 4 con _items ya cargados (resuelve race condition)
            initInformeCierre();
        }
    };

    if (!w.Sintel) w.Sintel = {};
    w.Sintel.ProyectosPresupuesto = ProyectosPresupuesto;

    // ============================================================================
    // FIN MÓDULO PRESUPUESTO
    // ============================================================================

    // ============================================================================
    // MÓDULO: Cotización de Planeación
    // (PLAN_PROYECTOS_FASE_2_COTIZACION_RECURSOS_PRESUPUESTO)
    // ============================================================================
    const ProyectosCotizacionPlaneacion = {
        _proyectoUuid: null,

        async init(proyectoUuid) {
            if (!proyectoUuid) return;
            this._proyectoUuid = proyectoUuid;
            this._bindEvents();

            const resp = await w.proyectosAPI.cotizacionPlaneacion.get(proyectoUuid);
            if (!resp.ok) {
                console.error(`${MOD} Error al cargar cotizacion de planeacion:`, resp);
                this._render(null);
                return;
            }
            this._render(resp.data);
        },

        _render(data) {
            const sinVincular = d.getElementById('cotizacion-sin-vincular');
            const vinculada = d.getElementById('cotizacion-vinculada');
            if (!sinVincular || !vinculada) return;

            if (!data || !data.cotizacion) {
                sinVincular.classList.remove('d-none');
                vinculada.classList.add('d-none');
                return;
            }

            sinVincular.classList.add('d-none');
            vinculada.classList.remove('d-none');

            const cot = data.cotizacion;
            const setText = (id, text) => { const el = d.getElementById(id); if (el) el.textContent = text; };
            setText('cot-plan-numero', cot.numero || '—');
            setText('cot-plan-cliente', `Cliente: ${cot.cliente || '—'}`);
            setText('cot-plan-estado', cot.estado || '—');
            setText('cot-plan-fecha', cot.fecha_emision ? `Fecha: ${cot.fecha_emision}` : '');
            setText('cot-plan-valor-antes-iva', w.proyectosAPI.formatCurrency(cot.valor_antes_iva));

            const r = data.resumen || {};
            setText('cot-plan-mo-cotizado', w.proyectosAPI.formatCurrency(r.mano_obra && r.mano_obra.cotizado));
            setText('cot-plan-mo-costobase', w.proyectosAPI.formatCurrency(r.mano_obra && r.mano_obra.costo_base));
            setText('cot-plan-mat-cotizado', w.proyectosAPI.formatCurrency(r.materiales && r.materiales.cotizado));
            setText('cot-plan-mat-costobase', w.proyectosAPI.formatCurrency(r.materiales && r.materiales.costo_base));
            setText('cot-plan-eq-cotizado', w.proyectosAPI.formatCurrency(r.equipos && r.equipos.cotizado));
            setText('cot-plan-eq-costobase', w.proyectosAPI.formatCurrency(r.equipos && r.equipos.costo_base));
        },

        _bindEvents() {
            const btnToggle = d.getElementById('btn-vincular-cotizacion');
            const buscador = d.getElementById('cotizacion-buscador');
            const searchInput = d.getElementById('cotizacion-search');
            const suggestions = d.getElementById('cotizacion-suggestions');
            const btnDesvincular = d.getElementById('btn-desvincular-cotizacion');
            const btnSincronizar = d.getElementById('btn-sincronizar-cotizacion');

            if (btnToggle && buscador && searchInput && suggestions && !searchInput.dataset.cotPlanBound) {
                searchInput.dataset.cotPlanBound = 'true';

                btnToggle.addEventListener('click', async () => {
                    buscador.classList.toggle('d-none');
                    if (!buscador.classList.contains('d-none')) {
                        searchInput.focus();
                        await this._buscar('');
                    }
                });

                let debounceTimer;
                searchInput.addEventListener('input', (e) => {
                    clearTimeout(debounceTimer);
                    const query = e.target.value.trim();
                    debounceTimer = setTimeout(() => this._buscar(query), 300);
                });

                d.addEventListener('click', (e) => {
                    if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                        suggestions.classList.add('d-none');
                    }
                });
            }

            if (btnDesvincular && !btnDesvincular.dataset.cotPlanBound) {
                btnDesvincular.dataset.cotPlanBound = 'true';
                btnDesvincular.addEventListener('click', () => this.desvincular());
            }

            if (btnSincronizar && !btnSincronizar.dataset.cotPlanBound) {
                btnSincronizar.dataset.cotPlanBound = 'true';
                btnSincronizar.addEventListener('click', () => this.sincronizar());
            }
        },

        async _buscar(query) {
            const suggestions = d.getElementById('cotizacion-suggestions');
            if (!suggestions) return;
            const url = w.proyectosAPI.cotizacionPlaneacion.buscarAprobadas(query);
            const resp = await w.Sintel.Core.Http.request('GET', url);
            const items = resp.ok ? (resp.data.results || resp.data || []) : [];
            this._renderSuggestions(items, suggestions);
        },

        _renderSuggestions(items, container) {
            if (items.length === 0) {
                container.innerHTML = '<div class="list-group-item small text-muted">No se encontraron cotizaciones aprobadas</div>';
            } else {
                container.innerHTML = items.map(c => `
                    <button type="button" class="list-group-item list-group-item-action small py-2" data-uuid="${c.uuid}">
                        <div class="d-flex justify-content-between">
                            <span><strong>${c.numero_cotizacion || ''}</strong> — ${c.cliente_razon_social || ''}</span>
                            <span>${w.proyectosAPI.formatCurrency(c.total_con_impuestos)}</span>
                        </div>
                        <small class="text-muted">Fecha: ${c.fecha_emision || '—'}</small>
                    </button>`).join('');
            }
            container.classList.remove('d-none');
            container.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', () => this.vincular(btn.dataset.uuid));
            });
        },

        async vincular(cotizacionUuid, confirmarReemplazo = false) {
            const resp = await w.proyectosAPI.cotizacionPlaneacion.vincular(this._proyectoUuid, cotizacionUuid, confirmarReemplazo);
            if (!resp.ok) {
                // Fase 19 del plan: reemplazar una cotizacion ya vinculada
                // exige confirmacion explicita del usuario, nunca silenciosa.
                if (resp.data && resp.data.error === 'requiere_confirmacion_reemplazo') {
                    const confirmar = await w.UIManager?.confirm(resp.data.message);
                    if (confirmar) {
                        await this.vincular(cotizacionUuid, true);
                    }
                    return;
                }
                w.UIManager?.handleError(resp, 'Error al vincular la cotización');
                return;
            }
            w.SintelFeedback?.success('Cotización vinculada correctamente al proyecto.');
            d.getElementById('cotizacion-buscador')?.classList.add('d-none');
            const searchInput = d.getElementById('cotizacion-search');
            if (searchInput) searchInput.value = '';
            // El vinculo NUNCA sincroniza automaticamente (Fase 11 del plan)
            // -- solo refresca el panel de cotizacion/recursos; el
            // presupuesto se actualiza al pulsar "Sincronizar costos de
            // cotización" explicitamente.
            await this.init(this._proyectoUuid);
        },

        async desvincular() {
            if (!(await w.UIManager?.confirm('¿Desvincular la cotización de este proyecto? El presupuesto ya sincronizado se conserva como histórico.'))) return;
            const resp = await w.proyectosAPI.cotizacionPlaneacion.desvincular(this._proyectoUuid);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al desvincular la cotización');
                return;
            }
            w.SintelFeedback?.success('Cotización desvinculada del proyecto.');
            await this.init(this._proyectoUuid);
        },

        async sincronizar() {
            const resp = await w.proyectosAPI.cotizacionPlaneacion.sincronizar(this._proyectoUuid);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al sincronizar los costos de la cotización');
                return;
            }
            const r = resp.data;
            w.SintelFeedback?.success(
                `Sincronizado: ${r.items_creados} creados, ${r.items_actualizados} actualizados, ${r.items_eliminados} eliminados ` +
                `(${r.items_manuales_preservados} ítems manuales preservados).`
            );
            const ultimaSync = d.getElementById('cot-plan-ultima-sync');
            if (ultimaSync) {
                const ahora = new Date().toLocaleString('es-CO');
                ultimaSync.textContent =
                    `Última sincronización: ${ahora} — ${r.items_creados + r.items_actualizados} líneas sincronizadas, ` +
                    `${r.items_manuales_preservados} manuales preservadas.`;
            }
            // Refrescar presupuesto (tabla + resumen) y el proyecto completo
            // (KPIs costo_planeado_total/utilidad_planeada/margen_planeado,
            // Fase 31: JavaScript nunca recalcula estos, solo presenta lo
            // que ya devolvio el backend).
            await w.Sintel.ProyectosPresupuesto.init(this._proyectoUuid, currentProyecto && currentProyecto.fase_actual === 'CIERRE');
            await refrescarProyectoActual();
        }
    };

    w.Sintel.ProyectosCotizacionPlaneacion = ProyectosCotizacionPlaneacion;

    // ============================================================================
    // FIN MÓDULO Cotización de Planeación
    // ============================================================================

    // ============================================================================
    // MÓDULO GASTOS DEL PROYECTO (GASTOS_PROYECTOS_01)
    // ============================================================================

    const ProyectosGastos = {
        _proyectoUuid: null,

        async init(proyectoUuid) {
            if (!proyectoUuid) return;
            this._proyectoUuid = proyectoUuid;
            this._bindSearch();

            const resp = await w.proyectosAPI.gastos.list(proyectoUuid);
            if (!resp.ok) {
                console.error(`${MOD} Error al cargar gastos del proyecto:`, resp);
                this._render([], 0);
                return;
            }
            const data = resp.data || {};
            this._render(data.results || [], data.costo_gastos_real);
        },

        _render(items, costoGastosReal) {
            const tbody = d.getElementById('tbody-gastos-proyecto');
            if (tbody) {
                if (items.length === 0) {
                    tbody.innerHTML = `
                        <tr><td colspan="7" class="text-center text-muted py-3">
                            <small><i class="bi bi-info-circle me-1"></i>Sin gastos asociados a este proyecto.</small>
                        </td></tr>`;
                } else {
                    tbody.innerHTML = items.map(g => {
                        const estado = g.anulado
                            ? '<span class="badge bg-danger">Anulado</span>'
                            : (g.activo ? '<span class="badge bg-success">Activo</span>' : '<span class="badge bg-secondary">Inactivo</span>');
                        return `
                            <tr data-uuid="${g.uuid}">
                                <td><small>${g.fecha || '—'}</small></td>
                                <td><small>${g.numero_documento || '—'}</small></td>
                                <td><small>${g.proveedor_nombre || '—'}</small></td>
                                <td><small>${g.descripcion || '—'}</small></td>
                                <td class="text-end"><small>${w.proyectosAPI.formatCurrency(g.subtotal)}</small></td>
                                <td>${estado}</td>
                                <td>
                                    <button type="button" class="btn btn-xs btn-outline-danger"
                                            onclick="window.Sintel.ProyectosGastos.desvincular('${g.uuid}')"
                                            title="Desvincular">
                                        <i class="bi bi-x-circle"></i>
                                    </button>
                                </td>
                            </tr>`;
                    }).join('');
                }
            }

            const totalEl = d.getElementById('gastos-proyecto-total');
            if (totalEl) {
                const total = costoGastosReal !== undefined
                    ? parseFloat(costoGastosReal) || 0
                    : items.reduce((s, g) => s + (parseFloat(g.subtotal) || 0), 0);
                totalEl.textContent = w.proyectosAPI.formatCurrency(total);
            }
        },

        _bindSearch() {
            const btnToggle = d.getElementById('btn-agregar-gasto-proyecto');
            const buscador = d.getElementById('gasto-proyecto-buscador');
            const searchInput = d.getElementById('gasto-proyecto-search');
            const suggestions = d.getElementById('gasto-proyecto-suggestions');
            if (!btnToggle || !buscador || !searchInput || !suggestions) return;
            if (searchInput.dataset.gastosBound === 'true') return;
            searchInput.dataset.gastosBound = 'true';

            btnToggle.addEventListener('click', () => {
                buscador.classList.toggle('d-none');
                if (!buscador.classList.contains('d-none')) searchInput.focus();
            });

            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                const query = e.target.value.trim();
                if (query.length < 2) {
                    suggestions.classList.add('d-none');
                    return;
                }
                debounceTimer = setTimeout(async () => {
                    const resp = await w.Sintel.Core.Http.request('GET', w.proyectosAPI.gastos.search(query));
                    const items = resp.ok ? (resp.data.results || resp.data || []) : [];
                    this._renderSuggestions(items, suggestions, searchInput);
                }, 300);
            });

            d.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                    suggestions.classList.add('d-none');
                }
            });
        },

        _renderSuggestions(items, container, searchInput) {
            if (items.length === 0) {
                container.innerHTML = '<div class="list-group-item small text-muted">No se encontraron gastos</div>';
            } else {
                // Gastos sin proyecto primero, para reducir errores de doble asignacion.
                const ordenados = [...items].sort((a, b) => (a.proyecto_uuid ? 1 : 0) - (b.proyecto_uuid ? 1 : 0));
                container.innerHTML = ordenados.map(g => {
                    const yaAsociado = g.proyecto_uuid ? ' <span class="badge bg-warning text-dark">Ya asociado a otro proyecto</span>' : '';
                    return `<button type="button" class="list-group-item list-group-item-action small py-2" data-uuid="${g.uuid}">
                        <div class="d-flex justify-content-between">
                            <span><strong>${g.ds_vendedor || ''}</strong> — ${g.ds_numero_documento || ''}</span>
                            <span>${w.proyectosAPI.formatCurrency(g.ds_subtotal)}</span>
                        </div>
                        <small class="text-muted">${g.descripcion || ''}</small>${yaAsociado}
                    </button>`;
                }).join('');
            }
            container.classList.remove('d-none');
            container.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', () => this.agregar(btn.dataset.uuid));
            });
        },

        async agregar(gastoUuid) {
            const resp = await w.proyectosAPI.gastos.agregar(gastoUuid, this._proyectoUuid);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al asociar el gasto al proyecto');
                return;
            }
            w.SintelFeedback?.success('Gasto asociado correctamente. Costo del proyecto actualizado.');
            d.getElementById('gasto-proyecto-buscador')?.classList.add('d-none');
            d.getElementById('gasto-proyecto-search').value = '';
            await this.init(this._proyectoUuid);
            await refrescarProyectoActual();
        },

        async desvincular(gastoUuid) {
            if (!(await w.UIManager?.confirm('¿Desvincular este gasto del proyecto?'))) return;

            const resp = await w.proyectosAPI.gastos.desvincular(gastoUuid);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al desvincular el gasto');
                return;
            }
            w.SintelFeedback?.success('Gasto desvinculado. Costo del proyecto actualizado.');
            await this.init(this._proyectoUuid);
            await refrescarProyectoActual();
        }
    };

    w.Sintel.ProyectosGastos = ProyectosGastos;

    /**
     * Recarga currentProyecto desde la API y refresca el panel de
     * indicadores financieros tras una mutacion de Gastos (el costo real
     * cambio en el backend, pero currentProyecto en memoria quedo obsoleto).
     */
    async function refrescarProyectoActual() {
        if (!currentProyecto?.uuid) return;
        const resp = await w.proyectosAPI.get(currentProyecto.uuid);
        if (resp.ok) {
            currentProyecto = resp.data;
            populateStepDetails();
        }
    }

    // ============================================================================
    // FIN MÓDULO GASTOS DEL PROYECTO
    // ============================================================================

    // ============================================================================
    // MÓDULO ÓRDENES DE COMPRA DEL PROYECTO
    // (PLAN_INTEGRACION_PROYECTOS_ORDENES_COMPRA_VENTA_OPCIONAL)
    // ============================================================================

    const ProyectosOrdenesCompra = {
        _proyectoUuid: null,

        async init(proyectoUuid, faseActual) {
            if (!proyectoUuid) return;
            this._proyectoUuid = proyectoUuid;

            // El bloque siempre existe en el DOM (mismo patron que Gastos);
            // un proyecto NUEVO guardado dentro de la misma apertura del
            // offcanvas pasa aqui de "sin guardar" a "contenido real" sin
            // necesidad de reabrir el offcanvas.
            d.getElementById('ordenes-compra-sin-guardar')?.classList.add('d-none');
            d.getElementById('ordenes-compra-contenido')?.classList.remove('d-none');

            this._bindSearch();

            // Regla B / FASE 6 del plan: el botón solo aparece en fase BORRADOR
            // -- el backend (ordenes_compra_disponibles/asociar) rechaza igual
            // la operación fuera de esa fase, esto es solo UX.
            const btnToggle = d.getElementById('btn-agregar-orden-compra');
            if (btnToggle) {
                btnToggle.classList.toggle('d-none', faseActual !== 'BORRADOR');
            }

            const resp = await w.proyectosAPI.ordenesCompra.list(proyectoUuid);
            if (!resp.ok) {
                console.error(`${MOD} Error al cargar ordenes de compra del proyecto:`, resp);
                this._render({ ordenes: [] });
                return;
            }
            this._render(resp.data || {});
        },

        _render(data) {
            const items = data.ordenes || [];
            const tbody = d.getElementById('tbody-ordenes-compra-proyecto');
            if (tbody) {
                if (items.length === 0) {
                    tbody.innerHTML = `
                        <tr><td colspan="7" class="text-center text-muted py-3">
                            <small><i class="bi bi-info-circle me-1"></i>Sin órdenes de compra asociadas a este proyecto.</small>
                        </td></tr>`;
                } else {
                    tbody.innerHTML = items.map(o => `
                        <tr data-uuid="${o.uuid}">
                            <td><small>${o.numero_documento || '—'}</small></td>
                            <td><small>${o.proveedor || '—'}</small></td>
                            <td><small>${o.fecha || '—'}</small></td>
                            <td><span class="badge bg-secondary">${o.estado || '—'}</span></td>
                            <td class="text-end"><small>${w.proyectosAPI.formatCurrency(o.total)}</small></td>
                            <td class="text-end"><small>${w.proyectosAPI.formatCurrency(o.total_recibido)}</small></td>
                            <td class="text-end"><small>${w.proyectosAPI.formatCurrency(o.saldo_pendiente)}</small></td>
                        </tr>`).join('');
                }
            }

            const setEl = (id, value) => {
                const el = d.getElementById(id);
                if (el) el.textContent = w.proyectosAPI.formatCurrency(value);
            };
            setEl('ordenes-compra-comprometido', data.comprometido);
            setEl('ordenes-compra-recibido', data.recibido);
            setEl('ordenes-compra-pendiente', data.pendiente);
        },

        _bindSearch() {
            const btnToggle = d.getElementById('btn-agregar-orden-compra');
            const buscador = d.getElementById('orden-compra-buscador');
            const searchInput = d.getElementById('orden-compra-search');
            const suggestions = d.getElementById('orden-compra-suggestions');
            if (!btnToggle || !buscador || !searchInput || !suggestions) return;
            if (searchInput.dataset.ordenesCompraBound === 'true') return;
            searchInput.dataset.ordenesCompraBound = 'true';

            btnToggle.addEventListener('click', async () => {
                buscador.classList.toggle('d-none');
                if (!buscador.classList.contains('d-none')) {
                    searchInput.focus();
                    await this._buscar('');
                }
            });

            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                const query = e.target.value.trim();
                debounceTimer = setTimeout(() => this._buscar(query), 300);
            });

            d.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                    suggestions.classList.add('d-none');
                }
            });
        },

        async _buscar(query) {
            const suggestions = d.getElementById('orden-compra-suggestions');
            if (!suggestions) return;
            const resp = await w.proyectosAPI.ordenesCompra.disponibles(this._proyectoUuid, query);
            const items = resp.ok ? (resp.data.ordenes || []) : [];
            this._renderSuggestions(items, suggestions);
        },

        _renderSuggestions(items, container) {
            if (items.length === 0) {
                container.innerHTML = '<div class="list-group-item small text-muted">No se encontraron órdenes de compra aprobadas disponibles</div>';
            } else {
                container.innerHTML = items.map(o => `
                    <button type="button" class="list-group-item list-group-item-action small py-2" data-uuid="${o.uuid}">
                        <div class="d-flex justify-content-between">
                            <span><strong>${o.numero_documento || ''}</strong> — ${o.proveedor || ''}</span>
                            <span>${w.proyectosAPI.formatCurrency(o.total)}</span>
                        </div>
                        <small class="text-muted">Fecha: ${o.fecha || '—'}</small>
                    </button>`).join('');
            }
            container.classList.remove('d-none');
            container.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', () => this.asociar(btn.dataset.uuid));
            });
        },

        async asociar(ordenUuid) {
            const resp = await w.proyectosAPI.ordenesCompra.asociar(this._proyectoUuid, ordenUuid);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al asociar la orden de compra al proyecto');
                return;
            }
            w.SintelFeedback?.success('Orden de compra asociada correctamente al proyecto.');
            d.getElementById('orden-compra-buscador')?.classList.add('d-none');
            const searchInput = d.getElementById('orden-compra-search');
            if (searchInput) searchInput.value = '';
            await this.init(this._proyectoUuid, currentProyecto?.fase_actual);
        }
    };

    w.Sintel.ProyectosOrdenesCompra = ProyectosOrdenesCompra;

    // ============================================================================
    // FIN MÓDULO ÓRDENES DE COMPRA DEL PROYECTO
    // ============================================================================

    // ============================================================================
    // MÓDULO TAREAS DIARIAS (v3.5.3)
    // ============================================================================

    const TareasDiarias = {
        _tareas: [],
        _proyectoUuid: null,
        _enCierre: false,
        // PLAN_PROYECTOS_FASE_3_EJECUCION_TIEMPOS_GASTOS_NO_FACTURABLES
        // Seccion 21: filtros sobre el dataset ya cargado, sin tocar el
        // contrato de la API (misma lista que devuelve tareasDiarias.list()).
        _filtros: { estado: 'TODAS', prioridad: 'TODAS', desde: '', hasta: '' },
        _filtrosInicializados: false,

        async init(proyectoUuid, proyecto, enCierre) {
            if (!proyectoUuid || !proyecto) return;
            this._proyectoUuid = proyectoUuid;
            this._enCierre = !!enCierre;

            // Mostrar período del proyecto
            const periodoEl = d.getElementById('tareas-periodo-display');
            if (periodoEl) {
                const inicio = proyecto.fecha_inicio ? new Date(proyecto.fecha_inicio).toLocaleDateString('es-CO') : '--';
                const fin = proyecto.fecha_fin_estimada ? new Date(proyecto.fecha_fin_estimada).toLocaleDateString('es-CO') : '--';
                periodoEl.textContent = `${inicio} a ${fin}`;
            }

            // Cargar tareas desde API
            const resp = await w.proyectosAPI.tareasDiarias.list(proyectoUuid);
            if (!resp.ok) {
                console.error(`${MOD} Error al cargar tareas:`, resp);
                this._tareas = [];
            } else {
                this._tareas = resp.data.results || resp.data || [];
            }

            this._bindFiltros();
            this._render(this._enCierre);
            this._refreshResumen();
            this._actualizarAvance();
        },

        // Seccion 21: filtros Estado/Prioridad/Periodo -- se enlazan una sola
        // vez (flag), mismo patron anti-doble-listener que ProyectosPresupuesto.
        _bindFiltros() {
            if (this._filtrosInicializados) return;
            this._filtrosInicializados = true;

            const grupoEstado = d.getElementById('tareas-filtro-estado');
            grupoEstado?.addEventListener('click', (ev) => {
                const btn = ev.target.closest('button[data-filtro]');
                if (!btn) return;
                grupoEstado.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this._filtros.estado = btn.dataset.filtro;
                this._render(this._enCierre);
            });

            d.getElementById('tareas-filtro-prioridad')?.addEventListener('change', (ev) => {
                this._filtros.prioridad = ev.target.value;
                this._render(this._enCierre);
            });

            d.getElementById('tareas-filtro-periodo-desde')?.addEventListener('change', (ev) => {
                this._filtros.desde = ev.target.value;
                this._render(this._enCierre);
            });

            d.getElementById('tareas-filtro-periodo-hasta')?.addEventListener('change', (ev) => {
                this._filtros.hasta = ev.target.value;
                this._render(this._enCierre);
            });

            d.getElementById('btn-limpiar-filtros-tareas')?.addEventListener('click', () => {
                this._filtros = { estado: 'TODAS', prioridad: 'TODAS', desde: '', hasta: '' };
                grupoEstado?.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.filtro === 'TODAS'));
                const selPrioridad = d.getElementById('tareas-filtro-prioridad');
                if (selPrioridad) selPrioridad.value = 'TODAS';
                const inpDesde = d.getElementById('tareas-filtro-periodo-desde');
                if (inpDesde) inpDesde.value = '';
                const inpHasta = d.getElementById('tareas-filtro-periodo-hasta');
                if (inpHasta) inpHasta.value = '';
                this._render(this._enCierre);
            });
        },

        _aplicarFiltros() {
            const { estado, prioridad, desde, hasta } = this._filtros;
            return this._tareas.filter(tarea => {
                if (estado !== 'TODAS' && tarea.estado !== estado) return false;
                if (prioridad !== 'TODAS' && tarea.prioridad !== prioridad) return false;
                // Periodo: la tarea coincide si su rango [fecha_inicio, fecha_fin]
                // se superpone con el rango filtrado [desde, hasta].
                if (desde && tarea.fecha_fin < desde) return false;
                if (hasta && tarea.fecha_inicio > hasta) return false;
                return true;
            });
        },

        // Seccion 22: indicador operativo, siempre sobre el total de tareas
        // (no se ve afectado por los filtros visuales) -- no reemplaza
        // Proyecto.porcentaje_avance.
        _actualizarAvance() {
            const el = d.getElementById('tareas-avance-pct');
            if (!el) return;
            const activas = this._tareas.filter(t => t.estado !== 'CANCELADA');
            if (activas.length === 0) {
                el.textContent = '0%';
                return;
            }
            const completadas = activas.filter(t => t.estado === 'COMPLETADA').length;
            el.textContent = `${Math.round((completadas / activas.length) * 100)}%`;
        },

        _render(enCierre = false) {
            const container = d.getElementById('tareas-timeline-container');
            if (!container) return;

            const tareasFiltradas = this._aplicarFiltros();

            if (this._tareas.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-info-circle me-2"></i>
                        <small>Sin tareas aún. Agrega tareas para esta fase.</small>
                    </div>
                `;
                return;
            }

            if (tareasFiltradas.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-funnel me-2"></i>
                        <small>Ninguna tarea coincide con los filtros aplicados.</small>
                    </div>
                `;
                return;
            }

            // Agrupar por fecha_inicio
            const tareasAgrupadas = {};
            tareasFiltradas.forEach(tarea => {
                if (!tareasAgrupadas[tarea.fecha_inicio]) {
                    tareasAgrupadas[tarea.fecha_inicio] = [];
                }
                tareasAgrupadas[tarea.fecha_inicio].push(tarea);
            });

            // Renderizar timeline
            let html = '<div class="timeline">';
            Object.keys(tareasAgrupadas).sort().forEach(fechaInicio => {
                const tareasDelPeriodo = tareasAgrupadas[fechaInicio];
                const fechaObj = new Date(fechaInicio);
                const fechaDisplay = fechaObj.toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' });

                html += `<div class="timeline-day mb-3">
                    <div class="fw-bold text-primary mb-2">${fechaDisplay}</div>`;

                tareasDelPeriodo.forEach(tarea => {
                    const estadoBadge = this._getEstadoBadge(tarea.estado);
                    const prioridadClase = this._getPrioridadClase(tarea.prioridad);
                    const btnCambiarEstado = enCierre ? '' : `
                        <div class="dropdown d-inline-block">
                            <button type="button" class="btn btn-xs btn-outline-secondary dropdown-toggle"
                                    data-bs-toggle="dropdown" aria-expanded="false" title="Cambiar estado">
                                <i class="bi bi-arrow-repeat"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end">
                                ${['PENDIENTE', 'EN_PROCESO', 'COMPLETADA', 'CANCELADA'].map(estadoOpcion => `
                                    <li><a class="dropdown-item" href="#"
                                            onclick="window.Sintel.TareasDiarias.cambiarEstado('${tarea.uuid}', '${estadoOpcion}'); return false;">
                                        ${this._getEstadoLabel(estadoOpcion)}
                                    </a></li>
                                `).join('')}
                            </ul>
                        </div>
                    `;
                    const btnEliminar = enCierre ? '' : `
                        <button type="button" class="btn btn-xs btn-outline-danger"
                                onclick="window.Sintel.TareasDiarias.eliminar('${tarea.uuid}')"
                                title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    `;

                    const rango = tarea.fecha_fin !== tarea.fecha_inicio
                        ? `${tarea.fecha_inicio} — ${tarea.fecha_fin}`
                        : tarea.fecha_inicio;
                    // Seccion 23: `atrasada`/`dias_atraso` vienen calculados del
                    // backend (TareasDiariasBusinessService.esta_atrasada) --
                    // el frontend solo los pinta, nunca recalcula el criterio.
                    const badgeAtrasada = tarea.atrasada
                        ? `<span class="badge bg-danger-subtle text-danger border border-danger d-block mt-1">
                               <i class="bi bi-exclamation-triangle-fill me-1"></i>ATRASADA · venció hace ${tarea.dias_atraso} día${tarea.dias_atraso === 1 ? '' : 's'}
                           </span>`
                        : '';

                    html += `
                        <div class="card mb-2 border-${prioridadClase} border-opacity-25" data-tarea-uuid="${tarea.uuid}">
                            <div class="card-body p-2">
                                <div class="d-flex justify-content-between align-items-start gap-2">
                                    <div class="flex-grow-1">
                                        <h6 class="mb-1 text-dark">${tarea.titulo}</h6>
                                        <small class="text-muted d-block"><strong>${rango}</strong></small>
                                        ${tarea.descripcion ? `<small class="text-muted d-block">${tarea.descripcion}</small>` : ''}
                                        <small class="text-muted d-block mt-1">
                                            ${tarea.asignado_a ? `Asignado: ${tarea.asignado_a}` : 'Sin asignar'}
                                        </small>
                                        ${badgeAtrasada}
                                    </div>
                                    <div class="text-end">
                                        ${estadoBadge}
                                    </div>
                                </div>
                                ${tarea.notas_progreso ? `<small class="text-muted d-block mt-2"><em>${tarea.notas_progreso}</em></small>` : ''}
                                <div class="gap-1 mt-2">
                                    ${btnCambiarEstado}
                                    ${btnEliminar}
                                </div>
                            </div>
                        </div>
                    `;
                });

                html += '</div>';
            });

            html += '</div>';
            container.innerHTML = html;
        },

        _getEstadoBadge(estado) {
            const badges = {
                'PENDIENTE': '<span class="badge bg-secondary">Pendiente</span>',
                'EN_PROCESO': '<span class="badge bg-warning text-dark">En Proceso</span>',
                'COMPLETADA': '<span class="badge bg-success">Completada</span>',
                'CANCELADA': '<span class="badge bg-danger">Cancelada</span>'
            };
            return badges[estado] || '<span class="badge bg-light text-dark">Desconocido</span>';
        },

        _getEstadoLabel(estado) {
            const labels = {
                'PENDIENTE': 'Pendiente',
                'EN_PROCESO': 'En Proceso',
                'COMPLETADA': 'Completada',
                'CANCELADA': 'Cancelada'
            };
            return labels[estado] || estado;
        },

        _getPrioridadClase(prioridad) {
            const clases = {
                'BAJA': 'info',
                'NORMAL': 'secondary',
                'ALTA': 'danger'
            };
            return clases[prioridad] || 'secondary';
        },

        async cambiarEstado(tareaId, nuevoEstado) {
            const resp = await w.proyectosAPI.tareasDiarias.cambiarEstado(tareaId, nuevoEstado);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al cambiar estado');
                return;
            }
            w.SintelFeedback?.success('Estado actualizado');
            await this.init(this._proyectoUuid, currentProyecto, currentProyecto?.fase_actual === 'CIERRE');
        },

        async agregar() {
            const fechaInicio = d.getElementById('tareas-fecha-inicio')?.value;
            const fechaFin = d.getElementById('tareas-fecha-fin')?.value || fechaInicio;
            const titulo = d.getElementById('tareas-titulo')?.value;
            const prioridad = d.getElementById('tareas-prioridad')?.value || 'NORMAL';

            if (!fechaInicio || !titulo) {
                w.SintelFeedback?.error('Fecha de inicio y título son requeridos');
                return;
            }

            if (fechaInicio > fechaFin) {
                w.SintelFeedback?.error('La fecha de inicio debe ser anterior o igual a la fecha de fin');
                return;
            }

            const data = {
                proyecto_uuid: this._proyectoUuid,
                fecha_inicio: fechaInicio,
                fecha_fin: fechaFin,
                titulo: titulo,
                prioridad: prioridad
            };

            const resp = await w.proyectosAPI.tareasDiarias.create(data);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al crear tarea');
                return;
            }

            w.SintelFeedback?.success('Tarea creada');
            d.getElementById('tareas-fecha-inicio').value = '';
            d.getElementById('tareas-fecha-fin').value = '';
            d.getElementById('tareas-titulo').value = '';
            d.getElementById('tareas-prioridad').value = 'NORMAL';
            await this.init(this._proyectoUuid, currentProyecto);
        },

        async eliminar(tareaId) {
            if (!(await w.UIManager?.confirm('¿Eliminar esta tarea?'))) return;

            const resp = await w.proyectosAPI.tareasDiarias.delete(tareaId);
            if (!resp.ok) {
                w.UIManager?.handleError(resp, 'Error al eliminar tarea');
                return;
            }

            w.SintelFeedback?.success('Tarea eliminada');
            await this.init(this._proyectoUuid, currentProyecto, currentProyecto?.fase_actual === 'CIERRE');
        },

        _refreshResumen() {
            const conteos = { 'PENDIENTE': 0, 'EN_PROCESO': 0, 'COMPLETADA': 0, 'CANCELADA': 0 };
            this._tareas.forEach(tarea => {
                if (conteos.hasOwnProperty(tarea.estado)) {
                    conteos[tarea.estado]++;
                }
            });

            d.getElementById('tareas-resumen-pendiente').textContent = conteos['PENDIENTE'];
            d.getElementById('tareas-resumen-en-proceso').textContent = conteos['EN_PROCESO'];
            d.getElementById('tareas-resumen-completada').textContent = conteos['COMPLETADA'];
            d.getElementById('tareas-resumen-cancelada').textContent = conteos['CANCELADA'];
        }
    };

    w.Sintel.TareasDiarias = TareasDiarias;

    // ============================================================================
    // FIN MÓDULO TAREAS DIARIAS
    // ============================================================================

    // ============================================================================
    // MÓDULO FASE 1 (INICIO): VIABILIDAD Y APROBACIÓN
    // PLAN_AJUSTE_CICLO_PROYECTOS_FASE_1_VIABILIDAD_APROBACION
    //
    // El frontend NUNCA calcula viabilidad (Seccion 67 del plan) -- solo
    // pinta lo que devuelve GET .../inicio/ (ProyectoInicioResumenService).
    // Supervisor/Contratista se guardan via el formulario principal
    // (hidden inputs con name= real, mismo patron que responsable_comercial);
    // Facturas/Cotizaciones de Costo/Inversiones/Aprobacion usan sus propias
    // acciones HTTP inmediatas (no esperan al boton "Guardar cambios").
    // ============================================================================
    const ProyectoInicio = {
        _proyectoUuid: null,

        /**
         * Muestra el mensaje de error REAL del backend (resp.data.message,
         * ya redactado en lenguaje de usuario por el Service Layer -- ver
         * inicio_service.py) como un toast simple, en vez de
         * `UIManager.handleError()` -- ese helper delega en
         * `SintelFeedback.handleAPIError()`, que aplana TODAS las claves
         * del payload (incluida `error`, el codigo tecnico) en un volcado
         * crudo tipo "error: sin_valor_vendido / message: ... / Detalle:
         * sin_valor_vendido" (confirmado en navegador real). Es un
         * comportamiento preexistente de un componente compartido -- no se
         * modifica aqui (riesgo para otras apps), se evita localmente.
         */
        _mostrarError(resp, fallback) {
            const mensaje = resp?.data?.message || resp?.data?.detail || fallback;
            w.SintelFeedback?.error(mensaje);
        },

        async init(proyectoUuid, _proyecto) {
            if (!proyectoUuid) return;
            this._proyectoUuid = proyectoUuid;
            this._bindUI();
            await this.refrescar();
        },

        async refrescar() {
            const [resumenResp, cotResp, invResp] = await Promise.all([
                w.proyectosAPI.inicio.get(this._proyectoUuid),
                w.proyectosAPI.inicio.cotizacionesCosto.list(this._proyectoUuid),
                w.proyectosAPI.inicio.inversiones.list(this._proyectoUuid)
            ]);

            const resumen = resumenResp.ok ? resumenResp.data : null;
            this._renderFacturas(resumen?.facturas_venta?.facturas || []);
            this._renderValorVendido(resumen?.facturas_venta?.valor_vendido_subtotal);
            this._renderCotizaciones(cotResp.ok ? (cotResp.data.results || cotResp.data || []) : []);
            this._renderInversiones(invResp.ok ? (invResp.data.results || invResp.data || []) : []);
            this._renderViabilidad(resumen);
            this._renderAprobacion(resumen);
        },

        // --- Supervisor / Contratista: buscador + hidden inputs del form principal ---
        _bindUI() {
            // [FIX] La bandera de "ya enlazado" DEBE vivir en el propio
            // elemento del DOM (dataset), nunca en el modulo JS -- mismo
            // patron que ProyectosGastos._bindSearch() (searchInput.
            // dataset.gastosBound). El offcanvas se recarga via HTMX cada
            // vez que se abre "Editar Proyecto" (DOM nuevo cada vez); una
            // bandera a nivel de modulo (this._bound) quedaba en `true`
            // desde la primera apertura y nunca volvia a enlazar los
            // listeners sobre el DOM nuevo -- los buscadores de Supervisor/
            // Contratista (y el resto de botones de Fase 1: facturas,
            // cotizaciones de costo, inversiones, aprobacion) dejaban de
            // responder a partir de la segunda apertura del offcanvas.
            const anchor = d.getElementById('inicio-supervisor-search');
            if (!anchor || anchor.dataset.inicioBound === 'true') return;
            anchor.dataset.inicioBound = 'true';

            this._bindBuscadorSimple({
                inputId: 'inicio-supervisor-search',
                suggestionsId: 'inicio-supervisor-suggestions',
                hiddenIdId: 'inicio-supervisor-id',
                hiddenNombreId: 'inicio-supervisor-nombre',
                buscar: (q) => w.proyectosAPI.lookups.empleados(q),
                extraer: (resp) => resp.data?.results || resp.data || [],
                renderLabel: (e) => `${e.primer_nombre || ''} ${e.primer_apellido || ''}`.trim(),
            });

            this._bindBuscadorSimple({
                inputId: 'inicio-contratista-search',
                suggestionsId: 'inicio-contratista-suggestions',
                hiddenIdId: 'inicio-contratista-id',
                hiddenNombreId: 'inicio-contratista-nombre',
                buscar: (q) => w.proyectosAPI.lookups.proveedores(q),
                extraer: (resp) => resp.data?.results || resp.data || [],
                renderLabel: (p) => p.razon_social || p.nombre_comercial || '',
            });

            // --- Facturas de Venta ---
            const btnToggleFactura = d.getElementById('btn-mostrar-buscador-factura-venta');
            const buscadorFactura = d.getElementById('inicio-factura-buscador');
            btnToggleFactura?.addEventListener('click', () => {
                buscadorFactura.classList.toggle('d-none');
                if (!buscadorFactura.classList.contains('d-none')) d.getElementById('inicio-factura-search')?.focus();
            });

            const inputFactura = d.getElementById('inicio-factura-search');
            const suggestionsFactura = d.getElementById('inicio-factura-suggestions');
            let debounceFactura;
            inputFactura?.addEventListener('input', (e) => {
                clearTimeout(debounceFactura);
                const q = e.target.value.trim();
                if (q.length < 2) { suggestionsFactura.classList.add('d-none'); return; }
                debounceFactura = setTimeout(async () => {
                    const resp = await w.proyectosAPI.inicio.facturasVenta.buscarDisponibles(this._proyectoUuid, q);
                    const items = resp.ok ? (resp.data || []) : [];
                    if (items.length === 0) {
                        suggestionsFactura.innerHTML = '<div class="list-group-item small text-muted">Sin facturas disponibles</div>';
                    } else {
                        suggestionsFactura.innerHTML = items.map(f => `
                            <button type="button" class="list-group-item list-group-item-action small py-2" data-uuid="${f.uuid}">
                                <div class="d-flex justify-content-between">
                                    <span><strong>${f.numero}</strong> — ${f.cliente || ''}${f.nit ? ` <span class="text-muted">(NIT ${f.nit})</span>` : ''}</span>
                                    <span>${w.proyectosAPI.formatCurrency(f.subtotal)}</span>
                                </div>
                            </button>`).join('');
                        suggestionsFactura.querySelectorAll('button').forEach(btn => {
                            btn.addEventListener('click', () => this.vincularFactura(btn.dataset.uuid));
                        });
                    }
                    suggestionsFactura.classList.remove('d-none');
                }, 300);
            });
            d.addEventListener('click', (e) => {
                if (inputFactura && suggestionsFactura && !inputFactura.contains(e.target) && !suggestionsFactura.contains(e.target)) {
                    suggestionsFactura.classList.add('d-none');
                }
            });

            // --- Cotizaciones de Costo: toggle de formulario ---
            d.getElementById('btn-mostrar-form-cotizacion-costo')?.addEventListener('click', () => {
                d.getElementById('inicio-form-cotizacion-costo')?.classList.remove('d-none');
            });
            d.getElementById('btn-cancelar-cotizacion-costo')?.addEventListener('click', () => {
                d.getElementById('inicio-form-cotizacion-costo')?.classList.add('d-none');
            });
            d.getElementById('btn-guardar-cotizacion-costo')?.addEventListener('click', () => this.guardarCotizacionCosto());

            // --- Inversiones: toggle de formulario ---
            d.getElementById('btn-mostrar-form-inversion')?.addEventListener('click', () => {
                d.getElementById('inicio-form-inversion')?.classList.remove('d-none');
            });
            d.getElementById('btn-cancelar-inversion')?.addEventListener('click', () => {
                d.getElementById('inicio-form-inversion')?.classList.add('d-none');
            });
            d.getElementById('btn-guardar-inversion')?.addEventListener('click', () => this.guardarInversion());

            // --- Aprobacion ---
            d.getElementById('btn-enviar-aprobacion-inicio')?.addEventListener('click', () => this.enviarAprobacion());
            d.getElementById('btn-aprobar-inicio')?.addEventListener('click', () => this.aprobar());
            // Rechazar: formulario inline (motivo), nunca prompt() nativo.
            d.getElementById('btn-rechazar-inicio')?.addEventListener('click', () => {
                d.getElementById('inicio-rechazo-form')?.classList.remove('d-none');
            });
            d.getElementById('btn-cancelar-rechazo-inicio')?.addEventListener('click', () => {
                d.getElementById('inicio-rechazo-form')?.classList.add('d-none');
                d.getElementById('inicio-rechazo-motivo').value = '';
            });
            d.getElementById('btn-confirmar-rechazo-inicio')?.addEventListener('click', () => this.rechazar());
        },

        /** Buscador generico texto+sugerencias que solo fija hidden inputs
         * del formulario principal (sin API propia) -- Supervisor/Contratista
         * se guardan junto con el resto del Proyecto. */
        _bindBuscadorSimple({ inputId, suggestionsId, hiddenIdId, hiddenNombreId, buscar, extraer, renderLabel }) {
            const input = d.getElementById(inputId);
            const suggestions = d.getElementById(suggestionsId);
            const hiddenId = d.getElementById(hiddenIdId);
            const hiddenNombre = d.getElementById(hiddenNombreId);
            if (!input || !suggestions || !hiddenId || !hiddenNombre) return;

            let debounceTimer;
            input.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                hiddenId.value = '';
                hiddenNombre.value = '';
                const q = e.target.value.trim();
                if (q.length < 2) { suggestions.classList.add('d-none'); return; }
                debounceTimer = setTimeout(async () => {
                    const resp = await buscar(q);
                    const items = resp.ok ? extraer(resp) : [];
                    if (items.length === 0) {
                        suggestions.innerHTML = '<div class="list-group-item small text-muted">Sin resultados</div>';
                    } else {
                        suggestions.innerHTML = items.map((item, idx) => `
                            <button type="button" class="list-group-item list-group-item-action small py-2" data-idx="${idx}">
                                ${renderLabel(item)}
                            </button>`).join('');
                        suggestions.querySelectorAll('button').forEach(btn => {
                            btn.addEventListener('click', () => {
                                const item = items[parseInt(btn.dataset.idx, 10)];
                                input.value = renderLabel(item);
                                hiddenId.value = item.id;
                                hiddenNombre.value = renderLabel(item);
                                suggestions.classList.add('d-none');
                            });
                        });
                    }
                    suggestions.classList.remove('d-none');
                }, 300);
            });
            d.addEventListener('click', (e) => {
                if (!input.contains(e.target) && !suggestions.contains(e.target)) {
                    suggestions.classList.add('d-none');
                }
            });
        },

        // --- Facturas de Venta ---
        _renderFacturas(facturas) {
            const tbody = d.getElementById('inicio-tbody-facturas');
            if (!tbody) return;
            if (facturas.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3"><small>Sin facturas de venta vinculadas.</small></td></tr>`;
                return;
            }
            tbody.innerHTML = facturas.map(f => `
                <tr>
                    <td><small>${f.numero || '—'}</small></td>
                    <td><small>${f.cliente || '—'}</small></td>
                    <td class="text-end"><small>${w.proyectosAPI.formatCurrency(f.subtotal)}</small></td>
                    <td class="text-end"><small>${w.proyectosAPI.formatCurrency(f.total)}</small></td>
                    <td>
                        <button type="button" class="btn btn-xs btn-outline-danger"
                                onclick="window.Sintel.ProyectoInicio.desvincularFactura('${f.uuid}')" title="Desvincular">
                            <i class="bi bi-x-circle"></i>
                        </button>
                    </td>
                </tr>`).join('');
        },

        _renderValorVendido(valor) {
            const el = d.getElementById('inicio-valor-vendido');
            if (el) el.textContent = w.proyectosAPI.formatCurrency(valor || 0);
        },

        async vincularFactura(facturaUuid) {
            const resp = await w.proyectosAPI.inicio.facturasVenta.vincular(this._proyectoUuid, facturaUuid);
            if (!resp.ok) { this._mostrarError(resp, 'Error al vincular la factura'); return; }
            w.SintelFeedback?.success('Factura vinculada. Valor vendido actualizado.');
            d.getElementById('inicio-factura-buscador')?.classList.add('d-none');
            d.getElementById('inicio-factura-search').value = '';
            await this.refrescar();
        },

        async desvincularFactura(facturaUuid) {
            if (!(await w.UIManager?.confirm('¿Desvincular esta factura de venta del proyecto?'))) return;
            const resp = await w.proyectosAPI.inicio.facturasVenta.desvincular(this._proyectoUuid, facturaUuid);
            if (!resp.ok) { this._mostrarError(resp, 'Error al desvincular la factura'); return; }
            w.SintelFeedback?.success('Factura desvinculada.');
            await this.refrescar();
        },

        // --- Cotizaciones de Costo ---
        _renderCotizaciones(items) {
            const tbody = d.getElementById('inicio-tbody-cotizaciones-costo');
            if (tbody) {
                if (items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3"><small>Sin cotizaciones de costo registradas.</small></td></tr>`;
                } else {
                    tbody.innerHTML = items.map(c => `
                        <tr>
                            <td><small>${c.categoria_display || c.categoria}</small></td>
                            <td><small>${c.proveedor_nombre || '—'}</small></td>
                            <td class="text-end"><small>${w.proyectosAPI.formatCurrency(c.valor)}</small></td>
                            <td>${c.archivo_pdf ? `<a href="${c.archivo_pdf}" target="_blank" class="btn btn-xs btn-outline-secondary"><i class="bi bi-file-pdf"></i></a>` : '<span class="text-muted small">—</span>'}</td>
                            <td>
                                <button type="button" class="btn btn-xs btn-outline-danger"
                                        onclick="window.Sintel.ProyectoInicio.eliminarCotizacionCosto('${c.uuid}')" title="Eliminar">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>`).join('');
                }
            }
            const totalEl = d.getElementById('inicio-total-cotizado');
            if (totalEl) {
                const total = items.reduce((s, c) => s + (parseFloat(c.valor) || 0), 0);
                totalEl.textContent = w.proyectosAPI.formatCurrency(total);
            }
        },

        async guardarCotizacionCosto() {
            const valor = d.getElementById('cc-valor')?.value;
            const archivo = d.getElementById('cc-archivo-pdf')?.files?.[0];
            if (!valor || parseFloat(valor) <= 0) { w.SintelFeedback?.error('El valor es requerido'); return; }
            if (!archivo) { w.SintelFeedback?.error('El PDF de la cotización es requerido'); return; }

            const fd = new FormData();
            fd.append('proyecto_uuid', this._proyectoUuid);
            fd.append('categoria', d.getElementById('cc-categoria').value);
            fd.append('descripcion', d.getElementById('cc-descripcion')?.value || '');
            fd.append('proveedor_nombre', d.getElementById('cc-proveedor-nombre')?.value || '');
            fd.append('fecha', d.getElementById('cc-fecha')?.value || '');
            fd.append('valor', valor);
            fd.append('archivo_pdf', archivo);

            const resp = await w.proyectosAPI.inicio.cotizacionesCosto.create(fd);
            if (!resp.ok) { this._mostrarError(resp, 'Error al guardar la cotización de costo'); return; }
            w.SintelFeedback?.success('Cotización de costo guardada.');
            ['cc-proveedor-nombre', 'cc-descripcion', 'cc-fecha', 'cc-valor', 'cc-archivo-pdf'].forEach(id => {
                const el = d.getElementById(id);
                if (el) el.value = '';
            });
            d.getElementById('inicio-form-cotizacion-costo')?.classList.add('d-none');
            await this.refrescar();
        },

        async eliminarCotizacionCosto(itemUuid) {
            if (!(await w.UIManager?.confirm('¿Eliminar esta cotización de costo?'))) return;
            const resp = await w.proyectosAPI.inicio.cotizacionesCosto.delete(itemUuid);
            if (!resp.ok) { this._mostrarError(resp, 'Error al eliminar la cotización de costo'); return; }
            w.SintelFeedback?.success('Cotización de costo eliminada.');
            await this.refrescar();
        },

        // --- Inversiones Reales ---
        _renderInversiones(items) {
            const tbody = d.getElementById('inicio-tbody-inversiones');
            if (tbody) {
                if (items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3"><small>Sin inversiones reales registradas.</small></td></tr>`;
                } else {
                    tbody.innerHTML = items.map(inv => `
                        <tr>
                            <td><small>${inv.categoria_display || inv.categoria}</small></td>
                            <td><small>${inv.descripcion || '—'}</small></td>
                            <td class="text-end"><small>${w.proyectosAPI.formatCurrency(inv.valor)}</small></td>
                            <td><small>${inv.fecha || '—'}</small></td>
                            <td>
                                <button type="button" class="btn btn-xs btn-outline-danger"
                                        onclick="window.Sintel.ProyectoInicio.eliminarInversion('${inv.uuid}')" title="Eliminar">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>`).join('');
                }
            }
            const totalEl = d.getElementById('inicio-total-invertido');
            if (totalEl) {
                const total = items.reduce((s, inv) => s + (parseFloat(inv.valor) || 0), 0);
                totalEl.textContent = w.proyectosAPI.formatCurrency(total);
            }
        },

        async guardarInversion() {
            const valor = d.getElementById('inv-valor')?.value;
            const fecha = d.getElementById('inv-fecha')?.value;
            if (!valor || parseFloat(valor) <= 0) { w.SintelFeedback?.error('El valor es requerido'); return; }
            if (!fecha) { w.SintelFeedback?.error('La fecha es requerida'); return; }

            const data = {
                proyecto_uuid: this._proyectoUuid,
                categoria: d.getElementById('inv-categoria').value,
                descripcion: d.getElementById('inv-descripcion')?.value || '',
                proveedor_nombre: d.getElementById('inv-proveedor-nombre')?.value || '',
                fecha,
                valor,
                documento_referencia: d.getElementById('inv-documento-referencia')?.value || ''
            };
            const resp = await w.proyectosAPI.inicio.inversiones.create(data);
            if (!resp.ok) { this._mostrarError(resp, 'Error al guardar la inversión'); return; }
            w.SintelFeedback?.success('Inversión registrada.');
            ['inv-proveedor-nombre', 'inv-descripcion', 'inv-fecha', 'inv-valor', 'inv-documento-referencia'].forEach(id => {
                const el = d.getElementById(id);
                if (el) el.value = '';
            });
            d.getElementById('inicio-form-inversion')?.classList.add('d-none');
            await this.refrescar();
        },

        async eliminarInversion(itemUuid) {
            if (!(await w.UIManager?.confirm('¿Eliminar esta inversión?'))) return;
            const resp = await w.proyectosAPI.inicio.inversiones.delete(itemUuid);
            if (!resp.ok) { this._mostrarError(resp, 'Error al eliminar la inversión'); return; }
            w.SintelFeedback?.success('Inversión eliminada.');
            await this.refrescar();
        },

        // --- Viabilidad (solo pinta lo que calcula el backend) ---
        _renderViabilidad(resumen) {
            const set = (id, text) => { const el = d.getElementById(id); if (el) el.textContent = text; };
            if (!resumen) return;

            set('via-valor-vendido', w.proyectosAPI.formatCurrency(resumen.facturas_venta?.valor_vendido_subtotal));
            set('via-costo-cotizacion', w.proyectosAPI.formatCurrency(resumen.cotizaciones_costo?.total));
            set('via-costo-inversion', w.proyectosAPI.formatCurrency(resumen.inversion_real?.total));
            set('via-resultado-cotizacion', w.proyectosAPI.formatCurrency(resumen.viabilidad?.resultado_cotizacion));
            set('via-resultado-inversion', w.proyectosAPI.formatCurrency(resumen.viabilidad?.resultado_inversion));

            // Margen como badge verde/rojo segun sea positivo o negativo --
            // de un vistazo, sin que el cliente tenga que interpretar el
            // numero (Seccion 10 del plan: ambos margenes, sin forzar uno
            // "oficial", pero cada uno debe leerse solo).
            this._renderMargenBadge('via-margen-cotizacion', resumen.viabilidad?.margen_cotizacion_pct);
            this._renderMargenBadge('via-margen-inversion', resumen.viabilidad?.margen_inversion_pct);
        },

        _renderMargenBadge(elId, margenPct) {
            const el = d.getElementById(elId);
            if (!el) return;
            if (margenPct === null || margenPct === undefined) {
                el.textContent = 'Sin datos (aún no hay valor vendido)';
                el.className = 'badge bg-secondary';
                return;
            }
            const valor = parseFloat(margenPct);
            el.textContent = `${margenPct}%`;
            el.className = `badge ${valor >= 0 ? 'bg-success' : 'bg-danger'}`;
        },

        // --- Aprobacion ---
        _renderAprobacion(resumen) {
            const badge = d.getElementById('inicio-estado-aprobacion-badge');
            const motivoEl = d.getElementById('inicio-motivo-rechazo');
            const btnEnviar = d.getElementById('btn-enviar-aprobacion-inicio');
            const btnAprobar = d.getElementById('btn-aprobar-inicio');
            const btnRechazar = d.getElementById('btn-rechazar-inicio');
            if (!badge) return;

            const estado = resumen?.estado_aprobacion || 'SIN_ENVIAR';
            const estilos = {
                'SIN_ENVIAR': ['bg-secondary', 'Sin enviar'],
                'PENDIENTE': ['bg-warning text-dark', 'En revisión'],
                'APROBADA': ['bg-success', 'Aprobado'],
                'RECHAZADA': ['bg-danger', 'Rechazado'],
                'CANCELADA': ['bg-secondary', 'Aprobación anulada: reenvíe para revisión']
            };
            const [clase, texto] = estilos[estado] || ['bg-secondary', estado];
            badge.className = `badge ${clase}`;
            badge.textContent = texto;

            if (motivoEl) {
                if (estado === 'RECHAZADA' && resumen?.motivo_rechazo) {
                    motivoEl.textContent = `Motivo: ${resumen.motivo_rechazo}`;
                    motivoEl.classList.remove('d-none');
                } else {
                    motivoEl.classList.add('d-none');
                }
            }

            // "Enviar a aprobacion" disponible salvo que ya este PENDIENTE o APROBADA vigente.
            const puedeEnviar = estado === 'SIN_ENVIAR' || estado === 'RECHAZADA' || estado === 'CANCELADA';
            btnEnviar?.classList.toggle('d-none', !puedeEnviar);
            // "Aprobar/Rechazar" solo tienen sentido con una solicitud PENDIENTE
            // (el backend ya exige rol ADMIN -- esto es solo UX, no seguridad).
            btnAprobar?.classList.toggle('d-none', estado !== 'PENDIENTE');
            btnRechazar?.classList.toggle('d-none', estado !== 'PENDIENTE');
        },

        async enviarAprobacion() {
            const resp = await w.proyectosAPI.inicio.enviarAprobacion(this._proyectoUuid);
            if (!resp.ok) { this._mostrarError(resp, 'Error al enviar a aprobación'); return; }
            w.SintelFeedback?.success('Inicio enviado a aprobación administrativa.');
            await this.refrescar();
            await refrescarProyectoActual();
        },

        async aprobar() {
            if (!(await w.UIManager?.confirm('¿Aprobar el Inicio de este proyecto? Esto desbloqueará la Fase de Planeación.'))) return;
            const resp = await w.proyectosAPI.inicio.aprobar(this._proyectoUuid);
            if (!resp.ok) { this._mostrarError(resp, 'Error al aprobar'); return; }
            w.SintelFeedback?.success('Inicio aprobado. Planeación desbloqueada.');
            await this.refrescar();
            await refrescarProyectoActual();
        },

        async rechazar() {
            const motivoInput = d.getElementById('inicio-rechazo-motivo');
            const motivo = (motivoInput?.value || '').trim();
            if (!motivo) { w.SintelFeedback?.error('Debe indicar el motivo del rechazo'); return; }

            const resp = await w.proyectosAPI.inicio.rechazar(this._proyectoUuid, motivo);
            if (!resp.ok) { this._mostrarError(resp, 'Error al rechazar'); return; }
            w.SintelFeedback?.success('Inicio rechazado.');
            motivoInput.value = '';
            d.getElementById('inicio-rechazo-form')?.classList.add('d-none');
            await this.refrescar();
            await refrescarProyectoActual();
        }
    };

    w.Sintel.ProyectoInicio = ProyectoInicio;

    // ============================================================================
    // FIN MÓDULO FASE 1 (INICIO)
    // ============================================================================

    w.ProyectosEditorModule = {
        init,
        guardarProyecto,
        avanzarFaseProyecto,
        cargarDetallesProyecto,
        irAFaseInicio: () => irAStep(1)
    };

    if (!w.ProyectosModule) {
        w.ProyectosModule = {};
    }
    w.ProyectosModule.guardarProyecto = guardarProyecto;

})(window, document);
