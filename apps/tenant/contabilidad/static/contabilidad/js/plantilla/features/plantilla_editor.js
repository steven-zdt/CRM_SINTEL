/**
 * plantilla_editor.js - Editor de PlantillaContable + LineaPlantilla v3.16.2
 * Feature-Sliced Design: ciclo de vida del offcanvas, recoleccion de datos,
 * gestion inline de LineaPlantilla.
 * Dependencias: PlantillaAPI, UIManager, PlantillaList
 */
(function (w, d) {
  'use strict';

  const MOD = '[plantilla.editor]';
  const CONTAINER = '#offcanvas-container-plantilla';
  const ERR_SEL = '#error-container-plantilla';
  const API_CUENTAS = '/api/v1/contabilidad/cuentas-contables/?solo_auxiliares=true&search=';

  // ----------------------------------------------------------------- helpers
  function closeOffcanvas(id) {
    const el = d.getElementById(id);
    if (!el) return;
    const inst = w.bootstrap?.Offcanvas?.getInstance(el);
    if (inst) inst.hide();
  }

  function showError(msg) {
    if (w.UIManager?.handleError) {
      w.UIManager.handleError({ ok: false, status: 400, data: { detail: msg } }, MOD, { errorContainerSelector: ERR_SEL });
    } else if (w.SintelFeedback) {
      w.SintelFeedback.error(msg);
    }
  }

  // Muestra el error real de la API si tiene status/data, fallback a msg generico
  function showApiError(err, fallbackMsg) {
    if (err && typeof err.status !== 'undefined' && w.UIManager?.handleError) {
      w.UIManager.handleError(err, MOD, { errorContainerSelector: ERR_SEL });
    } else {
      showError(fallbackMsg);
    }
  }

  function showSuccess(msg) {
    if (w.SintelFeedback) w.SintelFeedback.success(msg);
  }

  function reloadList() {
    if (w.PlantillaList?.reload) w.PlantillaList.reload();
  }

  // ------------------------------------------------ autocomplete de cuentas
  let _cuentasCache = {};

  async function buscarCuentas(q) {
    if (!q || q.length < 2) return [];
    const key = q.toLowerCase();
    if (_cuentasCache[key]) return _cuentasCache[key];
    try {
      const res = await w.Sintel.Core.Http.request('GET', API_CUENTAS + encodeURIComponent(q) + '&page_size=20');
      if (!res.ok) return [];
      const items = (res.data.results || res.data || []).map(function (c) {
        return { id: c.id, codigo: c.codigo, nombre: c.nombre };
      });
      _cuentasCache[key] = items;
      return items;
    } catch { return []; }
  }

  // Inicializa autocomplete sobre un <input> de busqueda de cuenta
  function initCuentaAutocomplete(inputEl, hiddenIdEl, hiddenCodEl, hiddenNomEl) {
    if (!inputEl) return;

    let dropdown = null;

    function destroyDropdown() {
      if (dropdown) { dropdown.remove(); dropdown = null; }
    }

    inputEl.addEventListener('input', async function () {
      destroyDropdown();
      const q = inputEl.value.trim();
      if (q.length < 2) return;
      const cuentas = await buscarCuentas(q);
      if (!cuentas.length) return;

      dropdown = d.createElement('ul');
      dropdown.className = 'list-group position-absolute z-3 shadow-sm';
      dropdown.style.cssText = 'width:100%;max-height:200px;overflow-y:auto;top:100%;left:0;';

      cuentas.forEach(function (c) {
        const li = d.createElement('li');
        li.className = 'list-group-item list-group-item-action py-1 small';
        li.textContent = c.codigo + ' - ' + c.nombre;
        li.addEventListener('click', function () {
          inputEl.value = c.codigo + ' - ' + c.nombre;
          if (hiddenIdEl) hiddenIdEl.value = c.id;
          if (hiddenCodEl) hiddenCodEl.value = c.codigo;
          if (hiddenNomEl) hiddenNomEl.value = c.nombre;
          destroyDropdown();
        });
        dropdown.appendChild(li);
      });

      const wrapper = inputEl.closest('.cuenta-autocomplete-wrapper');
      if (wrapper) wrapper.appendChild(dropdown);
    });

    inputEl.addEventListener('blur', function () {
      setTimeout(destroyDropdown, 200);
    });
  }

  // -------------------------------------------- formulario PlantillaContable
  function collectPlantillaData(formId) {
    const form = d.querySelector(formId);
    if (!form) return null;
    return {
      nombre:           form.querySelector('[name="nombre"]')?.value?.trim() || null,
      tipo_transaccion: form.querySelector('[name="tipo_transaccion"]')?.value || null,
      activo:           form.querySelector('[name="activo"]')?.checked !== false,
    };
  }

  // Valida que todas las cuentas en la tabla de lineas sean nivel 6 (6 digitos NIIF)
  function _validarCuentasNivel6() {
    const tbody = d.querySelector('#tbody-lineas-plantilla');
    if (!tbody) return true;
    const codigos = [];
    tbody.querySelectorAll('td code').forEach(function (el) {
      const cod = (el.textContent || '').trim();
      if (cod && cod !== '-') codigos.push(cod);
    });
    if (!codigos.length) return true;
    const noAuxiliares = codigos.filter(function (cod) {
      return cod.length !== 6 || !/^\d{6}$/.test(cod);
    });
    if (noAuxiliares.length > 0) {
      showError(
        'NIIF PYMES: Todas las cuentas de la plantilla deben ser auxiliares (Nivel 6 - 6 digitos). '
        + 'Cuentas no validas: ' + noAuxiliares.join(', ')
      );
      return false;
    }
    return true;
  }

  async function handleSave(mode) {
    const formId     = mode === 'create' ? '#form-plantilla-crear' : '#form-plantilla-editar';
    const offcanvasId = mode === 'create' ? 'offcanvas-plantilla-crear' : 'offcanvas-plantilla-editar';
    if (!w.PlantillaAPI) { showError('PlantillaAPI no disponible'); return; }

    if (mode === 'update' && !_validarCuentasNivel6()) return;

    const data = collectPlantillaData(formId);
    if (!data) return;

    try {
      if (mode === 'create') {
        await w.PlantillaAPI.create(data);
        showSuccess('Plantilla contable creada');
      } else {
        const uuid = d.querySelector(formId + ' [name="uuid"]')?.value;
        if (!uuid) { showError('UUID no encontrado'); return; }
        await w.PlantillaAPI.update(uuid, data);
        showSuccess('Plantilla actualizada');
      }
      closeOffcanvas(offcanvasId);
      reloadList();
    } catch (err) {
      console.error(MOD, err);
      showApiError(err, 'Error al guardar la plantilla. Revise los campos e intente de nuevo.');
    }
  }

  async function handleDelete(uuid) {
    if (!uuid || !w.PlantillaAPI) return;
    try {
      await w.PlantillaAPI.destroy(uuid);
      showSuccess('Plantilla eliminada');
      reloadList();
    } catch (err) {
      console.error(MOD, err);
      showError('No se pudo eliminar la plantilla.');
    }
  }

  // ----------------------------------------------- gestion inline de Lineas
  function buildLineaRow(linea, uuid, rowIdx) {
    // Fila para tabla de lineas (en edicion inline del offcanvas)
    const naturalezaBadge = linea.naturaleza === 'DEBE'
      ? '<span class="badge bg-danger">DEBE</span>'
      : '<span class="badge bg-success">HABER</span>';

    const origenes = {
      SALDO_BASE: 'Base/Subtotal', IVA_GENERADO: 'IVA Generado',
      IVA_DESCONTABLE: 'IVA Descontable', RETEFUENTE: 'Retefuente',
      RETEICA: 'ReteICA', RETEIVA: 'ReteIVA', TOTAL_DOCUMENTO: 'Total Neto',
    };

    return [
      '<tr data-linea-id="' + (linea.id || '') + '" data-idx="' + rowIdx + '">',
      '  <td class="align-middle">' + linea.orden + '</td>',
      '  <td class="align-middle">' + naturalezaBadge + '</td>',
      '  <td class="align-middle small">' + (origenes[linea.origen_valor] || linea.origen_valor) + '</td>',
      '  <td class="align-middle small"><code>' + (linea.cuenta_codigo || '-') + '</code><br><span class="text-muted">' + (linea.cuenta_nombre || '') + '</span></td>',
      '  <td class="align-middle text-end">' + parseFloat(linea.porcentaje_aplicar || 100).toFixed(0) + '%</td>',
      '  <td class="align-middle">',
      '    <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-linea" data-uuid="' + uuid + '" data-linea-id="' + linea.id + '" title="Eliminar linea"><i class="bi bi-x"></i></button>',
      '  </td>',
      '</tr>',
    ].join('');
  }

  async function refreshLineasTable(uuid, tbodySel) {
    const tbody = d.querySelector(tbodySel);
    if (!tbody) return;
    try {
      const data = await w.PlantillaAPI.retrieve(uuid);
      const lineas = data.lineas || [];
      tbody.innerHTML = lineas.length
        ? lineas.map(function (l, i) { return buildLineaRow(l, uuid, i + 1); }).join('')
        : '<tr><td colspan="6" class="text-center text-muted py-3">Sin lineas configuradas</td></tr>';
    } catch (err) {
      console.error(MOD, 'refreshLineasTable:', err);
    }
  }

  async function handleAgregarLinea(uuid, formSel, tbodySel) {
    const form = d.querySelector(formSel);
    if (!form || !uuid) return;

    const cuentaId = form.querySelector('[name="linea_cuenta_id"]')?.value;
    if (!cuentaId) { showError('Seleccione una cuenta contable para la linea'); return; }

    const payload = {
      cuenta_contable:   cuentaId,
      naturaleza:        form.querySelector('[name="linea_naturaleza"]')?.value || 'DEBE',
      origen_valor:      form.querySelector('[name="linea_origen_valor"]')?.value || 'SALDO_BASE',
      porcentaje_aplicar: form.querySelector('[name="linea_porcentaje"]')?.value || '100.00',
      orden:             form.querySelector('[name="linea_orden"]')?.value || '1',
      descripcion:       form.querySelector('[name="linea_descripcion"]')?.value?.trim() || '',
    };

    try {
      await w.PlantillaAPI.agregarLinea(uuid, payload);
      showSuccess('Linea agregada');
      // Limpiar campos del formulario de linea
      const busquedaInput = d.getElementById('linea-cuenta-busqueda');
      if (busquedaInput) busquedaInput.value = '';
      const hId  = form.querySelector('[name="linea_cuenta_id"]');
      const hCod = form.querySelector('[name="linea_cuenta_codigo"]');
      const hNom = form.querySelector('[name="linea_cuenta_nombre"]');
      if (hId)  hId.value  = '';
      if (hCod) hCod.value = '';
      if (hNom) hNom.value = '';
      const porcInput = form.querySelector('[name="linea_porcentaje"]');
      if (porcInput) porcInput.value = '100';
      const descInput = form.querySelector('[name="linea_descripcion"]');
      if (descInput) descInput.value = '';
      // Refrescar tabla y auto-incrementar orden
      await refreshLineasTable(uuid, tbodySel);
      const tbody = d.querySelector(tbodySel);
      const ordenInput = form.querySelector('[name="linea_orden"]');
      if (ordenInput && tbody) {
        ordenInput.value = tbody.querySelectorAll('tr[data-linea-id]').length + 1;
      }
    } catch (err) {
      console.error(MOD, 'handleAgregarLinea:', err);
      showApiError(err, 'Error al agregar la linea.');
    }
  }

  async function handleEliminarLinea(uuid, lineaId, tbodySel) {
    if (!confirm('Eliminar esta linea?')) return;
    try {
      await w.PlantillaAPI.eliminarLinea(uuid, lineaId);
      showSuccess('Linea eliminada');
      await refreshLineasTable(uuid, tbodySel);
    } catch (err) {
      console.error(MOD, 'handleEliminarLinea:', err);
      showApiError(err, 'No se pudo eliminar la linea.');
    }
  }

  // ------------------------------------------------------ event delegation
  function attachEditorListeners() {
    // Guardar crear
    d.addEventListener('click', function (ev) {
      if (ev.target.closest('#btn-guardar-plantilla-crear')) {
        ev.preventDefault(); handleSave('create');
      }
    });

    // Guardar editar
    d.addEventListener('click', function (ev) {
      if (ev.target.closest('#btn-guardar-plantilla-editar')) {
        ev.preventDefault(); handleSave('update');
      }
    });

    // Agregar linea (en offcanvas editar)
    d.addEventListener('click', function (ev) {
      const btn = ev.target.closest('#btn-agregar-linea-plantilla');
      if (!btn) return;
      ev.preventDefault();
      const uuid = btn.dataset.uuid;
      handleAgregarLinea(uuid, '#form-nueva-linea-plantilla', '#tbody-lineas-plantilla');
    });

    // Eliminar linea
    d.addEventListener('click', function (ev) {
      const btn = ev.target.closest('.btn-eliminar-linea');
      if (!btn) return;
      ev.preventDefault();
      handleEliminarLinea(btn.dataset.uuid, btn.dataset.lineaId, '#tbody-lineas-plantilla');
    });

    // Inicializar autocomplete cuando se abra el offcanvas
    d.addEventListener('shown.bs.offcanvas', function (ev) {
      if (ev.target.id === 'offcanvas-plantilla-crear' || ev.target.id === 'offcanvas-plantilla-editar') {
        const input  = ev.target.querySelector('#linea-cuenta-busqueda');
        const hId    = ev.target.querySelector('[name="linea_cuenta_id"]');
        const hCod   = ev.target.querySelector('[name="linea_cuenta_codigo"]');
        const hNom   = ev.target.querySelector('[name="linea_cuenta_nombre"]');
        initCuentaAutocomplete(input, hId, hCod, hNom);
      }
    });
  }

  function init() {
    // Guard: attachEditorListeners() registra listeners delegados en `document`
    // — sin este guard, cada recarga HTMX del modulo "plantilla" vuelve a
    // ejecutar este script y duplica los listeners globales (FE-A1/A2).
    if (d.body.dataset.plantillaEditorInitialized) return;
    d.body.dataset.plantillaEditorInitialized = 'true';

    attachEditorListeners();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  w.PlantillaEditor = Object.freeze({
    save:    handleSave,
    delete:  handleDelete,
    closeOffcanvas: closeOffcanvas,
    refreshLineas: refreshLineasTable,
  });
})(window, document);
