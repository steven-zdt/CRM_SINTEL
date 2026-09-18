// @ts-nocheck
/**
 * extracto_editor.js — Importación y Detalle de Extractos Bancarios
 * Namespace: window.Sintel.Bancos.ExtractoEditor
 * Skills: vanilla-js.md §1, §2 | htmx.md §2 | ui-management.md §26
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:extracto_editor]';
  const API_URL       = '/api/v1/bancos/extractos/';
  const API_TX_BASE   = '/api/v1/bancos/transacciones/';
  const CONTAINER_ID  = '#offcanvas-container-bancos';

  // ── Abrir offcanvas crear ─────────────────────────────────────────────
  async function openOffcanvas() {
    let container = d.querySelector(CONTAINER_ID);
    if (!container) {
      container = d.createElement('div');
      container.id = CONTAINER_ID.substring(1);
      d.body.appendChild(container);
    }
    return htmx.ajax('GET', `${API_URL}render-offcanvas/crear/`, { target: CONTAINER_ID, swap: 'innerHTML' });
  }

  // ── Abrir detalle de extracto ─────────────────────────────────────────
  async function openDetalle(uuid) {
    if (!uuid) return;
    let container = d.querySelector(CONTAINER_ID);
    if (!container) {
      container = d.createElement('div');
      container.id = CONTAINER_ID.substring(1);
      d.body.appendChild(container);
    }
    return htmx.ajax('GET', `${API_URL}${uuid}/render-offcanvas/detalle/`, { target: CONTAINER_ID, swap: 'innerHTML' });
  }

  // ── Escuchar HTMX afterSettle para activar offcanvas ─────────────────
  d.body.addEventListener('htmx:afterSettle', (e) => {
    const target = e.detail.target;
    if (!target || ('#' + target.id) !== CONTAINER_ID) return;

    // Busca ambos IDs posibles
    const offcanvasEl = target.querySelector('#offcanvas-extracto-crear, #offcanvas-extracto-detalle');
    if (!offcanvasEl) return;

    // Mostrar offcanvas (AGENTS.md §26 — UIManager evita backdrops acumulados)
    if (w.UIManager?.handleOffcanvas) {
      w.UIManager.handleOffcanvas(offcanvasEl, 'show');
    } else {
      // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
      w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
    }

    if (offcanvasEl.id === 'offcanvas-extracto-crear') {
      _bindCrear(offcanvasEl);
    } else if (offcanvasEl.id === 'offcanvas-extracto-detalle') {
      _bindDetalle(offcanvasEl);
    }
  });

  // ── Helpers de error (POST procesar con forzar=true) ──────────────────
  function _mensajeError(res) {
    const detail = res?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.join(', ');
    return 'No se pudo procesar el extracto.';
  }

  function _requiereForzar(res) {
    return res?.status === 422 && /forzar=true/i.test(_mensajeError(res));
  }

  // ── Configurar eventos del formulario crear ───────────────────────────
  function _bindCrear(container) {
    const form = container.querySelector('#extracto-form');
    if (!form || form.dataset.editorInitialized) return;
    form.dataset.editorInitialized = '1';

    form.addEventListener('submit', (e) => { e.preventDefault(); _guardar(form); });
    const btn = container.querySelector('#btn-guardar-extracto');
    if (btn) btn.addEventListener('click', () => form.requestSubmit());
  }

  // ── Configurar eventos del panel de detalle + conciliación ───────────
  function _bindDetalle(container) {
    if (container.dataset.editorInitialized) return;
    container.dataset.editorInitialized = '1';

    // Botón Procesar
    const btnProcesar = container.querySelector('#btn-procesar-extracto-detalle');
    if (btnProcesar && !btnProcesar.dataset.bound) {
      btnProcesar.dataset.bound = '1';
      btnProcesar.addEventListener('click', async function () {
        const uuid = btnProcesar.dataset.uuid;
        if (!uuid) return;
        btnProcesar.disabled = true;
        btnProcesar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Procesando...';
        let res = await w.Sintel.Bancos.API?.extractos?.procesar(uuid);
        // Fase 24 (importacion no destructiva): el backend rechaza reprocesar
        // un extracto con conciliaciones/aplicaciones salvo forzar=true --
        // se ofrece confirmar y reintentar en vez de dejar al usuario sin salida.
        if (!res?.ok && _requiereForzar(res) && w.confirm(_mensajeError(res))) {
          res = await w.Sintel.Bancos.API?.extractos?.procesar(uuid, true);
        }
        if (!res?.ok) {
          btnProcesar.disabled = false;
          btnProcesar.innerHTML = '<i class="bi bi-cpu me-1"></i>Procesar';
          return w.UIManager?.handleError(res, MOD);
        }
        w.UIManager?.showSuccess('Extracto procesado. Transacciones importadas.');
        if (w.UIManager?.handleOffcanvas) {
          w.UIManager.handleOffcanvas(container, 'hide');
        }
        w.Sintel.Bancos.ExtractoList?.refresh();
      });
    }

    // ── Filtros de tabla ──────────────────────────────────────────────
    const rows = Array.from(container.querySelectorAll('.tx-row'));
    let filtroTipo = 'TODOS', filtroConc = 'TODOS_CONC';

    function aplicarFiltros() {
      rows.forEach(r => {
        const okTipo = filtroTipo === 'TODOS' || r.dataset.tipo === filtroTipo;
        const okConc = filtroConc === 'TODOS_CONC' || (filtroConc === 'PENDIENTE' && r.dataset.conciliado === '0');
        r.style.display = okTipo && okConc ? '' : 'none';
      });
    }

    container.querySelectorAll('[data-filtro-tx]').forEach(btn => {
      btn.addEventListener('click', () => {
        container.querySelectorAll('[data-filtro-tx]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filtroTipo = btn.dataset.filtroTx;
        aplicarFiltros();
      });
    });

    container.querySelectorAll('[data-filtro-conc]').forEach(btn => {
      btn.addEventListener('click', () => {
        container.querySelectorAll('[data-filtro-conc]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filtroConc = btn.dataset.filtroConc;
        aplicarFiltros();
      });
    });

    // ── Panel de conciliación ──────────────────────────────────────────
    const placeholder = container.querySelector('#conc-placeholder');
    const form        = container.querySelector('#conc-form');
    const concUuid    = container.querySelector('#conc-uuid');
    const txDescEl    = container.querySelector('#conc-tx-desc');
    const txFechaEl   = container.querySelector('#conc-tx-fecha');
    const txValorEl   = container.querySelector('#conc-tx-valor');
    const feedback    = container.querySelector('#conc-feedback');
    const hidFact     = container.querySelector('#conc-factura-uuid');
    const hidProv     = container.querySelector('#conc-proveedor-uuid');
    const hidCli      = container.querySelector('#conc-cliente-uuid');

    if (!form || !concUuid) return;

    // ── Click en fila → flujo cíclico 3 pasos ──────────────────────
    rows.forEach(row => {
      row.addEventListener('click', () => {
        rows.forEach(r => r.classList.remove('tx-activa'));
        row.classList.add('tx-activa');

        const uuid    = row.dataset.uuid;
        const esEgreso = row.dataset.tipo === 'EGRESO';

        // Paso 1: rellenar info de la transacción
        concUuid.value = uuid;
        const tipoHid = container.querySelector('#conc-tipo-movimiento');
        if (tipoHid) tipoHid.value = esEgreso ? 'EGRESO' : 'INGRESO';

        if (txDescEl) txDescEl.textContent = row.dataset.descripcion || '—';
        if (txFechaEl) txFechaEl.textContent = row.querySelector('td:first-child .font-monospace')?.textContent || '';

        const valCell = row.querySelector('td:nth-child(4)');
        if (txValorEl) {
          txValorEl.textContent = valCell?.textContent?.trim() || '';
          txValorEl.className   = 'fw-bold font-monospace ' + (esEgreso ? 'val-egreso' : 'val-ingreso');
        }

        // Badge tipo en paso 1
        const tipoBadge = container.querySelector('#conc-tipo-badge');
        if (tipoBadge) {
          if (esEgreso) {
            tipoBadge.className   = 'ms-auto badge bg-danger';
            tipoBadge.innerHTML   = '<i class="bi bi-arrow-down me-1"></i>Egreso';
          } else {
            tipoBadge.className   = 'ms-auto badge bg-success';
            tipoBadge.innerHTML   = '<i class="bi bi-arrow-up me-1"></i>Ingreso';
          }
        }

        // Paso 2: auto-seleccionar tab de factura según tipo de movimiento
        _activarTabFac(esEgreso ? 'COMPRA' : 'VENTA');

        // Actualizar label del paso 2
        const paso2Label = container.querySelector('#conc-step-factura-label');
        if (paso2Label) {
          paso2Label.textContent = esEgreso ? 'Factura de Compra' : 'Factura de Venta';
        }

        // Paso 3: mostrar solo el tercero relevante
        const stepProveedor = container.querySelector('#conc-step-proveedor');
        const stepCliente   = container.querySelector('#conc-step-cliente');
        if (esEgreso) {
          stepProveedor?.classList.remove('d-none');
          stepCliente?.classList.add('d-none');
          _limpiarChip(container, 'cliente');
        } else {
          stepCliente?.classList.remove('d-none');
          stepProveedor?.classList.add('d-none');
          _limpiarChip(container, 'proveedor');
        }

        // Limpiar selecciones previas, notas y feedback
        _limpiarChip(container, 'factura');
        const notasEl = container.querySelector('#conc-notas');
        if (notasEl) notasEl.value = row.dataset.notas || '';
        if (feedback) { feedback.className = 'd-none'; feedback.innerHTML = ''; }

        // Pre-cargar vínculos ya existentes si los hay
        // BAN-06/07: el nombre/numero real ya viene resuelto server-side
        // (render_offcanvas_detalle -> TerceroDisplaySelector); si el
        // registro fue eliminado y no se pudo resolver, se cae al UUID
        // truncado como antes (soft-ref sin resolver, no bloquea).
        if (row.dataset.facturaUuid) {
          _setChip(container, 'factura',
            row.dataset.facturaUuid,
            row.dataset.facturaInfo || 'Factura ya vinculada',
            row.dataset.facturaInfo ? 'UUID: ' + row.dataset.facturaUuid.slice(-8)
                                     : '(no se pudo resolver el nombre)');
        }
        if (esEgreso && row.dataset.proveedorUuid) {
          _setChip(container, 'proveedor',
            row.dataset.proveedorUuid,
            row.dataset.proveedorInfo || 'Proveedor ya vinculado',
            row.dataset.proveedorInfo ? 'UUID: ' + row.dataset.proveedorUuid.slice(-8)
                                       : '(no se pudo resolver el nombre)');
        }
        if (!esEgreso && row.dataset.clienteUuid) {
          _setChip(container, 'cliente',
            row.dataset.clienteUuid,
            row.dataset.clienteInfo || 'Cliente ya vinculado',
            row.dataset.clienteInfo ? 'UUID: ' + row.dataset.clienteUuid.slice(-8)
                                     : '(no se pudo resolver el nombre)');
        }

        // Marcar paso 1 como completado
        const stepNum1 = container.querySelector('.conc-step:first-of-type .conc-step-num');
        if (stepNum1) stepNum1.classList.add('done');

        // Mostrar formulario
        if (placeholder) placeholder.style.display = 'none';
        form.classList.add('visible');

        // Paso 5: cargar aplicaciones multiples de esta transaccion (Fase 5-12)
        _cargarAplicaciones(container, uuid);
      });
    });

    // Chips — botones ×
    container.querySelectorAll('.chip-remove').forEach(btn => {
      btn.addEventListener('click', () => _limpiarChip(container, btn.dataset.clear));
    });

    // ── Tab VENTA / COMPRA para facturas (naturaleza) ───────────────
    let naturalezaFac = 'VENTA';
    const tabsFac = container.querySelectorAll('[data-tipo-fac]');

    function _activarTabFac(nat) {
      naturalezaFac = nat;
      tabsFac.forEach(b => {
        const isThis = b.dataset.tipoFac === nat;
        b.classList.toggle('active',          isThis);
        b.classList.toggle('btn-primary',     isThis && nat === 'VENTA');
        b.classList.toggle('btn-secondary',   isThis && nat !== 'VENTA');
        b.classList.toggle('btn-outline-primary',   !isThis && b.dataset.tipoFac === 'VENTA');
        b.classList.toggle('btn-outline-secondary', !isThis && b.dataset.tipoFac !== 'VENTA');
      });
      const inp = container.querySelector('#ac-factura-input');
      const dd  = container.querySelector('#ac-factura-dd');
      if (inp) inp.value = '';
      if (dd)  dd.classList.remove('open');
    }

    tabsFac.forEach(btn => {
      btn.addEventListener('click', () => _activarTabFac(btn.dataset.tipoFac));
    });
    _activarTabFac('VENTA'); // estado inicial

    // Autocompletados con renders enriquecidos
    _initAC(container, 'factura',
      // endpoint como función para capturar naturalezaFac en el momento de la búsqueda
      (q) => `${API_TX_BASE}search-facturas/?naturaleza=${naturalezaFac}&q=${encodeURIComponent(q)}`,
      (f) => {
        const natBadge = f.naturaleza === 'VENTA'
          ? `<span class="badge bg-primary" style="font-size:.58rem;"><i class="bi bi-arrow-up-right me-1"></i>Venta</span>`
          : `<span class="badge bg-warning text-dark" style="font-size:.58rem;"><i class="bi bi-arrow-down-left me-1"></i>Compra</span>`;

        const PAGO_MAP = {
          'PAGADA':       ['bg-success',           'Pagada'],
          'PAGO_PARCIAL': ['bg-info text-dark',    'Parcial'],
          'NO_PAGADA':    ['bg-danger',            'Sin pago'],
        };
        const [pagoCls, pagoLbl] = PAGO_MAP[f.estado_pago] || ['bg-secondary', f.estado_pago || '—'];
        const pagoBadge = `<span class="badge ${pagoCls}" style="font-size:.58rem;">${pagoLbl}</span>`;

        const docNum = (f.prefijo ? f.prefijo + '-' : '') + (f.numero || '—');
        return `
          <div class="d-flex justify-content-between align-items-center gap-1 mb-1">
            <span class="ac-name fw-bold text-truncate">${docNum}</span>
            <div class="d-flex gap-1 flex-shrink-0">${natBadge}${pagoBadge}</div>
          </div>
          <div class="ac-sub text-truncate"><i class="bi bi-person me-1"></i>${f.nombre || '—'}</div>
          <div class="ac-sub d-flex justify-content-between">
            <span><i class="bi bi-credit-card me-1"></i>${f.nit || '—'}</span>
            <span class="fw-semibold text-success">$${_fmt(f.total)}</span>
          </div>
          <div class="ac-sub text-muted">${f.tipo_display || ''} · ${f.fecha || ''}</div>`;
      },
      (f) => {
        const docNum = (f.prefijo ? f.prefijo + '-' : '') + (f.numero || '—');
        _setChip(container, 'factura', f.uuid,
          `${docNum} — ${f.nombre || '—'}`,
          `NIT: ${f.nit || '—'} · $${_fmt(f.total)} · ${f.fecha || ''}`);
      }
    );

    _initAC(container, 'proveedor',
      (q) => `${API_TX_BASE}search-proveedores/?q=${encodeURIComponent(q)}`,
      (p) => {
        const banco = p.banco ? `<span class="badge bg-light text-dark border" style="font-size:.58rem;">${p.banco}</span>` : '';
        return `
          <div class="ac-name text-truncate">${p.razon_social}</div>
          <div class="ac-sub d-flex justify-content-between align-items-center">
            <span>${p.tipo_documento}: ${p.numero_documento}</span>
            ${banco}
          </div>
          ${p.ciudad ? `<div class="ac-sub"><i class="bi bi-geo-alt me-1" style="font-size:.65rem;"></i>${p.ciudad}</div>` : ''}`;
      },
      (p) => _setChip(container, 'proveedor', p.uuid,
        p.nombre_comercial || p.razon_social,
        `${p.tipo_documento}: ${p.numero_documento}${p.ciudad ? ' · ' + p.ciudad : ''}`)
    );

    _initAC(container, 'cliente',
      (q) => `${API_TX_BASE}search-clientes/?q=${encodeURIComponent(q)}`,
      (c) => {
        const nombre = c.nombre_comercial || c.razon_social;
        return `
          <div class="ac-name text-truncate">${nombre}</div>
          <div class="ac-sub d-flex justify-content-between align-items-center">
            <span>${c.tipo_documento}: ${c.numero_documento}</span>
            ${c.ciudad ? `<span class="text-muted">${c.ciudad}</span>` : ''}
          </div>
          ${c.email ? `<div class="ac-sub"><i class="bi bi-envelope me-1" style="font-size:.65rem;"></i>${c.email}</div>` : ''}`;
      },
      (c) => _setChip(container, 'cliente', c.uuid,
        c.nombre_comercial || c.razon_social,
        `${c.tipo_documento}: ${c.numero_documento}${c.ciudad ? ' · ' + c.ciudad : ''}`)
    );

    // Guardar vínculo
    const btnGuardar = container.querySelector('#btn-guardar-vinculo');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', async () => {
        const uuid      = concUuid.value;
        if (!uuid) return;
        const tipoMov   = container.querySelector('#conc-tipo-movimiento')?.value || 'INGRESO';
        const esEgreso  = tipoMov === 'EGRESO';

        const notasVal = container.querySelector('#conc-notas')?.value?.trim() || null;

        // Solo enviar el tercero relevante según tipo de movimiento
        const payload = {
          factura_uuid:       hidFact?.value?.trim() || null,
          proveedor_uuid:     esEgreso  ? (hidProv?.value?.trim() || null) : null,
          cliente_uuid:       !esEgreso ? (hidCli?.value?.trim()  || null) : null,
          notas_conciliacion: notasVal,
        };

        if (!payload.factura_uuid && !payload.proveedor_uuid && !payload.cliente_uuid) {
          const hint = esEgreso
            ? 'Selecciona al menos una factura de compra o un proveedor.'
            : 'Selecciona al menos una factura de venta o un cliente.';
          _mostrarFeedback(feedback, 'warning', hint);
          return;
        }

        btnGuardar.disabled = true;
        btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

        try {
          const res = await w.Sintel.Core.Http.request('PATCH', `${API_TX_BASE}${uuid}/conciliar/`, payload);
          if (res?.ok) {
            _mostrarFeedback(feedback, 'success', '<i class="bi bi-check-circle me-1"></i>Vínculo guardado correctamente.');
            _actualizarFilaBadge(container, uuid, payload, true);
          } else {
            const msg = res?.data?.detail || JSON.stringify(res?.data) || 'Error al guardar.';
            _mostrarFeedback(feedback, 'danger', msg);
          }
        } catch (e) {
          _mostrarFeedback(feedback, 'danger', 'Error de conexión.');
        }

        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Guardar vínculo';
      });
    }

    // Quitar vínculo
    const btnQuitar = container.querySelector('#btn-quitar-vinculo');
    if (btnQuitar) {
      btnQuitar.addEventListener('click', async () => {
        const uuid = concUuid.value;
        if (!uuid) return;
        btnQuitar.disabled = true;
        try {
          const payload = { factura_uuid: null, proveedor_uuid: null, cliente_uuid: null, conciliado: false };
          const res = await w.Sintel.Core.Http.request('PATCH', `${API_TX_BASE}${uuid}/conciliar/`, payload);
          if (res?.ok) {
            _limpiarChip(container, 'factura');
            _limpiarChip(container, 'proveedor');
            _limpiarChip(container, 'cliente');
            _actualizarFilaBadge(container, uuid, payload, false);
            _mostrarFeedback(feedback, 'warning', 'Vínculo eliminado.');
          }
        } catch (e) {}
        btnQuitar.disabled = false;
      });
    }

    // ── Paso 5: Aplicaciones multiples (Fase 5-12, v3.0) ────────────────
    const btnSugerencias = container.querySelector('#btn-sugerencias');
    if (btnSugerencias) {
      btnSugerencias.addEventListener('click', async () => {
        const uuid = concUuid.value;
        if (!uuid) return;
        btnSugerencias.disabled = true;
        const res = await w.Sintel.Bancos.API.transacciones.sugerencias(uuid);
        btnSugerencias.disabled = false;
        if (!res?.ok) return;
        _renderSugerencias(container, res.data?.results || []);
      });
    }

    const btnAgregar = container.querySelector('#btn-agregar-aplicacion');
    if (btnAgregar) {
      btnAgregar.addEventListener('click', async () => {
        const uuid = concUuid.value;
        const feedback = container.querySelector('#apl-feedback');
        if (!uuid) return;

        const tipo = container.querySelector('#apl-tipo')?.value;
        const montoRaw = container.querySelector('#apl-monto')?.value;
        const notas = container.querySelector('#apl-notas')?.value?.trim() || null;
        const referenciaUuid = container.querySelector('#apl-referencia-uuid')?.value || null;

        if (!montoRaw || parseFloat(montoRaw) <= 0) {
          _mostrarFeedback(feedback, 'warning', 'Ingresa un monto valido mayor a 0.');
          return;
        }

        btnAgregar.disabled = true;
        const payload = {
          tipo_referencia: tipo,
          monto_aplicado: montoRaw,
          referencia_uuid: referenciaUuid,
          notas,
        };
        const res = await w.Sintel.Bancos.API.transacciones.crearAplicacion(uuid, payload);
        btnAgregar.disabled = false;

        if (!res?.ok) {
          const msg = res?.data?.monto_aplicado?.[0] || res?.data?.detail || JSON.stringify(res?.data) || 'Error al aplicar.';
          _mostrarFeedback(feedback, 'danger', msg);
          return;
        }

        container.querySelector('#apl-monto').value = '';
        container.querySelector('#apl-notas').value = '';
        container.querySelector('#apl-referencia-uuid').value = '';
        container.querySelector('#apl-sugerencias-box')?.classList.add('d-none');
        _mostrarFeedback(feedback, 'success', 'Aplicacion agregada.');
        await _cargarAplicaciones(container, uuid);
      });
    }
  }

  // ── Aplicaciones multiples (Fase 5-12) ────────────────────────────────
  async function _cargarAplicaciones(container, uuid) {
    const [aplicacionesRes, txRes] = await Promise.all([
      w.Sintel.Bancos.API.transacciones.listarAplicaciones(uuid),
      w.Sintel.Bancos.API.transacciones.get(uuid),
    ]);
    const aplicaciones = aplicacionesRes?.ok ? (aplicacionesRes.data?.results || []) : [];
    const tx = txRes?.ok ? txRes.data : null;

    _renderAplicaciones(container, aplicaciones);

    if (tx) {
      const aplicado = parseFloat(tx.monto_aplicado || '0');
      const pendiente = parseFloat(tx.monto_pendiente || '0');
      const monto = aplicado + pendiente;
      const pct = monto > 0 ? Math.min(100, Math.round((aplicado / monto) * 100)) : 0;

      const elAplicado = container.querySelector('#apl-total-aplicado');
      const elPendiente = container.querySelector('#apl-total-pendiente');
      const bar = container.querySelector('#apl-progress-bar');
      if (elAplicado) elAplicado.textContent = '$' + _fmt(aplicado);
      if (elPendiente) elPendiente.textContent = '$' + _fmt(pendiente);
      if (bar) bar.style.width = pct + '%';

      // Sincroniza el badge de estado de la fila con el estado real del servidor
      // (conciliado puede haber ascendido a True via aplicaciones, ver crud_service).
      const row = container.querySelector(`.tx-row[data-uuid="${uuid}"]`);
      if (row) {
        row.dataset.conciliado = tx.conciliado ? '1' : '0';
        const badge = row.querySelector('td:last-child .badge');
        if (badge && tx.conciliado) {
          badge.className = 'badge bg-success';
          badge.style.fontSize = '.62rem';
          badge.innerHTML = '<i class="bi bi-check2-all me-1"></i>Conciliado';
        } else if (badge && tx.estado_aplicacion === 'PARCIAL') {
          badge.className = 'badge bg-warning text-dark';
          badge.style.fontSize = '.62rem';
          badge.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Parcial';
        }
      }
      _recalcularKpiConciliacion(container);
    }
  }

  // Fase 19: el KPI de Pendientes/Conciliados se renderiza server-side al
  // abrir el offcanvas -- tras aplicar/quitar una aplicacion el badge de la
  // fila ya se actualiza en el DOM (arriba), asi que el conteo se recalcula
  // aqui mismo contando filas en vez de re-pedir todo el offcanvas al server.
  function _recalcularKpiConciliacion(container) {
    const totalEl = container.querySelector('#kpi-total');
    const total = totalEl ? parseInt(totalEl.textContent, 10) || 0 : 0;
    if (!total) return;
    const conciliadas = container.querySelectorAll('.tx-row[data-conciliado="1"]').length;
    const elConc = container.querySelector('#kpi-conciliados');
    const elPend = container.querySelector('#kpi-pendientes');
    if (elConc) elConc.textContent = String(conciliadas);
    if (elPend) elPend.textContent = String(total - conciliadas);
  }

  function _renderAplicaciones(container, aplicaciones) {
    const box = container.querySelector('#apl-lista');
    if (!box) return;
    if (!aplicaciones.length) {
      box.innerHTML = '<div class="text-muted" style="font-size:.72rem;">Sin aplicaciones registradas.</div>';
      return;
    }
    box.innerHTML = aplicaciones.map(a => `
      <div class="d-flex justify-content-between align-items-center border rounded px-2 py-1 mb-1">
        <div class="min-w-0">
          <div class="fw-semibold text-truncate" style="max-width:180px;">
            ${a.tipo_referencia_display || a.tipo_referencia}
          </div>
          <div class="text-muted text-truncate" style="max-width:180px;font-size:.68rem;">
            ${a.notas ? a.notas : (a.referencia_uuid ? 'Ref: ...' + a.referencia_uuid.slice(-8) : 'Sin referencia')}
          </div>
        </div>
        <div class="d-flex align-items-center gap-2 flex-shrink-0">
          <span class="fw-bold">$${_fmt(a.monto_aplicado)}</span>
          <button type="button" class="btn btn-sm btn-link text-danger p-0 btn-eliminar-aplicacion" data-uuid="${a.uuid}" title="Quitar">
            <i class="bi bi-x-circle"></i>
          </button>
        </div>
      </div>`).join('');

    box.querySelectorAll('.btn-eliminar-aplicacion').forEach(btn => {
      btn.addEventListener('click', async () => {
        const aplicacionUuid = btn.dataset.uuid;
        const txUuid = container.querySelector('#conc-uuid')?.value;
        btn.disabled = true;
        const res = await w.Sintel.Bancos.API.aplicaciones.eliminar(aplicacionUuid);
        if (res?.ok && txUuid) {
          await _cargarAplicaciones(container, txUuid);
        } else {
          btn.disabled = false;
        }
      });
    });
  }

  const _TIPO_POR_CANDIDATO = {
    FACTURA_VENTA: 'FACTURA_VENTA',
    FACTURA_COMPRA: 'FACTURA_COMPRA',
    CLIENTE: 'CARTERA',
    PROVEEDOR: 'CUENTA_POR_PAGAR',
    GASTO: 'GASTO',
  };

  function _renderSugerencias(container, sugerencias) {
    const box = container.querySelector('#apl-sugerencias-box');
    if (!box) return;
    if (!sugerencias.length) {
      box.innerHTML = '<div class="text-muted p-2" style="font-size:.72rem;">Sin sugerencias para este movimiento.</div>';
      box.classList.remove('d-none');
      return;
    }
    box.innerHTML = sugerencias.map((s, i) => `
      <div class="ac-item" data-idx="${i}">
        <div class="d-flex justify-content-between">
          <span class="ac-name text-truncate">${s.descripcion}</span>
          <span class="badge bg-info text-dark" style="font-size:.6rem;">${Math.round(s.score * 100)}%</span>
        </div>
        <div class="ac-sub">${(s.reason || []).join(' · ')}</div>
      </div>`).join('');
    box.classList.remove('d-none');

    box.querySelectorAll('.ac-item').forEach((el, i) => {
      el.addEventListener('click', () => {
        const s = sugerencias[i];
        const tipoSel = container.querySelector('#apl-tipo');
        const montoInp = container.querySelector('#apl-monto');
        const notasInp = container.querySelector('#apl-notas');
        const refInp = container.querySelector('#apl-referencia-uuid');
        if (tipoSel && _TIPO_POR_CANDIDATO[s.tipo]) tipoSel.value = _TIPO_POR_CANDIDATO[s.tipo];
        if (montoInp && s.monto) montoInp.value = s.monto;
        if (notasInp) notasInp.value = s.descripcion;
        if (refInp) refInp.value = s.uuid;
        box.classList.add('d-none');
      });
    });
  }

  // ── Helpers de autocomplete ───────────────────────────────────────────
  function _initAC(container, tipo, endpoint, renderItem, onSelect) {
    const input = container.querySelector(`#ac-${tipo}-input`);
    const dd    = container.querySelector(`#ac-${tipo}-dd`);
    if (!input || !dd) return;

    let timer;
    input.addEventListener('input', () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { dd.classList.remove('open'); return; }
      timer = setTimeout(async () => {
        try {
          // endpoint puede ser función (q)=>url o string prefijo
          const url = typeof endpoint === 'function' ? endpoint(q) : endpoint + encodeURIComponent(q);
          const res = await w.Sintel.Core.Http.request('GET', url);
          const items = res?.ok && res?.data?.results ? res.data.results : [];
          dd.innerHTML = '';
          if (!items.length) {
            dd.innerHTML = `<div class="ac-item text-muted small py-2">Sin resultados para "${q}"</div>`;
          } else {
            items.forEach(item => {
              const el = d.createElement('div');
              el.className = 'ac-item';
              el.innerHTML = renderItem(item);
              el.addEventListener('click', () => {
                onSelect(item);
                input.value = '';
                dd.classList.remove('open');
              });
              dd.appendChild(el);
            });
          }
          dd.classList.add('open');
        } catch (e) { console.error(`${MOD} AC error`, tipo, e); }
      }, 280);
    });

    d.addEventListener('click', (e) => {
      if (!input.contains(e.target) && !dd.contains(e.target)) dd.classList.remove('open');
    });
  }

  // ── Helpers de chips ─────────────────────────────────────────────────
  function _setChip(container, tipo, uuid, label, sub) {
    const chip    = container.querySelector(`#chip-${tipo}`);
    const lblEl   = container.querySelector(`#chip-${tipo}-label`);
    const subEl   = container.querySelector(`#chip-${tipo}-sub`);
    const aw      = container.querySelector(`#aw-${tipo}`);
    const hidEl   = container.querySelector(`#conc-${tipo}-uuid`);

    if (!chip || !hidEl) return;
    hidEl.value        = uuid;
    if (lblEl) lblEl.textContent = label;
    if (subEl) subEl.textContent = sub || '';
    chip.classList.remove('d-none');
    if (aw) aw.style.display = 'none';
  }

  function _limpiarChip(container, tipo) {
    const chip  = container.querySelector(`#chip-${tipo}`);
    const aw    = container.querySelector(`#aw-${tipo}`);
    const input = container.querySelector(`#ac-${tipo}-input`);
    const hidEl = container.querySelector(`#conc-${tipo}-uuid`);

    if (hidEl) hidEl.value = '';
    if (chip)  chip.classList.add('d-none');
    if (aw)    aw.style.display = '';
    if (input) input.value = '';
  }

  // ── Helpers de feedback y badge ──────────────────────────────────────
  function _mostrarFeedback(el, tipo, msg) {
    if (!el) return;
    el.className = `alert alert-${tipo} py-2 px-3 small`;
    el.innerHTML = msg;
    el.classList.remove('d-none');
    setTimeout(() => el.classList.add('d-none'), 5000);
  }

  function _actualizarFilaBadge(container, uuid, payload, conciliado) {
    const row = container.querySelector(`.tx-row[data-uuid="${uuid}"]`);
    if (!row) return;

    row.dataset.conciliado    = conciliado ? '1' : '0';
    row.dataset.facturaUuid   = payload.factura_uuid   || '';
    row.dataset.proveedorUuid = payload.proveedor_uuid || '';
    row.dataset.clienteUuid   = payload.cliente_uuid   || '';

    // Marcar el paso 1 como completado visualmente
    if (conciliado) {
      container.querySelector('.conc-step:first-of-type .conc-step-num')?.classList.add('done');
    }

    const badge = row.querySelector('td:last-child .badge');
    if (!badge) return;

    if (conciliado) {
      const partes = [];
      if (payload.factura_uuid)   partes.push('Factura');
      if (payload.proveedor_uuid) partes.push('Proveedor');
      if (payload.cliente_uuid)   partes.push('Cliente');
      const lbl = partes.map(p => p.charAt(0)).join('+') || 'OK';
      badge.className   = 'badge bg-success';
      badge.style.fontSize = '.62rem';
      badge.innerHTML   = `<i class="bi bi-check2-all me-1"></i>${lbl}`;
    } else {
      badge.className   = 'badge bg-light text-muted border';
      badge.style.fontSize = '.62rem';
      badge.innerHTML   = '<i class="bi bi-dash me-1"></i>Pendiente';
    }
  }

  function _fmt(val) {
    return new Intl.NumberFormat('es-CO', { minimumFractionDigits: 0 }).format(parseFloat(val) || 0);
  }

  // ── Guardar extracto ─────────────────────────────────────────────────
  async function _guardar(form) {
    if (!form.checkValidity()) return form.reportValidity();

    const api = w.Sintel?.Bancos?.API;
    if (!api?.extractos) return;

    const formData = new FormData();
    formData.append('cuenta', form.querySelector('#cuenta_uuid')?.value || '');
    formData.append('mes',    form.querySelector('#mes')?.value || '');
    formData.append('anio',   form.querySelector('#anio')?.value || '');

    const fileInput = form.querySelector('#archivo');
    if (fileInput?.files?.length) formData.append('archivo_s3', fileInput.files[0]);

    const btn = form.closest('.offcanvas')?.querySelector('#btn-guardar-extracto');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...'; }

    const res = await api.extractos.save(formData);

    if (!res?.ok) {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-cloud-upload me-1"></i>Importar y Procesar'; }
      return w.UIManager?.handleError(res, MOD, { errorContainerSelector: '#form-extracto-feedback' });
    }

    w.UIManager?.showSuccess('Extracto importado con éxito');
    const offcanvasEl = form.closest('.offcanvas');
    if (offcanvasEl) {
      w.UIManager?.handleOffcanvas ? w.UIManager.handleOffcanvas(offcanvasEl, 'hide')
        : bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
    }
    w.Sintel.Bancos.ExtractoList?.refresh();
  }

  // ── Export ───────────────────────────────────────────────────────────
  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.ExtractoEditor = { openOffcanvas, openDetalle };

})(window, document);
