/**
 * UI Module para Contabilidad - Renderizado y Eventos
 */

(function() {
  'use strict';

  if (typeof window.contabilidadAPI === 'undefined') {
    console.error('[contabilidad.ui] contabilidadAPI no está disponible. Cargar contabilidad.api.js primero.');
    return;
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function fmtMoney(value, currency = 'COP') {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: currency,
    }).format(Number(value || 0));
  }

  async function renderContabilidad(container) {
    if (!container) {
      console.error('[contabilidad.ui] Container no encontrado');
      return;
    }

    container.innerHTML = '<div class="text-center text-muted py-4">Cargando contabilidad...</div>';

    try {
      const rCuentas = await window.contabilidadAPI.listCuentas({ limit: 20 });
      const rAsientos = await window.contabilidadAPI.listAsientos({ limit: 10 });

      if (!rCuentas.ok || !rAsientos.ok) {
        container.innerHTML = `<div class="alert alert-danger">Error cargando datos</div>`;
        return;
      }

      const cuentas = Array.isArray(rCuentas.data) ? rCuentas.data : (rCuentas.data?.results || []);
      const asientos = Array.isArray(rAsientos.data) ? rAsientos.data : (rAsientos.data?.results || []);

      container.innerHTML = `
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="card-title mb-0">📚 Contabilidad</h5>
            <div>
              <button id="btn-contabilidad-nueva-cuenta" class="btn btn-sm btn-primary me-2">Nueva Cuenta</button>
              <button id="btn-contabilidad-nuevo-asiento" class="btn btn-sm btn-success">Nuevo Asiento</button>
            </div>
          </div>
          <div class="card-body">
            <div id="contabilidad-feedback" class="alert d-none" role="alert"></div>
            
            <ul class="nav nav-tabs mb-3" role="tablist">
              <li class="nav-item">
                <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-cuentas">Cuentas</button>
              </li>
              <li class="nav-item">
                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-asientos">Asientos</button>
              </li>
            </ul>

            <div class="tab-content">
              <div class="tab-pane fade show active" id="tab-cuentas">
                <div class="table-responsive">
                  <table class="table table-sm table-hover">
                    <thead>
                      <tr>
                        <th>Código</th>
                        <th>Nombre</th>
                        <th>Tipo</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${cuentas.length === 0 ? '<tr><td colspan="4" class="text-center text-muted">No hay cuentas</td></tr>' : ''}
                      ${cuentas.map(c => `
                        <tr>
                          <td>${escapeHtml(c.codigo || '-')}</td>
                          <td>${escapeHtml(c.nombre || '-')}</td>
                          <td>${escapeHtml(c.tipo || '-')}</td>
                          <td>
                            <button class="btn btn-sm btn-outline-primary" data-action="view-cuenta" data-id="${c.id}">Ver</button>
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
              <div class="tab-pane fade" id="tab-asientos">
                <div class="table-responsive">
                  <table class="table table-sm table-hover">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Número</th>
                        <th>Descripción</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${asientos.length === 0 ? '<tr><td colspan="5" class="text-center text-muted">No hay asientos</td></tr>' : ''}
                      ${asientos.map(a => `
                        <tr>
                          <td>${a.fecha ? new Date(a.fecha).toLocaleDateString('es-CO') : '-'}</td>
                          <td>${escapeHtml(a.numero || '-')}</td>
                          <td>${escapeHtml(a.descripcion || '-')}</td>
                          <td>${escapeHtml(a.estado || '-')}</td>
                          <td>
                            <button class="btn btn-sm btn-outline-primary" data-action="view-asiento" data-id="${a.id}">Ver</button>
                            ${a.estado !== 'APROBADO' ? `<button class="btn btn-sm btn-outline-success" data-action="aprobar-asiento" data-id="${a.id}">Aprobar</button>` : ''}
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;

    } catch (error) {
      console.error('[contabilidad.ui] Error cargando contabilidad:', error);
      container.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  if (typeof window !== 'undefined') {
    window.contabilidadUI = {
      renderContabilidad,
    };
  }
})();
