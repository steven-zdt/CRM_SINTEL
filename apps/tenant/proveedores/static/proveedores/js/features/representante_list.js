/**
 * representante_list.js — Tabla de Representantes v3.17.2
 * Namespace: window.Sintel.Proveedores.Representante
 *
 * BUGFIX v3.17.2: api.listar() ahora retorna res.data (no el objeto {ok,status,data}).
 * Se usa resData.results para obtener el array de representantes.
 */

window.Sintel = window.Sintel || {};
window.Sintel.Proveedores = window.Sintel.Proveedores || {};
window.Sintel.Proveedores.Representante = window.Sintel.Proveedores.Representante || {};

(function (mod) {
  'use strict';

  const api = window.Sintel.Representante;

  /**
   * Carga y renderiza la tabla de representantes de un proveedor.
   * @param {string} proveedorUuid
   */
  mod.cargarTabla = async (proveedorUuid) => {
    try {
      const resData = await api.listar(proveedorUuid);
      // resData = { count: N, results: [...] }  (respuesta paginada DRF)
      const lista = resData?.results || (Array.isArray(resData) ? resData : []);
      const container = document.getElementById('representantes-container');
      const proveedorNombre = container?.dataset?.proveedorNombre || '';
      mod.renderizarTabla(lista, proveedorUuid, proveedorNombre);
    } catch (error) {
      console.error('[representante_list] Error cargando representantes:', error);
      document.getElementById('representantes-empty-state')?.classList.remove('d-none');
    }
  };

  /**
   * Renderiza la tabla con datos provistos.
   * @param {Array}  representantes  Array de objetos Representante
   * @param {string} proveedorUuid   UUID del proveedor padre (para botones de accion)
   * @param {string} proveedorNombre Nombre del proveedor (para badge del editor)
   */
  mod.renderizarTabla = (representantes, proveedorUuid, proveedorNombre) => {
    const tbody      = document.getElementById('tbody-representantes');
    const emptyState = document.getElementById('representantes-empty-state');

    if (!tbody) return;

    if (!Array.isArray(representantes) || representantes.length === 0) {
      tbody.innerHTML = '';
      emptyState?.classList.remove('d-none');
      return;
    }

    emptyState?.classList.add('d-none');

    const escNombre = (s) => (s || '').replace(/'/g, "\\'");

    tbody.innerHTML = representantes.map(rep => `
      <tr data-uuid="${rep.uuid}">
        <td>
          <strong>${rep.numero_documento || '—'}</strong>
          <small class="d-block text-muted">${api.getTipoDocumentoDisplay(rep.tipo_documento)}</small>
        </td>
        <td>
          ${rep.nombre_completo || '—'}
          ${rep.es_principal ? '<span class="badge bg-success ms-2" style="font-size:.65rem;">Principal</span>' : ''}
        </td>
        <td>${rep.cargo || '—'}</td>
        <td>
          <small class="text-truncate d-block" style="max-width:140px;">
            ${rep.email_contacto || rep.telefono_contacto || '—'}
          </small>
        </td>
        <td>
          <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-primary btn-sm"
                    title="Editar"
                    onclick="window.Sintel.Proveedores.abrirFormRepresentante('${rep.uuid}', '${proveedorUuid || ''}', '${escNombre(proveedorNombre)}')">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-outline-danger btn-sm"
                    title="Eliminar"
                    onclick="window.Sintel.Proveedores.eliminarRepresentante('${rep.uuid}', '${proveedorUuid || ''}')">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  };

})(window.Sintel.Proveedores.Representante);
