/**
 * asientos_form.js - Módulo de Formulario de Asientos Contables v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ HTMX: Usa HTMX para cargar offcanvas dinámicamente
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.60: Sistema de Cuadratura en Tiempo Real
 * - Carga cuentas contables automáticamente
 * - Calcula totales debe/haber en tiempo real
 * - Valida cuadratura (debe == haber) antes de permitir guardar
 * - Gestión dinámica de movimientos (agregar/eliminar)
 * 
 * Dependencias globales requeridas:
 * - w.contabilidadAPI (definido en contabilidad.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - HTMX (cargado globalmente)
 * - Bootstrap (cargado globalmente)
 */
(function (w, d) {
  'use strict';

  const MOD = '[asientos.form]';
  const OFFCANVAS_ID = 'offcanvas-asiento-crear';
  const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-asientos';
  const API_BASE = '/api/v1/contabilidad/';
  const CUENTAS_API = `${API_BASE}cuentas-contables/`;
  const ASIENTOS_API = `${API_BASE}asientos-contables/`;
  const MOVIMIENTOS_API = `${API_BASE}movimientos-contables/`;

  // Estado del módulo
  let state = {
    cuentas: [], // Cache de cuentas contables
    movimientos: [], // Array de movimientos en memoria
    movimientoCounter: 0 // Contador para índices únicos
  };

  // Singleton: Instancia del Offcanvas
  let offcanvasInstance = null;

  // ⚠️ CRÍTICO v2.60: Exponer AppAsientos INMEDIATAMENTE (antes de definir funciones)
  if (!w.AppAsientos) {
    w.AppAsientos = {};
    console.log(`${MOD} AppAsientos expuesto inmediatamente (se actualizará con funciones reales)`);
  }

  /**
   * Helper: Obtener CSRF token
   */
  function getCSRFToken() {
    const name = 'csrftoken';
    const value = `; ${d.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
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
   * Cargar cuentas contables desde la API
   */
  async function cargarCuentasContables() {
    if (state.cuentas.length > 0) {
      return state.cuentas; // Usar cache
    }

    try {
      const response = await fetch(`${CUENTAS_API}?page_size=1000`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      state.cuentas = data.results || [];
      console.log(`${MOD} ${state.cuentas.length} cuentas contables cargadas`);
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
   * Poblar select de cuentas contables
   */
  async function poblarSelectCuentas(selectElement) {
    if (!selectElement) return;

    // Mostrar estado de carga
    selectElement.innerHTML = '<option value="">Cargando cuentas...</option>';
    selectElement.disabled = true;

    const cuentas = await cargarCuentasContables();
    
    // Limpiar y agregar opción por defecto
    selectElement.innerHTML = '<option value="">Seleccione cuenta...</option>';
    
    // Agregar cada cuenta al select
    cuentas.forEach(cuenta => {
      if (cuenta.activa) { // Solo mostrar cuentas activas
        const option = d.createElement('option');
        option.value = cuenta.id;
        option.textContent = `${cuenta.codigo} - ${cuenta.nombre}`;
        selectElement.appendChild(option);
      }
    });
    
    selectElement.disabled = false;
    console.log(`${MOD} Select de cuentas poblado con ${cuentas.filter(c => c.activa).length} cuentas activas`);
  }

  /**
   * Calcular totales de movimientos
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
   * ⚠️ v2.61: Actualiza estado de movimientos desde el DOM antes de calcular
   */
  function actualizarTotales() {
    // ⚠️ v2.61: Actualizar estado de movimientos desde el DOM
    const tbodyMovimientos = d.getElementById('tbody-movimientos');
    if (tbodyMovimientos) {
      const rows = tbodyMovimientos.querySelectorAll('tr[data-movimiento-index]');
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
    // ⚠️ v2.61: Tolerancia de 0.01 para errores de redondeo (igual que el backend)
    // Usar <= en lugar de < para ser más permisivo con diferencias exactas de 0.01
    const cuadra = diferencia <= 0.01; // Tolerancia para errores de punto flotante

    // Actualizar displays en tabla
    const totalDebeDisplay = d.getElementById('total-debe-display');
    const totalHaberDisplay = d.getElementById('total-haber-display');
    const cuadraturaRow = d.getElementById('row-cuadratura');
    const cuadraturaStatus = d.getElementById('cuadratura-status');
    const cuadraturaDiferencia = d.getElementById('cuadratura-diferencia');

    if (totalDebeDisplay) totalDebeDisplay.textContent = fmtMoney(debe);
    if (totalHaberDisplay) totalHaberDisplay.textContent = fmtMoney(haber);

    // Actualizar resumen
    const resumenTotalDebe = d.getElementById('resumen-total-debe');
    const resumenTotalHaber = d.getElementById('resumen-total-haber');
    const resumenDiferencia = d.getElementById('resumen-diferencia');
    const resumenStatus = d.getElementById('resumen-status');

    if (resumenTotalDebe) resumenTotalDebe.textContent = fmtMoney(debe);
    if (resumenTotalHaber) resumenTotalHaber.textContent = fmtMoney(haber);
    if (resumenDiferencia) resumenDiferencia.textContent = fmtMoney(diferencia);

    // Mostrar/ocultar fila de cuadratura
    if (cuadraturaRow) {
      if (state.movimientos.length > 0) {
        cuadraturaRow.classList.remove('d-none');
      } else {
        cuadraturaRow.classList.add('d-none');
      }
    }

    // Actualizar estado de cuadratura
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

    // Actualizar badge de estado
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

    // ⚠️ v2.61: Validar que todos los movimientos tengan cuenta seleccionada
    let todosTienenCuenta = true;
    if (tbodyMovimientos) {
      const rows = tbodyMovimientos.querySelectorAll('tr[data-movimiento-index]');
      rows.forEach(row => {
        const selectCuenta = row.querySelector('.select-cuenta');
        if (!selectCuenta || !selectCuenta.value) {
          todosTienenCuenta = false;
        }
      });
    }

    // Habilitar/deshabilitar botón de guardar (buscar ambos IDs posibles: crear/editar)
    const btnGuardar = d.getElementById('btn-guardar-asiento-crear') || d.getElementById('btn-guardar-asiento-editar');
    if (btnGuardar) {
      // El botón se habilita solo si: cuadra, hay movimientos, y todos tienen cuenta
      const puedeGuardar = cuadra && state.movimientos.length > 0 && todosTienenCuenta;
      if (puedeGuardar) {
        btnGuardar.disabled = false;
        console.log(`${MOD} Botón guardar habilitado (cuadra: ${cuadra}, movimientos: ${state.movimientos.length}, todosTienenCuenta: ${todosTienenCuenta})`);
      } else {
        btnGuardar.disabled = true;
        if (!cuadra) {
          console.log(`${MOD} Botón guardar deshabilitado: asiento no cuadra (diferencia: ${fmtMoney(diferencia)})`);
        } else if (state.movimientos.length === 0) {
          console.log(`${MOD} Botón guardar deshabilitado: no hay movimientos`);
        } else if (!todosTienenCuenta) {
          console.log(`${MOD} Botón guardar deshabilitado: algunos movimientos no tienen cuenta seleccionada`);
        }
      }
    } else {
      console.warn(`${MOD} Botón guardar no encontrado (ni btn-guardar-asiento-crear ni btn-guardar-asiento-editar)`);
    }

    return { debe, haber, diferencia, cuadra };
  }

  /**
   * Agregar movimiento a la tabla
   */
  async function agregarMovimiento() {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) {
      console.warn(`${MOD} tbody-movimientos no encontrado`);
      return;
    }

    const template = d.getElementById('template-movimiento-row');
    if (!template) {
      console.warn(`${MOD} template-movimiento-row no encontrado`);
      return;
    }

    // Clonar template
    const newRow = template.content.cloneNode(true);
    const tr = newRow.querySelector('tr');
    const index = state.movimientoCounter++;
    tr.setAttribute('data-movimiento-index', index);

    // Actualizar orden
    const ordenSpan = tr.querySelector('.movimiento-orden');
    if (ordenSpan) {
      ordenSpan.textContent = state.movimientos.length + 1;
    }

    // Configurar nombres de campos
    tr.querySelectorAll('input, select').forEach(input => {
      const name = input.getAttribute('name');
      if (name) {
        input.setAttribute('name', name.replace('[]', `[${index}]`));
      }
    });

    // Poblar select de cuentas
    const selectCuenta = tr.querySelector('.select-cuenta');
    if (selectCuenta) {
      await poblarSelectCuentas(selectCuenta);
      // ⚠️ v2.61: Event listener para validar cuando se selecciona una cuenta
      selectCuenta.addEventListener('change', () => {
        actualizarTotales();
      });
    }

    // Agregar event listeners para cálculo en tiempo real
    const debeInput = tr.querySelector('.input-debe');
    const haberInput = tr.querySelector('.input-haber');

    if (debeInput) {
      debeInput.addEventListener('input', () => {
        // Si se ingresa debe, limpiar haber
        if (parseFloat(debeInput.value) > 0) {
          haberInput.value = '0.00';
        }
        actualizarTotales();
      });
    }

    if (haberInput) {
      haberInput.addEventListener('input', () => {
        // Si se ingresa haber, limpiar debe
        if (parseFloat(haberInput.value) > 0) {
          debeInput.value = '0.00';
        }
        actualizarTotales();
      });
    }

    // Botón eliminar
    const btnEliminar = tr.querySelector('.btn-eliminar-movimiento');
    if (btnEliminar) {
      btnEliminar.addEventListener('click', () => {
        eliminarMovimiento(index);
      });
    }

    // Agregar a DOM
    tbody.appendChild(newRow);

    // Agregar a estado
    state.movimientos.push({
      index,
      cuenta: null,
      descripcion: '',
      debe: 0,
      haber: 0
    });

    // Actualizar totales
    actualizarTotales();

    console.log(`${MOD} Movimiento agregado (índice: ${index})`);
  }

  /**
   * Eliminar movimiento de la tabla
   */
  function eliminarMovimiento(index) {
    const tbody = d.getElementById('tbody-movimientos');
    if (!tbody) return;

    const row = tbody.querySelector(`tr[data-movimiento-index="${index}"]`);
    if (row) {
      row.remove();
    }

    // Remover de estado
    state.movimientos = state.movimientos.filter(m => m.index !== index);

    // Reordenar movimientos restantes
    const rows = tbody.querySelectorAll('tr[data-movimiento-index]');
    rows.forEach((row, idx) => {
      const ordenSpan = row.querySelector('.movimiento-orden');
      if (ordenSpan) {
        ordenSpan.textContent = idx + 1;
      }
    });

    // Actualizar totales
    actualizarTotales();

    console.log(`${MOD} Movimiento eliminado (índice: ${index})`);
  }

  /**
   * Recolectar datos del formulario
   * ⚠️ v2.61: Soporta IDs dinámicos (crear/editar)
   */
  function recolectarDatos() {
    const form = d.getElementById('form-asiento-crear') || d.getElementById('form-asiento-editar');
    if (!form) {
      console.warn(`${MOD} Formulario no encontrado para recolectar datos`);
      return null;
    }

    const formData = new FormData(form);
    const data = {
      numero: formData.get('numero') || null,
      fecha: formData.get('fecha'),
      descripcion: formData.get('descripcion'),
      estado: formData.get('estado') || 'BORRADOR',
      // ⚠️ NORMATIVA: Campos de comprobante para trazabilidad
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
          // ⚠️ NORMATIVA: Incluir campos de terceros si están disponibles en el formulario
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
          
          // Agregar campos de terceros si existen en el formulario
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

    return { ...data, movimientos };
  }

  /**
   * Guardar asiento
   */
  async function guardar() {
    const form = d.getElementById('form-asiento-crear');
    if (!form) {
      console.warn(`${MOD} Formulario #form-asiento-crear no encontrado`);
      return;
    }

    // ⚠️ v2.61: Limpiar errores previos antes de intentar guardar
    const offcanvasCrear = d.getElementById('offcanvas-asiento-crear');
    const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
    const offcanvasActivo = offcanvasCrear || offcanvasEditar;
    
    if (offcanvasActivo) {
      const errorContainer = offcanvasActivo.querySelector('#error-container');
      if (errorContainer) {
        errorContainer.classList.add('d-none');
        const errorMessage = errorContainer.querySelector('#error-message');
        if (errorMessage) {
          errorMessage.textContent = '';
        }
        const missingFieldsList = errorContainer.querySelector('#missing-fields-list');
        if (missingFieldsList) {
          missingFieldsList.classList.add('d-none');
        }
        const fieldsUl = errorContainer.querySelector('#fields-ul');
        if (fieldsUl) {
          fieldsUl.innerHTML = '';
        }
      }
      
      // También limpiar el contenedor de feedback
      const feedbackContainer = offcanvasActivo.querySelector('#feedback-asiento-create, #feedback-asiento-edit');
      if (feedbackContainer) {
        feedbackContainer.classList.add('d-none');
        feedbackContainer.textContent = '';
      }
    }
    
    // También limpiar usando ErrorHandler si está disponible
    if (w.ErrorHandler && typeof w.ErrorHandler.reset === 'function') {
      w.ErrorHandler.reset();
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

    // Validar que haya movimientos
    if (!datos.movimientos || datos.movimientos.length === 0) {
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error('Debe agregar al menos un movimiento contable');
      } else {
        alert('Debe agregar al menos un movimiento contable');
      }
      return;
    }

    // ⚠️ v2.61: Validar cuadratura usando la misma lógica que actualizarTotales()
    // Usar actualizarTotales() para obtener el estado actualizado de cuadratura
    // Esto asegura que la validación sea idéntica a la que habilita/deshabilita el botón
    const { debe, haber, diferencia, cuadra } = actualizarTotales();
    
    // ⚠️ v2.61: Log de depuración para validar cuadratura
    console.log(`${MOD} 🔍 Validación de cuadratura antes de guardar:`, {
      debe: debe,
      haber: haber,
      diferencia: diferencia,
      cuadra: cuadra,
      movimientos: datos.movimientos.length
    });
    
    if (!cuadra) {
      console.warn(`${MOD} ⚠️ Asiento no cuadrado - bloqueando guardado (diferencia: ${diferencia})`);
      // Mostrar error visualmente en el offcanvas
      const offcanvasCrear = d.getElementById('offcanvas-asiento-crear');
      const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
      const offcanvasActivo = offcanvasCrear || offcanvasEditar;
      
      if (offcanvasActivo) {
        let errorContainer = offcanvasActivo.querySelector('#error-container');
        let errorMessage = offcanvasActivo.querySelector('#error-message');
        
        // Crear contenedor si no existe
        if (!errorContainer && offcanvasActivo) {
          const offcanvasBody = offcanvasActivo.querySelector('.offcanvas-body');
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
            errorContainer = offcanvasActivo.querySelector('#error-container');
            errorMessage = offcanvasActivo.querySelector('#error-message');
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
      
      // También mostrar feedback si está disponible
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error(`El asiento no está cuadrado. Diferencia: ${fmtMoney(diferencia)}`);
      }
      
      // Restaurar botón
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = btnOriginalText;
      }
      return;
    }
    
    // ⚠️ v2.61: Log de éxito - cuadratura validada correctamente
    console.log(`${MOD} ✅ Cuadratura validada correctamente - procediendo con guardado (diferencia: ${diferencia})`);

    // ⚠️ v2.61: Buscar botón guardar con IDs dinámicos
    const btnGuardar = d.getElementById('btn-guardar-asiento-crear') || d.getElementById('btn-guardar-asiento-editar');
    const btnOriginalText = btnGuardar ? btnGuardar.innerHTML : '';
    
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    }

    try {
      // ⚠️ v2.61: Crear asiento con movimientos en una sola petición (el servicio lo espera así)
      const payload = {
        // ⚠️ v2.61: Si numero está vacío o es null, no enviarlo (el backend lo generará automáticamente)
        // Solo enviar numero si tiene un valor válido (no vacío, no null, no undefined)
        ...(datos.numero && datos.numero.trim() ? { numero: datos.numero.trim() } : {}),
        fecha: datos.fecha,
        descripcion: datos.descripcion,
        estado: datos.estado,
        // ⚠️ NORMATIVA: Campos de comprobante para trazabilidad
        tipo_comprobante: datos.tipo_comprobante || null,
        numero_comprobante: datos.numero_comprobante || null,
        // ⚠️ v2.61: Incluir movimientos en el payload
        movimientos: datos.movimientos.map(mov => ({
          cuenta: mov.cuenta,
          descripcion: mov.descripcion || '',
          debe: parseFloat(mov.debe) || 0,
          haber: parseFloat(mov.haber) || 0,
          orden: mov.orden,
          // ⚠️ NORMATIVA: Campos de terceros (opcionales, se pueden poblar automáticamente desde el backend)
          tipo_tercero: mov.tipo_tercero || null,
          tercero_nit: mov.tercero_nit || null,
          tercero_razon_social: mov.tercero_razon_social || null
        }))
      };

      const responseAsiento = await fetch(ASIENTOS_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });

      if (!responseAsiento.ok) {
        // ⚠️ v2.61: Manejo mejorado de errores con error_injector.js
        const errorData = await responseAsiento.json().catch(() => ({ detail: 'Error al crear asiento' }));
        
        // ⚠️ v2.61: Función helper para mostrar errores visualmente
        const mostrarErrorVisual = (errorInfo) => {
          // Buscar el offcanvas activo (crear o editar)
          const offcanvasCrear = d.getElementById('offcanvas-asiento-crear');
          const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
          const offcanvasActivo = offcanvasCrear || offcanvasEditar;
          
          let errorContainer = null;
          let errorMessage = null;
          let missingFieldsList = null;
          let fieldsUl = null;
          
          // 1. Buscar contenedor de errores dentro del offcanvas activo
          if (offcanvasActivo) {
            errorContainer = offcanvasActivo.querySelector('#error-container');
            errorMessage = offcanvasActivo.querySelector('#error-message');
            missingFieldsList = offcanvasActivo.querySelector('#missing-fields-list');
            if (errorContainer) {
              fieldsUl = errorContainer.querySelector('#fields-ul');
            }
          }
          
          // 2. Si no se encuentra, buscar en el contenedor HTMX
          if (!errorContainer) {
            const offcanvasContainer = d.getElementById('offcanvas-container-asientos');
            if (offcanvasContainer) {
              errorContainer = offcanvasContainer.querySelector('#error-container');
              errorMessage = offcanvasContainer.querySelector('#error-message');
              missingFieldsList = offcanvasContainer.querySelector('#missing-fields-list');
              if (errorContainer) {
                fieldsUl = errorContainer.querySelector('#fields-ul');
              }
            }
          }
          
          // 3. Si aún no se encuentra, buscar en el DOM principal
          if (!errorContainer) {
            errorContainer = d.getElementById('error-container');
            errorMessage = d.getElementById('error-message');
            missingFieldsList = d.getElementById('missing-fields-list');
            if (errorContainer) {
              fieldsUl = errorContainer.querySelector('#fields-ul');
            }
          }
          
          // 4. Si no existe, crear el contenedor dinámicamente en el offcanvas
          if (!errorContainer && offcanvasActivo) {
            const offcanvasBody = offcanvasActivo.querySelector('.offcanvas-body');
            if (offcanvasBody) {
              const errorHtml = `
                <div id="error-container" class="mt-3">
                  <div class="alert alert-danger d-flex align-items-start" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                    <div class="flex-grow-1">
                      <div id="error-message" class="mb-0"></div>
                      <div id="missing-fields-list" class="mt-2 d-none">
                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Campos Requeridos Faltantes:</small>
                        <ul class="list-group list-group-flush small mb-0" id="fields-ul"></ul>
                      </div>
                    </div>
                  </div>
                </div>
              `;
              // Insertar al inicio del offcanvas-body (después del header)
              offcanvasBody.insertAdjacentHTML('afterbegin', errorHtml);
              errorContainer = offcanvasActivo.querySelector('#error-container');
              errorMessage = offcanvasActivo.querySelector('#error-message');
              missingFieldsList = offcanvasActivo.querySelector('#missing-fields-list');
              fieldsUl = errorContainer ? errorContainer.querySelector('#fields-ul') : null;
            }
          }
          
          // Mostrar el error si se encontró o creó el contenedor
          if (errorContainer && errorMessage) {
            // Construir mensaje de error
            let msg = errorInfo.message || errorInfo.detail || 'Error al procesar la solicitud.';
            
            // Si hay detalles adicionales, agregarlos
            if (errorInfo.detalles) {
              const detalles = errorInfo.detalles;
              if (detalles.diferencia) {
                msg += `<br><small class="text-muted">Diferencia: ${fmtMoney(parseFloat(detalles.diferencia))}</small>`;
              }
              if (detalles.sugerencia) {
                msg += `<br><small class="text-info">💡 ${detalles.sugerencia}</small>`;
              }
            }
            
            errorMessage.innerHTML = msg;
            errorContainer.classList.remove('d-none');
            
            // Mostrar campos faltantes si existen
            if (errorInfo.missing_fields && Array.isArray(errorInfo.missing_fields) && errorInfo.missing_fields.length > 0) {
              if (fieldsUl && missingFieldsList) {
                fieldsUl.innerHTML = errorInfo.missing_fields.map(field => 
                  `<li class="list-group-item"><strong>${field}</strong></li>`
                ).join('');
                missingFieldsList.classList.remove('d-none');
              }
            }
            
            // Scroll al contenedor de errores
            setTimeout(() => {
              errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
            
            console.log(`${MOD} ✅ Error mostrado visualmente en offcanvas`);
            return true;
          }
          
          return false;
        };
        
        // Si es 422, usar error_injector.js primero, luego fallback visual
        if (responseAsiento.status === 422) {
          // ⚠️ v2.61: Crear un objeto XHR simulado completo para error_injector.js
          const mockXHR = {
            status: 422,
            statusText: 'Unprocessable Entity',
            response: JSON.stringify(errorData),
            responseText: JSON.stringify(errorData),
            getResponseHeader: function() { return 'application/json'; }
          };
          
          // Intentar usar error_injector.js primero
          let errorMostrado = false;
          if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
            console.log(`${MOD} Intentando mostrar error con ErrorHandler:`, errorData);
            try {
              w.ErrorHandler.show(mockXHR);
              // Dar tiempo para que error_injector.js procese
              setTimeout(() => {
                const errorContainer = d.getElementById('error-container');
                if (errorContainer && !errorContainer.classList.contains('d-none')) {
                  errorMostrado = true;
                  console.log(`${MOD} ✅ Error mostrado por ErrorHandler`);
                } else {
                  // Si error_injector no lo mostró, usar fallback
                  console.log(`${MOD} ⚠️ ErrorHandler no mostró el error, usando fallback visual`);
                  mostrarErrorVisual(errorData);
                }
              }, 200);
            } catch (err) {
              console.error(`${MOD} Error al llamar ErrorHandler.show:`, err);
              // Continuar con fallback
              mostrarErrorVisual(errorData);
            }
          } else {
            // ErrorHandler no disponible, usar fallback directo
            console.log(`${MOD} ErrorHandler no disponible, usando fallback visual`);
            mostrarErrorVisual(errorData);
          }
          
          // También mostrar en consola para debugging
          console.error(`${MOD} ❌ Error 422 al crear asiento:`, errorData);
          
          // Restaurar botón
          if (btnGuardar) {
            btnGuardar.disabled = false;
            btnGuardar.innerHTML = btnOriginalText;
          }
          return; // No continuar
        }
        
        // Para otros errores (500, 400, etc.), también mostrarlos visualmente
        console.error(`${MOD} ❌ Error ${responseAsiento.status} al crear asiento:`, errorData);
        const errorMostrado = mostrarErrorVisual(errorData);
        
        if (!errorMostrado) {
          // Último recurso: usar feedback o alert
          if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
            w.SintelFeedback.error(errorData.message || errorData.detail || `Error ${responseAsiento.status}: No se pudo crear el asiento.`);
          } else {
            alert(errorData.message || errorData.detail || `Error ${responseAsiento.status}: No se pudo crear el asiento.`);
          }
        }
        
        // Restaurar botón
        if (btnGuardar) {
          btnGuardar.disabled = false;
          btnGuardar.innerHTML = btnOriginalText;
        }
        return; // No continuar
      }

      const asientoData = await responseAsiento.json();

      // ⚠️ v2.61: Éxito - Asiento creado con todos sus movimientos
      if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
        w.SintelFeedback.success('Asiento contable creado correctamente');
      }

      // Cerrar offcanvas
      if (offcanvasInstance) {
        offcanvasInstance.hide();
      }

      // Refrescar tabla Tabulator (si existe)
      if (w.AppAsientos && typeof w.AppAsientos.refreshGrid === 'function') {
        w.AppAsientos.refreshGrid();
      }

      // Limpiar formulario
      limpiarFormulario();

    } catch (error) {
      console.error(`${MOD} ❌ Error inesperado al guardar asiento:`, error);
      
      // ⚠️ v2.61: Mostrar error visualmente en el offcanvas
      const offcanvasCrear = d.getElementById('offcanvas-asiento-crear');
      const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
      const offcanvasActivo = offcanvasCrear || offcanvasEditar;
      
      let errorContainer = null;
      let errorMessage = null;
      
      if (offcanvasActivo) {
        errorContainer = offcanvasActivo.querySelector('#error-container');
        errorMessage = offcanvasActivo.querySelector('#error-message');
        
        // Si no existe, crearlo dinámicamente
        if (!errorContainer && offcanvasActivo) {
          const offcanvasBody = offcanvasActivo.querySelector('.offcanvas-body');
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
            errorContainer = offcanvasActivo.querySelector('#error-container');
            errorMessage = offcanvasActivo.querySelector('#error-message');
          }
        }
        
        if (errorContainer && errorMessage) {
          errorMessage.textContent = `Error inesperado: ${error.message || 'Error desconocido al guardar el asiento.'}`;
          errorContainer.classList.remove('d-none');
          setTimeout(() => {
            errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }, 100);
          console.log(`${MOD} ✅ Error mostrado visualmente en offcanvas`);
        }
      }
      
      // También usar UIManager si está disponible (para otros contenedores)
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
      } else if (!errorContainer) {
        // Último recurso: alert solo si no se pudo mostrar visualmente
        alert(`Error al guardar asiento: ${error.message}`);
      }
    } finally {
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = btnOriginalText;
      }
    }
  }

  /**
   * Limpiar formulario
   */
  function limpiarFormulario() {
    const form = d.getElementById('form-asiento-crear');
    if (form) {
      form.reset();
    }

    const tbody = d.getElementById('tbody-movimientos');
    if (tbody) {
      tbody.innerHTML = '';
    }

    state.movimientos = [];
    state.movimientoCounter = 0;

    // ⚠️ v2.61: Limpiar también los errores visuales
    const offcanvasCrear = d.getElementById('offcanvas-asiento-crear');
    const offcanvasEditar = d.getElementById('offcanvas-asiento-editar');
    const offcanvasActivo = offcanvasCrear || offcanvasEditar;
    
    if (offcanvasActivo) {
      const errorContainer = offcanvasActivo.querySelector('#error-container');
      if (errorContainer) {
        errorContainer.classList.add('d-none');
        const errorMessage = errorContainer.querySelector('#error-message');
        if (errorMessage) {
          errorMessage.textContent = '';
        }
        const missingFieldsList = errorContainer.querySelector('#missing-fields-list');
        if (missingFieldsList) {
          missingFieldsList.classList.add('d-none');
        }
        const fieldsUl = errorContainer.querySelector('#fields-ul');
        if (fieldsUl) {
          fieldsUl.innerHTML = '';
        }
      }
      
      // También limpiar el contenedor de feedback
      const feedbackContainer = offcanvasActivo.querySelector('#feedback-asiento-create, #feedback-asiento-edit');
      if (feedbackContainer) {
        feedbackContainer.classList.add('d-none');
        feedbackContainer.textContent = '';
      }
    }
    
    // Limpiar usando ErrorHandler si está disponible
    if (w.ErrorHandler && typeof w.ErrorHandler.reset === 'function') {
      w.ErrorHandler.reset();
    }

    actualizarTotales();

    // Establecer fecha por defecto
    const fechaInput = d.getElementById('input-fecha');
    if (fechaInput && !fechaInput.value) {
      const hoy = new Date().toISOString().split('T')[0];
      fechaInput.value = hoy;
    }
  }

  /**
   * Configurar eventos del formulario
   * ⚠️ v2.61: Soporta IDs dinámicos (crear/editar)
   */
  function configurarEventosFormulario() {
    // Buscar formulario (puede ser crear o editar)
    const form = d.getElementById('form-asiento-crear') || d.getElementById('form-asiento-editar');
    if (!form) {
      console.warn(`${MOD} Formulario no encontrado (ni form-asiento-crear ni form-asiento-editar)`);
      return;
    }

    console.log(`${MOD} Configurando eventos del formulario:`, form.id);

    // Botón agregar movimiento
    const btnAgregar = d.getElementById('btn-agregar-movimiento');
    if (btnAgregar) {
      // Remover listener anterior si existe para evitar duplicados
      btnAgregar.removeEventListener('click', agregarMovimiento);
      btnAgregar.addEventListener('click', agregarMovimiento);
      console.log(`${MOD} Event listener agregado para btn-agregar-movimiento`);
    } else {
      console.warn(`${MOD} Botón agregar movimiento no encontrado`);
    }

    // Botón guardar (buscar ambos IDs posibles)
    const btnGuardar = d.getElementById('btn-guardar-asiento-crear') || d.getElementById('btn-guardar-asiento-editar');
    if (btnGuardar) {
      // Remover listener anterior si existe para evitar duplicados
      btnGuardar.removeEventListener('click', guardar);
      btnGuardar.addEventListener('click', guardar);
      console.log(`${MOD} Event listener agregado para botón guardar:`, btnGuardar.id);
    } else {
      console.warn(`${MOD} Botón guardar no encontrado (ni btn-guardar-asiento-crear ni btn-guardar-asiento-editar)`);
    }

    // Establecer fecha por defecto
    const fechaInput = d.getElementById('input-fecha');
    if (fechaInput && !fechaInput.value) {
      const hoy = new Date().toISOString().split('T')[0];
      fechaInput.value = hoy;
    }

    // Cargar cuentas contables y actualizar totales
    cargarCuentasContables().then(() => {
      actualizarTotales();
      console.log(`${MOD} Cuentas contables cargadas y totales actualizados`);
    }).catch(err => {
      console.error(`${MOD} Error al cargar cuentas contables:`, err);
    });

    console.log(`${MOD} Eventos del formulario configurados correctamente`);
  }

  /**
   * Inicializar y mostrar Offcanvas
   */
  function initOffcanvas(offcanvasEl) {
    if (!offcanvasEl) return null;
    
    if (w.bootstrap && w.bootstrap.Offcanvas) {
      offcanvasInstance = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      return offcanvasInstance;
    }
    return null;
  }

  /**
   * Mostrar Offcanvas
   */
  function showOffcanvas(offcanvasEl) {
    if (!offcanvasEl) {
      console.warn(`${MOD} Intento de mostrar offcanvas pero el elemento no existe`);
      return;
    }
    
    const instance = initOffcanvas(offcanvasEl);
    if (instance) {
      instance.show();
      // Configurar eventos del formulario después de que el offcanvas esté visible
      // Usar evento de Bootstrap para asegurar que el offcanvas esté completamente visible
      offcanvasEl.addEventListener('shown.bs.offcanvas', function onShown() {
        configurarEventosFormulario();
        offcanvasEl.removeEventListener('shown.bs.offcanvas', onShown);
      }, { once: true });
    } else {
      console.error(`${MOD} No se pudo inicializar el offcanvas. Bootstrap no está disponible.`);
    }
  }

  /**
   * Cargar Offcanvas desde el servidor vía HTMX
   */
  async function cargarOffcanvas() {
    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) {
      console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
      return;
    }

    const url = `${ASIENTOS_API}render-offcanvas/crear/`;

    try {
      // ⚠️ HTMX: Cargar HTML desde el servidor
      await htmx.ajax('GET', url, {
        target: `#${OFFCANVAS_CONTAINER_ID}`,
        swap: 'innerHTML'
      });

      // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
      await new Promise(resolve => setTimeout(resolve, 50));

      // ⚠️ v2.61: Buscar offcanvas con IDs dinámicos (crear/editar)
      const offcanvasEl = d.getElementById('offcanvas-asiento-crear') || 
                          d.getElementById('offcanvas-asiento-editar');
      if (offcanvasEl) {
        showOffcanvas(offcanvasEl);
      } else {
        console.warn(`${MOD} Offcanvas cargado pero elemento no encontrado (buscando offcanvas-asiento-crear o offcanvas-asiento-editar)`);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario' } }, MOD);
      } else {
        alert('Error al cargar el formulario de asiento');
      }
    }
  }

  // ⚠️ HTMX: Escuchar evento afterSettle para inicializar cuando el offcanvas se carga
  d.body.addEventListener('htmx:afterSettle', function(evt) {
    // Verificar que el swap haya ocurrido en nuestro contenedor
    const target = evt.detail.target;
    if (!target) return;
    
    // Verificar si el target es nuestro contenedor o está dentro de él
    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) return;
    
    // Verificar que el target sea el contenedor o esté dentro de él
    if (target.id === OFFCANVAS_CONTAINER_ID || container.contains(target)) {
      // Buscar el offcanvas dentro del contenedor
      const offcanvasEl = container.querySelector(`#${OFFCANVAS_ID}`);
      if (offcanvasEl) {
        console.log(`${MOD} Offcanvas cargado por HTMX, inicializando...`);
        // Usar setTimeout para asegurar que el DOM esté completamente actualizado
        setTimeout(() => {
          showOffcanvas(offcanvasEl);
        }, 50);
      } else {
        console.warn(`${MOD} Offcanvas #${OFFCANVAS_ID} no encontrado en el contenedor después de HTMX swap`);
      }
    }
  });

  /**
   * ⚠️ v2.61: Cargar offcanvas de detalle (solo lectura)
   */
  async function cargarOffcanvasDetalleAsiento(asientoId) {
    if (!asientoId) {
      console.warn(`${MOD} ID de asiento no proporcionado`);
      return;
    }

    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) {
      console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
      return;
    }

    const url = `${ASIENTOS_API}render-offcanvas/detalle/?id=${asientoId}`;

    try {
      // ⚠️ HTMX: Cargar HTML desde el servidor
      await htmx.ajax('GET', url, {
        target: `#${OFFCANVAS_CONTAINER_ID}`,
        swap: 'innerHTML'
      });

      // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
      await new Promise(resolve => setTimeout(resolve, 50));

      // Buscar offcanvas de detalle
      const offcanvasEl = d.getElementById('offcanvas-asiento-detalle');
      if (offcanvasEl) {
        showOffcanvas(offcanvasEl);
      } else {
        console.warn(`${MOD} Offcanvas de detalle cargado pero elemento #offcanvas-asiento-detalle no encontrado`);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas de detalle:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el detalle del asiento' } }, MOD);
      } else {
        alert('Error al cargar el detalle del asiento');
      }
    }
  }

  /**
   * ⚠️ v2.61: Cargar offcanvas de edición (delega a AppAsientosEditar)
   */
  async function cargarOffcanvasEditarAsiento(asientoId) {
    // ⚠️ v2.61: Delegar a módulo específico de edición
    if (w.AppAsientosEditar && typeof w.AppAsientosEditar.cargar === 'function') {
      await w.AppAsientosEditar.cargar(asientoId);
    } else {
      console.warn(`${MOD} AppAsientosEditar.cargar no disponible, cargando módulo...`);
      // El módulo se carga automáticamente desde el template asiento_offcanvas_editar.html
      // Intentar cargar el offcanvas directamente
      const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
      if (!container) {
        console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
        return;
      }

      const url = `${ASIENTOS_API}${asientoId}/render-offcanvas/editar/`;

      try {
        await htmx.ajax('GET', url, {
          target: `#${OFFCANVAS_CONTAINER_ID}`,
          swap: 'innerHTML'
        });

        await new Promise(resolve => setTimeout(resolve, 200));

        const offcanvasEl = d.getElementById('offcanvas-asiento-editar');
        if (offcanvasEl && w.AppAsientosEditar && typeof w.AppAsientosEditar.cargar === 'function') {
          // El módulo ya debería estar cargado desde el template
          await w.AppAsientosEditar.cargar(asientoId);
        }
      } catch (error) {
        console.error(`${MOD} Error al cargar Offcanvas de edición:`, error);
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario de edición' } }, MOD);
        }
      }
    }
  }

  // Exponer funciones públicas
  w.AppAsientos.crear = cargarOffcanvas;
  w.AppAsientos.agregarMovimiento = agregarMovimiento;
  w.AppAsientos.eliminarMovimiento = eliminarMovimiento;
  w.AppAsientos.calcularTotales = actualizarTotales;
  w.AppAsientos.guardar = guardar;
  w.AppAsientos.cargarOffcanvasDetalleAsiento = cargarOffcanvasDetalleAsiento;
  w.AppAsientos.cargarOffcanvasEditarAsiento = cargarOffcanvasEditarAsiento;
  w.AppAsientos.refreshGrid = function() {
    // Función para refrescar la tabla (se implementará en asientos_main.js si es necesario)
    if (w.AppAsientos && typeof w.AppAsientos.refreshTable === 'function') {
      w.AppAsientos.refreshTable();
    }
  };

  console.log(`${MOD} Módulo inicializado`);

})(window, document);
