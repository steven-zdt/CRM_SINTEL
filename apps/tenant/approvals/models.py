"""
Motor generico de Solicitudes de Aprobacion - SINTEL FSD.

App tenant propia (app_label 'tenant_approvals'), dominio independiente de
Compras/Requisiciones/Cotizaciones (ver PLAN_CENTRO_APROBACIONES_DASHBOARD_
COMPRAS.md #37: "Approval SSoT = workflow de aprobacion", distinto de los
dominios que aprueba). Fases 1-4 de ese plan: solo modelos + Service Layer,
sin API ni UI todavia (el enganche real con RequisicionCompra.
enviar_a_aprobacion() y el Centro de Aprobaciones del Dashboard son Fase 5+,
DEFERRED explicito -- ver docs/approvals/APPROVALS_DESIGN.md).

Decisiones de diseno relevantes (no repetir el razonamiento fuera de aqui):
- Registry explicito en services/business_service.py (TIPO_DOCUMENTO_REGISTRY),
  NUNCA GenericForeignKey -- riesgo de fuga cross-tenant auditado en el plan
  (#9) y evitado aqui a proposito: `objeto_uuid` es una soft-reference simple,
  resuelta siempre filtrando por empresa_id en el Service Layer.
- Sin FK real al documento aprobado (Requisicion/Cotizacion/OrdenCompra) --
  mismo patron de soft-reference que ya usa el resto del proyecto
  (RequisicionDocumento.documento_uuid, Factura.cotizacion_uuid, etc.).
"""

import uuid as uuid_module

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel


class SolicitudAprobacion(SintelTenantBaseModel):
    """Una solicitud de aprobacion sobre un documento de otro dominio
    (Requisicion por ahora; Cotizacion/OrdenCompra son extensiones futuras
    del registry, sin cambios a este modelo)."""

    class TipoDocumento(models.TextChoices):
        REQUISICION = "REQUISICION", _("Requisicion de Compra")
        # PLAN_AJUSTE_CICLO_PROYECTOS_FASE_1_VIABILIDAD_APROBACION: gate
        # INICIO -> PLANEACION de Proyectos. `objeto_uuid` = Proyecto.uuid.
        # Registry en apps/tenant/proyectos/services/inicio_service.py
        # (resolver/aprobar/rechazar/snapshot), enganchado en
        # TIPO_DOCUMENTO_REGISTRY de este mismo archivo mas abajo.
        PROYECTO_INICIO = "PROYECTO_INICIO", _("Inicio de Proyecto (Viabilidad)")

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", _("Pendiente")
        APROBADA = "APROBADA", _("Aprobada")
        RECHAZADA = "RECHAZADA", _("Rechazada")
        CANCELADA = "CANCELADA", _("Cancelada")

    class Prioridad(models.TextChoices):
        BAJA = "BAJA", _("Baja")
        MEDIA = "MEDIA", _("Media")
        ALTA = "ALTA", _("Alta")

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    tipo_documento = models.CharField(
        max_length=30,
        choices=TipoDocumento.choices,
        db_index=True,
        verbose_name=_("Tipo de Documento"),
    )
    objeto_uuid = models.UUIDField(
        db_index=True,
        verbose_name=_("Documento de Origen"),
        help_text=_(
            "Soft-reference al documento real (resuelto via registry + empresa_id, nunca GenericForeignKey)."
        ),
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        help_text=_(
            "Calculo de riesgo/prioridad real es responsabilidad del Dashboard (Fase 8, DEFERRED) -- aqui es solo un campo de datos."
        ),
    )
    solicitante = models.ForeignKey(
        "perfil.TenantProfile",
        on_delete=models.PROTECT,
        related_name="solicitudes_aprobacion_enviadas",
        verbose_name=_("Solicitante"),
    )
    aprobador = models.ForeignKey(
        "perfil.TenantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_aprobacion_decididas",
        verbose_name=_("Aprobador"),
    )
    fecha_envio = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de Envio"))
    fecha_decision = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Fecha de Decision")
    )
    motivo_rechazo = models.TextField(blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    snapshot_financiero = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Resumen de control al momento de enviar (valor, numero, tipo, documento origen, cotizacion, proyecto, cantidad de lineas, hash/version) -- usado para revalidar antes de aprobar, ver #13 del plan."
        ),
    )

    class Meta:
        verbose_name = _("Solicitud de Aprobacion")
        verbose_name_plural = _("Solicitudes de Aprobacion")
        ordering = ["-fecha_envio"]
        indexes = [
            models.Index(fields=["empresa", "estado", "-fecha_envio"]),
            models.Index(fields=["empresa", "tipo_documento", "objeto_uuid"]),
        ]
        constraints = [
            # Idempotencia estructural (ver tambien el chequeo en
            # ApprovalBusinessService.crear_solicitud): nunca 2 solicitudes
            # PENDIENTE simultaneas para el mismo documento. Postgres permite
            # UniqueConstraint con condition sobre un valor fijo del choice.
            models.UniqueConstraint(
                fields=["empresa", "tipo_documento", "objeto_uuid"],
                condition=models.Q(estado="PENDIENTE"),
                name="unique_solicitud_pendiente_por_documento",
            ),
        ]

    def __str__(self):
        return f"{self.tipo_documento}:{self.objeto_uuid} [{self.estado}]"


class SolicitudAprobacionHistorial(SintelTenantBaseModel):
    """Historial append-only de eventos de una SolicitudAprobacion. Mismo
    patron que RequisicionHistorialEstado (apps.tenant.compras.requisiciones.
    models) -- no existe infraestructura transversal reutilizable en el
    proyecto para esto (auditado, ver Fase 0 de esta mision). Solo
    `crear_entrada` en el Service Layer; ningun endpoint permite update/delete."""

    class Evento(models.TextChoices):
        CREADA = "CREADA", _("Creada")
        ENVIADA = "ENVIADA", _("Enviada")
        VISTA = "VISTA", _("Vista")
        APROBADA = "APROBADA", _("Aprobada")
        RECHAZADA = "RECHAZADA", _("Rechazada")
        CANCELADA = "CANCELADA", _("Cancelada")

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    solicitud = models.ForeignKey(
        SolicitudAprobacion,
        related_name="historial",
        on_delete=models.CASCADE,
    )
    evento = models.CharField(max_length=20, choices=Evento.choices)
    estado_anterior = models.CharField(max_length=20, blank=True, default="")
    estado_nuevo = models.CharField(max_length=20)
    usuario = models.ForeignKey(
        "perfil.TenantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    observacion = models.TextField(blank=True, default="")
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Historial de Solicitud de Aprobacion")
        verbose_name_plural = _("Historiales de Solicitud de Aprobacion")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "solicitud", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.solicitud_id}: {self.estado_anterior} -> {self.estado_nuevo} ({self.evento})"
