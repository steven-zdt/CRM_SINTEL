"""
Modelos de Requisiciones de Compra - SINTEL FSD.

Submodulo de apps.tenant.compras (app Django propia, app_label
'tenant_compras_requisiciones', ver apps.py) que modela el documento de
ORIGEN de una compra: la necesidad + justificacion + contexto organizacional
que antecede a una OrdenCompra. Ver docs/compras/REQUISICIONES_DESIGN.md.

Decisiones de diseno relevantes (no repetir el razonamiento fuera de aqui):
- Sin campo `centro_costo`: no existe ninguna entidad CentroCosto real en el
  proyecto (ver docs/compras/REQUISITION_BASELINE.md #2) -- se usa `proyecto`
  (FK real a tenant_proyectos.Proyecto) como agrupador, igual que el resto
  del sistema ya lo trata (Proyecto.factura_costo, MovimientoContable.
  centro_costo_id sin FK).
- RequisicionCompra hereda SedeAwareModel con `sede` endurecida a NOT NULL
  desde el inicio (tabla nueva, sin datos historicos -- mismo patron que
  RecepcionCompra en apps.tenant.compras.models, a diferencia de OrdenCompra
  que necesito nullable->backfill->harden por tener filas preexistentes).
"""

import uuid as uuid_module
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SedeAwareModel, SintelTenantBaseModel

# Storage privado para archivos adjuntos de Requisicion (cotizaciones/facturas
# externas aun no reconciliadas, soportes, etc.) -- mismo patron que
# apps.tenant.proyectos.models.documentos_storage: nginx sirve /media/
# publicamente sin autenticacion, por lo que NUNCA se usa el storage por
# defecto (MEDIA_ROOT) para documentos de negocio.
requisiciones_storage = FileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT))


def _hoy():
    """Mismo patron de default explicito que Cotizacion._hoy() -- evita que
    auto_now_add ignore un valor calculado por el Service Layer.

    `timezone.localdate()`, NUNCA `timezone.now().date()` -- bug real
    encontrado en vivo (2026-09-26): con `TIME_ZONE='America/Bogota'`
    (UTC-5) y `USE_TZ=True`, `timezone.now()` es un datetime en UTC:
    `.date()` sobre ese datetime toma la fecha CALENDARIO DE UTC, que ya es
    el dia siguiente al de Bogota entre las 19:00 y las 23:59 hora local
    (ventana de 5 horas, UTC 00:00-05:00). En esa ventana, una Requisicion
    creada con `fecha_necesidad=hoy()` (fecha local real) violaba el check
    constraint `requisicion_compra_fecha_necesidad_gte_solicitud` porque
    `fecha_solicitud` (este default) quedaba UN DIA ADELANTADO. `timezone.
    localdate()` devuelve la fecha ya convertida a `settings.TIME_ZONE`."""
    return timezone.localdate()


def _requisicion_adjunto_upload_path(instance, filename):
    return f"compras/requisiciones/{instance.requisicion_id}/{filename}"


class RequisicionCompra(SedeAwareModel):
    """
    Documento de origen/justificacion de una compra: quien la solicita, para
    que, con que urgencia, y bajo que contexto organizacional -- ANTES de que
    exista ninguna OrdenCompra. No es un "ERP dentro del ERP": no duplica
    datos fiscales (Factura), comerciales (Cotizacion) ni de ejecucion
    (Proyecto) -- solo referencia lo que ya existe (ver SSoT matrix en el
    plan original, PLAN_IMPLEMENTACION_REQUISICIONES_COMPRAS.md #42).
    """

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", _("Borrador")
        PENDIENTE_APROBACION = "PENDIENTE_APROBACION", _("Pendiente de Aprobacion")
        APROBADA = "APROBADA", _("Aprobada")
        RECHAZADA = "RECHAZADA", _("Rechazada")
        CANCELADA = "CANCELADA", _("Cancelada")
        EN_PROCESO_COMPRA = "EN_PROCESO_COMPRA", _("En Proceso de Compra")
        PARCIALMENTE_ATENDIDA = "PARCIALMENTE_ATENDIDA", _("Parcialmente Atendida")
        ATENDIDA = "ATENDIDA", _("Atendida")

    class Tipo(models.TextChoices):
        BIEN = "BIEN", _("Bien")
        SERVICIO = "SERVICIO", _("Servicio")
        MIXTO = "MIXTO", _("Mixto")

    class Prioridad(models.TextChoices):
        BAJA = "BAJA", _("Baja")
        MEDIA = "MEDIA", _("Media")
        ALTA = "ALTA", _("Alta")
        URGENTE = "URGENTE", _("Urgente")

    # Tabla nueva sin datos historicos: se endurece sede a NOT NULL desde el
    # inicio, mismo criterio documentado en RecepcionCompra
    # (apps.tenant.compras.models).
    sede = models.ForeignKey(
        "empresa.Sede",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_related",
        verbose_name=_("Sede"),
        help_text=_("Sede solicitante (Contexto Organizacional). Obligatoria."),
        null=False,
        blank=False,
        db_index=True,
    )

    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        db_index=True,
        editable=False,
    )

    # PLAN_NUEVA_REQUISICION_NUMERACION_CLIENTE_COTIZACIONES.md Fase B:
    # reemplaza el REQ-%06d hardcoded (antes armado por
    # RequisicionCompraCRUDService.asignar_siguiente_numero(), retirado) por
    # el mismo motor de PlantillaOrdenCompra (select_for_update + F()+1) que
    # ya usa OrdenCompra, filtrado por tipo_documento=REQUISICION. `null=True`
    # a nivel de BD -- hay 30 filas historicas reales (tenant `admin`, previas
    # a esta Fase) sin plantilla; la obligatoriedad para Requisiciones NUEVAS
    # se aplica en el Service Layer/serializer, nunca se inventa un valor
    # retroactivo para el historico (documento original #30).
    plantilla = models.ForeignKey(
        "tenant_compras.PlantillaOrdenCompra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requisiciones_compra",
        verbose_name=_("Plantilla de Numeración"),
    )

    numero_documento = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Numero de Documento"),
        help_text=_("Formato definido por la Plantilla de Numeración, autoasignado."),
    )

    consecutivo = models.IntegerField(
        db_index=True,
        verbose_name=_("Consecutivo"),
    )

    fecha_solicitud = models.DateField(default=_hoy, verbose_name=_("Fecha de Solicitud"))
    fecha_necesidad = models.DateField(verbose_name=_("Fecha en que se Necesita"))

    solicitante = models.ForeignKey(
        "perfil.TenantProfile",
        on_delete=models.PROTECT,
        related_name="requisiciones_solicitadas",
        verbose_name=_("Solicitante"),
    )

    responsable_aprobacion = models.ForeignKey(
        "perfil.TenantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisiciones_por_aprobar",
        verbose_name=_("Responsable de Aprobacion"),
        help_text=_(
            "Asignado al enviar a aprobacion. Opcional: puede aprobar cualquier admin del tenant."
        ),
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.MIXTO,
        verbose_name=_("Tipo"),
    )

    prioridad = models.CharField(
        max_length=20,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        db_index=True,
        verbose_name=_("Prioridad"),
    )

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
        verbose_name=_("Estado"),
    )

    justificacion = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Justificacion"),
        help_text=_("Obligatoria para salir de BORRADOR (validado en el Service Layer)."),
    )

    observaciones = models.TextField(blank=True, default="", verbose_name=_("Observaciones"))

    # PLAN_NUEVA_REQUISICION_NUMERACION_CLIENTE_COTIZACIONES.md Fase C: FK
    # real (no snapshot) -- a diferencia de Proyecto.cliente_id/cliente_nombre
    # (Zero-Coupling deliberado, "para evitar FK", apps.tenant.proyectos.
    # models.py:84-91), RequisicionCompra YA usa FKs reales para
    # sede/solicitante/proyecto/area, asi que un FK real a Cliente es
    # consistente con el patron propio de ESTE modelo. `null=True` por el
    # mismo motivo que `plantilla` arriba (30 filas historicas reales sin
    # cliente); obligatorio solo en Service Layer/serializer para creacion.
    cliente = models.ForeignKey(
        "tenant_clientes.Cliente",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requisiciones_compra",
        verbose_name=_("Cliente"),
    )

    # Agrupador real (ver docstring del modulo): cubre el caso comun de 0..1
    # proyecto por requisicion. N proyectos por requisicion queda DEFERRED
    # (ver docs/compras/REQUISICIONES_DESIGN.md #2) hasta evidencia real.
    proyecto = models.ForeignKey(
        "tenant_proyectos.Proyecto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisiciones_compra",
        verbose_name=_("Proyecto"),
    )

    moneda = models.CharField(max_length=3, default="COP", verbose_name=_("Moneda"))

    subtotal_estimado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Subtotal Estimado"),
    )
    impuestos_estimados = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Impuestos Estimados"),
    )
    total_estimado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Total Estimado"),
    )

    class Meta:
        verbose_name = _("Requisicion de Compra")
        verbose_name_plural = _("Requisiciones de Compra")
        ordering = ["-fecha_solicitud", "-consecutivo"]
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "fecha_solicitud"]),
            # Meta.indexes de la clase concreta NO fusiona con el de
            # SedeAwareModel (hallazgo real ya documentado en
            # apps.tenant.compras.models.OrdenCompra) -- repetir explicito.
            models.Index(fields=["empresa", "sede"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero_documento"],
                name="unique_requisicion_compra_numero_documento",
            ),
            models.CheckConstraint(
                check=models.Q(fecha_necesidad__gte=models.F("fecha_solicitud")),
                name="requisicion_compra_fecha_necesidad_gte_solicitud",
            ),
        ]

    def __str__(self):
        return f"{self.numero_documento} ({self.get_estado_display()})"


class RequisicionCompraItem(SintelTenantBaseModel):
    """Linea de una RequisicionCompra. cantidad_ordenada/cancelada se acumulan
    transaccionalmente desde OrdenCompra (mismo patron que
    ItemOrdenCompra.cantidad_recibida en apps.tenant.compras.models)."""

    class TipoItem(models.TextChoices):
        BIEN = "BIEN", _("Bien")
        SERVICIO = "SERVICIO", _("Servicio")

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    requisicion = models.ForeignKey(
        RequisicionCompra,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Requisicion"),
    )

    descripcion = models.CharField(max_length=255, verbose_name=_("Descripcion"))

    item_inventario_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Soft reference a Producto o Servicio del catalogo de inventario, opcional."),
    )

    tipo_item = models.CharField(
        max_length=20, choices=TipoItem.choices, verbose_name=_("Tipo de Item")
    )

    cantidad_solicitada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Cantidad Solicitada"),
    )
    unidad_medida = models.CharField(
        max_length=20, default="UND", verbose_name=_("Unidad de Medida")
    )

    valor_unitario_estimado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Valor Unitario Estimado"),
    )
    porcentaje_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Porcentaje IVA"),
    )
    valor_iva_estimado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Valor IVA Estimado"),
    )
    subtotal_estimado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Subtotal Estimado"),
    )
    total_estimado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Total Estimado"),
    )

    cantidad_aprobada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Cantidad Aprobada"),
        help_text=_(
            "Igual a cantidad_solicitada al aprobar la requisicion, salvo ajuste explicito."
        ),
    )
    cantidad_ordenada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Cantidad Ordenada"),
        help_text=_("Acumulado desde ItemOrdenCompra generados a partir de este item."),
    )
    cantidad_cancelada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Cantidad Cancelada"),
    )

    observaciones = models.TextField(blank=True, default="", verbose_name=_("Observaciones"))

    class Meta:
        verbose_name = _("Item de Requisicion de Compra")
        verbose_name_plural = _("Items de Requisicion de Compra")
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    cantidad_aprobada__gte=models.F("cantidad_ordenada")
                    + models.F("cantidad_cancelada")
                ),
                name="req_item_ordenada_mas_cancelada_lte_aprobada",
            ),
        ]

    @property
    def cantidad_pendiente(self):
        return self.cantidad_aprobada - self.cantidad_ordenada - self.cantidad_cancelada

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad_solicitada}"


class RequisicionDocumento(SintelTenantBaseModel):
    """Evidencia/archivo adjunto a una Requisicion. `documento_uuid` es una
    referencia blanda (sin FK) al objeto real una vez reconciliado -- soporta
    el caso de documentos externos (ej. factura de proveedor) que llegan
    antes de existir como registro real en Facturas (ver plan original #8)."""

    class Tipo(models.TextChoices):
        COTIZACION = "COTIZACION", _("Cotizacion")
        FACTURA = "FACTURA", _("Factura")
        PROYECTO = "PROYECTO", _("Proyecto")
        ORDEN_INTERNA = "ORDEN_INTERNA", _("Orden Interna")
        DOCUMENTO_SOPORTE = "DOCUMENTO_SOPORTE", _("Documento Soporte")
        OTRO = "OTRO", _("Otro")

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    requisicion = models.ForeignKey(
        RequisicionCompra,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name=_("Requisicion"),
    )

    tipo = models.CharField(
        max_length=20, choices=Tipo.choices, verbose_name=_("Tipo de Documento")
    )
    nombre = models.CharField(max_length=255, verbose_name=_("Nombre"))
    numero_referencia = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Numero de Referencia"),
        help_text=_("Ej: numero de factura externa aun no reconciliada (FE-12345)."),
    )
    documento_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("UUID del Documento Real"),
        help_text=_(
            "Soft reference al UUID real (Cotizacion/Factura/Proyecto/OrdenCompra) una vez reconciliado."
        ),
    )
    archivo = models.FileField(
        upload_to=_requisicion_adjunto_upload_path,
        storage=requisiciones_storage,
        blank=True,
        verbose_name=_("Archivo"),
    )
    descripcion = models.TextField(blank=True, default="", verbose_name=_("Descripcion"))

    class Meta:
        verbose_name = _("Documento de Requisicion")
        verbose_name_plural = _("Documentos de Requisicion")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "requisicion"]),
        ]

    def __str__(self):
        return f"{self.tipo}: {self.nombre}"


class RequisicionCotizacion(SintelTenantBaseModel):
    """Vinculo de trazabilidad (no de negocio) entre una Requisicion y una
    Cotizacion COMERCIAL A CLIENTE ya existente (ver hallazgo en
    docs/compras/REQUISITION_BASELINE.md #3.2: Cotizacion en este ERP es
    exclusivamente cliente, nunca proveedor -- este vinculo es solo de
    contexto, ej. "esta compra es para atender la venta cotizada X")."""

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    requisicion = models.ForeignKey(
        RequisicionCompra,
        on_delete=models.CASCADE,
        related_name="cotizaciones_vinculadas",
        verbose_name=_("Requisicion"),
    )
    cotizacion = models.ForeignKey(
        "tenant_cotizaciones.Cotizacion",
        on_delete=models.PROTECT,
        related_name="requisiciones_vinculadas",
        verbose_name=_("Cotizacion"),
    )
    tipo_relacion = models.CharField(
        max_length=30, blank=True, default="CONTEXTO", verbose_name=_("Tipo de Relacion")
    )
    es_principal = models.BooleanField(default=False, verbose_name=_("Es Principal"))
    observacion = models.TextField(blank=True, default="", verbose_name=_("Observacion"))

    class Meta:
        verbose_name = _("Cotizacion Vinculada a Requisicion")
        verbose_name_plural = _("Cotizaciones Vinculadas a Requisicion")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["requisicion", "cotizacion"],
                name="unique_requisicion_cotizacion",
            ),
        ]

    def __str__(self):
        return f"{self.requisicion_id} <-> Cotizacion {self.cotizacion_id}"


class RequisicionFactura(SintelTenantBaseModel):
    """Vinculo de trazabilidad entre una Requisicion y una Factura real ya
    persistida (SSoT fiscal DIAN, sin duplicar CUFE/totales/estado -- ver
    docs/compras/REQUISITION_BASELINE.md #3.3)."""

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    requisicion = models.ForeignKey(
        RequisicionCompra,
        on_delete=models.CASCADE,
        related_name="facturas_vinculadas",
        verbose_name=_("Requisicion"),
    )
    factura = models.ForeignKey(
        "facturas.Factura",
        on_delete=models.PROTECT,
        related_name="requisiciones_vinculadas",
        verbose_name=_("Factura"),
    )
    tipo_relacion = models.CharField(
        max_length=30, blank=True, default="EVIDENCIA", verbose_name=_("Tipo de Relacion")
    )
    es_principal = models.BooleanField(default=False, verbose_name=_("Es Principal"))
    observacion = models.TextField(blank=True, default="", verbose_name=_("Observacion"))

    class Meta:
        verbose_name = _("Factura Vinculada a Requisicion")
        verbose_name_plural = _("Facturas Vinculadas a Requisicion")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["requisicion", "factura"],
                name="unique_requisicion_factura",
            ),
        ]

    def __str__(self):
        return f"{self.requisicion_id} <-> Factura {self.factura_id}"


class RequisicionHistorialEstado(SintelTenantBaseModel):
    """Historial append-only de transiciones de estado. Mismo patron que
    CotizacionHistorialEstado (apps.tenant.cotizaciones.models) -- no existe
    infraestructura transversal reutilizable en el proyecto para esto (ya
    auditado en esa mision anterior). Solo `crear_entrada` en el Service
    Layer; ningun endpoint permite update/delete."""

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    requisicion = models.ForeignKey(
        RequisicionCompra,
        related_name="historial_estados",
        on_delete=models.CASCADE,
    )
    estado_anterior = models.CharField(max_length=30, blank=True, default="")
    estado_nuevo = models.CharField(max_length=30)
    usuario = models.ForeignKey(
        "perfil.TenantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    comentario = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = _("Historial de Estado de Requisicion")
        verbose_name_plural = _("Historiales de Estado de Requisicion")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "requisicion", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.requisicion_id}: {self.estado_anterior} -> {self.estado_nuevo}"
