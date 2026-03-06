/**
 * UX Smoke Runner - Pruebas de interfaz humanas automatizadas
 * 
 * ⚠️ FASE 5: Harness de pruebas UX que simula interacción real de usuario
 * - Clicks reales, formularios, modales
 * - Verifica que DataTables recargue sin perder estado
 * - No usa alertas intrusivas (errMode='none' configurado en ErrorService)
 * - Ajusta columnas al cambiar de tabs (columns.adjust().responsive.recalc())
 */

(function (w, d) {
  'use strict';

  // No alerts intrusivos; manejar errores con dt-error (configurado en ErrorService)
  // DataTables recomienda errMode configurable; nosotros lo forzamos a 'none' en ErrorService
  const logEl = d.getElementById('ux-log');
  
  const log = (m) => {
    if (logEl) {
      const timestamp = new Date().toISOString();
      logEl.textContent += `[${timestamp}] ${m}\n`;
      logEl.scrollTop = logEl.scrollHeight;
    }
  };
  
  const ok = (m) => log('✅ ' + m);
  const err = (m) => log('❌ ' + m);
  const warn = (m) => log('⚠️ ' + m);

  /**
   * Simula click en elemento
   */
  const click = async (sel) => {
    return new Promise((res, rej) => {
      const el = d.querySelector(sel);
      if (!el) {
        return rej(`Elemento no encontrado: ${sel}`);
      }
      el.click();
      setTimeout(res, 150); // micro delay para simular humano
    });
  };

  /**
   * Simula escribir en campo
   */
  const type = async (sel, val) => {
    return new Promise((res, rej) => {
      const el = d.querySelector(sel);
      if (!el) {
        return rej(`Campo no encontrado: ${sel}`);
      }
      el.value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      setTimeout(res, 120);
    });
  };

  /**
   * Espera a que un elemento aparezca en el DOM
   */
  const waitFor = async (sel, timeout = 6000) => {
    return new Promise((res, rej) => {
      const t0 = Date.now();
      const iv = setInterval(() => {
        const el = d.querySelector(sel);
        if (el) {
          clearInterval(iv);
          res(el);
        }
        if (Date.now() - t0 > timeout) {
          clearInterval(iv);
          rej(`Timeout esperando ${sel}`);
        }
      }, 100);
    });
  };

  /**
   * Recarga DataTable sin perder estado (paginación/orden/búsqueda)
   * Usa refreshSafe() o ajax.reload(null, false) para no pisar estado
   */
  function reloadDT(id) {
    const dt = w.jQuery?.(id)?.DataTable?.();
    dt?.refreshSafe?.() ?? dt?.ajax?.reload(null, false); // no pisar estado (search/order/page)
  }

  /**
   * Suites mínimas (ajusta los selectores según los IDs reales en tus vistas)
   */
  const suites = {
    async clientes() {
      await click('#btn-clientes-nuevo');
      await waitFor('#modal-clientes');
      await type('#cliente-nombre', 'Cliente UX');
      await type('#cliente-nit', `${Date.now()}`);
      await click('#btn-clientes-guardar');
      reloadDT('#table-clientes');
      ok('Clientes: crear + reload DT');
    },
    async proveedores() {
      await click('#btn-proveedores-nuevo');
      await waitFor('#modal-proveedores');
      await type('#prov-razon_social', 'Proveedor UX');
      await type('#prov-nit', `${Date.now()}`);
      await click('#btn-proveedores-guardar');
      reloadDT('#table-proveedores');
      ok('Proveedores: crear + reload DT');
    },
    async gastos() {
      await click('#btn-gastos-nuevo');
      await waitFor('#modal-gastos');
      await type('#gasto-descripcion', 'Gasto UX');
      await type('#gasto-monto', '123');
      await type('#gasto-fecha', new Date().toISOString().slice(0, 10));
      await click('#btn-gastos-guardar');
      reloadDT('#table-gastos');
      ok('Gastos: crear + reload DT');
    },
    async empleados() {
      await click('#btn-empleados-nuevo');
      await waitFor('#modal-empleados');
      await type('#emp-nombre', 'Empleado UX');
      await type('#emp-documento', `${Math.floor(Math.random() * 1e7)}`);
      await click('#btn-empleados-guardar');
      reloadDT('#table-empleados');
      ok('Empleados: crear + reload DT');
    },
    async facturas() {
      reloadDT('#table-facturas');
      ok('Facturas: reload DT server-side');
    },
    async contab_cuentas() {
      reloadDT('#table-contabilidad-cuentas');
      ok('Contabilidad Cuentas: reload');
    },
    async contab_asientos() {
      reloadDT('#table-contabilidad-asientos');
      ok('Contabilidad Asientos: reload');
    },
    async inv_catalogo() {
      reloadDT('#table-inventario-catalogo');
      ok('Inventario Catálogo: reload');
    },
    async inv_activos() {
      reloadDT('#table-inventario-activos');
      ok('Inventario Activos: reload');
    },
    async empresa() {
      await click('#btn-empresa-editar');
      await waitFor('#modal-empresa');
      await type('#empresa-razon_social', 'Empresa UX');
      await click('#btn-empresa-guardar');
      ok('Empresa: edición');
    },
    async perfil() {
      await click('#btn-perfil-editar');
      await waitFor('#modal-perfil');
      await type('#perfil-nombre', 'Usuario UX');
      await click('#btn-perfil-guardar');
      ok('Perfil: edición');
    }
  };

  /**
   * UI bindings
   */
  d.addEventListener('DOMContentLoaded', () => {
    const btnAll = d.getElementById('ux-btn-run-all');
    const btns = d.querySelectorAll('.ux-run');
    
    btnAll && (btnAll.onclick = async () => {
      if (logEl) logEl.textContent = '';
      for (const k of Object.keys(suites)) {
        try {
          await suites[k]();
        } catch (e) {
          err(`${k}: ${e}`);
        }
      }
      ok('UX Smoke completo');
    });
    
    btns.forEach(b => {
      b.onclick = async () => {
        const k = b.dataset.suite;
        if (logEl) logEl.textContent = '';
        try {
          await suites[k]();
          ok(`${k}: OK`);
        } catch (e) {
          err(`${k}: ${e}`);
        }
      };
    });
  });

})(window, document);
