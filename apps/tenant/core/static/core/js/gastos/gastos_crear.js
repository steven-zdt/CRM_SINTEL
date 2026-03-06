/**
 * gastos_crear.js - Módulo de Creación de Gastos v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ HTMX: Usa HTMX para cargar offcanvas dinámicamente
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.40: Sistema de Documento Soporte Inmutable con Resolución DIAN Automática
 * - Carga resolución vigente automáticamente
 * - Calcula retenciones en tiempo real
 * - Valida formulario antes de enviar
 * 
 * Dependencias globales requeridas:
 * - w.gastosAPI (definido en gastos.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - HTMX (cargado globalmente)
 * - Bootstrap (cargado globalmente)
 */
(function (w, d) {
  'use strict';

  const MOD = '[gastos.crear]';
  const OFFCANVAS_ID = 'offcanvas-gasto-crear';
  const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-gastos';
  const GESTOR_OFFCANVAS_URL = '/api/v1/gastos/gestor-offcanvas/';

  // Singleton: Instancia del Offcanvas
  let offcanvasInstance = null;

  // ⚠️ CRÍTICO v2.60: Exponer AppGastos INMEDIATAMENTE (antes de definir funciones)
  if (!w.AppGastos) {
    w.AppGastos = {};
    console.log(`${MOD} AppGastos expuesto inmediatamente (se actualizará con funciones reales)`);
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
    const instance = initOffcanvas(offcanvasEl);
    if (instance) {
      instance.show();
    }
  }

  /**
   * Ocultar Offcanvas
   */
  function hideOffcanvas() {
    if (offcanvasInstance) {
      offcanvasInstance.hide();
    }
  }

  /**
   * Cargar Offcanvas desde el servidor vía HTMX
   */
  async function cargarOffcanvas() {
    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) {
      console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error('Error: Contenedor de Offcanvas no encontrado');
      }
      return;
    }

    // Construir URL para modo creación
    const url = `${GESTOR_OFFCANVAS_URL}?simple=true`;

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
        // Configurar eventos del formulario después de que el offcanvas esté visible
        setTimeout(() => {
          configurarEventosFormulario();
        }, 100);
      } else {
        console.warn(`${MOD} Offcanvas cargado pero elemento #${OFFCANVAS_ID} no encontrado`);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario' } }, MOD);
      } else {
        alert('Error al cargar el formulario de gasto');
      }
    }
  }

  /**
   * Configurar eventos del formulario de creación
   */
  function configurarEventosFormulario() {
    const form = d.getElementById('form-gasto-crear');
    if (!form) {
      console.warn(`${MOD} Formulario #form-gasto-crear no encontrado`);
      return;
    }

    // ⚠️ v2.40: Configurar event listeners para cálculo automático de retenciones
    const subtotalInput = d.getElementById('input-subtotal');
    const retefuenteSelect = d.getElementById('select-retefuente-porcentaje');
    const reteicaSelect = d.getElementById('select-reteica-porcentaje');

    // Remover listeners anteriores si existen
    if (subtotalInput) {
      subtotalInput.removeEventListener('input', calcularRetenciones);
      subtotalInput.addEventListener('input', calcularRetenciones);
    }
    if (retefuenteSelect) {
      retefuenteSelect.removeEventListener('change', calcularRetenciones);
      retefuenteSelect.addEventListener('change', calcularRetenciones);
    }
    if (reteicaSelect) {
      reteicaSelect.removeEventListener('change', calcularRetenciones);
      reteicaSelect.addEventListener('change', calcularRetenciones);
    }

    // Calcular valores iniciales
    calcularRetenciones();

    // Cargar resolución activa automáticamente
    cargarResolucionActiva();

    // Establecer valores por defecto
    establecerValoresPorDefecto();
  }

  /**
   * Cargar resoluciones disponibles y mostrarlas en el formulario
   * ⚠️ v2.60: Función pública para sincronización con módulo de resolución
   * ⚠️ v2.60: Muestra todas las resoluciones disponibles, marca la vigente como predeterminada
   */
  async function cargarResolucionActiva() {
    const select = d.getElementById('select-resolucion');
    if (!select) {
      console.warn(`${MOD} Select #select-resolucion no encontrado`);
      return;
    }

    console.log(`${MOD} Cargando resoluciones disponibles...`);

    // ⚠️ v2.60: Usar endpoint directo de resoluciones-dian (sin paginación para el select)
    // El endpoint /api/v1/gastos/resoluciones/ puede estar paginado, mejor usar el endpoint directo
    // Verificar si http() está disponible, si no, usar gastosAPI
    let resList;
    if (typeof w.http === 'function') {
      resList = await w.http('GET', '/api/v1/resoluciones-dian/?page_size=100');
    } else {
      // Fallback: usar el endpoint de gastos (puede estar paginado)
      resList = await w.gastosAPI.resoluciones();
    }
    const resActiva = await w.gastosAPI.getResolucionActiva();
    
    // Limpiar select
    select.innerHTML = '<option value="">Cargando resoluciones...</option>';
    
    // ⚠️ v2.60: Manejar respuesta paginada o directa
    let resoluciones = [];
    if (resList.ok && resList.data) {
      // Si viene paginado, usar results; si no, usar data directamente
      if (resList.data.results && Array.isArray(resList.data.results)) {
        resoluciones = resList.data.results;
      } else if (Array.isArray(resList.data)) {
        resoluciones = resList.data;
      }
    }
    
    console.log(`${MOD} Resoluciones encontradas:`, resoluciones.length);
    
    if (resoluciones.length > 0) {
      // Hay resoluciones disponibles
      let resolucionVigenteId = null;
      
      // Obtener ID de resolución vigente si existe
      if (resActiva.ok && resActiva.data) {
        resolucionVigenteId = resActiva.data.id;
        console.log(`${MOD} Resolución vigente ID:`, resolucionVigenteId);
      }
      
      // Limpiar y agregar opción por defecto
      select.innerHTML = '<option value="">Seleccione una resolución...</option>';
      
      // Agregar cada resolución al select
      resoluciones.forEach(resolucion => {
        const vigenteBadge = resolucion.vigente ? ' (VIGENTE)' : '';
        const option = d.createElement('option');
        option.value = resolucion.id;
        option.textContent = `${resolucion.prefijo} - Res: ${resolucion.numero_resolucion} (Rango: ${resolucion.rango_desde}-${resolucion.rango_hasta})${vigenteBadge}`;
        
        // Marcar la resolución vigente como seleccionada por defecto
        if (resolucion.id === resolucionVigenteId || resolucion.vigente) {
          option.selected = true;
          console.log(`${MOD} Resolución seleccionada por defecto:`, resolucion.numero_resolucion);
        }
        
        select.appendChild(option);
      });
      
      // ⚠️ v2.60: Habilitar select para que el usuario pueda seleccionar
      select.disabled = false;
      console.log(`${MOD} Select de resoluciones cargado exitosamente`);
    } else {
      // No hay resoluciones disponibles
      select.innerHTML = '<option value="">No hay resoluciones configuradas. Configure una resolución primero.</option>';
      select.disabled = true;
      console.warn(`${MOD} No se encontraron resoluciones disponibles`);
    }
  }

  /**
   * Actualizar select de resolución (sincronización con módulo de resolución)
   * ⚠️ v2.60: Función pública para actualizar el select cuando se guarda una nueva resolución
   * Se llama desde gastos_resolucion.js después de guardar exitosamente
   */
  async function actualizarSelectResolucion() {
    // Verificar si el offcanvas de creación está abierto
    const offcanvasEl = d.getElementById(OFFCANVAS_ID);
    if (!offcanvasEl) {
      // Offcanvas no está cargado, no hay nada que actualizar
      return;
    }

    // Verificar si el offcanvas está visible
    const isVisible = offcanvasEl.classList.contains('show');
    if (!isVisible) {
      // Offcanvas no está visible, no hay nada que actualizar
      return;
    }

    // Actualizar el select de resolución
    await cargarResolucionActiva();
    console.log(`${MOD} Select de resolución actualizado después de guardar nueva resolución`);
  }

  /**
   * Establecer valores por defecto en el formulario
   */
  function establecerValoresPorDefecto() {
    // Establecer fecha por defecto (hoy)
    const fechaInput = d.querySelector(`#${OFFCANVAS_ID} input[name="fecha"]`);
    if (fechaInput && !fechaInput.value) {
      const hoy = new Date().toISOString().split('T')[0];
      fechaInput.value = hoy;
    }

    // Establecer periodo por defecto (mes actual)
    const periodoInput = d.querySelector(`#${OFFCANVAS_ID} input[name="periodo"]`);
    if (periodoInput && !periodoInput.value) {
      const hoy = new Date();
      const periodo = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
      periodoInput.value = periodo;
    }
  }

  /**
   * Calcular retenciones automáticamente
   * ⚠️ v2.40: Función para calcular retenciones en tiempo real
   */
  function calcularRetenciones() {
    const subtotalInput = d.getElementById('input-subtotal');
    const retefuenteSelect = d.getElementById('select-retefuente-porcentaje');
    const reteicaSelect = d.getElementById('select-reteica-porcentaje');
    const displayRetefuente = d.getElementById('display-retefuente');
    const displayReteica = d.getElementById('display-reteica');
    const totalNetoInput = d.getElementById('input-total-neto');
    
    if (!subtotalInput || !retefuenteSelect || !reteicaSelect) return;
    
    const subtotal = parseFloat(subtotalInput.value) || 0;
    const retefuentePorcentaje = parseFloat(retefuenteSelect.value) || 0;
    const reteicaPorcentaje = parseFloat(reteicaSelect.value) || 0;
    
    // Calcular valores
    const retefuente = subtotal * retefuentePorcentaje;
    const reteica = subtotal * reteicaPorcentaje;
    const totalNeto = subtotal - retefuente - reteica;
    
    // Actualizar displays
    if (displayRetefuente) {
      displayRetefuente.textContent = fmtMoney(retefuente);
    }
    if (displayReteica) {
      displayReteica.textContent = fmtMoney(reteica);
    }
    if (totalNetoInput) {
      totalNetoInput.value = totalNeto.toFixed(2);
    }
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
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  }

  /**
   * Guardar gasto desde el formulario
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function guardar() {
    const form = d.getElementById('form-gasto-crear');
    if (!form) {
      console.warn(`${MOD} Formulario #form-gasto-crear no encontrado`);
      return;
    }

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const btnGuardar = d.getElementById('btn-guardar-gasto');
    const btnOriginalText = btnGuardar ? btnGuardar.innerHTML : '';
    
    // ⚠️ v2.40: Estado de loading para evitar dobles clics
    let isLoading = false;
    if (btnGuardar) {
      isLoading = btnGuardar.disabled;
      if (!isLoading) {
        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Guardando...';
      }
    }

    // Validar que haya resolución activa antes de enviar
    const resCheck = await w.gastosAPI.getResolucionActiva();
    if (!resCheck.ok || resCheck.status === 404) {
      const errorMsg = 'No hay resolución DIAN configurada. Configure una resolución primero.';
      
      // Restaurar botón
      if (btnGuardar && !isLoading) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = btnOriginalText;
      }
      
      // ⚠️ v2.60: Error Boundary - Mostrar error en offcanvas
      const errorContainer = d.getElementById('feedback-create-gasto');
      if (errorContainer) {
        errorContainer.className = 'alert alert-danger';
        errorContainer.textContent = errorMsg;
        errorContainer.classList.remove('d-none');
        errorContainer.style.display = 'block';
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 404, data: { detail: errorMsg } }, MOD);
      }
      return;
    }

    // ⚠️ v2.40: El backend calcula automáticamente las retenciones basándose en los porcentajes
    // Solo enviamos: subtotal, retefuente_porcentaje, reteica_porcentaje
    const payload = new FormData(form);
    
    // Error Boundary Pattern v2.40
    const res = await w.gastosAPI.create(payload);
    if (!res.ok) {
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = btnOriginalText;
      }
      
      // ⚠️ v2.60: Error Boundary - Mostrar error en offcanvas
      const errorContainer = d.getElementById('feedback-create-gasto');
      if (errorContainer) {
        let errorMessage = 'Error al guardar gasto';
        if (res.data) {
          if (res.data.detail) {
            errorMessage = res.data.detail;
          } else if (res.data.message) {
            errorMessage = res.data.message;
          } else if (typeof res.data === 'string') {
            errorMessage = res.data;
          }
        }
        
        errorContainer.className = 'alert alert-danger';
        errorContainer.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Error:</strong> ${errorMessage}`;
        errorContainer.classList.remove('d-none');
        errorContainer.style.display = 'block';
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      
      return w.UIManager?.notifyError(res, MOD);
    }

    // Éxito: cerrar offcanvas y mostrar notificación
    hideOffcanvas();
    
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Documento Soporte generado con éxito');
    }
    
    // Forzar recarga de la tabla y resumen
    if (w.AppGastos && typeof w.AppGastos.refresh === 'function') {
      w.AppGastos.refresh();
    }
  }

  /**
   * Función pública: Crear nuevo gasto
   */
  async function crear() {
    await cargarOffcanvas();
  }

  // ⚠️ CRÍTICO v2.60: Exponer funciones INMEDIATAMENTE después de definirlas
  if (w.AppGastos) {
    w.AppGastos.crear = crear;
    w.AppGastos.guardar = guardar;
    w.AppGastos.actualizarSelectResolucion = actualizarSelectResolucion; // ⚠️ v2.60: Sincronización con módulo de resolución
  }

  // ⚠️ v2.60: Limpiar formulario al cerrar offcanvas
  d.addEventListener('hidden.bs.offcanvas', (e) => {
    if (e.target.id === OFFCANVAS_ID) {
      const form = d.getElementById('form-gasto-crear');
      if (form) form.reset();
      
      // ⚠️ v2.40: Resetear valores calculados después de limpiar el formulario
      setTimeout(() => {
        calcularRetenciones();
      }, 100);
      
      const feedback = d.getElementById('feedback-create-gasto');
      if (feedback) {
        feedback.classList.add('d-none');
        feedback.textContent = '';
      }
      
      // ⚠️ v2.60: Resetear select de resolución (se recargará cuando se abra el offcanvas)
      const select = d.getElementById('select-resolucion');
      if (select) {
        select.innerHTML = '<option value="">Cargando resoluciones disponibles...</option>';
        select.disabled = false; // ⚠️ v2.60: Habilitado para selección
      }
      
      // ⚠️ v2.40: Restaurar botón guardar
      const btnGuardar = d.getElementById('btn-guardar-gasto');
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="bi bi-cloud-arrow-up me-1"></i> Guardar y Firmar';
      }
    }
  });

  console.log(`${MOD} Módulo de creación inicializado`);

})(window, document);
