/**
 * asientos_editar.js - Módulo de Edición de Asientos Contables v2.61 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ HTMX: Usa HTMX para cargar offcanvas dinámicamente
 * ⚠️ Separación de responsabilidades: EXCLUSIVAMENTE para EDITAR asientos (no crear)
 * 
 * ⚠️ v2.61: Sistema de Edición de Asientos
 * - Carga datos del asiento existente
 * - Carga movimientos existentes en la tabla
 * - Valida cuadratura en tiempo real
 * - Actualiza asiento existente (PUT/PATCH)
 * 
 * Dependencias globales requeridas:
 * - w.contabilidadAPI (definido en contabilidad.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - HTMX (cargado globalmente)
 * - Bootstrap (cargado globalmente)
 * - asientos_form.js (para funciones compartidas de cuadratura)
 */
(function (w, d) {
  'use strict';

  const MOD = '[asientos.editar]';
  const OFFCANVAS_ID = 'offcanvas-asiento-editar';
  const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-asientos';
  const API_BASE = '/api/v1/contabilidad/';
  const CUENTAS_API = `${API_BASE}cuentas-contables/`;
  const ASIENTOS_API = `${API_BASE}asientos-contables/`;

  // Estado del módulo
  let state = {
    asientoId: null,
    cuentas: [], // Cache de cuentas contables
    movimientos: [], // Array de movimientos en memoria
    movimientoCounter: 0 // Contador para índices únicos
  };

  // Singleton: Instancia del Offcanvas
  let offcanvasInstance = null;

  // ⚠️ CRÍTICO v2.61: Exponer AppAsientosEditar INMEDIATAMENTE
  if (!w.AppAsientosEditar) {
    w.AppAsientosEditar = {};
    console.log(`${MOD} AppAsientosEditar expuesto`);
  }

  /**
   * Helper: Obtener CSRF token
   */
  function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = d.cookie.split(';');
    for (let cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) return value;
    }
    return '';
  }

  /**
   * Helper: Formatear dinero
   */
  function fmtMoney(v) {
    if (w.DOMUtils && typeof w.DOMUtils.fmtMoney === 'function') {
      return w.DOMUtils.fmtMoney(v);
    }
    const num = parseFloat(v) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  /**
   * Cargar cuentas contables
   */
  async function cargarCuentasContables() {
    try {
      const response = await fetch(CUENTAS_API, {
        headers: {
          'X-CSRFToken': getCSRFToken()
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      state.cuentas = data.results || data;
      return state.cuentas;
    } catch (error) {
      console.error(`${MOD} Error al cargar cuentas contables:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar cuentas contables' } }, MOD);
      }
      return [];
    }
  }

  /**
   * Cargar datos del asiento desde el servidor
   */
  async function cargarDatosAsiento(asientoId) {
    if (!asientoId) {
      console.warn(`${MOD} ID de asiento no proporcionado`);
      return null;
    }

    try {
      // Intentar obtener por ID numérico primero, luego por UUID
      let url = `${ASIENTOS_API}${asientoId}/`;
      
      const response = await fetch(url, {
        headers: {
          'X-CSRFToken': getCSRFToken()
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const asiento = await response.json();
      return asiento;
    } catch (error) {
      console.error(`${MOD} Error al cargar asiento:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el asiento' } }, MOD);
      }
      return null;
    }
  }

  /**
   * Poblar formulario con datos del asiento
   */
  function poblarFormulario(asiento) {
    if (!asiento) return;

    // Datos básicos
    const numeroInput = d.getElementById('input-numero');
    if (numeroInput) numeroInput.value = asiento.numero || '';

    const fechaInput = d.getElementById('input-fecha');
    if (fechaInput && asiento.fecha) {
      // Convertir fecha a formato YYYY-MM-DD
      const fecha = new Date(asiento.fecha);
      fechaInput.value = fecha.toISOString().split('T')[0];
    }

    const estadoSelect = d.getElementById('select-estado');
    if (estadoSelect) estadoSelect.value = asiento.estado || 'BORRADOR';

    const descripcionTextarea = d.getElementById('input-descripcion');
    if (descripcionTextarea) descripcionTextarea.value = asiento.descripcion || '';

    const tipoComprobanteSelect = d.getElementById('select-tipo-comprobante');
    if (tipoComprobanteSelect) tipoComprobanteSelect.value = asiento.tipo_comprobante || '';

    const numeroComprobanteInput = d.getElementById('input-numero-comprobante');
    if (numeroComprobanteInput) numeroComprobanteInput.value = asiento.numero_comprobante || '';

    // Cargar movimientos
    if (asiento.movimientos && Array.isArray(asiento.movimientos)) {
      cargarMovimientosEnTabla(asiento.movimientos);
    }
  }

  /**
   * Cargar movimientos existentes en la tabla
   */
  async function cargarMovimientosEnTabla(movimientos) {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) {
      console.warn(`${MOD} tbody-movimientos no encontrado`);
      return;
    }

    // Limpiar tabla
    tbody.innerHTML = '';
    state.movimientos = [];
    state.movimientoCounter = 0;

    // Cargar cuentas si no están cargadas
    if (state.cuentas.length === 0) {
      await cargarCuentasContables();
    }

    // Agregar cada movimiento
    for (const mov of movimientos) {
      agregarMovimientoDesdeDatos(mov);
    }

    // Actualizar totales
    actualizarTotales();
  }

  /**
   * Agregar movimiento desde datos del servidor
   */
  function agregarMovimientoDesdeDatos(movData) {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) return;

    const template = d.getElementById('template-movimiento-row');
    if (!template) {
      console.warn(`${MOD} Template de movimiento no encontrado`);
      return;
    }

    const row = template.content.cloneNode(true);
    const tr = row.querySelector('tr');
    const index = state.movimientoCounter++;
    tr.setAttribute('data-movimiento-index', index);

    // Actualizar orden
    const ordenSpan = tr.querySelector('.movimiento-orden');
    if (ordenSpan) ordenSpan.textContent = index + 1;

    // Seleccionar cuenta
    const cuentaSelect = tr.querySelector('.select-cuenta');
    if (cuentaSelect) {
      // Poblar opciones de cuentas
      state.cuentas.forEach(cuenta => {
        const option = d.createElement('option');
        option.value = cuenta.id;
        option.textContent = `${cuenta.codigo} - ${cuenta.nombre}`;
        if (movData.cuenta === cuenta.id || movData.cuenta_id === cuenta.id) {
          option.selected = true;
        }
        cuentaSelect.appendChild(option);
      });

      // Seleccionar cuenta del movimiento
      if (movData.cuenta) {
        cuentaSelect.value = movData.cuenta;
      } else if (movData.cuenta_id) {
        cuentaSelect.value = movData.cuenta_id;
      }
    }

    // Descripción
    const descripcionInput = tr.querySelector('input[name*="descripcion"]');
    if (descripcionInput) descripcionInput.value = movData.descripcion || '';

    // Débito y Crédito
    const debeInput = tr.querySelector('.input-debe');
    if (debeInput) debeInput.value = parseFloat(movData.debe || 0).toFixed(2);

    const haberInput = tr.querySelector('.input-haber');
    if (haberInput) haberInput.value = parseFloat(movData.haber || 0).toFixed(2);

    // Terceros (si están disponibles)
    const terceroNitInput = tr.querySelector('input[name*="tercero_nit"]');
    if (terceroNitInput) terceroNitInput.value = movData.tercero_nit || '';

    const terceroRazonSocialInput = tr.querySelector('input[name*="tercero_razon_social"]');
    if (terceroRazonSocialInput) terceroRazonSocialInput.value = movData.tercero_razon_social || '';

    // Botón eliminar
    const btnEliminar = tr.querySelector('.btn-eliminar-movimiento');
    if (btnEliminar) {
      btnEliminar.addEventListener('click', () => eliminarMovimiento(index));
    }

    // Agregar listeners para actualizar totales
    if (debeInput) {
      debeInput.addEventListener('input', actualizarTotales);
    }
    if (haberInput) {
      haberInput.addEventListener('input', actualizarTotales);
    }

    tbody.appendChild(tr);

    // Guardar en estado
    state.movimientos.push({
      index: index,
      cuenta: movData.cuenta || movData.cuenta_id,
      descripcion: movData.descripcion || '',
      debe: parseFloat(movData.debe || 0),
      haber: parseFloat(movData.haber || 0),
      orden: index + 1,
      tipo_tercero: movData.tipo_tercero || null,
      tercero_nit: movData.tercero_nit || null,
      tercero_razon_social: movData.tercero_razon_social || null
    });
  }

  /**
   * Agregar nuevo movimiento (vacío)
   */
  function agregarMovimiento() {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) return;

    const template = d.getElementById('template-movimiento-row');
    if (!template) {
      console.warn(`${MOD} Template de movimiento no encontrado`);
      return;
    }

    const row = template.content.cloneNode(true);
    const tr = row.querySelector('tr');
    const index = state.movimientoCounter++;
    tr.setAttribute('data-movimiento-index', index);

    // Actualizar orden
    const ordenSpan = tr.querySelector('.movimiento-orden');
    if (ordenSpan) ordenSpan.textContent = index + 1;

    // Poblar select de cuentas
    const cuentaSelect = tr.querySelector('.select-cuenta');
    if (cuentaSelect) {
      state.cuentas.forEach(cuenta => {
        const option = d.createElement('option');
        option.value = cuenta.id;
        option.textContent = `${cuenta.codigo} - ${cuenta.nombre}`;
        cuentaSelect.appendChild(option);
      });
    }

    // Botón eliminar
    const btnEliminar = tr.querySelector('.btn-eliminar-movimiento');
    if (btnEliminar) {
      btnEliminar.addEventListener('click', () => eliminarMovimiento(index));
    }

    // Listeners para actualizar totales
    const debeInput = tr.querySelector('.input-debe');
    const haberInput = tr.querySelector('.input-haber');
    if (debeInput) debeInput.addEventListener('input', actualizarTotales);
    if (haberInput) haberInput.addEventListener('input', actualizarTotales);

    tbody.appendChild(tr);

    // Guardar en estado
    state.movimientos.push({
      index: index,
      cuenta: null,
      descripcion: '',
      debe: 0,
      haber: 0,
      orden: index + 1
    });

    actualizarTotales();
  }

  /**
   * Eliminar movimiento
   */
  function eliminarMovimiento(index) {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) return;

    const row = tbody.querySelector(`tr[data-movimiento-index="${index}"]`);
    if (row) {
      row.remove();
    }

    // Remover del estado
    state.movimientos = state.movimientos.filter(m => m.index !== index);

    // Reordenar
    const rows = tbody.querySelectorAll('tr[data-movimiento-index]');
    rows.forEach((r, idx) => {
      const ordenSpan = r.querySelector('.movimiento-orden');
      if (ordenSpan) ordenSpan.textContent = idx + 1;
    });

    actualizarTotales();
  }

  /**
   * Calcular totales desde el DOM
   */
  function calcularTotales() {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) return { debe: 0, haber: 0 };

    let totalDebe = 0;
    let totalHaber = 0;

    const rows = tbody.querySelectorAll('tr[data-movimiento-index]');
    rows.forEach(row => {
      const debeInput = row.querySelector('.input-debe');
      const haberInput = row.querySelector('.input-haber');
      
      const debe = parseFloat(debeInput?.value || 0);
      const haber = parseFloat(haberInput?.value || 0);
      
      totalDebe += debe;
      totalHaber += haber;
    });

    return { debe: totalDebe, haber: totalHaber };
  }

  /**
   * Actualizar displays de totales
   */
  function actualizarTotales() {
    // Actualizar estado desde el DOM
    const tbody = d.getElementById('tbody-movimientos');
    if (tbody) {
      const rows = tbody.querySelectorAll('tr[data-movimiento-index]');
      rows.forEach(row => {
        const index = parseInt(row.getAttribute('data-movimiento-index'));
        const debeInput = row.querySelector('.input-debe');
        const haberInput = row.querySelector('.input-haber');
        const selectCuenta = row.querySelector('.select-cuenta');
        const inputDescripcion = row.querySelector('input[name*="descripcion"]');
        
        const movimiento = state.movimientos.find(m => m.index === index);
        if (movimiento) {
          movimiento.debe = parseFloat(debeInput?.value || 0);
          movimiento.haber = parseFloat(haberInput?.value || 0);
          movimiento.cuenta = selectCuenta?.value || null;
          movimiento.descripcion = inputDescripcion?.value || '';
        }
      });
    }
    
    const { debe, haber } = calcularTotales();
    const diferencia = Math.abs(debe - haber);
    const cuadra = diferencia <= 0.01;

    // Actualizar displays
    const totalDebeDisplay = d.getElementById('total-debe-display');
    const totalHaberDisplay = d.getElementById('total-haber-display');
    const cuadraturaRow = d.getElementById('row-cuadratura');
    const cuadraturaStatus = d.getElementById('cuadratura-status');
    const cuadraturaDiferencia = d.getElementById('cuadratura-diferencia');

    if (totalDebeDisplay) totalDebeDisplay.textContent = fmtMoney(debe);
    if (totalHaberDisplay) totalHaberDisplay.textContent = fmtMoney(haber);

    if (cuadraturaRow) {
      if (state.movimientos.length > 0) {
        cuadraturaRow.classList.remove('d-none');
      } else {
        cuadraturaRow.classList.add('d-none');
      }
    }

    if (cuadraturaStatus) {
      if (cuadra && state.movimientos.length > 0) {
        cuadraturaStatus.innerHTML = '<i class="bi bi-check-circle text-success me-1"></i>Cuadrado';
        if (cuadraturaRow) cuadraturaRow.classList.remove('table-danger');
        if (cuadraturaRow) cuadraturaRow.classList.add('table-success');
      } else {
        cuadraturaStatus.innerHTML = '<i class="bi bi-x-circle text-danger me-1"></i>No cuadra';
        if (cuadraturaRow) cuadraturaRow.classList.remove('table-success');
        if (cuadraturaRow) cuadraturaRow.classList.add('table-danger');
      }
    }

    if (cuadraturaDiferencia) {
      cuadraturaDiferencia.textContent = `Diferencia: ${fmtMoney(diferencia)}`;
    }

    // Actualizar resumen
    const resumenTotalDebe = d.getElementById('resumen-total-debe');
    const resumenTotalHaber = d.getElementById('resumen-total-haber');
    const resumenDiferencia = d.getElementById('resumen-diferencia');
    const resumenStatus = d.getElementById('resumen-status');

    if (resumenTotalDebe) resumenTotalDebe.textContent = fmtMoney(debe);
    if (resumenTotalHaber) resumenTotalHaber.textContent = fmtMoney(haber);
    if (resumenDiferencia) resumenDiferencia.textContent = fmtMoney(diferencia);

    if (resumenStatus) {
      if (state.movimientos.length === 0) {
        resumenStatus.textContent = 'Sin movimientos';
        resumenStatus.className = 'badge bg-secondary';
      } else if (cuadra) {
        resumenStatus.textContent = 'Cuadrado';
        resumenStatus.className = 'badge bg-success';
      } else {
        resumenStatus.textContent = 'No cuadra';
        resumenStatus.className = 'badge bg-danger';
      }
    }

    // Validar que todos los movimientos tengan cuenta
    let todosTienenCuenta = true;
    if (tbody) {
      const rows = tbody.querySelectorAll('tr[data-movimiento-index]');
      rows.forEach(row => {
        const selectCuenta = row.querySelector('.select-cuenta');
        if (!selectCuenta || !selectCuenta.value) {
          todosTienenCuenta = false;
        }
      });
    }

    // Habilitar/deshabilitar botón de guardar
    const btnGuardar = d.getElementById('btn-guardar-asiento-editar');
    if (btnGuardar) {
      const puedeGuardar = cuadra && state.movimientos.length > 0 && todosTienenCuenta;
      btnGuardar.disabled = !puedeGuardar;
    }

    return { debe, haber, diferencia, cuadra };
  }

  /**
   * Recolectar datos del formulario
   */
  function recolectarDatos() {
    const form = d.getElementById('form-asiento-editar');
    if (!form) return null;

    const formData = new FormData(form);
    const data = {
      numero: formData.get('numero') || null,
      fecha: formData.get('fecha'),
      descripcion: formData.get('descripcion'),
      estado: formData.get('estado') || 'BORRADOR',
      tipo_comprobante: formData.get('tipo_comprobante') || null,
      numero_comprobante: formData.get('numero_comprobante') || null
    };

    // Recolectar movimientos
    const tbody = d.getElementById('tbody-movimientos');
    const movimientos = [];
    
    if (tbody) {
      const rows = tbody.querySelectorAll('tr[data-movimiento-index]');
      rows.forEach((row, idx) => {
        const cuentaSelect = row.querySelector('.select-cuenta');
        const descripcionInput = row.querySelector('input[name*="descripcion"]');
        const debeInput = row.querySelector('.input-debe');
        const haberInput = row.querySelector('.input-haber');

        const cuentaId = cuentaSelect?.value;
        const descripcion = descripcionInput?.value || '';
        const debe = parseFloat(debeInput?.value || 0);
        const haber = parseFloat(haberInput?.value || 0);

        if (cuentaId && (debe > 0 || haber > 0)) {
          const tipoTerceroInput = row.querySelector('input[name*="tipo_tercero"], select[name*="tipo_tercero"]');
          const terceroNitInput = row.querySelector('input[name*="tercero_nit"]');
          const terceroRazonSocialInput = row.querySelector('input[name*="tercero_razon_social"]');
          
          const movimiento = {
            cuenta: parseInt(cuentaId),
            descripcion: descripcion,
            debe: debe,
            haber: haber,
            orden: idx + 1
          };
          
          if (tipoTerceroInput) {
            movimiento.tipo_tercero = tipoTerceroInput.value || null;
          }
          if (terceroNitInput) {
            movimiento.tercero_nit = terceroNitInput.value || null;
          }
          if (terceroRazonSocialInput) {
            movimiento.tercero_razon_social = terceroRazonSocialInput.value || null;
          }
          
          movimientos.push(movimiento);
        }
      });
    }

    data.movimientos = movimientos;
    return data;
  }

  /**
   * Guardar cambios del asiento
   */
  async function guardar() {
    const form = d.getElementById('form-asiento-editar');
    if (!form) {
      console.warn(`${MOD} Formulario #form-asiento-editar no encontrado`);
      return;
    }

    // Limpiar errores previos
    const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
    if (offcanvasEditar) {
      const errorContainer = offcanvasEditar.querySelector('#error-container');
      if (errorContainer) {
        errorContainer.classList.add('d-none');
        const errorMessage = errorContainer.querySelector('#error-message');
        if (errorMessage) errorMessage.textContent = '';
      }
    }

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const datos = recolectarDatos();
    if (!datos) {
      console.warn(`${MOD} No se pudieron recolectar datos del formulario`);
      return;
    }

    if (!datos.movimientos || datos.movimientos.length === 0) {
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error('Debe agregar al menos un movimiento contable');
      } else {
        alert('Debe agregar al menos un movimiento contable');
      }
      return;
    }

    // Validar cuadratura
    const { debe, haber, diferencia, cuadra } = actualizarTotales();
    
    if (!cuadra) {
      const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
      if (offcanvasEditar) {
        let errorContainer = offcanvasEditar.querySelector('#error-container');
        let errorMessage = offcanvasEditar.querySelector('#error-message');
        
        if (!errorContainer && offcanvasEditar) {
          const offcanvasBody = offcanvasEditar.querySelector('.offcanvas-body');
          if (offcanvasBody) {
            const errorHtml = `
              <div id="error-container" class="mt-3">
                <div class="alert alert-danger d-flex align-items-start" role="alert">
                  <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                  <div class="flex-grow-1">
                    <div id="error-message" class="mb-0"></div>
                  </div>
                </div>
              </div>
            `;
            offcanvasBody.insertAdjacentHTML('afterbegin', errorHtml);
            errorContainer = offcanvasEditar.querySelector('#error-container');
            errorMessage = offcanvasEditar.querySelector('#error-message');
          }
        }
        
        if (errorContainer && errorMessage) {
          errorMessage.innerHTML = `⚠️ El asiento no está cuadrado. Diferencia: <strong>${fmtMoney(diferencia)}</strong><br><small class="text-muted">Total Débito: ${fmtMoney(debe)} | Total Crédito: ${fmtMoney(haber)}</small>`;
          errorContainer.classList.remove('d-none');
          setTimeout(() => {
            errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }, 100);
        }
      }
      return;
    }

    const btnGuardar = d.getElementById('btn-guardar-asiento-editar');
    const btnOriginalText = btnGuardar ? btnGuardar.innerHTML : '';
    
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    }

    try {
      // ⚠️ v2.61: Actualizar asiento existente (PUT)
      const asientoId = state.asientoId || d.getElementById('input-id')?.value;
      if (!asientoId) {
        throw new Error('ID de asiento no encontrado');
      }

      const payload = {
        ...(datos.numero && datos.numero.trim() ? { numero: datos.numero.trim() } : {}),
        fecha: datos.fecha,
        descripcion: datos.descripcion,
        estado: datos.estado,
        tipo_comprobante: datos.tipo_comprobante || null,
        numero_comprobante: datos.numero_comprobante || null,
        movimientos: datos.movimientos.map(mov => ({
          cuenta: mov.cuenta,
          descripcion: mov.descripcion || '',
          debe: parseFloat(mov.debe) || 0,
          haber: parseFloat(mov.haber) || 0,
          orden: mov.orden,
          tipo_tercero: mov.tipo_tercero || null,
          tercero_nit: mov.tercero_nit || null,
          tercero_razon_social: mov.tercero_razon_social || null
        }))
      };

      const responseAsiento = await fetch(`${ASIENTOS_API}${asientoId}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });

      if (!responseAsiento.ok) {
        const errorData = await responseAsiento.json().catch(() => ({ detail: 'Error al actualizar asiento' }));
        
        // Manejo de errores similar a asientos_form.js
        if (responseAsiento.status === 422) {
          const mockXHR = {
            status: 422,
            statusText: 'Unprocessable Entity',
            response: JSON.stringify(errorData),
            responseText: JSON.stringify(errorData),
            getResponseHeader: function() { return 'application/json'; }
          };
          
          if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
            w.ErrorHandler.show(mockXHR);
          } else if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
            w.SintelFeedback.error(errorData.message || errorData.detail || 'Error de validación. Revise los campos marcados.');
          }
        } else {
          throw new Error(errorData.detail || errorData.message || `HTTP ${responseAsiento.status}`);
        }
        
        if (btnGuardar) {
          btnGuardar.disabled = false;
          btnGuardar.innerHTML = btnOriginalText;
        }
        return;
      }

      const asientoData = await responseAsiento.json();

      if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
        w.SintelFeedback.success('Asiento contable actualizado correctamente');
      }

      // Cerrar offcanvas
      if (offcanvasInstance) {
        offcanvasInstance.hide();
      }

      // Refrescar tabla Tabulator (si existe)
      if (w.AppAsientos && typeof w.AppAsientos.refreshGrid === 'function') {
        w.AppAsientos.refreshGrid();
      }

    } catch (error) {
      console.error(`${MOD} ❌ Error inesperado al actualizar asiento:`, error);
      
      const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
      if (offcanvasEditar) {
        let errorContainer = offcanvasEditar.querySelector('#error-container');
        let errorMessage = offcanvasEditar.querySelector('#error-message');
        
        if (!errorContainer && offcanvasEditar) {
          const offcanvasBody = offcanvasEditar.querySelector('.offcanvas-body');
          if (offcanvasBody) {
            const errorHtml = `
              <div id="error-container" class="mt-3">
                <div class="alert alert-danger d-flex align-items-start" role="alert">
                  <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                  <div class="flex-grow-1">
                    <div id="error-message" class="mb-0"></div>
                  </div>
                </div>
              </div>
            `;
            offcanvasBody.insertAdjacentHTML('afterbegin', errorHtml);
            errorContainer = offcanvasEditar.querySelector('#error-container');
            errorMessage = offcanvasEditar.querySelector('#error-message');
          }
        }
        
        if (errorContainer && errorMessage) {
          errorMessage.textContent = `Error inesperado: ${error.message || 'Error desconocido al actualizar el asiento.'}`;
          errorContainer.classList.remove('d-none');
          setTimeout(() => {
            errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }, 100);
        }
      }
      
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
      }
    } finally {
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = btnOriginalText;
      }
    }
  }

  /**
   * Mostrar offcanvas
   */
  function showOffcanvas(offcanvasEl) {
    if (!offcanvasEl) return;
    
    if (window.bootstrap && window.bootstrap.Offcanvas) {
      offcanvasInstance = window.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      offcanvasInstance.show();
      console.log(`${MOD} Offcanvas mostrado`);
    } else {
      console.error(`${MOD} Bootstrap Offcanvas no disponible`);
    }
  }

  /**
   * Inicializar formulario de edición
   */
  async function inicializarFormularioEdicion() {
    const asientoId = state.asientoId || d.getElementById('input-id')?.value;
    if (!asientoId) {
      console.warn(`${MOD} ID de asiento no encontrado para inicializar`);
      return;
    }

    // Cargar cuentas contables
    await cargarCuentasContables();

    // Cargar datos del asiento
    const asiento = await cargarDatosAsiento(asientoId);
    if (asiento) {
      poblarFormulario(asiento);
    }

    // Configurar eventos
    const btnAgregar = d.getElementById('btn-agregar-movimiento');
    if (btnAgregar) {
      btnAgregar.addEventListener('click', agregarMovimiento);
    }

    const btnGuardar = d.getElementById('btn-guardar-asiento-editar');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', guardar);
    }

    // Actualizar totales
    actualizarTotales();
  }

  /**
   * Cargar offcanvas de edición
   */
  async function cargarOffcanvasEditarAsiento(asientoId) {
    if (!asientoId) {
      console.warn(`${MOD} ID de asiento no proporcionado`);
      return;
    }

    state.asientoId = asientoId;

    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) {
      console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
      return;
    }

    let url = `${ASIENTOS_API}${asientoId}/render-offcanvas/editar/`;

    try {
      await htmx.ajax('GET', url, {
        target: `#${OFFCANVAS_CONTAINER_ID}`,
        swap: 'innerHTML'
      });

      await new Promise(resolve => setTimeout(resolve, 100));

      const offcanvasEl = d.getElementById(OFFCANVAS_ID);
      if (offcanvasEl) {
        showOffcanvas(offcanvasEl);
        // Inicializar después de mostrar el offcanvas
        setTimeout(() => {
          inicializarFormularioEdicion();
        }, 200);
      } else {
        console.warn(`${MOD} Offcanvas #${OFFCANVAS_ID} no encontrado`);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas de edición:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario de edición' } }, MOD);
      } else {
        alert('Error al cargar el formulario de edición');
      }
    }
  }

  // ⚠️ HTMX: Escuchar evento afterSettle para inicializar cuando el offcanvas se carga
  d.body.addEventListener('htmx:afterSettle', function(evt) {
    const target = evt.detail.target;
    if (!target) return;
    
    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) return;
    
    if (target.id === OFFCANVAS_CONTAINER_ID || container.contains(target)) {
      const offcanvasEl = container.querySelector(`#${OFFCANVAS_ID}`);
      if (offcanvasEl) {
        console.log(`${MOD} Offcanvas cargado por HTMX, inicializando...`);
        setTimeout(() => {
          showOffcanvas(offcanvasEl);
          inicializarFormularioEdicion();
        }, 100);
      }
    }
  });

  // Exponer funciones públicas
  w.AppAsientosEditar.cargar = cargarOffcanvasEditarAsiento;
  w.AppAsientosEditar.agregarMovimiento = agregarMovimiento;
  w.AppAsientosEditar.eliminarMovimiento = eliminarMovimiento;
  w.AppAsientosEditar.actualizarTotales = actualizarTotales;
  w.AppAsientosEditar.guardar = guardar;

  // También exponer en AppAsientos para compatibilidad
  if (!w.AppAsientos) {
    w.AppAsientos = {};
  }
  w.AppAsientos.cargarOffcanvasEditarAsiento = cargarOffcanvasEditarAsiento;

  console.log(`${MOD} Módulo inicializado`);

})(window, document);
