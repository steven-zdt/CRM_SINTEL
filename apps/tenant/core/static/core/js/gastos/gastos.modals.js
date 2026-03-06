/**
 * gastos.modals.js - Modales Gastos v2.60
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.40: Sistema de Documento Soporte Inmutable con Resolución DIAN Automática
 * - showCreate(): Obtiene automáticamente la resolución vigente y la muestra como readonly
 * - save(): Valida resolución activa antes de crear, usa automáticamente la vigente
 * - El backend (obtener_siguiente_numero_soporte) busca automáticamente la resolución vigente
 * - showDetail(): Muestra evidencia legal completa del documento soporte
 */
(function(w, d) {
  'use strict';

  // Helper: Formatear dinero con fallback
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

  const MODAL_CREATE = '#modal-gasto-create';
  const MODAL_DETAIL = '#modal-gasto-detail';

  // ⚠️ v2.40: Función para calcular retenciones automáticamente
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

  w.gastosModals = {
    /** Carga resolución activa y abre modal de creación */
    showCreate: async () => {
      console.log('[gastos.modals] showCreate() llamado');
      
      // ⚠️ v2.40: Obtener resolución activa automáticamente
      const res = await w.gastosAPI.getResolucionActiva();
      const select = d.getElementById('select-resolucion');
      
      if (res.ok && res.data && select) {
        const resolucion = res.data;
        // Campo readonly informativo
        select.innerHTML = `<option value="${resolucion.id}" selected>${resolucion.prefijo} - Res: ${resolucion.numero_resolucion} (Rango: ${resolucion.rango_desde}-${resolucion.rango_hasta})</option>`;
        select.disabled = true; // ⚠️ v2.40: Readonly - se usa automáticamente la vigente
      } else {
        // No hay resolución activa - esto no debería pasar porque se valida antes en gastos.page.js
        // Si llegamos aquí, es un error de estado, no abrimos ningún modal
        console.error('[gastos.modals] No hay resolución activa (esto no debería pasar)');
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 404, data: { detail: 'No hay resolución DIAN configurada. Configure una resolución primero.' } }, '[gastos.modals]');
        } else if (w.SintelFeedback) {
          w.SintelFeedback.error('No hay resolución DIAN configurada. Configure una resolución primero.');
        }
        // ⚠️ IMPORTANTE: No abrimos el modal de configuración aquí, eso lo maneja gastos.page.js
        return;
      }
      
      // Establecer fecha por defecto (hoy)
      const fechaInput = d.querySelector('#modal-gasto-create input[name="fecha"]');
      if (fechaInput && !fechaInput.value) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.value = hoy;
      }
      
      // Establecer periodo por defecto (mes actual)
      const periodoInput = d.querySelector('#modal-gasto-create input[name="periodo"]');
      if (periodoInput && !periodoInput.value) {
        const hoy = new Date();
        const periodo = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
        periodoInput.value = periodo;
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
      
      // Limpiar feedback
      const feedback = d.getElementById('feedback-create-gasto');
      if (feedback) {
        feedback.classList.add('d-none');
        feedback.textContent = '';
      }
      
      const modalEl = d.getElementById('modal-gasto-create');
      if (modalEl) {
        // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
        if (w.bootstrap && w.bootstrap.Modal) {
          const modal = w.bootstrap.Modal.getOrCreateInstance(modalEl);
          modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
            const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) {
              firstInput.focus();
            }
            modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
          }, { once: true });
          modal.show();
        } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          // Fallback: usar UIManager si Bootstrap no está disponible
          w.UIManager.handleModal('#modal-gasto-create', 'show');
        }
      }
    },

    /**
     * Muestra la evidencia legal completa del gasto
     * ⚠️ v2.60: Aislamiento Gradual - Solo verifica ok
     */
    showDetail: async (id) => {
      // Error Boundary Pattern v2.40
      const res = await w.gastosAPI.get(id);
      if (!res.ok || !res.data) return w.UIManager?.notifyError(res, 'Gastos');

      const g = res.data;
      const ds = g.documento_soporte;

      const html = `
        <div class="row">
          <div class="col-md-6">
            <h6>Evidencia Legal</h6>
            <table class="table table-sm">
              <tr><th>Documento:</th><td>${ds.prefijo}-${ds.consecutivo}</td></tr>
              <tr><th>Fecha:</th><td>${new Date(ds.fecha).toLocaleString()}</td></tr>
              <tr><th>Vendedor:</th><td>${ds.vendedor_nombre}</td></tr>
              <tr><th>NIT:</th><td>${ds.vendedor_nit}</td></tr>
              <tr><th>Estado:</th><td>
                ${ds.anulado ? '<b class="text-danger">ANULADO</b>' : 
                  (ds.activo ? '<b class="text-success">ACTIVO</b>' : '<b class="text-warning">INACTIVO</b>')}
              </td></tr>
            </table>
          </div>
          <div class="col-md-6">
            <h6>Valores Monetarios</h6>
            <table class="table table-sm">
              <tr><th>Subtotal:</th><td>${fmtMoney(ds.subtotal)}</td></tr>
              <tr>
                <th>Retefuente:</th>
                <td>
                  ${fmtMoney(parseFloat(ds.retefuente || 0))}
                  ${ds.retefuente_porcentaje ? `<small class="text-muted d-block">(${(parseFloat(ds.retefuente_porcentaje) * 100).toFixed(2)}%)</small>` : ''}
                </td>
              </tr>
              <tr>
                <th>ReteICA:</th>
                <td>
                  ${fmtMoney(parseFloat(ds.reteica || 0))}
                  ${ds.reteica_porcentaje ? `<small class="text-muted d-block">(${(parseFloat(ds.reteica_porcentaje) * 100).toFixed(3)}%)</small>` : ''}
                </td>
              </tr>
              <tr><th>Total Retenciones:</th><td>${fmtMoney(parseFloat(ds.retefuente || 0) + parseFloat(ds.reteica || 0))}</td></tr>
              <tr class="table-active"><th>Total Neto:</th><td><b>${fmtMoney(ds.total)}</b></td></tr>
            </table>
          </div>
        </div>
        <hr>
        <h6>Clasificación Contable</h6>
        <p><b>Categoría:</b> ${g.categoria_contable} | <b>Centro de Costo:</b> ${g.centro_costo}</p>
        <p><b>Descripción:</b> ${g.descripcion || 'Sin descripción'}</p>
      `;

      d.getElementById('detail-content-gastos').innerHTML = html;
      const modalEl = d.getElementById('modal-gasto-detail');
      if (modalEl) {
        // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
        if (w.bootstrap && w.bootstrap.Modal) {
          const modal = w.bootstrap.Modal.getOrCreateInstance(modalEl);
          modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
            const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) {
              firstInput.focus();
            }
            modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
          }, { once: true });
          modal.show();
        } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          // Fallback: usar UIManager si Bootstrap no está disponible
          w.UIManager.handleModal('#modal-gasto-create', 'show');
        }
      }
    },

    /**
     * Persistencia desde el formulario
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     */
    save: async () => {
      const form = d.getElementById('form-gasto');
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

      // ⚠️ v2.40: El backend calcula automáticamente las retenciones basándose en los porcentajes
      // Solo enviamos: subtotal, retefuente_porcentaje, reteica_porcentaje
      const payload = new FormData(form);
      
      // ⚠️ IMPORTANTE: No enviar retefuente ni reteica como valores numéricos
      // El backend los calculará automáticamente usando calcular_retenciones()
      // Solo enviamos los porcentajes seleccionados
      
      // Validar que haya resolución activa antes de enviar
      const resCheck = await w.gastosAPI.getResolucionActiva();
      if (!resCheck.ok || resCheck.status === 404) {
        const errorMsg = 'No hay resolución DIAN configurada. Configure una resolución primero.';
        
        // Restaurar botón
        if (btnGuardar && !isLoading) {
          btnGuardar.disabled = false;
          btnGuardar.innerHTML = btnOriginalText;
        }
        
        // ⚠️ v2.60: Error Boundary - Mostrar error en modal
        const errorContainer = d.getElementById('feedback-create-gasto');
        if (errorContainer) {
          errorContainer.className = 'alert alert-danger';
          errorContainer.textContent = errorMsg;
          errorContainer.classList.remove('d-none');
          errorContainer.style.display = 'block';
          errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 404, data: { detail: errorMsg } }, '[gastos.modals]');
        }
        return;
      }

      // Error Boundary Pattern v2.40
      const res = await w.gastosAPI.create(payload);
      if (!res.ok) {
        if (btnGuardar) {
          btnGuardar.disabled = false;
          btnGuardar.innerHTML = btnOriginalText;
        }
        return w.UIManager?.notifyError(res, 'Gastos');
      }

      // Éxito: cerrar modal y mostrar notificación
      if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
        w.UIManager.handleModal('#modal-gasto-create', 'hide');
      } else {
        const modalEl = d.getElementById('modal-gasto-create');
        if (modalEl) {
          const modal = bootstrap.Modal.getInstance(modalEl);
          if (modal) modal.hide();
        }
      }
      
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Documento Soporte generado con éxito');
      }
      
      // Forzar recarga de la tabla y resumen en la página
      if (w.gastosPage && typeof w.gastosPage.refresh === 'function') {
        w.gastosPage.refresh();
      } else if (w.gastosPage && w.gastosPage.table) {
        w.gastosPage.table.replaceData();
      } else {
        const btnRefrescar = d.getElementById('btn-refrescar-gastos');
        if (btnRefrescar) btnRefrescar.click();
      }
    }
  };
  
  // ⚠️ v2.40: Limpiar formulario al cerrar modal
  d.addEventListener('hidden.bs.modal', (e) => {
    if (e.target.id === 'modal-gasto-create') {
      const form = d.getElementById('form-gasto');
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
      
      // Resetear select de resolución
      const select = d.getElementById('select-resolucion');
      if (select) {
        select.innerHTML = '<option value="">Cargando resolución activa...</option>';
        select.disabled = true;
      }
      
      // ⚠️ v2.40: Restaurar botón guardar
      const btnGuardar = d.getElementById('btn-guardar-gasto');
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="bi bi-cloud-arrow-up me-1"></i> Guardar y Firmar';
      }
    }
  });
})(window, document);