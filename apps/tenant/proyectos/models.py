"""
Modelo de Proyectos v3.3 - Stand-Alone Module (SSoT Strict)
-------------------------------------------------------------------
ARQUITECTURA V2.40 (Zero-Coupling con otras apps de negocio):
- [OK] uNICA dependencia externa: apps.tenant.empresa.models.Empresa (SSoT)
- [ERROR] NO hay ForeignKeys a Clientes, Proveedores, Empleados o Inventario.
- [OK] Uso estricto del Patron "Snapshot" (ID referencial + CharField) para que
     el modulo no se rompa si otros servicios no estan disponibles.
- [OK] Modelo Anemico: Solo estructura de datos. Toda validacion de IDs 
     y calculos financieros viviran en services.py.
-------------------------------------------------------------------
"""

import uuid as uuid_module

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT
from apps.tenant.empresa.models import Empresa  # uNICA Dependencia Externa (SSoT)

# Storage privado para el expediente documental (DocumentoProyecto). NO usa el
# storage por defecto (MEDIA_ROOT) porque nginx sirve /media/ publicamente sin
# autenticacion (ver PRIVATE_MEDIA_ROOT en config/settings.py). Solo se accede
# via el endpoint de descarga autenticado en api/viewsets.py.
documentos_storage = FileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT))


class Proyecto(SintelTenantBaseModel):
    """
    Entidad Maestra de Proyectos.
    Funciona autonomamente almacenando snapshots de los responsables y clientes.
    """
    TIPO_SERVICIO = [
        ('PROYECTO_INTEGRAL', _('Proyecto Integral')),
        ('INSTALACION', _('Instalacion Tecnica')),
        ('MANTENIMIENTO', _('Mantenimiento')),
        ('SUPERVISION', _('Supervision/Interventoria')),
        ('CONSULTORIA', _('Consultoria')),
    ]

    FASES = [
        ('BORRADOR', _('0. Borrador / Oportunidad')),
        ('INICIO', _('1. Inicio (Comercial y Legal)')),
        ('PLANEACION', _('2. Planeacion (Diseno y Tecnica)')),
        ('EJECUCION', _('3. Ejecucion (Operativa)')),
        ('CIERRE', _('4. Cierre (Administrativa)')),
    ]
    
    ESTADO_TAREA = [
        ('PENDIENTE', _('Pendiente de Gestion')),
        ('EN_PROCESO', _('En Proceso')),
        ('DETENIDO', _('Detenido / Bloqueado')),
        ('COMPLETADO', _('Fase Finalizada')),
    ]

    # UUID Lookup Field (AGENTS.md section 14 - expone UUID en URLs, no pk secuencial)
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # --- SSoT (Vinculo Estricto Obligatorio v2.40) ---
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.PROTECT, 
        related_name='proyectos', 
        verbose_name=_('Empresa'),
        help_text=_('SSoT Empresa propietaria')
    )

    # --- DATOS BaSICOS ---
    nombre = models.CharField(_('Nombre del Proyecto'), max_length=200)
    codigo = models.CharField(_('Codigo'), max_length=50, blank=True)
    tipo_servicio = models.CharField(_('Tipo de Servicio'), max_length=30, choices=TIPO_SERVICIO, default='PROYECTO_INTEGRAL')
    descripcion = models.TextField(_('Descripcion'), blank=True)

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
        help_text=_("Numero o Codigo de la factura asociada")
    )
    
    factura_costo = models.ForeignKey(
        'facturas.Factura',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_asociados',
        verbose_name=_('Factura (Centro de Costos)'),
        help_text=_('Factura que actua como centro de costos para este proyecto')
    )
    factura_costo_numero = models.CharField(
        _('Numero Factura (Snapshot)'), max_length=50, blank=True,
        help_text=_("Snapshot del numero de la factura para evitar FK en listados")
    )

    # --- ViNCULO CON INVENTARIO (Pull Model / DSV) ---
    servicio_asociado = models.ForeignKey(
        'tenant_inventario.Servicio',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='proyectos_ejecucion',
        verbose_name=_('Servicio Asociado'),
        help_text=_('Servicio del catalogo/portafolio (campo legacy, no usar en formularios nuevos)')
    )
    movimiento_inventario_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name=_('Movimiento de Inventario'),
        help_text=_('UUID del MovimientoInventario vinculado (Soft Reference Kardex).')
    )

    valor_contrato_proyectado = models.DecimalField(_('Valor Contrato Proyectado'), max_digits=15, decimal_places=2, default=0)

    # --- RESPONSABLES (WORKFLOW - Referencias Desacopladas) ---
    responsable_comercial_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial comercial (Fase: Inicio)"))
    responsable_comercial_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable comercial'))
    
    responsable_tecnico_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial tecnico (Fase: Planeacion)"))
    responsable_tecnico_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable tecnico'))
    
    responsable_operativo_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial operativo (Fase: Ejecucion)"))
    responsable_operativo_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable operativo'))
    
    responsable_administrativo_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial administrativo (Fase: Cierre)"))
    responsable_administrativo_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable administrativo'))
    
    responsable_actual_id = models.IntegerField(null=True, blank=True, help_text=_("ID referencial del responsable actual"))
    responsable_actual_nombre = models.CharField(max_length=150, blank=True, help_text=_('Snapshot responsable actual'))

    # --- PROVEEDOR (Snapshot - Zero-Coupling) ---
    proveedor_id = models.IntegerField(
        _('ID Proveedor'), null=True, blank=True, 
        help_text=_("ID referencial del sistema de proveedores (Soft Reference)")
    )
    proveedor_nombre = models.CharField(
        _('Nombre Proveedor'), max_length=200, blank=True, 
        help_text=_("Snapshot del nombre del proveedor para evitar FK")
    )

    # --- DOCUMENTACIoN ---
    contrato_archivo = models.FileField(upload_to='proyectos/contratos/', null=True, blank=True)
    acta_inicio_archivo = models.FileField(upload_to='proyectos/actas/', null=True, blank=True)
    cronograma_archivo = models.FileField(upload_to='proyectos/cronogramas/', null=True, blank=True)
    
    fecha_inicio = models.DateField(_('Fecha de Inicio'), null=True, blank=True)
    fecha_fin_estimada = models.DateField(_('Fecha Fin Estimada'), null=True, blank=True)
    
    # --- INDICADORES FINANCIEROS (Modelo Anemico) ---
    costo_mano_obra_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py'))
    costo_materiales_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py'))
    costo_gastos_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py -- suma de DocumentoSoporte.subtotal asociados (GASTOS_PROYECTOS_01)'))
    utilidad_estimada = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Calculado por services.py'))
    margen_rentabilidad = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text=_('Calculado por services.py'))

    # --- INDICADORES PLANEADOS (v3.5.2 - Presupuesto Manual) ---
    costo_planeado_total = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('Suma de ItemPresupuestoProyecto - Zero Waste cache'))
    utilidad_planeada = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text=_('valor_contrato - costo_planeado_total'))
    margen_planeado = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text=_('utilidad_planeada / valor_contrato * 100'))

    # --- ENTREGABLES FINALES ---
    porcentaje_avance = models.PositiveIntegerField(_('Porcentaje Avance'), default=0)
    fecha_cierre_real = models.DateField(_('Fecha Cierre Real'), null=True, blank=True)
    acta_entrega_archivo = models.FileField(upload_to='proyectos/entregas/', null=True, blank=True)
    informe_final_archivo = models.FileField(upload_to='proyectos/finales/', null=True, blank=True)

    # --- ESTADO ---
    fase_actual = models.CharField(_('Fase Actual'), max_length=20, choices=FASES, default='BORRADOR')
    estado_tarea = models.CharField(_('Estado de Tarea'), max_length=20, choices=ESTADO_TAREA, default='PENDIENTE')

    # Sede: vinculacion para indicadores y KPIs por sede (DT-SEDE-03).
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos',
        verbose_name=_('Sede'),
        help_text=_('Sede de la empresa donde se ejecuta el proyecto. '
                    'Opcional: si no se asigna aplica a toda la empresa.'),
        db_index=True,
    )

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
            # v3.5: Los indices base (empresa, created_at) vienen de SintelTenantBaseModel.
            # Solo anadimos indices especificos de la logica de negocio de Proyectos.
            models.Index(fields=["empresa", "fase_actual"]),
            models.Index(fields=["empresa", "cliente_id"]),
            models.Index(fields=["responsable_actual_id"]),
            models.Index(fields=["proveedor_id"]),
        ]

    @property
    def movimiento_referencia(self):
        if not self.movimiento_inventario_uuid:
            return None
        try:
            from apps.tenant.inventario.services.selectors import MovimientoInventarioSelector
            mov = MovimientoInventarioSelector.get_detail(
                empresa_id=self.empresa_id,
                movimiento_uuid=self.movimiento_inventario_uuid
            )
            item_nombre = ""
            item_codigo = ""
            item_tipo = ""
            if mov.producto:
                item_nombre = mov.producto.nombre
                item_codigo = mov.producto.codigo
                item_tipo = "PRODUCTO"
            elif mov.activo_fijo:
                item_nombre = mov.activo_fijo.nombre
                item_codigo = mov.activo_fijo.codigo
                item_tipo = "ACTIVO_FIJO"
            return {
                'tipo': mov.tipo,
                'tipo_display': mov.get_tipo_display(),
                'item_tipo': item_tipo,
                'item_nombre': item_nombre,
                'item_codigo': item_codigo,
                'cantidad': float(mov.cantidad or 0),
            }
        except Exception:
            return None

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class DocumentoProyecto(SintelTenantBaseModel):
    """
    Expediente documental del proyecto (Ciclo de Vida Controlado v4.0).

    Un proyecto puede tener multiples documentos por tipo a lo largo de su
    ciclo de vida. Para los tipos de "unico vigente" (todos salvo
    DOCUMENTO_EJECUCION), subir uno nuevo del mismo tipo desactiva
    (activo=False) el anterior en la misma transaccion -- nunca se duplica
    silenciosamente el requisito de un gate de fase, y el archivo viejo se
    conserva (no se borra fisicamente).

    Archivo almacenado en `documentos_storage` (PRIVATE_MEDIA_ROOT), NUNCA en
    MEDIA_ROOT -- nginx sirve /media/ publicamente sin autenticacion, y estos
    documentos (ordenes de compra, autorizaciones, actas) son mas sensibles
    que el resto de archivos del sistema. Solo se sirven via el endpoint de
    descarga autenticado que valida empresa_id + proyecto_id + uuid.
    """
    class TipoDocumento(models.TextChoices):
        ORDEN_COMPRA = 'ORDEN_COMPRA', _('Orden de Compra')
        ORDEN_PEDIDO = 'ORDEN_PEDIDO', _('Orden de Pedido')
        AUTORIZACION = 'AUTORIZACION', _('Autorizacion')
        COTIZACION_APROBADA = 'COTIZACION_APROBADA', _('Cotizacion Aprobada')
        ACTA_INICIO = 'ACTA_INICIO', _('Acta de Inicio')
        CRONOGRAMA = 'CRONOGRAMA', _('Cronograma')
        DOCUMENTO_EJECUCION = 'DOCUMENTO_EJECUCION', _('Documento de Ejecucion')
        ACTA_ENTREGA = 'ACTA_ENTREGA', _('Acta de Entrega')
        INFORME_FINAL = 'INFORME_FINAL', _('Informe Final')

    # Tipos que admiten multiples documentos activos simultaneamente. El resto
    # son de "unico vigente": subir uno nuevo desactiva el anterior.
    TIPOS_MULTIPLES = {TipoDocumento.DOCUMENTO_EJECUCION}

    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name=_('Proyecto'),
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='documentos_proyecto',
        verbose_name=_('Empresa'),
        help_text=_('DSV: valida que el documento pertenezca al tenant'),
    )

    fase = models.CharField(
        _('Fase'),
        max_length=20,
        choices=Proyecto.FASES,
        help_text=_('Fase del ciclo de vida a la que corresponde este documento'),
    )
    tipo_documento = models.CharField(
        _('Tipo de Documento'),
        max_length=30,
        choices=TipoDocumento.choices,
    )
    nombre = models.CharField(_('Nombre'), max_length=200, blank=True)
    archivo = models.FileField(
        _('Archivo'),
        upload_to='proyectos/documentos/%Y/%m/',
        storage=documentos_storage,
    )
    fecha_documento = models.DateField(_('Fecha del Documento'), null=True, blank=True)
    observaciones = models.TextField(_('Observaciones'), blank=True)
    subido_por = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_proyecto_subidos',
        verbose_name=_('Subido por'),
    )
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Documento de Proyecto')
        verbose_name_plural = _('Documentos de Proyecto')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', 'proyecto', 'tipo_documento', 'activo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.proyecto.nombre}"


class HistorialFaseProyecto(SintelTenantBaseModel):
    """
    Historial append-only de cambios de fase del proyecto (Ciclo de Vida
    Controlado v4.0). Clon del patron ya probado en produccion:
    apps.tenant.cotizaciones.models.CotizacionHistorialEstado.

    Se crea EXCLUSIVAMENTE dentro de la misma transaccion atomica que el
    cambio de fase real (ver services/business_service.py::cambiar_fase_proyecto).
    No existe ningun update/delete expuesto para esta tabla en el Service
    Layer -- solo creacion y lectura.
    """
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='historial_fases',
        verbose_name=_('Proyecto'),
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='historial_fases_proyecto',
        verbose_name=_('Empresa'),
        help_text=_('DSV: valida que el historial pertenezca al tenant'),
    )

    fase_anterior = models.CharField(_('Fase Anterior'), max_length=20, blank=True, default='')
    fase_nueva = models.CharField(_('Fase Nueva'), max_length=20)
    usuario = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cambios_fase_proyecto',
        verbose_name=_('Usuario'),
    )
    motivo = models.TextField(_('Motivo'), blank=True, default='')

    class Meta:
        verbose_name = _('Historial de Fase')
        verbose_name_plural = _('Historial de Fases')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', 'proyecto', '-created_at']),
        ]

    def __str__(self):
        return f"{self.proyecto.nombre}: {self.fase_anterior} -> {self.fase_nueva}"


class AsignacionPersonal(SintelTenantBaseModel):
    """
    Registro de Talento Humano asignado al proyecto.
    Desacoplado del modulo de Empleados.
    """
    ROLES = [
        ('TECNICO', _('Tecnico Operativo')),
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
    
    fecha_asignacion = models.DateField(_('Fecha Asignacion'))
    fecha_fin_asignacion = models.DateField(_('Fecha Fin Asignacion'), null=True, blank=True)
    
    # --- Financieros ---
    horas_totales_registradas = models.DecimalField(_('Horas Totales'), max_digits=10, decimal_places=2, default=0)
    costo_hora = models.DecimalField(_('Costo por Hora'), max_digits=12, decimal_places=2, default=0)
    costo_total_asignacion = models.DecimalField(_('Costo Total'), max_digits=15, decimal_places=2, default=0)

    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _("Asignacion Personal")
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
    proveedor_id = models.IntegerField(_('ID Proveedor'), null=True, blank=True, help_text=_("ID referencial si existe modulo de proveedores"))
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
    Detalle de linea de pedido. Estrictamente datos, sin relaciones a Inventario.
    """
    pedido = models.ForeignKey(PedidoProyecto, on_delete=models.CASCADE, related_name='items')
    
    # --- Referencia Desacoplada ---
    material_ref = models.CharField(_('Referencia/SKU'), max_length=50, blank=True, help_text=_("SKU o ID del material referencial"))
    nombre_material = models.CharField(_('Nombre Material'), max_length=200)
    
    cantidad = models.DecimalField(_('Cantidad'), max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(_('Unidad de Medida'), max_length=20)
    precio_unitario = models.DecimalField(_('Precio Unitario'), max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = _("Item de Pedido")
        verbose_name_plural = _("Items de Pedido")
        constraints = [
            models.UniqueConstraint(
                fields=['pedido', 'material_ref'],
                condition=models.Q(material_ref__gt=''),
                name='uniq_itempedido_pedido_material_ref'
            )
        ]
        indexes = [
            models.Index(fields=["pedido"]),
            models.Index(fields=["material_ref"]),
        ]

    def __str__(self):
        return f"{self.cantidad} {self.unidad_medida} - {self.nombre_material}"


class ItemPresupuestoProyecto(SintelTenantBaseModel):
    """
    Linea de Presupuesto Manual para Fase 2 (Planeacion).
    Permite desglosar costos planeados por categoria.

    Patron: 1-a-N sobre Proyecto.
    Service Layer gestiona recalculo de totales en proyecto padre.
    DSV (Double Semantic Verification) valida empresa_id.
    """
    class Categoria(models.TextChoices):
        MANO_OBRA = 'MANO_OBRA', _('Mano de Obra')
        EQUIPOS = 'EQUIPOS', _('Equipos')
        MATERIALES = 'MATERIALES', _('Materiales')

    # WARNING: [ARQ-A1] UUID Lookup Field (AGENTS.md §25)
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # --- Relaciones ---
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='items_presupuesto',
        verbose_name=_('Proyecto')
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='items_presupuesto',
        verbose_name=_('Empresa'),
        help_text=_('DSV: valida que item pertenezca al tenant')
    )

    # --- Datos del item ---
    categoria = models.CharField(
        _('Categoria'),
        max_length=20,
        choices=Categoria.choices,
        help_text=_('Mano de Obra, Equipos o Materiales')
    )
    descripcion = models.CharField(
        _('Descripcion'),
        max_length=300,
        blank=True,
        help_text=_('Ej: Instalacion de cableado, Alquiler de grua, etc.')
    )
    cantidad = models.DecimalField(
        _('Cantidad'),
        max_digits=10,
        decimal_places=2,
        default=1,
        help_text=_('Cantidad planeada')
    )
    valor_unitario = models.DecimalField(
        _('Valor Unitario'),
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text=_('Valor por unidad')
    )
    subtotal = models.DecimalField(
        _('Subtotal'),
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text=_('cantidad x valor_unitario (calculado en service layer)')
    )

    class Meta:
        verbose_name = _('Item de Presupuesto')
        verbose_name_plural = _('items de Presupuesto')
        ordering = ['categoria', 'id']
        indexes = [
            models.Index(fields=['proyecto']),
            models.Index(fields=['empresa']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.descripcion} ({self.cantidad})"


class TareaDiariaProyecto(SintelTenantBaseModel):
    """
    Seguimiento de Tareas Diarias (Fase 3 - Ejecucion) v3.5.4

    Permite registrar tareas por periodo (fecha_inicio a fecha_fin) asociadas a un proyecto.
    Validaciones criticas:
    - fecha_inicio <= fecha_fin (rango coherente)
    - [fecha_inicio, fecha_fin] DEBE intersectar con [proyecto.fecha_inicio, proyecto.fecha_fin_estimada]
    - Si proyecto.fase_actual == 'CIERRE', tareas son inmutables (read-only)
    - DSV: empresa_id DEBE coincidir con proyecto.empresa_id

    Patron: 1-a-N sobre Proyecto.
    Service Layer gestiona validaciones y persistencia.
    """
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', _('Pendiente')
        EN_PROCESO = 'EN_PROCESO', _('En Proceso')
        COMPLETADA = 'COMPLETADA', _('Completada')
        CANCELADA = 'CANCELADA', _('Cancelada')

    class Prioridad(models.TextChoices):
        BAJA = 'BAJA', _('Baja')
        NORMAL = 'NORMAL', _('Normal')
        ALTA = 'ALTA', _('Alta')

    # WARNING: [ARQ-A1] UUID Lookup Field (AGENTS.md §25)
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # --- Relaciones ---
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='tareas_diarias',
        verbose_name=_('Proyecto')
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='tareas_diarias',
        verbose_name=_('Empresa'),
        help_text=_('DSV: valida que tarea pertenezca al tenant')
    )

    # --- Datos de la Tarea ---
    fecha_inicio = models.DateField(
        _('Fecha Inicio'),
        help_text=_('Primer dia de la tarea. DEBE estar entre fecha_inicio y fecha_fin_estimada del proyecto')
    )
    fecha_fin = models.DateField(
        _('Fecha Fin'),
        help_text=_('ultimo dia de la tarea. DEBE ser >= fecha_inicio y dentro del rango del proyecto')
    )
    titulo = models.CharField(
        _('Titulo'),
        max_length=200,
        help_text=_('Descripcion breve de la tarea')
    )
    descripcion = models.TextField(
        _('Descripcion'),
        blank=True,
        help_text=_('Detalles completos de la tarea')
    )
    estado = models.CharField(
        _('Estado'),
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    prioridad = models.CharField(
        _('Prioridad'),
        max_length=20,
        choices=Prioridad.choices,
        default=Prioridad.NORMAL
    )

    # --- Seguimiento ---
    asignado_a = models.CharField(
        _('Asignado a'),
        max_length=150,
        blank=True,
        help_text=_('Snapshot del nombre del empleado (no FK)')
    )
    notas_progreso = models.TextField(
        _('Notas de Progreso'),
        blank=True,
        help_text=_('Actualizaciones diarias sobre la ejecucion')
    )

    # --- Bitacora de Ejecucion (Ciclo de Vida Controlado v4.0) ---
    avance = models.PositiveIntegerField(
        _('Avance (%)'),
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
        help_text=_('Porcentaje de avance reportado para esta tarea (0-100), opcional')
    )
    bloqueos = models.TextField(
        _('Bloqueos'),
        blank=True,
        default='',
        help_text=_('Impedimentos u obstaculos reportados en el dia')
    )
    incidencias = models.TextField(
        _('Incidencias'),
        blank=True,
        default='',
        help_text=_('Incidentes o eventos relevantes reportados en el dia')
    )

    class Meta:
        verbose_name = _('Tarea Diaria')
        verbose_name_plural = _('Tareas Diarias')
        ordering = ['fecha_inicio', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['proyecto', 'fecha_inicio', 'titulo'],
                name='unique_tarea_por_proyecto_fecha_inicio_titulo'
            )
        ]
        indexes = [
            models.Index(fields=['proyecto', 'fecha_inicio']),
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['fecha_inicio']),
        ]

    def __str__(self):
        rango = f"{self.fecha_inicio}" if self.fecha_inicio == self.fecha_fin else f"{self.fecha_inicio} - {self.fecha_fin}"
        return f"[{rango}] {self.titulo} - {self.get_estado_display()}"

    @property
    def fecha(self):
        """Alias legacy de lectura para integraciones anteriores a fecha_inicio/fecha_fin."""
        return self.fecha_inicio


class TareaCorta(SintelTenantBaseModel):
    """
    Seguimiento de Tareas Cortas v3.10.0

    Permite registrar tareas de corta duracion dirigidas a un cliente y
    asignadas a un empleado.
    Validaciones criticas:
    - fecha_inicio <= fecha_fin (rango coherente)
    - DSV: empresa_id DEBE coincidir con cliente.empresa_id y empleado.empresa_id
    """
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', _('Pendiente')
        EN_PROCESO = 'EN_PROCESO', _('En Proceso')
        COMPLETADA = 'COMPLETADA', _('Completada')
        CANCELADA = 'CANCELADA', _('Cancelada')

    class Prioridad(models.TextChoices):
        BAJA = 'BAJA', _('Baja')
        NORMAL = 'NORMAL', _('Normal')
        ALTA = 'ALTA', _('Alta')

    # UUID Lookup Field (AGENTS.md)
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # --- Relaciones ---
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='tareas_cortas',
        verbose_name=_('Empresa'),
        help_text=_('DSV: valida que tarea pertenezca al tenant')
    )
    empleado = models.ForeignKey(
        'tenant_empleados.Empleado',
        on_delete=models.PROTECT,
        related_name='tareas_cortas',
        verbose_name=_('Empleado'),
        null=True,
        blank=True,
        help_text=_('Empleado asignado a la tarea corta')
    )
    cliente = models.ForeignKey(
        'tenant_clientes.Cliente',
        on_delete=models.SET_NULL,
        related_name='tareas_cortas',
        verbose_name=_('Cliente'),
        null=True,
        blank=True,
        help_text=_('Cliente destino de la tarea corta')
    )

    # --- Datos de la Tarea ---
    fecha_inicio = models.DateField(
        _('Fecha Inicio'),
        help_text=_('Primer dia de la tarea.')
    )
    fecha_fin = models.DateField(
        _('Fecha Fin'),
        help_text=_('Ultimo dia de la tarea. DEBE ser >= fecha_inicio')
    )
    titulo = models.CharField(
        _('Titulo'),
        max_length=200,
        help_text=_('Descripcion breve de la tarea')
    )
    descripcion = models.TextField(
        _('Descripcion'),
        blank=True,
        help_text=_('Detalles completos de la tarea')
    )
    estado = models.CharField(
        _('Estado'),
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    prioridad = models.CharField(
        _('Prioridad'),
        max_length=20,
        choices=Prioridad.choices,
        default=Prioridad.NORMAL
    )
    notas_progreso = models.TextField(
        _('Notas de Progreso'),
        blank=True,
        help_text=_('Notas de avance de la tarea')
    )

    class Meta:
        verbose_name = _('Tarea Corta')
        verbose_name_plural = _('Tareas Cortas')
        ordering = ['fecha_inicio', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['cliente', 'empleado', 'fecha_inicio', 'titulo'],
                name='unique_tarea_corta_por_cliente_empleado_fecha_titulo'
            )
        ]
        indexes = [
            models.Index(fields=['cliente', 'fecha_inicio']),
            models.Index(fields=['empleado', 'fecha_inicio']),
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['fecha_inicio']),
        ]

    def __str__(self):
        rango = f"{self.fecha_inicio}" if self.fecha_inicio == self.fecha_fin else f"{self.fecha_inicio} - {self.fecha_fin}"
        return f"[{rango}] {self.titulo} - {self.get_estado_display()}"

