# Plan de Migración en Cascada - Normativa NIIF Colombia (2024-2026)

**Fecha:** 2024-12-19  
**Versión:** 2.0 - Alineado con Flujo Existente  
**Objetivo:** Migrar `apps/tenant/contabilidad/models.py` a normativa NIIF PYMES Colombia

---

## ⚠️ IMPORTANTE: Plan Actualizado

**Este documento ha sido actualizado y alineado con el flujo existente del sistema.**

**📄 Ver plan completo alineado:** [`PLAN_MIGRACION_NIIF_COLOMBIA_ALINEADO.md`](./PLAN_MIGRACION_NIIF_COLOMBIA_ALINEADO.md)

El plan alineado incluye:
- ✅ Análisis completo del flujo actual (Frontend → ViewSet → Service → Model)
- ✅ Actualización incremental sin crear código redundante
- ✅ Migración gradual (campos opcionales primero, luego obligatorios)
- ✅ Compatibilidad hacia atrás garantizada
- ✅ Integración con servicios existentes (`create_asiento`, `materializar_asiento_desde_factura`, etc.)

---

## 📋 Resumen Ejecutivo

Este plan describe la migración en cascada para refactorizar los modelos contables según la normativa colombiana (NIIF PYMES y Estatuto Tributario), asegurando:

1. **Partida Doble Estricta**: Validación obligatoria de ∑ Débitos = ∑ Créditos
2. **Niveles de Cuenta**: Solo registros en cuentas de nivel 6 (Subcuentas)
3. **Terceros Obligatorios**: Cada movimiento debe tener tercero (NIT/CC) para medios magnéticos
4. **Lógica Tributaria**: Cálculo automático de IVA y retenciones
5. **Integridad de Datos**: DecimalField(15,2) para evitar errores de redondeo en COP
6. **Comprobantes**: Trazabilidad con tipos de documento (FVE, CE, RC, GN, ND, NC)

**⚠️ Principios Fundamentales:**
- NO crear código redundante
- Actualizar flujo existente, no duplicar
- Migración incremental que no rompa funcionalidad
- Compatibilidad hacia atrás garantizada

---

## 🔄 Paso 1: Generación de la Migración de Base de Datos

### 1.1 Preparación

```bash
# 1. Backup de la base de datos
python manage.py dumpdata tenant.contabilidad > backup_contabilidad_$(date +%Y%m%d).json

# 2. Revisar estado actual de migraciones
python manage.py showmigrations tenant.contabilidad
```

### 1.2 Crear Migración

```bash
# Crear migración automática (Django detectará los cambios)
python manage.py makemigrations tenant.contabilidad --name refactor_normativa_niif_colombia

# Revisar la migración generada
# Archivo: apps/tenant/contabilidad/migrations/XXXX_refactor_normativa_niif_colombia.py
```

### 1.3 Campos Nuevos Agregados

**AsientoContable:**
- `tipo_comprobante` (CharField, max_length=5, null=True, blank=True)
- `numero_comprobante` (CharField, max_length=50, null=True, blank=True)

**MovimientoContable:**
- `tipo_tercero` (CharField, max_length=20) - **OBLIGATORIO**
- `tercero_id` (PositiveIntegerField) - **OBLIGATORIO**
- `tercero_nit` (CharField, max_length=32) - **OBLIGATORIO**
- `tercero_razon_social` (CharField, max_length=200) - **OBLIGATORIO**
- `base_iva` (DecimalField, max_digits=15, decimal_places=2, default=0.00)
- `iva_generado` (DecimalField, max_digits=15, decimal_places=2, default=0.00)
- `iva_descontable` (DecimalField, max_digits=15, decimal_places=2, default=0.00)
- `retefuente` (DecimalField, max_digits=15, decimal_places=2, default=0.00)
- `reteica` (DecimalField, max_digits=15, decimal_places=2, default=0.00)

**CuentaContable:**
- `nivel` (IntegerField, default=6) - **OBLIGATORIO**

### 1.4 Migración de Datos (Data Migration)

Crear migración de datos personalizada:

```python
# apps/tenant/contabilidad/migrations/XXXX_populate_normativa_fields.py
from django.db import migrations
from decimal import Decimal

def populate_normativa_fields(apps, schema_editor):
    """
    Pobla los campos nuevos de normativa con valores por defecto o calculados.
    """
    MovimientoContable = apps.get_model('contabilidad', 'MovimientoContable')
    CuentaContable = apps.get_model('contabilidad', 'CuentaContable')
    AsientoContable = apps.get_model('contabilidad', 'AsientoContable')
    
    # 1. Poblar nivel=6 en todas las cuentas existentes
    CuentaContable.objects.all().update(nivel=6)
    
    # 2. Poblar terceros en movimientos existentes
    # Estrategia: Si el asiento tiene factura, usar datos del cliente/proveedor de la factura
    # Si no, usar datos genéricos de la empresa
    for movimiento in MovimientoContable.objects.all():
        asiento = movimiento.asiento
        
        # Intentar obtener tercero desde factura
        if asiento.factura:
            factura = asiento.factura
            if hasattr(factura, 'cliente'):
                movimiento.tipo_tercero = 'CLIENTE'
                movimiento.tercero_id = factura.cliente.id
                movimiento.tercero_nit = factura.cliente.numero_documento
                movimiento.tercero_razon_social = factura.cliente.razon_social
            elif hasattr(factura, 'proveedor'):
                movimiento.tipo_tercero = 'PROVEEDOR'
                movimiento.tercero_id = factura.proveedor.id
                movimiento.tercero_nit = factura.proveedor.numero_documento
                movimiento.tercero_razon_social = factura.proveedor.razon_social
        else:
            # Usar datos de la empresa como tercero genérico
            empresa = asiento.empresa
            movimiento.tipo_tercero = 'OTRO'
            movimiento.tercero_id = empresa.id
            movimiento.tercero_nit = empresa.nit or '000000000'
            movimiento.tercero_razon_social = empresa.razon_social or empresa.nombre
        
        movimiento.save()
    
    # 3. Poblar campos tributarios (se calcularán en el siguiente paso)
    MovimientoContable.objects.all().update(
        base_iva=Decimal('0.00'),
        iva_generado=Decimal('0.00'),
        iva_descontable=Decimal('0.00'),
        retefuente=Decimal('0.00'),
        reteica=Decimal('0.00')
    )

def reverse_populate_normativa_fields(apps, schema_editor):
    """Reversa la migración de datos."""
    # No hay reversa necesaria, los campos nuevos se eliminarán automáticamente
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('contabilidad', 'XXXX_refactor_normativa_niif_colombia'),  # Reemplazar con número real
    ]

    operations = [
        migrations.RunPython(populate_normativa_fields, reverse_populate_normativa_fields),
    ]
```

---

## 🔄 Paso 2: Script de Actualización para Mapear Registros Viejos

### 2.1 Script de Mapeo de Cuentas

```python
# apps/tenant/contabilidad/management/commands/mapear_cuentas_nivel_6.py
from django.core.management.base import BaseCommand
from apps.tenant.contabilidad.models import CuentaContable, CatalogoMaestroNIIF
from apps.tenant.contabilidad.choices.choices import CATALOGO_NIIF_COLOMBIA

class Command(BaseCommand):
    help = 'Mapea cuentas existentes al catálogo NIIF y valida nivel 6'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando mapeo de cuentas al catálogo NIIF...')
        
        # 1. Crear catálogo maestro si no existe
        for codigo, nombre, nivel, naturaleza in CATALOGO_NIIF_COLOMBIA:
            CatalogoMaestroNIIF.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'nivel': nivel,
                    'naturaleza': naturaleza
                }
            )
        
        # 2. Mapear cuentas existentes al catálogo
        cuentas_sin_mapeo = []
        for cuenta in CuentaContable.objects.all():
            # Buscar en catálogo por código
            try:
                catalogo = CatalogoMaestroNIIF.objects.get(codigo=cuenta.codigo)
                cuenta.catalogo_referencia = catalogo
                cuenta.nivel = catalogo.nivel
                cuenta.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Cuenta {cuenta.codigo} mapeada a catálogo')
                )
            except CatalogoMaestroNIIF.DoesNotExist:
                cuentas_sin_mapeo.append(cuenta)
                # Asignar nivel 6 por defecto
                cuenta.nivel = 6
                cuenta.save()
                self.stdout.write(
                    self.style.WARNING(f'⚠ Cuenta {cuenta.codigo} no encontrada en catálogo, nivel=6 asignado')
                )
        
        # 3. Validar que todas las cuentas tengan nivel 6
        cuentas_nivel_incorrecto = CuentaContable.objects.exclude(nivel=6)
        if cuentas_nivel_incorrecto.exists():
            self.stdout.write(
                self.style.ERROR(
                    f'❌ {cuentas_nivel_incorrecto.count()} cuentas no son de nivel 6. '
                    f'Estas cuentas no podrán usarse para registros contables.'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('Mapeo completado.'))
```

### 2.2 Script de Actualización de Terceros

```python
# apps/tenant/contabilidad/management/commands/poblar_terceros_movimientos.py
from django.core.management.base import BaseCommand
from apps.tenant.contabilidad.models import MovimientoContable, AsientoContable
from apps.tenant.empresa.models import Empresa

class Command(BaseCommand):
    help = 'Pobla campos de terceros en movimientos existentes'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando poblamiento de terceros en movimientos...')
        
        movimientos_sin_tercero = MovimientoContable.objects.filter(
            tercero_nit__isnull=True
        ) | MovimientoContable.objects.filter(tercero_nit='')
        
        count = 0
        for movimiento in movimientos_sin_tercero:
            asiento = movimiento.asiento
            
            # Estrategia 1: Obtener desde factura
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
            
            # Estrategia 2: Usar empresa como tercero genérico
            if not movimiento.tercero_nit:
                empresa = asiento.empresa
                movimiento.tipo_tercero = 'OTRO'
                movimiento.tercero_id = empresa.id
                movimiento.tercero_nit = empresa.nit or '000000000'
                movimiento.tercero_razon_social = empresa.razon_social or empresa.nombre
            
            movimiento.save()
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {count} movimientos actualizados con datos de terceros.')
        )
```

### 2.3 Script de Validación de Partida Doble

```python
# apps/tenant/contabilidad/management/commands/validar_partida_doble.py
from django.core.management.base import BaseCommand
from apps.tenant.contabilidad.models import AsientoContable
from decimal import Decimal

class Command(BaseCommand):
    help = 'Valida Partida Doble en todos los asientos existentes'

    def handle(self, *args, **options):
        self.stdout.write('Validando Partida Doble en asientos existentes...')
        
        asientos_no_cuadrados = []
        for asiento in AsientoContable.objects.all():
            diferencia = abs(asiento.total_debe - asiento.total_haber)
            if diferencia >= Decimal('0.01'):
                asientos_no_cuadrados.append({
                    'asiento': asiento,
                    'diferencia': diferencia
                })
        
        if asientos_no_cuadrados:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ {len(asientos_no_cuadrados)} asientos no están cuadrados:'
                )
            )
            for item in asientos_no_cuadrados[:10]:  # Mostrar primeros 10
                self.stdout.write(
                    f"  - {item['asiento'].numero}: Diferencia ${item['diferencia']:,.2f}"
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ Todos los asientos están cuadrados.')
            )
```

---

## 🔄 Paso 3: Actualización de Serializers y Admin

### 3.1 Actualizar Serializers

```python
# apps/tenant/contabilidad/api/serializers.py
# Agregar campos nuevos en MovimientoContableSerializer

class MovimientoContableDetailSerializer(serializers.ModelSerializer):
    # Campos existentes...
    
    # Campos nuevos de normativa
    tipo_tercero = serializers.ChoiceField(choices=TIPO_TERCERO_CHOICES, required=True)
    tercero_id = serializers.IntegerField(required=True)
    tercero_nit = serializers.CharField(max_length=32, required=True)
    tercero_razon_social = serializers.CharField(max_length=200, required=True)
    base_iva = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    iva_generado = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    iva_descontable = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    retefuente = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    reteica = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = MovimientoContable
        fields = [
            # Campos existentes...
            'tipo_tercero', 'tercero_id', 'tercero_nit', 'tercero_razon_social',
            'base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'
        ]
```

### 3.2 Actualizar Admin

```python
# apps/tenant/contabilidad/admin.py
from django.contrib import admin
from .models import AsientoContable, MovimientoContable, CuentaContable

@admin.register(MovimientoContable)
class MovimientoContableAdmin(admin.ModelAdmin):
    list_display = [
        'asiento', 'cuenta', 'tercero_razon_social', 'tercero_nit',
        'debe', 'haber', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'
    ]
    list_filter = ['tipo_tercero', 'asiento__estado']
    search_fields = ['tercero_nit', 'tercero_razon_social', 'cuenta__codigo']
    readonly_fields = ['base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('asiento', 'cuenta', 'descripcion', 'orden')
        }),
        ('Valores', {
            'fields': ('debe', 'haber')
        }),
        ('Tercero (Obligatorio)', {
            'fields': ('tipo_tercero', 'tercero_id', 'tercero_nit', 'tercero_razon_social')
        }),
        ('Cálculos Tributarios (Automáticos)', {
            'fields': ('base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'),
            'classes': ('collapse',)
        }),
    )

@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'fecha', 'estado', 'tipo_comprobante', 'numero_comprobante',
        'total_debe', 'total_haber', 'diferencia_display'
    ]
    
    def diferencia_display(self, obj):
        diferencia = abs(obj.total_debe - obj.total_haber)
        if diferencia < Decimal('0.01'):
            return f"✓ ${diferencia:,.2f}"
        return f"❌ ${diferencia:,.2f}"
    diferencia_display.short_description = 'Diferencia'
```

---

## ✅ Checklist de Ejecución

- [ ] **Paso 1.1**: Backup de base de datos realizado
- [ ] **Paso 1.2**: Migración automática generada y revisada
- [ ] **Paso 1.3**: Migración de datos personalizada creada
- [ ] **Paso 1.4**: Migraciones ejecutadas en ambiente de desarrollo
- [ ] **Paso 2.1**: Script de mapeo de cuentas ejecutado
- [ ] **Paso 2.2**: Script de poblamiento de terceros ejecutado
- [ ] **Paso 2.3**: Script de validación de partida doble ejecutado
- [ ] **Paso 3.1**: Serializers actualizados
- [ ] **Paso 3.2**: Admin actualizado
- [ ] **Validación**: Todos los asientos existentes cuadran
- [ ] **Validación**: Todos los movimientos tienen terceros
- [ ] **Validación**: Todas las cuentas tienen nivel 6
- [ ] **Testing**: Pruebas unitarias actualizadas
- [ ] **Documentación**: Documentación actualizada

---

## ⚠️ Consideraciones Importantes

1. **Backup Obligatorio**: Siempre hacer backup antes de ejecutar migraciones
2. **Ambiente de Pruebas**: Ejecutar primero en ambiente de desarrollo/staging
3. **Validación de Datos**: Verificar que todos los datos existentes sean válidos
4. **Rollback Plan**: Tener plan de rollback en caso de problemas
5. **Comunicación**: Notificar a usuarios sobre cambios en la estructura

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 1.0
