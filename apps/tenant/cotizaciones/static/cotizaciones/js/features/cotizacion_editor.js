/**
 * cotizacion_editor.js - Editor Profesional Maestro-Detalle v2.62.0
 * Soporta: Agregar filas, Pegar desde Excel, Cálculos en tiempo real, Utilidad Global e IVA incluido por ítem.
 * Namespace: window.Sintel.Cotizaciones.Editor
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var MOD = '[Cotizaciones:Editor]';
  
  var CotizacionEditor = {
    _initialized: false,
    _uuid: null,
    _api: null,

    format: function (val) {
      return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0
      }).format(val || 0);
    },

    init: function (uuid) {
      console.log(MOD + ' Iniciando editor...', uuid || 'DRAFT');
      this._uuid = uuid;
      this._api = w.Sintel.Cotizaciones.api;

      if (!this._api) {
        console.error(MOD + ' API no encontrada. Asegurese que cotizaciones.api.js carga primero.');
        return;
      }

      this.bindEvents();
      this.calculateTotals();
      this._initialized = true;

      if (uuid) {
        this.loadItems(uuid);
      }
    },

    clearAllItems: function () {
      d.querySelectorAll('.item-row').forEach(function (row) {
        row.remove();
      });
      console.log(MOD + ' Items limpios del DOM');
    },

    loadItems: function (uuid) {
      var self = this;
      var headers = this._api.getHeaders();

      this.clearAllItems();

      fetch('/api/v1/cotizaciones/items/?cotizacion_id=' + uuid + '&page_size=200', { headers: headers })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function (data) {
          var items = data.results || data;
          items.forEach(function (item) {
            self.addRow(item.tipo_item, {
              id: item.id,
              descripcion: item.descripcion || '',
              marca: item.marca || '',
              referencia: item.referencia || '',
              cantidad: item.cantidad || 1,
              unidad: item.unidad || 'UND',
              costo: parseFloat(item.costo_unitario) || 0,
              utilidad: parseFloat(item.porcentaje_utilidad) || 0,
            });
          });
          self.calculateTotals();
        })
        .catch(function (err) {
          console.warn(MOD + ' No se pudieron cargar los items:', err);
        });
    },

    bindEvents: function () {
      var self = this;
      var container = d.getElementById('cot-tabla-items');
      if (!container) return;

      // Guard: `this._initialized` no sirve como guard real (este objeto se
      // redeclara entero cada vez que el script vuelve a cargar, asi que el
      // flag siempre nace en false) — se ancla al contenedor, que sí persiste
      // dentro de la misma inserción del fragmento (FE-A1).
      if (container.dataset.editorInitialized) return;
      container.dataset.editorInitialized = 'true';

      // Delegación de eventos para la tabla
      container.addEventListener('input', function (e) {
        if (e.target.classList.contains('item-calc')) {
          var row = e.target.closest('tr');
          self.calculateRow(row);
        }
      });

      // Botones de agregar item
      d.querySelectorAll('.btn-add-item').forEach(function (btn) {
        btn.addEventListener('click', function () {
          self.addRow(this.dataset.tipo);
        });
      });

      // Botón Guardar
      var btnGuardar = d.getElementById('btn-guardar-cot');
      if (btnGuardar) {
        btnGuardar.addEventListener('click', function () {
          self.save();
        });
      }

      // Switch Aplicar AIU
      var swAiu = d.getElementById('cot-aplicar-aiu');
      if (swAiu) {
        swAiu.addEventListener('change', function () {
          var fields = d.getElementById('cot-aiu-fields');
          if (this.checked) {
            fields.classList.remove('d-none');
          } else {
            fields.classList.add('d-none');
            // Opcional: Limpiar valores al apagar? 
            // d.getElementById('cot-aiu-admin').value = 0;
            // d.getElementById('cot-aiu-imprevistos').value = 0;
            // d.getElementById('cot-aiu-utilidad').value = 0;
          }
          self.calculateTotals();
        });
      }

      // Manejo de pegado (Paste) en descripciones
      container.addEventListener('paste', function (e) {
        if (e.target.classList.contains('item-descripcion')) {
          self.handlePaste(e);
        }
      });

      // Cambio de configuración o cliente (DOM Shield)
      var selCliente = d.getElementById('cot-cliente-select');
      if (selCliente) {
        selCliente.addEventListener('change', function () {
          d.getElementById('cot-cliente-id').value = this.value;
        });
      }
      var selConfig = d.getElementById('cot-config-select');
      if (selConfig) {
        selConfig.addEventListener('change', function () {
          d.getElementById('cot-config-id').value = this.value;
        });
      }

      // Otros campos de cabecera que disparan recalculo global
      ['cot-iva', 'cot-utilidad-global', 'cot-aiu-admin', 'cot-aiu-imprevistos', 'cot-aiu-utilidad'].forEach(function(id){
          var el = d.getElementById(id);
          if(el) {
              el.addEventListener('input', function() { 
                  // Si cambia la utilidad global o el IVA global, recalculamos todas las filas
                  if(id === 'cot-utilidad-global' || id === 'cot-iva') {
                      self.recalculateAllRows();
                  } else {
                      self.calculateTotals(); 
                  }
              });

              // Validar que si queda vacío, asuma el valor base garantizado
              if (id === 'cot-iva' || id === 'cot-utilidad-global') {
                el.addEventListener('blur', function() {
                  if (this.value === "") {
                    this.value = (id === 'cot-iva') ? "19.00" : "20.00";
                    self.recalculateAllRows();
                  }
                });
              }
          }
      });

      // Evento Tiempos del Proyecto
      var inputDias = d.getElementById('cot-dias-totales');
      if (inputDias) {
        inputDias.addEventListener('input', function () {
          self.calculateSchedule();
        });
      }

      this.recalculateAllRows();
      this.calculateSchedule();
    },

    recalculateAllRows: function() {
        var self = this;
        d.querySelectorAll('.item-row').forEach(function(row) {
            self.calculateRow(row);
        });
        this.calculateTotals();
    },

    addRow: function (tipo, data) {
      data = data || {};
      var tbody = d.getElementById('seccion-' + tipo);
      var subtotalRow = d.getElementById('subtotal-row-' + tipo);
      if (!tbody || !subtotalRow) return;

      var row = d.createElement('tr');
      row.className = 'item-row';
      row.dataset.tipo = tipo;
      if (data.id) row.dataset.id = data.id;
      
      var index = tbody.querySelectorAll('.item-row').length + 1;
      var secNum = tbody.querySelector('.seccion-header').dataset.secnum;

      row.innerHTML = `
        <td class="text-center fw-semibold text-muted">${secNum}.${index}</td>
        <td><textarea class="form-control form-control-sm border-0 bg-transparent item-descripcion" rows="1">${data.descripcion || ''}</textarea></td>
        <td><input type="text" class="form-control form-control-sm border-0 bg-transparent item-marca" value="${data.marca || ''}"></td>
        <td><input type="text" class="form-control form-control-sm border-0 bg-transparent item-referencia" value="${data.referencia || ''}"></td>
        <td><input type="number" class="form-control form-control-sm border-0 bg-transparent text-center item-calc item-cantidad" value="${data.cantidad || 1}" min="0"></td>
        <td><input type="text" class="form-control form-control-sm border-0 bg-transparent text-center item-unidad" value="${data.unidad || 'UND'}"></td>
        <td><input type="number" class="form-control form-control-sm border-0 bg-transparent text-end item-calc item-costo" value="${data.costo || 0}"></td>
        <td class="text-end fw-semibold px-2 item-v-unitario" style="font-size:0.75rem; color:#666;">$ 0</td>
        <td class="text-end fw-bold px-2 item-valor-total">$ 0</td>
        <td class="text-center">
          <button type="button" class="btn btn-link btn-sm p-0 text-danger btn-remove-row"><i class="bi bi-x-circle"></i></button>
        </td>
      `;

      tbody.insertBefore(row, subtotalRow);
      
      row.querySelector('.btn-remove-row').addEventListener('click', function () {
        row.remove();
        CotizacionEditor.calculateTotals();
      });

      this.calculateRow(row);
    },

    calculateRow: function (row) {
      var self = this;
      var utils = w.Sintel.Cotizaciones.utils;
      var cantInput = row.querySelector('.item-cantidad');
      var cant = utils ? utils.parseFloatSafe(cantInput.value) : (parseFloat(cantInput.value) || 0);
      
      // No permitir negativos
      if (cant < 0) {
        cant = 0;
        cantInput.value = 0;
      }
      var costoBase = utils ? utils.parseFloatSafe(row.querySelector('.item-costo').value) : (parseFloat(row.querySelector('.item-costo').value) || 0);
      
      var utilGlobal = utils ? utils.parseFloatSafe(d.getElementById('cot-utilidad-global').value) : (parseFloat(d.getElementById('cot-utilidad-global').value) || 0);
      var ivaRaw = d.getElementById('cot-iva').value;
      var ivaGlobal = (ivaRaw === "") ? 19 : (parseFloat(ivaRaw) || 0);

      // NUEVA FÓRMULA SOLICITADA (Transparente para el cliente):
      // 1. Aplicar utilidad: Valor Unitario (Costo Ajustado) = Costo Base * (1 + %Utilidad)
      var precioVenta = costoBase * (1 + (utilGlobal / 100));
      
      // 2. Subtotal por línea = Valor Unitario * Cantidad
      var subtotalLinea = precioVenta * cant;

      // Actualizar UI de la fila
      row.querySelector('.item-v-unitario').innerText = self.format(precioVenta);
      row.querySelector('.item-valor-total').innerText = self.format(subtotalLinea);
      
      row.dataset.vUnitario = precioVenta;
      row.dataset.valorTotal = subtotalLinea;
      row.dataset.utilidad = utilGlobal;
      row.dataset.iva = ivaGlobal;

      this.calculateTotals();
    },

    calculateTotals: function () {
      var self = this;
      var subtotales = { PRODUCTO: 0, MATERIAL: 0, SERVICIO: 0 };
      
      d.querySelectorAll('.item-row').forEach(function (row) {
        var tipo = row.dataset.tipo;
        subtotales[tipo] += parseFloat(row.dataset.valorTotal || 0);
      });

      var subtotalGlobal = 0;
      Object.keys(subtotales).forEach(function (tipo) {
        var elSub = d.getElementById('subtotal-' + tipo);
        if (elSub) elSub.innerText = self.format(subtotales[tipo]);
        subtotalGlobal += subtotales[tipo];
      });

      var totalNetoGeneral = 0;
      var totalIvaGeneral = 0;
      
      var ivaRaw = d.getElementById('cot-iva').value;
      var ivaPct = (ivaRaw === "") ? 19 : (parseFloat(ivaRaw) || 0);

      var seccionTotales = {}; // Almacenar totales finales por sección para indicadores

      ['PRODUCTO', 'MATERIAL', 'SERVICIO'].forEach(function (tipo) {
        var netoSeccion = subtotales[tipo];
        var ivaSeccion = netoSeccion * (ivaPct / 100);
        var totalSeccion = netoSeccion + ivaSeccion;
        
        seccionTotales[tipo] = totalSeccion;

        // Actualizar UI de la sección en la tabla
        var elSub = d.getElementById('subtotal-' + tipo);
        var elIva = d.getElementById('iva-' + tipo);
        var elTot = d.getElementById('total-' + tipo);

        if (elSub) elSub.innerText = self.format(netoSeccion);
        if (elIva) elIva.innerText = self.format(ivaSeccion);
        if (elTot) elTot.innerText = self.format(totalSeccion);

        totalNetoGeneral += netoSeccion;
        totalIvaGeneral += ivaSeccion;
      });

      // El total final base es la suma de los totales de las secciones
      var totalFinal = totalNetoGeneral + totalIvaGeneral;
      var ivaConsolidado = totalIvaGeneral;

      var swAiu = d.getElementById('cot-aplicar-aiu');
      var aiuActivo = swAiu ? swAiu.checked : false;

      if (aiuActivo) {
        var adminPct = parseFloat(d.getElementById('cot-aiu-admin').value) || 0;
        var imprPct = parseFloat(d.getElementById('cot-aiu-imprevistos').value) || 0;
        var utilPct = parseFloat(d.getElementById('cot-aiu-utilidad').value) || 0;

        var valorAiu = totalNetoGeneral * ((adminPct + imprPct + utilPct) / 100);
        var valorIvaAiu = (totalNetoGeneral * (utilPct / 100)) * (ivaPct / 100); 
        
        totalFinal += valorAiu + valorIvaAiu;
        ivaConsolidado += valorIvaAiu;
      }

      // Actualizar Indicadores de Participación
      ['PRODUCTO', 'MATERIAL', 'SERVICIO'].forEach(function (tipo) {
        var valSeccion = seccionTotales[tipo] || 0;
        var pct = totalFinal > 0 ? (valSeccion / totalFinal) * 100 : 0;
        
        var elVal = d.getElementById('indicador-valor-' + tipo);
        var elPct = d.getElementById('indicador-pct-' + tipo);
        
        if (elVal) elVal.innerText = self.format(valSeccion);
        if (elPct) elPct.innerText = pct.toFixed(1) + '%';
      });

      // Actualizar Resumen de Costos Simplificado
      var elSumNeto = d.getElementById('summary-subtotal-neto');
      if (elSumNeto) elSumNeto.innerText = self.format(totalNetoGeneral);

      // Actualizar Resumen Final
      var elIvaCons = d.getElementById('summary-iva-consolidado');
      if (elIvaCons) elIvaCons.innerText = self.format(ivaConsolidado);

      var elTotalGen = d.getElementById('summary-total-general');
      if (elTotalGen) elTotalGen.innerText = self.format(totalFinal);
    },

    calculateSchedule: function () {
      var input = d.getElementById('cot-dias-totales');
      if (!input) return;

      var total = parseInt(input.value) || 1;
      if (total < 1) total = 1;

      // Distribución heurística: 40% Infra, 30% Instal, 20% Config, 10% Pruebas
      var infra = Math.max(1, Math.round(total * 0.4));
      var instal = Math.max(1, Math.round(total * 0.3));
      var config = Math.max(1, Math.round(total * 0.2));
      var pruebas = Math.max(1, total - (infra + instal + config));

      if (pruebas < 1) pruebas = 1; // Garantizar al menos 1 día

      var elInfra = d.getElementById('tiempo-infra');
      var elInstal = d.getElementById('tiempo-instal');
      var elConfig = d.getElementById('tiempo-config');
      var elPruebas = d.getElementById('tiempo-pruebas');

      if (elInfra) { elInfra.innerText = infra + (infra === 1 ? ' Día' : ' Días'); elInfra.dataset.valor = infra; }
      if (elInstal) { elInstal.innerText = instal + (instal === 1 ? ' Día' : ' Días'); elInstal.dataset.valor = instal; }
      if (elConfig) { elConfig.innerText = config + (config === 1 ? ' Día' : ' Días'); elConfig.dataset.valor = config; }
      if (elPruebas) { elPruebas.innerText = pruebas + (pruebas === 1 ? ' Día' : ' Días'); elPruebas.dataset.valor = pruebas; }
    },

    format: function (val) {
      return w.Sintel.Cotizaciones.utils ? w.Sintel.Cotizaciones.utils.fmtMoney(val) : '$ ' + val.toLocaleString();
    },

    handlePaste: function (e) {
      var self = this;
      var clipboardData = e.clipboardData || w.clipboardData;
      var pastedData = clipboardData.getData('Text');
      
      if (pastedData.includes('\n') || pastedData.includes('\t')) {
        e.preventDefault();
        var rows = pastedData.split(/\r\n|\r|\n/);
        var firstRow = true;
        var tbody = e.target.closest('tbody');
        if (!tbody) return;
        var tipo = tbody.id.replace('seccion-', '');

        rows.forEach(function (line) {
          if (!line.trim()) return;
          var cols = line.split('\t');
          var utils = w.Sintel.Cotizaciones.utils;
          var data = {
            descripcion: cols[0] || '',
            marca: cols[1] || '',
            referencia: cols[2] || '',
            cantidad: utils ? utils.parseFloatSafe(cols[3]) : (parseFloat(cols[3]) || 1),
            unidad: cols[4] || 'UND',
            costo: utils ? utils.parseFloatSafe(cols[5]) : (parseFloat(cols[5]) || 0)
          };

          if (firstRow) {
            var currentRow = e.target.closest('tr');
            if (currentRow && !currentRow.querySelector('.item-descripcion').value.trim()) {
                currentRow.querySelector('.item-descripcion').value = data.descripcion;
                currentRow.querySelector('.item-marca').value = data.marca;
                currentRow.querySelector('.item-referencia').value = data.referencia;
                currentRow.querySelector('.item-cantidad').value = data.cantidad;
                currentRow.querySelector('.item-unidad').value = data.unidad;
                currentRow.querySelector('.item-costo').value = data.costo;
                self.calculateRow(currentRow);
                firstRow = false;
                return;
            }
            firstRow = false;
          }
          self.addRow(tipo, data);
        });
      }
    },

    save: function () {
      var self = this;
      var spinner = d.getElementById('cot-editor-spinner');
      if (spinner) spinner.classList.remove('d-none');

      var utils = w.Sintel.Cotizaciones.utils;
      var payload = {
        cliente: d.getElementById('cot-cliente-id')?.value || '',
        configuracion: d.getElementById('cot-config-id')?.value || '',
        fecha_emision: d.getElementById('cot-fecha-emision')?.value || '',
        iva_porcentaje: parseFloat(d.getElementById('cot-iva')?.value || 19),
        porcentaje_aiu_admin: parseFloat(d.getElementById('cot-aiu-admin')?.value || 0),
        porcentaje_aiu_imprevistos: parseFloat(d.getElementById('cot-aiu-imprevistos')?.value || 0),
        porcentaje_aiu_utilidad: parseFloat(d.getElementById('cot-aiu-utilidad')?.value || 0),
        tipo_cotizacion: d.getElementById('cot-tipo')?.value || 'MIXTO',
        dias_totales: parseInt(d.getElementById('cot-dias-totales')?.value || 1),
        dias_infraestructura: parseInt(d.getElementById('tiempo-infra')?.dataset.valor || 0),
        dias_instalacion: parseInt(d.getElementById('tiempo-instal')?.dataset.valor || 0),
        dias_configuracion: parseInt(d.getElementById('tiempo-config')?.dataset.valor || 0),
        dias_pruebas: parseInt(d.getElementById('tiempo-pruebas')?.dataset.valor || 0),
        items: []
      };

      if (!payload.cliente || !payload.configuracion) {
          if (w.UIManager) w.UIManager.notifyError('Cliente y Plantilla son obligatorios');
          if (spinner) spinner.classList.add('d-none');
          return;
      }

      d.querySelectorAll('.item-row').forEach(function (row, idx) {
        var itemData = {
          tipo_item: row.dataset.tipo,
          descripcion: row.querySelector('.item-descripcion').value,
          marca: row.querySelector('.item-marca').value,
          referencia: row.querySelector('.item-referencia').value,
          cantidad: utils ? utils.parseFloatSafe(row.querySelector('.item-cantidad').value) : parseFloat(row.querySelector('.item-cantidad').value),
          unidad: row.querySelector('.item-unidad').value,
          costo_unitario: utils ? utils.parseFloatSafe(row.querySelector('.item-costo').value) : parseFloat(row.querySelector('.item-costo').value),
          porcentaje_utilidad: parseFloat(row.dataset.utilidad || 0),
          orden: idx + 1
        };
        if (row.dataset.id) {
          itemData.id = parseInt(row.dataset.id);
        }
        payload.items.push(itemData);
      });

      var url = this._uuid ? this._api.updateUrl(this._uuid) : this._api.createUrl;
      var method = this._uuid ? 'PATCH' : 'POST';

      var btnGuardar = d.getElementById('btn-guardar-cot');
      if (btnGuardar) btnGuardar.disabled = true;

      fetch(url, {
        method: method,
        headers: this._api.getHeaders(),
        body: JSON.stringify(payload)
      })
      .then(function (r) {
        // Bug real (auditoria de modernizacion, 2026-08-27): antes se
        // lanzaba el body JSON crudo del error (ej. {"cliente": ["..."]})
        // en vez de la forma {ok,status,data} que UIManager.handleError
        // espera (documentada en cotizaciones.api.js) -- el usuario siempre
        // veia "Error desconocido" sin importar el error real de validacion.
        if (!r.ok) return r.json().catch(function () { return {}; }).then(function (e) {
          throw { ok: false, status: r.status, data: e };
        });
        return r.json();
      })
      .then(function (data) {
        if (data.items) self.syncIds(data.items);

        var msg = 'Cotización guardada exitosamente';
        if (method === 'POST') msg += ' • PDF generado';
        else msg += ' • PDF actualizado';

        if (w.UIManager) w.UIManager.showSuccess(msg);

        if (w.Sintel.Cotizaciones.table) w.Sintel.Cotizaciones.table.refresh();

        if (data.uuid) {
           self._uuid = data.uuid;
           // Activar botón PDF dinámicamente
           var btnPdf = d.getElementById('btn-pdf-cot');
           if (btnPdf) {
             btnPdf.href = `/api/v1/cotizaciones/${data.uuid}/exportar-pdf/`;
             btnPdf.classList.remove('d-none');
           }
           // Redirigir al workspace en lugar de exponer la URL del editor interno
           setTimeout(function () {
             window.location.href = '/workspace/#cotizaciones';
           }, 800);
        }
      })
      .catch(function (err) {
        if (w.UIManager) w.UIManager.handleError(err);
        else console.error(err);
      })
      .finally(function () {
        if (spinner) spinner.classList.add('d-none');
        if (btnGuardar) btnGuardar.disabled = false;
      });
    },

    /**
     * Sincroniza los IDs de la base de datos con las filas del DOM
     * Evita duplicados al guardar múltiples veces
     */
    syncIds: function (items) {
      var rows = d.querySelectorAll('.item-row');
      // Sincronizar por orden de aparición (match 1:1 con payload)
      rows.forEach(function (row, idx) {
        if (items[idx] && items[idx].id) {
          row.dataset.id = items[idx].id;
        }
      });
      console.log(MOD + ' IDs sincronizados con el backend');
    }
  };

  w.Sintel.Cotizaciones.Editor = CotizacionEditor;

})(window, document);
