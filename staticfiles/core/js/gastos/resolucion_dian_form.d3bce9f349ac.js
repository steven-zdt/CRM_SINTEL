/**
 * resolucion_dian_form.js - Modulo Formulario Resolucion DIAN v2.61 - Feature-Sliced Architecture
 * Namespace: w.AppResolucionDIAN
 *
 * Reemplaza: gastos_resolucion.js
 *
 * Dependencias globales:
 * - w.gastosAPI  (gastos.api.js) - setConfigResolucion, getResolucionActiva
 * - w.UIManager
 * - w.SintelFeedback
 * - w.AppGastos  (gastos_main.js) - verificarResolucionActiva
 * - w.AppGasto   (gasto_form.js) - actualizarSelectResolucion
 * - w.AppResolucionDIAN (resolucion_dian_main.js) - refresh
 * - htmx
 */
(function (w, d) {
  'use strict';

  const MOD = '[resolucion-dian.form]';

  if (!w.AppResolucion) {
    w.AppResolucion = {};
  }
  // Compatibilidad: alias para código legacy
  if (!w.AppResolucionDIAN) {
    w.AppResolucionDIAN = w.AppResolucion;
  }

  function redirectToWorkspaceGastos() {
    const targetPath = '/workspace/';
    const targetHash = '#gastos';

    const currentPath = (w.location.pathname || '').replace(/\/+$/, '');
    const normalizedTarget = targetPath.replace(/\/+$/, '');

    if (currentPath === normalizedTarget) {
      if (w.location.hash !== targetHash) {
        w.location.hash = 'gastos';
      }
      return;
    }

    w.location.assign(`${targetPath}${targetHash}`);
  }

  function closeResolucionOffcanvas() {
    const offcanvasEl = d.getElementById('offcanvas-resolucion-config');
    if (!offcanvasEl) return;

    if (w.bootstrap?.Offcanvas) {
      w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).hide();
    }

    // Fallback defensivo para casos donde Bootstrap no remueve backdrop/clases.
    offcanvasEl.classList.remove('show');
    offcanvasEl.setAttribute('aria-hidden', 'true');
    offcanvasEl.style.visibility = 'hidden';
    d.querySelectorAll('.offcanvas-backdrop').forEach((el) => el.remove());
    d.body.classList.remove('offcanvas-open');
    d.body.style.removeProperty('overflow');
    d.body.style.removeProperty('padding-right');
  }

  // ---------------------------------------------------------------------------
  // MOSTRAR OFFCANVAS
  // ---------------------------------------------------------------------------

  async function mostrar() {
    const container = d.getElementById('offcanvas-container-gastos');
    if (!container) {
      console.error(`${MOD} Contenedor #offcanvas-container-gastos no encontrado`);
      return;
    }

    try {
      await htmx.ajax('GET', '/api/v1/gastos/render-offcanvas/resolucion/', {
        target: '#offcanvas-container-gastos',
        swap: 'innerHTML'
      });
      await new Promise(r => setTimeout(r, 50));
      inicializarValoresPorDefecto();

      const offcanvasEl = d.getElementById('offcanvas-resolucion-config');
      if (offcanvasEl && w.bootstrap?.Offcanvas) {
        w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas:`, error);
      w.UIManager?.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario de configuracion' } }, MOD);
    }
  }

  // ---------------------------------------------------------------------------
  // FORMULARIO: valores por defecto
  // ---------------------------------------------------------------------------

  function inicializarValoresPorDefecto() {
    const form = d.getElementById('form-resolucion-config');
    if (!form) return;

    const fechaResolucion = form.querySelector('input[name="fecha_resolucion"]');
    if (fechaResolucion && !fechaResolucion.value) {
      fechaResolucion.value = new Date().toISOString().split('T')[0];
    }

    const fechaFin = form.querySelector('input[name="fecha_fin"]');
    if (fechaFin && !fechaFin.value) {
      const hoy = new Date();
      hoy.setFullYear(hoy.getFullYear() + 1);
      fechaFin.value = hoy.toISOString().split('T')[0];
    }

    const feedbackEl = d.getElementById('feedback-config-resolucion');
    if (feedbackEl) {
      feedbackEl.textContent = '';
      feedbackEl.className = 'alert d-none';
      feedbackEl.style.display = 'none';
    }

    configurarValidacionUnicidadLocal();
  }

  // ---------------------------------------------------------------------------
  // VALIDACION PREVENTIVA: unicidad numero_resolucion
  // ---------------------------------------------------------------------------

  function configurarValidacionUnicidadLocal() {
    const form = d.getElementById('form-resolucion-config');
    if (!form) return;

    if (form.dataset.unicidadBound === '1') return;
    form.dataset.unicidadBound = '1';

    form.addEventListener('submit', function(event) {
      const inputNumero = d.getElementById('numero_resolucion') || form.querySelector('input[name="numero_resolucion"]');
      const numeroNuevo = (inputNumero?.value || '').trim();
      if (!numeroNuevo) return;

      const table = w.AppResolucion?.table;
      const data = table && typeof table.getData === 'function' ? table.getData() : [];
      const existeLocal = data.some(r => String(r.numero_resolucion || '').trim() === numeroNuevo);

      if (existeLocal) {
        event.preventDefault();
        event.stopPropagation();
        if (inputNumero) inputNumero.classList.add('is-invalid');

        if (w.UIManager?.handleError) {
          w.UIManager.handleError(
            { status: 422, data: { detail: 'El numero de resolucion ya esta registrado en el sistema.', missing_fields: ['numero_resolucion'] } },
            MOD,
            { errorContainerSelector: '#feedback-config-resolucion' }
          );
        } else if (w.SintelFeedback?.error) {
          w.SintelFeedback.error('El numero de resolucion ya esta registrado en el sistema.');
        }
      } else if (inputNumero) {
        inputNumero.classList.remove('is-invalid');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // VER DETALLE
  // ---------------------------------------------------------------------------

  async function ver(id) {
    const res = await w.resolucionesAPI.get(id);
    if (!res.ok) {
      console.error(`${MOD} Error al obtener detalle de resolucion ${id}:`, res);
      w.UIManager?.handleError(res, MOD);
      return;
    }

    const data = res.data;
    const container = d.getElementById('offcanvas-container-gastos');
    if (!container) {
      console.error(`${MOD} Contenedor #offcanvas-container-gastos no encontrado`);
      return;
    }

    const fmtD = (str) => {
      if (!str) return '---';
      try { return new Date(str).toLocaleDateString('es-CO'); } catch(e) { return str; }
    };

    const vigenteBadge = data.vigente
      ? '<span class="badge bg-success ms-1">VIGENTE</span>'
      : '<span class="badge bg-secondary ms-1">INACTIVA</span>';

    const conteo = parseInt(data.conteo_documentos, 10) || 0;
    const conteoBadge = `<span class="badge ${conteo > 0 ? 'bg-primary' : 'bg-secondary'}">${conteo}</span>`;

    container.innerHTML = `
      <div class="offcanvas offcanvas-end" tabindex="-1" id="offcanvas-resolucion-detalle"
           data-bs-scroll="false" aria-labelledby="resolucion-detalle-label"
           style="width:90%;max-width:560px;">
        <div class="offcanvas-header border-bottom" style="background:#344767;color:#fff;">
          <h5 class="offcanvas-title" id="resolucion-detalle-label">
            <i class="bi bi-gear-fill me-2"></i>Detalle Resolucion DIAN ${vigenteBadge}
          </h5>
          <button type="button" class="btn-close btn-close-white"
                  data-bs-dismiss="offcanvas" aria-label="Cerrar"></button>
        </div>
        <div class="offcanvas-body">
          <div class="row g-3">
            <div class="col-md-6">
              <p class="text-muted small mb-1">Numero Resolucion</p>
              <p class="fw-semibold mb-0">${data.numero_resolucion || '---'}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Prefijo</p>
              <p class="mb-0">${data.prefijo || '---'}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Rango Desde</p>
              <p class="mb-0">${data.rango_desde !== undefined && data.rango_desde !== null ? data.rango_desde : '---'}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Rango Hasta</p>
              <p class="mb-0">${data.rango_hasta !== undefined && data.rango_hasta !== null ? data.rango_hasta : '---'}</p>
            </div>
            <div class="col-md-4">
              <p class="text-muted small mb-1">Fecha Emision</p>
              <p class="mb-0">${fmtD(data.fecha_resolucion)}</p>
            </div>
            <div class="col-md-4">
              <p class="text-muted small mb-1">Fecha Inicio</p>
              <p class="mb-0">${fmtD(data.fecha_inicio)}</p>
            </div>
            <div class="col-md-4">
              <p class="text-muted small mb-1">Fecha Fin</p>
              <p class="mb-0">${fmtD(data.fecha_fin)}</p>
            </div>
            <div class="col-12">
              <p class="text-muted small mb-1">Clave Tecnica</p>
              <p class="mb-0 small font-monospace text-break">${data.clave_tecnica || '---'}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Documentos Asociados</p>
              <p class="mb-0">${conteoBadge}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Estado</p>
              <p class="mb-0">${vigenteBadge}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Creado</p>
              <p class="mb-0 small">${fmtD(data.created_at)}</p>
            </div>
            <div class="col-md-6">
              <p class="text-muted small mb-1">Actualizado</p>
              <p class="mb-0 small">${fmtD(data.updated_at)}</p>
            </div>
          </div>
        </div>
      </div>
    `;

    const offcanvasEl = d.getElementById('offcanvas-resolucion-detalle');
    if (offcanvasEl && w.bootstrap?.Offcanvas) {
      w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
    }
  }

  // ---------------------------------------------------------------------------
  // ELIMINAR
  // ---------------------------------------------------------------------------

  async function eliminar(id) {
    if (!confirm('¿Esta seguro de eliminar esta Resolucion DIAN?\nSolo es posible si no tiene Documentos de Soporte asociados.')) return;

    const res = await w.resolucionesAPI.delete(id);
    if (!res.ok) {
      console.error(`${MOD} Error al eliminar resolucion ${id}:`, res);
      w.UIManager?.handleError(res, MOD);
      return;
    }

    if (w.SintelFeedback) {
      w.SintelFeedback.success('Resolucion DIAN eliminada correctamente');
    }

    // Refrescar tabla
    w.AppResolucion?.refresh?.();

    d.dispatchEvent(new CustomEvent('Sintel:ResolucionesChanged'));
  }

  async function desactivar(id) {
    if (!confirm('¿Desea desactivar esta Resolucion DIAN?')) return;

    const res = await w.resolucionesAPI.desactivar(id);
    if (!res.ok) {
      console.error(`${MOD} Error al desactivar resolucion ${id}:`, res);
      w.UIManager?.handleError(res, MOD);
      return;
    }

    if (w.SintelFeedback) {
      w.SintelFeedback.success('Resolucion DIAN desactivada correctamente');
    }

    w.AppResolucion?.refresh?.();
    d.dispatchEvent(new CustomEvent('Sintel:ResolucionesChanged'));
  }

  // ---------------------------------------------------------------------------
  // POST-SAVE CALLBACK (llamado por HTMX desde el template)
  // ---------------------------------------------------------------------------

  function onResolucionSaved(response) {
    try {
      const data = typeof response === 'string' ? JSON.parse(response) : response;
      if (!data) return;

      const feedbackEl = d.getElementById('feedback-config-resolucion');
      if (feedbackEl) {
        const fechaResolucion = data.fecha_resolucion ? new Date(data.fecha_resolucion).toLocaleDateString('es-CO') : 'N/A';
        const fechaInicio = data.fecha_inicio ? new Date(data.fecha_inicio).toLocaleDateString('es-CO') : 'N/A';
        const fechaFin = data.fecha_fin ? new Date(data.fecha_fin).toLocaleDateString('es-CO') : 'N/A';
        const vigenteBadge = data.vigente
          ? '<span class="badge bg-success ms-2">VIGENTE</span>'
          : '<span class="badge bg-secondary ms-2">INACTIVA</span>';

        feedbackEl.className = 'alert alert-success';
        feedbackEl.innerHTML = `
          <div class="d-flex align-items-start">
            <i class="bi bi-check-circle-fill me-2 fs-5"></i>
            <div class="flex-grow-1">
              <strong>Resolucion DIAN guardada correctamente</strong>${vigenteBadge}
              <hr class="my-2">
              <div class="small">
                <div class="row g-2">
                  <div class="col-md-6"><strong>Numero:</strong> ${data.numero_resolucion || 'N/A'}</div>
                  <div class="col-md-6"><strong>Prefijo:</strong> ${data.prefijo || 'N/A'}</div>
                  <div class="col-md-6"><strong>Rango:</strong> ${data.rango_desde || 'N/A'} - ${data.rango_hasta || 'N/A'}</div>
                  <div class="col-md-6"><strong>Fecha Emision:</strong> ${fechaResolucion}</div>
                  <div class="col-md-6"><strong>Fecha Inicio:</strong> ${fechaInicio}</div>
                  <div class="col-md-6"><strong>Fecha Fin:</strong> ${fechaFin}</div>
                </div>
              </div>
            </div>
          </div>
        `;
        feedbackEl.style.display = 'block';
        feedbackEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      if (w.SintelFeedback) {
        w.SintelFeedback.success('Resolucion DIAN configurada correctamente');
      } else if (w.DOMUtils?.showToast) {
        w.DOMUtils.showToast('Resolucion DIAN configurada correctamente', 'success');
      }

      // Reactividad inter-modulos: notificar a otros modulos que hay una nueva resolucion
      d.dispatchEvent(new CustomEvent('Sintel:ResolucionesChanged', { detail: data }));

      // Cerrar inmediatamente para evitar formularios abiertos tras guardar.
      closeResolucionOffcanvas();

      const form = d.getElementById('form-resolucion-config');
      if (form) form.reset();
      if (feedbackEl) {
        feedbackEl.innerHTML = '';
        feedbackEl.className = 'alert d-none';
        feedbackEl.style.display = 'none';
      }

      // Refrescar estado y redirigir al hash correcto tras cierre.
      setTimeout(() => {
        // Verificar resolucion activa (actualiza badge en gastos_main)
        w.AppGastos?.verificarResolucionActiva?.();

        w.AppResolucion?.refresh?.();

        // Mantener la navegación anclada al módulo correcto después de guardar.
        redirectToWorkspaceGastos();
      }, 150);

    } catch (error) {
      console.error(`${MOD} Error procesando respuesta:`, error);
    }
  }

  // ---------------------------------------------------------------------------
  // Exponer API publica del modulo
  // ---------------------------------------------------------------------------

  w.AppResolucion.mostrar = mostrar;
  w.AppResolucion.onResolucionSaved = onResolucionSaved;
  w.AppResolucion.ver = ver;
  w.AppResolucion.desactivar = desactivar;
  w.AppResolucion.eliminar = eliminar;
  w.AppResolucionDIAN = w.AppResolucion;

  // Compatibilidad con referencias legacy desde templates HTMX existentes.
  if (!w.AppGastos) {
    w.AppGastos = {};
  }
  w.AppGastos.onResolucionSaved = onResolucionSaved;

  console.log(`${MOD} Modulo inicializado (w.AppResolucion)`);

})(window, document);

