"""
Selectors for Proveedores v3.5 - Zero Waste Queries.
Incluye CuentaPorPagarSelector (sub-modulo CxP).
"""
from decimal import Decimal
from django.db.models import Q, Count, Sum, Case, When, IntegerField, DecimalField, F
from django.db.models.functions import Coalesce
from ..models import Proveedor, CuentasPagar

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

class ProveedorSelector:
    """Clase selectora para inyección en mixins."""
    
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """Retorna listado optimizado para Tabulator."""
        qs = Proveedor.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS).order_by('razon_social')
        
        if search:
            qs = qs.filter(
                Q(razon_social__icontains=search) | 
                Q(numero_documento__icontains=search) |
                Q(email_contacto__icontains=search) |
                Q(nombre_comercial__icontains=search)
            ).distinct()
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
    def qs_list_facturas_compra(empresa_id: int, proveedor_uuid=None, estado_pago=None, vencidas: bool = False):
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
