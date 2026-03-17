/**
 * clientes.page.js - Módulo Clientes v2.61 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Lazy Loading: Usa DOMUtils.onVisibleOnce() para inicialización diferida
 */
(function (w, d) {
  'use strict';

  const MOD = '[clientes.page]';
  const GRID_ID = '#grid-clientes';
  const SEARCH_ID = '#search-cliente';
  const API_URL = '/api/v1/clientes/';
  let table = null;

  /**
   * Definir columnas con acciones funcionales (Reconstrucción Debug)
   */
  function getColumns() {
    return [
      { title: "ID", field: "id", width: 60, headerSort: false },
      { title: "Razón Social", field: "razon_social", minWidth: 200, headerFilter: "input" },
      { title: "Documento", field: "numero_documento", width: 150, headerFilter: "input" },
      { title: "Segmento", field: "segmento", width: 120 },
      { title: "Email", field: "email", width: 180 },
      { title: "Teléfono", field: "telefono", width: 150 },
      {
        title: "Estado",
        field: "activo",
        formatter: function(cell) {
          return cell.getValue() ? '<span class="badge bg-success">Activo</span>' : '<span class="badge bg-secondary">Inactivo</span>';
        },
        width: 100,
        hozAlign: "center"
      },
      {
        title: "Acciones",
        field: "acciones",
        hozAlign: "center",
        headerSort: false,
        width: 120,
        formatter: function(cell) {
            return `
                <button class="btn btn-sm btn-outline-info btn-view-cliente" title="Ver Detalle" style="z-index: 10;">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger btn-delete-cliente" title="Eliminar" style="z-index: 10;">
                    <i class="bi bi-trash"></i>
                </button>`;
        },
        cellClick: function(e, cell) {
            const btn = e.target.closest('button');
            if (!btn) return;
            
            const action = btn.className;
            const data = cell.getData();
            console.log("Evento capturado para ID:", data.id); // Test de vida

            if (action.includes('btn-delete-cliente')) {
                alert('Click en Eliminar detectado');
                eliminarCliente(cell.getRow(), data.id);
            } else if (action.includes('btn-view-cliente')) {
                alert('Click en Ver Detalle detectado');
                abrirDetalle(data.id);
            }
        }
      }
    ];
  }

  /**
   * Inicializar tabla mediante TabulatorFactory
   */
  function initTable() {
    // Verificación de existencia antes de inicializar
    if (d.querySelector(GRID_ID)) {
        table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
            searchInputSelector: SEARCH_ID
        });
    } else {
        console.error(`${MOD} Contenedor ${GRID_ID} no encontrado`);
    }
  }

  /**
   * Eliminar Cliente (Atomic Flow)
   */
  async function eliminarCliente(row, id) {
    // Paso A: Confirmación
    if (!confirm('¿Está seguro de eliminar este cliente?')) return;
    
    // Paso B: Petición fetch/AJAX
    const res = await w.http('DELETE', `${API_URL}${id}/`);
    
    // Paso C: Si respuesta 200/204, eliminar fila visualmente
    if (res.ok) {
        w.SintelFeedback.success('Cliente eliminado correctamente');
        // Paso D: Actualizar la vista (row.delete)
        row.delete();
    } else {
        // Manejo de errores
        w.UIManager.handleError(res, MOD);
    }
  }
  
  /**
   * Ver detalle (Reconstrucción Flujo Ciego)
   */
  async function abrirDetalle(id) {
      console.log("Cargando detalle para:", id);
      const url = `/api/v1/clientes/render-offcanvas/detalle/?id=${id}`;
      
      try {
          // 1. Cargar HTML vía HTMX
          await htmx.ajax('GET', url, { 
              target: '#offcanvas-container-clientes', 
              swap: 'innerHTML' 
          });

          // 2. Inicializar y mostrar Bootstrap Offcanvas
          const offcanvasEl = d.getElementById('offcanvas-cliente-detalle');
          if (offcanvasEl) {
              const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
              offcanvas.show();
          } else {
              console.error("Offcanvas de detalle no encontrado en el DOM");
              w.SintelFeedback.error("No se pudo abrir el panel de detalle");
          }
      } catch (err) {
          console.error("Error al cargar detalle:", err);
          w.SintelFeedback.error("Error de conexión al cargar detalle");
      }
  }

  /**
   * Inicialización
   */
  function initClientes() {
    initTable();
    d.querySelector('#btn-nuevo-cliente')?.addEventListener('click', () => {
        // Lógica de creación futura
    });
  }

  // Lazy loading
  if (w.DOMUtils) {
    w.DOMUtils.onVisibleOnce(GRID_ID, initClientes, { once: true });
  } else {
    d.addEventListener('DOMContentLoaded', initClientes);
  }

})(window, document);
