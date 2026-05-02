/**
 * contacto_cliente_main.js - Orquestador del módulo Contactos de Cliente v2.61
 * Feature-Sliced: Inicialización de Tabulator, event delegation, HTMX integration
 * 
 * Dependencias globales:
 * - window.Tabulator (tabla reactiva)
 * - window.contactosClienteAPI (capa de datos)
 * - window.bootstrap (offcanvas)
 * - window.UIManager (notificaciones)
 */
(function(w, d) {
  'use strict';

  w.AppContactoCliente = w.AppContactoCliente || {};

  class ContactoClienteModule {
    constructor() {
      this.table = null;
      this.currentClienteId = null;
      this.offcanvasEl = null;
    }

    /**
     * Inicializar tabla de Tabulator
     */
    initTable(containerSelector) {
      const container = d.querySelector(containerSelector);
      if (!container) {
        console.warn('[contacto_cliente_main] Contenedor no encontrado:', containerSelector);
        return;
      }

      const columns = [
        {
          title: 'Nombre',
          field: 'nombre_completo',
          width: 200,
          sorter: 'string'
        },
        {
          title: 'Cliente',
          field: 'cliente_nombre',
          width: 180,
          sorter: 'string'
        },
        {
          title: 'Email',
          field: 'email',
          width: 200,
          formatter: (cell) => {
            const email = cell.getValue();
            return email ? `<a href="mailto:${email}">${email}</a>` : '-';
          }
        },
        {
          title: 'Cargo',
          field: 'cargo',
          width: 120,
          sorter: 'string'
        },
        {
          title: 'Principal',
          field: 'is_principal',
          width: 80,
          formatter: (cell) => {
            return cell.getValue() 
              ? '<span class="badge bg-primary">Sí</span>' 
              : '-';
          },
          sorter: 'boolean'
        },
        {
          title: 'Activo',
          field: 'activo',
          width: 80,
          formatter: (cell) => {
            return cell.getValue() 
              ? '<span class="badge bg-success">Activo</span>' 
              : '<span class="badge bg-secondary">Inactivo</span>';
          },
          sorter: 'boolean'
        },
        {
          title: 'Acciones',
          width: 120,
          formatter: this.renderAcciones.bind(this),
          hozAlign: 'center'
        }
      ];

      this.table = new Tabulator(container, {
        columns: columns,
        ajaxURL: '/api/v1/clientes/contactos/',
        ajaxParams: this.currentClienteId ? { cliente: this.currentClienteId } : {},
        layout: 'fitColumns',
        pagination: 'remote',
        paginationSize: 10,
        paginationSizeSelector: [5, 10, 20],
        placeholder: 'No hay contactos registrados',
        selectableRows: 'highlight',
        rowFormatter: this.rowFormatter.bind(this)
      });

      this.attachTableEvents();
      console.log('[contacto_cliente_main] Tabla inicializada');
    }

    /**
     * Renderizar columna de acciones
     */
    renderAcciones(cell) {
      const data = cell.getRow().getData();
      return `
        <div class="btn-group btn-group-sm" role="group">
          <button type="button" class="btn btn-outline-primary btn-editar-contacto" 
                  data-contacto-id="${data.id}" title="Editar">
            <i class="bi bi-pencil"></i>
          </button>
          <button type="button" class="btn btn-outline-danger btn-eliminar-contacto" 
                  data-contacto-id="${data.id}" title="Eliminar">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      `;
    }

    /**
     * Formatear fila (resaltado para principales)
     */
    rowFormatter(row) {
      const data = row.getData();
      if (data.is_principal) {
        row.getElement().classList.add('table-primary');
      }
    }

    /**
     * Adjuntar eventos a la tabla
     */
    attachTableEvents() {
      if (!this.table) return;

      // Event delegation para botones de acción
      const container = this.table.element.parentElement;
      
      container.addEventListener('click', async (e) => {
        const btnEditar = e.target.closest('.btn-editar-contacto');
        const btnEliminar = e.target.closest('.btn-eliminar-contacto');

        if (btnEditar) {
          const contactoId = btnEditar.getAttribute('data-contacto-id');
          await this.abrirEditarContacto(contactoId);
        }

        if (btnEliminar) {
          const contactoId = btnEliminar.getAttribute('data-contacto-id');
          const nombreContacto = this.table.getRow(contactoId)?.getData()?.nombre_completo || 'contacto';
          if (w.ContactoClienteUtils?.eliminar) {
            w.ContactoClienteUtils.eliminar(contactoId, nombreContacto);
          }
        }
      });
    }

    /**
     * Abrir offcanvas de creación
     */
    async abrirCrearContacto(clienteId = null) {
      try {
        let response;
        if (clienteId) {
          // Pasar cliente_id en parámetro
          response = await w.contactosClienteAPI.renderCrear();
        } else {
          response = await w.contactosClienteAPI.renderCrear();
        }

        if (!response.ok) {
          if (w.UIManager?.notifyError) {
            w.UIManager.notifyError(response, 'Contactos');
          }
          return;
        }

        // Inyectar HTML en el DOM
        const container = d.getElementById('offcanvas-container-contacto') || d.body;
        const existingOffcanvas = container.querySelector('#offcanvas-contacto-cliente');
        if (existingOffcanvas) {
          existingOffcanvas.remove();
        }

        const div = d.createElement('div');
        div.innerHTML = response.data;
        container.appendChild(div);

        // Rellenar cliente_id si está disponible
        if (clienteId) {
          const input = d.querySelector('#contacto-cliente-id');
          if (input) input.value = clienteId;
        }

        // Mostrar offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-contacto-cliente');
        if (offcanvasEl && window.bootstrap) {
          new bootstrap.Offcanvas(offcanvasEl).show();
        }
      } catch (error) {
        console.error('[contacto_cliente_main] Error abriendo crear:', error);
      }
    }

    /**
     * Abrir offcanvas de edición
     */
    async abrirEditarContacto(contactoId) {
      try {
        const response = await w.contactosClienteAPI.renderEditar(contactoId);

        if (!response.ok) {
          if (w.UIManager?.notifyError) {
            w.UIManager.notifyError(response, 'Contactos');
          }
          return;
        }

        // Inyectar HTML en el DOM
        const container = d.getElementById('offcanvas-container-contacto') || d.body;
        const existingOffcanvas = container.querySelector('#offcanvas-contacto-cliente');
        if (existingOffcanvas) {
          existingOffcanvas.remove();
        }

        const div = d.createElement('div');
        div.innerHTML = response.data;
        container.appendChild(div);

        // Mostrar offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-contacto-cliente');
        if (offcanvasEl && window.bootstrap) {
          new bootstrap.Offcanvas(offcanvasEl).show();
        }
      } catch (error) {
        console.error('[contacto_cliente_main] Error abriendo editar:', error);
      }
    }

    /**
     * Filtrar por cliente
     */
    filterByCliente(clienteId) {
      this.currentClienteId = clienteId;
      if (this.table) {
        this.table.setData(
          '/api/v1/clientes/contactos/',
          { cliente: clienteId }
        );
      }
    }

    /**
     * Recargar tabla
     */
    reload() {
      if (this.table) {
        this.table.replaceData();
      }
    }

    /**
     * Inicializar eventos globales
     */
    initEventListeners() {
      // Botón crear
      const btnCrear = d.querySelector('#btn-crear-contacto');
      if (btnCrear) {
        btnCrear.addEventListener('click', () => this.abrirCrearContacto());
      }

      // Eventos de actualización
      d.addEventListener('contactoGuardado', () => this.reload());
      d.addEventListener('contactoActualizado', () => this.reload());
      d.addEventListener('contactoEliminado', () => this.reload());

      console.log('[contacto_cliente_main] Event listeners inicializados');
    }
  }

  // Instancia global
  const modulo = new ContactoClienteModule();

  // Exponer API
  w.ContactoClienteModule = {
    initTable: (selector) => modulo.initTable(selector),
    abrirCrear: (clienteId) => modulo.abrirCrearContacto(clienteId),
    abrirEditar: (contactoId) => modulo.abrirEditarContacto(contactoId),
    filterByCliente: (clienteId) => modulo.filterByCliente(clienteId),
    reload: () => modulo.reload()
  };

  w.AppContactoCliente.main = w.ContactoClienteModule;

  // Inicializar en DOMContentLoaded
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', () => modulo.initEventListeners());
  } else {
    modulo.initEventListeners();
  }

  console.log('[contacto_cliente_main] OK: Módulo ContactoCliente inicializado');
})(window, document);
