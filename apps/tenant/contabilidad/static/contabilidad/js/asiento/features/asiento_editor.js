/**
 * asiento_editor.js - Feature Editor para AsientoContable v2.60
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente del ciclo de vida del Offcanvas (abrir, recolectar FormData, guardar)
 * ⚠️ Error Boundary: Todo el manejo de errores (400, 422, 500) DEBE delegarse al UIManager y error_injector.js
 * ⚠️ PROHIBIDO: Uso de alert() o manejo manual de errores
 * 
 * Dependencias globales requeridas:
 * - AsientoAPI (definido en asiento.api.js)
 * - CuentaAPI (definido en cuenta.api.js) - Para cargar cuentas en select de movimientos
 * - UIManager (definido en ui-manager.js)
 * - AsientoList (definido en asiento_list.js) - Para refrescar tabla después de guardar
 */
(function (w, d) {
  'use strict';

  const MOD = '[asiento.editor]';
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-asiento';
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
      if (btnGuardar) btnGuardar.disabled = true;
    }
  }

  /**
   * Recolecta los datos del formulario y los convierte a objeto JSON
   * ⚠️ v2.60: El backend obtiene automáticamente la empresa del tenant (singleton)
   */
  function collectFormData(formId) {
    const form = d.querySelector(formId);
    if (!form) {
      console.error(MOD, 'Formulario no encontrado:', formId);
      return null;
    }

    const formData = new FormData(form);
    const data = {};
    
    // Datos básicos del asiento
    for (const [key, value] of formData.entries()) {
      if (key.startsWith('movimientos[')) continue; // Movimientos se procesan aparte
      if (key === 'id') continue; // Ignorar ID en creación
      if (key === 'empresa') continue; // ⚠️ v2.60: El backend obtiene la empresa automáticamente
      
      // Normalizar valores según tipo de campo
      if (key === 'fecha') {
        // Fecha: mantener formato YYYY-MM-DD
        data[key] = value || null;
      } else if (key === 'estado') {
        // Estado: mantener valor tal cual
        data[key] = value || 'BORRADOR';
      } else if (key === 'numero') {
        // Número: trim y validar (opcional, se genera automáticamente si está vacío)
        data[key] = value ? value.trim() : null;
      } else if (key === 'descripcion') {
        // Descripción: trim
        data[key] = value ? value.trim() : '';
      } else {
        data[key] = value || null;
      }
    }

    // Recolectar movimientos
    const movimientos = [];
    const tbody = d.querySelector('#tbody-movimientos');
    if (tbody) {
      tbody.querySelectorAll('tr').forEach(row => {
        const cuentaId = row.querySelector('.select-cuenta')?.value;
        const descripcion = row.querySelector('input[name*="descripcion"]')?.value || '';
        const debe = parseFloat(row.querySelector('.input-debe')?.value || 0);
        const haber = parseFloat(row.querySelector('.input-haber')?.value || 0);

        if (cuentaId && (debe > 0 || haber > 0)) {
          movimientos.push({
            cuenta: parseInt(cuentaId),
            descripcion: descripcion ? descripcion.trim() : '',
            debe: parseFloat(debe.toFixed(2)), // Normalizar a 2 decimales
            haber: parseFloat(haber.toFixed(2)) // Normalizar a 2 decimales
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
   * ⚠️ Error Boundary: Errores delegados a UIManager
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

    // Validar que tenga movimientos
    if (!data.movimientos || data.movimientos.length === 0) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: 422,
            responseText: JSON.stringify({
              error: 'El asiento debe tener al menos un movimiento contable.',
              missing_fields: ['movimientos']
            })
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      }
      return;
    }

    try {
      let result;
      if (mode === 'create') {
        result = await w.AsientoAPI.create(data);
      } else {
        const id = d.querySelector('#input-id')?.value;
        if (!id) {
          console.error(MOD, 'ID de asiento no encontrado para actualización');
          return;
        }
        result = await w.AsientoAPI.update(parseInt(id), data);
      }

      // Éxito: Recargar tabla y cerrar offcanvas
      if (w.AsientoList && typeof w.AsientoList.reload === 'function') {
        w.AsientoList.reload();
      }

      closeOffcanvas(offcanvasId);

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success(mode === 'create' ? 'Asiento creado correctamente' : 'Asiento actualizado correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a error_injector.js o UIManager
      console.error(MOD, 'Error guardando asiento:', error);
      
      // ⚠️ v2.60: Manejo estructurado de errores de DRF (ValidationError)
      // El error lanzado por asiento.api.js tiene: status, data, response
      if (error && typeof error === 'object' && 'status' in error && 'data' in error) {
        // Error estructurado de http.js (422 con detalles de cuadratura)
        // Construir un objeto XHR simulado para ErrorHandler.show()
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          const mockXHR = {
            status: error.status,
            statusText: error.status === 422 ? 'Unprocessable Entity' : 'Error',
            response: JSON.stringify(error.data),
            responseText: JSON.stringify(error.data)
          };
          w.ErrorHandler.show(mockXHR);
        } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          const errorDetail = {
            xhr: {
              status: error.status,
              responseText: JSON.stringify(error.data)
            }
          };
          w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else if (w.SintelFeedback) {
          const msg = error.data?.message || error.data?.detail || 'Error al guardar el asiento.';
          w.SintelFeedback.error(msg);
        }
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al guardar el asiento. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Maneja la aprobación de un asiento
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleAprobar(id) {
    if (!id) {
      console.error(MOD, 'ID de asiento requerido');
      return;
    }

    if (!w.AsientoAPI) {
      console.error(MOD, 'AsientoAPI no está disponible');
      return;
    }

    try {
      await w.AsientoAPI.aprobar(id);

      // Éxito: Recargar tabla
      if (w.AsientoList && typeof w.AsientoList.reload === 'function') {
        w.AsientoList.reload();
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Asiento aprobado correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a ErrorHandler o UIManager
      console.error(MOD, 'Error aprobando asiento:', error);
      
      // ⚠️ v2.60: Manejo estructurado de errores de DRF (ValidationError)
      // El error lanzado por asiento.api.js tiene: status, data, response
      if (error && typeof error === 'object' && 'status' in error && 'data' in error) {
        // Error estructurado de http.js (422 con detalles de cuadratura)
        // Construir un objeto XHR simulado para ErrorHandler.show()
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          const mockXHR = {
            status: error.status,
            statusText: error.status === 422 ? 'Unprocessable Entity' : 'Error',
            response: JSON.stringify(error.data),
            responseText: JSON.stringify(error.data)
          };
          w.ErrorHandler.show(mockXHR);
        } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          const errorDetail = {
            xhr: {
              status: error.status,
              responseText: JSON.stringify(error.data)
            }
          };
          w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else if (w.SintelFeedback) {
          const msg = error.data?.message || error.data?.detail || 'Error al aprobar el asiento. Verifique que esté cuadrado.';
          w.SintelFeedback.error(msg);
        }
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al aprobar el asiento. Verifique que esté cuadrado.');
      }
    }
  }

  /**
   * Maneja la eliminación de un asiento
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleDelete(id) {
    if (!id) {
      console.error(MOD, 'ID de asiento requerido');
      return;
    }

    if (!w.AsientoAPI) {
      console.error(MOD, 'AsientoAPI no está disponible');
      return;
    }

    try {
      await w.AsientoAPI.delete(id);

      // Éxito: Recargar tabla
      if (w.AsientoList && typeof w.AsientoList.reload === 'function') {
        w.AsientoList.reload();
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Asiento eliminado correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a ErrorHandler o UIManager
      console.error(MOD, 'Error eliminando asiento:', error);
      
      // ⚠️ v2.60: Manejo estructurado de errores de DRF
      if (error && typeof error === 'object' && 'status' in error && 'data' in error) {
        // Construir un objeto XHR simulado para ErrorHandler.show()
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          const mockXHR = {
            status: error.status,
            statusText: error.status === 422 ? 'Unprocessable Entity' : 'Error',
            response: JSON.stringify(error.data),
            responseText: JSON.stringify(error.data)
          };
          w.ErrorHandler.show(mockXHR);
        } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          const errorDetail = {
            xhr: {
              status: error.status,
              responseText: JSON.stringify(error.data)
            }
          };
          w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else if (w.SintelFeedback) {
          w.SintelFeedback.error(error.data?.message || error.data?.detail || 'Error al eliminar el asiento.');
        }
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al eliminar el asiento. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Event delegation para botones de guardado y acciones
   */
  function attachEditorListeners() {
    // Guardar crear
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-asiento-crear');
      if (btn) {
        ev.preventDefault();
        handleSave('create');
      }
    });

    // Guardar editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-asiento-editar');
      if (btn) {
        ev.preventDefault();
        handleSave('update');
      }
    });

    // Agregar movimiento
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-agregar-movimiento');
      if (btn) {
        ev.preventDefault();
        agregarMovimiento();
      }
    });
  }

  /**
   * Inicialización
   */
  function init() {
    attachEditorListeners();
  }

  // Inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Exportar API pública
  if (typeof w !== 'undefined') {
    w.AsientoEditor = Object.freeze({
      save: handleSave,
      delete: handleDelete,
      aprobar: handleAprobar,
      agregarMovimiento: agregarMovimiento,
      actualizarTotales: actualizarTotales,
      closeOffcanvas: closeOffcanvas
    });
  }
})(window, document);
