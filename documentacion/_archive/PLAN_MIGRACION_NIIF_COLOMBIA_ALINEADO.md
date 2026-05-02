# Plan de Migración Alineado - Normativa NIIF Colombia (2024-2026)

**Fecha:** 2024-12-19  
**Versión:** 2.0 - Alineado con Flujo Existente  
**Objetivo:** Migrar `apps/tenant/contabilidad/models.py` a normativa NIIF PYMES Colombia sin crear código redundante

---

## 📋 Principios Fundamentales

1. **NO crear código redundante**: Actualizar flujo existente, no duplicar
2. **Alineación con estructura actual**: Respetar Service Layer Pattern y arquitectura existente
3. **Migración incremental**: Cambios graduales que no rompan funcionalidad existente
4. **Compatibilidad hacia atrás**: Los datos existentes deben seguir funcionando

---

## 🔍 Análisis del Flujo Actual

### Flujo 1: Crear Asiento Manual (Frontend → Backend)

```
1. Frontend (asientos_form.js):
   - recolectarDatos() → Extrae datos del formulario y movimientos del DOM
   - Envía POST con: { numero, fecha, descripcion, estado, movimientos: [...] }

2. ViewSet (AsientoContableViewSet.create):
   - Recibe request.data
   - Delega a create_asiento(data)

3. Service (asientos_service.py → create_asiento):
   - Extrae movimientos_data del payload
   - Crea AsientoContable
   - Itera movimientos_data y crea MovimientoContable.objects.create()
   - Calcula totales y valida cuadratura

4. Model (MovimientoContable.save):
   - Valida debe/haber
   - Actualiza totales del asiento
```

### Flujo 2: Crear Asiento Automático (Factura/Gasto → Backend)

```
1. Service (materializar_asiento_desde_factura/gasto):
   - Recibe factura/gasto
   - Crea AsientoContable con datos de la factura/gasto
   - Crea MovimientoContable.objects.create() con datos calculados
   - Tiene acceso a cliente/proveedor desde factura/gasto
```

### Flujo 3: Actualizar Asiento (Frontend → Backend)

```
1. ViewSet (AsientoContableViewSet.update):
   - Recibe request.data
   - Delega a update_asiento(asiento_id, data)

2. Service (asientos_service.py → update_asiento):
   - Actualiza campos del asiento
   - Si hay movimientos_data, elimina movimientos antiguos y crea nuevos
   - Recalcula totales
```

---

## 🎯 Plan de Actualización (Sin Código Redundante)

### FASE 1: Actualizar Modelos (models.py)

**Objetivo:** Agregar campos nuevos de normativa sin romper funcionalidad existente

#### 1.1 Actualizar AsientoContable

**Cambios:**
- Agregar `tipo_comprobante` (CharField, null=True, blank=True) - **OPCIONAL inicialmente**
- Agregar `numero_comprobante` (CharField, null=True, blank=True) - **OPCIONAL inicialmente**
- Mejorar `save()` con validación de Partida Doble Estricta
- Agregar método `calcular_totales()` usando agregación de BD
- Agregar método `validar_partida_doble()`

**Código:**
```python
# En models.py - AsientoContable
# Agregar campos nuevos (OPCIONALES inicialmente para compatibilidad)
tipo_comprobante = models.CharField(
    max_length=5,
    choices=TIPO_COMPROBANTE_CHOICES,
    blank=True,
    null=True,
    verbose_name=_('Tipo de Comprobante')
)
numero_comprobante = models.CharField(
    max_length=50,
    blank=True,
    null=True,
    verbose_name=_('Número de Comprobante')
)

# Mejorar save() con validación de Partida Doble
def calcular_totales(self):
    """Recalcula totales desde movimientos usando agregación."""
    from django.db.models import Sum
    totales = self.movimientos.aggregate(
        total_debe=Sum('debe'),
        total_haber=Sum('haber')
    )
    self.total_debe = totales['total_debe'] or Decimal('0.00')
    self.total_haber = totales['total_haber'] or Decimal('0.00')

def validar_partida_doble(self):
    """Valida Partida Doble Estricta."""
    diferencia = abs(self.total_debe - self.total_haber)
    if diferencia >= Decimal('0.01'):
        raise ValidationError({
            'total_debe': _(
                f'Partida Doble no cumplida. Diferencia: ${diferencia:,.2f}. '
                f'La normativa colombiana exige que ∑ Débitos = ∑ Créditos.'
            )
        })
    return True

def save(self, *args, **kwargs):
    # Recalcular totales antes de validar
    self.calcular_totales()
    
    # Validar Partida Doble si está aprobado/cerrado
    if self.estado in ['APROBADO', 'CERRADO']:
        self.validar_partida_doble()
    
    super().save(*args, **kwargs)
```

#### 1.2 Actualizar MovimientoContable

**Cambios:**
- Agregar campos de terceros (OPCIONALES inicialmente, luego obligatorios)
- Agregar campos tributarios (OPCIONALES, se calculan automáticamente)
- Agregar validación de nivel 6 en `clean()`
- Mejorar `save()` con cálculos automáticos de IVA y retenciones

**Código:**
```python
# En models.py - MovimientoContable
# Agregar campos de terceros (OPCIONALES inicialmente)
tipo_tercero = models.CharField(
    max_length=20,
    choices=TIPO_TERCERO_CHOICES,
    blank=True,  # OPCIONAL inicialmente
    null=True,
    verbose_name=_('Tipo de Tercero')
)
tercero_id = models.PositiveIntegerField(
    blank=True,  # OPCIONAL inicialmente
    null=True,
    verbose_name=_('ID del Tercero')
)
tercero_nit = models.CharField(
    max_length=32,
    blank=True,  # OPCIONAL inicialmente
    null=True,
    verbose_name=_('NIT/CC del Tercero')
)
tercero_razon_social = models.CharField(
    max_length=200,
    blank=True,  # OPCIONAL inicialmente
    null=True,
    verbose_name=_('Razón Social del Tercero')
)

# Campos tributarios (OPCIONALES, se calculan automáticamente)
base_iva = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name=_('Base IVA')
)
iva_generado = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name=_('IVA Generado')
)
iva_descontable = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name=_('IVA Descontable')
)
retefuente = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name=_('Retención en la Fuente')
)
reteica = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    default=Decimal('0.00'),
    verbose_name=_('Retención ICA')
)

# Agregar métodos de cálculo
def calcular_iva(self, porcentaje_iva=Decimal('0.19')):
    """Calcula IVA generado o descontable según cuenta."""
    if self.cuenta.codigo == '240805':  # IVA Generado
        self.base_iva = self.debe if self.debe > 0 else self.haber
        self.iva_generado = (self.base_iva * porcentaje_iva).quantize(Decimal('0.01'))
        self.iva_descontable = Decimal('0.00')
    elif self.cuenta.codigo == '240810':  # IVA Descontable
        self.base_iva = self.debe if self.debe > 0 else self.haber
        self.iva_descontable = (self.base_iva * porcentaje_iva).quantize(Decimal('0.01'))
        self.iva_generado = Decimal('0.00')
    else:
        self.base_iva = Decimal('0.00')
        self.iva_generado = Decimal('0.00')
        self.iva_descontable = Decimal('0.00')

def calcular_retenciones(self, porcentaje_retefuente=Decimal('0.00'), porcentaje_reteica=Decimal('0.00')):
    """Calcula retenciones según cuenta."""
    base = self.debe if self.debe > 0 else self.haber
    if self.cuenta.codigo.startswith('2365'):
        self.retefuente = (base * porcentaje_retefuente).quantize(Decimal('0.01'))
    else:
        self.retefuente = Decimal('0.00')
    if self.cuenta.codigo.startswith('2368'):
        self.reteica = (base * porcentaje_reteica).quantize(Decimal('0.01'))
    else:
        self.reteica = Decimal('0.00')

def clean(self):
    """Validaciones según normativa."""
    super().clean()
    
    # Validar nivel 6 (solo advertencia inicialmente, no bloquea)
    if self.cuenta and self.cuenta.nivel != 6:
        # Advertencia pero no error (para compatibilidad)
        pass
    
    # Validar terceros (solo advertencia inicialmente)
    if not self.tercero_nit or not self.tercero_razon_social:
        # Advertencia pero no error (para compatibilidad)
        pass

def save(self, *args, **kwargs):
    # Validaciones existentes
    if self.debe > 0 and self.haber > 0:
        raise ValueError(_('Un movimiento no puede tener débito y crédito simultáneamente'))
    if self.debe == 0 and self.haber == 0:
        raise ValueError(_('Un movimiento debe tener débito o crédito mayor a cero'))
    
    # Calcular IVA y retenciones si aplica
    self.calcular_iva()
    self.calcular_retenciones()
    
    super().save(*args, **kwargs)
    
    # Actualizar totales del asiento (usar método mejorado)
    self.asiento.calcular_totales()
    self.asiento.save(update_fields=['total_debe', 'total_haber'])
```

#### 1.3 Actualizar CuentaContable

**Cambios:**
- Agregar campo `nivel` (IntegerField, default=6)
- Agregar validación en `clean()` para nivel 6

**Código:**
```python
# En models.py - CuentaContable
nivel = models.IntegerField(
    default=6,
    verbose_name=_('Nivel'),
    help_text=_('Nivel de la cuenta según NIIF. Solo nivel 6 permite registros.')
)

def clean(self):
    """Validación de nivel según normativa."""
    super().clean()
    # Si no tiene nivel, asignar 6 por defecto
    if not self.nivel:
        self.nivel = 6

def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)
```

---

### FASE 2: Actualizar Services (asientos_service.py)

**Objetivo:** Actualizar `create_asiento()` y `update_asiento()` para poblar terceros automáticamente

#### 2.1 Función Helper: Extraer Tercero desde Asiento

**Código:**
```python
# En asientos_service.py - Agregar función helper
def _extraer_tercero_desde_asiento(asiento, movimiento_data=None):
    """
    Extrae datos de tercero desde factura o datos del movimiento.
    
    ⚠️ NORMATIVA: Pobla terceros automáticamente cuando es posible.
    
    Returns:
        dict: {
            'tipo_tercero': str,
            'tercero_id': int,
            'tercero_nit': str,
            'tercero_razon_social': str
        }
    """
    # Estrategia 1: Obtener desde factura relacionada
    if asiento.factura:
        factura = asiento.factura
        if hasattr(factura, 'cliente') and factura.cliente:
            return {
                'tipo_tercero': 'CLIENTE',
                'tercero_id': factura.cliente.id,
                'tercero_nit': factura.cliente.numero_documento,
                'tercero_razon_social': factura.cliente.razon_social
            }
        elif hasattr(factura, 'proveedor') and factura.proveedor:
            return {
                'tipo_tercero': 'PROVEEDOR',
                'tercero_id': factura.proveedor.id,
                'tercero_nit': factura.proveedor.numero_documento,
                'tercero_razon_social': factura.proveedor.razon_social
            }
    
    # Estrategia 2: Obtener desde movimiento_data (si viene del frontend)
    if movimiento_data:
        if 'tipo_tercero' in movimiento_data and movimiento_data['tipo_tercero']:
            return {
                'tipo_tercero': movimiento_data['tipo_tercero'],
                'tercero_id': movimiento_data.get('tercero_id'),
                'tercero_nit': movimiento_data.get('tercero_nit', ''),
                'tercero_razon_social': movimiento_data.get('tercero_razon_social', '')
            }
    
    # Estrategia 3: Usar empresa como tercero genérico (fallback)
    empresa = asiento.empresa
    return {
        'tipo_tercero': 'OTRO',
        'tercero_id': empresa.id,
        'tercero_nit': empresa.nit or '000000000',
        'tercero_razon_social': empresa.razon_social or empresa.nombre
    }
```

#### 2.2 Actualizar create_asiento()

**Cambios:**
- Usar `_extraer_tercero_desde_asiento()` para poblar terceros en cada movimiento
- Validar nivel 6 de cuenta antes de crear movimiento
- Poblar campos tributarios automáticamente

**Código:**
```python
# En asientos_service.py - Actualizar create_asiento()
@transaction.atomic
def create_asiento(data: Dict[str, Any]) -> Dict[str, Any]:
    # ... código existente hasta crear asiento ...
    
    asiento = AsientoContable.objects.create(**data)
    
    # Crear movimientos
    total_debe = Decimal('0.00')
    total_haber = Decimal('0.00')
    orden = 1
    
    for mov_data in movimientos_data:
        cuenta_id = mov_data.get('cuenta')
        if not cuenta_id:
            raise ValidationError({
                'movimientos': [f'Movimiento {orden}: El campo "cuenta" es requerido.']
            })
        
        # ⚠️ NORMATIVA: Validar nivel 6 de cuenta
        cuenta = CuentaContable.objects.get(id=cuenta_id)
        if cuenta.nivel != 6:
            raise ValidationError({
                'movimientos': [f'Movimiento {orden}: La cuenta {cuenta.codigo} no es de nivel 6. Solo se permiten registros en cuentas auxiliares (nivel 6).']
            })
        
        debe = Decimal(str(mov_data.get('debe', 0)))
        haber = Decimal(str(mov_data.get('haber', 0)))
        
        # Validaciones existentes...
        
        # ⚠️ NORMATIVA: Extraer tercero automáticamente
        tercero_data = _extraer_tercero_desde_asiento(asiento, mov_data)
        
        # Crear movimiento con datos de tercero
        movimiento = MovimientoContable.objects.create(
            asiento=asiento,
            cuenta_id=cuenta_id,
            descripcion=mov_data.get('descripcion', ''),
            debe=debe,
            haber=haber,
            orden=orden,
            # ⚠️ NORMATIVA: Campos de terceros
            tipo_tercero=tercero_data['tipo_tercero'],
            tercero_id=tercero_data['tercero_id'],
            tercero_nit=tercero_data['tercero_nit'],
            tercero_razon_social=tercero_data['tercero_razon_social']
        )
        
        # Los campos tributarios se calculan automáticamente en MovimientoContable.save()
        
        total_debe += debe
        total_haber += haber
        orden += 1
    
    # Actualizar totales (usar método mejorado del modelo)
    asiento.calcular_totales()
    asiento.save(update_fields=['total_debe', 'total_haber'])
    
    # Validar cuadratura si está aprobado...
    # ... resto del código existente ...
```

#### 2.3 Actualizar materializar_asiento_desde_factura()

**Cambios:**
- Poblar terceros desde factura.cliente o factura.proveedor
- Agregar tipo_comprobante y numero_comprobante al asiento

**Código:**
```python
# En asientos_service.py - Actualizar materializar_asiento_desde_factura()
@transaction.atomic
def materializar_asiento_desde_factura(factura) -> Dict[str, Any]:
    # ... código existente hasta crear asiento ...
    
    # ⚠️ NORMATIVA: Agregar comprobante
    asiento = AsientoContable.objects.create(
        numero=numero_asiento,
        fecha=factura.fecha_emision.date() if hasattr(factura.fecha_emision, 'date') else factura.fecha_emision,
        descripcion=descripcion,
        estado='APROBADO',
        empresa=empresa,
        factura=factura,
        tipo_comprobante='FVE',  # Factura de Venta Electrónica
        numero_comprobante=factura.numero
    )
    
    # ... código existente para crear movimientos ...
    
    # ⚠️ NORMATIVA: Poblar terceros en cada movimiento
    for mov_data in movimientos:
        # Extraer tercero desde factura
        if factura.naturaleza == Factura.Naturaleza.VENTA and hasattr(factura, 'cliente'):
            tercero_data = {
                'tipo_tercero': 'CLIENTE',
                'tercero_id': factura.cliente.id,
                'tercero_nit': factura.cliente.numero_documento,
                'tercero_razon_social': factura.cliente.razon_social
            }
        elif factura.naturaleza == Factura.Naturaleza.COMPRA and hasattr(factura, 'proveedor'):
            tercero_data = {
                'tipo_tercero': 'PROVEEDOR',
                'tercero_id': factura.proveedor.id,
                'tercero_nit': factura.proveedor.numero_documento,
                'tercero_razon_social': factura.proveedor.razon_social
            }
        else:
            tercero_data = {
                'tipo_tercero': 'OTRO',
                'tercero_id': empresa.id,
                'tercero_nit': empresa.nit or '000000000',
                'tercero_razon_social': empresa.razon_social or empresa.nombre
            }
        
        # Agregar terceros al movimiento
        mov_data.update(tercero_data)
        MovimientoContable.objects.create(**mov_data)
    
    # ... resto del código existente ...
```

#### 2.4 Actualizar materializar_asiento_desde_gasto()

**Cambios similares a materializar_asiento_desde_factura()**

---

### FASE 3: Actualizar Serializers (api/serializers.py)

**Objetivo:** Agregar campos nuevos a serializers sin romper compatibilidad

#### 3.1 Actualizar MovimientoContableDetailSerializer

**Código:**
```python
# En api/serializers.py - Actualizar MovimientoContableDetailSerializer
class MovimientoContableDetailSerializer(serializers.ModelSerializer):
    cuenta_nombre = serializers.CharField(source='cuenta.nombre', read_only=True)
    cuenta_codigo = serializers.CharField(source='cuenta.codigo', read_only=True)
    
    # ⚠️ NORMATIVA: Campos de terceros (opcionales inicialmente)
    tipo_tercero = serializers.ChoiceField(choices=TIPO_TERCERO_CHOICES, required=False, allow_null=True)
    tercero_id = serializers.IntegerField(required=False, allow_null=True)
    tercero_nit = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
    tercero_razon_social = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)
    
    # ⚠️ NORMATIVA: Campos tributarios (read-only, se calculan automáticamente)
    base_iva = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    iva_generado = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    iva_descontable = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    retefuente = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    reteica = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = MovimientoContable
        fields = (
            'id', 'asiento', 'cuenta', 'cuenta_nombre', 'cuenta_codigo',
            'orden', 'debe', 'haber', 'descripcion',
            # Campos nuevos
            'tipo_tercero', 'tercero_id', 'tercero_nit', 'tercero_razon_social',
            'base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'
        )
        read_only_fields = ['id', 'base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica']
```

#### 3.2 Actualizar AsientoContableDetailSerializer

**Código:**
```python
# En api/serializers.py - Actualizar AsientoContableDetailSerializer
class AsientoContableDetailSerializer(serializers.ModelSerializer):
    movimientos = MovimientoContableDetailSerializer(many=True, read_only=True)
    
    # ⚠️ NORMATIVA: Campos de comprobante (opcionales inicialmente)
    tipo_comprobante = serializers.ChoiceField(choices=TIPO_COMPROBANTE_CHOICES, required=False, allow_null=True)
    numero_comprobante = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = AsientoContable
        fields = tuple(ASIENTO_DETAIL_FIELDS) + ('movimientos', 'tipo_comprobante', 'numero_comprobante')
        read_only_fields = ['id', 'total_debe', 'total_haber', 'created_at', 'updated_at']
```

---

### FASE 4: Migración de Base de Datos

#### 4.1 Migración Automática

```bash
# Generar migración automática
python manage.py makemigrations tenant.contabilidad --name add_normativa_niif_fields
```

#### 4.2 Migración de Datos

**Archivo:** `apps/tenant/contabilidad/migrations/XXXX_populate_normativa_fields.py`

```python
from django.db import migrations
from decimal import Decimal

def populate_normativa_fields(apps, schema_editor):
    """
    Pobla campos nuevos de normativa con valores por defecto o calculados.
    """
    MovimientoContable = apps.get_model('contabilidad', 'MovimientoContable')
    CuentaContable = apps.get_model('contabilidad', 'CuentaContable')
    AsientoContable = apps.get_model('contabilidad', 'AsientoContable')
    
    # 1. Poblar nivel=6 en todas las cuentas existentes
    CuentaContable.objects.all().update(nivel=6)
    
    # 2. Poblar terceros en movimientos existentes
    for movimiento in MovimientoContable.objects.all():
        asiento = movimiento.asiento
        
        # Estrategia: Obtener desde factura
        if asiento.factura:
            factura = asiento.factura
            if hasattr(factura, 'cliente') and factura.cliente:
                movimiento.tipo_tercero = 'CLIENTE'
                movimiento.tercero_id = factura.cliente.id
                movimiento.tercero_nit = factura.cliente.numero_documento
                movimiento.tercero_razon_social = factura.cliente.razon_social
            elif hasattr(factura, 'proveedor') and factura.proveedor:
                movimiento.tipo_tercero = 'PROVEEDOR'
                movimiento.tercero_id = factura.proveedor.id
                movimiento.tercero_nit = factura.proveedor.numero_documento
                movimiento.tercero_razon_social = factura.proveedor.razon_social
        
        # Fallback: Usar empresa
        if not movimiento.tercero_nit:
            empresa = asiento.empresa
            movimiento.tipo_tercero = 'OTRO'
            movimiento.tercero_id = empresa.id
            movimiento.tercero_nit = empresa.nit or '000000000'
            movimiento.tercero_razon_social = empresa.razon_social or empresa.nombre
        
        # Calcular IVA y retenciones (se ejecutarán en save())
        movimiento.save()
    
    # 3. Poblar comprobantes en asientos con factura
    for asiento in AsientoContable.objects.filter(factura__isnull=False):
        asiento.tipo_comprobante = 'FVE'
        asiento.numero_comprobante = asiento.factura.numero if hasattr(asiento.factura, 'numero') else None
        asiento.save(update_fields=['tipo_comprobante', 'numero_comprobante'])

def reverse_populate_normativa_fields(apps, schema_editor):
    """Reversa la migración de datos."""
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('contabilidad', 'XXXX_add_normativa_niif_fields'),  # Reemplazar con número real
    ]

    operations = [
        migrations.RunPython(populate_normativa_fields, reverse_populate_normativa_fields),
    ]
```

---

### FASE 5: Hacer Campos Obligatorios (Migración Gradual)

**Objetivo:** Después de poblar todos los datos, hacer campos obligatorios

#### 5.1 Migración para Hacer Campos Obligatorios

```python
# apps/tenant/contabilidad/migrations/XXXX_make_normativa_fields_required.py
from django.db import migrations, models
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [
        ('contabilidad', 'XXXX_populate_normativa_fields'),
    ]

    operations = [
        # Hacer campos de terceros obligatorios
        migrations.AlterField(
            model_name='movimientocontable',
            name='tipo_tercero',
            field=models.CharField(
                max_length=20,
                choices=[...],
                verbose_name='Tipo de Tercero'
                # Remover blank=True, null=True
            ),
        ),
        migrations.AlterField(
            model_name='movimientocontable',
            name='tercero_id',
            field=models.PositiveIntegerField(
                verbose_name='ID del Tercero'
                # Remover blank=True, null=True
            ),
        ),
        migrations.AlterField(
            model_name='movimientocontable',
            name='tercero_nit',
            field=models.CharField(
                max_length=32,
                verbose_name='NIT/CC del Tercero'
                # Remover blank=True, null=True, allow_blank=True
            ),
        ),
        migrations.AlterField(
            model_name='movimientocontable',
            name='tercero_razon_social',
            field=models.CharField(
                max_length=200,
                verbose_name='Razón Social del Tercero'
                # Remover blank=True, null=True, allow_blank=True
            ),
        ),
    ]
```

---

## 📝 Checklist de Ejecución

### Pre-Migración
- [ ] Backup completo de base de datos
- [ ] Revisar código actual en `models.py`, `services/asientos_service.py`, `api/serializers.py`
- [ ] Identificar todos los lugares donde se crean `MovimientoContable`

### Fase 1: Modelos
- [ ] Actualizar `AsientoContable` con campos nuevos y métodos
- [ ] Actualizar `MovimientoContable` con campos nuevos y métodos
- [ ] Actualizar `CuentaContable` con campo `nivel`
- [ ] Probar que modelos existentes siguen funcionando

### Fase 2: Services
- [ ] Agregar función `_extraer_tercero_desde_asiento()`
- [ ] Actualizar `create_asiento()` para poblar terceros
- [ ] Actualizar `update_asiento()` para poblar terceros
- [ ] Actualizar `materializar_asiento_desde_factura()` para poblar terceros
- [ ] Actualizar `materializar_asiento_desde_gasto()` para poblar terceros
- [ ] Probar que creación de asientos sigue funcionando

### Fase 3: Serializers
- [ ] Actualizar `MovimientoContableDetailSerializer` con campos nuevos
- [ ] Actualizar `AsientoContableDetailSerializer` con campos nuevos
- [ ] Probar que API sigue funcionando

### Fase 4: Migración de BD
- [ ] Generar migración automática
- [ ] Crear migración de datos personalizada
- [ ] Ejecutar migraciones en desarrollo
- [ ] Validar que datos existentes se poblaron correctamente

### Fase 5: Validaciones Estrictas
- [ ] Ejecutar script de validación de partida doble
- [ ] Ejecutar script de validación de niveles de cuenta
- [ ] Ejecutar script de validación de terceros
- [ ] Hacer campos obligatorios (migración gradual)

### Post-Migración
- [ ] Probar creación de asientos manuales
- [ ] Probar creación de asientos automáticos desde facturas
- [ ] Probar creación de asientos automáticos desde gastos
- [ ] Validar que cálculos de IVA y retenciones funcionan
- [ ] Actualizar documentación

---

## ⚠️ Consideraciones Importantes

1. **Compatibilidad hacia atrás**: Campos nuevos son OPCIONALES inicialmente
2. **Migración gradual**: Primero poblar datos, luego hacer obligatorios
3. **No romper funcionalidad**: Todos los flujos existentes deben seguir funcionando
4. **Testing exhaustivo**: Probar todos los flujos antes de producción

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 2.0 - Alineado con Flujo Existente
