"""
Modelo de Proyectos v3.3 - Stand-Alone Module (SSoT Strict)
-------------------------------------------------------------------
ARQUITECTURA V2.40 (Zero-Coupling con otras apps de negocio):
- [OK] ÚNICA dependencia externa: apps.tenant.empresa.models.Empresa (SSoT)
- [ERROR] NO hay ForeignKeys a Clientes, Proveedores, Empleados o Inventario.
- [OK] Uso estricto del Patrón "Snapshot" (ID referencial + CharField) para que
     el módulo no se rompa si otros servicios no están disponibles.
- [OK] Modelo Anémico: Solo estructura de datos. Toda validación de IDs 
     y cálculos financieros vivirán en services.py.
-------------------------------------------------------------------
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT
from apps.tenant.empresa.models import Empresa  # ÚNICA Dependencia Externa (SSoT)


class Proyecto(SintelTenantBaseModel):
    """
    Entidad Maestra de Proyectos.
    Funciona autónomamente almacenando snapshots de los responsables y clientes.
    """
    TIPO_SERVICIO = [
        ('PROYECTO_INTEGRAL', _('Proyecto Integral')),
        ('INSTALACION', _('Instalación Técnica')),
        ('MANTENIMIENTO', _('Mantenimiento')),
        ('SUPERVISION', _('Supervisión/Interventoría')),
        ('CONSULTORIA', _('Consultoría')),
    ]

    FASES = [
        ('BORRADOR', _('0. Borrador / Oportunidad')),
        ('INICIO', _('1. Inicio (Comercial y Legal)')),
        ('PLANEACION', _('2. Planeación (Diseño y Técnica)')),
        ('EJECUCION', _('3. Ejecución (Operativa)')),
        ('CIERRE', _('4. Cierre (Administrativa)')),
    ]
    
    ESTADO_TAREA = [
        ('PENDIENTE', _('Pendiente de Gestión')),
        ('EN_PROCESO', _('En Proceso')),
        ('DETENIDO', _('Detenido / Bloqueado')),
        ('COMPLETADO', _('Fase Finalizada')),
    ]

    # --- SSoT (Vínculo Estricto Obligatorio v2.40) ---
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.PROTECT, 
        related_name='proyectos', 
        verbose_name=_('Empresa'),
        help_text=_('SSoT Empresa propietaria')
    )

    # --- DATOS BÁSICOS ---
    nombre = models.CharField(_('Nombre del Proyecto'), max_length=200)
    codigo = models.CharField(_('Código'), max_length=50, blank=True)
    tipo_servicio = models.CharField(_('Tipo de Servicio'), max_length=30, choices=TIPO_SERVICIO, default='PROYECTO_INTEGRAL')
    descripcion = models.TextField(_('Descripción'), blank=True)

    # --- RELACIONES DESACOPLADAS (Loose Coupling / Snapshots) ---
    cliente_id = models.IntegerField(
        _('ID Cliente'), null=True, blank=True, 
        help_text=_("ID referencial del sistema de clientes (Soft Reference)")
    )
    cliente_nombre = models.CharField(
        _('Nombre Cliente'), max_length=200, blank=True, 
        help_text=_("Snapshot del nombre del cliente para evitar FK")
    )
    
    factura_ref = models.CharField(
        _('Referencia Factura'), max_length=50, blank=True, 
        help_text=_("Número o Código de la factura asociada")
    )
    
    valor_contrato_proyectado = models.DecimalField(_('Valor Contrato Proyectado'), max_digits=15, decimal_places=2, default=0)

    # --- RESPONSABLES (WORKFLOW - Referencias Desacopladas) ---
    responsable_comercial_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial comercial (Fase: Inicio)"))
    responsable_comercial_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable comercial'))
    
    responsable_tecnico_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial técnico (Fase: Planeación)"))
    responsable_tecnico_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable técnico'))
    
    responsable_operativo_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial operativo (Fase: Ejecución)"))
    responsable_operativo_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable operativo'))
    
    responsable_administrativo_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial administrativo (Fase: Cierre)"))
    responsable_administrativo_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable administrativo'))
    
    responsable_actual_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial del responsable actual"))
    responsable_actual_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable actual'))

    # --- DOCUMENTACIÓN ---
    contrato_archivo = models.FileField(upload_to='proyectos/contratos/', null=True, blank=True)
    acta_inicio_archivo = models.FileField(upload_to='proyectos/actas/', null=True, blank=True)
    cronograma_archivo = models.FileField(upload_to='proyectos/cronogramas/', null=True, blank=True)
    
    fecha_inicio = models.DateField(_('Fecha de Inicio'), null=True, blank=True)
    fecha_fin_estimada = models.DateField(_('Fecha Fin Estimada'), null=True, blank=True)
    
    # --- INDICADORES FINANCIEROS (Modelo Anémico) ---
    costo_mano_obra_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py'))
    costo_materiales_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py'))
    utilidad_estimada = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py'))
    margen_rentabilidad = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text=_('Calculado por services.py'))

    # --- ENTREGABLES FINALES ---
    porcentaje_avance = models.PositiveIntegerField(_('Porcentaje Avance'), default=0)
    fecha_cierre_real = models.DateField(_('Fecha Cierre Real'), null=True, blank=True)
    acta_entrega_archivo = models.FileField(upload_to='proyectos/entregas/', null=True, blank=True)
    informe_final_archivo = models.FileField(upload_to='proyectos/finales/', null=True, blank=True)

    # --- ESTADO ---
    fase_actual = models.CharField(_('Fase Actual'), max_length=20, choices=FASES, default='BORRADOR')
    estado_tarea = models.CharField(_('Estado de Tarea'), max_length=20, choices=ESTADO_TAREA, default='PENDIENTE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Proyecto")
        verbose_name_plural = _("Proyectos")
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], condition=models.Q(codigo__gt=''), name="uniq_proyecto_codigo_empresa")
        ]
        indexes = [
            # v3.5: Los índices base (empresa, created_at) vienen de SintelTenantBaseModel.
            # Solo añadimos índices específicos de la lógica de negocio de Proyectos.
            models.Index(fields=["empresa", "fase_actual"]),
            models.Index(fields=["empresa", "cliente_id"]),
            models.Index(fields=["responsable_actual_id"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class AsignacionPersonal(SintelTenantBaseModel):
    """
    Registro de Talento Humano asignado al proyecto.
    Desacoplado del módulo de Empleados.
    """
    ROLES = [
        ('TECNICO', _('Técnico Operativo')),
        ('AYUDANTE', _('Ayudante / Auxiliar')),
        ('RESIDENTE', _('Ingeniero Residente')),
        ('SISOMA', _('Inspector SST')),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='asignaciones_personal')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='equipo_trabajo')
    
    # --- Referencia desacoplada ---
    empleado_id = models.IntegerField(_('ID Empleado'), null=True, blank=True, help_text=_("ID referencial del empleado"))
    nombre_colaborador = models.CharField(_('Nombre Colaborador'), max_length=150, help_text=_("Snapshot al momento de asignar"))
    
    rol = models.CharField(_('Rol'), max_length=20, choices=ROLES, default='TECNICO')
    
    fecha_asignacion = models.DateField(_('Fecha Asignación'))
    fecha_fin_asignacion = models.DateField(_('Fecha Fin Asignación'), null=True, blank=True)
    
    # --- Financieros ---
    horas_totales_registradas = models.DecimalField(_('Horas Totales'), max_digits=10, decimal_places=2, default=0)
    costo_hora = models.DecimalField(_('Costo por Hora'), max_digits=12, decimal_places=2, default=0)
    costo_total_asignacion = models.DecimalField(_('Costo Total'), max_digits=15, decimal_places=2, default=0)

    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _("Asignación Personal")
        verbose_name_plural = _("Equipo de Trabajo")
        indexes = [
            # v3.5: Index base en empresa provisto por SintelTenantBaseModel.
            models.Index(fields=["proyecto"]),
            models.Index(fields=["empleado_id"]),
        ]

    def __str__(self):
        return f"{self.nombre_colaborador} - {self.get_rol_display()}"


class PedidoProyecto(SintelTenantBaseModel):
    """
    Encabezado de Solicitud de Recursos.
    Desacoplado de Proveedores e Inventario.
    """
    TIPO = [
        ('MATERIALES', _('Materiales')), 
        ('EQUIPOS', _('Equipos')), 
        ('HERRAMIENTAS', _('Herramientas'))
    ]
    FUENTE = [
        ('PROVEEDOR', _('Proveedor')), 
        ('EMPLEADO', _('Reembolso')), 
        ('ALMACEN', _('Interno'))
    ]
    ESTADO = [
        ('BORRADOR', _('Borrador')), 
        ('SOLICITADO', _('Solicitado')), 
        ('APROBADO', _('Aprobado')), 
        ('RECHAZADO', _('Rechazado'))
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='pedidos_proyecto')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='pedidos')
    
    # Solicitante: Operador del tenant que solicita recursos (TenantProfile para mantener aislamiento)
    solicitante = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_realizados',
        verbose_name=_('Solicitante'),
        help_text=_('Operador del tenant que solicita los recursos')
    )
    
    tipo_recurso = models.CharField(_('Tipo de Recurso'), max_length=20, choices=TIPO)
    fuente_suministro = models.CharField(_('Fuente de Suministro'), max_length=20, choices=FUENTE, default='PROVEEDOR')
    
    # --- Referencias Desacopladas ---
    proveedor_id = models.IntegerField(_('ID Proveedor'), null=True, blank=True, help_text=_("ID referencial si existe módulo de proveedores"))
    proveedor_nombre = models.CharField(_('Nombre Proveedor/Tienda'), max_length=200, blank=True, help_text=_("Snapshot del proveedor"))
    empleado_encargado_nombre = models.CharField(_('Encargado'), max_length=150, blank=True, help_text=_("Quien gestiona el recurso"))

    fecha_solicitud = models.DateField(_('Fecha Solicitud'), auto_now_add=True)
    estado = models.CharField(_('Estado'), max_length=20, choices=ESTADO, default='BORRADOR')
    observaciones = models.TextField(_('Observaciones'), blank=True)
    archivo_adjunto = models.FileField(upload_to='proyectos/pedidos/', null=True, blank=True)

    class Meta:
        verbose_name = _("Pedido de Proyecto")
        verbose_name_plural = _("Pedidos de Proyecto")
        ordering = ['-fecha_solicitud']
        indexes = [
            # v3.5: Index base en empresa provisto por SintelTenantBaseModel.
            models.Index(fields=["proyecto"]),
            models.Index(fields=["proveedor_id"]),
        ]

    def __str__(self):
        return f"Pedido #{self.id} - {self.proyecto.nombre}"


class ItemPedido(SintelTenantBaseModel):
    """
    Detalle de línea de pedido. Estrictamente datos, sin relaciones a Inventario.
    """
    pedido = models.ForeignKey(PedidoProyecto, on_delete=models.CASCADE, related_name='items')
    
    # --- Referencia Desacoplada ---
    material_ref = models.CharField(_('Referencia/SKU'), max_length=50, blank=True, help_text=_("SKU o ID del material referencial"))
    nombre_material = models.CharField(_('Nombre Material'), max_length=200)
    
    cantidad = models.DecimalField(_('Cantidad'), max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(_('Unidad de Medida'), max_length=20)
    precio_unitario = models.DecimalField(_('Precio Unitario'), max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = _("Ítem de Pedido")
        verbose_name_plural = _("Ítems de Pedido")
        unique_together = ('pedido', 'material_ref')
        indexes = [
            models.Index(fields=["pedido"]),
            models.Index(fields=["material_ref"]),
        ]

    def __str__(self):
        return f"{self.cantidad} {self.unidad_medida} - {self.nombre_material}"
