/**
 * proveedores.utils.js - Helpers y utilidades para el módulo de proveedores.
 * [ARCHITECTURE v3.5]
 * - Centralización de lógica de búsqueda y autocompletado.
 */
(function (w) {
    'use strict';

    const proveedoresUtils = {
        /**
         * Configura el autocompletado de cuentas contables.
         * @param {Object} config - Configuración de elementos del DOM.
         */
        setupCuentaAutocomplete: function (config) {
            const { inputId, resultsId, hiddenId, onSelect } = config;
            const input = document.getElementById(inputId);
            const results = document.getElementById(resultsId);
            const hidden = document.getElementById(hiddenId);

            if (!input || !results || !hidden) return;

            let debounceTimer;

            input.addEventListener('input', function () {
                clearTimeout(debounceTimer);
                const q = this.value.trim();

                if (q.length < 2) {
                    results.classList.add('d-none');
                    return;
                }

                debounceTimer = setTimeout(async () => {
                    const response = await w.Sintel.Proveedores.API.searchCuentas(q);
                    if (response.ok && response.data) {
                        renderResults(response.data);
                    }
                }, 300);
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
        }
    };

    w.Sintel = w.Sintel || {};
    w.Sintel.Proveedores = w.Sintel.Proveedores || {};
    w.Sintel.Proveedores.Utils = proveedoresUtils;

})(window);
