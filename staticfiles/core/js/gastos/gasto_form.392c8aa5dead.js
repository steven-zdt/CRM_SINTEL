/**
 * gasto_form.js - DEPRECATED v2.61.8
 *
 * WARNING: Este archivo es LEGACY y esta programado para eliminacion.
 * La funcionalidad moderna reside en:
 *   - apps/tenant/gastos/static/gastos/js/features/gasto_editor.js
 *   - apps/tenant/gastos/static/gastos/js/features/gasto_list.js
 *   - apps/tenant/gastos/static/gastos/js/features/resolucion_editor.js
 * Namespace moderno: window.Sintel.Gastos (vs legacy w.AppGasto)
 *
 * Anti-patrones presentes:
 *   - URLs hardcodeadas (no usa gastos.api.js centralizado)
 *   - Missing JWT auth headers
 *   - Duplica logica ya migrada a Feature-Sliced Design
 *
 * Namespace: w.AppGasto
 *
 * Merges: gastos_crear.js + gastos_anular.js
 * Reemplaza las referencias legacy de w.AppGastos.crear / .guardar / .ver / .desactivar / .anular
 *
 * Dependencias globales:
 * - w.gastosAPI  (gastos.api.js)
 * - w.UIManager  (ui-manager.js)
 * - w.SintelFeedback
 * - w.DOMUtils
 * - w.bootstrap
 * - htmx
 */
(function (w, d) {
  'use strict';

  const MOD = '[gasto.form]';
  const OFFCANVAS_ID = 'offcanvas-gasto-crear';
  const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-gastos';
  const GESTOR_OFFCANVAS_URL = '/api/v1/gastos/gestor-offcanvas/';

  // Singleton Offcanvas instance
  let offcanvasInstance = null;
  let totalsListenerRef = null;
  let proveedoresCatalogo = [];
  let subtotalEnMemoria = null;

  // Inicializar namespace compartido para mantener compatibilidad entre
  // los módulos nuevos (AppGasto) y el orquestador legacy (AppGastos).
  const gastosNamespace = w.AppGastos || w.AppGasto || {};
  w.AppGastos = gastosNamespace;
  w.AppGasto = gastosNamespace;

  // ---------------------------------------------------------------------------
  // HELPERS: Offcanvas lifecycle
  // ---------------------------------------------------------------------------

  function initOffcanvas(el) {
    if (!el) return null;
    if (w.bootstrap && w.bootstrap.Offcanvas) {
      offcanvasInstance = w.bootstrap.Offcanvas.getOrCreateInstance(el);
      return offcanvasInstance;
    }
    return null;
  }

  function showOffcanvas(el) {
    const inst = initOffcanvas(el);
    if (inst) inst.show();
  }

  function hideOffcanvas() {
    if (offcanvasInstance) offcanvasInstance.hide();
  }

  // ---------------------------------------------------------------------------
  // HELPERS: UI / dinero
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // CREACION: cargar resoluciones
  // ---------------------------------------------------------------------------

  async function cargarResolucionActiva() {
    const select     = d.getElementById('select-resolucion-dian');
    const hiddenInput = d.getElementById('hidden-resolucion-dian');
    const btnGuardar = d.getElementById('btn-guardar-gasto');
    const subtotalInput = d.getElementById('input-subtotal');
    if (!select) return;

    console.log(`${MOD} Cargando resoluciones disponibles...`);

    let resList;
    if (typeof w.resolucionesAPI?.list === 'function') {
      resList = await w.resolucionesAPI.list();
    } else if (typeof w.gastosAPI?.resoluciones === 'function') {
      resList = await w.gastosAPI.resoluciones();
    } else if (typeof w.http === 'function') {
      resList = await w.http('GET', '/api/v1/gastos/resoluciones/');
    }

    select.innerHTML = '<option value="">Cargando resoluciones...</option>';

    let resoluciones = [];
    if (resList?.ok && resList.data) {
      if (Array.isArray(resList.data.results)) {
        resoluciones = resList.data.results;
      } else if (Array.isArray(resList.data)) {
        resoluciones = resList.data;
      }
    }

    if (resoluciones.length > 0) {
      select.innerHTML = '<option value="">Seleccione una resolucion...</option>';
      let vigenteId = null;

      resoluciones.forEach(res => {
        const vigenteBadge = res.vigente ? ' [VIGENTE]' : '';
        const opt = d.createElement('option');
        opt.value = res.id;
        opt.textContent = `${res.prefijo} - Res: ${res.numero_resolucion} (Rango: ${res.rango_desde}-${res.rango_hasta})${vigenteBadge}`;
        select.appendChild(opt);
        if (res.vigente && vigenteId === null) {
          vigenteId = String(res.id);
        }
      });

      if (vigenteId) {
        select.value = vigenteId;
        console.log(`${MOD} Resolucion vigente pre-seleccionada ID:`, vigenteId);
      }
      select.disabled = false;
      if (subtotalInput) subtotalInput.disabled = false;
      // DOM Shield: sincronizar hidden input con la seleccion inicial
      if (hiddenInput) hiddenInput.value = parseInt(select.value) || '';
      // Desbloquear boton de guardado
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.title = ''; }
    } else {
      select.innerHTML = '<option value="">No hay resoluciones configuradas. Configure una primero.</option>';
      select.disabled = true;
      if (subtotalInput) subtotalInput.disabled = true;
      if (hiddenInput) hiddenInput.value = '';
      // Bloquear boton de guardado y notificar al usuario
      if (btnGuardar) {
        btnGuardar.disabled = true;
        btnGuardar.title = 'Debe configurar una Resolucion DIAN antes de generar gastos';
      }
      w.UIManager?.handleError(
        { status: 0, data: { detail: 'Debe configurar una Resolucion DIAN antes de generar gastos. Use el boton "Configurar nueva" al lado del campo de resolucion.' } },
        MOD,
        { errorContainerSelector: '#feedback-create-gasto' }
      );
    }
  }

  async function actualizarSelectResolucion() {
    const offcanvasEl = d.getElementById(OFFCANVAS_ID);
    if (!offcanvasEl || !offcanvasEl.classList.contains('show')) return;
    await cargarResolucionActiva();
    console.log(`${MOD} Select de resolucion actualizado`);
  }

  function resetProveedorCascade(message) {
    const proveedorSelect = d.getElementById('id_proveedor_select');
    const proveedorUuidInput = d.getElementById('id_proveedor_uuid');
    const nitInput = d.getElementById('id_nit_vendedor');
    const razonSocialInput = d.getElementById('id_razon_social_vendedor');
    const nitLabel = d.getElementById('id_nit_vendedor_label');
    const razonSocialLabel = d.getElementById('id_razon_social_vendedor_label');
    const help = d.getElementById('proveedor-help');

    if (proveedorSelect) {
      proveedorSelect.disabled = true;
      proveedorSelect.innerHTML = '<option value="">-- Seleccione un Proveedor --</option>';
    }
    if (proveedorUuidInput) proveedorUuidInput.value = '';
    if (nitInput) nitInput.value = '';
    if (razonSocialInput) razonSocialInput.value = '';
    if (nitLabel) nitLabel.textContent = '--';
    if (razonSocialLabel) razonSocialLabel.textContent = '--';
    if (help) help.textContent = message;
  }

  function preservarSubtotalEnMemoria() {
    const subtotalInput = d.getElementById('input-subtotal');
    if (!subtotalInput) return;
    subtotalEnMemoria = subtotalInput.value;
  }

  function restaurarSubtotalEnMemoria() {
    const subtotalInput = d.getElementById('input-subtotal');
    if (!subtotalInput) return;
    if (subtotalEnMemoria !== null && subtotalEnMemoria !== undefined) {
      subtotalInput.value = subtotalEnMemoria;
      syncTotals();
    }
  }

  function setSelectValueOrAppend(selectEl, value) {
    if (!selectEl) return;
    const normalizedValue = String(value ?? '').trim();
    if (!normalizedValue) return;
    const existing = Array.from(selectEl.options || []).find((opt) => String(opt.value).trim() === normalizedValue);
    if (!existing) {
      const option = d.createElement('option');
      option.value = normalizedValue;
      option.textContent = `${normalizedValue}% - Configurado proveedor`;
      selectEl.appendChild(option);
    }
    selectEl.value = normalizedValue;
  }

  function calcularTotalNetoProveedorServiceJs(subtotal, retefuentePct, reteicaPct) {
    const subtotalNum = parseFloat(subtotal) || 0;
    const retefuenteNum = parseFloat(retefuentePct) || 0;
    const reteicaNum = parseFloat(reteicaPct) || 0;
    const porcentajeRetencion = retefuenteNum + reteicaNum;
    return subtotalNum - (subtotalNum * (porcentajeRetencion / 100));
  }

  async function solicitarCalculoFinancieroServicio() {
    const subtotal = parseFloat(d.getElementById('input-subtotal')?.value) || 0;
    const retefuentePct = parseFloat(d.getElementById('select-retefuente')?.value) || 0;
    const reteicaPct = parseFloat(d.getElementById('select-reteica')?.value) || 0;
    const proveedorUuid = String(d.getElementById('id_proveedor_uuid')?.value || '').trim() || null;
    const tipoDocumento = String(d.getElementById('id_tipo_documento')?.value || '').trim();

    const payload = {
      subtotal: parseFloat(subtotal) || 0,
      retefuente_porcentaje: parseFloat(retefuentePct) || 0,
      reteica_porcentaje: parseFloat(reteicaPct) || 0,
      proveedor_uuid: proveedorUuid,
      tipo_documento: tipoDocumento
    };

    const res = (typeof w.http === 'function')
      ? await w.http('POST', '/api/v1/gastos/validar-financieros/', payload)
      : null;
    if (!res?.ok) {
      return null;
    }
    return res.data || null;
  }

  function validarConsistenciaNetoProveedorService() {
    const subtotal = parseFloat(d.getElementById('input-subtotal')?.value) || 0;
    const retefuentePct = parseFloat(d.getElementById('select-retefuente')?.value) || 0;
    const reteicaPct = parseFloat(d.getElementById('select-reteica')?.value) || 0;
    const totalNetoUi = parseFloat(d.getElementById('input-total-neto')?.value) || 0;
    const totalEsperado = calcularTotalNetoProveedorServiceJs(subtotal, retefuentePct, reteicaPct);
    const diferencia = Math.abs(totalEsperado - totalNetoUi);
    return diferencia <= 0.01;
  }

  async function loadProveedoresList(tipoDocumento) {
    const proveedorSelect = d.getElementById('id_proveedor_select');
    const proveedorUuidInput = d.getElementById('id_proveedor_uuid');
    const nitInput = d.getElementById('id_nit_vendedor');
    const razonSocialInput = d.getElementById('id_razon_social_vendedor');
    const nitLabel = d.getElementById('id_nit_vendedor_label');
    const razonSocialLabel = d.getElementById('id_razon_social_vendedor_label');
    const help = d.getElementById('proveedor-help');

    if (!proveedorSelect || !proveedorUuidInput || !nitInput || !razonSocialInput) return;

    if (!tipoDocumento) {
      resetProveedorCascade('Seleccione un tipo de documento para cargar proveedores.');
      return;
    }

    preservarSubtotalEnMemoria();

    proveedoresCatalogo = [];
    proveedorSelect.innerHTML = '<option value="">-- Seleccione un Proveedor --</option>';
    proveedorSelect.disabled = true;
    proveedorUuidInput.value = '';
    nitInput.value = '';
    razonSocialInput.value = '';
    if (nitLabel) nitLabel.textContent = '--';
    if (razonSocialLabel) razonSocialLabel.textContent = '--';

    try {
      const response = await w.fetch(`/api/v1/proveedores/filtrar-por-tipo/?tipo=${encodeURIComponent(tipoDocumento)}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json'
        }
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      proveedoresCatalogo = await response.json();
    } catch (error) {
      console.warn(`${MOD} Error consultando proveedores`, error);
      resetProveedorCascade('No fue posible cargar proveedores para el tipo seleccionado.');
      restaurarSubtotalEnMemoria();
      return;
    }

    if (!proveedoresCatalogo.length) {
      resetProveedorCascade('No hay proveedores activos con este tipo de documento.');
      restaurarSubtotalEnMemoria();
      return;
    }

    proveedorSelect.disabled = false;

    proveedoresCatalogo.forEach((proveedor) => {
      const uuid = String(proveedor.uuid || '').trim();
      const nit = String(proveedor.documento || '').trim();
      const razon = String(proveedor.nombre || '').trim();
      if (!uuid) return;
      const option = d.createElement('option');
      option.value = uuid;
      option.textContent = `[${nit}] - [${razon}]`;
      proveedorSelect.appendChild(option);
    });

    proveedorSelect.onchange = function() {
      preservarSubtotalEnMemoria();
      const selectedUuid = String(this.value || '').trim();
      const selected = proveedoresCatalogo.find((p) => String(p.uuid || '').trim() === selectedUuid);
      if (!selectedUuid || !selected) {
        proveedorUuidInput.value = '';
        nitInput.value = '';
        razonSocialInput.value = '';
        if (nitLabel) nitLabel.textContent = '--';
        if (razonSocialLabel) razonSocialLabel.textContent = '--';
        if (help) help.textContent = 'Seleccione un proveedor valido del listado.';
        restaurarSubtotalEnMemoria();
        return;
      }

      proveedorUuidInput.value = selectedUuid;
      nitInput.value = String(selected.documento || '').trim();
      razonSocialInput.value = String(selected.nombre || '').trim();
      if (nitLabel) nitLabel.textContent = nitInput.value || '--';
      if (razonSocialLabel) razonSocialLabel.textContent = razonSocialInput.value || '--';
      syncTotals();
      if (help) help.textContent = 'Proveedor seleccionado correctamente.';
      restaurarSubtotalEnMemoria();
    };

    if (help) help.textContent = 'Seleccione un proveedor del listado para ver su documento y nombre.';
    restaurarSubtotalEnMemoria();
  }

  async function loadCategoriasContables() {
    const select = d.getElementById('id_cuenta_contable_uuid');
    if (!select) return;

    select.innerHTML = '<option value="">Cargando categorias contables...</option>';
    select.disabled = true;

    let res = null;
    if (typeof w.http === 'function') {
      res = await w.http('GET', '/api/v1/contabilidad/cuentas-contables/cuentas_gasto/');
    }

    if (!res?.ok) {
      select.innerHTML = '<option value="">No fue posible cargar categorias contables</option>';
      select.disabled = true;
      console.error('[gasto:contabilidad] Error al cargar categorias contables', res);
      return;
    }

    const cuentas = Array.isArray(res.data)
      ? res.data
      : Array.isArray(res.data?.results)
        ? res.data.results
        : [];

    if (!cuentas.length) {
      select.innerHTML = '<option value="">No hay cuentas contables de gasto disponibles</option>';
      select.disabled = true;
      return;
    }

    select.innerHTML = '<option value="">Seleccione una categoria contable...</option>';
    cuentas.forEach((cuenta) => {
      const opt = d.createElement('option');
      opt.value = String(cuenta.uuid || '').trim();
      opt.textContent = String(cuenta.display || '').trim();
      if (!opt.value) return;
      select.appendChild(opt);
    });
    select.disabled = false;
  }

  function getCuentaContableSeleccion() {
    const select = d.getElementById('id_cuenta_contable_uuid');
    if (!select) {
      return { codigo: '', nombre: '', display: '' };
    }
    const text = String(select.options?.[select.selectedIndex]?.textContent || '').trim();
    const match = text.match(/^\[([^\]]+)\]\s*-\s*(.+)$/);
    if (!match) {
      return { codigo: '', nombre: text, display: text };
    }
    return {
      codigo: String(match[1] || '').trim(),
      nombre: String(match[2] || '').trim(),
      display: text,
    };
  }

  // ---------------------------------------------------------------------------
  // CREACION: calculos y valores por defecto
  // ---------------------------------------------------------------------------

  function establecerValoresPorDefecto() {
    const fechaInput = d.querySelector(`#${OFFCANVAS_ID} input[name="fecha"]`);
    if (fechaInput && !fechaInput.value) {
      fechaInput.value = new Date().toISOString().split('T')[0];
    }
    const periodoInput = d.querySelector(`#${OFFCANVAS_ID} input[name="periodo"]`);
    if (periodoInput && !periodoInput.value) {
      const hoy = new Date();
      periodoInput.value = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
    }
  }

  // Zero Trust: Función única para sincronizar totales según AGENTS.md
  async function syncTotals() {
    const subtotalInput = d.getElementById('input-subtotal');
    const retefuenteSelect = d.getElementById('select-retefuente');
    const reteicaSelect = d.getElementById('select-reteica');
    const totalNetoInput = d.getElementById('input-total-neto');
    const displayRetefuente = d.getElementById('input-retefuente-calculada');
    const displayReteica = d.getElementById('input-reteica-calculada');

    if (!subtotalInput || !totalNetoInput) return;

    // Zero Trust: parseFloat(val) || 0 para procesar valores
    const subtotal = parseFloat(subtotalInput.value) || 0;
    const retefuentePct = parseFloat(retefuenteSelect?.value) || 0;
    const reteicaPct = parseFloat(reteicaSelect?.value) || 0;

    // Fallback local temporal. El valor oficial llega desde el backend.
    const retefuente = subtotal * (retefuentePct / 100);
    const reteica = subtotal * (reteicaPct / 100);
    const totalNeto = calcularTotalNetoProveedorServiceJs(subtotal, retefuentePct, reteicaPct);

    // Actualizar displays
    if (displayRetefuente) displayRetefuente.value = retefuente.toFixed(2);
    if (displayReteica) displayReteica.value = reteica.toFixed(2);
    totalNetoInput.value = totalNeto.toFixed(2);

    try {
      const validacion = await solicitarCalculoFinancieroServicio();
      if (!validacion) return;
      const retefuenteSrv = parseFloat(validacion.retefuente) || 0;
      const reteicaSrv = parseFloat(validacion.reteica) || 0;
      const totalSrv = parseFloat(validacion.total_neto) || 0;
      if (displayRetefuente) displayRetefuente.value = retefuenteSrv.toFixed(2);
      if (displayReteica) displayReteica.value = reteicaSrv.toFixed(2);
      totalNetoInput.value = totalSrv.toFixed(2);
    } catch (error) {
      console.warn(`${MOD} No fue posible validar calculo financiero en backend`, error);
    }
  }

  // ---------------------------------------------------------------------------
  // CREACION: configurar eventos del formulario
  // ---------------------------------------------------------------------------

  function configurarEventosFormulario() {
    const form = d.getElementById('form-gasto-crear');
    if (!form) return;

    // Listener único delegado para Subtotal y Retenciones
    if (totalsListenerRef) {
      form.removeEventListener('input', totalsListenerRef);
      form.removeEventListener('change', totalsListenerRef);
    }
    totalsListenerRef = function(event) {
      const targetId = event?.target?.id || '';
      if (targetId === 'input-subtotal' || targetId === 'select-retefuente' || targetId === 'select-reteica') {
        syncTotals();
      }
    };
    form.addEventListener('input', totalsListenerRef);
    form.addEventListener('change', totalsListenerRef);

    syncTotals();
    cargarResolucionActiva();
    loadCategoriasContables();
    const tipoDocumentoSelect = d.getElementById('id_tipo_documento');
    if (tipoDocumentoSelect) {
      tipoDocumentoSelect.onchange = function() {
        const tipoDocumento = String(this.value || '').trim();
        resetProveedorCascade('Cargando proveedores para el tipo de documento seleccionado.');
        loadProveedoresList(tipoDocumento);
      };
      if (tipoDocumentoSelect.value) {
        loadProveedoresList(String(tipoDocumentoSelect.value || '').trim());
      } else {
        resetProveedorCascade('Seleccione un tipo de documento para cargar proveedores.');
      }
    }
    establecerValoresPorDefecto();

    // DOM Shield: sincronizar select visible con hidden input en cada cambio
    const selectResDian = d.getElementById('select-resolucion-dian');
    if (selectResDian) {
      selectResDian.addEventListener('change', function() {
        const hid = d.getElementById('hidden-resolucion-dian');
        if (hid) hid.value = parseInt(this.value) || '';
      });
    }

    const btnGuardar = d.getElementById('btn-guardar-gasto');
    if (btnGuardar) {
      btnGuardar.onclick = function(e) {
        e.preventDefault();
        guardar();
      };
    }
  }

  // ---------------------------------------------------------------------------
  // CREACION: cargar offcanvas y abrir
  // ---------------------------------------------------------------------------

  async function cargarOffcanvas() {
    const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
    if (!container) {
      console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
      if (w.SintelFeedback) w.SintelFeedback.error('Error: Contenedor de Offcanvas no encontrado');
      return;
    }

    const url = `${GESTOR_OFFCANVAS_URL}?simple=true`;

    try {
      await htmx.ajax('GET', url, { target: `#${OFFCANVAS_CONTAINER_ID}`, swap: 'innerHTML' });
      await new Promise(r => setTimeout(r, 50));

      const offcanvasEl = d.getElementById(OFFCANVAS_ID);
      if (offcanvasEl) {
        showOffcanvas(offcanvasEl);
        setTimeout(() => configurarEventosFormulario(), 100);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas:`, error);
      if (w.UIManager?.notifyError) {
        w.UIManager.notifyError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario' } }, MOD);
      } else if (w.UIManager?.handleError) {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario' } }, MOD);
      }
    }
  }

  function inicializarOffcanvasActual() {
    const offcanvasEl = d.getElementById(OFFCANVAS_ID);
    if (!offcanvasEl) return;
    initOffcanvas(offcanvasEl);
    configurarEventosFormulario();
  }

  function crear() {
    return cargarOffcanvas();
  }

  // ---------------------------------------------------------------------------
  // CREACION: guardar (JSON payload)
  // ---------------------------------------------------------------------------

  async function guardar() {
    const form = d.getElementById('form-gasto-crear');
    if (!form) { console.warn(`${MOD} Formulario no encontrado`); return; }
    if (!form.checkValidity()) { form.reportValidity(); return; }

    const btnGuardar = d.getElementById('btn-guardar-gasto');
    const btnOriginalText = btnGuardar ? btnGuardar.innerHTML : '';

    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Guardando...';
    }

    // DOM Shield: leer resolucion_dian desde campo oculto (Zero Trust)
    const resolucionId = parseInt(d.getElementById('hidden-resolucion-dian')?.value) || 0;
    if (!resolucionId) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }
      _mostrarErrorOffcanvas('Debe seleccionar una Resolucion DIAN antes de guardar. Use el boton "Configurar nueva" si aun no ha registrado ninguna.');
      return;
    }

    const proveedorUuid = d.getElementById('id_proveedor_uuid')?.value || '';
    const tipoDocumento = String(d.getElementById('id_tipo_documento')?.value || '').trim();

    if (!tipoDocumento) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }
      _mostrarErrorOffcanvas('Debe seleccionar el tipo de documento del proveedor.');
      return;
    }

    if (!proveedorUuid) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }
      _mostrarErrorOffcanvas('Debe seleccionar un proveedor del directorio antes de guardar.');
      return;
    }

    const vendedorNit = String(d.getElementById('id_nit_vendedor')?.value || '').trim();
    const vendedorNombre = String(d.getElementById('id_razon_social_vendedor')?.value || '').trim();
    if (!vendedorNit || !vendedorNombre) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }
      _mostrarErrorOffcanvas('No se pudo resolver la identificacion del proveedor. Re-seleccione el proveedor e intente de nuevo.');
      return;
    }

    const cuentaContableUuid = String(d.getElementById('id_cuenta_contable_uuid')?.value || '').trim();
    if (!cuentaContableUuid) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }
      _mostrarErrorOffcanvas('Debe seleccionar una categoria contable antes de guardar.');
      return;
    }

    console.info('[gasto:form] Omitiendo validación de campos opcionales (CC/Cat Legacy).');

    if (!validarConsistenciaNetoProveedorService()) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }
      _mostrarErrorOffcanvas('El total neto no coincide con la logica central de proveedores. Verifique subtotal y retenciones.');
      return;
    }

    // Construir payload JSON (Zero Trust: conversion explicita de tipos)
    // 🛡️ v2.61: SINTEL DOM SHIELD PATTERN - Protección contra plugins visuales (AGENTS.md)
    const selectElements = form.querySelectorAll('select[name]');
    const tempNames = new Map();
    selectElements.forEach(select => {
      tempNames.set(select, select.getAttribute('name'));
      select.removeAttribute('name');
    });

    const formData = new FormData(form);

    // 🛡️ v2.61: Restaurar DOM original
    selectElements.forEach(select => {
      select.setAttribute('name', tempNames.get(select));
    });
    const payload = {};
    for (const [key, value] of formData.entries()) {
      if (key === 'adjunto') continue; // archivo: manejar por separado si se requiere
      payload[key] = value;
    }

    // Payload simplificado: proveedor_uuid obligatorio + subtotal, retenciones y metadatos
    const subtotalValue = parseFloat(payload.subtotal) || 0;
    const retefuenteValue = parseFloat(payload.retefuente_porcentaje) || 0;
    const reteicaValue = parseFloat(payload.reteica_porcentaje) || 0;
    const totalNetoValue = parseFloat(d.getElementById('input-total-neto')?.value) || 0;
    const cuentaContableSeleccion = getCuentaContableSeleccion();
    const categoriaLegacy = String(payload.categoria_contable || '').trim();
    const categoriaDesdePlan = String(cuentaContableSeleccion.display || '').trim();

    const cleanPayload = {
      proveedor_uuid: proveedorUuid || null,
      tipo_documento: tipoDocumento,
      vendedor_nit: vendedorNit,
      vendedor_nombre: vendedorNombre,
      subtotal: subtotalValue,
      retefuente_porcentaje: retefuenteValue,
      reteica_porcentaje: reteicaValue,
      total_neto: totalNetoValue,
      resolucion_dian: parseInt(d.getElementById('hidden-resolucion-dian')?.value) || 0,
      // Metadatos del Documento Soporte
      numero_factura_proveedor: payload.numero_factura_proveedor || '',
      fecha: payload.fecha || '',
      periodo: payload.periodo || '',
      centro_costo: payload.centro_costo || '',
      categoria_contable: categoriaLegacy || categoriaDesdePlan,
      codigo_contable: d.getElementById('select-codigo-contable')?.value || '',
      cuenta_contable_uuid: cuentaContableUuid,
      cuenta_contable_codigo: cuentaContableSeleccion.codigo || '',
      cuenta_contable_nombre: cuentaContableSeleccion.nombre || '',
      descripcion: payload.descripcion || '',
      observaciones: payload.observaciones || ''
    };

    const res = (typeof w.http === 'function')
      ? await w.http('POST', '/api/v1/gastos/', cleanPayload)
      : await w.gastosAPI.create(cleanPayload);

    if (!res.ok) {
      if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.innerHTML = btnOriginalText; }

      let errorMessage = 'Error al guardar gasto';
      if (res.data?.detail) errorMessage = res.data.detail;
      else if (res.data?.message) errorMessage = res.data.message;
      else if (res.data?.data?.detail) errorMessage = res.data.data.detail;
      else if (typeof res.data === 'string') errorMessage = res.data;

      _mostrarErrorOffcanvas(errorMessage);
      return w.UIManager?.handleError(res, MOD, { errorContainerSelector: '#feedback-create-gasto' });
    }

    // Exito
    hideOffcanvas();
    d.dispatchEvent(new CustomEvent('Sintel:GastosChanged', { detail: res.data }));
    if (w.SintelFeedback) w.SintelFeedback.success('Documento Soporte generado con exito');
    if (w.AppGastos && typeof w.AppGastos.refresh === 'function') w.AppGastos.refresh();
  }

  function _mostrarErrorOffcanvas(errorMessage) {
    const errorContainer = d.getElementById('feedback-create-gasto');
    if (!errorContainer) return;
    errorContainer.className = 'alert alert-danger';
    errorContainer.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Error:</strong> ${errorMessage}`;
    errorContainer.classList.remove('d-none');
    errorContainer.style.display = 'block';
    errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // ---------------------------------------------------------------------------
  // ANULACION: ver, desactivar, anular
  // ---------------------------------------------------------------------------

  async function ver(id) {
    const container = d.getElementById('offcanvas-container-gastos');
    if (!container) { console.error(`${MOD} Contenedor #offcanvas-container-gastos no encontrado`); return; }

    const url = `/api/v1/gastos/gestor-offcanvas/?id=${id}&simple=true`;
    try {
      await htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
      await new Promise(r => setTimeout(r, 50));
      const offcanvasEl = d.getElementById('offcanvas-gasto-detalle');
      if (offcanvasEl) {
        if (w.bootstrap?.Offcanvas) w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar detalle:`, error);
      w.UIManager?.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el detalle' } }, MOD);
    }
  }

  async function desactivar(id) {
    if (!confirm('Esta seguro de desactivar este Documento Soporte? Debe estar desactivado para poder anularlo.')) return;

    const res = await w.gastosAPI.desactivar(id);
    if (!res.ok) { w.UIManager?.handleError(res, MOD); return; }

    if (w.SintelFeedback) w.SintelFeedback.success('Documento desactivado correctamente. Ahora puede anularlo si lo desea.');
    if (w.AppGastos && typeof w.AppGastos.refresh === 'function') w.AppGastos.refresh();
  }

  async function anular(id) {
    const resGet = await w.gastosAPI.get(id);
    if (!resGet.ok || !resGet.data) { w.UIManager?.handleError(resGet, MOD); return; }

    const documento = resGet.data;
    const documentoSoporte = documento.documento_soporte || {};
    const activo = (typeof documento.ds_activo === 'boolean')
      ? documento.ds_activo
      : (typeof documentoSoporte.activo === 'boolean' ? documentoSoporte.activo : true);
    const anuladoDoc = (typeof documento.ds_anulado === 'boolean')
      ? documento.ds_anulado
      : (typeof documentoSoporte.anulado === 'boolean' ? documentoSoporte.anulado : false);

    if (activo) {
      const msg = 'No se puede anular un documento que esta activo. Debe desactivarlo primero.';
      if (w.SintelFeedback) w.SintelFeedback.error(msg);
      else w.UIManager?.handleError({ ok: false, status: 422, data: { detail: msg } }, MOD);
      return;
    }

    if (anuladoDoc === true) {
      if (w.SintelFeedback) w.SintelFeedback.warning('Este documento ya esta anulado.');
      return;
    }

    if (!confirm('Esta seguro de anular este Documento Soporte? Esta accion es irreversible y afectara los totales financieros.')) return;

    const res = await w.gastosAPI.anular(id);
    if (!res.ok) { w.UIManager?.handleError(res, MOD); return; }

    if (w.SintelFeedback) w.SintelFeedback.success('Documento Soporte anulado correctamente.');
    if (w.AppGastos && typeof w.AppGastos.refresh === 'function') w.AppGastos.refresh();
  }

  // ---------------------------------------------------------------------------
  // Reset al cerrar offcanvas
  // ---------------------------------------------------------------------------

  d.addEventListener('hidden.bs.offcanvas', (e) => {
    if (e.target.id !== OFFCANVAS_ID) return;

    const form = d.getElementById('form-gasto-crear');
    if (form) form.reset();

    setTimeout(() => syncTotals(), 100);

    const feedback = d.getElementById('feedback-create-gasto');
    if (feedback) { feedback.classList.add('d-none'); feedback.textContent = ''; }

    const select = d.getElementById('select-resolucion-dian');
    const tipoDocumentoSelect = d.getElementById('id_tipo_documento');
    const proveedorSelect = d.getElementById('id_proveedor_select');
    const proveedorUuid = d.getElementById('id_proveedor_uuid');
    const nitInput = d.getElementById('id_nit_vendedor');
    const razonSocialInput = d.getElementById('id_razon_social_vendedor');
    const nitLabel = d.getElementById('id_nit_vendedor_label');
    const razonSocialLabel = d.getElementById('id_razon_social_vendedor_label');
    const proveedorHelp = d.getElementById('proveedor-help');
    const hiddenResReset = d.getElementById('hidden-resolucion-dian');
    const cuentaContableSelect = d.getElementById('id_cuenta_contable_uuid');
    if (select) {
      select.innerHTML = '<option value="">Cargando resoluciones disponibles...</option>';
      select.disabled = false;
    }
    if (tipoDocumentoSelect) {
      tipoDocumentoSelect.value = '';
    }
    if (proveedorSelect) {
      proveedorSelect.innerHTML = '<option value="">-- Seleccione un Proveedor --</option>';
      proveedorSelect.disabled = true;
    }
    if (proveedorUuid) proveedorUuid.value = '';
    if (hiddenResReset) hiddenResReset.value = '';
    if (cuentaContableSelect) {
      cuentaContableSelect.innerHTML = '<option value="">Cargando categorias contables...</option>';
      cuentaContableSelect.disabled = false;
    }
    if (nitInput) nitInput.value = '';
    if (razonSocialInput) razonSocialInput.value = '';
    if (nitLabel) nitLabel.textContent = '--';
    if (razonSocialLabel) razonSocialLabel.textContent = '--';
    if (proveedorHelp) {
      proveedorHelp.textContent = 'Seleccione tipo de documento para habilitar el listado de proveedores.';
    }

    const btnGuardar = d.getElementById('btn-guardar-gasto');
    if (btnGuardar) {
      btnGuardar.disabled = false;
      btnGuardar.innerHTML = '<i class="bi bi-cloud-arrow-up me-1"></i> Guardar y Firmar';
    }
  });

  // ---------------------------------------------------------------------------
  // Exponer API publica del modulo
  // ---------------------------------------------------------------------------

  // Reactividad inter-modulos: actualizar select de resolucion cuando se guarde una nueva
  function onResolucionActualizada() {
    actualizarSelectResolucion();
  }

  d.addEventListener('Sintel:ResolucionesChanged', onResolucionActualizada);

  d.addEventListener('htmx:afterSwap', function(event) {
    const target = event?.detail?.target;
    if (!target || target.id !== OFFCANVAS_CONTAINER_ID) return;
    if (!d.getElementById(OFFCANVAS_ID)) return;
    inicializarOffcanvasActual();
  });

  d.addEventListener('shown.bs.offcanvas', function(event) {
    if (event?.target?.id !== OFFCANVAS_ID) return;
    inicializarOffcanvasActual();
    loadCategoriasContables();
    const selectResolucion = d.getElementById('select-resolucion-dian');
    if (selectResolucion && selectResolucion.options.length <= 1) {
      setTimeout(() => actualizarSelectResolucion(), 200);
    }
  });

  gastosNamespace.crear = crear;
  gastosNamespace.guardar = guardar;
  gastosNamespace.ver = ver;
  gastosNamespace.desactivar = desactivar;
  gastosNamespace.anular = anular;
  gastosNamespace.inicializarOffcanvasActual = inicializarOffcanvasActual;
  gastosNamespace.actualizarSelectResolucion = actualizarSelectResolucion;

  console.log(`${MOD} Modulo inicializado (AppGasto/AppGastos)`);

})(window, document);

