// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * bancos.main.js - Orquestador Central del Módulo Bancos
 * Namespace: window.Sintel.Bancos.Main
 * ⚠️ FSD / Vanilla JS
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:main]';
  let initialized = false;
  let currentDeleteUuid = null;
  let currentDeleteType = null; // 'cuenta' o 'extracto'

  function init() {
    if (initialized) return;

    console.log(`${MOD} Ejecutando orquestación inicial del módulo Bancos...`);

    // 1. Inicializar pestaña activa por defecto
    const tabCuentas = d.getElementById('tab-cuentas');
    if (tabCuentas && tabCuentas.classList.contains('active')) {
      if (w.Sintel.Bancos.CuentaList?.init) {
        w.Sintel.Bancos.CuentaList.init();
      }
    }

    // 2. Escuchar cambios de sub-pestañas
    bindSubTabs();

    // 3. Delegar eventos de acciones de filas (Listado y Tablas)
    bindActionsDelegation();

    initialized = true;
    console.log(`${MOD} Módulo Bancos estabilizado.`);
  }

  function bindSubTabs() {
    const tabCuentas = d.getElementById('tab-cuentas');
    const tabExtractos = d.getElementById('tab-extractos');

    if (tabCuentas) {
      tabCuentas.addEventListener('shown.bs.tab', () => {
        const list = w.Sintel.Bancos.CuentaList;
        if (list?.init) list.init();
        // redraw(true) recalcula anchos de columna cuando el container estaba oculto al inicializar
        if (list?.redraw) list.redraw();
      });
    }

    if (tabExtractos) {
      tabExtractos.addEventListener('shown.bs.tab', () => {
        const list = w.Sintel.Bancos.ExtractoList;
        if (list?.init) list.init();
        if (list?.redraw) list.redraw();
      });
    }
  }

  function bindActionsDelegation() {
    d.body.addEventListener('click', async function(e) {
      // 1. Editar Cuenta
      const btnEditCuenta = e.target.closest('.btn-edit-cuenta');
      if (btnEditCuenta) {
        const uuid = btnEditCuenta.dataset.id;
        if (w.Sintel.Bancos.CuentaEditor?.openOffcanvas) {
          w.Sintel.Bancos.CuentaEditor.openOffcanvas(uuid);
        }
        return;
      }

      // 2. Eliminar Cuenta
      const btnDeleteCuenta = e.target.closest('.btn-delete-cuenta');
      if (btnDeleteCuenta) {
        const uuid = btnDeleteCuenta.dataset.id;
        confirmarEliminacion(uuid, 'cuenta');
        return;
      }

      // 3. Ver Detalle de Extracto
      const btnViewExtracto = e.target.closest('.btn-view-extracto');
      if (btnViewExtracto) {
        const uuid = btnViewExtracto.dataset.id;
        if (w.Sintel.Bancos.ExtractoEditor?.openDetalle) {
          w.Sintel.Bancos.ExtractoEditor.openDetalle(uuid);
        }
        return;
      }

      // 3b. Conciliar Extracto (atajo directo — abre el mismo detalle)
      const btnConciliar = e.target.closest('.btn-conciliar-extracto');
      if (btnConciliar) {
        const uuid = btnConciliar.dataset.id;
        if (w.Sintel.Bancos.ExtractoEditor?.openDetalle) {
          w.Sintel.Bancos.ExtractoEditor.openDetalle(uuid);
        }
        return;
      }

      // 4. Procesar Extracto
      const btnProcesarExtracto = e.target.closest('.btn-procesar-extracto');
      if (btnProcesarExtracto) {
        const uuid = btnProcesarExtracto.dataset.id;
        if (w.Sintel.Bancos.ExtractoList?.procesarExtracto) {
          w.Sintel.Bancos.ExtractoList.procesarExtracto(uuid);
        }
        return;
      }

      // 5. Eliminar Extracto
      const btnDeleteExtracto = e.target.closest('.btn-delete-extracto');
      if (btnDeleteExtracto) {
        const uuid = btnDeleteExtracto.dataset.id;
        confirmarEliminacion(uuid, 'extracto');
        return;
      }
    });
  }

  async function confirmarEliminacion(uuid, type) {
    const confirmado = await w.UIManager?.confirm('Esta seguro de que desea eliminar este registro? Esta accion no se puede deshacer y puede afectar las transacciones asociadas.');
    if (!confirmado) return;
    currentDeleteUuid = uuid;
    currentDeleteType = type;
    await ejecutarEliminacion();
  }

  async function ejecutarEliminacion() {
    if (!currentDeleteUuid) return;

    let res;
    if (currentDeleteType === 'cuenta') {
      res = await w.Sintel.Bancos.API.cuentas.delete(currentDeleteUuid);
    } else if (currentDeleteType === 'extracto') {
      res = await w.Sintel.Bancos.API.extractos.delete(currentDeleteUuid);
    }

    if (res && res.ok) {
      if (w.UIManager?.showSuccess) {
        w.UIManager.showSuccess('Registro eliminado exitosamente');
      }
      if (currentDeleteType === 'cuenta') {
        w.Sintel.Bancos.CuentaList?.refresh();
      } else {
        w.Sintel.Bancos.ExtractoList?.refresh();
      }
    } else {
      if (w.UIManager?.handleError) {
        w.UIManager.handleError(res, MOD);
      }
    }

    currentDeleteUuid = null;
    currentDeleteType = null;
  }

  // Registro en Namespace Global
  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.Main = {
    init: init,
    refresh: () => {
      w.Sintel.Bancos.CuentaList?.refresh();
      w.Sintel.Bancos.ExtractoList?.refresh();
    }
  };

  // Escuchar activación de tab del módulo
  d.addEventListener('tab-activated', function (event) {
    if (event.detail?.tabName === 'bancos') {
      setTimeout(function () {
        init();
        requestAnimationFrame(function () {
          w.Sintel.Bancos.CuentaList?.redraw?.();
          w.Sintel.Bancos.ExtractoList?.redraw?.();
        });
      }, 100);
    }
  });

  // Fallback: solo si el tab ya es visible al cargar
  function _initSiVisible() {
    const section = d.getElementById('tab-bancos');
    if (section && section.style.display !== 'none') init();
  }

  if (d.readyState === 'complete') _initSiVisible();
  else w.addEventListener('load', _initSiVisible);

})(window, document);
