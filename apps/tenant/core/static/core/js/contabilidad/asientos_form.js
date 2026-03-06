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
   */
  function actualizarTotales() {
    const { debe, haber } = calcularTotales();
    const diferencia = Math.abs(debe - haber);
    const cuadra = diferencia < 0.01; // Tolerancia para errores de punto flotante

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

    // Habilitar/deshabilitar botón de guardar
    const btnGuardar = d.getElementById('btn-guardar-asiento');
    if (btnGuardar) {
      if (cuadra && state.movimientos.length > 0) {
        btnGuardar.disabled = false;
      } else {
        btnGuardar.disabled = true;
      }
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
   */
  function recolectarDatos() {
    const form = d.getElementById('form-asiento-crear');
    if (!form) return null;

    const formData = new FormData(form);
    const data = {
      numero: formData.get('numero') || null,
      fecha: formData.get('fecha'),
      descripcion: formData.get('descripcion'),
      estado: formData.get('estado') || 'BORRADOR'
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
          movimientos.push({
            cuenta: parseInt(cuentaId),
            descripcion: descripcion,
            debe: debe,
            haber: haber,
            orden: idx + 1
          });
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

    // Validar cuadratura
    const { debe, haber, cuadra } = calcularTotales();
    if (!cuadra) {
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error(`El asiento no está cuadrado. Diferencia: ${fmtMoney(Math.abs(debe - haber))}`);
      } else {
        alert(`El asiento no está cuadrado. Diferencia: ${fmtMoney(Math.abs(debe - haber))}`);
      }
      return;
    }

    const btnGuardar = d.getElementById('btn-guardar-asiento');
    const btnOriginalText = btnGuardar ? btnGuardar.innerHTML : '';
    
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    }

    try {
      // Crear asiento primero
      const responseAsiento = await fetch(ASIENTOS_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          numero: datos.numero,
          fecha: datos.fecha,
          descripcion: datos.descripcion,
          estado: datos.estado
        })
      });

      if (!responseAsiento.ok) {
        // ⚠️ v2.60: Si es error 422, usar error_injector.js para mostrarlo
        const errorData = await responseAsiento.json().catch(() => ({ detail: 'Error al crear asiento' }));
        
        // Si es 422, simular el evento HTMX para que error_injector.js lo maneje
        if (responseAsiento.status === 422) {
          // Crear un objeto XHR simulado para error_injector.js
          const mockXHR = {
            status: 422,
            statusText: 'Unprocessable Entity',
            response: JSON.stringify(errorData),
            responseText: JSON.stringify(errorData)
          };
          
          // Llamar directamente a error_injector.js si está disponible
          if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
            w.ErrorHandler.show(mockXHR);
          } else {
            // Fallback: mostrar error manualmente
            console.error(`${MOD} Error 422:`, errorData);
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
              w.SintelFeedback.error(errorData.message || 'Error de validación. Revise los campos marcados.');
            }
          }
          return; // No continuar con la creación de movimientos
        }
        
        // Para otros errores, lanzar excepción
        throw new Error(errorData.detail || errorData.message || `HTTP ${responseAsiento.status}`);
      }

      const asientoData = await responseAsiento.json();
      const asientoId = asientoData.id;

      // Crear movimientos
      for (const movimiento of datos.movimientos) {
        const responseMovimiento = await fetch(MOVIMIENTOS_API, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            asiento: asientoId,
            cuenta: movimiento.cuenta,
            descripcion: movimiento.descripcion,
            debe: movimiento.debe,
            haber: movimiento.haber,
            orden: movimiento.orden
          })
        });

        if (!responseMovimiento.ok) {
          // ⚠️ v2.60: Si es error 422, usar error_injector.js para mostrarlo
          const errorData = await responseMovimiento.json().catch(() => ({ detail: 'Error al crear movimiento' }));
          
          // Si es 422, simular el evento HTMX para que error_injector.js lo maneje
          if (responseMovimiento.status === 422) {
            const mockXHR = {
              status: 422,
              statusText: 'Unprocessable Entity',
              response: JSON.stringify(errorData),
              responseText: JSON.stringify(errorData)
            };
            
            if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
              w.ErrorHandler.show(mockXHR);
            } else {
              console.error(`${MOD} Error 422 al crear movimiento:`, errorData);
              if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error(errorData.message || 'Error de validación al crear movimiento.');
              }
            }
            return; // No continuar con más movimientos
          }
          
          // Para otros errores, lanzar excepción
          throw new Error(errorData.detail || errorData.message || `HTTP ${responseMovimiento.status}`);
        }
      }

      // Éxito
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
      console.error(`${MOD} Error al guardar asiento:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
      } else {
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
   */
  function configurarEventosFormulario() {
    const form = d.getElementById('form-asiento-crear');
    if (!form) {
      console.warn(`${MOD} Formulario #form-asiento-crear no encontrado`);
      return;
    }

    // Botón agregar movimiento
    const btnAgregar = d.getElementById('btn-agregar-movimiento');
    if (btnAgregar) {
      btnAgregar.addEventListener('click', agregarMovimiento);
    }

    // Botón guardar
    const btnGuardar = d.getElementById('btn-guardar-asiento');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', guardar);
    }

    // Establecer fecha por defecto
    const fechaInput = d.getElementById('input-fecha');
    if (fechaInput && !fechaInput.value) {
      const hoy = new Date().toISOString().split('T')[0];
      fechaInput.value = hoy;
    }

    console.log(`${MOD} Eventos del formulario configurados`);
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

      // Inicializar y mostrar el Offcanvas
      const offcanvasEl = d.getElementById(OFFCANVAS_ID);
      if (offcanvasEl) {
        showOffcanvas(offcanvasEl);
      } else {
        console.warn(`${MOD} Offcanvas cargado pero elemento #${OFFCANVAS_ID} no encontrado`);
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

  // Exponer funciones públicas
  w.AppAsientos.crear = cargarOffcanvas;
  w.AppAsientos.agregarMovimiento = agregarMovimiento;
  w.AppAsientos.eliminarMovimiento = eliminarMovimiento;
  w.AppAsientos.calcularTotales = actualizarTotales;
  w.AppAsientos.guardar = guardar;

  console.log(`${MOD} Módulo inicializado`);

})(window, document);
