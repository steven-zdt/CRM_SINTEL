# 📊 Implementación de AIU (Administración, Imprevistos, Utilidad) - Cotizaciones v2.40

**Versión:** 2.40  
**Fecha:** 2026-02-17  
**Arquitectura:** SINTEL v2.40 (API-First, Service Layer, Multi-tenant)

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura de AIU](#arquitectura-de-aiu)
3. [Modelo de Datos](#modelo-de-datos)
4. [Service Layer](#service-layer)
5. [Capa API (DRF)](#capa-api-drf)
6. [Interfaz de Usuario](#interfaz-de-usuario)
7. [Flujos de Trabajo](#flujos-de-trabajo)
8. [Validaciones e Inmutabilidad](#validaciones-e-inmutabilidad)
9. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 🎯 Resumen Ejecutivo

**AIU (Administración, Imprevistos, Utilidad)** es una característica habilitable por cotización individual que permite aplicar un cálculo especial de IVA según la normativa colombiana, donde el IVA se aplica únicamente sobre el componente de **Utilidad**.

### Características Principales

- ✅ **Característica por Cotización**: AIU se configura individualmente para cada cotización, no es una configuración global
- ✅ **Modal de Configuración**: Interfaz dedicada para activar/desactivar y configurar porcentajes AIU
- ✅ **Validación de Modelo**: Solo aplicable para cotizaciones de tipo `SERVICIO` o `MATERIAL`
- ✅ **Inmutabilidad**: No se puede modificar el modo AIU en cotizaciones `ACEPTADA`
- ✅ **Cálculo Automático**: El sistema calcula automáticamente los valores de A, I, U y el IVA sobre Utilidad
- ✅ **Integración con Editor**: Configuración accesible desde el Editor Estilo Excel

### Reglas de Negocio

1. **Aplicabilidad**: AIU solo es válido para cotizaciones de tipo `SERVICIO` o `MATERIAL`
2. **Cálculo de IVA**: En modo AIU, el IVA (19%) se aplica únicamente sobre el valor de Utilidad
3. **Inmutabilidad**: Una vez guardada una cotización, el modo AIU no puede modificarse si está en estado `ACEPTADA`
4. **Valores por Defecto**: Los porcentajes AIU pueden tomarse de la configuración global, pero son personalizables por cotización

---

## 🏗️ Arquitectura de AIU

### Principio de Diseño

**AIU es una característica de la cotización, no de la configuración global.**

A diferencia de la configuración global que provee valores sugeridos, AIU se activa y configura directamente en cada cotización individual, permitiendo flexibilidad y personalización por documento.

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    Cotizacion Model                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ es_aiu (Boolean)                                     │  │
│  │ aiu_admin_porcentaje (Decimal)                        │  │
│  │ aiu_imprevistos_porcentaje (Decimal)                 │  │
│  │ aiu_utilidad_porcentaje (Decimal)                    │  │
│  │ valor_administracion (Decimal)                        │  │
│  │ valor_imprevistos (Decimal)                           │  │
│  │ valor_utilidad (Decimal)                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ actualizar_totales()                                  │  │
│  │ - Lee es_aiu de la instancia                         │  │
│  │ - Calcula A, I, U si es_aiu = True                  │  │
│  │ - Aplica IVA solo sobre Utilidad                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Service Layer (services.py)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ recalcular_totales_cotizacion()                      │  │
│  │ - Usa actualizar_totales() del modelo                │  │
│  │ - Respeta inmutabilidad                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend (cotizacion_editor.js)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ abrirModalConfigurarAIU()                            │  │
│  │ aplicarConfiguracionAIU()                             │  │
│  │ actualizarEstadoBotonAIU()                            │  │
│  │ cargarDatosAIU()                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ calcularTotales()                                     │  │
│  │ - Calcula A, I, U si esAiuActivo = true              │  │
│  │ - Aplica IVA solo sobre Utilidad                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Modelo de Datos

### Campos en `Cotizacion`

**Ubicación**: `apps/tenant/cotizaciones/models.py`

```python
class Cotizacion(models.Model):
    # ... otros campos ...
    
    # ⚠️ v2.40: Modo AIU (Administración, Imprevistos, Utilidad) - Colombia
    es_aiu = models.BooleanField(
        _('Modo AIU'),
        default=False,
        help_text=_('Si está activo, aplica cálculo AIU (IVA solo sobre Utilidad). Solo válido para SERVICIO y MATERIAL.')
    )
    
    # Porcentajes AIU (se pueden personalizar por cotización)
    aiu_admin_porcentaje = models.DecimalField(
        _('AIU - Administración (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text=_('Porcentaje de administración para cálculo AIU')
    )
    
    aiu_imprevistos_porcentaje = models.DecimalField(
        _('AIU - Imprevistos (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text=_('Porcentaje de imprevistos para cálculo AIU')
    )
    
    aiu_utilidad_porcentaje = models.DecimalField(
        _('AIU - Utilidad (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text=_('Porcentaje de utilidad para cálculo AIU. El IVA solo se aplica sobre este valor.')
    )
    
    # Valores calculados AIU
    valor_administracion = models.DecimalField(
        _('Valor Administración'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Valor calculado de administración (solo en modo AIU)')
    )
    
    valor_imprevistos = models.DecimalField(
        _('Valor Imprevistos'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Valor calculado de imprevistos (solo en modo AIU)')
    )
    
    valor_utilidad = models.DecimalField(
        _('Valor Utilidad'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Valor calculado de utilidad (solo en modo AIU). Base para cálculo de IVA.')
    )
```

### Método `actualizar_totales()`

El método `actualizar_totales()` del modelo `Cotizacion` implementa la lógica de cálculo AIU:

```python
def actualizar_totales(self):
    """
    Recalcula los totales de la cotización.
    
    ⚠️ v2.40: Lee es_aiu directamente de la instancia, no de la configuración global.
    """
    items = self.items.all()
    
    if self.es_aiu:
        # ⚠️ Modo AIU: Calcular subtotal como suma de (cantidad * costo_unitario) sin utilidad
        self.subtotal = sum(item.cantidad * item.costo_unitario for item in items)
        
        # Calcular valores AIU sobre el subtotal base
        self.valor_administracion = self.subtotal * (self.aiu_admin_porcentaje / Decimal('100.00'))
        self.valor_imprevistos = self.subtotal * (self.aiu_imprevistos_porcentaje / Decimal('100.00'))
        self.valor_utilidad = self.subtotal * (self.aiu_utilidad_porcentaje / Decimal('100.00'))
        
        # IVA solo sobre la utilidad
        self.iva_valor = self.valor_utilidad * (self.iva_porcentaje / Decimal('100.00'))
        
        # Total Neto = Subtotal + A + I + U + IVA
        self.total_neto = self.subtotal + self.valor_administracion + self.valor_imprevistos + self.valor_utilidad + self.iva_valor
    else:
        # Modo Estándar: Cálculo tradicional
        self.subtotal = sum(item.subtotal_linea for item in items)
        self.iva_valor = self.subtotal * (self.iva_porcentaje / Decimal('100.00'))
        self.total_neto = self.subtotal + self.iva_valor
        
        # En modo estándar, los valores AIU son 0
        self.valor_administracion = Decimal('0.00')
        self.valor_imprevistos = Decimal('0.00')
        self.valor_utilidad = Decimal('0.00')
    
    # Actualizar en BD usando update para evitar disparar clean de inmutabilidad
    Cotizacion.objects.filter(pk=self.pk).update(
        subtotal=self.subtotal,
        valor_administracion=self.valor_administracion,
        valor_imprevistos=self.valor_imprevistos,
        valor_utilidad=self.valor_utilidad,
        iva_valor=self.iva_valor,
        total_neto=self.total_neto
    )
```

### Validaciones en `clean()`

```python
def clean(self):
    if self.pk:
        original = Cotizacion.objects.get(pk=self.pk)
        # Validar inmutabilidad de es_aiu una vez guardada
        if original.es_aiu != self.es_aiu:
            raise ValidationError(_("El modo AIU no puede modificarse una vez guardada la cotización."))
    
    # Validar que AIU solo aplica para SERVICIO y MATERIAL
    if self.es_aiu and self.modelo_tipo not in [self.ModeloTipo.SERVICIO, self.ModeloTipo.MATERIAL]:
        raise ValidationError(_("El modo AIU solo es válido para cotizaciones de tipo SERVICIO o MATERIAL."))
```

---

## 🔧 Service Layer

### Función `recalcular_totales_cotizacion()`

**Ubicación**: `apps/tenant/cotizaciones/services.py`

```python
def recalcular_totales_cotizacion(cotizacion_id: int) -> Dict[str, Any]:
    """
    Recalcula los totales de una cotización basándose en sus ítems.
    
    ⚠️ v2.40: 
    - Solo recalcula si la cotización no está aceptada (no inmutable).
    - Usa el método actualizar_totales() del modelo que maneja AIU automáticamente.
    - Lee es_aiu directamente de la instancia de Cotización, no de la configuración global.
    
    Args:
        cotizacion_id: ID de la cotización
        
    Returns:
        Dict con los nuevos totales calculados
    """
    try:
        cotizacion = Cotizacion.objects.select_related('empresa').get(pk=cotizacion_id)
        
        # Validar que no esté aceptada
        if cotizacion.es_inmutable:
            raise ValidationError("No se puede recalcular una cotización aceptada (inmutable).")
        
        # ⚠️ v2.40: Usar el método actualizar_totales() del modelo
        # Este método lee es_aiu directamente de la instancia y calcula correctamente
        cotizacion.actualizar_totales()
        
        # Refrescar desde la BD para obtener los valores actualizados
        cotizacion.refresh_from_db()
        
        # Retornar totales calculados
        return {
            'subtotal': float(cotizacion.subtotal),
            'iva_valor': float(cotizacion.iva_valor),
            'total_neto': float(cotizacion.total_neto),
            # Valores AIU (si aplica)
            'valor_administracion': float(cotizacion.valor_administracion) if cotizacion.es_aiu else 0.00,
            'valor_imprevistos': float(cotizacion.valor_imprevistos) if cotizacion.es_aiu else 0.00,
            'valor_utilidad': float(cotizacion.valor_utilidad) if cotizacion.es_aiu else 0.00,
            'es_aiu': cotizacion.es_aiu
        }
        
    except Cotizacion.DoesNotExist:
        raise ValidationError("Cotización no encontrada.")
```

---

## 🌐 Capa API (DRF)

### Endpoint `bulk-save`

**Ubicación**: `apps/tenant/cotizaciones/api/viewsets.py`

El endpoint `bulk-save` acepta los parámetros AIU en el payload:

```python
@action(detail=False, methods=['post'], url_path='bulk-save')
def bulk_save(self, request):
    """
    Guarda una cotización completa desde editor estilo Excel.
    
    POST /api/v1/cotizaciones/bulk-save/
    
    Body:
        {
            "cliente_id": 1,
            "modelo_tipo": "SERVICIO",
            "es_aiu": true,
            "aiu_admin_porcentaje": "10.00",
            "aiu_imprevistos_porcentaje": "5.00",
            "aiu_utilidad_porcentaje": "10.00",
            "iva_porcentaje": "19.00",
            "items": [...]
        }
    """
    # Obtener parámetros AIU
    es_aiu = request.data.get('es_aiu', False)
    aiu_admin_porcentaje = request.data.get('aiu_admin_porcentaje')
    aiu_imprevistos_porcentaje = request.data.get('aiu_imprevistos_porcentaje')
    aiu_utilidad_porcentaje = request.data.get('aiu_utilidad_porcentaje')
    
    # Procesar guardado masivo
    resultado = procesar_guardado_masivo(
        empresa_id=empresa.id,
        cliente_id=cliente_id,
        data_items=items,
        modelo_tipo=modelo_tipo,
        es_aiu=es_aiu,
        aiu_admin_porcentaje=aiu_admin_porcentaje,
        aiu_imprevistos_porcentaje=aiu_imprevistos_porcentaje,
        aiu_utilidad_porcentaje=aiu_utilidad_porcentaje,
        # ... otros parámetros ...
    )
```

### Serializers

Los serializers incluyen los campos AIU:

```python
class CotizacionDetailSerializer(serializers.ModelSerializer):
    es_aiu = serializers.BooleanField(read_only=False)
    aiu_admin_porcentaje = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    aiu_imprevistos_porcentaje = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    aiu_utilidad_porcentaje = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    valor_administracion = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    valor_imprevistos = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    valor_utilidad = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cotizacion
        fields = [
            # ... otros campos ...
            'es_aiu',
            'aiu_admin_porcentaje', 'aiu_imprevistos_porcentaje', 'aiu_utilidad_porcentaje',
            'valor_administracion', 'valor_imprevistos', 'valor_utilidad',
        ]
```

---

## 🎨 Interfaz de Usuario

### Botón "Configurar AIU"

**Ubicación**: `apps/tenant/core/templates/tenant/core/partials/cotizaciones/modal_editor.html`

El botón se encuentra en el header del panel de totales:

```html
<div class="card-header bg-light d-flex justify-content-between align-items-center">
  <h6 class="mb-0 fw-bold"><i class="bi bi-calculator me-2"></i>Resumen Económico</h6>
  <button type="button" class="btn btn-sm btn-outline-info" id="btn-configurar-aiu-editor" title="Configurar AIU (Administración, Imprevistos, Utilidad)">
    <i class="bi bi-sliders me-1"></i><span id="btn-aiu-texto">Configurar AIU</span>
  </button>
</div>
```

### Modal de Configuración AIU

**Ubicación**: `apps/tenant/core/templates/tenant/core/partials/cotizaciones/modal_editor.html`

```html
<!-- Modal: Configurar AIU por Cotización -->
<div class="modal fade" id="modal-configurar-aiu" tabindex="-1">
  <div class="modal-dialog modal-md">
    <div class="modal-content">
      <div class="modal-header bg-info text-white">
        <h5 class="modal-title">
          <i class="bi bi-sliders me-2"></i>Configurar AIU
        </h5>
      </div>
      <div class="modal-body">
        <div class="alert alert-warning mb-3">
          <strong>Importante:</strong> El modo AIU solo es válido para cotizaciones de tipo 
          <strong>SERVICIO</strong> o <strong>MATERIAL</strong>.
        </div>
        
        <form id="form-configurar-aiu">
          <!-- Toggle Activar/Desactivar AIU -->
          <div class="form-check form-switch mb-3">
            <input class="form-check-input" type="checkbox" id="aiu-es-activo" name="es_aiu">
            <label class="form-check-label fw-bold" for="aiu-es-activo">
              Activar Modo AIU para esta cotización
            </label>
          </div>
          
          <!-- Campos de Porcentajes AIU -->
          <div id="panel-aiu-campos" class="d-none">
            <div class="row">
              <div class="col-md-12 mb-3">
                <label for="aiu-admin-porcentaje" class="form-label">% Administración</label>
                <input type="number" class="form-control" id="aiu-admin-porcentaje" 
                       name="aiu_admin_porcentaje" min="0" max="100" step="0.01" value="10.00">
              </div>
              <div class="col-md-12 mb-3">
                <label for="aiu-imprevistos-porcentaje" class="form-label">% Imprevistos</label>
                <input type="number" class="form-control" id="aiu-imprevistos-porcentaje" 
                       name="aiu_imprevistos_porcentaje" min="0" max="100" step="0.01" value="5.00">
              </div>
              <div class="col-md-12 mb-3">
                <label for="aiu-utilidad-porcentaje" class="form-label">% Utilidad</label>
                <input type="number" class="form-control" id="aiu-utilidad-porcentaje" 
                       name="aiu_utilidad_porcentaje" min="0" max="100" step="0.01" value="10.00">
                <small class="form-text text-muted fw-bold text-danger">
                  El IVA se aplica únicamente sobre este valor
                </small>
              </div>
            </div>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button type="button" class="btn btn-primary" id="btn-aiu-guardar">
          <i class="bi bi-check-lg me-1"></i>Aplicar Configuración
        </button>
      </div>
    </div>
  </div>
</div>
```

### Funciones JavaScript

**Ubicación**: `apps/tenant/core/static/core/js/cotizaciones/cotizacion_editor.js`

#### `abrirModalConfigurarAIU()`

Abre el modal de configuración AIU con validaciones:

```javascript
function abrirModalConfigurarAIU() {
  const modeloTipoSelect = d.querySelector('#cotizacion-modelo-tipo');
  const modeloTipo = modeloTipoSelect?.value || 'MIXTO';
  
  // Validar que el modelo sea SERVICIO o MATERIAL
  if (modeloTipo !== 'SERVICIO' && modeloTipo !== 'MATERIAL') {
    if (w.notyf) {
      w.notyf.error('El modo AIU solo es válido para cotizaciones de tipo SERVICIO o MATERIAL');
    }
    return;
  }
  
  // Validar inmutabilidad: si la cotización está ACEPTADA, no permitir cambios
  if (cotizacionEstadoActual === 'ACEPTADA') {
    if (w.notyf) {
      w.notyf.error('No se puede modificar el modo AIU de una cotización aceptada (inmutable)');
    }
    return;
  }
  
  // Cargar valores actuales en el modal
  // ... código de carga de valores ...
  
  // Abrir modal
  const modal = bootstrap.Modal.getOrCreateInstance(modalAiu);
  modal.show();
}
```

#### `aplicarConfiguracionAIU()`

Aplica la configuración AIU desde el modal:

```javascript
function aplicarConfiguracionAIU() {
  const esActivoCheck = d.querySelector('#aiu-es-activo');
  const adminInput = d.querySelector('#aiu-admin-porcentaje');
  const imprevistosInput = d.querySelector('#aiu-imprevistos-porcentaje');
  const utilidadInput = d.querySelector('#aiu-utilidad-porcentaje');
  
  const nuevoEstado = esActivoCheck.checked;
  esAiuActivo = nuevoEstado;
  
  // Actualizar valores en el editor principal
  if (nuevoEstado) {
    const adminEditor = d.querySelector('#cotizacion-aiu-admin');
    const imprevistosEditor = d.querySelector('#cotizacion-aiu-imprevistos');
    const utilidadEditor = d.querySelector('#cotizacion-aiu-utilidad');
    
    if (adminEditor && adminInput) adminEditor.value = adminInput.value;
    if (imprevistosEditor && imprevistosInput) imprevistosEditor.value = imprevistosInput.value;
    if (utilidadEditor && utilidadInput) utilidadEditor.value = utilidadInput.value;
    
    // Mostrar panel de porcentajes AIU en el editor
    const panelAiuPorcentajes = d.querySelector('#panel-aiu-porcentajes');
    if (panelAiuPorcentajes) {
      panelAiuPorcentajes.classList.remove('d-none');
    }
    
    // Actualizar texto del botón
    const btnAiuTexto = d.querySelector('#btn-aiu-texto');
    if (btnAiuTexto) {
      btnAiuTexto.textContent = 'AIU Activo';
    }
  } else {
    // Ocultar panel y resetear texto del botón
    // ...
  }
  
  // Actualizar totales
  actualizarPanelTotales();
  
  // Cerrar modal
  // ...
}
```

#### `calcularTotales()`

Calcula los totales considerando el modo AIU:

```javascript
function calcularTotales() {
  let subtotal = 0;
  
  // Sumar totales de las 3 secciones
  Object.keys(tables).forEach(seccion => {
    const table = tables[seccion];
    if (table) {
      const rows = table.getRows();
      rows.forEach(row => {
        const data = row.getData();
        if (esAiuActivo) {
          // Modo AIU: subtotal = cantidad * costo_unitario (sin utilidad)
          const cantidad = parseFloat(data.cantidad) || 0;
          const costoUnitario = parseFloat(data.costo_unitario) || 0;
          subtotal += cantidad * costoUnitario;
        } else {
          // Modo estándar: subtotal = subtotal_linea (con utilidad)
          const subtotalLinea = parseFloat(data.subtotal_linea) || 0;
          subtotal += subtotalLinea;
        }
      });
    }
  });
  
  const ivaPorcentaje = parseFloat(d.querySelector('#cotizacion-iva-porcentaje')?.value || '19.00');
  
  if (esAiuActivo) {
    // Modo AIU: Calcular A, I, U y IVA solo sobre Utilidad
    const aiuAdminPorcentaje = parseFloat(d.querySelector('#cotizacion-aiu-admin')?.value || '10.00');
    const aiuImprevistosPorcentaje = parseFloat(d.querySelector('#cotizacion-aiu-imprevistos')?.value || '5.00');
    const aiuUtilidadPorcentaje = parseFloat(d.querySelector('#cotizacion-aiu-utilidad')?.value || '10.00');
    
    const valorAdministracion = subtotal * (aiuAdminPorcentaje / 100);
    const valorImprevistos = subtotal * (aiuImprevistosPorcentaje / 100);
    const valorUtilidad = subtotal * (aiuUtilidadPorcentaje / 100);
    const iva = valorUtilidad * (ivaPorcentaje / 100); // IVA solo sobre utilidad
    const total = subtotal + valorAdministracion + valorImprevistos + valorUtilidad + iva;
    
    return {
      subtotal: subtotal,
      valorAdministracion: valorAdministracion,
      valorImprevistos: valorImprevistos,
      valorUtilidad: valorUtilidad,
      iva: iva,
      total: total
    };
  } else {
    // Modo estándar: IVA sobre subtotal completo
    const iva = subtotal * (ivaPorcentaje / 100);
    const total = subtotal + iva;
    
    return {
      subtotal: subtotal,
      iva: iva,
      total: total
    };
  }
}
```

---

## 🔄 Flujos de Trabajo

### Flujo 1: Activar AIU en Nueva Cotización

```
1. Usuario abre Editor Estilo Excel
2. Selecciona modelo_tipo = "SERVICIO" o "MATERIAL"
3. Hace clic en "Configurar AIU"
4. Modal se abre con validación de modelo
5. Usuario activa toggle "Activar Modo AIU"
6. Se muestran campos de porcentajes AIU
7. Usuario ajusta porcentajes (opcional)
8. Hace clic en "Aplicar Configuración"
9. Modal se cierra
10. Panel de porcentajes AIU se muestra en el editor
11. Totales se recalculan automáticamente
12. Al guardar, los valores AIU se envían al backend
```

### Flujo 2: Editar Cotización con AIU Activo

```
1. Usuario abre cotización existente en el editor
2. Sistema carga datos AIU (es_aiu, porcentajes, valores calculados)
3. Si cotizacion.estado = "ACEPTADA":
   - Botón "Configurar AIU" se deshabilita
   - No se permite modificar AIU
4. Si cotizacion.estado != "ACEPTADA":
   - Botón "Configurar AIU" está habilitado
   - Usuario puede modificar configuración AIU
5. Al modificar porcentajes, totales se recalculan automáticamente
```

### Flujo 3: Validación de Modelo

```
1. Usuario intenta abrir modal AIU
2. Sistema valida modelo_tipo actual
3. Si modelo_tipo != "SERVICIO" y != "MATERIAL":
   - Muestra error: "El modo AIU solo es válido para cotizaciones de tipo SERVICIO o MATERIAL"
   - No abre el modal
4. Si modelo_tipo es válido:
   - Abre el modal normalmente
```

---

## ✅ Validaciones e Inmutabilidad

### Validaciones en el Modelo

1. **Validación de Modelo**: AIU solo aplica para `SERVICIO` o `MATERIAL`
   ```python
   if self.es_aiu and self.modelo_tipo not in [self.ModeloTipo.SERVICIO, self.ModeloTipo.MATERIAL]:
       raise ValidationError(_("El modo AIU solo es válido para cotizaciones de tipo SERVICIO o MATERIAL."))
   ```

2. **Inmutabilidad de `es_aiu`**: No se puede cambiar una vez guardada
   ```python
   if original.es_aiu != self.es_aiu:
       raise ValidationError(_("El modo AIU no puede modificarse una vez guardada la cotización."))
   ```

3. **Inmutabilidad por Estado**: Cotizaciones `ACEPTADA` son inmutables
   ```python
   if original.estado == self.Estado.ACEPTADA:
       raise ValidationError(_("Cotización inmutable por estado ACEPTADA."))
   ```

### Validaciones en el Frontend

1. **Validación de Modelo antes de Abrir Modal**
   ```javascript
   if (modeloTipo !== 'SERVICIO' && modeloTipo !== 'MATERIAL') {
       w.notyf.error('El modo AIU solo es válido para cotizaciones de tipo SERVICIO o MATERIAL');
       return;
   }
   ```

2. **Validación de Inmutabilidad**
   ```javascript
   if (cotizacionEstadoActual === 'ACEPTADA') {
       w.notyf.error('No se puede modificar el modo AIU de una cotización aceptada (inmutable)');
       return;
   }
   ```

3. **Deshabilitar Botón si Inmutable**
   ```javascript
   function actualizarEstadoBotonAIU() {
       if (cotizacionEstadoActual === 'ACEPTADA') {
           btnConfigurarAiu.disabled = true;
           btnConfigurarAiu.classList.add('disabled');
       }
   }
   ```

---

## 📝 Ejemplos de Uso

### Ejemplo 1: Cotización de Servicios con AIU

**Escenario**: Cotización de servicios de instalación con AIU activo.

**Datos de Entrada**:
- Modelo: `SERVICIO`
- Subtotal (sin utilidad): $1,000,000
- % Administración: 10%
- % Imprevistos: 5%
- % Utilidad: 10%
- % IVA: 19%

**Cálculo**:
```
Subtotal Base: $1,000,000
Administración (10%): $100,000
Imprevistos (5%): $50,000
Utilidad (10%): $100,000
IVA (19% sobre Utilidad): $19,000
─────────────────────────────
Total Neto: $1,169,000
```

### Ejemplo 2: Cotización Estándar (sin AIU)

**Escenario**: Cotización de equipos sin AIU.

**Datos de Entrada**:
- Modelo: `EQUIPO`
- Subtotal (con utilidad): $1,000,000
- % IVA: 19%

**Cálculo**:
```
Subtotal: $1,000,000
IVA (19% sobre Subtotal): $190,000
─────────────────────────────
Total Neto: $1,190,000
```

### Ejemplo 3: Cambio de Modelo con AIU Activo

**Escenario**: Usuario cambia modelo de `SERVICIO` a `EQUIPO` con AIU activo.

**Comportamiento**:
1. Sistema detecta que AIU está activo
2. Valida que `EQUIPO` no permite AIU
3. Muestra error: "El modo AIU solo es válido para cotizaciones de tipo SERVICIO o MATERIAL"
4. Desactiva AIU automáticamente o requiere desactivación manual

---

## 🔗 Referencias

- **Documentación Principal**: [INFORME_ESTRUCTURA_FUNCIONAL_COTIZACIONES.md](./INFORME_ESTRUCTURA_FUNCIONAL_COTIZACIONES.md)
- **Configuración y Numeración**: [COTIZACIONES_CONFIGURACION_Y_NUMERACION.md](./COTIZACIONES_CONFIGURACION_Y_NUMERACION.md)
- **Arquitectura General**: [arquitectura_general.md](./arquitectura_general.md)

---

## 📌 Notas Técnicas

### Corrección en Configuración Global

La función `guardarConfiguracion()` en `cotizaciones.page.js` resetea valores AIU a `0.00` si el tipo de plantilla no es `SERVICIO` o `MATERIAL`:

```javascript
const esServicioOMaterial = tipoPlantilla === 'SERVICIO' || tipoPlantilla === 'MATERIAL';

const data = {
  // ... otros campos ...
  aiu_admin_default: esServicioOMaterial ? (parseFloat(formData.get('aiu_admin_default')) || 10.00) : 0.00,
  aiu_imprevistos_default: esServicioOMaterial ? (parseFloat(formData.get('aiu_imprevistos_default')) || 5.00) : 0.00,
  aiu_utilidad_default: esServicioOMaterial ? (parseFloat(formData.get('aiu_utilidad_default')) || 10.00) : 0.00
};
```

Esto evita errores de validación cuando se guarda una configuración global con tipo `EQUIPO` o `MIXTO`.

---

**Última actualización**: 2026-02-17  
**Versión del documento**: 1.0
