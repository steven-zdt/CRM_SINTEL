/**
 * Helpers y Renderers para Facturas
 * 
 * Funciones de utilidad para formateo, renderizado y eventos globales.
 */

(function() {
  'use strict';

  /**
   * Escapa HTML para prevenir XSS
   * @param {string} text - Texto a escapar
   * @returns {string}
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Formatea dinero con Intl.NumberFormat
   * @param {number|string} value - Valor a formatear
   * @param {string} currency - Código de moneda (default: COP)
   * @returns {string}
   */
  function fmtMoney(value, currency = 'COP') {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: currency,
    }).format(Number(value || 0));
  }

  /**
   * Renderiza badge de naturaleza (VENTA/COMPRA)
   * @param {string} val - Naturaleza (VENTA o COMPRA)
   * @returns {string} HTML del badge
   */
  function badgeNaturaleza(val) {
    const cls = val === 'VENTA' ? 'badge bg-success' : 'badge bg-primary';
    return `<span class="${cls}">${escapeHtml(val || '-')}</span>`;
  }

  /**
   * Renderiza emisor/receptor en dos líneas
   * @param {string} razon - Razón social
   * @param {string} nit - NIT
   * @returns {string} HTML
   */
  function twoLineParty(razon, nit) {
    return `
      <div class="text-truncate" title="${escapeHtml(razon || '')}">${escapeHtml(razon || '-')}</div>
      <div class="text-muted small">NIT: ${escapeHtml(nit || '-')}</div>
    `;
  }

  /**
   * Trunca hash largo (ej: CUFE)
   * @param {string} hash - Hash a truncar
   * @returns {string}
   */
  function shortHash(hash) {
    if (!hash) return '';
    return hash.length > 32 ? `${hash.slice(0, 12)}…${hash.slice(-12)}` : hash;
  }

  /**
   * Renderiza celda de CUFE con botón copiar y link QR
   * @param {string} cufe - CUFE completo
   * @param {string} qrUrl - URL del QR (opcional)
   * @returns {string} HTML
   */
  function cufeCell(cufe, qrUrl) {
    if (!cufe) return '';
    const copyBtn = `<button class="btn btn-sm btn-outline-secondary" data-copy="${escapeHtml(cufe)}" title="Copiar CUFE">📋</button>`;
    const qrLink = qrUrl ? ` <a href="${escapeHtml(qrUrl)}" target="_blank" rel="noopener" title="Ver QR DIAN">🔗</a>` : '';
    return `<span class="font-monospace" title="${escapeHtml(cufe)}">${shortHash(cufe)}</span> ${copyBtn}${qrLink}`;
  }

  /**
   * Renderiza celda de acciones (ver, XML, eliminar)
   * @param {Object} factura - Objeto factura con id
   * @returns {string} HTML
   */
  function actionsCell(factura) {
    const viewBtn = `<button class="btn btn-sm btn-outline-primary" data-action="view" data-id="${factura.id}" title="Ver detalle">👁️</button>`;
    const xmlBtn = `<button class="btn btn-sm btn-outline-info" data-action="xml" data-id="${factura.id}" title="Ver XML">📄</button>`;
    const deleteBtn = `<button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${factura.id}" title="Eliminar (error de carga)">🗑️</button>`;
    
    return `<div class="btn-group btn-group-sm" role="group">${viewBtn} ${xmlBtn} ${deleteBtn}</div>`;
  }

  /**
   * Inicializa handler global para copiar CUFE
   */
  function initCopyHandler() {
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-copy]');
      if (btn) {
        const text = btn.dataset.copy;
        navigator.clipboard.writeText(text).then(() => {
          btn.textContent = '✅';
          setTimeout(() => {
            btn.textContent = '📋';
          }, 1200);
        }).catch(() => {
          btn.textContent = '❌';
          setTimeout(() => {
            btn.textContent = '📋';
          }, 1200);
        });
      }
    });
  }

  // Inicializar handler de copiar al cargar
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCopyHandler);
  } else {
    initCopyHandler();
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.facturasComponents = {
      escapeHtml,
      fmtMoney,
      badgeNaturaleza,
      twoLineParty,
      shortHash,
      cufeCell,
      actionsCell,
    };
  }
})();
