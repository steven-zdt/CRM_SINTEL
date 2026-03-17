/**
 * Feature: Listado de Clientes v2.61 (Deprecated - Logic moved to Alpine.js)
 * ⚠️ Feature-Sliced Architecture: Compatibilidad solo si Alpine.js no carga correctamente
 * ⚠️ Este archivo es un fallback - La lógica principal está en list.html Alpine.js
 * 
 * Nota: En v2.61, la inicialización de tablas se hace en el template con Alpine.js
 * para manejar lazy loading y estado de carga correctamente.
 */
(function(w, d) {
    'use strict';

    // Este módulo solo se activa si Alpine.js falla o no está disponible
    if (!w.Alpine) {
        console.warn('[clientes.list] Alpine.js no disponible, cargando fallback...', );
        initLegacyFallback();
    }

    /**
     * Fallback para cuando Alpine.js no esté disponible
     */
    function initLegacyFallback() {
        console.warn('[clientes.list] Usando fallback legacy (sin lazy loading)');
        
        // Inicializar tabla de clientes directamente
        if (w.TabulatorFactory && d.querySelector('#grid-clientes')) {
            const table = w.TabulatorFactory.create(
                '#grid-clientes',
                '/api/v1/clientes/',
                getColumnas(),
                { searchInputSelector: '#search-cliente' }
            );

            // Attachar event listeners
            if (table) {
                d.addEventListener('clienteGuardado', () => table.replaceData());
                d.addEventListener('clienteEliminado', () => table.replaceData());
            }
        }
    }

    /**
     * Columnas para tabla de clientes
     */
    function getColumnas() {
        return [
            {
                title: "Documento",
                field: "numero_documento",
                width: 120,
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    const badge = data.tipo_documento_display 
                        ? `<span class="badge bg-secondary me-1">${data.tipo_documento_display}</span>` 
                        : '';
                    return `${badge}${data.numero_documento || '-'}`;
                }
            },
            {
                title: "Razón Social",
                field: "razon_social",
                widthGrow: 2
            },
            {
                title: "Email",
                field: "email",
                formatter: (cell) => cell.getValue() || '<span class="text-muted">-</span>'
            },
            {
                title: "Teléfono",
                field: "telefono",
                formatter: (cell) => cell.getValue() || '<span class="text-muted">-</span>'
            },
            {
                title: "Ciudad",
                field: "ciudad",
                formatter: (cell) => cell.getValue() || '<span class="text-muted">-</span>'
            },
            {
                title: "Estado",
                field: "activo",
                width: 100,
                hozAlign: "center",
                formatter: function(cell) {
                    const value = cell.getValue();
                    return value 
                        ? '<span class="badge bg-success">Activo</span>'
                        : '<span class="badge bg-danger">Inactivo</span>';
                }
            },
            {
                title: "Acciones",
                width: 150,
                hozAlign: "center",
                headerSort: false,
                formatter: () => `
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary btn-editar" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-info btn-ver" title="Ver">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-eliminar" title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                `,
                cellClick: function(e, cell) {
                    const btn = e.target.closest('button');
                    if (!btn) return;

                    const data = cell.getRow().getData();

                    if (btn.classList.contains('btn-editar')) {
                        editarCliente(data.id);
                    } else if (btn.classList.contains('btn-ver')) {
                        verCliente(data.id);
                    } else if (btn.classList.contains('btn-eliminar')) {
                        eliminarCliente(data.id);
                    }
                }
            }
        ];
    }

    /**
     * Editar cliente
     */
    async function editarCliente(id) {
        const url = `/api/v1/clientes/${id}/render-offcanvas/editar/`;
        try {
            await htmx.ajax('GET', url, {
                target: '#offcanvas-container-clientes',
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error('[clientes.list] Error:', error);
            if (w.SintelFeedback) w.SintelFeedback.error('Error al cargar el formulario');
        }
    }

    /**
     * Ver cliente
     */
    async function verCliente(id) {
        const url = `/api/v1/clientes/render-offcanvas/detalle/?id=${id}`;
        try {
            await htmx.ajax('GET', url, {
                target: '#offcanvas-container-clientes',
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error('[clientes.list] Error:', error);
        }
    }

    /**
     * Eliminar cliente
     */
    async function eliminarCliente(id) {
        if (!confirm('¿Está seguro de eliminar este cliente?')) return;

        try {
            const response = await w.clientesAPI.delete(id);
            if (response.ok || response.status === 204) {
                if (w.SintelFeedback) w.SintelFeedback.success('Cliente eliminado');
                d.dispatchEvent(new CustomEvent('clienteEliminado'));
            } else {
                if (w.SintelFeedback) w.SintelFeedback.error('No se puede eliminar un cliente activo');
            }
        } catch (error) {
            console.error('[clientes.list] Error:', error);
        }
    }

})(window, document);
