/**
 * Módulo de Edición de Cotizaciones - cotizacion_editar.js
 * Maneja EXCLUSIVAMENTE la edición (PATCH) de cotizaciones existentes.
 * Completamente independiente de cotizacion_editor.js (creación).
 */
(function (w, d) {
  'use strict';

  const MOD = 'cotizacion-editar';

  // ─── Estado local del módulo ────────────────────────────────────────────────
  let _tables   = {};   // { equipos: TabulatorInstance, ... }
  let _uuid     = null; // UUID de la cotización en edición

  // Garantizar que el global de tablas exista (lo lee cotizacion_columns.js)
  if (!w.SintelCotizacionTables) w.SintelCotizacionTables = {};

  // ─── Utilidades ─────────────────────────────────────────────────────────────
  function notify(msg, type) {
    if (w.SintelFeedback && typeof w.SintelFeedback[type] === 'function') {
      w.SintelFeedback[type](msg);
    } else if (w.UIManager && typeof w.UIManager.showToast === 'function') {
      w.UIManager.showToast(msg, type === 'success' ? 'success' : 'error');
    } else {
      console[type === 'success' ? 'log' : 'error']('[' + MOD + ']', msg);
    }
  }

  function fmtMoney(v) {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency', currency: 'COP', minimumFractionDigits: 0
    }).format(v || 0);
  }

  // ─── Limpieza de estado ──────────────────────────────────────────────────────
  function resetState() {
    Object.keys(_tables).forEach(function (k) {
      try { if (_tables[k] && typeof _tables[k].destroy === 'function') _tables[k].destroy(); }
      catch (e) { /* silenciar */ }
      delete w.SintelCotizacionTables[k]; // limpiar global también
    });
    _tables = {};
    _uuid   = null;
    var editorDiv = d.getElementById('modal-cotizacion-editar');
    if (editorDiv) editorDiv.removeAttribute('data-init');
  }

  // ─── Inicialización de tablas Tabulator ─────────────────────────────────────
  function initTable(containerId, seccion) {
    var el = d.getElementById(containerId);
    if (!el || !w.getCotizacionColumns) return null;

    var columns = w.getCotizacionColumns(seccion, true);
    var table = new Tabulator(el, {
      data: [],
      columns: columns,
      layout: 'fitColumns',
      placeholder: 'Sin ítems. Use el botón + para agregar.',
      rowFormatter: function (row) {
        if (w.CotizacionEditorModule && w.CotizacionEditorModule.reindexarFilas) return;
      }
    });
    _tables[seccion] = table;
    w.SintelCotizacionTables[seccion] = table; // registrar en global para cotizacion_columns.js
    return table;
  }

  function initVisibleTables() {
    if (!_tables['equipos'] && !d.getElementById('section-equipos').classList.contains('d-none')) {
      initTable('grid-editor-equipos', 'equipos');
    }
    if (!_tables['materiales'] && !d.getElementById('section-materiales').classList.contains('d-none')) {
      initTable('grid-editor-materiales', 'materiales');
    }
    if (!_tables['servicios'] && !d.getElementById('section-servicios').classList.contains('d-none')) {
      initTable('grid-editor-servicios', 'servicios');
    }
  }

  // ─── Panel de totales ────────────────────────────────────────────────────────
  function recalcularTotales() {
    try {
      var subtotal = 0, ivaTotal = 0;

      Object.keys(_tables).forEach(function (k) {
        var t = _tables[k];
        if (!t) return;
        var section = d.getElementById('section-' + k);
        if (section && section.classList.contains('d-none')) return;

        t.getData().forEach(function (row) {
          subtotal += parseFloat(row.subtotal_linea) || 0;
          ivaTotal += parseFloat(row._valor_iva_interno) || 0;
        });
      });

      var switchAiu = d.getElementById('switch-activar-aiu');
      var aiuTotal  = 0;
      if (switchAiu && switchAiu.checked) {
        var admin = parseFloat(d.getElementById('input-aiu-admin')?.value) || 0;
        var impr  = parseFloat(d.getElementById('input-aiu-imprevistos')?.value) || 0;
        var util  = parseFloat(d.getElementById('input-aiu-utilidad')?.value) || 0;
        aiuTotal  = subtotal * (admin + impr + util) / 100;
      }

      var total = subtotal + ivaTotal + aiuTotal;

      var elSub   = d.getElementById('total-subtotal');
      var elIva   = d.getElementById('total-iva');
      var elAiu   = d.getElementById('total-aiu');
      var elFinal = d.getElementById('total-final');
      var elAiuC  = d.getElementById('contenedor-total-aiu');

      if (elSub)   elSub.textContent   = fmtMoney(subtotal);
      if (elIva)   elIva.textContent   = fmtMoney(ivaTotal);
      if (elFinal) elFinal.textContent = fmtMoney(total);
      if (elAiuC)  elAiuC.style.display = aiuTotal > 0 ? 'block' : 'none';
      if (elAiu)   elAiu.textContent   = fmtMoney(aiuTotal);
    } catch (e) {
      console.error('[' + MOD + '] Error recalculando totales:', e);
    }
  }

  // ─── Cargar datos del emisor ─────────────────────────────────────────────────
  async function cargarEmisor() {
    try {
      if (!w.cotizacionesAPI || typeof w.cotizacionesAPI.getEmpresa !== 'function') return;
      var res = await w.cotizacionesAPI.getEmpresa();
      if (!res || !res.ok) return;
      var emp = res.data;
      var elNombre = d.getElementById('emisor-nombre');
      var elNit    = d.getElementById('emisor-nit');
      if (elNombre) elNombre.textContent = emp.nombre || emp.razon_social || 'Empresa';
      if (elNit)    elNit.textContent    = emp.nit || '—';
    } catch (e) { /* silenciar */ }
  }

  // ─── Cargar cotización existente ─────────────────────────────────────────────
  async function cargarCotizacion(uuid) {
    if (!w.cotizacionesAPI) {
      notify('API de cotizaciones no disponible', 'error');
      return;
    }

    var selCliente = d.getElementById('editor-select-cliente');
    var selPerfil  = d.getElementById('editor-select-perfil');

    // 1. Cargar catálogos y emisor en paralelo
    var promises = [cargarEmisor()];
    if (w.CotizacionesHelpers) {
      if (selCliente) promises.push(w.CotizacionesHelpers.cargarClientesEnSelect(selCliente));
      if (selPerfil)  promises.push(w.CotizacionesHelpers.cargarPerfilesEnSelect(selPerfil));
    }
    await Promise.allSettled(promises);

    // 2. Obtener datos de la cotización
    var res = await w.cotizacionesAPI.get(uuid);
    if (!res || !res.ok || !res.data) {
      notify('No se pudo cargar la cotización', 'error');
      return;
    }

    var cot = res.data;
    console.log('[' + MOD + '] Cotización cargada:', cot);

    // 3. Poblar cabecera
    if (selCliente && cot.cliente) {
      var clienteId = typeof cot.cliente === 'object' ? cot.cliente.id : cot.cliente;
      selCliente.value = String(clienteId);
      selCliente.dispatchEvent(new Event('change', { bubbles: true }));
    }
    if (selPerfil && cot.configuracion) {
      var configId = typeof cot.configuracion === 'object' ? cot.configuracion.id : cot.configuracion;
      selPerfil.value = String(configId);
      selPerfil.dispatchEvent(new Event('change', { bubbles: true }));
    }
    if (cot.fecha_emision) {
      var inputFecha = d.getElementById('input-fecha-emision');
      if (inputFecha) {
        var fecha = new Date(cot.fecha_emision);
        if (!isNaN(fecha)) inputFecha.value = fecha.toISOString().split('T')[0];
      }
    }
    var selTipo = d.getElementById('editor-select-tipo-cotizacion');
    if (selTipo && cot.tipo_cotizacion) selTipo.value = cot.tipo_cotizacion;

    // 4. Poblar financieros
    var inputIva = d.getElementById('input-iva-porcentaje');
    if (inputIva && cot.iva_porcentaje != null) inputIva.value = parseFloat(cot.iva_porcentaje).toFixed(2);

    var aiuAdmin = parseFloat(cot.porcentaje_aiu_admin) || 0;
    var aiuImpr  = parseFloat(cot.porcentaje_aiu_imprevistos) || 0;
    var aiuUtil  = parseFloat(cot.porcentaje_aiu_utilidad) || 0;
    var tieneAiu = aiuAdmin > 0 || aiuImpr > 0 || aiuUtil > 0;

    var switchAiu    = d.getElementById('switch-activar-aiu');
    var containerAiu = d.getElementById('container-aiu-fields');
    if (switchAiu) switchAiu.checked = tieneAiu;
    if (containerAiu) containerAiu.classList.toggle('d-none', !tieneAiu);

    var inAdmin = d.getElementById('input-aiu-admin');
    var inImpr  = d.getElementById('input-aiu-imprevistos');
    var inUtil  = d.getElementById('input-aiu-utilidad');
    if (inAdmin) inAdmin.value = aiuAdmin.toFixed(2);
    if (inImpr)  inImpr.value  = aiuImpr.toFixed(2);
    if (inUtil)  inUtil.value  = aiuUtil.toFixed(2);

    // 5. Distribuir ítems por sección y activar módulos correspondientes
    var items       = cot.items || [];
    var equipos     = items.filter(function (i) { return i.tipo_item === 'PRODUCTO'; });
    var materiales  = items.filter(function (i) { return i.tipo_item === 'MATERIAL'; });
    var servicios   = items.filter(function (i) { return i.tipo_item === 'SERVICIO'; });

    function activarSeccion(id, switchId, tieneItems) {
      if (!tieneItems) return;
      var sec = d.getElementById(id);
      var sw  = d.getElementById(switchId);
      if (sec) sec.classList.remove('d-none');
      if (sw)  sw.checked = true;
    }

    activarSeccion('section-equipos',    'switch-equipos',    equipos.length > 0);
    activarSeccion('section-materiales', 'switch-materiales', materiales.length > 0);
    activarSeccion('section-servicios',  'switch-servicios',  servicios.length > 0);

    initVisibleTables();

    function mapItem(item) {
      return {
        descripcion:        item.descripcion || '',
        cantidad:           parseFloat(item.cantidad) || 0,
        costo_unitario:     parseFloat(item.costo_unitario) || 0,
        precio_unitario_venta: parseFloat(item.precio_unitario_venta ?? item.costo_unitario) || 0,
        utilidad_porcentaje: parseFloat(item.porcentaje_utilidad) || 0,
        porcentaje_utilidad: parseFloat(item.porcentaje_utilidad) || 0,
        subtotal_linea:     parseFloat(item.subtotal_linea) || 0,
        iva_porcentaje:     parseFloat(item.iva_porcentaje ?? 19) || 19,
        marca:              item.marca || '',
        referencia:         item.referencia || '',
        unidad:             item.unidad || 'UND',
        nro_item:           item.orden || 0
      };
    }

    // 6. Cargar datos en tablas con delay para que Tabulator esté inicializado
    setTimeout(function () {
      if (equipos.length > 0 && _tables['equipos']) {
        _tables['equipos'].setData(equipos.map(mapItem));
      }
      if (materiales.length > 0 && _tables['materiales']) {
        _tables['materiales'].setData(materiales.map(mapItem));
      }
      if (servicios.length > 0 && _tables['servicios']) {
        _tables['servicios'].setData(servicios.map(mapItem));
      }
      setTimeout(recalcularTotales, 150);
    }, 300);
  }

  // ─── Construir payload PATCH ─────────────────────────────────────────────────
  function buildPayload() {
    var selCliente = d.getElementById('editor-select-cliente');
    var selPerfil  = d.getElementById('editor-select-perfil');
    var inputFecha = d.getElementById('input-fecha-emision');
    var selTipo    = d.getElementById('editor-select-tipo-cotizacion');
    var inputIva   = d.getElementById('input-iva-porcentaje');

    var clienteId   = selCliente  ? parseInt(selCliente.value, 10)  : null;
    var configId    = selPerfil   ? parseInt(selPerfil.value, 10)   : null;
    var fechaEmision = inputFecha ? inputFecha.value || null        : null;
    var tipoCot     = selTipo     ? selTipo.value                   : 'MIXTO';

    var ivaRaw = inputIva ? parseFloat(inputIva.value) : NaN;
    var iva    = isNaN(ivaRaw) ? 19.00 : ivaRaw;

    var switchAiu = d.getElementById('switch-activar-aiu');
    var aiuActivo = switchAiu && switchAiu.checked;

    function aiuVal(id) {
      if (!aiuActivo) return 0;
      var el = d.getElementById(id);
      var v  = el ? parseFloat(el.value) : NaN;
      return isNaN(v) ? 0 : v;
    }

    // Recoger ítems de tablas activas
    var items = [];
    var seccionesMap = {
      equipos:    { section: '#section-equipos',    tipo: 'PRODUCTO' },
      materiales: { section: '#section-materiales', tipo: 'MATERIAL' },
      servicios:  { section: '#section-servicios',  tipo: 'SERVICIO'  }
    };

    Object.keys(_tables).forEach(function (key) {
      var cfg  = seccionesMap[key];
      var sec  = cfg ? d.querySelector(cfg.section) : null;
      if (sec && sec.classList.contains('d-none')) return;

      var rows = _tables[key] ? _tables[key].getData() : [];
      rows.forEach(function (row, idx) {
        items.push({
          descripcion:        (row.descripcion || '').trim() || 'Sin descripción',
          cantidad:           parseFloat(row.cantidad) || 0,
          costo_unitario:     parseFloat(row.costo_unitario) || 0,
          porcentaje_utilidad: parseFloat(row.utilidad_porcentaje ?? row.porcentaje_utilidad) || 0,
          tipo_item:          cfg ? cfg.tipo : 'PRODUCTO',
          marca:              row.marca || '',
          referencia:         row.referencia || '',
          unidad:             row.unidad || 'UND',
          orden:              row.nro_item || idx
        });
      });
    });

    return {
      cliente:                 clienteId,
      configuracion:           configId,
      fecha_emision:           fechaEmision,
      tipo_cotizacion:         tipoCot,
      iva_porcentaje:          iva,
      porcentaje_aiu_admin:    aiuVal('input-aiu-admin'),
      porcentaje_aiu_imprevistos: aiuVal('input-aiu-imprevistos'),
      porcentaje_aiu_utilidad: aiuVal('input-aiu-utilidad'),
      items:                   items
    };
  }

  // ─── Guardar (PATCH) ─────────────────────────────────────────────────────────
  async function guardar() {
    if (!_uuid) {
      notify('UUID de cotización no encontrado', 'error');
      return;
    }

    var payload = buildPayload();

    // Validaciones básicas
    if (!payload.cliente || isNaN(payload.cliente)) {
      notify('Debe seleccionar un cliente válido', 'error');
      return;
    }
    if (!payload.configuracion || isNaN(payload.configuracion)) {
      notify('Debe seleccionar un perfil de configuración', 'error');
      return;
    }

    console.log('[' + MOD + '] PATCH payload:', payload);

    var url = '/api/v1/core/v1/cotizaciones/' + _uuid + '/';
    try {
      var res = await w.http('PATCH', url, payload);

      if (res && res.ok) {
        notify('Cotización actualizada exitosamente', 'success');

        var offcanvasEl = d.getElementById('offcanvas-container');
        if (offcanvasEl) {
          var bsOffcanvas = w.bootstrap && w.bootstrap.Offcanvas
            ? w.bootstrap.Offcanvas.getInstance(offcanvasEl)
            : null;

          if (bsOffcanvas) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', function _done() {
              offcanvasEl.removeEventListener('hidden.bs.offcanvas', _done);
              resetState();
              offcanvasEl.innerHTML = '';
              if (w.cotizacionesPage && typeof w.cotizacionesPage.refresh === 'function') {
                w.cotizacionesPage.refresh();
              }
            });
            bsOffcanvas.hide();
          } else {
            resetState();
            offcanvasEl.innerHTML = '';
            if (w.cotizacionesPage && typeof w.cotizacionesPage.refresh === 'function') {
              w.cotizacionesPage.refresh();
            }
          }
        }
      } else {
        console.error('[' + MOD + '] Error 400 respuesta completa:', res.status, JSON.stringify(res.data, null, 2));
        var rawDetail = res && res.data ? (res.data.detail || res.data.error || res.data) : null;
        var detailStr;
        if (typeof rawDetail === 'string') {
          detailStr = rawDetail;
        } else if (rawDetail && typeof rawDetail === 'object') {
          // Extraer el primer mensaje de error de los campos
          var msgs = [];
          function extractMsgs(obj, prefix) {
            Object.keys(obj).forEach(function (k) {
              var val = obj[k];
              var label = prefix ? prefix + '.' + k : k;
              if (Array.isArray(val)) {
                msgs.push(label + ': ' + val.join(', '));
              } else if (val && typeof val === 'object') {
                extractMsgs(val, label);
              } else {
                msgs.push(label + ': ' + val);
              }
            });
          }
          extractMsgs(rawDetail, '');
          detailStr = msgs.length ? msgs.join(' | ') : JSON.stringify(rawDetail);
        } else {
          detailStr = 'Error al guardar la cotización';
        }
        notify(detailStr, 'error');
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(res, '[' + MOD + ']');
        }
      }
    } catch (e) {
      console.error('[' + MOD + '] Error en guardar:', e);
      notify(e.message || 'Error inesperado al guardar', 'error');
    }
  }

  // ─── Inicialización principal ────────────────────────────────────────────────
  async function init() {
    var editorDiv = d.getElementById('modal-cotizacion-editar');
    if (!editorDiv) {
      console.warn('[' + MOD + '] #modal-cotizacion-editar no encontrado');
      return;
    }

    // Anti-doble ejecución
    if (editorDiv.getAttribute('data-init') === 'true') return;
    editorDiv.setAttribute('data-init', 'true');

    _uuid = editorDiv.getAttribute('data-cotizacion-uuid');
    if (!_uuid || _uuid === '' || _uuid === 'None') {
      notify('UUID de cotización inválido', 'error');
      return;
    }
    console.log('[' + MOD + '] Inicializando edición para UUID:', _uuid);

    // Configurar switch AIU
    var switchAiu = d.getElementById('switch-activar-aiu');
    if (switchAiu) {
      switchAiu.addEventListener('change', function () {
        var container = d.getElementById('container-aiu-fields');
        if (container) container.classList.toggle('d-none', !switchAiu.checked);
        recalcularTotales();
      });
    }

    // Configurar switches de módulos
    d.querySelectorAll('.dna-switch').forEach(function (sw) {
      sw.addEventListener('change', function () {
        var targetSel = sw.getAttribute('data-target');
        var seccion   = sw.getAttribute('data-seccion');
        var target    = targetSel ? d.querySelector(targetSel) : null;
        if (target) target.classList.toggle('d-none', !sw.checked);
        if (sw.checked && seccion && !_tables[seccion]) {
          initTable('grid-editor-' + seccion, seccion);
        }
        recalcularTotales();
      });
    });

    // Configurar botón guardar
    var btnGuardar = d.getElementById('btn-guardar-editar');
    if (btnGuardar) {
      var newBtn = btnGuardar.cloneNode(true);
      btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);
      newBtn.addEventListener('click', guardar);
    }

    // Configurar inputs financieros para recalcular totales
    ['input-iva-porcentaje', 'input-aiu-admin', 'input-aiu-imprevistos', 'input-aiu-utilidad']
      .forEach(function (id) {
        var el = d.getElementById(id);
        if (el) el.addEventListener('input', recalcularTotales);
      });

    // Cargar cotización existente
    await cargarCotizacion(_uuid);
  }

  // ─── Exponer módulo globalmente ──────────────────────────────────────────────
  w.CotizacionEditarModule = {
    init:              init,
    resetState:        resetState,
    recalcularTotales: recalcularTotales,
    getTables:         function () { return _tables; }
  };

  // ─── Listeners de ciclo de vida ──────────────────────────────────────────────

  // HTMX: se disparará cuando el partial cargue vía hx-get
  d.body.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'offcanvas-container') {
      var editorDiv = d.getElementById('modal-cotizacion-editar');
      if (editorDiv) {
        console.log('[' + MOD + '] HTMX swap detectado → init()');
        resetState();
        init();
      }
    }
  });

  // Fallback: cuando el offcanvas ya está visible pero init aún no corrió
  d.body.addEventListener('shown.bs.offcanvas', function (e) {
    if (e.target && e.target.id === 'offcanvas-container') {
      var editorDiv = d.getElementById('modal-cotizacion-editar');
      if (editorDiv && !editorDiv.getAttribute('data-init')) {
        console.log('[' + MOD + '] shown.bs.offcanvas fallback → init()');
        init();
      }
    }
  });

}(window, document));
