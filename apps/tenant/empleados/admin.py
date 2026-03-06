"""
Admin para empleados (aislado por tenant).

⚠️ v2.95: Alineado con arquitectura Tabulator Factory y flujo secuencial.
⚠️ v2.40: Modelos Anemic - Lógica de negocio en services.py

django-tenants maneja automáticamente el aislamiento por esquema.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Empleado, Contrato, Devengo


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    """
    Admin para el modelo Empleado.
    
    ⚠️ v2.95: Incluye campos de seguridad social (EPS, AFP, ARL).
    ⚠️ FLUJO SECUENCIAL: Empleado → Contrato → Nómina
    """
    list_display = (
        "numero_documento", 
        "primer_nombre", 
        "primer_apellido",
        "email",
        "telefono",
        "estado", 
        "fecha_ingreso",
        "eps",
        "afp"
    )
    list_display_links = ("numero_documento", "primer_nombre", "primer_apellido")
    search_fields = (
        "numero_documento", 
        "primer_nombre", 
        "primer_apellido", 
        "segundo_nombre",
        "segundo_apellido",
        "email",
        "telefono"
    )
    list_filter = (
        "estado", 
        "tipo_documento",
        "eps",
        "afp",
        "arl",
        "fecha_ingreso"
    )
    readonly_fields = ("nombre_completo",)
    
    fieldsets = (
        ('Identificación', {
            'fields': ('tipo_documento', 'numero_documento', 'empresa')
        }),
        ('Datos Personales', {
            'fields': (
                'primer_nombre', 'segundo_nombre',
                'primer_apellido', 'segundo_apellido',
                'nombre_completo'
            )
        }),
        ('Contacto', {
            'fields': ('email', 'telefono')
        }),
        ('Seguridad Social', {
            'fields': ('eps', 'afp', 'arl', 'nivel_riesgo_arl'),
            'description': 'Información de seguridad social colombiana'
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'fecha_ingreso', 'fecha_retiro')
        }),
    )
    
    def nombre_completo(self, obj):
        """Muestra el nombre completo calculado."""
        return obj.nombre_completo
    nombre_completo.short_description = _('Nombre Completo')
    nombre_completo.admin_order_field = 'primer_nombre'


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    """
    Admin para el modelo Contrato.
    
    ⚠️ v2.40: Máquina de Estados Estricta - Solo UN contrato ACTIVO por empleado.
    ⚠️ FLUJO SECUENCIAL: Requiere Empleado, habilita creación de Nómina.
    """
    list_display = (
        "empleado", 
        "tipo", 
        "cargo", 
        "salario_mensual", 
        "auxilio_transporte",
        "estado",
        "activo",
        "fecha_inicio",
        "fecha_fin"
    )
    list_display_links = ("empleado", "cargo")
    list_filter = (
        "tipo", 
        "estado",
        "activo",
        "fecha_inicio"
    )
    search_fields = (
        "empleado__primer_nombre", 
        "empleado__primer_apellido",
        "empleado__numero_documento",
        "cargo"
    )
    readonly_fields = ("activo",)  # Se sincroniza automáticamente con estado
    
    fieldsets = (
        ('Empleado', {
            'fields': ('empleado',)
        }),
        ('Tipo y Fechas', {
            'fields': ('tipo', 'fecha_inicio', 'fecha_fin')
        }),
        ('Valores Económicos', {
            'fields': (
                'salario_mensual',
                'auxilio_transporte',
                'prestamos_empresa'
            )
        }),
        ('Información Adicional', {
            'fields': ('cargo', 'archivo_pdf')
        }),
        ('Estado', {
            'fields': ('estado', 'activo'),
            'description': '⚠️ estado es la fuente de verdad. activo se sincroniza automáticamente.'
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """activo siempre es readonly porque se sincroniza con estado."""
        readonly = list(self.readonly_fields)
        if obj:  # En edición, activo es readonly
            readonly.append('activo')
        return readonly


@admin.register(Devengo)
class DevengoAdmin(admin.ModelAdmin):
    """
    Admin para el modelo Devengo (Nómina).
    
    ⚠️ v2.40: Inmutable - Una vez creada, solo se puede anular (no editar).
    ⚠️ FLUJO SECUENCIAL: Requiere Contrato ACTIVO, habilita botón "Historial".
    ⚠️ SSoT: neto_pagar se calcula automáticamente en save().
    """
    list_display = (
        "empleado", 
        "periodo_mes", 
        "fecha_pago",
        "dias_laborados",
        "salario_base", 
        "neto_pagar", 
        "anulado"
    )
    list_display_links = ("empleado", "periodo_mes")
    list_filter = (
        "periodo_mes", 
        "fecha_pago", 
        "anulado",
        "contrato__estado"
    )
    search_fields = (
        "empleado__primer_nombre", 
        "empleado__primer_apellido", 
        "empleado__numero_documento",
        "periodo_mes"
    )
    readonly_fields = (
        "neto_pagar",
        "salario_base",
        "auxilio_transporte",
        "salud_empleado",
        "pension_empleado"
    )
    
    fieldsets = (
        ('Empleado y Contrato', {
            'fields': ('empleado', 'contrato')
        }),
        ('Periodo', {
            'fields': ('periodo_mes', 'fecha_pago', 'dias_laborados')
        }),
        ('Devengos', {
            'fields': (
                'salario_base',
                'auxilio_transporte',
                'otros_devengos'
            ),
            'description': 'Valores proporcionales calculados según días laborados'
        }),
        ('Deducciones', {
            'fields': (
                'salud_empleado',
                'pension_empleado',
                'prestamos',
                'descuentos_operativos'
            )
        }),
        ('Resultado', {
            'fields': ('neto_pagar', 'anulado', 'observaciones'),
            'description': '⚠️ neto_pagar se calcula automáticamente (SSoT)'
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """
        ⚠️ v2.40: Nómina es INMUTABLE - Solo se puede anular, no editar.
        Si ya existe (obj.pk), hacer todos los campos readonly excepto anulado y observaciones.
        """
        readonly = list(self.readonly_fields)
        if obj and obj.pk:
            # Si ya existe, solo permitir editar anulado y observaciones
            readonly.extend([
                'empleado', 'contrato', 'periodo_mes', 'fecha_pago',
                'dias_laborados', 'otros_devengos', 'prestamos', 
                'descuentos_operativos'
            ])
        return readonly
    
    def has_delete_permission(self, request, obj=None):
        """
        ⚠️ v2.40: No permitir eliminar nóminas, solo anularlas.
        """
        return False  # Usar anulado=True en lugar de eliminar
