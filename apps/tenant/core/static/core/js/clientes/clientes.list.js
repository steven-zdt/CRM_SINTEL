/**
 * Clientes List Module v2.61 (Refactored)
 * 
 * ⚠️ ARCHITECTURE: Zero JS in HTML
 * - All logic moved from list.html <script> to this module
 * - Data attributes used for configuration
 * - Event delegation for all user interactions
 * - DRY pattern: Generic CRUD operations, reusable functions
 * 
 * Dependencies: Tabulator, HTMX, UIManager
 */

(function(w, d) {
    'use strict';

    // ============================================================
    // MODULE STATE
    // ============================================================
    const state = {
        clientesLoaded: false,
        clientesLoading: false,
        contactosLoaded: false,
        contactosLoading: false,
        clientesTable: null,
        contactosTable: null,
        clientesCount: 0,
        contactosCount: 0
    };

    // ============================================================
    // LOGGING UTILITY
    // ============================================================
    const log = {
        info: (msg, data) => console.log(`[Clientes.List] ${msg}`, data || ''),
        warn: (msg, data) => console.warn(`[Clientes.List] ${msg}`, data || ''),
        error: (msg, data) => console.error(`[Clientes.List] ${msg}`, data || '')
    };

    // ============================================================
    // TABLE CONFIGURATION
    // ============================================================
    const TABLE_COLUMNS = {
        clientes: [
            { title: 'Razón Social', field: 'razon_social', widthGrow: 2 },
            { title: 'Documento', field: 'numero_documento' },
            { title: 'Email', field: 'email' },
            { title: 'Teléfono', field: 'telefono' },
            { title: 'Ciudad', field: 'ciudad' },
            {
                title: 'Acciones',
                width: 150,
                hozAlign: 'center',
                headerSort: false,
                formatter: () => `
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" data-action="edit" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-info" data-action="view" title="Ver">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-danger" data-action="delete" title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                `,
                cellClick: (e, cell) => handleCellAction(e, cell, 'clientes')
            }
        ],
        contactos: [
            { title: 'Nombre', field: 'nombre_completo', widthGrow: 2 },
            { title: 'Email', field: 'email' },
            { title: 'Teléfono', field: 'telefono' },
            {
                title: 'Cargo',
                field: 'cargo',
                formatter: (cell) => cell.getValue() || '<span class="text-muted">-</span>'
            },
            {
                title: 'Estado',
                field: 'activo',
                width: 80,
                hozAlign: 'center',
                formatter: (cell) => {
                    const value = cell.getValue();
                    return value
                        ? '<span class="badge bg-success">Activo</span>'
                        : '<span class="badge bg-danger">Inactivo</span>';
                }
            },
            {
                title: 'Acciones',
                width: 120,
                hozAlign: 'center',
                headerSort: false,
                formatter: () => `
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" data-action="edit" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" data-action="delete" title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                `,
                cellClick: (e, cell) => handleCellAction(e, cell, 'contactos')
            }
        ]
    };

    // ============================================================
    // TABLE INITIALIZATION
    // ============================================================

    /**
     * Initialize clientes table (lazy loading)
     */
    async function loadClientesTable() {
        const gridElement = d.querySelector('#grid-clientes');
        
        // ⚠️ v2.61.4: Verificar si la tabla ya está cargada Y existe en el DOM
        if (state.clientesLoaded && gridElement && gridElement.children.length > 0) {
            log.info('Clientes table already loaded and exists in DOM, skipping');
            return;
        }

        // Si el contenedor no existe o está vacío, resetear estado
        if (!gridElement || gridElement.children.length === 0) {
            log.info('Clientes grid missing or empty, resetting state');
            state.clientesLoaded = false;
        }

        state.clientesLoading = true;
        updateUIState('clientes');

        try {
            // Wait for TabulatorFactory with timeout
            await waitForTabulatorFactory();

            log.info('Creating clientes table...');
            state.clientesTable = w.TabulatorFactory.create(
                '#grid-clientes',
                '/api/v1/clientes/',
                TABLE_COLUMNS.clientes,
                { searchInputSelector: '#search-cliente' }
            );

            if (!state.clientesTable) {
                throw new Error('TabulatorFactory.create returned null');
            }

            state.clientesLoaded = true;
            log.info('Clientes table loaded successfully');

            // Track data loaded event
            state.clientesTable.on('dataLoaded', () => {
                state.clientesCount = state.clientesTable.getDataCount('active');
                log.info(`Clientes data loaded: ${state.clientesCount} rows`);
                updateUIState('clientes');
            });

        } catch (error) {
            log.error('Error loading clientes table', error);
            state.clientesLoaded = true; // Hide spinner even on error
            showError('Error al cargar la tabla de clientes');
        } finally {
            state.clientesLoading = false;
            updateUIState('clientes');
        }
    }

    /**
     * Initialize contactos table (lazy loading)
     */
    async function loadContactosTable() {
        const gridElement = d.querySelector('#grid-contactos');
        
        // ⚠️ v2.61.4: Verificar si la tabla ya está cargada Y existe en el DOM
        if (state.contactosLoaded && gridElement && gridElement.children.length > 0) {
            log.info('Contactos table already loaded and exists in DOM, skipping');
            return;
        }

        // Si el contenedor no existe o está vacío, resetear estado
        if (!gridElement || gridElement.children.length === 0) {
            log.info('Contactos grid missing or empty, resetting state');
            state.contactosLoaded = false;
        }

        state.contactosLoading = true;
        updateUIState('contactos');

        try {
            await waitForTabulatorFactory();

            log.info('Creating contactos table...');
            state.contactosTable = w.TabulatorFactory.create(
                '#grid-contactos',
                '/api/v1/clientes/contactos/',
                TABLE_COLUMNS.contactos,
                { searchInputSelector: '#search-contacto' }
            );

            if (!state.contactosTable) {
                throw new Error('TabulatorFactory.create returned null');
            }

            state.contactosLoaded = true;
            log.info('Contactos table loaded successfully');

            state.contactosTable.on('dataLoaded', () => {
                state.contactosCount = state.contactosTable.getDataCount('active');
                log.info(`Contactos data loaded: ${state.contactosCount} rows`);
                updateUIState('contactos');
            });

        } catch (error) {
            log.error('Error loading contactos table', error);
            state.contactosLoaded = true; // Hide spinner even on error
            showError('Error al cargar la tabla de contactos');
        } finally {
            state.contactosLoading = false;
            updateUIState('contactos');
        }
    }

    /**
     * Reload data in specified table
     */
    function reloadTable(type) {
        if (type === 'clientes' && state.clientesTable) {
            state.clientesTable.replaceData();
        } else if (type === 'contactos' && state.contactosTable) {
            state.contactosTable.replaceData();
        }
    }

    // ============================================================
    // TABULATOR FACTORY HELPER
    // ============================================================

    /**
     * Wait for TabulatorFactory to be available
     */
    async function waitForTabulatorFactory() {
        if (w.TabulatorFactory) return;

        log.warn('TabulatorFactory not available, waiting...');

        return new Promise((resolve, reject) => {
            let attempts = 0;
            const interval = setInterval(() => {
                attempts++;
                if (w.TabulatorFactory) {
                    clearInterval(interval);
                    log.info('TabulatorFactory available after ' + attempts + ' attempts');
                    resolve();
                } else if (attempts > 50) { // 5 seconds max
                    clearInterval(interval);
                    reject(new Error('TabulatorFactory timeout'));
                }
            }, 100);
        });
    }

    // ============================================================
    // TABLE CELL ACTIONS (Event Delegation)
    // ============================================================

    /**
     * Generic cell action handler
     */
    function handleCellAction(e, cell, type) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const rowData = cell.getRow().getData();

        switch (action) {
            case 'edit':
                if (type === 'clientes') editCliente(rowData.id);
                else if (type === 'contactos') editContacto(rowData.id);
                break;
            case 'view':
                if (type === 'clientes') viewCliente(rowData.id);
                break;
            case 'delete':
                if (type === 'clientes') deleteCliente(rowData.id);
                else if (type === 'contactos') deleteContacto(rowData.id);
                break;
        }
    }

    /**
     * Edit cliente - Load form and show offcanvas
     */
    function editCliente(id) {
        const url = `/api/v1/clientes/${id}/render-offcanvas/editar/`;
        try {
            log.info(`Loading edit form for cliente ${id}`);
            
            // Use htmx.ajax with swap listener pattern
            htmx.ajax('GET', url, {
                target: '#offcanvas-container-clientes',
                swap: 'innerHTML'
            });
        } catch (error) {
            log.error(`Error loading edit form for cliente ${id}`, error);
            showError('Error al cargar el formulario');
        }
    }

    /**
     * View cliente details - Load form and show offcanvas
     */
    function viewCliente(id) {
        const url = `/api/v1/clientes/render-offcanvas/detalle/?id=${id}`;
        try {
            log.info(`Loading detail view for cliente ${id}`);
            
            // Use htmx.ajax with swap listener pattern
            htmx.ajax('GET', url, {
                target: '#offcanvas-container-clientes',
                swap: 'innerHTML'
            });
        } catch (error) {
            log.error(`Error loading detail view for cliente ${id}`, error);
            showError('Error al cargar detalles');
        }
    }

    /**
     * Delete cliente with confirmation
     */
    async function deleteCliente(id) {
        if (!confirm('¿Está seguro de eliminar este cliente?')) return;

        try {
            const response = await w.clientesAPI.delete(id);
            if (response.ok || response.status === 204) {
                showSuccess('Cliente eliminado');
                document.dispatchEvent(new CustomEvent('clienteEliminado'));
            } else {
                showError('No se puede eliminar un cliente activo');
            }
        } catch (error) {
            log.error(`Error deleting cliente ${id}`, error);
            showError('Error al eliminar');
        }
    }

    /**
     * Edit contacto
     */
    async function editContacto(id) {
        if (!confirm('¿Desea editar este contacto?')) return;

        const url = `/api/v1/clientes/contactos/gestor-offcanvas/?id=${id}`;
        try {
            await htmx.ajax('GET', url, {
                target: '#offcanvas-container-contactos',
                swap: 'innerHTML'
            });
            log.info(`Loaded edit form for contacto ${id}`);
        } catch (error) {
            log.error(`Error loading edit form for contacto ${id}`, error);
            showError('Error al cargar el formulario');
        }
    }

    /**
     * Delete contacto with confirmation
     */
    async function deleteContacto(id) {
        if (!confirm('¿Está seguro de eliminar este contacto?')) return;

        try {
            const response = await w.http('DELETE', `/api/v1/clientes/contactos/${id}/`);
            if (response.ok || response.status === 204) {
                showSuccess('Contacto eliminado');
                document.dispatchEvent(new CustomEvent('contactoEliminado'));
            } else {
                showError('No se puede eliminar este contacto');
            }
        } catch (error) {
            log.error(`Error deleting contacto ${id}`, error);
            showError('Error al eliminar');
        }
    }

    // ============================================================
    // UI STATE MANAGEMENT
    // ============================================================

    /**
     * Update UI visibility based on state
     */
    function updateUIState(type) {
        const isClientes = type === 'clientes';
        const loading = isClientes ? state.clientesLoading : state.contactosLoading;
        const loaded = isClientes ? state.clientesLoaded : state.contactosLoaded;
        const count = isClientes ? state.clientesCount : state.contactosCount;

        // Update spinner visibility
        const spinner = d.querySelector(`[data-spinner="${type}"]`);
        if (spinner) {
            spinner.style.display = (!loaded && loading) ? 'block' : 'none';
        }

        // Update grid visibility
        const grid = d.querySelector(`[data-grid="${type}"]`);
        if (grid) {
            grid.style.display = loaded ? 'block' : 'none';
        }

        // Update empty state
        const empty = d.querySelector(`[data-empty-state="${type}"]`);
        if (empty) {
            empty.style.display = (!loading && loaded && count === 0) ? 'block' : 'none';
        }

        // Update buttons disabled state
        const buttons = d.querySelectorAll(`[data-module="${type}"] .btn`);
        buttons.forEach(btn => {
            btn.disabled = loading;
        });
    }

    // ============================================================
    // EVENT LISTENERS
    // ============================================================

    /**
     * Search input - debounced reload
     */
    d.addEventListener('keyup', (e) => {
        if (e.target.matches('#search-cliente')) {
            clearTimeout(e.target._searchTimeout);
            e.target._searchTimeout = setTimeout(() => reloadTable('clientes'), 300);
        } else if (e.target.matches('#search-contacto')) {
            clearTimeout(e.target._searchTimeout);
            e.target._searchTimeout = setTimeout(() => reloadTable('contactos'), 300);
        }
    });

    /**
     * Search button clicks
     */
    d.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action="search"]');
        if (btn) {
            const type = btn.dataset.module;
            reloadTable(type);
        }
    });

    /**
     * Custom events from workspace
     */
    d.addEventListener('tab-shown', (e) => {
        const tabName = e.detail?.tabName;
        if (tabName === 'clientes') {
            log.info('Tab shown from workspace: clientes');
            loadClientesTable();
        }
    });

    /**
     * CRUD completion events
     */
    d.addEventListener('clienteGuardado', () => {
        log.info('Cliente saved, reloading table');
        reloadTable('clientes');
    });

    d.addEventListener('clienteEliminado', () => {
        log.info('Cliente deleted, reloading table');
        reloadTable('clientes');
    });

    d.addEventListener('contactoGuardado', () => {
        log.info('Contacto saved, reloading table');
        reloadTable('contactos');
    });

    d.addEventListener('contactoEliminado', () => {
        log.info('Contacto deleted, reloading table');
        reloadTable('contactos');
    });

    /**
     * Bootstrap tab change events
     */
    d.addEventListener('shown.bs.tab', (e) => {
        const tabId = e.target.id;
        if (tabId === 'tab-clientes') {
            log.info('Bootstrap tab shown: clientes');
            loadClientesTable();
        } else if (tabId === 'tab-contactos') {
            log.info('Bootstrap tab shown: contactos');
            loadContactosTable();
        }
    });

    /**
     * HTMX settle events - Show offcanvas after HTML is injected and rendered
     * ⚠️ Use htmx:afterSettle instead of afterSwap for better timing
     * ⚠️ Wait for Bootstrap to be available (CDN loading)
     */
    function waitForBootstrap(callback) {
        if (w.bootstrap) {
            callback();
        } else {
            // Bootstrap still loading from CDN, retry
            setTimeout(() => waitForBootstrap(callback), 50);
        }
    }
    
    d.body.addEventListener('htmx:afterSettle', (e) => {
        const target = e.detail.target;
        
        if (target && target.id === 'offcanvas-container-clientes') {
            // Cliente offcanvas loaded (create/edit/view)
            log.info('Cliente offcanvas loaded, waiting for DOM...');
            
            // Wait for next frame to ensure DOM is fully updated
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const offcanvasEl = d.getElementById('offcanvas-cliente');
                    if (offcanvasEl) {
                        // Wait for Bootstrap to be available
                        waitForBootstrap(() => {
                            try {
                                const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                                offcanvasInstance.show();
                                log.info('Cliente offcanvas shown successfully');
                            } catch (err) {
                                log.error('Error showing offcanvas', err);
                            }
                        });
                    } else {
                        log.error('offcanvas-cliente not found in DOM', {
                            container: target.innerHTML.substring(0, 100)
                        });
                    }
                });
            });
        } else if (target && target.id === 'offcanvas-container-contactos') {
            // Contactos offcanvas loaded
            log.info('Contactos offcanvas loaded, waiting for DOM...');
            
            // Wait for next frame to ensure DOM is fully updated
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const offcanvasEl = d.getElementById('offcanvas-contactos');
                    if (offcanvasEl) {
                        // Wait for Bootstrap to be available
                        waitForBootstrap(() => {
                            try {
                                const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                                offcanvasInstance.show();
                                log.info('Contactos offcanvas shown successfully');
                            } catch (err) {
                                log.error('Error showing offcanvas', err);
                            }
                        });
                    } else {
                        log.error('offcanvas-contactos not found in DOM');
                    }
                });
            });
        }
    });

    /**
     * Initialize when tab is already visible
     */
    d.addEventListener('DOMContentLoaded', () => {
        const section = d.getElementById('tab-clientes');
        if (section && section.style.display !== 'none') {
            log.info('Clientes tab visible on load, initializing');
            loadClientesTable();
        }
    });

    // ============================================================
    // NOTIFICATION HELPERS
    // ============================================================

    function showSuccess(msg) {
        if (w.UIManager) {
            w.UIManager.success(msg);
        }
        log.info('Success: ' + msg);
    }

    function showError(msg) {
        if (w.UIManager) {
            w.UIManager.error(msg);
        }
        log.error('Error: ' + msg);
    }

    // ============================================================
    // INITIALIZATION
    // ============================================================

    log.info('Module loaded and ready');

    // Export for testing/debugging
    w.ClientesListModule = {
        state,
        loadClientesTable,
        loadContactosTable,
        reloadTable,
        log
    };

})(window, document);
