/**
 * catalogo_modular.js - Módulo Atómico del Buscador NIIF v2.61
 * ⚠️ Modularización: Componente independiente y reutilizable
 * ⚠️ Delegación de eventos: Sobrevive a recargas HTMX del Offcanvas
 * ⚠️ Sincronización en cascada: Cambios en select tipo → habilita/deshabilita buscador
 * 
 * Características:
 * 1. Delegación de eventos en document.body
 * 2. Re-vinculación automática con htmx:afterOnLoad
 * 3. Sincronización Tipo ↔ Buscador
 * 4. Independiente: funciona en cualquier formulario con select#select-tipo-cuenta
 */
(function (w, d) {
  'use strict';

  const MOD = '[catalogo.modular]';
  const DEBUG = true;

  function log(msg, data = null) {
    if (DEBUG) {
      console.log(`%c${MOD} ${msg}`, 'color: #4ecdc4; font-weight: bold;', data || '');
    }
  }

  function warn(msg, data = null) {
    console.warn(`${MOD} ${msg}`, data || '');
  }

  /**
   * ═══════════════════════════════════════════════════════════════
   * PARTE 1: SINCRONIZACIÓN DEL BUSCADOR (Lógica Principal)
   * ═══════════════════════════════════════════════════════════════
   */

  /**
   * Sincroniza el estado del buscador según el tipo seleccionado
   * @param {HTMLSelectElement} selectTipo - Select con id="select-tipo-cuenta"
   */
  function sincronizarBuscador(selectTipo) {
    if (!selectTipo) {
      warn('Select tipo no encontrado');
      return;
    }

    const tipoValue = selectTipo.value;
    const inputBuscador = selectTipo.closest('form')?.querySelector('#input-buscador-niif')
      || d.getElementById('input-buscador-niif');
    const btnBuscador = selectTipo.closest('form')?.querySelector('#btn-buscar-niif')
      || d.getElementById('btn-buscar-niif');

    if (!inputBuscador) {
      warn('Input buscador no encontrado');
      return;
    }

    log(`🔄 Sincronizando buscador con tipo: "${tipoValue}"`);

    if (tipoValue && tipoValue.trim() !== '') {
      // ✅ HABILITAR
      inputBuscador.disabled = false;
      inputBuscador.classList.remove('bg-light');
      inputBuscador.placeholder = `Buscar en cuentas de ${tipoValue}...`;
      if (btnBuscador) {
        btnBuscador.disabled = false;
      }

      log(`✅ Buscador HABILITADO para tipo: ${tipoValue}`);

      // Focus automático
      setTimeout(() => inputBuscador.focus(), 100);
    } else {
      // ❌ DESHABILITAR
      inputBuscador.disabled = true;
      inputBuscador.value = '';
      inputBuscador.classList.add('bg-light');
      inputBuscador.placeholder = 'Primero seleccione tipo...';
      if (btnBuscador) {
        btnBuscador.disabled = true;
      }

      // Limpiar resultados
      const resultados = selectTipo.closest('form')?.querySelector('#resultados-catalogo')
        || d.getElementById('resultados-catalogo');
      if (resultados) {
        resultados.innerHTML = '';
      }

      log(`❌ Buscador DESHABILITADO`);
    }
  }

  /**
   * ═══════════════════════════════════════════════════════════════
   * PARTE 2: DELEGACIÓN DE EVENTOS (Escucha Global)
   * ═══════════════════════════════════════════════════════════════
   */

  /**
   * Delegación: Escucha cambios en select#select-tipo-cuenta
   * Funciona incluso si el select se carga dinámicamente vía HTMX
   */
  d.addEventListener('change', (event) => {
    const target = event.target;

    if (!target) return;

    const isTipoSelect = (
      target.tagName === 'SELECT'
      && (target.id === 'select-tipo-cuenta' || target.name === 'tipo')
    );

    if (!isTipoSelect) return;

    log(`🎯 CHANGE detectado en select tipo`);
    sincronizarBuscador(target);
  }, true); // Captura = true para asegurar que se dispare primero

  /**
   * ═══════════════════════════════════════════════════════════════
   * PARTE 3: SINCRONIZACIÓN CON HTMX (Re-vinculación Automática)
   * ═══════════════════════════════════════════════════════════════
   */

  /**
   * Re-vinculación automática cuando HTMX carga contenido
   * Asegura que la sincronización funcione incluso después de recargas
   */
  d.addEventListener('htmx:afterOnLoad', (event) => {
    log(`🔄 HTMX:afterOnLoad detectado`);

    // Buscar select tipo en el contenido cargado
    const selectTipo = event.detail?.target?.querySelector('#select-tipo-cuenta')
      || d.querySelector('#select-tipo-cuenta');

    if (selectTipo) {
      log(`✅ Select tipo encontrado, sincronizando...`);
      sincronizarBuscador(selectTipo);
    }
  });

  /**
   * Alternativa: htmx:afterSwap
   * Se dispara después de que HTMX intercambia el contenido
   */
  d.addEventListener('htmx:afterSwap', (event) => {
    const target = event.detail?.target;

    if (!target) return;

    // Filtrar: solo sincronizar si es un formulario o offcanvas
    const isFormOrOffcanvas = (
      target.tagName === 'FORM'
      || target.classList?.contains('offcanvas')
      || target.id?.includes('offcanvas')
    );

    if (!isFormOrOffcanvas) return;

    log(`🔄 HTMX:afterSwap detectado en formulario/offcanvas`);

    const selectTipo = target.querySelector('#select-tipo-cuenta');
    if (selectTipo) {
      log(`✅ Select tipo encontrado, sincronizando...`);
      sincronizarBuscador(selectTipo);
    }
  });

  /**
   * ═══════════════════════════════════════════════════════════════
   * PARTE 4: INICIALIZADOR CENTRALIZADO
   * ═══════════════════════════════════════════════════════════════
   */

  /**
   * Inicializa la sincronización cuando el DOM está listo
   */
  function initializeModule() {
    log(`🚀 Inicializando módulo de buscador NIIF`);

    const selectTipo = d.querySelector('#select-tipo-cuenta');
    if (selectTipo) {
      log(`✅ Select tipo encontrado en carga inicial`);
      sincronizarBuscador(selectTipo);
    } else {
      log(`⚠️ Select tipo no encontrado en carga inicial (se vinculará cuando HTMX lo cargue)`);
    }
  }

  // Ejecutar inicialización cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', initializeModule, { once: true });
  } else {
    initializeModule();
  }

  /**
   * ═══════════════════════════════════════════════════════════════
   * PARTE 5: EXPORTACIONES (API Pública)
   * ═══════════════════════════════════════════════════════════════
   */

  w.CatalogoModular = {
    /**
     * Sincronizar manualmente (para debugging)
     */
    sync: sincronizarBuscador,

    /**
     * Reinicializar módulo
     */
    reinit: initializeModule,

    /**
     * Debug: ver estado actual
     */
    debug: () => {
      const selectTipo = d.querySelector('#select-tipo-cuenta');
      const inputBuscador = d.getElementById('input-buscador-niif');
      const btnBuscador = d.getElementById('btn-buscar-niif');

      return {
        selectTipo: selectTipo ? `✅ ${selectTipo.id} = "${selectTipo.value}"` : '❌ No encontrado',
        inputBuscador: inputBuscador ? `✅ ${inputBuscador.id} (disabled=${inputBuscador.disabled})` : '❌ No encontrado',
        btnBuscador: btnBuscador ? `✅ ${btnBuscador.id} (disabled=${btnBuscador.disabled})` : '❌ No encontrado'
      };
    }
  };

  log(`✅ Módulo cargado y listo`);
  log(`Listeners activos:`);
  log(`  - change (delegación global)`);
  log(`  - htmx:afterOnLoad`);
  log(`  - htmx:afterSwap`);

})(window, document);
