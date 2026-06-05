/**
 * Feature: Nueva Tarea - editor.
 * Maneja exclusivamente captura y creacion de tareas cortas.
 */
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.nueva_tarea.editor]';
    let initialized = false;
    let lookupsLoaded = false;

    function form() {
        return d.getElementById('form-nueva-tarea');
    }

    function value(id) {
        return d.getElementById(id)?.value || '';
    }

    function setValue(id, nextValue) {
        const el = d.getElementById(id);
        if (el) el.value = nextValue;
    }

    function asRows(response) {
        const data = response?.data;
        if (Array.isArray(data)) return data;
        if (Array.isArray(data?.results)) return data.results;
        if (Array.isArray(data?.data)) return data.data;
        return [];
    }

    function option(label, value = '') {
        const opt = d.createElement('option');
        opt.value = value;
        opt.textContent = label;
        return opt;
    }

    function fillSelect(id, rows, mapper, placeholder) {
        const select = d.getElementById(id);
        if (!select) return;
        const currentValue = select.value;
        select.innerHTML = '';
        select.appendChild(option(placeholder));
        rows.forEach((row) => {
            const mapped = mapper(row);
            if (mapped?.value && mapped?.label) {
                select.appendChild(option(mapped.label, mapped.value));
            }
        });
        if (currentValue) select.value = currentValue;
    }

    async function loadLookups() {
        if (lookupsLoaded) return;
        const clienteSelect = d.getElementById('nt-cliente');
        const empleadoSelect = d.getElementById('nt-empleado');
        if (clienteSelect) clienteSelect.innerHTML = '<option value="">Cargando clientes...</option>';
        if (empleadoSelect) empleadoSelect.innerHTML = '<option value="">Cargando empleados...</option>';

        try {
            const [clientesRes, empleadosRes] = await Promise.all([
                w.proyectosAPI?.lookups?.clientes?.(),
                w.proyectosAPI?.lookups?.empleados?.()
            ]);

            fillSelect('nt-cliente', asRows(clientesRes), (cliente) => ({
                value: cliente.uuid,
                label: `${cliente.razon_social || 'Cliente'}${cliente.numero_documento ? ` - ${cliente.numero_documento}` : ''}`
            }), 'Cliente destino *');

            fillSelect('nt-empleado', asRows(empleadosRes), (empleado) => ({
                value: empleado.uuid,
                label: empleado.nombre_completo || `${empleado.primer_nombre || ''} ${empleado.primer_apellido || ''}`.trim()
            }), 'Empleado asignado *');

            lookupsLoaded = true;
        } catch (error) {
            console.error(`${MOD} Error cargando listas`, error);
            w.UIManager?.notifyError?.('Error al cargar clientes y empleados');
        }
    }

    async function show() {
        const el = form();
        if (el) el.style.display = 'block';
        await loadLookups();
        const context = w.Sintel?.ProyectosNuevaTarea?.getContext?.() || {};
        if (context.empleadoUuid) {
            setValue('nt-empleado', context.empleadoUuid);
        }
        d.getElementById('nt-titulo')?.focus?.();
    }

    function hide() {
        const el = form();
        if (el) el.style.display = 'none';
    }

    function toggle() {
        const el = form();
        if (!el) return;
        if (el.style.display === 'none' || !el.style.display) {
            show();
        } else {
            hide();
        }
    }

    function reset() {
        setValue('nt-titulo', '');
        setValue('nt-descripcion', '');
        setValue('nt-fecha-inicio', '');
        setValue('nt-fecha-fin', '');
        setValue('nt-prioridad', 'NORMAL');
        setValue('nt-cliente', '');
        setValue('nt-empleado', '');
    }

    function buildPayload() {
        const titulo = value('nt-titulo').trim();
        const cliente = value('nt-cliente');
        const empleado = value('nt-empleado');
        const fechaInicio = value('nt-fecha-inicio');
        const fechaFin = value('nt-fecha-fin');
        const prioridad = value('nt-prioridad') || 'NORMAL';
        const descripcion = value('nt-descripcion');

        if (!titulo || !cliente || !empleado || !fechaInicio || !fechaFin) {
            w.UIManager?.notifyWarning?.('Titulo, cliente, empleado, fecha inicio y fecha fin son requeridos');
            return null;
        }

        const payload = {
            titulo,
            cliente,
            empleado,
            fecha_inicio: fechaInicio,
            fecha_fin: fechaFin,
            prioridad,
            descripcion
        };

        return payload;
    }

    async function save(button) {
        const payload = buildPayload();
        if (!payload) return;

        const originalHtml = button?.innerHTML || '';
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }

        try {
            const response = await w.proyectosAPI?.tareasCortas?.create(payload);
            if (response?.ok) {
                w.UIManager?.notifySuccess?.('Tarea creada correctamente');
                reset();
                hide();
                await w.Sintel?.ProyectosNuevaTarea?.refresh?.();
            } else {
                w.UIManager?.handleError?.(response, MOD);
            }
        } catch (error) {
            console.error(`${MOD} Error de red`, error);
            w.UIManager?.notifyError?.('Error de red al crear la tarea');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = originalHtml || '<i class="bi bi-check-lg me-1"></i>Guardar';
            }
        }
    }

    function bindEvents() {
        d.addEventListener('click', (event) => {
            const saveButton = event.target.closest('#btn-guardar-nueva-tarea');
            if (saveButton) {
                event.preventDefault();
                save(saveButton);
                return;
            }

            if (event.target.closest('#btn-cancelar-nueva-tarea')) {
                event.preventDefault();
                reset();
                hide();
            }
        });
    }

    function init() {
        if (initialized) return;
        initialized = true;
        bindEvents();
    }

    if (!w.Sintel) w.Sintel = {};
    w.Sintel.ProyectosNuevaTareaEditor = {
        init,
        show,
        hide,
        toggle,
        reset,
        save
    };

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window, document);
