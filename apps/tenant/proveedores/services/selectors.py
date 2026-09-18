"""
Selectors for Proveedores v3.5 - Zero Waste Queries.
Incluye CuentaPorPagarSelector (sub-modulo CxP) y RepresentanteSelector.
"""
from decimal import Decimal
from django.db.models import Q, Count, Sum, Case, When, IntegerField, DecimalField, F, Prefetch
from django.db.models.functions import Coalesce
from ..models import Proveedor, CuentasPagar, Representante

LIST_FIELDS = (
    "id",
    "uuid",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "responsable_iva",
    "autoretenedor",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email_contacto",
    "telefono_contacto",
    "direccion",
    "ciudad",
    "departamento",
    "activo",
    "created_at",
)

# Campos para Representante — Zero Waste
LIST_FIELDS_REPRESENTANTE = (
    "id",
    "uuid",
    "tipo_documento",
    "numero_documento",
    "nombre_completo",
    "email_contacto",
    "telefono_contacto",
    "cargo",
    "es_principal",
    "created_at",
)

DETAIL_FIELDS_REPRESENTANTE = (
    "id",
    "uuid",
    "empresa_id",
    "proveedor_id",
    "tipo_documento",
    "numero_documento",
    "nombre_completo",
    "email_contacto",
    "telefono_contacto",
    "cargo",
    "es_principal",
    "created_at",
    "updated_at",
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "actividad_economica_ciiu",
    "responsable_iva",
    "gran_contribuyente",
    "autoretenedor",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email_contacto",
    "telefono_contacto",
    "direccion",
    "ciudad",
    "departamento",
    "plazo_pago_dias",
    "banco",
    "tipo_cuenta",
    "numero_cuenta",
    "activo",
    "observaciones",
    "created_at",
    "updated_at",
)

class RepresentanteSelector:
    """Selectores de solo lectura para Representantes (Zero Waste)."""

    @staticmethod
    def get_list_por_proveedor(empresa_id: int, proveedor_uuid: str):
        """
        Retorna listado optimizado de representantes de un proveedor.
        Filtros DSV: empresa_id + proveedor_uuid.
        """
        qs = (
            Representante.objects
            .filter(empresa_id=empresa_id, proveedor__uuid=proveedor_uuid)
            .only(*LIST_FIELDS_REPRESENTANTE)
            .order_by("-es_principal", "nombre_completo")
        )
        return qs

    @staticmethod
    def get_by_uuid(empresa_id: int, representante_uuid: str):
        """
        Retorna detalle completo de un representante por UUID (DSV).
        """
        return (
            Representante.objects
            .filter(empresa_id=empresa_id, uuid=representante_uuid)
            .only(*DETAIL_FIELDS_REPRESENTANTE)
            .first()
        )

    @staticmethod
    def get_list_por_empresa(empresa_id: int):
        """
        Retorna todos los representantes de la empresa sin filtro de proveedor.
        Usado por el directorio global (/representantes/ sin ?proveedor_uuid).
        """
        return (
            Representante.objects
            .filter(empresa_id=empresa_id)
            .only(*LIST_FIELDS_REPRESENTANTE)
            .order_by("-es_principal", "nombre_completo")
        )

    @staticmethod
    def get_principal_por_proveedor(empresa_id: int, proveedor_uuid: str):
        """
        Retorna el representante principal de un proveedor (es_principal=True).
        Si no existe, retorna None.
        """
        return (
            Representante.objects
            .filter(
                empresa_id=empresa_id,
                proveedor__uuid=proveedor_uuid,
                es_principal=True
            )
            .only(*LIST_FIELDS_REPRESENTANTE)
            .first()
        )


class ProveedorSelector:
    """Clase selectora para inyección en mixins."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, filtro: str = None):
        """
        Retorna listado optimizado con representante principal precargado.

        `filtro` (RELEASE-CLOSE/PROVEEDORES-02, Fase 7/18 -- coherencia visual
        con clientes/tables.py::ClienteTable): "" (todos), JURIDICA, NATURAL,
        RETENEDOR, ACTIVO, INACTIVO.
        """
        # Prefetch solo el representante principal (es_principal=True)
        representante_principal = Prefetch(
            'representantes',
            Representante.objects.filter(es_principal=True).only(*LIST_FIELDS_REPRESENTANTE)
        )

        qs = (
            Proveedor.objects
            .filter(empresa_id=empresa_id)
            .prefetch_related(representante_principal)
            .only(*LIST_FIELDS)
            .order_by('razon_social')
        )

        if search:
            qs = qs.filter(
                Q(razon_social__icontains=search) |
                Q(numero_documento__icontains=search) |
                Q(email_contacto__icontains=search) |
                Q(nombre_comercial__icontains=search)
            ).distinct()

        if filtro == "JURIDICA":
            qs = qs.filter(tipo_persona="JURIDICA")
        elif filtro == "NATURAL":
            qs = qs.filter(tipo_persona="NATURAL")
        elif filtro == "RETENEDOR":
            qs = qs.filter(es_retenedor=True)
        elif filtro == "ACTIVO":
            qs = qs.filter(activo=True)
        elif filtro == "INACTIVO":
            qs = qs.filter(activo=False)

        return qs
    
    @staticmethod
    def get_by_id(empresa_id: int, pk: int):
        """Retorna detalle completo para edición por PK."""
        return Proveedor.objects.filter(empresa_id=empresa_id, pk=pk).only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_by_uuid(empresa_id: int, uuid_val: str):
        """Retorna detalle completo para edición por UUID."""
        return Proveedor.objects.filter(empresa_id=empresa_id, uuid=uuid_val).only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_cuentas_pagar_resumen(empresa_id: int, proveedor_uuids: list) -> dict:
        """
        FASE 2 — Nivel Acreedor: deuda consolidada por proveedor.

        Lee directamente de Factura.naturaleza=COMPRA (fuente de verdad).
        Una sola query agrupada — N=1, sin N+1 al renderizar Tabulator.

        Factura.estado_pago: NO_PAGADA | PAGO_PARCIAL | PAGADA
        Factura.proveedor_uuid: soft reference al proveedor

        Returns dict keyed by str(proveedor.uuid):
          {
            'pendiente_count': int      — facturas NO_PAGADA o PAGO_PARCIAL
            'pendiente_monto': Decimal  — suma total de facturas pendientes
            'pagada_count':    int      — facturas PAGADAS
            'total_count':     int      — total facturas COMPRA del proveedor
          }
        """
        if not proveedor_uuids:
            return {}

        # Import local — Bounded Context (AGENTS.md §18): lectura de solo lectura
        # desde proveedores hacia facturas (sin FK directa, solo query)
        from apps.tenant.facturas.models import Factura

        PENDIENTE = ('NO_PAGADA', 'PAGO_PARCIAL')

        rows = (
            Factura.objects
            .filter(
                empresa_id=empresa_id,
                naturaleza='COMPRA',
                proveedor_uuid__in=proveedor_uuids,
            )
            .values('proveedor_uuid')
            .annotate(
                pendiente_count=Count(
                    Case(When(estado_pago__in=PENDIENTE, then=1),
                         output_field=IntegerField())
                ),
                pendiente_monto=Coalesce(
                    Sum(
                        Case(When(estado_pago__in=PENDIENTE, then=F('total')),
                             output_field=DecimalField(max_digits=15, decimal_places=2))
                    ),
                    Decimal('0')
                ),
                pagada_count=Count(
                    Case(When(estado_pago='PAGADA', then=1),
                         output_field=IntegerField())
                ),
                total_count=Count('id'),
            )
        )
        return {
            str(r['proveedor_uuid']): {
                'pendiente_count': r['pendiente_count'] or 0,
                'pendiente_monto': r['pendiente_monto'] or Decimal('0'),
                'pagada_count':    r['pagada_count'] or 0,
                'total_count':     r['total_count'] or 0,
            }
            for r in rows
            if r['proveedor_uuid']
        }

    @staticmethod
    def existe_documento(
        empresa_id: int,
        tipo_documento: str,
        numero_documento: str,
        exclude_uuid: str | None = None,
    ) -> bool:
        """
        Defensa-en-profundidad pre-DB: verifica si ya existe un Proveedor con
        la clave compuesta (empresa, tipo_documento, numero_documento).

        - Normaliza el numero_documento antes de comparar.
        - exclude_uuid: UUID del registro actual al actualizar (evita falso positivo contra si mismo).
        - Zero Waste: solo carga 'id' mediante .only('id').exists().
        """
        import re
        num_norm = re.sub(r"[\s\.\-]", "", str(numero_documento or "")).upper()
        if not num_norm:
            return False
        qs = Proveedor.objects.filter(
            empresa_id=empresa_id,
            tipo_documento=tipo_documento,
            numero_documento=num_norm,
        )
        if exclude_uuid:
            qs = qs.exclude(uuid=str(exclude_uuid))
        return qs.only("id").exists()

    @staticmethod
    def get_by_documento(empresa_id: int, tipo_documento: str, numero_documento: str):
        """Retorna un proveedor por empresa y documento legal."""
        return Proveedor.objects.filter(
            empresa_id=empresa_id,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
        ).only(
            "id",
            "uuid",
            "empresa_id",
            "tipo_documento",
            "numero_documento",
            "digito_verificacion",
            "razon_social",
            "nombre_comercial",
            "email_contacto",
            "telefono_contacto",
            "activo",
        ).first()


# ==============================================================================
# CuentasPagar Selector — estado de deudas con proveedores (AGENTS.md §4.5 Zero Waste)
# ==============================================================================

LIST_FIELDS_CUENTAS_PAGAR = (
    "id", "uuid", "empresa_id", "proveedor_id",
    "numero_factura", "factura_uuid",
    "fecha_emision", "fecha_vencimiento",
    "valor_total", "valor_pagado", "saldo",
    "estado_pago", "fecha_ultimo_pago", "referencia_pago",
    "created_at",
)

DETAIL_FIELDS_CUENTAS_PAGAR = LIST_FIELDS_CUENTAS_PAGAR + ("observaciones", "updated_at")


class CuentasPagarSelector:
    """Selectores de solo lectura para Cuentas por Pagar."""

    # Campos de Factura necesarios para el listado de CxP
    FACTURA_LIST_FIELDS = (
        "id", "uuid", "numero", "empresa_id",
        "emisor_nit", "emisor_razon_social",
        "proveedor_uuid",
        "total", "estado_pago",
        "fecha_emision", "payment_due_date",
    )

    @staticmethod
    def qs_list_facturas_compra(empresa_id: int, proveedor_uuid=None, estado_pago=None, vencidas: bool = False, search=None):
        """
        FASE 3 — Listado de facturas de compra pendientes/pagadas (fuente de verdad).

        Lee directamente de Factura.naturaleza='COMPRA'.
        Para COMPRA: emisor = proveedor, receptor = empresa del tenant.

        Mapeo de estados Factura → CxP:
          NO_PAGADA   → SIN_PAGO
          PAGO_PARCIAL → PARCIAL
          PAGADA       → PAGADA
        """
        from apps.tenant.facturas.models import Factura
        from django.utils import timezone

        qs = (
            Factura.objects
            .filter(empresa_id=empresa_id, naturaleza='COMPRA')
            .only(*CuentasPagarSelector.FACTURA_LIST_FIELDS)
        )

        if proveedor_uuid:
            qs = qs.filter(proveedor_uuid=proveedor_uuid)

        if search:
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(emisor_razon_social__icontains=search) |
                Q(emisor_nit__icontains=search)
            )

        if estado_pago:
            # Traducir estado CxP → estado Factura
            mapa_inverso = {
                'SIN_PAGO': 'NO_PAGADA',
                'PARCIAL':  'PAGO_PARCIAL',
                'PAGADA':   'PAGADA',
            }
            estado_factura = mapa_inverso.get(estado_pago, estado_pago)
            qs = qs.filter(estado_pago=estado_factura)

        if vencidas:
            hoy = timezone.now().date()
            qs = qs.filter(
                payment_due_date__lt=hoy
            ).exclude(estado_pago='PAGADA')

        return qs.order_by('payment_due_date', '-fecha_emision')

    # Factura.EstadoPago <-> CuentasPagar.estado_pago: mismos 3 estados,
    # nombres distintos. Reutilizado por qs_list_facturas_compra() (arriba,
    # direccion CxP->Factura) y por _adaptar_cuentas_pagar_a_forma_factura()
    # (abajo, direccion Factura->CxP) -- una sola tabla, sin duplicar.
    _ESTADO_CXP_A_FACTURA = {'SIN_PAGO': 'NO_PAGADA', 'PARCIAL': 'PAGO_PARCIAL', 'PAGADA': 'PAGADA'}

    @staticmethod
    def _fila_unificada(*, uuid, numero, proveedor_nombre, proveedor_nit, total, valor_pagado,
                         saldo, fecha_vencimiento, fecha_emision, estado_pago, factura_uuid,
                         origen, puede_eliminar):
        """
        Forma comun de una fila del listado unificado de CxP. Consumida por
        CuentasPagarTable (server-rendered, ver views.py), FacturaCxPListSerializer
        (API DRF) y CuentasPagarViewSet.render_offcanvas()/retrieve() (misma
        forma para list/detail, ver `resolver_fila_por_uuid` abajo) -- una sola
        forma de objeto para toda la fila, sin importar su origen real.

        estado_pago siempre en vocabulario de Factura (NO_PAGADA/PAGO_PARCIAL/
        PAGADA) -- SSoT ya establecida por FacturaCxPListSerializer/tables.py.
        """
        from types import SimpleNamespace
        return SimpleNamespace(
            uuid=uuid,
            numero=numero,
            emisor_razon_social=proveedor_nombre,
            emisor_nit=proveedor_nit,
            total=total,
            valor_pagado=valor_pagado,
            saldo=saldo,
            payment_due_date=fecha_vencimiento,
            fecha_emision=fecha_emision,
            estado_pago=estado_pago,
            factura_uuid=factura_uuid,
            origen=origen,
            puede_eliminar=puede_eliminar,
        )

    @staticmethod
    def qs_list_unificado(empresa_id: int, proveedor_uuid=None, estado_pago=None, vencidas: bool = False, search=None):
        """
        Fuente unificada para la grilla de Cuentas por Pagar: Facturas de
        compra + CxP generadas desde Compras o creadas a mano (sin Factura).
        Consumido por CuentasPagarViewSet.list() (API DRF) y
        CuentasPagarTableView (HTMX/django-tables2) -- misma SSoT para ambas.

        [RELEASE-CLOSE / PROVEEDORES-02] Hallazgo real corregido: cuando una
        fila se origina en una Factura(COMPRA) y luego se le registra un abono
        (materializa una CuentasPagar vinculada via factura_uuid, ver
        CuentasPagarBusinessService.resolver_cuenta_pagar), el listado volvia
        a leer Factura.estado_pago/total directo en la siguiente carga --
        Factura.estado_pago NUNCA se actualiza desde aqui (propiedad exclusiva
        de Facturas, bounded context intacto), asi que el abono recien
        registrado quedaba invisible. Fix: por cada Factura(COMPRA) se busca
        si existe una CuentasPagar vinculada por factura_uuid (una sola query
        extra, N=1) -- si existe, ES la fuente autoritativa de
        valor_pagado/saldo/estado_pago para esa fila; la Factura solo aporta
        datos documentales (numero, proveedor, fecha).

        No es un QuerySet real (mezcla dos modelos) -- una lista Python ya
        ordenada (ambos consumidores solo iteran/paginan, nunca llaman
        .filter()/.order_by() de nuevo sobre el resultado).
        """
        from datetime import date, datetime
        from decimal import Decimal

        from django.utils import timezone

        # Filtro de estado/vencidas se aplica al FINAL sobre el estado ya
        # resuelto (Factura o CxP vinculada) -- no sobre Factura.estado_pago
        # crudo, que puede estar desactualizado frente a una CxP vinculada.
        facturas = list(CuentasPagarSelector.qs_list_facturas_compra(
            empresa_id=empresa_id, proveedor_uuid=proveedor_uuid, estado_pago=None,
            vencidas=False, search=search,
        ))
        factura_uuids = [f.uuid for f in facturas]
        cxp_por_factura = {
            c.factura_uuid: c
            for c in CuentasPagar.objects.filter(
                empresa_id=empresa_id, factura_uuid__in=factura_uuids,
            ).only(*LIST_FIELDS_CUENTAS_PAGAR)
        } if factura_uuids else {}

        mapa = CuentasPagarSelector._ESTADO_CXP_A_FACTURA
        filas = []
        for f in facturas:
            cxp = cxp_por_factura.get(f.uuid)
            if cxp:
                filas.append(CuentasPagarSelector._fila_unificada(
                    uuid=cxp.uuid, numero=f.numero, proveedor_nombre=f.emisor_razon_social,
                    proveedor_nit=f.emisor_nit, total=cxp.valor_total, valor_pagado=cxp.valor_pagado,
                    saldo=cxp.saldo, fecha_vencimiento=cxp.fecha_vencimiento or f.payment_due_date,
                    fecha_emision=f.fecha_emision, estado_pago=mapa.get(cxp.estado_pago, "NO_PAGADA"),
                    factura_uuid=f.uuid, origen="FACTURA", puede_eliminar=False,
                ))
            else:
                filas.append(CuentasPagarSelector._fila_unificada(
                    uuid=f.uuid, numero=f.numero, proveedor_nombre=f.emisor_razon_social,
                    proveedor_nit=f.emisor_nit, total=f.total, valor_pagado=Decimal("0.00"),
                    saldo=Decimal("0.00") if f.estado_pago == "PAGADA" else (f.total or Decimal("0.00")),
                    fecha_vencimiento=f.payment_due_date, fecha_emision=f.fecha_emision,
                    estado_pago=f.estado_pago, factura_uuid=f.uuid, origen="FACTURA", puede_eliminar=False,
                ))

        # CxP sin Factura asociada (creadas a mano o desde aprobacion de Orden
        # de Compra, v3.18.0) -- eliminables solo si nunca recibieron abono.
        extra_qs = (
            CuentasPagar.objects
            .filter(empresa_id=empresa_id, factura_uuid__isnull=True)
            .select_related("proveedor")
            .only(*LIST_FIELDS_CUENTAS_PAGAR, "proveedor__razon_social", "proveedor__numero_documento")
        )
        if proveedor_uuid:
            extra_qs = extra_qs.filter(proveedor__uuid=proveedor_uuid)
        if search:
            extra_qs = extra_qs.filter(
                Q(numero_factura__icontains=search) |
                Q(proveedor__razon_social__icontains=search) |
                Q(proveedor__numero_documento__icontains=search)
            )
        for c in extra_qs:
            filas.append(CuentasPagarSelector._fila_unificada(
                uuid=c.uuid, numero=c.numero_factura, proveedor_nombre=c.proveedor.razon_social,
                proveedor_nit=c.proveedor.numero_documento, total=c.valor_total,
                valor_pagado=c.valor_pagado, saldo=c.saldo, fecha_vencimiento=c.fecha_vencimiento,
                # Factura.fecha_emision es DateTimeField (aware); CuentasPagar.fecha_emision
                # es DateField -- convertir para que FacturaCxPListSerializer.fecha_emision
                # (DateTimeField) no reciba un date() plano.
                fecha_emision=timezone.make_aware(datetime.combine(c.fecha_emision, datetime.min.time()))
                    if c.fecha_emision else None,
                estado_pago=mapa.get(c.estado_pago, "NO_PAGADA"),
                factura_uuid=None, origen="MANUAL", puede_eliminar=(c.valor_pagado == Decimal("0.00")),
            ))

        if estado_pago:
            mapa_inverso = {"SIN_PAGO": "NO_PAGADA", "PARCIAL": "PAGO_PARCIAL", "PAGADA": "PAGADA"}
            estado_factura = mapa_inverso.get(estado_pago, estado_pago)
            filas = [r for r in filas if r.estado_pago == estado_factura]
        if vencidas:
            hoy = timezone.now().date()
            filas = [
                r for r in filas
                if r.payment_due_date and r.payment_due_date < hoy and r.estado_pago != "PAGADA"
            ]

        def _a_fecha(valor):
            if isinstance(valor, datetime):
                return valor.date()
            return valor

        filas.sort(key=lambda r: _a_fecha(r.fecha_emision) or date.min, reverse=True)
        filas.sort(key=lambda r: (r.payment_due_date is None, r.payment_due_date or date.max))
        return filas

    @staticmethod
    def resolver_fila_por_uuid(empresa_id: int, uuid_val: str):
        """
        Resuelve UNA fila del listado unificado por UUID, sin escribir en BD
        (uso: detalle/offcanvas de solo lectura). Acepta los 2 origenes
        posibles de qs_list_unificado(): uuid de una CuentasPagar real
        (vinculada a Factura o manual), o uuid de una Factura(COMPRA) que
        todavia no tiene ninguna CuentasPagar vinculada.

        Para materializar (crear) una CuentasPagar antes de mutar (abono),
        usar CuentasPagarBusinessService.resolver_cuenta_pagar() -- esa si
        escribe, deliberadamente separada de este selector de solo lectura.
        """
        from decimal import Decimal

        cxp = CuentasPagarSelector.get_by_uuid(empresa_id, uuid_val)
        if cxp:
            mapa = CuentasPagarSelector._ESTADO_CXP_A_FACTURA
            proveedor_nombre = getattr(cxp.proveedor, "razon_social", "") if cxp.proveedor_id else ""
            proveedor_nit = getattr(cxp.proveedor, "numero_documento", "") if cxp.proveedor_id else ""
            return CuentasPagarSelector._fila_unificada(
                uuid=cxp.uuid, numero=cxp.numero_factura, proveedor_nombre=proveedor_nombre,
                proveedor_nit=proveedor_nit, total=cxp.valor_total, valor_pagado=cxp.valor_pagado,
                saldo=cxp.saldo, fecha_vencimiento=cxp.fecha_vencimiento, fecha_emision=cxp.fecha_emision,
                estado_pago=mapa.get(cxp.estado_pago, "NO_PAGADA"), factura_uuid=cxp.factura_uuid,
                origen=("FACTURA" if cxp.factura_uuid else "MANUAL"),
                puede_eliminar=(not cxp.factura_uuid and cxp.valor_pagado == Decimal("0.00")),
            )

        from apps.tenant.facturas.models import Factura

        factura = (
            Factura.objects
            .filter(empresa_id=empresa_id, uuid=uuid_val, naturaleza="COMPRA")
            .only(*CuentasPagarSelector.FACTURA_LIST_FIELDS)
            .first()
        )
        if not factura:
            return None
        return CuentasPagarSelector._fila_unificada(
            uuid=factura.uuid, numero=factura.numero, proveedor_nombre=factura.emisor_razon_social,
            proveedor_nit=factura.emisor_nit, total=factura.total, valor_pagado=Decimal("0.00"),
            saldo=Decimal("0.00") if factura.estado_pago == "PAGADA" else (factura.total or Decimal("0.00")),
            fecha_vencimiento=factura.payment_due_date, fecha_emision=factura.fecha_emision,
            estado_pago=factura.estado_pago, factura_uuid=factura.uuid, origen="FACTURA",
            puede_eliminar=False,
        )

    @staticmethod
    def qs_list(empresa_id: int, proveedor_id=None, estado_pago=None, vencidas: bool = False):
        """
        QuerySet optimizado para listado.
        Filtros opcionales: proveedor_id, estado_pago, vencidas.
        """
        qs = (
            CuentasPagar.objects
            .filter(empresa_id=empresa_id)
            .select_related("proveedor")
            .only(
                *LIST_FIELDS_CUENTAS_PAGAR,
                "proveedor__razon_social",
                "proveedor__numero_documento",
            )
        )
        if proveedor_id:
            if isinstance(proveedor_id, str) and (len(proveedor_id) > 10 or '-' in proveedor_id):
                qs = qs.filter(proveedor__uuid=proveedor_id)
            else:
                qs = qs.filter(proveedor_id=proveedor_id)
        if estado_pago:
            qs = qs.filter(estado_pago=estado_pago)
        if vencidas:
            from django.utils import timezone
            qs = qs.filter(
                fecha_vencimiento__lt=timezone.now().date()
            ).exclude(estado_pago="PAGADA")
        return qs.order_by("fecha_vencimiento")

    @staticmethod
    def get_by_uuid(empresa_id: int, uuid_val):
        """Retorna una Cuenta por Pagar por UUID con datos del proveedor."""
        return (
            CuentasPagar.objects
            .filter(empresa_id=empresa_id, uuid=uuid_val)
            .select_related("proveedor")
            .only(
                *DETAIL_FIELDS_CUENTAS_PAGAR,
                "proveedor__razon_social",
                "proveedor__numero_documento",
                "proveedor__email_contacto",
            )
            .first()
        )

    @staticmethod
    def resumen_por_empresa(empresa_id: int) -> dict:
        """
        FASE 1 — KPIs Empresa (Dashboard Admin).
        Una sola query con .aggregate() + Coalesce para null safety.

        Retorna:
          deuda_total_pendiente  — suma saldo facturas SIN_PAGO o PARCIAL
          total_pagado_historico — suma valor_pagado acumulado (todas las facturas)
          facturas_pendientes_count — count SIN_PAGO | PARCIAL
          facturas_pagadas_count    — count PAGADAS
          deuda_vencida          — suma saldo pendiente con vencimiento < hoy
          facturas_vencidas_count — count facturas vencidas no pagadas
        """
        from django.utils import timezone
        hoy = timezone.now().date()
        PENDIENTE = ('SIN_PAGO', 'PARCIAL')

        # Query principal — todos los KPIs en una sola pasada
        kpis = CuentasPagar.objects.filter(empresa_id=empresa_id).aggregate(
            deuda_total_pendiente=Coalesce(
                Sum(
                    Case(When(estado_pago__in=PENDIENTE, then=F('saldo')),
                         output_field=DecimalField(max_digits=18, decimal_places=2))
                ),
                Decimal('0')
            ),
            total_pagado_historico=Coalesce(
                Sum('valor_pagado'),
                Decimal('0')
            ),
            facturas_pendientes_count=Count(
                Case(When(estado_pago__in=PENDIENTE, then=1),
                     output_field=IntegerField())
            ),
            facturas_pagadas_count=Count(
                Case(When(estado_pago='PAGADA', then=1),
                     output_field=IntegerField())
            ),
        )

        # Deuda vencida — segunda query (filtro de fecha diferente al principal)
        vencidas = CuentasPagar.objects.filter(
            empresa_id=empresa_id,
            estado_pago__in=PENDIENTE,
            fecha_vencimiento__lt=hoy,
        ).aggregate(
            deuda_vencida=Coalesce(Sum('saldo'), Decimal('0')),
            facturas_vencidas_count=Count('id'),
        )

        return {
            'deuda_total_pendiente':    kpis['deuda_total_pendiente'],
            'total_pagado_historico':   kpis['total_pagado_historico'],
            'facturas_pendientes_count': kpis['facturas_pendientes_count'],
            'facturas_pagadas_count':    kpis['facturas_pagadas_count'],
            'deuda_vencida':            vencidas['deuda_vencida'],
            'facturas_vencidas_count':  vencidas['facturas_vencidas_count'],
        }
