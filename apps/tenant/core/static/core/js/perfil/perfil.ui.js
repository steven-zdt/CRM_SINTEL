/**
 * UI Module para Perfil - Renderizado y Eventos
 */

(function() {
  'use strict';

  if (typeof window.perfilAPI === 'undefined') {
    console.error('[perfil.ui] perfilAPI no está disponible. Cargar perfil.api.js primero.');
    return;
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Renderiza el perfil del usuario
   * @param {HTMLElement} container - Contenedor donde renderizar
   */
  async function renderPerfil(container) {
    if (!container) {
      console.error('[perfil.ui] Container no encontrado');
      return;
    }

    container.innerHTML = '<div class="text-center text-muted py-4">Cargando perfil...</div>';

    try {
      const r = await window.perfilAPI.getMiPerfil();

      if (!r.ok) {
        container.innerHTML = `<div class="alert alert-danger">Error ${r.status}: ${escapeHtml(r.data?.detail || 'Error desconocido')}</div>`;
        return;
      }

      const perfil = r.data;
      
      container.innerHTML = `
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="card-title mb-0">👤 Perfil del Usuario</h5>
            <button id="btn-perfil-edit" class="btn btn-sm btn-primary">Editar</button>
          </div>
          <div class="card-body">
            <div id="perfil-feedback" class="alert d-none" role="alert"></div>
            <div class="row">
              <div class="col-md-6 mb-3">
                <strong>Nombre:</strong><br>
                <span>${escapeHtml(perfil.nombre || '-')}</span>
              </div>
              <div class="col-md-6 mb-3">
                <strong>Email:</strong><br>
                <span>${escapeHtml(perfil.email || '-')}</span>
              </div>
              ${perfil.cargo ? `
              <div class="col-md-6 mb-3">
                <strong>Cargo:</strong><br>
                <span>${escapeHtml(perfil.cargo)}</span>
              </div>
              ` : ''}
              ${perfil.departamento ? `
              <div class="col-md-6 mb-3">
                <strong>Departamento:</strong><br>
                <span>${escapeHtml(perfil.departamento)}</span>
              </div>
              ` : ''}
              ${perfil.telefono ? `
              <div class="col-md-6 mb-3">
                <strong>Teléfono:</strong><br>
                <span>${escapeHtml(perfil.telefono)}</span>
              </div>
              ` : ''}
              ${perfil.avatar ? `
              <div class="col-md-12 mb-3">
                <strong>Avatar:</strong><br>
                <img src="${escapeHtml(perfil.avatar)}" alt="Avatar" style="max-height: 100px;" />
              </div>
              ` : ''}
            </div>
          </div>
        </div>
      `;

      // Bind evento editar
      const btnEdit = container.querySelector('#btn-perfil-edit');
      if (btnEdit) {
        btnEdit.addEventListener('click', () => renderPerfilForm(container, perfil));
      }

    } catch (error) {
      console.error('[perfil.ui] Error cargando perfil:', error);
      container.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  /**
   * Renderiza formulario de edición
   */
  function renderPerfilForm(container, perfil) {
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h5 class="card-title mb-0">Editar Perfil</h5>
        </div>
        <div class="card-body">
          <div id="perfil-form-feedback" class="alert d-none" role="alert"></div>
          <form id="perfil-form">
            <div class="row">
              <div class="col-md-6 mb-3">
                <label for="perfil-nombre" class="form-label">Nombre</label>
                <input type="text" class="form-control" id="perfil-nombre" value="${escapeHtml(perfil.nombre || '')}" />
              </div>
              <div class="col-md-6 mb-3">
                <label for="perfil-email" class="form-label">Email</label>
                <input type="email" class="form-control" id="perfil-email" value="${escapeHtml(perfil.email || '')}" readonly />
              </div>
              <div class="col-md-6 mb-3">
                <label for="perfil-cargo" class="form-label">Cargo</label>
                <input type="text" class="form-control" id="perfil-cargo" value="${escapeHtml(perfil.cargo || '')}" />
              </div>
              <div class="col-md-6 mb-3">
                <label for="perfil-departamento" class="form-label">Departamento</label>
                <input type="text" class="form-control" id="perfil-departamento" value="${escapeHtml(perfil.departamento || '')}" />
              </div>
              <div class="col-md-6 mb-3">
                <label for="perfil-telefono" class="form-label">Teléfono</label>
                <input type="text" class="form-control" id="perfil-telefono" value="${escapeHtml(perfil.telefono || '')}" />
              </div>
              <div class="col-md-6 mb-3">
                <label for="perfil-avatar" class="form-label">Avatar</label>
                <input type="file" class="form-control" id="perfil-avatar" accept="image/*" />
              </div>
            </div>
            <div class="d-flex gap-2">
              <button type="submit" class="btn btn-primary">Guardar</button>
              <button type="button" class="btn btn-secondary" id="btn-perfil-cancel">Cancelar</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const form = container.querySelector('#perfil-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleSavePerfil(container, perfil);
      });
    }

    const btnCancel = container.querySelector('#btn-perfil-cancel');
    if (btnCancel) {
      btnCancel.addEventListener('click', () => renderPerfil(container));
    }
  }

  /**
   * Maneja el guardado del perfil
   */
  async function handleSavePerfil(container, perfilOriginal) {
    const feedback = container.querySelector('#perfil-form-feedback');
    
    const payload = {
      nombre: document.getElementById('perfil-nombre')?.value.trim(),
      cargo: document.getElementById('perfil-cargo')?.value.trim() || null,
      departamento: document.getElementById('perfil-departamento')?.value.trim() || null,
      telefono: document.getElementById('perfil-telefono')?.value.trim() || null,
    };

    const avatarFile = document.getElementById('perfil-avatar')?.files[0];

    try {
      // Actualizar perfil
      const r = await window.perfilAPI.updateMiPerfil(payload);
      
      if (!r.ok) {
        if (feedback) {
          feedback.className = 'alert alert-danger';
          feedback.textContent = r.data?.detail || `Error ${r.status}`;
          feedback.classList.remove('d-none');
        }
        return;
      }

      // Si hay avatar, actualizarlo por separado
      if (avatarFile) {
        const rAvatar = await window.perfilAPI.updateMiPerfilAvatar(avatarFile);
        if (!rAvatar.ok) {
          console.warn('[perfil.ui] Error actualizando avatar:', rAvatar.data);
        }
      }

      if (feedback) {
        feedback.className = 'alert alert-success';
        feedback.textContent = 'Perfil actualizado correctamente';
        feedback.classList.remove('d-none');
      }

      setTimeout(() => renderPerfil(container), 1000);

    } catch (error) {
      console.error('[perfil.ui] Error guardando perfil:', error);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error: ${error.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
    }
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.perfilUI = {
      renderPerfil,
    };
  }
})();
