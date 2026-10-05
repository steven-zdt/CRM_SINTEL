"""
PLAN_AJUSTE_CICLO_PROYECTOS_FASE_1_VIABILIDAD_APROBACION: unica orquestacion
del nuevo dominio de Fase 1 (Inicio) -- "filtro economico/comercial que
autoriza la entrada a Planeacion" (Proposito del plan).

Agrupa 4 responsabilidades estrechamente relacionadas en un solo archivo
(Seccion 36 del plan permite dividir o agrupar segun convenga; se agrupa
aqui porque las 4 comparten el mismo caso de uso y el mismo ciclo de vida,
mismo criterio que ya se aplico en cotizacion_planeacion_service.py):

- ProyectoFacturaVentaService   -- vincular/desvincular Facturas de Venta
                                   + "valor vendido" (Decisiones 03/04/05)
- CotizacionCostoProyectoService -- CRUD de cotizaciones de costo (+ PDF)
- InversionProyectoInicioService -- CRUD de inversiones reales
- ProyectoInicioResumenService  -- resumen economico + viabilidad (Seccion 68)
- ProyectoInicioAprobacionService -- enviar/aprobar/rechazar + gate de
                                   Planeacion, sobre el motor GENERICO
                                   apps.tenant.approvals (SolicitudAprobacion)
                                   -- Seccion 91 del plan: "si ya existe,
                                   leer desde la SSoT existente" en vez de
                                   duplicar un AprobacionInicioProyecto.

Decisiones funcionales cerradas por el usuario (Seccion 89 del plan, todas
las recomendaciones del plan fueron aceptadas):
  01 Supervisor: apps.tenant.empleados, solo activos.
  02 Contratista/Proveedor: UNO principal, reutiliza Proyecto.proveedor_*.
  03 Facturas validas: solo Factura.Estado.ACEPTADA.
  04 Notas Credito/Debito: valor vendido = FE + ND - NC.
  05 Base IVA oficial: subtotal (antes de IVA); total con IVA es informativo.
  06 Inversion real: costo/compromiso incurrido (no solo lo pagado).
  07 Aprobacion vigente + edicion de datos criticos -> se INVALIDA (pasa a
     CANCELADA), exige nueva revision -- nunca bloquea la edicion en si.
  08 Aprobar SOLO desbloquea Planeacion; el avance de fase sigue siendo una
     accion manual separada (avanzar-fase).
  09 No se construye "cotizacion ganadora" en esta version.
  10 Viabilidad: se muestran AMBOS margenes (cotizacion e inversion real),
     sin forzar un unico indicador oficial.
"""

import logging
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import (
    CotizacionCostoProyecto,
    InversionProyectoInicio,
    Proyecto,
    ProyectoFacturaVenta,
)

logger = logging.getLogger(__name__)

_TWO = Decimal("0.01")


def _q(value) -> Decimal:
    return (value or Decimal("0.00")).quantize(_TWO)


def _margen_pct(base: Decimal, costo: Decimal):
    """None si base==0 (division por cero protegida, Seccion 81 del plan)."""
    if not base:
        return None
    return _q((base - costo) / base * Decimal("100"))


class ProyectoFacturaVentaService:
    """Vincula/desvincula Facturas de Venta y calcula el 'valor vendido'
    oficial del proyecto (Secciones 8-13 del plan)."""

    @staticmethod
    @transaction.atomic
    def vincular_factura(*, proyecto, factura_uuid, empresa_id, usuario=None):
        if not factura_uuid:
            return False, {"error": "missing_factura_uuid", "message": "factura_uuid es requerido."}, 400

        from apps.tenant.facturas.models import Factura

        factura = (
            Factura.objects.filter(uuid=factura_uuid, empresa_id=empresa_id)
            .only("id", "uuid", "numero", "naturaleza", "estado", "tipo")
            .first()
        )
        if not factura:
            return (
                False,
                {
                    "error": "factura_no_encontrada",
                    "message": "La factura no existe o no pertenece a esta empresa.",
                },
                404,
            )
        if factura.naturaleza != Factura.Naturaleza.VENTA:
            return (
                False,
                {
                    "error": "naturaleza_invalida",
                    "message": "Solo se pueden vincular facturas de VENTA (emitidas por el tenant).",
                },
                422,
            )
        # Decision 03 del plan: solo Factura ACEPTADA (venta fiscalmente
        # aceptada, nunca un documento todavia provisional).
        if factura.estado != Factura.Estado.ACEPTADA:
            return (
                False,
                {
                    "error": "estado_invalido",
                    "message": (
                        f"Solo se pueden vincular facturas en estado ACEPTADA "
                        f"(estado actual: {factura.estado})."
                    ),
                },
                422,
            )
        if ProyectoFacturaVenta.objects.filter(proyecto=proyecto, factura_uuid=factura.uuid).exists():
            return (
                False,
                {
                    "error": "ya_vinculada",
                    "message": "Esta factura ya esta vinculada a este proyecto.",
                },
                409,
            )

        vinculo = ProyectoFacturaVenta.objects.create(
            empresa_id=empresa_id,
            proyecto=proyecto,
            factura_uuid=factura.uuid,
            factura_numero=factura.numero,
            vinculado_por=usuario,
        )
        logger.info(
            "[ProyectoFacturaVenta] Proyecto id=%s vinculado a Factura uuid=%s",
            proyecto.id,
            factura.uuid,
        )
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            proyecto, motivo="Se vinculo una nueva factura de venta."
        )
        return True, vinculo, 201

    @staticmethod
    @transaction.atomic
    def desvincular_factura(*, proyecto, factura_uuid):
        vinculo = ProyectoFacturaVenta.objects.filter(
            proyecto=proyecto, factura_uuid=factura_uuid
        ).first()
        if not vinculo:
            return (
                False,
                {
                    "error": "no_encontrada",
                    "message": "Esta factura no esta vinculada a este proyecto.",
                },
                404,
            )
        vinculo.delete()
        logger.info(
            "[ProyectoFacturaVenta] Proyecto id=%s desvinculado de Factura uuid=%s",
            proyecto.id,
            factura_uuid,
        )
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            proyecto, motivo="Se desvinculo una factura de venta."
        )
        return True, {"detail": "Factura desvinculada del proyecto."}, 200

    @staticmethod
    def buscar_disponibles(*, proyecto, empresa_id, search=""):
        """
        Seccion 40 del plan: buscador server-side (nunca un <select> con
        todo el catalogo). Solo Facturas VENTA + ACEPTADA (Decision 03) que
        AUN NO estan vinculadas a este proyecto -- la exclusion se hace en
        BD, nunca solo en el frontend (mismo criterio que
        OrdenCompraSelector.get_disponibles_para_proyecto()).
        """
        from apps.tenant.facturas.models import Factura

        ya_vinculadas = ProyectoFacturaVenta.objects.filter(proyecto=proyecto).values_list(
            "factura_uuid", flat=True
        )
        qs = (
            Factura.objects.filter(
                empresa_id=empresa_id,
                naturaleza=Factura.Naturaleza.VENTA,
                estado=Factura.Estado.ACEPTADA,
            )
            .exclude(uuid__in=list(ya_vinculadas))
            .only(
                "uuid",
                "numero",
                "tipo",
                "subtotal",
                "total",
                "receptor_razon_social",
                "receptor_nit",
                "fecha_emision",
            )
        )
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(numero__icontains=search)
                | Q(receptor_razon_social__icontains=search)
                | Q(receptor_nit__icontains=search)
            )
        return qs.order_by("-fecha_emision")[:50]

    @staticmethod
    def get_resumen(proyecto) -> dict:
        """
        Resuelve en VIVO los datos reales de cada Factura vinculada (Pull
        Model, nunca cachea estado/total aqui -- Seccion 10 del plan) y
        calcula el valor vendido oficial (Decisiones 04/05): suma de
        `subtotal` (antes de IVA) con signo FE/ND=+1, NC=-1. `total` (con
        IVA) se expone solo como dato informativo, nunca como base de
        viabilidad.
        """
        vinculos = list(
            ProyectoFacturaVenta.objects.filter(proyecto=proyecto)
            .only("factura_uuid", "factura_numero", "fecha_vinculacion")
            .order_by("-fecha_vinculacion")
        )
        if not vinculos:
            return {
                "facturas": [],
                "count": 0,
                "valor_vendido_subtotal": "0.00",
                "valor_vendido_total_con_iva": "0.00",
            }

        from apps.tenant.facturas.models import Factura

        uuids = [v.factura_uuid for v in vinculos]
        facturas_map = {
            f.uuid: f
            for f in Factura.objects.filter(uuid__in=uuids, empresa_id=proyecto.empresa_id).only(
                "uuid",
                "numero",
                "tipo",
                "estado",
                "naturaleza",
                "subtotal",
                "total",
                "receptor_razon_social",
                "fecha_emision",
            )
        }

        facturas_detalle = []
        subtotal_neto = Decimal("0.00")
        total_neto = Decimal("0.00")
        for vinculo in vinculos:
            factura = facturas_map.get(vinculo.factura_uuid)
            if not factura:
                # Factura vinculada que ya no se encuentra (empresa distinta
                # o eliminada) -- se muestra como incidencia, nunca se omite
                # en silencio del listado.
                facturas_detalle.append(
                    {
                        "uuid": str(vinculo.factura_uuid),
                        "numero": vinculo.factura_numero,
                        "estado": "NO_ENCONTRADA",
                        "tipo": None,
                        "cliente": None,
                        "subtotal": "0.00",
                        "total": "0.00",
                        "fecha_emision": None,
                    }
                )
                continue

            # Decision 04: FE y ND suman, NC resta.
            signo = Decimal("-1") if factura.tipo == Factura.TipoFactura.NC else Decimal("1")
            subtotal_neto += signo * (factura.subtotal or Decimal("0.00"))
            total_neto += signo * (factura.total or Decimal("0.00"))

            facturas_detalle.append(
                {
                    "uuid": str(factura.uuid),
                    "numero": factura.numero,
                    "tipo": factura.tipo,
                    "estado": factura.estado,
                    "cliente": factura.receptor_razon_social,
                    "subtotal": str(_q(factura.subtotal)),
                    "total": str(_q(factura.total)),
                    "fecha_emision": factura.fecha_emision.isoformat()
                    if factura.fecha_emision
                    else None,
                }
            )

        return {
            "facturas": facturas_detalle,
            "count": len(facturas_detalle),
            "valor_vendido_subtotal": str(_q(subtotal_neto)),
            "valor_vendido_total_con_iva": str(_q(total_neto)),
        }


def _validar_proveedor_dsv(proveedor_id, empresa_id, campo="proveedor_id"):
    if not proveedor_id:
        return
    from apps.tenant.proveedores.models import Proveedor

    if not Proveedor.objects.filter(id=proveedor_id, empresa_id=empresa_id).exists():
        raise ValidationError({campo: "El proveedor no existe o no pertenece a esta empresa."})


class CotizacionCostoProyectoService:
    """CRUD de Cotizaciones de Costo de Fase 1 (Secciones 15-19 del plan)."""

    ALLOWED_PDF_EXT = ".pdf"
    MAX_PDF_SIZE_MB = 10
    CAMPOS_EDITABLES = (
        "categoria",
        "descripcion",
        "proveedor_id",
        "proveedor_nombre",
        "fecha",
        "numero_documento",
        "valor",
        "moneda",
        "archivo_pdf",
        "observaciones",
    )

    @staticmethod
    def _validar_pdf(archivo):
        if not archivo:
            return
        nombre = (getattr(archivo, "name", "") or "").lower()
        if not nombre.endswith(CotizacionCostoProyectoService.ALLOWED_PDF_EXT):
            raise ValidationError({"archivo_pdf": "Solo se permiten archivos PDF."})
        tamano = getattr(archivo, "size", None)
        max_bytes = CotizacionCostoProyectoService.MAX_PDF_SIZE_MB * 1024 * 1024
        if tamano and tamano > max_bytes:
            raise ValidationError(
                {
                    "archivo_pdf": (
                        f"El archivo no puede superar {CotizacionCostoProyectoService.MAX_PDF_SIZE_MB}MB."
                    )
                }
            )

    @staticmethod
    @transaction.atomic
    def crear(*, proyecto, empresa_id, data) -> CotizacionCostoProyecto:
        _validar_proveedor_dsv(data.get("proveedor_id"), empresa_id)
        CotizacionCostoProyectoService._validar_pdf(data.get("archivo_pdf"))

        item = CotizacionCostoProyecto.objects.create(
            empresa_id=empresa_id,
            proyecto=proyecto,
            categoria=data["categoria"],
            descripcion=data.get("descripcion", ""),
            proveedor_id=data.get("proveedor_id"),
            proveedor_nombre=data.get("proveedor_nombre", ""),
            fecha=data.get("fecha"),
            numero_documento=data.get("numero_documento", ""),
            valor=data.get("valor") or 0,
            moneda=data.get("moneda") or "COP",
            archivo_pdf=data.get("archivo_pdf"),
            observaciones=data.get("observaciones", ""),
        )
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            proyecto, motivo="Se agrego una cotizacion de costo."
        )
        return item

    @staticmethod
    @transaction.atomic
    def actualizar(*, item: CotizacionCostoProyecto, data) -> CotizacionCostoProyecto:
        if "proveedor_id" in data:
            _validar_proveedor_dsv(data.get("proveedor_id"), item.empresa_id)
        if "archivo_pdf" in data:
            CotizacionCostoProyectoService._validar_pdf(data.get("archivo_pdf"))

        for campo in CotizacionCostoProyectoService.CAMPOS_EDITABLES:
            if campo in data:
                setattr(item, campo, data[campo])
        item.save()
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            item.proyecto, motivo="Se edito una cotizacion de costo."
        )
        return item

    @staticmethod
    @transaction.atomic
    def eliminar(*, item: CotizacionCostoProyecto):
        """Baja logica (`activo=False`) -- evidencia financiera de un
        proceso de aprobacion, nunca se borra fisicamente."""
        proyecto = item.proyecto
        item.activo = False
        item.save(update_fields=["activo", "updated_at"])
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            proyecto, motivo="Se elimino una cotizacion de costo."
        )


class InversionProyectoInicioService:
    """CRUD de Inversiones Reales de Fase 1 (Secciones 20-22 del plan)."""

    CAMPOS_EDITABLES = (
        "categoria",
        "descripcion",
        "fecha",
        "valor",
        "proveedor_id",
        "proveedor_nombre",
        "documento_referencia",
        "observaciones",
    )

    @staticmethod
    @transaction.atomic
    def crear(*, proyecto, empresa_id, data) -> InversionProyectoInicio:
        _validar_proveedor_dsv(data.get("proveedor_id"), empresa_id)

        item = InversionProyectoInicio.objects.create(
            empresa_id=empresa_id,
            proyecto=proyecto,
            categoria=data["categoria"],
            descripcion=data.get("descripcion", ""),
            fecha=data.get("fecha"),
            valor=data.get("valor") or 0,
            proveedor_id=data.get("proveedor_id"),
            proveedor_nombre=data.get("proveedor_nombre", ""),
            documento_referencia=data.get("documento_referencia", ""),
            observaciones=data.get("observaciones", ""),
        )
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            proyecto, motivo="Se agrego una inversion real."
        )
        return item

    @staticmethod
    @transaction.atomic
    def actualizar(*, item: InversionProyectoInicio, data) -> InversionProyectoInicio:
        if "proveedor_id" in data:
            _validar_proveedor_dsv(data.get("proveedor_id"), item.empresa_id)

        for campo in InversionProyectoInicioService.CAMPOS_EDITABLES:
            if campo in data:
                setattr(item, campo, data[campo])
        item.save()
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            item.proyecto, motivo="Se edito una inversion real."
        )
        return item

    @staticmethod
    @transaction.atomic
    def eliminar(*, item: InversionProyectoInicio):
        proyecto = item.proyecto
        item.activo = False
        item.save(update_fields=["activo", "updated_at"])
        ProyectoInicioAprobacionService.invalidar_si_aprobado(
            proyecto, motivo="Se elimino una inversion real."
        )


class ProyectoInicioResumenService:
    """Respuesta SSoT unica (Seccion 68 del plan: 'ProyectoInicioSummary')
    -- evita multiples GET dispersos al abrir Fase 1 (Seccion 69, Zero-Waste).
    El frontend SOLO pinta estos valores, nunca recalcula viabilidad
    (Seccion 67)."""

    @staticmethod
    def _totales_por_categoria(queryset, categorias) -> dict:
        totales = {c: Decimal("0.00") for c in categorias}
        for item in queryset:
            totales[item.categoria] = totales.get(item.categoria, Decimal("0.00")) + (
                item.valor or Decimal("0.00")
            )
        return totales

    @staticmethod
    def calcular_resumen(proyecto) -> dict:
        facturas_resumen = ProyectoFacturaVentaService.get_resumen(proyecto)
        valor_vendido = Decimal(facturas_resumen["valor_vendido_subtotal"])

        categorias = list(CotizacionCostoProyecto.Categoria.values)

        cotizaciones_qs = CotizacionCostoProyecto.objects.filter(
            proyecto=proyecto, activo=True
        ).only("categoria", "valor")
        cotizaciones_por_categoria = ProyectoInicioResumenService._totales_por_categoria(
            cotizaciones_qs, categorias
        )
        total_cotizado = sum(cotizaciones_por_categoria.values(), Decimal("0.00"))

        inversiones_qs = InversionProyectoInicio.objects.filter(
            proyecto=proyecto, activo=True
        ).only("categoria", "valor")
        inversiones_por_categoria = ProyectoInicioResumenService._totales_por_categoria(
            inversiones_qs, categorias
        )
        total_invertido = sum(inversiones_por_categoria.values(), Decimal("0.00"))

        # Decision 10: se muestran AMBOS margenes, sin forzar un oficial.
        viabilidad = {
            "resultado_cotizacion": str(_q(valor_vendido - total_cotizado)),
            "margen_cotizacion_pct": str(_margen_pct(valor_vendido, total_cotizado))
            if _margen_pct(valor_vendido, total_cotizado) is not None
            else None,
            "resultado_inversion": str(_q(valor_vendido - total_invertido)),
            "margen_inversion_pct": str(_margen_pct(valor_vendido, total_invertido))
            if _margen_pct(valor_vendido, total_invertido) is not None
            else None,
        }

        solicitud = ProyectoInicioAprobacionService.get_ultima_solicitud(proyecto)
        estado_aprobacion = solicitud.estado if solicitud else "SIN_ENVIAR"

        return {
            "supervisor": (
                {"id": proyecto.supervisor_id, "nombre": proyecto.supervisor_nombre}
                if proyecto.supervisor_id
                else None
            ),
            "contratista": (
                {"id": proyecto.proveedor_id, "nombre": proyecto.proveedor_nombre}
                if proyecto.proveedor_id
                else None
            ),
            "facturas_venta": facturas_resumen,
            "cotizaciones_costo": {
                "mano_obra": str(_q(cotizaciones_por_categoria.get("MANO_OBRA"))),
                "materiales": str(_q(cotizaciones_por_categoria.get("MATERIALES"))),
                "equipos": str(_q(cotizaciones_por_categoria.get("EQUIPOS"))),
                "total": str(_q(total_cotizado)),
            },
            "inversion_real": {
                "mano_obra": str(_q(inversiones_por_categoria.get("MANO_OBRA"))),
                "materiales": str(_q(inversiones_por_categoria.get("MATERIALES"))),
                "equipos": str(_q(inversiones_por_categoria.get("EQUIPOS"))),
                "total": str(_q(total_invertido)),
            },
            "viabilidad": viabilidad,
            "estado_aprobacion": estado_aprobacion,
            "motivo_rechazo": (
                solicitud.motivo_rechazo if solicitud and estado_aprobacion == "RECHAZADA" else None
            ),
            "puede_avanzar_planeacion": estado_aprobacion == "APROBADA",
        }

    @staticmethod
    def calcular_snapshot_aprobacion(proyecto) -> dict:
        """Snapshot financiero congelado al enviar a aprobacion (Secciones
        13/29 del plan) -- solo valores planos (JSONField). Revalidado por
        ApprovalBusinessService.aprobar() antes de aprobar: si cambia desde
        el envio, bloquea (nunca aprueba "a ciegas")."""
        resumen = ProyectoInicioResumenService.calcular_resumen(proyecto)
        return {
            "valor_vendido_subtotal": resumen["facturas_venta"]["valor_vendido_subtotal"],
            "facturas_count": resumen["facturas_venta"]["count"],
            "total_cotizado": resumen["cotizaciones_costo"]["total"],
            "total_invertido": resumen["inversion_real"]["total"],
            "supervisor_id": proyecto.supervisor_id,
            "proveedor_id": proyecto.proveedor_id,
        }


class ProyectoInicioAprobacionService:
    """Enviar/aprobar/rechazar sobre el motor GENERICO de
    apps.tenant.approvals (SolicitudAprobacion) + gate real de
    INICIO -> PLANEACION (Seccion 34/87 del plan: 'No hay Planeacion sin
    aprobacion del Inicio economico')."""

    @staticmethod
    def get_ultima_solicitud(proyecto):
        from apps.tenant.approvals.models import SolicitudAprobacion

        return (
            SolicitudAprobacion.objects.filter(
                empresa_id=proyecto.empresa_id,
                tipo_documento=SolicitudAprobacion.TipoDocumento.PROYECTO_INICIO,
                objeto_uuid=proyecto.uuid,
            )
            .order_by("-fecha_envio")
            .first()
        )

    @staticmethod
    def can_enter_planeacion(proyecto) -> bool:
        """Seccion 34/35 del plan: unica fuente de verdad del gate, llamada
        SIEMPRE desde cambiar_fase_proyecto() -- nunca solo desde el
        frontend (sin bypass por API)."""
        from apps.tenant.approvals.models import SolicitudAprobacion

        solicitud = ProyectoInicioAprobacionService.get_ultima_solicitud(proyecto)
        return bool(solicitud and solicitud.estado == SolicitudAprobacion.Estado.APROBADA)

    @staticmethod
    @transaction.atomic
    def enviar_aprobacion(*, proyecto, usuario):
        if proyecto.fase_actual != "INICIO":
            return (
                False,
                {
                    "error": "fase_invalida",
                    "message": "Solo se puede enviar a aprobacion un proyecto en fase INICIO.",
                },
                422,
            )

        resumen = ProyectoInicioResumenService.calcular_resumen(proyecto)
        if Decimal(resumen["facturas_venta"]["valor_vendido_subtotal"]) <= 0:
            return (
                False,
                {
                    "error": "sin_valor_vendido",
                    "message": (
                        "Debe vincular al menos una factura de venta ACEPTADA antes de "
                        "enviar a aprobacion."
                    ),
                },
                422,
            )

        from apps.tenant.approvals.models import SolicitudAprobacion
        from apps.tenant.approvals.services.business_service import ApprovalBusinessService

        return ApprovalBusinessService.crear_solicitud(
            tipo_documento=SolicitudAprobacion.TipoDocumento.PROYECTO_INICIO,
            objeto_uuid=proyecto.uuid,
            empresa_id=proyecto.empresa_id,
            solicitante=usuario,
            snapshot=ProyectoInicioResumenService.calcular_snapshot_aprobacion(proyecto),
        )

    @staticmethod
    @transaction.atomic
    def aprobar(*, proyecto, empresa_id, usuario, observacion=""):
        from apps.tenant.approvals.models import SolicitudAprobacion
        from apps.tenant.approvals.services.business_service import ApprovalBusinessService

        solicitud = ProyectoInicioAprobacionService.get_ultima_solicitud(proyecto)
        if not solicitud or solicitud.estado != SolicitudAprobacion.Estado.PENDIENTE:
            return (
                False,
                {
                    "error": "sin_solicitud_pendiente",
                    "message": "Este proyecto no tiene una solicitud de aprobacion pendiente.",
                },
                404,
            )
        return ApprovalBusinessService.aprobar(str(solicitud.uuid), empresa_id, usuario, observacion)

    @staticmethod
    @transaction.atomic
    def rechazar(*, proyecto, empresa_id, usuario, motivo):
        from apps.tenant.approvals.models import SolicitudAprobacion
        from apps.tenant.approvals.services.business_service import ApprovalBusinessService

        solicitud = ProyectoInicioAprobacionService.get_ultima_solicitud(proyecto)
        if not solicitud or solicitud.estado != SolicitudAprobacion.Estado.PENDIENTE:
            return (
                False,
                {
                    "error": "sin_solicitud_pendiente",
                    "message": "Este proyecto no tiene una solicitud de aprobacion pendiente.",
                },
                404,
            )
        return ApprovalBusinessService.rechazar(str(solicitud.uuid), empresa_id, usuario, motivo)

    @staticmethod
    @transaction.atomic
    def invalidar_si_aprobado(proyecto, motivo: str = ""):
        """
        Decision 07 del plan: un cambio en datos economicos criticos
        DESPUES de aprobado invalida la aprobacion vigente (pasa a
        CANCELADA, estado ya existente en SolicitudAprobacion) y exige
        nueva revision -- nunca bloquea la edicion en si. No-op si no hay
        ninguna aprobacion vigente (la ultima solicitud no esta APROBADA).
        """
        from apps.tenant.approvals.models import SolicitudAprobacion, SolicitudAprobacionHistorial
        from apps.tenant.approvals.services.crud_service import SolicitudAprobacionCRUDService

        solicitud = ProyectoInicioAprobacionService.get_ultima_solicitud(proyecto)
        if not solicitud or solicitud.estado != SolicitudAprobacion.Estado.APROBADA:
            return

        SolicitudAprobacionCRUDService.cambiar_estado(
            solicitud,
            SolicitudAprobacion.Estado.CANCELADA,
            evento=SolicitudAprobacionHistorial.Evento.CANCELADA,
            usuario=None,
            observacion=motivo
            or "Datos economicos de Inicio modificados tras la aprobacion -- requiere nueva revision.",
        )
        logger.info(
            "[ProyectoInicioAprobacion] Aprobacion de Inicio invalidada (proyecto id=%s): %s",
            proyecto.id,
            motivo,
        )

    # --- Callbacks del registry generico (apps.tenant.approvals.services.
    # business_service.TIPO_DOCUMENTO_REGISTRY) ---------------------------
    @staticmethod
    def resolver_proyecto(objeto_uuid, empresa_id):
        return Proyecto.objects.filter(uuid=objeto_uuid, empresa_id=empresa_id).first()

    @staticmethod
    def confirmar_aprobacion_dominio(objeto_uuid, empresa_id, usuario, observacion):
        """
        'aprobar' del registry (Regla de oro #26 de Approvals: este
        callback NUNCA escribe `fase_actual` -- Decision 08 del plan, la
        aprobacion solo DESBLOQUEA, el avance a Planeacion sigue siendo
        'avanzar-fase' manual). Solo revalida que el proyecto siga en
        condiciones de ser aprobado.
        """
        proyecto = ProyectoInicioAprobacionService.resolver_proyecto(objeto_uuid, empresa_id)
        if not proyecto:
            return (
                False,
                {"error": "proyecto_no_encontrado", "message": "El proyecto no existe."},
                404,
            )
        if proyecto.fase_actual != "INICIO":
            return (
                False,
                {
                    "error": "fase_invalida",
                    "message": "El proyecto ya no esta en fase INICIO.",
                },
                422,
            )
        return True, proyecto, 200

    @staticmethod
    def confirmar_rechazo_dominio(objeto_uuid, empresa_id, usuario, motivo):
        proyecto = ProyectoInicioAprobacionService.resolver_proyecto(objeto_uuid, empresa_id)
        if not proyecto:
            return (
                False,
                {"error": "proyecto_no_encontrado", "message": "El proyecto no existe."},
                404,
            )
        return True, proyecto, 200

    @staticmethod
    def snapshot_proyecto(proyecto) -> dict:
        return ProyectoInicioResumenService.calcular_snapshot_aprobacion(proyecto)
