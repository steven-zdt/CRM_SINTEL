/**
 * asiento_editor.js - Feature Editor para AsientoContable v2.61
 * ⚠️ v3.5 Architecture: DOM Shield implemented (no name attributes in HTML)
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente del ciclo de vida del Offcanvas (abrir, recolectar JSON, guardar)
 * ⚠️ Error Boundary: Todo el manejo de errores (400, 422, 500) DEBE delegarse al UIManager y ErrorHandler
 * 
 * Dependencias globales requeridas:
 * - AsientoAPI (definido en asiento.api.js)
 * - CuentaAPI (definido en cuenta.api.js)
 * - UIManager (definido en ui-manager.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[asiento.editor]';
  const ERROR_CONTAINER_ID = '#error-container-asiento';
  let movimientoIndex = 0;
  let cuentasCache = null;

  /**
   * Carga las cuentas contables para el select de movimientos
   */
  async function loadCuentas() {
    if (cuentasCache) return cuentasCache;

    try {
      if (w.CuentaAPI && typeof w.CuentaAPI.lookup === 'function') {
        cuentasCache = await w.CuentaAPI.lookup();
        return cuentasCache;
      }
    } catch (err) {
      console.error(MOD, 'Error cargando cuentas:', err);
    }
    return [];
  }

  /**
   * Agrega una nueva fila de movimiento a la tabla
   */
  async function agregarMovimiento() {
    const tbody = d.querySelector('#tbody-movimientos');
    if (!tbody) return;

    const template = d.querySelector('#template-movimiento-row');
    if (!template) return;

    const clone = template.content.cloneNode(true);
    const row = clone.querySelector('tr');
    movimientoIndex++;
    row.setAttribute('data-movimiento-index', movimientoIndex);
    row.querySelector('.movimiento-orden').textContent = movimientoIndex;

    // Cargar cuentas en el select
    const selectCuenta = row.querySelector('.select-cuenta');
    if (selectCuenta) {
      const cuentas = await loadCuentas();
      cuentas.forEach(cuenta => {
        const option = d.createElement('option');
        option.value = cuenta.id;
        option.textContent = `${cuenta.codigo} - ${cuenta.nombre}`;
        selectCuenta.appendChild(option);
      });
    }

    // Event listener para eliminar movimiento
    const btnEliminar = row.querySelector('.btn-eliminar-movimiento');
    if (btnEliminar) {
      btnEliminar.addEventListener('click', () => {
        row.remove();
        actualizarTotales();
      });
    }

    // Event listeners para actualizar totales cuando cambian los valores
    const inputDebe = row.querySelector('.input-debe');
    const inputHaber = row.querySelector('.input-haber');
    
    if (inputDebe) {
      inputDebe.addEventListener('input', actualizarTotales);
    }
    if (inputHaber) {
      inputHaber.addEventListener('input', actualizarTotales);
    }

    tbody.appendChild(clone);
    actualizarTotales();
  }

  /**
   * Actualiza los totales de débito y crédito y verifica cuadratura
   */
  function actualizarTotales() {
    const tbody = d.querySelector('#tbody-movimientos');
    if (!tbody) return;

    let totalDebe = 0;
    let totalHaber = 0;

    tbody.querySelectorAll('tr').forEach((row, index) => {
      const debe = parseFloat(row.querySelector('.input-debe')?.value || 0);
      const haber = parseFloat(row.querySelector('.input-haber')?.value || 0);
      totalDebe += debe;
      totalHaber += haber;
      
      // Actualizar número de orden
      const ordenSpan = row.querySelector('.movimiento-orden');
      if (ordenSpan) {
        ordenSpan.textContent = index + 1;
      }
    });

    // Actualizar displays
    const totalDebeDisplay = d.querySelector('#total-debe-display');
    const totalHaberDisplay = d.querySelector('#total-haber-display');
    const resumenTotalDebe = d.querySelector('#resumen-total-debe');
    const resumenTotalHaber = d.querySelector('#resumen-total-haber');
    const resumenDiferencia = d.querySelector('#resumen-diferencia');
    const resumenStatus = d.querySelector('#resumen-status');
    const cuadraturaStatus = d.querySelector('#cuadratura-status');
    const cuadraturaDiferencia = d.querySelector('#cuadratura-diferencia');
    const rowCuadratura = d.querySelector('#row-cuadratura');
    const btnGuardar = d.querySelector('#btn-guardar-asiento-crear, #btn-guardar-asiento-editar');

    const diferencia = Math.abs(totalDebe - totalHaber);
    const formatter = new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });

    if (totalDebeDisplay) totalDebeDisplay.textContent = formatter.format(totalDebe);
    if (totalHaberDisplay) totalHaberDisplay.textContent = formatter.format(totalHaber);
    if (resumenTotalDebe) resumenTotalDebe.textContent = formatter.format(totalDebe);
    if (resumenTotalHaber) resumenTotalHaber.textContent = formatter.format(totalHaber);
    if (resumenDiferencia) resumenDiferencia.textContent = formatter.format(diferencia);
    
    if (diferencia < 0.01) {
      // Cuadrado
      if (resumenStatus) {
        resumenStatus.className = 'badge bg-success';
        resumenStatus.textContent = 'Cuadrado';
      }
      if (cuadraturaStatus) {
        cuadraturaStatus.innerHTML = '<i class="bi bi-check-circle text-success me-1"></i>Cuadrado';
      }
      if (rowCuadratura) rowCuadratura.classList.add('d-none');
      if (btnGuardar) btnGuardar.disabled = false;
    } else {
      // No cuadra
      if (resumenStatus) {
        resumenStatus.className = 'badge bg-danger';
        resumenStatus.textContent = 'No cuadra';
      }
      if (cuadraturaStatus) {
        cuadraturaStatus.innerHTML = '<i class="bi bi-x-circle text-danger me-1"></i>No cuadra';
      }
      if (cuadraturaDiferencia) {
        cuadraturaDiferencia.textContent = `Diferencia: ${formatter.format(diferencia)}`;
      }
      if (rowCuadratura) rowCuadratura.classList.remove('d-none');
      
      // ⚠️ v3.5: Permitir guardar aunque no cuadre si está en BORRADOR
      const estado = d.querySelector('#select-estado')?.value;
      if (estado === 'BORRADOR') {
        if (btnGuardar) btnGuardar.disabled = false;
      } else {
        if (btnGuardar) btnGuardar.disabled = true;
      }
    }
  }

  /**
   * Recolecta los datos del formulario y los convierte a objeto JSON
   * ⚠️ DOM Shield: Recolección manual dirigida
   */
  function collectFormData(formId) {
    const form = d.querySelector(formId);
    if (!form) {
      console.error(MOD, 'Formulario no encontrado:', formId);
      return null;
    }

    const data = {
      numero: d.querySelector('#input-numero')?.value?.trim() || null,
      fecha: d.querySelector('#input-fecha')?.value || null,
      estado: d.querySelector('#select-estado')?.value || 'BORRADOR',
      descripcion: d.querySelector('#input-descripcion')?.value?.trim() || '',
      tipo_comprobante: d.querySelector('#select-tipo-comprobante')?.value || null,
      numero_comprobante: d.querySelector('#input-numero-comprobante')?.value?.trim() || null
    };

    // Recoleccionar movimientos
    const movimientos = [];
    const tbody = d.querySelector('#tbody-movimientos');
    if (tbody) {
      tbody.querySelectorAll('tr').forEach(row => {
        const cuentaId = row.querySelector('.select-cuenta')?.value;
        const descripcion = row.querySelector('.input-descripcion-mov')?.value || '';
        const debe = parseFloat(row.querySelector('.input-debe')?.value || 0);
        const haber = parseFloat(row.querySelector('.input-haber')?.value || 0);
        
        const terceroNit = row.querySelector('.input-tercero-nit')?.value || null;
        const terceroRazonSocial = row.querySelector('.input-tercero-razon-social')?.value || null;

        if (cuentaId && (debe > 0 || haber > 0)) {
          movimientos.push({
            cuenta: parseInt(cuentaId),
            descripcion: descripcion ? descripcion.trim() : '',
            debe: parseFloat(debe.toFixed(2)),
            haber: parseFloat(haber.toFixed(2)),
            tercero_nit: terceroNit ? terceroNit.trim() : null,
            tercero_razon_social: terceroRazonSocial ? terceroRazonSocial.trim() : null
          });
        }
      });
    }

    data.movimientos = movimientos;
    return data;
  }

  /**
   * Cierra el offcanvas activo
   */
  function closeOffcanvas(offcanvasId) {
    const offcanvasEl = d.querySelector(offcanvasId);
    if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
      const offcanvas = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
      if (offcanvas) {
        offcanvas.hide();
      }
    }
  }

  /**
   * Maneja el guardado de un asiento (crear o actualizar)
   */
  async function handleSave(mode) {
    const formId = mode === 'create' ? '#form-asiento-crear' : '#form-asiento-editar';
    const offcanvasId = mode === 'create' ? '#offcanvas-asiento-crear' : '#offcanvas-asiento-editar';
    
    if (!w.AsientoAPI) {
      console.error(MOD, 'AsientoAPI no está disponible');
      return;
    }

    const data = collectFormData(formId);
    if (!data) return;

    try {
      let result;
      if (mode === 'create') {
        result = await w.AsientoAPI.create(data);
      } else {
        const id = d.querySelector('#input-id')?.value;
        if (!id) {
          console.error(MOD, 'ID de asiento no encontrado');
          return;
        }
        result = await w.AsientoAPI.update(parseInt(id), data);
      }

      // Éxito: Recargar tabla y cerrar offcanvas
      if (w.AsientoList && typeof w.AsientoList.reload === 'function') {
        w.AsientoList.reload();
      }

      closeOffcanvas(offcanvasId);

      if (w.SintelFeedback) {
        w.SintelFeedback.success(mode === 'create' ? 'Asiento creado correctamente' : 'Asiento actualizado correctamente');
      }
    } catch (error) {
      console.error(MOD, 'Error guardando asiento:', error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(error, MOD);
      }
    }
  }

  /**
   * Maneja la aprobación de un asiento
   */
  async function handleAprobar(id) {
    if (!id || !w.AsientoAPI) return;

    try {
      await w.AsientoAPI.aprobar(id);
      if (w.AsientoList && typeof w.AsientoList.reload === 'function') {
        w.AsientoList.reload();
      }
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Asiento aprobado correctamente');
      }
    } catch (error) {
      console.error(MOD, 'Error aprobando asiento:', error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(error, MOD);
      }
    }
  }

  /**
   * Maneja la eliminación de un asiento
   */
  async function handleDelete(id) {
    if (!id || !w.AsientoAPI) return;

    try {
      await w.AsientoAPI.delete(id);
      if (w.AsientoList && typeof w.AsientoList.reload === 'function') {
        w.AsientoList.reload();
      }
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Asiento eliminado correctamente');
      }
    } catch (error) {
      console.error(MOD, 'Error eliminando asiento:', error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(error, MOD);
      }
    }
  }

  /**
   * Event listeners
   */
  function attachEditorListeners() {
    d.addEventListener('click', (ev) => {
      const btnCrear = ev.target.closest('#btn-guardar-asiento-crear');
      if (btnCrear) {
        ev.preventDefault();
        handleSave('create');
      }

      const btnEditar = ev.target.closest('#btn-guardar-asiento-editar');
      if (btnEditar) {
        ev.preventDefault();
        handleSave('update');
      }

      const btnAgregar = ev.target.closest('#btn-agregar-movimiento');
      if (btnAgregar) {
        ev.preventDefault();
        agregarMovimiento();
      }
    });

    d.addEventListener('change', (ev) => {
      if (ev.target.id === 'select-estado') {
        actualizarTotales();
      }
    });
  }

  function init() {
    attachEditorListeners();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  w.AsientoEditor = Object.freeze({
    save: handleSave,
    delete: handleDelete,
    aprobar: handleAprobar,
    agregarMovimiento: agregarMovimiento,
    actualizarTotales: actualizarTotales
  });

})(window, document);
