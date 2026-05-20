/**
 * proveedores.utils.js - Helpers y utilidades para el módulo de proveedores.
 * [ARCHITECTURE v3.5]
 * - Centralización de lógica de búsqueda y autocompletado.
 */
(function (w) {
    'use strict';

    const proveedoresUtils = {
        /**
         * Configura el autocompletado de cuentas contables con sincronización en cascada.
         * @param {Object} config - Configuración de elementos del DOM.
         * @param {string} config.inputId - ID del input de búsqueda
         * @param {string} config.resultsId - ID del div de resultados
         * @param {string} config.hiddenId - ID del input oculto UUID
         * @param {Array<string>} config.cascadeTriggers - IDs de campos que disparan recarga (tipo_persona, regimen_tributario, etc)
         * @param {Function} config.onSelect - Callback opcional al seleccionar
         */
        setupCuentaAutocomplete: function (config) {
            const { inputId, resultsId, hiddenId, cascadeTriggers, onSelect } = config;
            const input = document.getElementById(inputId);
            const results = document.getElementById(resultsId);
            const hidden = document.getElementById(hiddenId);

            if (!input || !results || !hidden) return;

            let debounceTimer;

            const performSearch = async (q) => {
                if (q.length < 2) {
                    results.classList.add('d-none');
                    return;
                }

                const response = await w.AppProveedor.API.searchCuentas(q);
                if (response.ok && response.data) {
                    const data = Array.isArray(response.data) ? response.data : (response.data.results || []);
                    renderResults(data);
                }
            };

            input.addEventListener('input', function () {
                clearTimeout(debounceTimer);
                const q = this.value.trim();

                debounceTimer = setTimeout(() => performSearch(q), 300);
            });

            function renderResults(data) {
                results.innerHTML = '';
                if (data.length === 0) {
                    results.innerHTML = '<div class="list-group-item">No se encontraron cuentas</div>';
                } else {
                    data.forEach(item => {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'list-group-item list-group-item-action text-start';
                        btn.innerHTML = `<strong>${item.codigo}</strong> - ${item.nombre}`;
                        btn.addEventListener('click', () => selectItem(item));
                        results.appendChild(btn);
                    });
                }
                results.classList.remove('d-none');
            }

            function selectItem(item) {
                input.value = `${item.codigo} - ${item.nombre}`;
                hidden.value = item.uuid;
                results.classList.add('d-none');
                if (typeof onSelect === 'function') onSelect(item);
            }

            // Cerrar resultados al hacer click fuera
            document.addEventListener('click', function (e) {
                if (!input.contains(e.target) && !results.contains(e.target)) {
                    results.classList.add('d-none');
                }
            });

            // Actualización en cascada: cuando cambian campos asociados, recarga opciones
            if (cascadeTriggers && Array.isArray(cascadeTriggers)) {
                cascadeTriggers.forEach(fieldId => {
                    const field = document.getElementById(fieldId);
                    if (field) {
                        field.addEventListener('change', function () {
                            // Limpiar búsqueda anterior y resultados
                            input.value = '';
                            hidden.value = '';
                            results.classList.add('d-none');
                        });
                    }
                });
            }
        }
    };

    w.AppProveedor = w.AppProveedor || {};
    w.AppProveedor.Utils = proveedoresUtils;

    // Backwards compatibility wrapper
    w.Sintel = w.Sintel || {};
    w.Sintel.Proveedores = w.Sintel.Proveedores || {};
    w.Sintel.Proveedores.Utils = w.AppProveedor.Utils;

})(window);
