/**
 * Feature: Editor - Proyectos v3.5.1
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en lib/http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 */
(function(w, d) {
    'use strict';

    const MOD = '[proyectos.editor]';
    let currentProyecto = null;
    let currentStep = 0;
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

        const formData = new FormData(form);

        // ⚠️ DOM Shield: Remover campos vacíos
        for (const [key, value] of Array.from(formData.entries())) {
            if (value === '' || value === null) {
                formData.delete(key);
            }
        }

        // Clean empty file inputs
        const fileFields = ['contrato_archivo', 'acta_inicio_archivo', 'cronograma_archivo', 'acta_entrega_archivo', 'informe_final_archivo'];
        fileFields.forEach(field => {
            const input = form.querySelector(`[name="${field}"]`);
            if (input && (!input.files || input.files.length === 0)) {
                formData.delete(field);
            }
        });

        // Eliminar UUID de los datos a enviar
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
            res = await w.http('PATCH', `/api/v1/proyectos/${uuid}/`, data);
        } else {
            res = await w.http('POST', '/api/v1/proyectos/', data);
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
            // Actualizar UUID e inputs
            const uuidInput = d.querySelector('#proyecto-uuid');
            if (uuidInput) uuidInput.value = currentProyecto.uuid;

            const codigoInput = d.querySelector('#proyecto-codigo');
            if (codigoInput && currentProyecto.codigo) {
                codigoInput.value = currentProyecto.codigo;
            }
            
            // Recargar detalles y estado del wizard
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
     * Renderizar candados y habilitar/deshabilitar fases en el stepper
     */
    function renderStepLocks() {
        const currentFase = currentProyecto?.fase_actual || 'BORRADOR';
        const activeFaseIdx = phaseMap[currentFase] || 0;

        // Configurar clases visuales de los nodos del Stepper header
        const nodes = d.querySelectorAll('#offcanvas-proyecto .step-node');
        nodes.forEach((node, idx) => {
            node.classList.remove('locked', 'completed');
            if (idx < activeFaseIdx) {
                node.classList.add('completed');
            } else if (idx > activeFaseIdx) {
                node.classList.add('locked');
            }
        });

        // Mostrar u ocultar contenedor con mensaje bloqueado y overlay de fase
        for (let idx = 1; idx <= 4; idx++) {
            const lockedContainer = d.querySelector(`#locked-step-${idx}`);
            const unlockedContent = d.querySelector(`#unlocked-step-${idx}`);
            if (idx > activeFaseIdx) {
                if (lockedContainer) lockedContainer.classList.remove('d-none');
                if (unlockedContent) unlockedContent.classList.add('d-none');
            } else {
                if (lockedContainer) lockedContainer.classList.add('d-none');
                if (unlockedContent) unlockedContent.classList.remove('d-none');
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

        // 4. Indicadores Financieros (Fase 4)
        const ind = currentProyecto.indicadores_financieros || {};
        const valContrato = ind.valor_contrato || 0;
        const costPersonal = currentProyecto.costo_mano_obra_real || 0;
        const costMateriales = currentProyecto.costo_materiales_real || 0;
        const costTotal = ind.costo_total || (costPersonal + costMateriales);
        const utilidad = ind.utilidad_estimada || 0;
        const margen = ind.margen_rentabilidad || 0;

        const setElementText = (id, text) => {
            const el = d.querySelector(`#${id}`);
            if (el) el.textContent = text;
        };

        setElementText('fin-valor-contrato', w.proyectosAPI.formatCurrency(valContrato));
        setElementText('fin-costo-personal', w.proyectosAPI.formatCurrency(costPersonal));
        setElementText('fin-costo-materiales', w.proyectosAPI.formatCurrency(costMateriales));
        setElementText('fin-costo-total', w.proyectosAPI.formatCurrency(costTotal));
        setElementText('fin-utilidad-neta', w.proyectosAPI.formatCurrency(utilidad));
        setElementText('fin-margen-rentabilidad', `${margen.toFixed(2)}%`);

        const cardUtilidad = d.querySelector('#fin-card-utilidad');
        const cardMargen = d.querySelector('#fin-card-margen');
        if (cardUtilidad && cardMargen) {
            cardUtilidad.className = 'card finance-card border';
            cardMargen.className = 'card finance-card border';

            if (utilidad > 0) {
                cardUtilidad.classList.add('bg-success-subtle', 'border-success');
                cardMargen.classList.add('bg-success-subtle', 'border-success');
            } else if (utilidad < 0) {
                cardUtilidad.classList.add('bg-danger-subtle', 'border-danger');
                cardMargen.classList.add('bg-danger-subtle', 'border-danger');
            } else {
                cardUtilidad.classList.add('bg-light');
                cardMargen.classList.add('bg-light');
            }
        }
    }

    /**
     * Cargar centros de costos de forma asíncrona
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

        const CCSelect = d.querySelector('#proyecto-factura-costo');
        if (CCSelect && currentProyecto.factura_costo_id) {
            CCSelect.setAttribute('data-initial-value', currentProyecto.factura_costo_id);
            cargarCentrosCostos(CCSelect);
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
     * Configurar todos los event listeners del editor
     */
    function initEditorEvents() {
        const form = d.querySelector('#form-proyecto');
        if (!form) {
            console.warn(`${MOD} Formulario #form-proyecto no encontrado`);
            return;
        }

        // 1. Submit del formulario
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            guardarProyecto();
        });

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

        // Factura (Centro de Costos)
        const CCSelect = form.querySelector('#proyecto-factura-costo');
        const CCIdInput = form.querySelector('#proyecto-factura-costo-id');
        const CCNumeroInput = form.querySelector('#proyecto-factura-costo-numero');

        if (CCSelect) {
            cargarCentrosCostos(CCSelect);
            CCSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    const selectedOption = e.target.options[e.target.selectedIndex];
                    if (selectedOption) {
                        if (CCIdInput) CCIdInput.value = e.target.value;
                        const numero = selectedOption.getAttribute('data-numero');
                        if (numero && CCNumeroInput) {
                            CCNumeroInput.value = numero;
                        }
                    }
                } else {
                    if (CCIdInput) CCIdInput.value = '';
                    if (CCNumeroInput) CCNumeroInput.value = '';
                }
            });
        }

        // 3. Slider de avance
        const slider = form.querySelector('#proyecto-porcentaje-avance');
        const bubble = form.querySelector('#porcentaje-avance-bubble');
        if (slider && bubble) {
            slider.addEventListener('input', (e) => {
                bubble.textContent = `${e.target.value}%`;
            });
        }

        // 4. Stepper click nodes
        const nodes = d.querySelectorAll('#offcanvas-proyecto .step-node');
        nodes.forEach(node => {
            node.addEventListener('click', () => {
                const stepIdx = parseInt(node.getAttribute('data-step'));
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
            btnNext.addEventListener('click', () => {
                if (currentStep < 4) {
                    irAStep(currentStep + 1);
                }
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

        // 6. Limpieza al cerrar offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        if (offcanvasEl) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
                const errorContainer = d.querySelector('#form-proyecto-feedback');
                if (errorContainer) {
                    errorContainer.classList.add('d-none');
                    errorContainer.textContent = '';
                }
            });
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

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', (event) => {
            if (event.detail.target.id === 'offcanvas-container-proyectos') {
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
                    }

                    if (w.UIManager?.handleOffcanvas) {
                        w.UIManager.handleOffcanvas(offcanvasEl, 'show');
                    } else if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
                    }
                    console.log(`${MOD} Offcanvas abierto y detalles cargados tras HTMX swap`);
                }
            }
        });
    }

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
