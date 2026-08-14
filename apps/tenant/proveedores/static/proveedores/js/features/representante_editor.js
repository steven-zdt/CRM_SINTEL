/**
 * representante_editor.js — Form Editor para Representantes v3.17.2
 * Namespace: window.Sintel.Proveedores
 *
 * BUGFIX v3.17.2:
 *  - api.* ahora retorna res.data directamente y lanza Error en 4xx/5xx.
 *  - Reemplazado <select> de proveedor por autocomplete con chip visual.
 *  - showNotification usa notyf (window.notyf) o alert como fallback.
 */

window.Sintel = window.Sintel || {};
window.Sintel.Proveedores = window.Sintel.Proveedores || {};

(function (mod) {
  'use strict';

  const api = window.Sintel.Representante;

  // ─────────────────────────────────── helpers UI ────────────────────────────
  function _notify(msg, type) {
    if (window.notyf) {
      type === 'success' ? window.notyf.success(msg)
        : type === 'warning' ? window.notyf.open({ type: 'warning', message: msg })
        : window.notyf.error(msg);
    } else {
      alert(msg);
    }
  }

  // ────────────────── Autocomplete de Proveedor (Modo Directorio) ────────────
  /**
   * Inicializa el autocomplete de proveedor en el offcanvas.
   * Se llama UNA SOLA VEZ en DOMContentLoaded — los listeners no se duplican.
   */
  function _initACProveedor() {
    const input  = document.getElementById('proveedor-ac-input');
    const dd     = document.getElementById('proveedor-ac-dd');
    const chip   = document.getElementById('proveedor-chip');
    const cNom   = document.getElementById('proveedor-chip-nombre');
    const cDoc   = document.getElementById('proveedor-chip-doc');
    const hidden = document.getElementById('proveedor-uuid-hidden');
    const awEl   = document.getElementById('aw-proveedor');
    const btnX   = document.getElementById('btn-limpiar-proveedor');

    if (!input || !dd || !hidden) return;

    function _seleccionar(p) {
      hidden.value      = p.uuid;
      cNom.textContent  = p.razon_social || p.nombre_comercial || '—';
      cDoc.textContent  = (p.tipo_documento || 'NIT') + ': ' + (p.numero_documento || '—');
      chip?.classList.remove('d-none');
      if (awEl) awEl.style.display = 'none';
      dd.style.display  = 'none';
      input.value       = '';
      input.classList.remove('is-invalid');
    }

    function _limpiar() {
      hidden.value = '';
      chip?.classList.add('d-none');
      if (awEl) awEl.style.display = '';
      input.value = '';
      input.focus();
    }

    let _timer;
    input.addEventListener('input', function () {
      clearTimeout(_timer);
      const q = input.value.trim();
      if (q.length < 2) { dd.style.display = 'none'; return; }
      _timer = setTimeout(async function () {
        try {
          const res = await window.Sintel.Core.Http.request(
            'GET',
            '/api/v1/proveedores/?search=' + encodeURIComponent(q) + '&page_size=15&activo=true'
          );
          const items = res.data?.results || [];
          dd.innerHTML = '';
          if (!items.length) {
            dd.innerHTML = '<div class="px-3 py-2 text-muted small">Sin resultados para "' + q + '"</div>';
          } else {
            items.forEach(function (p) {
              const el = document.createElement('div');
              el.className = 'ac-proveedor-item px-3 py-2 border-bottom';
              el.style.cursor = 'pointer';
              el.innerHTML =
                '<div class="fw-semibold small text-truncate">'
                + (p.razon_social || p.nombre_comercial || '—') + '</div>'
                + '<div class="text-muted" style="font-size:.72rem;">'
                + (p.tipo_documento || 'NIT') + ': ' + (p.numero_documento || '—') + '</div>';
              el.addEventListener('mouseenter', function () { el.classList.add('bg-light'); });
              el.addEventListener('mouseleave', function () { el.classList.remove('bg-light'); });
              el.addEventListener('click', function () { _seleccionar(p); });
              dd.appendChild(el);
            });
          }
          dd.style.display = 'block';
        } catch (err) {
          console.error('[representante_editor] autocomplete error:', err);
        }
      }, 280);
    });

    document.addEventListener('click', function (e) {
      if (!input.contains(e.target) && !dd.contains(e.target)) {
        dd.style.display = 'none';
      }
    });

    if (btnX) {
      btnX.addEventListener('click', _limpiar);
    }
  }

  /**
   * Resetea el widget de autocomplete a estado vacío (sin seleccion previa).
   * Se llama cada vez que se abre el offcanvas en modo directorio.
   */
  function _resetACProveedor() {
    const input  = document.getElementById('proveedor-ac-input');
    const dd     = document.getElementById('proveedor-ac-dd');
    const chip   = document.getElementById('proveedor-chip');
    const hidden = document.getElementById('proveedor-uuid-hidden');
    const awEl   = document.getElementById('aw-proveedor');

    if (hidden)  hidden.value = '';
    if (input)   { input.value = ''; input.classList.remove('is-invalid'); }
    if (dd)      dd.style.display = 'none';
    if (chip)    chip.classList.add('d-none');
    if (awEl)    awEl.style.display = '';
  }

  // ────────────────────────────── API publica del modulo ─────────────────────

  /**
   * Abre offcanvas para crear/editar representante.
   *
   * @param {string|null} representanteUuid  UUID del representante a editar, o null para crear.
   * @param {string|null} proveedorUuid      UUID del proveedor pre-seleccionado.
   * @param {string}      proveedorNombre    Nombre del proveedor para el badge.
   *
   * Modos:
   *   - representanteUuid=null, proveedorUuid=null  → crear desde directorio (autocomplete proveedor)
   *   - representanteUuid=null, proveedorUuid=uuid  → crear desde detalle proveedor (badge)
   *   - representanteUuid=uuid                      → editar (badge con nombre si lo hay)
   */
  mod.abrirFormRepresentante = async (representanteUuid, proveedorUuid, proveedorNombre) => {
    representanteUuid = representanteUuid || null;
    proveedorUuid     = proveedorUuid     || null;
    proveedorNombre   = proveedorNombre   || '';

    const offcanvas = document.getElementById('offcanvas-representante');
    if (!offcanvas) {
      console.error('[representante_editor] #offcanvas-representante no encontrado');
      return;
    }

    const form = document.getElementById('form-representante');
    if (!form) {
      console.error('[representante_editor] #form-representante no encontrado');
      return;
    }

    // Limpiar form
    form.reset();
    form.classList.remove('was-validated');

    const tituloEl = document.getElementById('offcanvas-titulo-accion');
    if (tituloEl) {
      tituloEl.textContent = representanteUuid ? 'Editar Encargado' : 'Nuevo Encargado';
    }

    const selectorContainer = document.getElementById('proveedor-selector-container');
    const infoContainer     = document.getElementById('proveedor-info-container');
    const nombreDisplay     = document.getElementById('proveedor-nombre-display');
    const modoDirectorio    = !representanteUuid && !proveedorUuid;

    // Ocultar ambos paneles; mostrar solo el que aplique
    selectorContainer?.classList.add('d-none');
    infoContainer?.classList.add('d-none');

    if (modoDirectorio) {
      // Modo directorio: autocomplete de proveedores
      _resetACProveedor();
      selectorContainer?.classList.remove('d-none');
    } else if (proveedorUuid) {
      // Modo detalle-proveedor: badge fijo
      infoContainer?.classList.remove('d-none');
      if (nombreDisplay) {
        nombreDisplay.textContent = proveedorNombre || 'Proveedor seleccionado';
      }
    } else if (representanteUuid) {
      // Editar sin proveedorUuid explícito: mostrar badge (nombre se carga abajo)
      infoContainer?.classList.remove('d-none');
    }

    // Cargar datos si estamos editando
    if (representanteUuid) {
      try {
        const data = await api.obtener(representanteUuid);
        // api.obtener ya retorna res.data directamente (v3.17.2)
        if (form.tipo_documento)    form.tipo_documento.value    = data.tipo_documento    || '';
        if (form.numero_documento)  form.numero_documento.value  = data.numero_documento  || '';
        if (form.nombre_completo)   form.nombre_completo.value   = data.nombre_completo   || '';
        if (form.email_contacto)    form.email_contacto.value    = data.email_contacto    || '';
        if (form.telefono_contacto) form.telefono_contacto.value = data.telefono_contacto || '';
        if (form.cargo)             form.cargo.value             = data.cargo             || 'Representante Legal';
        if (form.es_principal)      form.es_principal.checked    = !!data.es_principal;

        // Mostrar nombre del proveedor en el badge (si info-container visible)
        if (nombreDisplay && data.proveedor_razon_social) {
          nombreDisplay.textContent = data.proveedor_razon_social;
        }
      } catch (error) {
        console.error('[representante_editor] Error cargando datos:', error);
        _notify('Error cargando los datos del encargado', 'danger');
        return;
      }
    }

    // Guardar contexto en el form para guardarRepresentante
    form.dataset.representanteUuid = representanteUuid || '';
    form.dataset.proveedorUuid     = proveedorUuid     || '';
    form.dataset.modoDirectorio    = modoDirectorio ? '1' : '';

    // Mostrar offcanvas (evitar acumulacion de backdrops)
    if (window.UIManager?.handleOffcanvas) {
      window.UIManager.handleOffcanvas(offcanvas, 'show');
    } else {
      // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
      window.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvas);
    }
  };

  /**
   * Guarda representante (crear o actualizar).
   * Llamado por el boton #btn-guardar-representante.
   */
  mod.guardarRepresentante = async () => {
    const form = document.getElementById('form-representante');
    if (!form) return false;

    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      return false;
    }

    const representanteUuid = form.dataset.representanteUuid || '';
    const modoDirectorio    = form.dataset.modoDirectorio === '1';

    // Resolver proveedor UUID segun modo
    let proveedorUuid = form.dataset.proveedorUuid || '';
    if (!proveedorUuid && !representanteUuid) {
      // Modo directorio: leer del hidden input del autocomplete
      const hidden = document.getElementById('proveedor-uuid-hidden');
      proveedorUuid = hidden?.value?.trim() || '';
      if (!proveedorUuid) {
        document.getElementById('proveedor-ac-input')?.classList.add('is-invalid');
        _notify('Debe seleccionar un proveedor', 'warning');
        return false;
      }
    }

    const payload = {
      tipo_documento:    form.tipo_documento?.value     || '',
      numero_documento:  form.numero_documento?.value   || '',
      nombre_completo:   form.nombre_completo?.value    || '',
      email_contacto:    form.email_contacto?.value     || '',
      telefono_contacto: form.telefono_contacto?.value  || '',
      cargo:             form.cargo?.value              || 'Representante Legal',
      es_principal:      form.es_principal?.checked     || false,
    };

    try {
      if (representanteUuid) {
        await api.actualizar(representanteUuid, payload);
        _notify('Encargado actualizado correctamente', 'success');
      } else {
        await api.crear(payload, proveedorUuid);
        _notify('Encargado creado correctamente', 'success');
      }

      // Cerrar offcanvas
      const offcanvas = document.getElementById('offcanvas-representante');
      if (window.UIManager?.handleOffcanvas) {
        window.UIManager.handleOffcanvas(offcanvas, 'hide');
      } else {
        bootstrap.Offcanvas.getInstance(offcanvas)?.hide();
      }

      // Recargar tabla segun contexto
      _recargarTabla(modoDirectorio ? '' : proveedorUuid);
      return true;
    } catch (error) {
      console.error('[representante_editor] Error guardando:', error);
      _notify('Error: ' + (error.message || 'No se pudo guardar el encargado'), 'danger');
      return false;
    }
  };

  /**
   * Elimina un representante con confirmacion.
   * @param {string}      representanteUuid
   * @param {string|null} proveedorUuid  Para recargar la tabla correcta tras eliminar.
   */
  mod.eliminarRepresentante = async (representanteUuid, proveedorUuid) => {
    if (!(await w.UIManager?.confirm('¿Está seguro de eliminar este representante?'))) return false;
    try {
      await api.eliminar(representanteUuid);
      _notify('Representante eliminado correctamente', 'success');
      _recargarTabla(proveedorUuid || '');
      return true;
    } catch (error) {
      console.error('[representante_editor] Error eliminando:', error);
      _notify('Error: ' + (error.message || 'No se pudo eliminar'), 'danger');
      return false;
    }
  };

  // ─────────────────────── helpers internos ──────────────────────────────────

  function _recargarTabla(proveedorUuid) {
    if (proveedorUuid) {
      window.Sintel.Proveedores.Representante?.cargarTabla?.(proveedorUuid);
    } else {
      window.Sintel?.DirectorioRepresentantes?.reload?.();
    }
  }

  // ─────────────────────── DOMContentLoaded ──────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    // Inicializar autocomplete UNA vez (listeners no se duplican)
    _initACProveedor();

    // Boton guardar
    const btnGuardar = document.getElementById('btn-guardar-representante');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', function (e) {
        e.preventDefault();
        mod.guardarRepresentante();
      });
    }
  });

})(window.Sintel.Proveedores);
