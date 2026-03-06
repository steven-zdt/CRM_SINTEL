/**
 * Helpers de Cotizaciones v2.60
 * ⚠️ Feature-Sliced: Funciones utilitarias compartidas
 * ⚠️ API-First: Solo funciones de utilidad, sin lógica de negocio
 */
(function(w, d) {
  'use strict';

  const CotizacionesHelpers = {
    /**
     * Cargar clientes activos en el select
     * @param {HTMLElement} selectElement - Elemento select a poblar
     * @param {number|string} [clienteSeleccionadoId] - ID del cliente a preseleccionar (opcional)
     * @returns {Promise<boolean>} true si hay clientes disponibles
     */
    async cargarClientesEnSelect(selectElement, clienteSeleccionadoId = null) {
      if (!selectElement) {
        console.warn('[cotizaciones.helpers] Select element de clientes no encontrado');
        return false;
      }

      // ⚠️ Validar disponibilidad de window.http
      if (!w.http || typeof w.http !== 'function') {
        console.error('[cotizaciones.helpers] ❌ window.http no está disponible');
        selectElement.innerHTML = '<option value="">Error: Utilidad HTTP no disponible</option>';
        return false;
      }

      selectElement.innerHTML = '<option value="">Cargando clientes...</option>';
      console.log('[cotizaciones.helpers] Consultando API de clientes...');

      try {
        const res = await w.http('GET', '/api/v1/clientes/?page_size=100&activo=true');
        console.log('[cotizaciones.helpers] Respuesta de API:', res);
      
        if (!res.ok) {
          console.error('[cotizaciones.helpers] ❌ Error al cargar clientes:', res);
          selectElement.innerHTML = '<option value="">Error al cargar clientes. Intente recargar la página.</option>';
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(res, '[cotizaciones.helpers]');
          }
          return false;
        }

        const clientes = res.data?.results || res.data || [];
        console.log(`[cotizaciones.helpers] ✅ ${clientes.length} clientes recibidos de la API`);
        
        if (clientes.length === 0) {
          console.warn('[cotizaciones.helpers] ⚠️ No hay clientes disponibles');
          selectElement.innerHTML = '<option value="">No hay clientes disponibles</option>';
          return false;
        }

        selectElement.innerHTML = '<option value="">Seleccione un cliente</option>';
        
        // Normalizar clienteSeleccionadoId para comparación
        const clienteSeleccionadoIdNum = clienteSeleccionadoId != null 
          ? (typeof clienteSeleccionadoId === 'number' ? clienteSeleccionadoId : parseInt(String(clienteSeleccionadoId).trim(), 10))
          : null;
        
        let clientesAgregados = 0;
        clientes.forEach(cliente => {
          // ⚠️ CRÍTICO: Validar que cliente.id existe y es válido
          if (!cliente.id || (typeof cliente.id !== 'number' && typeof cliente.id !== 'string')) {
            console.warn('[cotizaciones.helpers] Cliente sin ID válido:', cliente);
            return;
          }
          
          // ⚠️ CRÍTICO: Convertir a número estrictamente (ID primario de la base de datos)
          const clienteId = typeof cliente.id === 'number' ? cliente.id : parseInt(String(cliente.id).trim(), 10);
          if (isNaN(clienteId) || clienteId <= 0) {
            console.warn('[cotizaciones.helpers] ID de cliente inválido:', cliente.id);
            return;
          }
          
          // ⚠️ CRÍTICO: option.value DEBE SER estrictamente el ID numérico (cliente.id)
          const option = d.createElement('option');
          // ⚠️ FUERZA BRUTA: Asegurar que value sea string del número (HTML requiere string)
          // pero el valor numérico es el que se enviará al backend
          option.value = String(clienteId); // HTML requiere string, pero contiene solo el ID numérico
          option.textContent = `${cliente.nombre_comercial || cliente.razon_social} (${cliente.numero_documento || ''})`;
          
          // ⚠️ VALIDACIÓN ADICIONAL: Verificar que el value sea correcto
          if (isNaN(parseInt(option.value, 10))) {
            console.error('[cotizaciones.helpers] ERROR: option.value no es numérico:', option.value);
            return; // Omitir este cliente si el value no es válido
          }
          
          // Preseleccionar si coincide con clienteSeleccionadoId
          if (clienteSeleccionadoIdNum !== null && clienteId === clienteSeleccionadoIdNum) {
            option.selected = true;
          }
          
          selectElement.appendChild(option);
          clientesAgregados++;
        });

        console.log(`[cotizaciones.helpers] ✅ ${clientesAgregados} clientes agregados al select`);
        return true;
      } catch (error) {
        console.error('[cotizaciones.helpers] ❌ Excepción al cargar clientes:', error);
        selectElement.innerHTML = '<option value="">Error: ' + (error.message || 'Error desconocido') + '</option>';
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({status: 500, data: {detail: error.message || 'Error al cargar clientes'}}, '[cotizaciones.helpers]');
        }
        return false;
      }
    },
    // ... dentro de CotizacionesHelpers ...
    async cargarConfiguracionesEnSelect(selectElement) {
      if (!selectElement) return;
      
      selectElement.innerHTML = '<option value="">Cargando...</option>';
      const response = await w.cotizacionesAPI.listConfiguraciones({ es_activo: true });
      
      if (response.ok) {
          const configs = response.data.results || [];
          selectElement.innerHTML = '<option value="">-- Seleccione Perfil --</option>';
          configs.forEach(c => {
              const opt = d.createElement('option');
              opt.value = c.id;
              opt.textContent = `${c.nombre_configuracion}${c.es_activo ? ' ✓' : ''}`;
              
              // ⚠️ v2.60: Inyectar datos para previsualización dinámica
              opt.setAttribute('data-dias', c.dias_validez || 15);
              opt.setAttribute('data-prefijo', c.prefijo_secuencia || '');
              opt.setAttribute('data-sufijo', c.sufijo_secuencia || '');
              opt.setAttribute('data-ultimo', c.ultimo_numero || 0);
              opt.setAttribute('data-semilla', c.semilla_inicial || 1);
              
              selectElement.appendChild(opt);
          });
      }
    },
    /**
     * Cargar perfiles activos en el select
     * @param {HTMLElement} selectElement - Elemento select a poblar
     * @returns {Promise<boolean>} true si hay perfiles disponibles
     */
    async cargarPerfilesEnSelect(selectElement) {
      if (!selectElement) {
        console.warn('[cotizaciones.helpers] Select element no encontrado');
        return false;
      }

      selectElement.innerHTML = '<option value="">Cargando perfiles...</option>';

      if (!w.cotizacionesAPI || typeof w.cotizacionesAPI.listConfiguraciones !== 'function') {
        console.error('[cotizaciones.helpers] cotizacionesAPI no está disponible');
        selectElement.innerHTML = '<option value="">API no disponible. Recargue la página.</option>';
        return false;
      }

      try {
        const response = await w.cotizacionesAPI.listConfiguraciones({ es_activo: true });
        console.log('[cotizaciones.helpers] Respuesta completa de API:', response);
        
        if (!response.ok) {
          console.error('[cotizaciones.helpers] ❌ Error al cargar perfiles:', response);
          selectElement.innerHTML = '<option value="">Error al cargar perfiles. Intente recargar la página.</option>';
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(response, '[cotizaciones.helpers]');
          }
          return false;
        }

        // ⚠️ v2.60: Procesar estructura DRF paginada: {count, next, previous, results: [...]}
        let perfiles = [];
        if (response.data) {
          if (Array.isArray(response.data)) {
            // Si la respuesta es directamente un array (sin paginación)
            perfiles = response.data;
            console.log('[cotizaciones.helpers] Respuesta es array directo:', perfiles.length, 'perfiles');
          } else if (response.data.results && Array.isArray(response.data.results)) {
            // Si la respuesta tiene estructura paginada DRF
            perfiles = response.data.results;
            console.log('[cotizaciones.helpers] Respuesta paginada DRF:', {
              count: response.data.count,
              results: perfiles.length,
              perfiles: perfiles
            });
          } else {
            console.warn('[cotizaciones.helpers] ⚠️ Estructura de respuesta desconocida:', response.data);
          }
        }

        if (perfiles.length === 0) {
          console.warn('[cotizaciones.helpers] ⚠️ No hay perfiles disponibles');
          selectElement.innerHTML = '<option value="">No hay perfiles disponibles</option>';
          return false;
        }

        selectElement.innerHTML = '';

        const optionDefault = d.createElement('option');
        optionDefault.value = '';
        optionDefault.textContent = '-- Seleccione un perfil --';
        selectElement.appendChild(optionDefault);

        let perfilesAgregados = 0;
        perfiles.forEach((perfil, index) => {
          console.log(`[cotizaciones.helpers] Procesando perfil ${index + 1}:`, perfil);
          
          if (!perfil.id || (typeof perfil.id !== 'number' && typeof perfil.id !== 'string')) {
            console.warn('[cotizaciones.helpers] ⚠️ Perfil sin ID válido:', perfil);
            return;
          }
          
          const perfilId = typeof perfil.id === 'number' ? perfil.id : parseInt(String(perfil.id).trim(), 10);
          if (isNaN(perfilId) || perfilId <= 0) {
            console.warn('[cotizaciones.helpers] ⚠️ ID de perfil inválido:', perfil.id);
            return;
          }
          
          const option = d.createElement('option');
          option.value = String(perfilId);
          
          // ⚠️ v2.60: User-Driven - Solo mostrar nombre del perfil
          const nombrePerfil = perfil.nombre_configuracion || 'Sin nombre';
          option.textContent = `${nombrePerfil}${perfil.es_activo ? ' ✓' : ''}`;
          
          // ⚠️ v2.60: Inyectar datos para previsualización dinámica (Folio Proyectado y Fecha de Vencimiento)
          // Estos atributos permiten mostrar una previsualización en tiempo real sin alterar la lógica transaccional del backend
          option.setAttribute('data-dias', perfil.dias_validez || 15);
          option.setAttribute('data-prefijo', perfil.prefijo_secuencia || '');
          option.setAttribute('data-sufijo', perfil.sufijo_secuencia || '');
          option.setAttribute('data-ultimo', perfil.ultimo_numero || 0);
          option.setAttribute('data-semilla', perfil.semilla_inicial || 1);
          
          selectElement.appendChild(option);
          perfilesAgregados++;
        });

        console.log(`[cotizaciones.helpers] ✅ ${perfilesAgregados} perfiles agregados al select`);
        return true;
      } catch (error) {
        console.error('[cotizaciones.helpers] ❌ Excepción al cargar perfiles:', error);
        selectElement.innerHTML = '<option value="">Error: ' + (error.message || 'Error desconocido') + '</option>';
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({status: 500, data: {detail: error.message || 'Error al cargar perfiles'}}, '[cotizaciones.helpers]');
        }
        return false;
      }
    },

    /**
     * Actualizar preview del perfil seleccionado
     * @param {HTMLElement} modalElement - Elemento del modal/offcanvas
     * @param {HTMLElement} selectElement - Elemento select del perfil
     */
    actualizarPreviewPerfil(modalElement, selectElement) {
      const previewContainer = modalElement.querySelector('#preview-perfil-seleccionado');
      const previewContent = modalElement.querySelector('#preview-perfil-content');
      
      if (!previewContainer || !previewContent) {
        return;
      }

      const selectedOption = selectElement.options[selectElement.selectedIndex];
      if (!selectedOption || !selectedOption.value) {
        previewContainer.classList.add('d-none');
        return;
      }

      const iva = selectedOption.getAttribute('data-iva') || '0.00';
      const utilidad = selectedOption.getAttribute('data-utilidad') || '0.00';
      const usaAIU = selectedOption.getAttribute('data-usa-aiu') === 'true';
      const aiuAdmin = selectedOption.getAttribute('data-aiu-admin') || '0.00';
      const aiuImprevistos = selectedOption.getAttribute('data-aiu-imprevistos') || '0.00';
      const aiuUtilidad = selectedOption.getAttribute('data-aiu-utilidad') || '0.00';
      const tipoPlantilla = selectedOption.getAttribute('data-tipo-plantilla') || 'MIXTO';

      let previewHTML = `<div class="mb-1"><strong>IVA:</strong> ${parseFloat(iva).toFixed(2)}%</div>`;
      previewHTML += `<div class="mb-1"><strong>Utilidad:</strong> ${parseFloat(utilidad).toFixed(2)}%</div>`;
      previewHTML += `<div class="mb-1"><strong>AIU:</strong> ${usaAIU ? '<span class="badge bg-success">Sí</span>' : '<span class="badge bg-secondary">No</span>'}</div>`;
      
      if (usaAIU) {
        previewHTML += `<div class="mb-1"><strong>AIU Admin:</strong> ${parseFloat(aiuAdmin).toFixed(2)}%</div>`;
        previewHTML += `<div class="mb-1"><strong>AIU Imprevistos:</strong> ${parseFloat(aiuImprevistos).toFixed(2)}%</div>`;
        previewHTML += `<div class="mb-1"><strong>AIU Utilidad:</strong> ${parseFloat(aiuUtilidad).toFixed(2)}%</div>`;
      }
      
      previewHTML += `<div class="mb-1"><strong>Tipo Plantilla:</strong> ${tipoPlantilla}</div>`;

      previewContent.innerHTML = previewHTML;
      previewContainer.classList.remove('d-none');
    },

    /**
     * Recargar selectores de plantillas en todos los elementos del DOM
     */
    async recargarSelectoresPlantillas() {
      if (!w.cotizacionesAPI) {
        console.warn('[cotizaciones.helpers] cotizacionesAPI no disponible');
        return;
      }

      const response = await w.cotizacionesAPI.listConfiguraciones({ es_activo: true });
      if (!response.ok) {
        console.error('[cotizaciones.helpers] Error al cargar configuraciones:', response);
        return;
      }

      const configuraciones = response.data.results || response.data || [];
      const selects = d.querySelectorAll('select[id*="plantilla"], select[id*="configuracion"], select[id*="perfil"]');
      
      selects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '';
        
        const optionDefault = d.createElement('option');
        optionDefault.value = '';
        optionDefault.textContent = '-- Seleccione un perfil --';
        select.appendChild(optionDefault);
        
        configuraciones.forEach(config => {
          const option = d.createElement('option');
          option.value = config.id;
          option.textContent = `${config.nombre_configuracion} (${config.tipo_plantilla_display || config.tipo_plantilla})` + (config.es_activo ? ' ✓' : '');
          select.appendChild(option);
        });
        
        if (currentValue) select.value = currentValue;
      });
    }
  };

  // Exportar al namespace global
  w.CotizacionesHelpers = CotizacionesHelpers;
  
  // ⚠️ Compatibilidad: Mantener w.cotizacionesModals para transición
  w.cotizacionesModals = CotizacionesHelpers;

})(window, document);
