/**
 * Tabulator Factory v2.60 - Resiliente y Modular
 * ⚠️ Alineado con arquitectura API-First
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * Maneja persistencia automática hacia CotizacionItemViewSet usando cotizacionesAPI
 * 
 * Dependencias globales requeridas:
 * - w.cotizacionesAPI (definido en cotizaciones.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function(w) {
  'use strict';

  // Asegurar que cotizacionesAPI esté disponible
  if (!w.cotizacionesAPI) {
    console.error('[cotizacion_factory] cotizacionesAPI no está disponible. Cargar cotizaciones.api.js primero.');
    return;
  }

  // Asegurar que getCotizacionColumns esté disponible (cargado dinámicamente)
  function getCotizacionColumns(isEditable) {
    // Si está disponible como módulo ES6, usarlo
    if (w.getCotizacionColumns && typeof w.getCotizacionColumns === 'function') {
      return w.getCotizacionColumns(isEditable);
    }
    // Fallback: columnas básicas
    // ⚠️ FASE 3: Sincronizado con cambios - usar campos que coinciden con backend
    console.warn('[cotizacion_factory] getCotizacionColumns no disponible, usando columnas básicas');
    return [
      {title: "Descripción", field: "descripcion", width: 300, editor: isEditable ? "input" : false},
      {title: "Cant.", field: "cantidad", width: 80, editor: isEditable ? "number" : false, hozAlign: "center"},
      {title: "Costo", field: "costo_unitario", hozAlign: "right", formatter: "money", editor: isEditable ? "number" : false},
      {title: "Utilidad (%)", field: "porcentaje_utilidad", width: 100, editor: isEditable ? "number" : false, hozAlign: "center"},
      {title: "Subtotal", field: "subtotal_linea", hozAlign: "right", formatter: "money", editor: false}
    ];
  }

  w.CotizacionTabulatorFactory = class {
    constructor(containerId, cotizacionUuid) {
      this.containerId = containerId;
      this.cotizacionUuid = cotizacionUuid;
      this.table = null;
      this.isDraft = false; // ⚠️ v2.60: Modo borrador (sin UUID)
      this.draftItems = []; // ⚠️ v2.60: Items en memoria para modo borrador
    }

    /**
     * ⚠️ v2.60: Detectar modo borrador desde el DOM
     */
    detectDraftMode() {
      const editorDiv = document.getElementById('modal-cotizacion-editor');
      if (!editorDiv) {
        return false;
      }
      
      // Verificar data-is-draft
      const isDraftAttr = editorDiv.getAttribute('data-is-draft');
      if (isDraftAttr === 'true') {
        return true;
      }
      
      // Verificar si no hay UUID
      const uuidAttr = editorDiv.getAttribute('data-cotizacion-uuid');
      if (!uuidAttr || uuidAttr.trim() === '') {
        return true;
      }
      
      // Verificar input hidden de UUID
      const uuidInput = document.getElementById('editor-uuid');
      if (uuidInput && (!uuidInput.value || uuidInput.value.trim() === '')) {
        return true;
      }
      
      return false;
    }

    init() {
      if (!w.Tabulator) {
        console.error('[cotizacion_factory] Tabulator no está disponible');
        return;
      }

      // ⚠️ v2.60: Detectar modo borrador
      this.isDraft = this.detectDraftMode();
      
      if (this.isDraft) {
        console.log('[cotizacion_factory] ⚠️ Modo borrador detectado - Items se guardarán en memoria');
        // Cargar items desde sessionStorage si existen
        this.loadDraftItems();
      }

      this.table = new Tabulator(this.containerId, {
        ajaxURL: (url, config, params) => {
          // ⚠️ v2.60: En modo borrador, retornar items desde memoria
          if (this.isDraft) {
            return Promise.resolve(this.draftItems);
          }
          
          // Usar API wrapper para obtener items (solo si hay UUID)
          if (!this.cotizacionUuid) {
            return Promise.resolve([]);
          }
          
          return w.cotizacionesAPI.listItems({ cotizacion: this.cotizacionUuid, ...params })
            .then(res => {
              if (res.ok) {
                // Manejar respuesta HATEOAS o array plano
                if (Array.isArray(res.data)) {
                  return res.data;
                } else if (res.data && Array.isArray(res.data.results)) {
                  return res.data.results;
                }
                return [];
              }
              return [];
            })
            .catch(err => {
              // ⚠️ v2.60: Aislamiento Gradual - Delegar a UIManager si es error de API
              if (err && err.status && w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError(err, '[cotizacion_factory]');
              }
              return [];
            });
        },
        layout: "fitColumns",
        columns: getCotizacionColumns(true),
        cellEdited: (cell) => this.saveItem(cell.getRow().getData()),
        dataLoaded: (data) => {
          // ⚠️ v2.60: En modo borrador, inicializar con items desde memoria
          if (this.isDraft && this.draftItems.length > 0) {
            this.table.setData(this.draftItems);
          }
        }
      });
    }

    /**
     * ⚠️ v2.60: Cargar items desde sessionStorage (modo borrador)
     */
    loadDraftItems() {
      try {
        const draftDataStr = sessionStorage.getItem('sintel_draft_cotizacion_items');
        if (draftDataStr) {
          this.draftItems = JSON.parse(draftDataStr);
          console.log('[cotizacion_factory] ✅ Items de borrador cargados desde sessionStorage:', this.draftItems.length);
        }
      } catch (error) {
        console.warn('[cotizacion_factory] ⚠️ Error cargando items de borrador:', error);
        this.draftItems = [];
      }
    }

    /**
     * ⚠️ v2.60: Guardar items en sessionStorage (modo borrador)
     */
    saveDraftItems() {
      try {
        sessionStorage.setItem('sintel_draft_cotizacion_items', JSON.stringify(this.draftItems));
        console.log('[cotizacion_factory] ✅ Items de borrador guardados en sessionStorage:', this.draftItems.length);
      } catch (error) {
        console.warn('[cotizacion_factory] ⚠️ Error guardando items de borrador:', error);
      }
    }

    /**
     * ⚠️ v2.60: Obtener todos los items (para guardado final)
     */
    getAllItems() {
      if (this.isDraft) {
        // En modo borrador, retornar items desde memoria
        return this.draftItems;
      }
      
      // En modo edición, obtener desde la tabla
      if (this.table) {
        return this.table.getData();
      }
      
      return [];
    }

    /**
     * Guardar item (crear o actualizar)
     * ⚠️ v2.60: Detecta modo borrador y guarda en memoria hasta el guardado final
     */
    async saveItem(data) {
      // ⚠️ DOM SHIELD / WIZARD SHIELD: Si no hay UUID, estamos en un Borrador.
      // El autoguardado no debe operar aquí. Se guardará masivamente al final del Editor.
      if (!this.cotizacionUuid) {
        return; 
      }
      
      // ⚠️ v2.60: Si estamos en modo borrador, guardar solo en memoria
      if (this.isDraft) {
        const isNew = !data.id;
        
        if (isNew) {
          // Generar ID temporal para el item
          const tempId = 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
          data.id = tempId;
          this.draftItems.push(data);
        } else {
          // Actualizar item existente en memoria
          const index = this.draftItems.findIndex(item => item.id === data.id);
          if (index !== -1) {
            this.draftItems[index] = data;
          } else {
            this.draftItems.push(data);
          }
        }
        
        // Guardar en sessionStorage
        this.saveDraftItems();
        
        console.log('[cotizacion_factory] ✅ Item guardado en memoria (modo borrador):', data);
        return;
      }
      
      // ⚠️ v2.60: Si no hay UUID, no podemos guardar en API
      if (!this.cotizacionUuid) {
        console.warn('[cotizacion_factory] ⚠️ No hay UUID de cotización, guardando en memoria como fallback');
        // Guardar en memoria como fallback
        const isNew = !data.id;
        if (isNew) {
          const tempId = 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
          data.id = tempId;
          this.draftItems.push(data);
        } else {
          const index = this.draftItems.findIndex(item => item.id === data.id);
          if (index !== -1) {
            this.draftItems[index] = data;
          } else {
            this.draftItems.push(data);
          }
        }
        this.saveDraftItems();
        return;
      }
      
      // ⚠️ v2.60: Modo edición - Guardar en API
      const isNew = !data.id;
      
      // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
      let response;
      if (isNew) {
        // Crear nuevo item
        response = await w.cotizacionesAPI.createItem({
          ...data,
          cotizacion: this.cotizacionUuid
        });
      } else {
        // Actualizar item existente
        response = await w.cotizacionesAPI.updateItem(data.id, data);
      }

      // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
      if (!response || !response.ok) {
        // ⚠️ v2.60: Delegar a UIManager para mostrar error
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(response, '[cotizacion_factory]');
        }
        return;
      }

      // Notificar al backend que recalcule el gran total de la cabecera
      const recalcularRes = await w.cotizacionesAPI.recalcular(this.cotizacionUuid);
      
      // ⚠️ v2.60: Si recalcular falla, mostrar error pero no bloquear
      if (!recalcularRes || !recalcularRes.ok) {
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(recalcularRes, '[cotizacion_factory]');
        }
      }
      
      // Refrescar la tabla
      if (this.table) {
        this.table.replaceData();
      }
    }
  };
})(window);
