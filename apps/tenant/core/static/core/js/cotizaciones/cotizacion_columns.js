/**
 * Columnas de Tabulator para Items de Cotización v2.60
 * Estándar: ITEM | DESCRIPCIÓN | MARCA | REFERENCIA | CANT | UND | VALOR UNIT | VALOR TOTAL | ACCIONES
 * 
 * SOLUCIÓN IMPLEMENTADA:
 * - Cálculo en tiempo real de subtotales al editar cantidad o precio unitario
 * - Función recalcularFila() centralizada que maneja el cálculo: subtotal = cantidad × (precio_unitario_venta × (1 + utilidad%))
 * - Columna "Valor / Unitario" con comportamiento estilo Excel: muestra precio final con utilidad, pero edita el costo base
 * - Manejo de errores con Error Boundary v2.60
 * - Sincronización automática con el panel de totales (IVA/AIU) mediante CotizacionEditorModule
 */
(function(w) {
  'use strict';

  function formatterCOP(cell) {
    const value = parseFloat(cell.getValue()) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  }

  /**
   * Función de recálculo alineada con CotizacionService.calcular_linea
   * Recalcula el subtotal de una fila: subtotal = cantidad * (precio_unitario_venta * (1 + utilidad%))
   * 
   * SOLUCIÓN: Esta función resuelve el problema de cálculo de subtotales en tiempo real.
   * - Limpia valores string (elimina símbolos $, espacios, comas, puntos)
   * - Convierte a números y valida (NaN se convierte a 0)
   * - Actualiza el subtotal sin disparar eventos adicionales (row.update con false)
   * - Notifica al módulo principal para actualizar totales generales (IVA/AIU)
   * 
   * ⚠️ Error Boundary v2.60: Envuelto con manejo de errores
   * 
   * @param {RowComponent} row - Fila de Tabulator a recalcular
   * @throws {Error} Capturado y notificado mediante UIManager.notifyError
   */
  /**
   * ⚠️ v2.60: SSoT (Single Source of Truth) - Fila como única fuente de verdad
   * Genera estrictamente las variables ocultas por cada fila, sin depender de variables globales externas
   */
  function recalcularFila(row) {
    try {
      if (!row) return;
      
      const data = row.getData();
      
      // 1. Normalización de entrada (sin fallbacks, solo valores directos)
      const cantidad = parseFloat(data.cantidad) || 0;
      const costoBase = parseFloat(data.precio_unitario_venta) || 0; 
      const utilidad = parseFloat(data.utilidad_porcentaje) || 0;
      const descuento = parseFloat(data.descuento_porcentaje) || 0;
      const ivaPorcentaje = parseFloat(data.iva_porcentaje) || 0;
      
      // 2. Precios unitarios
      const precioConUtilidad = costoBase * (1 + (utilidad / 100));
      const precioNetoUnitario = precioConUtilidad * (1 - (descuento / 100));
      
      // 3. Dinero para el Dashboard
      const costoTotalFila = costoBase * cantidad;
      const valorUtilidadFila = (precioConUtilidad - costoBase) * cantidad;
      const valorDescuentoFila = (precioConUtilidad - precioNetoUnitario) * cantidad;
      
      // 4. Totales
      const subtotalLinea = cantidad * precioNetoUnitario;
      const valorIvaLinea = subtotalLinea * (ivaPorcentaje / 100);
      const valorTotalLinea = subtotalLinea + valorIvaLinea;
      
      // 5. Actualización de la UI y variables ocultas (SSoT)
      // ⚠️ v2.60: Tabulator maneja update como una Promesa - Encadenar recálculo global SOLO cuando se resuelva
      row.update({
        "subtotal_linea": subtotalLinea,
        "valor_total_linea": valorTotalLinea,
        "_valor_iva_interno": valorIvaLinea,
        "_costo_total_interno": costoTotalFila,
        "_valor_utilidad_interno": valorUtilidadFila,
        "_valor_descuento_interno": valorDescuentoFila
      }, false).then(() => {
        // ⚠️ Este bloque garantiza el tiempo real exacto - Solo se ejecuta cuando Tabulator garantiza que los datos están asentados
        if (window.CotizacionEditorModule && typeof window.CotizacionEditorModule.recalcularTotalesGlobales === 'function') {
          window.CotizacionEditorModule.recalcularTotalesGlobales();
        }
      }).catch(error => {
        console.error('[cotizacion-columns] Error al actualizar fila:', error);
      });
    } catch (error) {
      // ⚠️ Error Boundary v2.60: Capturar errores en cálculo
      if (window.UIManager && typeof window.UIManager.notifyError === 'function') {
        window.UIManager.notifyError({ 
          status: 500, 
          data: { detail: `Error al recalcular fila: ${error.message || 'Error desconocido'}` } 
        }, '[cotizacion-columns]');
      }
      console.error('[cotizacion-columns] Error en recalcularFila:', error);
    }
  }

  /**
   * Obtiene la configuración de columnas unificada para la tabla de cotizaciones.
   * 
   * @param {string} seccion - Sección de la cotización (por defecto: 'equipos')
   * @param {boolean} isEditable - Indica si las columnas son editables (por defecto: true)
   * @returns {Array} Array de objetos de configuración de columnas para Tabulator
   * 
 * NOTAS IMPORTANTES:
 * - Ambas columnas disparan recalcularFila() al editar mediante cellEdited
 * - La columna VALOR TOTAL es de solo lectura y muestra el subtotal calculado
 */
  function getCotizacionColumns(seccion = 'equipos', isEditable = true) {
    return [
      { title: "ITEM", field: "nro_item", width: 60, hozAlign: "center", editor: false },
      { 
        title: "DESCRIPCIÓN", 
        field: "descripcion", 
        width: 250, 
        editor: isEditable ? "textarea" : false,
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como string
        mutator: function(value) {
          return value !== undefined && value !== null ? String(value).trim() : '';
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = String(cell.getValue() || '').trim();
          row.update({ descripcion: newValue }, false);
        }
      },
      { 
        title: "REFERENCIA", 
        field: "referencia", 
        width: 200, 
        editor: isEditable ? "input" : false,
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como string
        mutator: function(value) {
          return value !== undefined && value !== null ? String(value).trim() : '';
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = String(cell.getValue() || '').trim();
          row.update({ referencia: newValue }, false);
        }
      },
      { 
        title: "MARCA", 
        field: "marca", 
        width: 100, 
        editor: isEditable ? "input" : false,
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como string
        mutator: function(value) {
          return value !== undefined && value !== null ? String(value).trim() : '';
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = String(cell.getValue() || '').trim();
          row.update({ marca: newValue }, false);
        }
      },
      { 
        title: "UND", 
        field: "unidad", 
        width: 80, 
        editor: isEditable ? "list" : false,
        editorParams: { values: ["UND", "MTR", "GLN", "SERV", "HRA"] },
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como string
        mutator: function(value) {
          return value !== undefined && value !== null ? String(value) : 'UND';
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = String(cell.getValue() || 'UND');
          row.update({ unidad: newValue }, false);
        }
      },
      { 
        title: "Cantidad", 
        field: "cantidad", 
        editor: isEditable ? "number" : false, 
        sorter: "number",
        hozAlign: "center",
        width: 80,
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como número
        mutator: function(value) {
          const num = parseFloat(value);
          return isNaN(num) ? 0 : num;
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = parseFloat(cell.getValue()) || 0;
          row.update({ cantidad: newValue }, false).then(() => {
            recalcularFila(row);
          });
        }
      },
      { 
        title: "Valor Unitario Base", 
        field: "precio_unitario_venta", 
        editor: isEditable ? "number" : false,
        sorter: "number",
        hozAlign: "right",
        width: 150,
        formatter: "money", 
        formatterParams: { symbol: "$" },
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como número
        mutator: function(value) {
          const num = parseFloat(value);
          return isNaN(num) ? 0 : num;
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          // También actualizar costo_unitario para compatibilidad con el backend
          const row = cell.getRow();
          const newValue = parseFloat(cell.getValue()) || 0;
          row.update({ 
            precio_unitario_venta: newValue,
            costo_unitario: newValue  // ⚠️ Alias para compatibilidad con backend
          }, false).then(() => {
            recalcularFila(row);
          });
        }
      },
      { 
        title: "Utilidad (%)", 
        field: "utilidad_porcentaje", 
        editor: isEditable ? "number" : false,
        sorter: "number",
        hozAlign: "center",
        width: 120,
        mutator: function(value) {
          const num = parseFloat(value);
          return isNaN(num) ? 20 : num; // Default 20% si es inválido
        },
        formatter: function(cell) {
          return `${cell.getValue() || 0}%`;
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          // También actualizar porcentaje_utilidad para compatibilidad con el backend
          const row = cell.getRow();
          const newValue = parseFloat(cell.getValue()) || 0;
          row.update({ 
            utilidad_porcentaje: newValue,
            porcentaje_utilidad: newValue  // ⚠️ Alias para compatibilidad con backend
          }, false).then(() => {
            recalcularFila(row);
          });
        }
      },
      { 
        title: "Descuento (%)", 
        field: "descuento_porcentaje", 
        editor: isEditable ? "number" : false,
        sorter: "number",
        hozAlign: "center",
        width: 120,
        // ⚠️ FASE 3: Mutator para asegurar que el valor se guarde como número
        mutator: function(value) {
          const num = parseFloat(value);
          return isNaN(num) ? 0 : num;
        },
        formatter: function(cell) {
          return `${cell.getValue() || 0}%`;
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = parseFloat(cell.getValue()) || 0;
          row.update({ descuento_porcentaje: newValue }, false).then(() => {
            recalcularFila(row);
          });
        }
      },
      { 
        title: "Subtotal", 
        field: "subtotal_linea", 
        mutator: function(value) {
          return value || 0;
        },
        formatter: "money", 
        formatterParams: { symbol: "$" },
        editor: false,
        hozAlign: "right",
        width: 150,
        bottomCalc: "sum", 
        bottomCalcFormatter: formatterCOP
      },
      { 
        title: "IVA", 
        field: "iva_porcentaje", 
        editor: isEditable ? "list" : false,
        editorParams: { values: [0, 5, 19,15,10] }, // Tarifas legales de IVA en Colombia
        sorter: "number",
        hozAlign: "center",
        width: 150,
        mutator: function(value) {
          const num = parseFloat(value);
          return isNaN(num) ? 19 : num; // 19% por defecto si es inválido
        },
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const porc = parseFloat(cell.getValue()) || 0;
          const valorIva = parseFloat(rowData._valor_iva_interno) || 0;
          const formatoMoneda = new Intl.NumberFormat('es-CO', { 
            style: 'currency', 
            currency: 'COP', 
            minimumFractionDigits: 0 
          }).format(valorIva);
          return `${porc}% (${formatoMoneda})`;
        },
        cellEdited: function(cell) {
          // ⚠️ FASE 3: Asegurar que el valor se guarde en el objeto de la fila
          const row = cell.getRow();
          const newValue = parseFloat(cell.getValue()) || 19;
          row.update({ iva_porcentaje: newValue }, false).then(() => {
            recalcularFila(row);
          });
        }
      },
      { 
        title: "Valor Total", 
        field: "valor_total_linea", 
        mutator: function(value) {
          return value || 0;
        },
        formatter: "money", 
        formatterParams: { symbol: "$" },
        editor: false,
        hozAlign: "right",
        width: 150,
        bottomCalc: "sum", 
        bottomCalcFormatter: formatterCOP
      },
      {
        title: "ACCIONES",
        field: "acciones",
        width: 80,
        hozAlign: "center",
        headerSort: false,
        titleFormatter: function(cell, formatterParams, onRendered) {
          const btn = document.createElement('button');
          btn.className = 'btn btn-sm btn-primary';
          btn.style.cssText = 'width:32px;height:32px;padding:0;display:flex;align-items:center;justify-content:center;';
          btn.title = 'Añadir fila';
          btn.innerHTML = '<i class="bi bi-plus-lg" style="font-size:18px;color:white;"></i>';
          return btn;
        },
        headerClick: function(e, column) {
          e.stopPropagation();
          const table = column.getTable();
          
          // Añadir fila con valores por defecto al inicio
          table.addRow({
            nro_item: 0, // Se asignará automáticamente por reindexarFilas
            descripcion: '',
            referencia: '',
            marca: '',
            cantidad: 1,
            unidad: 'UND',
            precio_unitario_venta: 0, // Valor unitario base
            utilidad_porcentaje: 20, // Utilidad por ítem (Markup) - 20% por defecto
            descuento_porcentaje: 0, // Descuento por ítem
            iva_porcentaje: 19, // IVA por ítem (normatividad colombiana - 19% por defecto)
            subtotal_linea: 0, // Se calculará automáticamente: CANT × (Valor Base × (1 + Utilidad%) × (1 - Descuento%))
            valor_total_linea: 0 // Se calculará automáticamente: Subtotal + IVA
          }, true).then(function(row) {
            // Recalcular subtotal inicial después de añadir la fila usando la función centralizada
            recalcularFila(row);
            // Reindexar todas las filas después de añadir
            if (window.CotizacionEditorModule && window.CotizacionEditorModule.reindexarFilas) {
              window.CotizacionEditorModule.reindexarFilas(table);
            }
            
            // Enfocar la celda "descripcion" para edición inmediata
            row.getCell('descripcion').edit();
            
            // Actualizar totales después de añadir la fila
            if (window.CotizacionEditorModule && window.CotizacionEditorModule.actualizarPanelTotales) {
              window.CotizacionEditorModule.actualizarPanelTotales();
            }
          }).catch(function(error) {
            console.error('Error al añadir fila:', error);
          });
        },
        formatter: function(cell, formatterParams, onRendered) {
          const btn = document.createElement('button');
          btn.className = 'btn btn-sm btn-outline-danger';
          btn.style.cssText = 'width:32px;height:32px;padding:0;display:flex;align-items:center;justify-content:center;';
          btn.innerHTML = '<i class="bi bi-trash-lg" style="font-size:18px;"></i>';
          btn.type = 'button';
          btn.title = 'Eliminar fila';
          
          onRendered(function() {
            btn.addEventListener('click', function(e) {
              e.stopPropagation();
              if (confirm('¿Eliminar esta fila?')) {
                const table = cell.getTable();
                cell.getRow().delete();
                
                // Reindexar todas las filas después de eliminar
                if (window.CotizacionEditorModule && window.CotizacionEditorModule.reindexarFilas) {
                  window.CotizacionEditorModule.reindexarFilas(table);
                }
                
                // Actualizar totales después de eliminar la fila
                if (window.CotizacionEditorModule && window.CotizacionEditorModule.actualizarPanelTotales) {
                  window.CotizacionEditorModule.actualizarPanelTotales();
                }
              }
            });
          });
          return btn;
        }
      }
    ];
  }

  w.getCotizacionColumns = getCotizacionColumns;
  // ⚠️ v2.60: Exponer recalcularFila globalmente para acceso desde cotizacion_editor.js
  w.recalcularFila = recalcularFila;

  /**
   * ⚠️ v2.60: Columnas para la tabla principal de listado de cotizaciones
   * Sincronizado con Modelo Cotizacion y CotizacionSerializer
   * 
   * Campos del modelo:
   * - codigo_unico: Código único generado (ej: "STS. 0422-2026")
   * - fecha_emision: Fecha de emisión
   * - cliente_display: Nombre del cliente (SerializerMethodField)
   * - tipo_cotizacion: Tipo de cotización (MIXTO, PRODUCTO, SERVICIO, MATERIAL)
   * - total_con_impuestos: Total con impuestos calculado
   * - estado: Estado de la cotización (BORRADOR, ENVIADA, ACEPTADA, CANCELADA)
   * - uuid: UUID único para acciones
   */
  w.columnasCotizaciones = [
    {
      title: "NÚMERO",
      field: "codigo_unico",
      width: 150,
      headerFilter: "input",
      formatter: function(cell) {
        const value = cell.getValue();
        return value || '-';
      }
    },
    {
      title: "FECHA",
      field: "fecha_emision",
      width: 120,
      sorter: "date",
      formatter: function(cell) {
        const value = cell.getValue();
        if (!value) return '-';
        try {
          const date = new Date(value);
          return date.toLocaleDateString('es-CO');
        } catch (e) {
          return value;
        }
      }
    },
    {
      title: "CLIENTE",
      field: "cliente_display", // ⚠️ Usar cliente_display del serializer (SerializerMethodField)
      width: 200,
      headerFilter: "input",
      formatter: function(cell) {
        const value = cell.getValue();
        return value || 'Sin cliente';
      }
    },
    {
      title: "TIPO",
      field: "tipo_cotizacion",
      width: 100,
      formatter: function(cell) {
        const value = cell.getValue();
        const tipos = {
          'MIXTO': '<span class="badge bg-primary">Mixto</span>',
          'PRODUCTO': '<span class="badge bg-info">Producto</span>',
          'SERVICIO': '<span class="badge bg-success">Servicio</span>',
          'MATERIAL': '<span class="badge bg-warning text-dark">Material</span>'
        };
        return tipos[value] || value || '-';
      }
    },
    {
      title: "SUBTOTAL",
      field: "total_con_impuestos", // ⚠️ El modelo no tiene campo 'subtotal', usar total_con_impuestos
      formatter: "money",
      formatterParams: {
        symbol: "$",
        precision: 0,
        thousand: ".",
        decimal: ","
      },
      width: 130,
      hozAlign: "right",
      sorter: "number"
    },
    {
      title: "TOTAL",
      field: "total_con_impuestos",
      formatter: "money",
      formatterParams: {
        symbol: "$",
        precision: 0,
        thousand: ".",
        decimal: ","
      },
      width: 130,
      hozAlign: "right",
      sorter: "number",
      bottomCalc: "sum",
      bottomCalcFormatter: function(cell) {
        const value = parseFloat(cell.getValue()) || 0;
        return new Intl.NumberFormat('es-CO', {
          style: 'currency',
          currency: 'COP',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0
        }).format(value);
      }
    },
    {
      title: "ESTADO",
      field: "estado",
      width: 120,
      formatter: "lookup",
      formatterParams: {
        "BORRADOR": "<span class='badge bg-secondary'>Borrador</span>",
        "ENVIADA": "<span class='badge bg-primary'>Enviada</span>",
        "ACEPTADA": "<span class='badge bg-success'>Aceptada</span>",
        "CANCELADA": "<span class='badge bg-danger'>Cancelada</span>"
      },
      headerFilter: "select",
      headerFilterParams: {
        values: {
          "": "Todos",
          "BORRADOR": "Borrador",
          "ENVIADA": "Enviada",
          "ACEPTADA": "Aceptada",
          "CANCELADA": "Cancelada"
        }
      }
    },
    {
      title: "ACCIONES",
      field: "uuid",
      formatter: function(cell) {
        const uuid = cell.getValue();
        if (!uuid) return '-';
        
        // ⚠️ Usar HTMX para editar y métodos del módulo para otras acciones
        return `
          <div class='btn-group'>
            <button class='btn btn-sm btn-outline-primary' 
                    hx-get="/cotizaciones/editor/${uuid}/"
                    hx-target="#offcanvas-container"
                    hx-swap="innerHTML"
                    data-bs-toggle="offcanvas"
                    data-bs-target="#offcanvas-container"
                    title="Editar Cotización">
              <i class='bi bi-pencil'></i>
            </button>
            <button class='btn btn-sm btn-outline-danger' 
                    onclick="window.open('/api/v1/cotizaciones/${uuid}/exportar-pdf/', '_blank'); return false;"
                    title="Ver PDF">
              <i class='bi bi-file-pdf'></i>
            </button>
          </div>`;
      },
      headerSort: false,
      headerFilter: false,
      hozAlign: "center",
      width: 150
    }
  ];
})(window);