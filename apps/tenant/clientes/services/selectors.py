from decimal import Decimal
from django.db.models import Q, Count, Sum, Case, When, IntegerField, DecimalField, F
from ..models import Cliente, ContactoCliente

LIST_FIELDS = (
    "id",
    "uuid",
    "empresa_id",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email",
    "telefono",
    "ciudad",
    "activo",
)

DETAIL_FIELDS = (
    "id",
    "empresa_id",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email",
    "telefono",
    "direccion",
    "ciudad",
    "activo",
    "observaciones",
)

CONTACT_FIELDS = (
    "id",
    "empresa_id",
    "cliente_id",
    "nombre_completo",
    "cargo",
    "email",
    "telefono",
    "activo",
    "is_principal",
)

_CLIENTE_TRAVERSALS = (
    "cliente__id",
    "cliente__empresa_id",
    "cliente__razon_social",
)


class ClienteSelector:
    """Read-only optimized queries for Clientes."""

    @staticmethod
    def get_cliente_list(empresa_id: int, search: str = None, filters: dict = None):
        """Returns optimized queryset for list view with optional server-side filters."""
        qs = Cliente.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS).order_by("razon_social")
        if search:
            qs = qs.filter(
                Q(razon_social__icontains=search)
                | Q(numero_documento__icontains=search)
                | Q(email__icontains=search)
                | Q(nombre_comercial__icontains=search)
            )
        if filters:
            tipo_persona = filters.get('tipo_persona')
            if tipo_persona:
                qs = qs.filter(tipo_persona=tipo_persona)
            es_retenedor = filters.get('es_retenedor')
            if es_retenedor is not None:
                qs = qs.filter(es_retenedor=es_retenedor)
            activo = filters.get('activo')
            if activo is not None:
                qs = qs.filter(activo=activo)
        return qs

    @staticmethod
    def get_kpis(empresa_id: int) -> dict:
        """Returns aggregate KPI counts in a single DB query."""
        return Cliente.objects.filter(empresa_id=empresa_id).aggregate(
            total=Count('id'),
            activos=Count(Case(When(activo=True, then=1), output_field=IntegerField())),
            inactivos=Count(Case(When(activo=False, then=1), output_field=IntegerField())),
            juridicas=Count(Case(When(tipo_persona='JURIDICA', then=1), output_field=IntegerField())),
            naturales=Count(Case(When(tipo_persona='NATURAL', then=1), output_field=IntegerField())),
            retenedores=Count(Case(When(es_retenedor=True, then=1), output_field=IntegerField())),
        )

    @staticmethod
    def get_cliente_detail(empresa_id: int, pk: int):
        """Returns single cliente instance filtered by tenant."""
        return Cliente.objects.filter(empresa_id=empresa_id, pk=pk).only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_cartera_resumen(empresa_id: int, cliente_uuids: list) -> dict:
        """
        Retorna estado de cartera (cuentas por cobrar) para un conjunto de clientes.
        Una sola query agrupada — sin N+1.

        Returns dict keyed by str(uuid):
          {
            'pendiente_count': int,    # facturas VENTA no cobradas / cobro parcial
            'pendiente_monto': Decimal,
            'cobrada_count':   int,
            'total_count':     int,
          }
        """
        from ..models import Cartera
        from django.db.models import Count, Sum, Case, When, IntegerField, DecimalField

        if not cliente_uuids:
            return {}

        rows = (
            Cartera.objects
            .filter(empresa_id=empresa_id, cliente__uuid__in=cliente_uuids)
            .values('cliente__uuid')
            .annotate(
                pendiente_count=Count(
                    Case(When(estado_pago__in=['SIN_PAGO', 'PARCIAL'], then=1),
                         output_field=IntegerField())
                ),
                pendiente_monto=Sum(
                    Case(When(estado_pago__in=['SIN_PAGO', 'PARCIAL'], then=F('saldo')),
                         output_field=DecimalField(max_digits=18, decimal_places=2))
                ),
                cobrada_count=Count(
                    Case(When(estado_pago='PAGADA', then=1), output_field=IntegerField())
                ),
                total_count=Count('id'),
            )
        )
        return {
            str(r['cliente__uuid']): {
                'pendiente_count': r['pendiente_count'] or 0,
                'pendiente_monto': r['pendiente_monto'] or Decimal('0'),
                'cobrada_count':   r['cobrada_count'] or 0,
                'total_count':     r['total_count'] or 0,
            }
            for r in rows
            if r['cliente__uuid']
        }

    @staticmethod
    def existe_documento(
        empresa_id: int,
        tipo_documento: str,
        numero_documento: str,
        exclude_uuid: str | None = None,
    ) -> bool:
        """
        Defensa-en-profundidad pre-DB: verifica si ya existe un Cliente con
        la clave compuesta (empresa, tipo_documento, numero_documento).

        - Normaliza el numero_documento antes de comparar.
        - exclude_uuid: UUID del registro actual al actualizar (evita falso positivo contra si mismo).
        - Zero Waste: solo carga 'id' mediante .only('id').exists().
        """
        import re
        num_norm = re.sub(r"[\s\.\-]", "", str(numero_documento or "")).upper()
        if not num_norm:
            return False
        qs = Cliente.objects.filter(
            empresa_id=empresa_id,
            tipo_documento=tipo_documento,
            numero_documento=num_norm,
        )
        if exclude_uuid:
            qs = qs.exclude(uuid=str(exclude_uuid))
        return qs.only("id").exists()

    @staticmethod
    def get_cliente_by_documento(empresa_id: int, tipo_documento: str, numero_documento: str):
        """Returns one cliente by tenant and legal document."""
        return Cliente.objects.filter(
            empresa_id=empresa_id,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
        ).only(
            "id",
            "uuid",
            "empresa_id",
            "tipo_documento",
            "numero_documento",
            "razon_social",
            "nombre_comercial",
            "email",
            "telefono",
            "activo",
        ).first()


class ContactoSelector:
    """Read-only optimized queries for Contactos de Cliente."""
    
    @staticmethod
    def get_contacto_list(empresa_id: int, cliente_id: int = None):
        """Returns optimized queryset for contacts."""
        qs = (
            ContactoCliente.objects.filter(empresa_id=empresa_id)
            .select_related("cliente")
            .only(
                *CONTACT_FIELDS,
                *_CLIENTE_TRAVERSALS,
            )
            .order_by("-is_principal", "nombre_completo")
        )
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        return qs


CARTERA_FIELDS = (
    "id",
    "uuid",
    "empresa_id",
    "cliente_id",
    "numero_factura",
    "factura_uuid",
    "fecha_emision",
    "fecha_vencimiento",
    "valor_total",
    "valor_pagado",
    "saldo",
    "estado_pago",
    "observaciones",
)

_CARTERA_CLIENTE_TRAVERSALS = (
    "cliente__id",
    "cliente__uuid",
    "cliente__razon_social",
)


class CarteraSelector:
    """Read-only optimized queries for Cartera."""

    @staticmethod
    def get_cartera_list(empresa_id: int, cliente_id: int = None, estado_pago: str = None, search: str = None):
        """Returns optimized queryset for cartera list view."""
        from ..models import Cartera
        qs = (
            Cartera.objects.filter(empresa_id=empresa_id)
            .select_related("cliente")
            .only(*CARTERA_FIELDS, *_CARTERA_CLIENTE_TRAVERSALS)
            .order_by("fecha_vencimiento", "numero_factura")
        )
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if estado_pago:
            qs = qs.filter(estado_pago=estado_pago)
        if search:
            qs = qs.filter(
                Q(numero_factura__icontains=search)
                | Q(cliente__razon_social__icontains=search)
            )
        return qs

    @staticmethod
    def get_cartera_detail(empresa_id: int, uuid):
        """Returns single cartera instance by uuid."""
        from ..models import Cartera
        return (
            Cartera.objects.filter(empresa_id=empresa_id, uuid=uuid)
            .select_related("cliente")
            .only(*CARTERA_FIELDS, *_CARTERA_CLIENTE_TRAVERSALS)
            .first()
        )

    @staticmethod
    def qs_list_facturas_venta(
        empresa_id: int,
        cliente_uuid=None,
        estado_pago: str = None,
        search: str = None,
    ):
        """
        Listado de facturas de VENTA (fuente de verdad para la pestaña Cartera).
        Mapeo de estados: Factura.NO_PAGADA -> SIN_PAGO, PAGO_PARCIAL -> PARCIAL.
        """
        from apps.tenant.facturas.models import Factura
        from django.db.models import Q

        FACTURA_LIST_FIELDS = (
            "id", "uuid", "numero", "empresa_id",
            "receptor_nit", "receptor_razon_social",
            "cliente_uuid",
            "total", "estado_pago",
            "fecha_emision", "payment_due_date",
        )

        qs = (
            Factura.objects
            .filter(empresa_id=empresa_id, naturaleza='VENTA')
            .only(*FACTURA_LIST_FIELDS)
        )

        if cliente_uuid:
            qs = qs.filter(cliente_uuid=cliente_uuid)

        if estado_pago:
            mapa_inverso = {'SIN_PAGO': 'NO_PAGADA', 'PARCIAL': 'PAGO_PARCIAL', 'PAGADA': 'PAGADA'}
            qs = qs.filter(estado_pago=mapa_inverso.get(estado_pago, estado_pago))

        if search:
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(receptor_razon_social__icontains=search) |
                Q(receptor_nit__icontains=search)
            )

        return qs.order_by('-fecha_emision')

    @staticmethod
    def get_cartera_kpis_facturas_venta(empresa_id: int) -> dict:
        """KPIs calculados directamente sobre Factura.naturaleza=VENTA."""
        from apps.tenant.facturas.models import Factura
        from decimal import Decimal
        from django.db.models import Sum, Count, Case, When, DecimalField, IntegerField
        from django.db.models.functions import Coalesce
        PENDIENTE = ('NO_PAGADA', 'PAGO_PARCIAL')
        agg = Factura.objects.filter(empresa_id=empresa_id, naturaleza='VENTA').aggregate(
            pendiente_monto=Coalesce(
                Sum(Case(When(estado_pago__in=PENDIENTE, then='total'),
                         output_field=DecimalField(max_digits=15, decimal_places=2))),
                Decimal('0')
            ),
            pendiente_count=Count(
                Case(When(estado_pago__in=PENDIENTE, then=1), output_field=IntegerField())
            ),
            pagado_monto=Coalesce(
                Sum(Case(When(estado_pago='PAGADA', then='total'),
                         output_field=DecimalField(max_digits=15, decimal_places=2))),
                Decimal('0')
            ),
            total_count=Count('id'),
        )
        return {
            'pendiente_monto': str(agg['pendiente_monto']),
            'pendiente_count': agg['pendiente_count'],
            'pagado_monto':    str(agg['pagado_monto']),
            'total_count':     agg['total_count'],
        }

    @staticmethod
    def get_cartera_kpis(empresa_id: int) -> dict:
        """Returns aggregate KPI counts and sums for Cartera."""
        from ..models import Cartera
        from django.db.models import Sum, Count, Q
        from decimal import Decimal
        res = Cartera.objects.filter(empresa_id=empresa_id).aggregate(
            pendiente_monto=Sum('saldo'),
            pendiente_count=Count('id', filter=Q(estado_pago__in=['SIN_PAGO', 'PARCIAL'])),
            pagado_monto=Sum('valor_pagado'),
            total_count=Count('id')
        )
        return {
            "pendiente_monto": str(res.get("pendiente_monto") or Decimal("0")),
            "pendiente_count": res.get("pendiente_count") or 0,
            "pagado_monto": str(res.get("pagado_monto") or Decimal("0")),
            "total_count": res.get("total_count") or 0,
        }
