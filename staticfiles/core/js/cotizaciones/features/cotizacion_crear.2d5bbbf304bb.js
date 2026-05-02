/**
 * Módulo de Creación de Cotizaciones - cotizacion_crear.js
 * Maneja EXCLUSIVAMENTE la creación (POST) de nuevas cotizaciones.
 * Extraído de cotizacion_editor.js - Lógica completa de creación.
 * 
 * ⚠️ v2.61: Feature-Sliced Architecture - Separación completa de crear/editar
 * ⚠️ v2.61: Usa IDs estándar (modal-cotizacion-editor, editor-select-*, etc.)
 */
(function (w, d) {
  'use strict';

  const MOD = 'cotizacion-crear';

  // ⚠️ v2.60: PATRÓN SINGLETON - Usar objeto global para prevenir zombies de HTMX
  // Inicializar objeto global si no existe
  if (!w.SintelCotizacionTables) {
    w.SintelCotizacionTables = {};
  }

  // ─── Utilidades ─────────────────────────────────────────────────────────────
  function fmtMoney(v) {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(v || 0);
  }

  // ⚠️ v2.61: Flag para evitar múltiples llamadas simultáneas a cargarDatosEmisor
  let cargandoEmisor = false;

  // ─── Limpieza de estado ──────────────────────────────────────────────────────
  function resetState() {
    // ⚠️ v2.60: LIMPIEZA GLOBAL - Destruir instancias zombis de Tabulator antes de reiniciar
    if (w.SintelCotizacionTables) {
      Object.keys(w.SintelCotizacionTables).forEach(key => {
        const tb = w.SintelCotizacionTables[key];
        if (tb && typeof tb.destroy === 'function') {
          try {
            console.log(`[${MOD}] Limpiando tabla zombie: ${key}`);
            tb.destroy();
          } catch (e) {
            console.warn(`[${MOD}] Error al destruir tabla zombie ${key}:`, e);
          }
        }
      });
    }
    // ⚠️ v2.60: Reiniciar el registro global
    w.SintelCotizacionTables = {};
    console.log(`[${MOD}] Objeto global SintelCotizacionTables reiniciado`);
    
    // ⚠️ v2.61: Resetear flag de carga de emisor
    cargandoEmisor = false;
    
    const editorDiv = d.getElementById('modal-cotizacion-editor');
    if (editorDiv) editorDiv.removeAttribute('data-init');
  }

  /**
   * ⚠️ v2.60: Carga datos del emisor desde el SSoT de Empresas para el encabezado del Editor.
   * 
   * Consume el endpoint `/api/v1/empresas/current-header/` que retorna:
   * - id, razon_social, nit, logo (URL absoluta)
   * 
   * Actualiza el DOM del módulo "Datos del Emisor" con la información de la empresa.
   */
  async function cargarDatosEmisor() {
    const context = `[${MOD}.cargarDatosEmisor]`;
    
    // ⚠️ v2.61: Prevenir múltiples llamadas simultáneas
    if (cargandoEmisor) {
      console.log(`${context} Ya hay una carga en progreso, omitiendo...`);
      return;
    }
    
    // ⚠️ v2.61: Verificar que w.http esté disponible
    if (!w.http || typeof w.http !== 'function') {
      console.error(`${context} ❌ window.http no está disponible`);
      const elNombre = d.getElementById('emisor-nombre');
      const elNit = d.getElementById('emisor-nit');
      const elLogoContainer = d.getElementById('emisor-logo-container');
      if (elNombre) elNombre.textContent = 'Error: Utilidad HTTP no disponible';
      if (elNit) elNit.textContent = 'N/A';
      if (elLogoContainer) {
        elLogoContainer.innerHTML = `<div class="bg-light rounded p-2 text-muted d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;"><i class="bi bi-exclamation-triangle text-warning" style="font-size: 1.5rem;"></i></div>`;
      }
      return;
    }
    
    try {
      const elNombre = d.getElementById('emisor-nombre');
      const elNit = d.getElementById('emisor-nit');
      const elLogoContainer = d.getElementById('emisor-logo-container');
      
      // Verificar que los elementos existan
      if (!elNombre || !elNit || !elLogoContainer) {
        console.warn(`${context} Elementos del módulo emisor no encontrados en el DOM`);
        return;
      }
      
      // ⚠️ v2.61: Marcar como cargando
      cargandoEmisor = true;
      
      // ⚠️ v2.60: Consumir endpoint específico para header del editor
      const res = await w.http('GET', '/api/v1/empresas/current-header/');
      
      if (res.ok && res.data) {
        const empresa = res.data;
        
        // Actualizar nombre de la empresa
        elNombre.textContent = empresa.razon_social || 'Empresa Emisora';
        
        // Actualizar NIT
        elNit.textContent = empresa.nit || 'N/A';
        
        // Actualizar logo
        if (empresa.logo) {
          // Si hay logo, mostrar imagen
          elLogoContainer.innerHTML = `<img src="${empresa.logo}" alt="Logo ${empresa.razon_social || 'Empresa'}" style="max-height: 40px; width: auto; object-fit: contain;" class="rounded">`;
        } else {
          // Si no hay logo, mostrar icono placeholder
          elLogoContainer.innerHTML = `<div class="bg-light rounded p-2 text-muted d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;"><i class="bi bi-building" style="font-size: 1.5rem;"></i></div>`;
        }
        
        console.log(`${context} Datos del emisor cargados correctamente: ${empresa.razon_social}`);
      } else {
        // Si no hay empresa o hay error, mostrar estado por defecto
        elNombre.textContent = 'Empresa no configurada';
        elNit.textContent = 'N/A';
        elLogoContainer.innerHTML = `<div class="bg-light rounded p-2 text-muted d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;"><i class="bi bi-building" style="font-size: 1.5rem;"></i></div>`;
        
        if (res.status === 404) {
          console.warn(`${context} No existe una empresa configurada para este tenant`);
        } else {
          console.warn(`${context} Error al cargar datos del emisor:`, res.status);
        }
      }
    } catch (error) {
      // ⚠️ Error Boundary v2.60: Manejar errores con UIManager
      console.error(`${context} Error al cargar datos del emisor:`, error);
      
      const elNombre = d.getElementById('emisor-nombre');
      const elNit = d.getElementById('emisor-nit');
      const elLogoContainer = d.getElementById('emisor-logo-container');
      
      if (elNombre) elNombre.textContent = 'Error al cargar emisor';
      if (elNit) elNit.textContent = 'N/A';
      if (elLogoContainer) {
        elLogoContainer.innerHTML = `<div class="bg-light rounded p-2 text-muted d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;"><i class="bi bi-exclamation-triangle text-warning" style="font-size: 1.5rem;"></i></div>`;
      }
    } finally {
      // ⚠️ v2.61: Siempre resetear el flag al finalizar (éxito o error)
      cargandoEmisor = false;
    }
  }

  /**
   * ⚠️ v2.60: Configura fechas por defecto (emisión = hoy).
   * 
   * Establece automáticamente:
   * - Fecha de emisión: Día actual (si está vacía)
   */
  function configurarFechasPorDefecto() {
    const context = `[${MOD}.configurarFechasPorDefecto]`;
    
    try {
      const elEmision = d.getElementById('input-fecha-emision');
      
      if (!elEmision) {
        console.warn(`${context} Campo de fecha de emisión no encontrado en el DOM`);
        return;
      }

      // Obtener fecha actual en formato YYYY-MM-DD (hora local)
      const hoy = new Date();
      const tzOffset = hoy.getTimezoneOffset() * 60000;
      const fechaLocalISO = new Date(hoy - tzOffset).toISOString().split('T')[0];

      // Si la fecha de emisión está vacía (ej. nueva cotización), establecer hoy
      if (!elEmision.value) {
        elEmision.value = fechaLocalISO;
        console.log(`${context} Fecha de emisión establecida: ${fechaLocalISO}`);
      }
    } catch (error) {
      console.error(`${context} Error al configurar fechas por defecto:`, error);
    }
  }

  /**
   * ⚠️ v2.60: Actualiza la previsualización en tiempo real del Folio Proyectado y Fecha de Vencimiento
   * cuando el usuario selecciona una plantilla base.
   * 
   * Lee los atributos data-* del option seleccionado y calcula:
   * - Folio Proyectado: Prefijo + Siguiente Número (formateado) + Sufijo
   * - Fecha de Vencimiento: Fecha actual + Días de Validez
   */
  function actualizarPrevisualizacionPlantilla() {
    const selectPerfil = d.getElementById('editor-select-perfil');
    if (!selectPerfil || selectPerfil.selectedIndex === -1) {
      // Resetear previsualización si no hay selección
      const elFolio = d.getElementById('preview-folio');
      const elVencimiento = d.getElementById('preview-vencimiento');
      const elDiasValidez = d.getElementById('preview-dias-validez');
      
      if (elFolio) elFolio.textContent = 'Seleccione una plantilla...';
      if (elVencimiento) elVencimiento.textContent = '--';
      if (elDiasValidez) elDiasValidez.textContent = 'Validez: -- días.';
      return;
    }
    
    const option = selectPerfil.options[selectPerfil.selectedIndex];
    if (!option || !option.value) {
      // Resetear previsualización si no hay valor
      const elFolio = d.getElementById('preview-folio');
      const elVencimiento = d.getElementById('preview-vencimiento');
      const elDiasValidez = d.getElementById('preview-dias-validez');
      
      if (elFolio) elFolio.textContent = 'Seleccione una plantilla...';
      if (elVencimiento) elVencimiento.textContent = '--';
      if (elDiasValidez) elDiasValidez.textContent = 'Validez: -- días.';
      return;
    }

    // 1. Calcular Fecha de Vencimiento
    const diasValidez = parseInt(option.getAttribute('data-dias')) || 15;
    const fechaActual = new Date();
    fechaActual.setDate(fechaActual.getDate() + diasValidez);
    
    const opcionesFecha = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const fechaFormateada = fechaActual.toLocaleDateString('es-CO', opcionesFecha);
    
    const elVencimiento = d.getElementById('preview-vencimiento');
    const elDiasValidez = d.getElementById('preview-dias-validez');
    
    if (elVencimiento) {
      elVencimiento.textContent = fechaFormateada;
    }
    
    if (elDiasValidez) {
      elDiasValidez.textContent = `Validez: ${diasValidez} días desde hoy.`;
    }

    // 2. Calcular Folio Proyectado
    const ultimoNumero = parseInt(option.getAttribute('data-ultimo')) || 0;
    const semilla = parseInt(option.getAttribute('data-semilla')) || 1;
    const prefijo = option.getAttribute('data-prefijo') || '';
    const sufijo = option.getAttribute('data-sufijo') || '';
    
    const siguienteNumero = ultimoNumero === 0 ? semilla : ultimoNumero + 1;
    // Formatear a 4 dígitos con ceros a la izquierda
    const numeroFormateado = String(siguienteNumero).padStart(4, '0');
    
    const folioProyectado = `${prefijo}${numeroFormateado}${sufijo}`;
    const elFolio = d.getElementById('preview-folio');
    
    if (elFolio) {
      elFolio.innerHTML = `${folioProyectado} <span class="badge bg-warning text-dark ms-2 fs-6">Proyectado</span>`;
    }
    
    console.log(`[${MOD}] Previsualización actualizada: Folio=${folioProyectado}, Vencimiento=${fechaFormateada}, Días=${diasValidez}`);
  }

  /**
   * Reindexa todas las filas de una tabla asignando números consecutivos (1, 2, 3...)
   * @param {Tabulator} table - Instancia de Tabulator a reindexar
   */
  function reindexarFilas(table) {
    if (!table) return;
    
    const rows = table.getRows();
    rows.forEach(function(row, index) {
      row.update({ nro_item: index + 1 });
    });
  }

  /**
   * Inicializa las tablas Tabulator para los tres módulos: Equipos, Materiales y Servicios
   * ⚠️ Garantiza funcionalidad completa en todos los módulos visibles
   */
  function initVisibleGrids() {
    const grids = [
      { id: 'equipos', selector: '#grid-editor-equipos', section: 'section-equipos' },
      { id: 'materiales', selector: '#grid-editor-materiales', section: 'section-materiales' },
      { id: 'servicios', selector: '#grid-editor-servicios', section: 'section-servicios' }
    ];

    grids.forEach(sec => {
      const container = d.querySelector(sec.selector);
      const sectionEl = d.getElementById(sec.section);
      
      // Verificar que el contenedor existe y la sección está visible
      if (container && sectionEl && !sectionEl.classList.contains('d-none')) {
        // Si la tabla ya existe, no recrearla
        if (w.SintelCotizacionTables[sec.id]) {
          console.log(`[${MOD}] Tabla ${sec.id} ya inicializada`);
          return;
        }
        
        console.log(`[${MOD}] Inicializando tabla: ${sec.id}`);
        
        // ⚠️ Error Boundary v2.60: Envolver creación de tabla con manejo de errores
        let table;
        try {
          table = new w.Tabulator(sec.selector, {
            layout: "fitColumns",
            columns: w.getCotizacionColumns(sec.id, true),
            placeholder: "Presione el botón + en la columna ACCIONES para agregar items",
            dataChanged: function(data) {
              // Recalcular subtotales cuando cambian los datos
              data.forEach(function(row) {
                const cant = parseFloat(row.cantidad) || 0;
                const precio = parseFloat(row.costo_unitario) || 0;
                const subtotal = cant * precio;
                if (row.subtotal_linea !== subtotal) {
                  const tableRow = table.getRowFromData(row);
                  if (tableRow) {
                    tableRow.update({ subtotal_linea: subtotal }, false);
                  }
                }
              });
              actualizarPanelTotales();
            },
            rowAdded: function(row) {
              // ⚠️ Calcular subtotal_linea automáticamente al añadir nueva fila
              const data = row.getData();
              const cant = parseFloat(data.cantidad) || 0;
              const precio = parseFloat(data.costo_unitario) || 0;
              const subtotal = cant * precio;
              
              // Actualizar subtotal (usar true para actualizar visualmente)
              row.update({ subtotal_linea: subtotal }, true);
              
              // Reindexar todas las filas después de añadir
              reindexarFilas(table);
              
              // Actualizar panel de totales
              actualizarPanelTotales();
            },
            rowDeleted: function(row) {
              // Reindexar todas las filas después de eliminar
              reindexarFilas(table);
              
              // Actualizar panel de totales después de eliminar
              actualizarPanelTotales();
            }
          });
        } catch (error) {
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError({ 
              status: 500, 
              data: { detail: `Error al crear tabla ${sec.id}: ${error.message || 'Error desconocido'}` } 
            }, `[${MOD}]`);
          }
          console.error(`[${MOD}] Error al crear tabla ${sec.id}:`, error);
          return; // Salir de esta iteración si hay error
        }
        
        w.SintelCotizacionTables[sec.id] = table;
        
        console.log(`[${MOD}] Tabla ${sec.id} inicializada correctamente`);
        
        // Reindexar filas iniciales y recalcular subtotales si hay datos
        setTimeout(function() {
          if (table.getDataCount() > 0) {
            // Recalcular subtotales para todas las filas existentes
            const allData = table.getData();
            allData.forEach(function(rowData) {
              const cant = parseFloat(rowData.cantidad) || 0;
              const precio = parseFloat(rowData.costo_unitario) || 0;
              const subtotal = cant * precio;
              const row = table.getRowFromData(rowData);
              if (row) {
                row.update({ subtotal_linea: subtotal }, true);
              }
            });
            
            reindexarFilas(table);
            actualizarPanelTotales();
          }
        }, 100);
      } else {
        // Si la sección está oculta, destruir la tabla si existe
        if (w.SintelCotizacionTables[sec.id]) {
          console.log(`[${MOD}] Destruyendo tabla ${sec.id} (sección oculta)`);
          w.SintelCotizacionTables[sec.id].destroy();
          delete w.SintelCotizacionTables[sec.id];
        }
      }
    });
    
    // Actualizar totales después de inicializar todas las tablas
    setTimeout(function() {
      actualizarPanelTotales();
    }, 200);
  }

  /**
   * ⚠️ v2.60: Función principal para recalcular totales globales
   * Usa el objeto `tables` directamente para mayor confiabilidad
   * 
   * ⚠️ SAFEGUARD HTMX: Previene ejecuciones fantasma en DOM desprendido
   */
  function recalcularTotalesGlobales() {
    // ⚠️ BLINDAJE ANTI-ZOMBI v2.60: Verificar que el elemento existe Y está conectado al DOM principal
    // Esto mata a los listeners fantasma de HTMX que se ejecutan en DOM desprendido
    const elSubtotal = d.getElementById('total-subtotal');
    // ⚠️ SAFEGUARD HTMX: Si el panel no existe o no está conectado al DOM principal, abortar.
    // Esto previene que closures viejos alteren el DOM nuevo después de un swap de HTMX
    if (!elSubtotal || !elSubtotal.isConnected) {
      console.warn('[cotizacion-totales] ⚠️ Ejecución fantasma abortada. El DOM está desconectado o el elemento no existe.');
      return; // Abortar inmediatamente si el DOM no está disponible o está desconectado
    }
    
    try {
      
      // ⚠️ Debug: Verificar que la función se esté llamando y que tables esté disponible
      const tablasKeys = Object.keys(w.SintelCotizacionTables || {});
      console.log('[cotizacion-totales] Recalculando totales globales...', {
        tablasDisponibles: tablasKeys,
        cantidadTablas: tablasKeys.length
      });
      
      // ⚠️ Si no hay tablas, loguear pero aún así actualizar el DOM con valores en 0
      if (tablasKeys.length === 0) {
        console.warn('[cotizacion-totales] ⚠️ No hay tablas disponibles. Verificar que los módulos estén activados.');
        console.warn('[cotizacion-totales] Para activar un módulo, use los switches en "Configuración Dinámica"');
        // Aún así actualizar el DOM con valores en 0 para que se muestre correctamente
      }
      
      let subtotalGlobal = 0;
      let ivaGlobal = 0;
      let granTotal = 0;
      
      const tbodyDashboard = d.getElementById('tbody-dashboard-modulos');
      if (tbodyDashboard) tbodyDashboard.innerHTML = ''; // Limpiar dashboard

      const formatear = (valor) => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(valor || 0);

      // ⚠️ v2.60: Iterar sobre las tablas almacenadas en el objeto `tables` (más confiable que buscar en DOM)
      // Mapeo de secciones a contenedores para obtener títulos
      const seccionesMap = {
        'equipos': { container: '#section-equipos', titulo: 'Equipos y Suministros' },
        'materiales': { container: '#section-materiales', titulo: 'Materiales de Instalación' },
        'servicios': { container: '#section-servicios', titulo: 'Servicios Profesionales' }
      };

      // ⚠️ v2.60: Iterar sobre las tablas activas en el objeto global `SintelCotizacionTables`
      tablasKeys.forEach(seccion => {
        const table = w.SintelCotizacionTables[seccion];
        if (!table) {
          console.warn(`[cotizacion-totales] Tabla ${seccion} existe en keys pero es null/undefined`);
          return;
        }

        // Verificar que el módulo esté visible (no tenga d-none)
        const seccionInfo = seccionesMap[seccion];
        if (seccionInfo) {
          const container = d.querySelector(seccionInfo.container);
          if (container && container.classList.contains('d-none')) {
            // Módulo oculto, no incluir en cálculos
            console.log(`[cotizacion-totales] Módulo ${seccion} está oculto (d-none), omitiendo de cálculos`);
            return;
          }
        } else {
          console.warn(`[cotizacion-totales] No se encontró información de sección para: ${seccion}`);
        }

        let modCosto = 0;
        let modUtil = 0;
        let modDesc = 0;
        let modIva = 0;
        let modTotal = 0;
        let modSubtotal = 0;
        
        try {
          // ⚠️ Verificar que la tabla tenga el método getRows antes de usarlo
          if (typeof table.getRows !== 'function') {
            console.error(`[cotizacion-totales] Tabla ${seccion} no tiene método getRows(). Tipo:`, typeof table);
            return;
          }
          
          // Extraer datos estrictamente de las filas de Tabulator
          const rows = table.getRows();
          if (!rows || rows.length === 0) {
            console.log(`[cotizacion-totales] Tabla ${seccion} no tiene filas`);
            return;
          }
          
          rows.forEach(row => {
            const data = row.getData();
            modCosto += parseFloat(data._costo_total_interno) || 0;
            modUtil += parseFloat(data._valor_utilidad_interno) || 0;
            modDesc += parseFloat(data._valor_descuento_interno) || 0;
            modIva += parseFloat(data._valor_iva_interno) || 0;
            modSubtotal += parseFloat(data.subtotal_linea) || 0;
            modTotal += parseFloat(data.valor_total_linea) || 0;
          });

          // Sumar al acumulado global
          subtotalGlobal += modSubtotal;
          ivaGlobal += modIva;
          granTotal += modTotal;

          // Inyectar fila en el Dashboard Financiero por Módulo
          if (modTotal > 0 && tbodyDashboard && seccionInfo) {
            tbodyDashboard.insertAdjacentHTML('beforeend', `
              <tr>
                <td class="text-start fw-bold">${seccionInfo.titulo}</td>
                <td>${formatear(modCosto)}</td>
                <td class="text-success">+ ${formatear(modUtil)}</td>
                <td class="text-danger">- ${formatear(modDesc)}</td>
                <td>${formatear(modIva)}</td>
                <td class="fw-bold bg-light">${formatear(modTotal)}</td>
              </tr>
            `);
          }
        } catch (error) {
          console.error(`[cotizacion-totales] Error al procesar tabla ${seccion}:`, error);
        }
      });

      // ⚠️ REFACTORIZACIÓN: Lógica del AIU (Opcional - Componentes individuales)
      const switchAiu = d.getElementById('switch-activar-aiu');
      let valorAiuGlobal = 0;
      
      if (switchAiu && switchAiu.checked) {
        // ⚠️ REFACTORIZACIÓN: Calcular AIU desde los tres componentes individuales
        const porcentajeAiuAdmin = parseFloat(d.getElementById('input-aiu-admin')?.value) || 0;
        const porcentajeAiuImprevistos = parseFloat(d.getElementById('input-aiu-imprevistos')?.value) || 0;
        const porcentajeAiuUtilidad = parseFloat(d.getElementById('input-aiu-utilidad')?.value) || 0;
        
        // ⚠️ Sumar los tres porcentajes para obtener el porcentaje total de AIU
        const porcentajeAiuTotal = porcentajeAiuAdmin + porcentajeAiuImprevistos + porcentajeAiuUtilidad;
        
        // El AIU se calcula sobre el Subtotal (Base) de los costos
        valorAiuGlobal = subtotalGlobal * (porcentajeAiuTotal / 100);
      }

      // Gran Total Final (con AIU si aplica)
      const granTotalFinal = granTotal + valorAiuGlobal;

      // ⚠️ v2.60: Actualizar Panel de Totales Finales (elSubtotal ya fue verificado en el safeguard)
      // Re-obtener elementos para asegurar que están en el DOM actual (no desprendido)
      const elSubtotalFinal = d.getElementById('total-subtotal');
      const elIva = d.getElementById('total-iva');
      const elAiu = d.getElementById('total-aiu');
      const elContenedorAiu = d.getElementById('contenedor-total-aiu');
      const elFinal = d.getElementById('total-final');

      // ⚠️ v2.60: Actualización segura del DOM con verificación de existencia
      // Usar formatear() para consistencia en formato de moneda
      if (elSubtotalFinal) {
        elSubtotalFinal.textContent = formatear(subtotalGlobal);
      } else {
        console.warn('[cotizacion-totales] ⚠️ Elemento #total-subtotal no encontrado (DOM puede haber cambiado)');
      }
      
      if (elIva) {
        elIva.textContent = formatear(ivaGlobal);
      } else {
        console.warn('[cotizacion-totales] ⚠️ Elemento #total-iva no encontrado');
      }
      
      if (elFinal) {
        elFinal.textContent = formatear(granTotalFinal);
      } else {
        console.warn('[cotizacion-totales] ⚠️ Elemento #total-final no encontrado');
      }
      
      // Mostrar/ocultar AIU según si está aplicado
      if (elContenedorAiu && elAiu) {
        if (valorAiuGlobal > 0) {
          elContenedorAiu.style.display = 'block';
          elAiu.textContent = formatear(valorAiuGlobal);
        } else {
          elContenedorAiu.style.display = 'none';
          elAiu.textContent = formatear(0);
        }
      } else {
        if (!elContenedorAiu) console.warn('[cotizacion-totales] Elemento #contenedor-total-aiu no encontrado');
        if (!elAiu) console.warn('[cotizacion-totales] Elemento #total-aiu no encontrado');
      }

    } catch (error) {
      console.error('[cotizacion-totales] Error al recalcular totales globales:', error);
      // ⚠️ Error Boundary v2.60: Usar UIManager.notifyError según arquitectura
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(error, '[cotizacion-totales]');
      }
    }
  }

  /**
   * ⚠️ v2.60: Alias para compatibilidad - apunta a recalcularTotalesGlobales
   */
  function actualizarPanelTotales() {
    recalcularTotalesGlobales();
  }

  /**
   * ⚠️ v2.60: Configura listeners para Panel de Configuración Dinámica (User-Driven).
   * - Listeners para switches de módulos (.dna-switch)
   * - Listeners para campos financieros (.dna-finance)
   */
  function configurarListenersDinamicos() {
    const context = `[${MOD}.listeners-dinamicos]`;
    
    // ⚠️ Listeners para switches de módulos
    const switches = d.querySelectorAll('.dna-switch');
    switches.forEach(switchEl => {
      // Remover listeners previos si existen (prevención de duplicados)
      const newSwitch = switchEl.cloneNode(true);
      switchEl.parentNode.replaceChild(newSwitch, switchEl);
      
      newSwitch.addEventListener('change', async function(e) {
        const target = e.target;
        const containerSelector = target.getAttribute('data-target');
        const seccion = target.getAttribute('data-seccion');
        const isChecked = target.checked;
        
        console.log(`${context} Switch ${seccion} ${isChecked ? 'activado' : 'desactivado'}`);
        
        if (!containerSelector || !seccion) {
            console.warn(`${context} Switch sin data-target o data-seccion`);
            return;
        }
        
        const container = d.querySelector(containerSelector);
        if (!container) {
            console.warn(`${context} Contenedor no encontrado: ${containerSelector}`);
            return;
        }
        
        if (isChecked) {
            // ⚠️ Usuario enciende switch: Quitar d-none PRIMERO
            container.classList.remove('d-none');
            
            // ⚠️ v2.60: Pequeño delay para asegurar que el DOM se actualizó antes de inicializar
            await new Promise(resolve => setTimeout(resolve, 50));
            
            // ⚠️ Reutilizar función existente de inicialización
            if (!w.SintelCotizacionTables[seccion]) {
                // Mapear sección a grid selector
                const gridSelectors = {
                    'equipos': '#grid-editor-equipos',
                    'materiales': '#grid-editor-materiales',
                    'servicios': '#grid-editor-servicios'
                };
                
                const gridSelector = gridSelectors[seccion];
                if (gridSelector) {
                    console.log(`${context} Inicializando tabla para sección: ${seccion}, grid: ${gridSelector}`);
                    // Inicializar tabla usando initVisibleGrids
                    initVisibleGrids();
                    
                    // ⚠️ v2.60: Verificar que la tabla se guardó correctamente
                    if (w.SintelCotizacionTables[seccion]) {
                        console.log(`${context} ✅ Tabla ${seccion} guardada correctamente en SintelCotizacionTables`);
                        console.log(`${context} Estado actual de SintelCotizacionTables:`, Object.keys(w.SintelCotizacionTables));
                    } else {
                        console.error(`${context} ❌ ERROR: Tabla ${seccion} NO se guardó en SintelCotizacionTables`);
                    }
                } else {
                    console.error(`${context} ERROR: No se encontró gridSelector para sección: ${seccion}`);
                }
            } else {
                console.log(`${context} Tabla ${seccion} ya existe en SintelCotizacionTables`);
            }
        } else {
            // ⚠️ Usuario apaga switch: Añadir d-none y destruir tabla
            container.classList.add('d-none');
            
            // ⚠️ Reutilizar lógica existente de destrucción
            if (w.SintelCotizacionTables[seccion]) {
                console.log(`${context} Destruyendo tabla ${seccion} (switch desactivado)`);
                try {
                    w.SintelCotizacionTables[seccion].destroy();
                } catch (error) {
                    console.error(`${context} Error al destruir tabla ${seccion}:`, error);
                }
                delete w.SintelCotizacionTables[seccion];
            }
            
            // ⚠️ QA v2.60: Matemática de recálculo - Actualizar totales INMEDIATAMENTE
            // al destruir tabla para que el total global reste correctamente ese valor
            actualizarPanelTotales();
        }
        
        // Actualizar panel de totales después de cambiar visibilidad (solo si se activó)
        if (isChecked) {
            // ⚠️ v2.60: Esperar un poco más para asegurar que la tabla esté completamente inicializada
            setTimeout(function() {
                console.log(`${context} Verificando tabla ${seccion} antes de actualizar totales:`, {
                    existeEnSintelCotizacionTables: !!w.SintelCotizacionTables[seccion],
                    keysEnSintelCotizacionTables: Object.keys(w.SintelCotizacionTables || {})
                });
                actualizarPanelTotales();
            }, 200);
        }
      });
    });
    
    // ⚠️ Listeners para campos financieros (IVA, AIU)
    const financeInputs = d.querySelectorAll('.dna-finance');
    financeInputs.forEach(input => {
        // Remover listeners previos si existen (prevención de duplicados)
        const newInput = input.cloneNode(true);
        input.parentNode.replaceChild(newInput, input);
        
        newInput.addEventListener('input', function(e) {
            // ⚠️ Recalcular totales globales cuando cambian los parámetros financieros
            actualizarPanelTotales();
        });
    });
    
    // ⚠️ REFACTORIZACIÓN: Listener para switch "Activar AIU" (Opcional)
    // ⚠️ Este listener maneja la visibilidad de los campos AIU y resetea valores cuando se desactiva
    const switchActivarAiu = d.getElementById('switch-activar-aiu');
    if (switchActivarAiu) {
        // Remover listener previo si existe (prevención de duplicados en recargas HTMX)
        const newSwitch = switchActivarAiu.cloneNode(true);
        switchActivarAiu.parentNode.replaceChild(newSwitch, switchActivarAiu);
        
        newSwitch.addEventListener('change', function(e) {
            const container = d.getElementById('container-aiu-fields');
            
            if (!container) {
                console.warn(`${context} Contenedor de campos AIU (container-aiu-fields) no encontrado`);
                return;
            }
            
            if (e.target.checked) {
                // ⚠️ Switch activado: Mostrar campos AIU
                container.classList.remove('d-none');
                console.log(`${context} Campos AIU mostrados`);
                
                // ⚠️ Recalcular totales cuando se activa (por si hay valores predefinidos)
                actualizarPanelTotales();
            } else {
                // ⚠️ Switch desactivado: Ocultar campos AIU y resetear valores a 0
                container.classList.add('d-none');
                
                // ⚠️ Resetear valores a 0 si se desactiva
                const inputAiuAdmin = d.getElementById('input-aiu-admin');
                const inputAiuImprevistos = d.getElementById('input-aiu-imprevistos');
                const inputAiuUtilidad = d.getElementById('input-aiu-utilidad');
                
                if (inputAiuAdmin) {
                    inputAiuAdmin.value = "0.00";
                }
                if (inputAiuImprevistos) {
                    inputAiuImprevistos.value = "0.00";
                }
                if (inputAiuUtilidad) {
                    inputAiuUtilidad.value = "0.00";
                }
                
                console.log(`${context} Campos AIU ocultados y valores reseteados a 0.00`);
                
                // ⚠️ Forzar recálculo sin AIU (valores ahora son 0)
                actualizarPanelTotales();
            }
        });
    }
    
    console.log(`${context} Listeners dinámicos configurados: ${switches.length} switches, ${financeInputs.length} inputs financieros, switch AIU: ${switchActivarAiu ? 'configurado' : 'no encontrado'}`);
  }

  /**
   * ⚠️ v2.61: Guardar cotización (POST) - Solo creación
   * Extraído de guardarCotizaciónFinal() de cotizacion_editor.js
   */
  async function guardarCotizaciónFinal() {
    try {
      // ⚠️ v2.60: User-Driven - Extraer valores de inputs financieros desde el DOM
      // El backend espera estos campos individuales para IVA y componentes de AIU
      
      // ⚠️ v2.60: Construir payload con valores de inputs financieros en nivel principal
      // ⚠️ v2.60: fecha_vencimiento ELIMINADA - El backend la calcula según los días de validez de la plantilla
      
      // ⚠️ CORRECCIÓN: Asegurar que cliente sea un ID numérico, no texto descriptivo
      const selectCliente = d.getElementById('editor-select-cliente');
      const clienteValue = selectCliente?.value;
      
      // ⚠️ VALIDACIÓN ESTRICTA: Validar cliente ANTES de armar el payload
      if (!clienteValue || isNaN(parseInt(clienteValue, 10))) {
        if (w.UIManager && typeof w.UIManager.showToast === 'function') {
          w.UIManager.showToast('Debe seleccionar un cliente válido de la lista', 'error');
        } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ 
            status: 400, 
            data: { detail: 'Debe seleccionar un cliente válido de la lista' } 
          }, `[${MOD}]`);
        }
        return;
      }
      
      // ⚠️ CORRECCIÓN: Asegurar que configuracion sea un ID numérico
      const selectPerfil = d.getElementById('editor-select-perfil');
      const configuracionValue = selectPerfil?.value;
      const configuracionId = configuracionValue ? parseInt(configuracionValue, 10) : null;
      
      const payload = {
        // ⚠️ CRÍTICO: cliente DEBE ser un entero (ID numérico de la base de datos)
        cliente: parseInt(document.getElementById('editor-select-cliente').value, 10),
        configuracion: configuracionId,
        fecha_emision: d.getElementById('input-fecha-emision')?.value || null,
        // ⚠️ v2.60: fecha_vencimiento ELIMINADA - El backend la calcula automáticamente desde dias_validez del perfil
        
        // ⚠️ PASO 3: Valores financieros capturados del DOM con validación estricta
        // ⚠️ CRÍTICO: Usar parseFloat() con validación para evitar null o valores inválidos
        // Si el campo está vacío o es inválido, usar valores por defecto
        iva_porcentaje: (() => {
          const value = d.getElementById('input-iva-porcentaje')?.value;
          const parsed = parseFloat(value);
          return (!isNaN(parsed) && value !== '') ? parsed : 19.00;
        })(),
        // ⚠️ REFACTORIZACIÓN: Campos AIU opcionales - Enviar estrictamente 0 si el switch está apagado
        // ⚠️ CRÍTICO: Si el switch está desactivado, enviar 0 independientemente de valores en inputs ocultos
        porcentaje_aiu_admin: (() => {
          const switchAiu = d.getElementById('switch-activar-aiu');
          // ⚠️ Si el switch no existe o está desactivado, enviar estrictamente 0
          if (!switchAiu || !switchAiu.checked) {
            return 0.00;
          }
          // ⚠️ Solo capturar valor si el switch está activado
          const value = d.getElementById('input-aiu-admin')?.value;
          const parsed = parseFloat(value);
          return (!isNaN(parsed) && value !== '') ? parsed : 0.00;
        })(),
        porcentaje_aiu_imprevistos: (() => {
          const switchAiu = d.getElementById('switch-activar-aiu');
          // ⚠️ Si el switch no existe o está desactivado, enviar estrictamente 0
          if (!switchAiu || !switchAiu.checked) {
            return 0.00;
          }
          // ⚠️ Solo capturar valor si el switch está activado
          const value = d.getElementById('input-aiu-imprevistos')?.value;
          const parsed = parseFloat(value);
          return (!isNaN(parsed) && value !== '') ? parsed : 0.00;
        })(),
        porcentaje_aiu_utilidad: (() => {
          const switchAiu = d.getElementById('switch-activar-aiu');
          // ⚠️ Si el switch no existe o está desactivado, enviar estrictamente 0
          if (!switchAiu || !switchAiu.checked) {
            return 0.00;
          }
          // ⚠️ Solo capturar valor si el switch está activado
          const value = d.getElementById('input-aiu-utilidad')?.value;
          const parsed = parseFloat(value);
          return (!isNaN(parsed) && value !== '') ? parsed : 0.00;
        })(),
        tipo_cotizacion: d.getElementById('editor-select-tipo-cotizacion')?.value || 'MIXTO',
        items: []
      };
      
      // ⚠️ PASO 3: Logging para verificar valores financieros capturados
      console.log(`[${MOD}] ID Cliente enviado:`, payload.cliente, `(tipo: ${typeof payload.cliente})`);
      console.log(`[${MOD}] ID Configuración enviado:`, payload.configuracion, `(tipo: ${typeof payload.configuracion})`);
      console.log(`[${MOD}] Valores financieros capturados:`, {
        iva_porcentaje: payload.iva_porcentaje,
        porcentaje_aiu_admin: payload.porcentaje_aiu_admin,
        porcentaje_aiu_imprevistos: payload.porcentaje_aiu_imprevistos,
        porcentaje_aiu_utilidad: payload.porcentaje_aiu_utilidad,
        tipo_cotizacion: payload.tipo_cotizacion
      });
      
      // Validar campos requeridos
      if (!payload.cliente || !payload.configuracion || !payload.fecha_emision) {
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ 
            status: 400, 
            data: { detail: 'Por favor complete todos los campos requeridos (Cliente, Perfil, Fecha de Emisión)' } 
          }, `[${MOD}]`);
        }
        return;
      }
      
      // ⚠️ v2.60: Mapeo de secciones a contenedores para verificar visibilidad
      const seccionesMap = {
        'equipos': '#section-equipos',
        'materiales': '#section-materiales',
        'servicios': '#section-servicios'
      };
      
      // Asegurar que todas las tablas estén reindexadas antes de guardar (solo activas)
      Object.keys(w.SintelCotizacionTables || {}).forEach(key => {
        if (w.SintelCotizacionTables[key]) {
          // ⚠️ v2.60: Solo reindexar tablas de módulos activos
          const containerSelector = seccionesMap[key];
          if (containerSelector) {
            const container = d.querySelector(containerSelector);
            if (container && container.classList.contains('d-none')) {
              // Módulo desactivado: No reindexar
              return;
            }
          }
          
          try {
            reindexarFilas(w.SintelCotizacionTables[key]);
          } catch (error) {
            console.error(`[${MOD}] Error al reindexar tabla ${key}:`, error);
          }
        }
      });
      
      // ⚠️ v2.61: MODO CREACIÓN - NO hay UUID, siempre es POST
      // ⚠️ v2.60: Extraer items ÚNICAMENTE de tablas cuyos contenedores NO tengan d-none
      Object.keys(w.SintelCotizacionTables || {}).forEach(key => {
        if (w.SintelCotizacionTables[key]) {
          // ⚠️ Verificar que el contenedor NO tenga d-none (módulo activo)
          const containerSelector = seccionesMap[key];
          if (containerSelector) {
            const container = d.querySelector(containerSelector);
            if (container && container.classList.contains('d-none')) {
              // ⚠️ Módulo desactivado: No incluir items en payload
              console.log(`[${MOD}] Omitiendo tabla ${key} (módulo desactivado)`);
              return;
            }
          }
          
          try {
            // ⚠️ FASE 3: Antes de enviar, obtener los datos limpios de la tabla
            // ⚠️ CRÍTICO: Capturar explícitamente los campos de las celdas de Tabulator
            const tableData = w.SintelCotizacionTables[key].getData();
            
            // ⚠️ FASE 3: Mapear explícitamente los campos requeridos usando parseFloat()
            const data = tableData.map(row => {
              // ⚠️ FASE 3: Mapear campos explícitamente con parseFloat() para asegurar números válidos
              const item = {
                descripcion: row.descripcion || 'Sin descripción',
                cantidad: parseFloat(row.cantidad) || 0,
                costo_unitario: parseFloat(row.costo_unitario) || 0,
                porcentaje_utilidad: parseFloat(row.porcentaje_utilidad) || 0,
                tipo_item: (() => {
                  // ⚠️ v2.60: Mapear sección a tipo_item según modelo CotizacionItem
                  const tipoItemMap = {
                    'equipos': 'PRODUCTO',
                    'materiales': 'MATERIAL',
                    'servicios': 'SERVICIO'
                  };
                  return tipoItemMap[key] || 'PRODUCTO';
                })(),
                // ⚠️ Campos opcionales
                marca: row.marca || '',
                referencia: row.referencia || '',
                unidad: row.unidad || 'UND',
                orden: row.nro_item || 0
              };
              
              // ⚠️ CRÍTICO: En creación (POST), NO enviar el campo 'cotizacion' en los items
              // El backend lo asignará automáticamente después de crear la cotización
              
              // ⚠️ FASE 3: Logging para verificar que los datos se capturaron correctamente
              console.log(`[${MOD}] Item capturado de tabla ${key}:`, {
                descripcion: item.descripcion,
                cantidad: item.cantidad,
                costo_unitario: item.costo_unitario,
                porcentaje_utilidad: item.porcentaje_utilidad,
                tipo_item: item.tipo_item
              });
              
              return item;
            });
            
            payload.items.push(...data);
            console.log(`[${MOD}] ${data.length} items agregados desde tabla ${key}`);
          } catch (error) {
            console.error(`[${MOD}] Error al obtener datos de tabla ${key}:`, error);
          }
        }
      });
      
      // ⚠️ CORRECCIÓN: Validar y corregir descripciones vacías antes de enviar
      // Si un item no tiene descripción, asignar un valor por defecto
      payload.items = payload.items.map(item => {
        return {
          ...item,
          // ⚠️ CORRECCIÓN: Si la descripción está vacía, poner un valor por defecto
          // o alertar al usuario antes de enviar el payload.
          descripcion: item.descripcion && item.descripcion.trim() !== "" 
            ? item.descripcion.trim() 
            : "Sin descripción técnica"
        };
      });
      
      // ⚠️ v2.61: MODO CREACIÓN - Siempre POST
      const method = 'POST';
      const url = '/api/v1/cotizaciones/';
      
      console.log(`[${MOD}] Guardando cotización: ${method} ${url}`);
      
      const res = await w.http(method, url, payload);
      if (res.ok) {
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
          w.SintelFeedback.success('Cotización guardada exitosamente');
        }
        
        // ⚠️ FASE 3: Cerrar offcanvas si está abierto
        const offcanvasElement = d.getElementById('offcanvas-container');
        if (offcanvasElement) {
          const bsOffcanvas = w.bootstrap?.Offcanvas?.getInstance(offcanvasElement);
          if (bsOffcanvas) {
            bsOffcanvas.hide();
          }
        }
        
        // ⚠️ FASE 3: Redirigir a la lista de cotizaciones en workspace
        // Usar location.hash para navegar al tab de cotizaciones
        setTimeout(() => {
          w.location.hash = '#cotizaciones';
          // ⚠️ Si showTab está disponible, también llamarlo para asegurar que el tab se muestre
          if (w.showTab && typeof w.showTab === 'function') {
            w.showTab('cotizaciones');
          }
          // ⚠️ Refrescar la tabla de cotizaciones si está disponible
          if (w.cotizacionesPage && typeof w.cotizacionesPage.refresh === 'function') {
            w.cotizacionesPage.refresh();
          }
        }, 500); // ⚠️ Pequeño delay para que el usuario vea el mensaje de éxito
      } else {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(res, `[${MOD}]`);
        }
      }
    } catch (error) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ 
          status: 500, 
          data: { detail: error.message || 'Error al guardar la cotización' } 
        }, `[${MOD}]`);
      }
      console.error(`[${MOD}] Error en guardarCotizaciónFinal:`, error);
    }
  }

  // ─── Inicialización principal ────────────────────────────────────────────────
  async function init() {
    console.log(`[${MOD}] ========== INICIANDO MÓDULO DE CREACIÓN ==========`);
    
    const editorDiv = d.getElementById('modal-cotizacion-editor');
    if (!editorDiv) {
      console.error(`[${MOD}] ❌ modal-cotizacion-editor NO encontrado en DOM`);
      return;
    }
    
    // ⚠️ v2.61: Prevenir inicializaciones múltiples con flag
    if (editorDiv.getAttribute('data-init') === 'true') {
      console.log(`[${MOD}] ⚠️ Editor ya inicializado, omitiendo...`);
      return;
    }
    
    console.log(`[${MOD}] ✅ modal-cotizacion-editor encontrado en DOM`);
    
    // ⚠️ v2.61: Verificar dependencias críticas ANTES de marcar como inicializado
    if (!w.CotizacionesHelpers) {
      console.error(`[${MOD}] ❌ CotizacionesHelpers NO está disponible`);
      return;
    }
    console.log(`[${MOD}] ✅ CotizacionesHelpers disponible`);

    if (typeof w.getCotizacionColumns !== 'function') {
      console.error(`[${MOD}] ❌ getCotizacionColumns NO está disponible`);
      return;
    }
    console.log(`[${MOD}] ✅ getCotizacionColumns disponible`);

    if (!w.TabulatorFactory) {
      console.error(`[${MOD}] ❌ TabulatorFactory NO está disponible`);
      return;
    }
    console.log(`[${MOD}] ✅ TabulatorFactory disponible`);
    
    // ⚠️ v2.61: Verificar w.http ANTES de marcar como inicializado
    if (!w.http || typeof w.http !== 'function') {
      console.error(`[${MOD}] ❌ window.http NO está disponible`);
      return;
    }
    console.log(`[${MOD}] ✅ window.http disponible`);
    
    // ⚠️ v2.61: Marcar como inicializado SOLO después de verificar todas las dependencias
    editorDiv.setAttribute('data-init', 'true');

    try {
      // ⚠️ v2.60: LIMPIEZA GLOBAL - Destruir instancias zombis de Tabulator antes de reiniciar
      if (w.SintelCotizacionTables) {
        Object.keys(w.SintelCotizacionTables).forEach(key => {
          const tb = w.SintelCotizacionTables[key];
          if (tb && typeof tb.destroy === 'function') {
            try {
              console.log(`[${MOD}] Limpiando tabla zombie: ${key}`);
              tb.destroy();
            } catch (e) {
              console.warn(`[${MOD}] Error al destruir tabla zombie ${key}:`, e);
            }
          }
        });
      }
      // ⚠️ v2.60: Reiniciar el registro global
      w.SintelCotizacionTables = {};
      console.log(`[${MOD}] Objeto global SintelCotizacionTables reiniciado`);

      // ⚠️ v2.61: Verificar que NO tenga UUID (es modo creación)
      const uuid = editorDiv.getAttribute('data-cotizacion-uuid');
      const isDraft = !uuid || uuid === '' || uuid === 'None';
      
      if (!isDraft) {
        console.warn(`[${MOD}] Este módulo es solo para CREAR. UUID detectado: ${uuid}`);
        return; // No inicializar si hay UUID (es modo edición)
      }

      console.log(`[${MOD}] Modo: Creación (Borrador)`);

      // ⚠️ v2.60: Configurar fechas por defecto ANTES de cargar catálogos
      // Esto asegura que las fechas estén disponibles desde el inicio
      configurarFechasPorDefecto();

      // ⚠️ v2.60: Cargar datos del emisor en paralelo con los catálogos
      // Cargar catálogos directamente de la API con manejo de errores
      const selCliente = d.getElementById('editor-select-cliente');
      const selPerfil = d.getElementById('editor-select-perfil');
      
      try {
        await Promise.all([
          w.CotizacionesHelpers ? w.CotizacionesHelpers.cargarClientesEnSelect(selCliente) : Promise.resolve(),
          w.CotizacionesHelpers ? w.CotizacionesHelpers.cargarPerfilesEnSelect(selPerfil) : Promise.resolve(),
          cargarDatosEmisor() // ⚠️ v2.60: Cargar datos del emisor en paralelo
        ]);
        console.log(`[${MOD}] ✅ Catálogos y datos del emisor cargados correctamente`);
      } catch (error) {
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ 
            status: 500, 
            data: { detail: error.message || 'Error al cargar catálogos' } 
          }, `[${MOD}]`);
        }
        console.error(`[${MOD}] Error al cargar catálogos:`, error);
      }

      // ⚠️ v2.60: Listener para actualizar previsualización en tiempo real (Folio y Fecha de Vencimiento)
      if (selPerfil) {
        // Clonar elemento para prevenir listeners duplicados en recargas HTMX
        const newSelPerfil = selPerfil.cloneNode(true);
        selPerfil.parentNode.replaceChild(newSelPerfil, selPerfil);
        
        // Listener para cambios en el select
        newSelPerfil.addEventListener('change', actualizarPrevisualizacionPlantilla);
        
        // Actualizar previsualización inicial si hay un perfil seleccionado
        setTimeout(() => {
          if (newSelPerfil.value) {
            actualizarPrevisualizacionPlantilla();
          }
        }, 100);
      }
      
      // ⚠️ v2.60: Listeners para Panel de Configuración Dinámica (User-Driven)
      configurarListenersDinamicos();
      
      // ⚠️ QA v2.60: Prevenir listeners duplicados en recargas HTMX
      const btnGuardar = d.getElementById('btn-guardar-maestro');
      if (btnGuardar) {
        // Clonar elemento para remover listeners previos (prevención de fugas de memoria)
        const newBtnGuardar = btnGuardar.cloneNode(true);
        btnGuardar.parentNode.replaceChild(newBtnGuardar, btnGuardar);
        newBtnGuardar.addEventListener('click', guardarCotizaciónFinal);
      }
      
      // ⚠️ v2.61: CRÍTICO - Inicializar tablas Tabulator para secciones visibles por defecto
      // Esto asegura que el formulario sea funcional desde el inicio
      console.log(`[${MOD}] Inicializando tablas Tabulator para secciones visibles...`);
      initVisibleGrids();
      console.log(`[${MOD}] ✅ Tablas Tabulator inicializadas`);
      
      console.log(`[${MOD}] ========== MÓDULO DE CREACIÓN INICIALIZADO CORRECTAMENTE ==========`);
    } catch (error) {
      // ⚠️ v2.61: Resetear flag si hay error para permitir reintento
      if (editorDiv) {
        editorDiv.removeAttribute('data-init');
      }
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ 
          status: 500, 
          data: { detail: error.message || 'Error al inicializar el editor' } 
        }, `[${MOD}]`);
      }
      console.error(`[${MOD}] Error en init:`, error);
    }
  }

  // ⚠️ Exponer funciones globalmente para acceso desde cotizacion_columns.js
  w.CotizacionCrearModule = { 
    init,
    actualizarPanelTotales,
    recalcularTotalesGlobales,
    reindexarFilas,
    // ⚠️ v2.60: Exponer objeto global SintelCotizacionTables para debugging y acceso directo
    getTables: () => w.SintelCotizacionTables || {},
    // ⚠️ v2.60: Función helper para verificar estado de SintelCotizacionTables
    debugTables: () => {
      console.log('[cotizacion-crear] Estado de SintelCotizacionTables:', {
        keys: Object.keys(w.SintelCotizacionTables || {}),
        count: Object.keys(w.SintelCotizacionTables || {}).length,
        tables: w.SintelCotizacionTables
      });
      return w.SintelCotizacionTables || {};
    }
  };
  
  // ⚠️ v2.61: Listener HTMX con safeguard mejorado para prevenir ejecuciones fantasma y conflictos
  d.body.addEventListener('htmx:afterSwap', (e) => {
    // ⚠️ SAFEGUARD 1: Solo inicializar si el target es el contenedor del editor
    if (!e.detail || !e.detail.target || e.detail.target.id !== 'offcanvas-container') {
      return; // No es nuestro contenedor, ignorar silenciosamente
    }

    // ⚠️ SAFEGUARD 2: PRIORIDAD - Verificar PRIMERO dentro del target si existe el editor de EDICIÓN
    // Buscar dentro del contenido recién cargado por HTMX (más confiable que buscar en todo el DOM)
    const editorEditarDiv = e.detail.target.querySelector('#modal-cotizacion-editar');
    if (editorEditarDiv) {
      console.log('[cotizacion-crear] HTMX swap detectado pero editor de EDICIÓN presente en el target. Abortando.');
      return;
    }

    // ⚠️ SAFEGUARD 3: Verificar que el editor de CREACIÓN existe dentro del target
    const editorDiv = e.detail.target.querySelector('#modal-cotizacion-editor');
    if (!editorDiv) {
      // No mostrar warning si es un swap de edición (ya se abortó arriba)
      return;
    }

    // ⚠️ SAFEGUARD 4: Verificar que NO tenga UUID (es modo creación)
    const uuid = editorDiv.getAttribute('data-cotizacion-uuid');
    const isDraft = !uuid || uuid === '' || uuid === 'None';
    
    if (!isDraft) {
      console.log('[cotizacion-crear] HTMX swap detectado pero tiene UUID (modo edición). Abortando.');
      return;
    }

    // ⚠️ SAFEGUARD 5: Verificar el atributo data-mode para mayor seguridad
    const dataMode = editorDiv.getAttribute('data-mode');
    if (dataMode && dataMode !== 'crear') {
      console.log(`[cotizacion-crear] HTMX swap detectado pero data-mode="${dataMode}" (no es crear). Abortando.`);
      return;
    }

    // ⚠️ v2.61: Verificar si ya se inicializó para evitar múltiples inicializaciones
    if (editorDiv.getAttribute('data-init') === 'true') {
      console.log('[cotizacion-crear] Editor ya inicializado, omitiendo...');
      return;
    }

    // ⚠️ SAFEGUARD 6: Verificar dependencias críticas antes de inicializar
    if (!w.CotizacionesHelpers) {
      console.error('[cotizacion-crear] CotizacionesHelpers no está disponible. Esperando...');
      // Reintentar después de un breve delay
      setTimeout(() => {
        if (w.CotizacionesHelpers && d.getElementById('modal-cotizacion-editor')) {
          console.log('[cotizacion-crear] Dependencias disponibles, reinicializando...');
          init();
        }
      }, 500);
      return;
    }

    if (typeof w.getCotizacionColumns !== 'function') {
      console.error('[cotizacion-crear] getCotizacionColumns no está disponible. Esperando...');
      setTimeout(() => {
        if (typeof w.getCotizacionColumns === 'function' && d.getElementById('modal-cotizacion-editor')) {
          console.log('[cotizacion-crear] Dependencias disponibles, reinicializando...');
          init();
        }
      }, 500);
      return;
    }

    console.log('[cotizacion-crear] HTMX swap detectado, preparando inicialización...');
    
    // ⚠️ v2.60: Limpiar tablas existentes antes de reinicializar (ya se hace en init(), pero por seguridad)
    if (w.SintelCotizacionTables) {
      Object.keys(w.SintelCotizacionTables).forEach(key => {
        try {
          if (w.SintelCotizacionTables[key] && typeof w.SintelCotizacionTables[key].destroy === 'function') {
            w.SintelCotizacionTables[key].destroy();
          }
        } catch (error) {
          console.warn(`[cotizacion-crear] Error al destruir tabla ${key}:`, error);
        }
      });
    }
    // El reset se hace en init(), pero por seguridad también aquí
    w.SintelCotizacionTables = {};
    
    // ⚠️ v2.61: Inicializar después de un breve delay para asegurar que el DOM esté listo
    // El listener shown.bs.offcanvas también intentará inicializar como fallback
    setTimeout(() => {
      const editorDivCheck = d.getElementById('modal-cotizacion-editor');
      if (editorDivCheck && !editorDivCheck.getAttribute('data-init')) {
        // Verificar una vez más que NO tenga UUID y que data-mode sea "crear"
        const uuid = editorDivCheck.getAttribute('data-cotizacion-uuid');
        const dataMode = editorDivCheck.getAttribute('data-mode');
        const isDraft = !uuid || uuid === '' || uuid === 'None';
        
        if (isDraft && (!dataMode || dataMode === 'crear')) {
          console.log('[cotizacion-crear] Inicializando desde htmx:afterSwap...');
          init();
        }
      }
    }, 100);
  });

  // ⚠️ v2.61: Fallback PRINCIPAL - Inicializar cuando el offcanvas se muestra completamente
  // Este es el método más confiable porque se ejecuta cuando Bootstrap confirma que el offcanvas está visible
  d.body.addEventListener('shown.bs.offcanvas', function(e) {
    if (e.target && e.target.id === 'offcanvas-container') {
      const editorDiv = d.getElementById('modal-cotizacion-editor');
      if (!editorDiv) {
        return; // No es el editor de creación
      }
      
      // Verificar que no se haya inicializado ya
      if (editorDiv.getAttribute('data-init') === 'true') {
        console.log(`[${MOD}] shown.bs.offcanvas: Editor ya inicializado, omitiendo...`);
        return;
      }
      
      const uuid = editorDiv.getAttribute('data-cotizacion-uuid');
      const dataMode = editorDiv.getAttribute('data-mode');
      const isDraft = !uuid || uuid === '' || uuid === 'None';
      
      if (isDraft && (!dataMode || dataMode === 'crear')) {
        console.log(`[${MOD}] shown.bs.offcanvas → Inicializando módulo de creación...`);
        // Esperar un breve momento para asegurar que todos los scripts estén cargados
        setTimeout(() => {
          const editorDivCheck = d.getElementById('modal-cotizacion-editor');
          if (editorDivCheck && !editorDivCheck.getAttribute('data-init')) {
            // Verificar dependencias una vez más antes de inicializar
            if (w.CotizacionesHelpers && typeof w.getCotizacionColumns === 'function' && w.TabulatorFactory && w.http) {
              console.log(`[${MOD}] Todas las dependencias disponibles, ejecutando init()...`);
              init();
            } else {
              console.warn(`[${MOD}] Dependencias no disponibles en shown.bs.offcanvas, reintentando...`);
              // Reintentar después de un delay adicional
              setTimeout(() => {
                const editorDivRetry = d.getElementById('modal-cotizacion-editor');
                if (editorDivRetry && !editorDivRetry.getAttribute('data-init')) {
                  if (w.CotizacionesHelpers && typeof w.getCotizacionColumns === 'function' && w.TabulatorFactory && w.http) {
                    console.log(`[${MOD}] Dependencias disponibles en reintento, ejecutando init()...`);
                    init();
                  } else {
                    console.error(`[${MOD}] ❌ Dependencias aún no disponibles después del reintento`);
                  }
                }
              }, 300);
            }
          }
        }, 150);
      }
    }
  });

  // ⚠️ v2.61: Limpiar estado cuando se cierra el offcanvas
  d.body.addEventListener('hidden.bs.offcanvas', function(e) {
    if (e.target && e.target.id === 'offcanvas-container') {
      const editorDiv = d.getElementById('modal-cotizacion-editor');
      if (editorDiv && editorDiv.getAttribute('data-mode') === 'crear') {
        console.log(`[${MOD}] Offcanvas cerrado, limpiando estado...`);
        resetState();
      }
    }
  });

})(window, document);
