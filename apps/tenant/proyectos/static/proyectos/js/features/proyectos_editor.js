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
        const responsableFields = [
            'responsable_comercial_id', 'responsable_comercial_nombre',
            'responsable_tecnico_id', 'responsable_tecnico_nombre',
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
            res = await w.Sintel.Core.Http.request('POST', '/api/v1/proyectos/', data);
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
                'proyecto-responsable-tecnico-select',
                'proyecto-responsable-operativo-select',
                'proyecto-responsable-administrativo-select',
            ];
            const responsableFields = [
                'proyecto-responsable-comercial-id', 'proyecto-responsable-comercial-nombre',
                'proyecto-responsable-tecnico-id', 'proyecto-responsable-tecnico-nombre',
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

        const fmt    = (n) => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(n || 0);
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
        const costoReal   = costoMO + costoMat;

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

        // 1.6. Tareas Diarias (v3.5.3 - Fase 3)
        if (currentProyecto?.uuid) {
            const enCierre = currentProyecto.fase_actual === 'CIERRE';
            w.Sintel.TareasDiarias.init(currentProyecto.uuid, currentProyecto, enCierre);
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
        const costTotal      = costPersonal + costMateriales;
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
                ? new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(total)
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
        syncSelectInitial('proyecto-responsable-tecnico-select', currentProyecto.responsable_tecnico_id);
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
        setupSelectorSync('proyecto-responsable-tecnico-select', 'proyecto-responsable-tecnico-id', 'proyecto-responsable-tecnico-nombre');
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
            offcanvasEl.addEventListener('click', (e) => {
                if (e.target?.id === 'btn-agregar-presupuesto') {
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
            offcanvasEl.addEventListener('click', (e) => {
                if (e.target?.id === 'btn-agregar-tarea') {
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
                        <td colspan="6" class="text-center text-muted py-3">
                            <small><i class="bi bi-info-circle me-1"></i>Sin ítems aún. Agrega costos planeados.</small>
                        </td>
                    </tr>
                `;
                return;
            }

            let html = '';
            this._items.forEach(item => {
                const categDisplay = item.categoria_display || item.categoria;
                const btnEliminar = enCierre ? '' : `
                    <button type="button" class="btn btn-xs btn-outline-danger"
                            onclick="window.Sintel.ProyectosPresupuesto.eliminar('${item.uuid}')"
                            title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                html += `
                    <tr data-uuid="${item.uuid}">
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
    // MÓDULO TAREAS DIARIAS (v3.5.3)
    // ============================================================================

    const TareasDiarias = {
        _tareas: [],
        _proyectoUuid: null,

        async init(proyectoUuid, proyecto, enCierre) {
            if (!proyectoUuid || !proyecto) return;
            this._proyectoUuid = proyectoUuid;

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

            this._render(enCierre);
            this._refreshResumen();
        },

        _render(enCierre = false) {
            const container = d.getElementById('tareas-timeline-container');
            if (!container) return;

            if (this._tareas.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-info-circle me-2"></i>
                        <small>Sin tareas aún. Agrega tareas para esta fase.</small>
                    </div>
                `;
                return;
            }

            // Agrupar por fecha_inicio
            const tareasAgrupadas = {};
            this._tareas.forEach(tarea => {
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
                        <button type="button" class="btn btn-xs btn-outline-secondary"
                                onclick="window.Sintel.TareasDiarias.mostrarMenuEstado('${tarea.uuid}')"
                                title="Cambiar estado">
                            <i class="bi bi-arrow-repeat"></i>
                        </button>
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

        _getPrioridadClase(prioridad) {
            const clases = {
                'BAJA': 'info',
                'NORMAL': 'secondary',
                'ALTA': 'danger'
            };
            return clases[prioridad] || 'secondary';
        },

        mostrarMenuEstado(tareaId) {
            const estados = ['PENDIENTE', 'EN_PROCESO', 'COMPLETADA', 'CANCELADA'];
            const nuevoEstado = prompt('Nuevo estado:\n' + estados.join(', '), 'EN_PROCESO');
            if (nuevoEstado && estados.includes(nuevoEstado)) {
                this.cambiarEstado(tareaId, nuevoEstado);
            } else if (nuevoEstado) {
                w.SintelFeedback?.error('Estado inválido. Opciones: ' + estados.join(', '));
            }
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

    w.ProyectosEditorModule = {
        init,
        guardarProyecto,
        avanzarFaseProyecto,
        cargarDetallesProyecto
    };

    if (!w.ProyectosModule) {
        w.ProyectosModule = {};
    }
    w.ProyectosModule.guardarProyecto = guardarProyecto;

})(window, document);
