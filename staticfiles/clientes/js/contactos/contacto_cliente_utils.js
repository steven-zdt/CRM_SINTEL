/**
 * contacto_cliente_utils.js - Utilidades compartidas para Contactos de Cliente v2.61
 * Feature-Sliced: Funciones auxiliares reutilizables
 */
(function(w, d) {
  'use strict';

  w.AppContactoCliente = w.AppContactoCliente || {};

  w.ContactoClienteUtils = {
    /**
     * Marcar un contacto como principal (desactivar otros)
     */
    marcarPrincipal: function(contactoId) {
      if (typeof w.contactosClienteAPI === 'undefined') return;
      w.contactosClienteAPI.update(contactoId, { is_principal: true })
        .then(response => {
          if (response.ok) {
            if (w.UIManager?.success) {
              w.UIManager.success('Contacto marcado como principal');
            }
            d.dispatchEvent(new CustomEvent('contactoActualizado'));
          }
        });
    },

    /**
     * Inactivar un contacto
     */
    inactivar: function(contactoId) {
      if (typeof w.contactosClienteAPI === 'undefined') return;
      w.contactosClienteAPI.update(contactoId, { activo: false })
        .then(response => {
          if (response.ok) {
            if (w.UIManager?.success) {
              w.UIManager.success('Contacto inactivado');
            }
            d.dispatchEvent(new CustomEvent('contactoActualizado'));
          }
        });
    },

    /**
     * Activar un contacto
     */
    activar: function(contactoId) {
      if (typeof w.contactosClienteAPI === 'undefined') return;
      w.contactosClienteAPI.update(contactoId, { activo: true })
        .then(response => {
          if (response.ok) {
            if (w.UIManager?.success) {
              w.UIManager.success('Contacto activado');
            }
            d.dispatchEvent(new CustomEvent('contactoActualizado'));
          }
        });
    },

    /**
     * Eliminar un contacto con confirmación
     */
    eliminar: function(contactoId, nombreContacto) {
      if (!confirm(`¿Eliminar contacto "${nombreContacto}"?`)) return;
      
      if (typeof w.contactosClienteAPI === 'undefined') return;
      w.contactosClienteAPI.delete(contactoId)
        .then(response => {
          if (response.ok || response.status === 204) {
            if (w.UIManager?.success) {
              w.UIManager.success('Contacto eliminado');
            }
            d.dispatchEvent(new CustomEvent('contactoEliminado'));
          } else if (w.UIManager?.notifyError) {
            w.UIManager.notifyError(response, 'Contactos');
          }
        });
    }
  };

  w.AppContactoCliente.utils = w.ContactoClienteUtils;
  
  console.log('[contacto_cliente_utils] OK: ContactoClienteUtils inicializado');
})(window, document);
