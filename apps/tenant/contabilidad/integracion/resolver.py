"""
Account code resolver for journal entry lines.

Maps economic concepts (INGRESO_PRINCIPAL, AUXILIO_TRANSPORTE, etc.) to
actual PUC account codes based on ConfiguracionContable rules and tenant settings.

This replaces the hardcoded MAPEO_CUENTAS dictionary with a database-driven lookup.
"""

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from .excepciones import ReglaContableNoDefinidaError, TarifaNoVigenteError

if TYPE_CHECKING:
    from datetime import date
    from ..models import ReglaContable, TarifaImpuesto

# Matches RFC 4122 UUID format (version-agnostic)
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)


class ResolverCuentas:
    """
    Resolves PUC account codes for transaction lines.

    Stateless resolver that queries ConfiguracionContable models.
    Handles account hints (overrides) for advanced scenarios.
    """

    def __init__(self, empresa_id: int):
        """
        Initialize resolver for a specific tenant.

        Args:
            empresa_id: Tenant identifier
        """
        self.empresa_id = empresa_id
        self._cache_reglas: dict = {}
        self._cache_tarifas: dict = {}

    def resolver_cuenta(
        self,
        concepto: str,
        tipo_transaccion: str,
        cuenta_hint: Optional[str] = None
    ) -> str:
        """
        Resolve PUC account code for a transaction line.

        Lookup order:
        1. cuenta_hint if provided (explicit override)
        2. ReglaContable matching (tipo_transaccion + concepto)
        3. ReglaContable matching (tipo_transaccion + wildcard)
        4. Raise ReglaContableNoDefinidaError

        Args:
            concepto: Economic concept (INGRESO_PRINCIPAL, AUXILIO_TRANSPORTE, etc.)
            tipo_transaccion: Transaction type (VENTA_FACTURA, COMPRA_GASTO, etc.)
            cuenta_hint: Optional explicit account override

        Returns:
            PUC account code (e.g., '130505', '413501')

        Raises:
            ReglaContableNoDefinidaError: If no rule found
        """
        if cuenta_hint:
            hint_str = str(cuenta_hint)
            if _UUID_RE.match(hint_str):
                # cuenta_hint es UUID de CuentaContable — resolver a codigo PUC
                from ..models import CuentaContable
                row = CuentaContable.objects.filter(
                    empresa_id=self.empresa_id,
                    uuid=hint_str,
                ).values('codigo').first()
                if row:
                    return row['codigo']
                # UUID valido pero no encontrado en este tenant — caer a ReglaContable
            else:
                # Codigo PUC directo (ej: '130505') — usar sin lookup adicional
                return hint_str

        from ..models import ReglaContable

        key = (tipo_transaccion, concepto)
        if key in self._cache_reglas:
            return self._cache_reglas[key]

        regla = ReglaContable.objects.filter(
            empresa_id=self.empresa_id,
            tipo_transaccion=tipo_transaccion,
            concepto=concepto,
            activo=True
        ).first()

        if not regla:
            raise ReglaContableNoDefinidaError(
                f"Regla contable no definida para {tipo_transaccion} + {concepto} (empresa {self.empresa_id})"
            )

        self._cache_reglas[key] = regla.cuenta_codigo
        return regla.cuenta_codigo

    def resolver_tarifa(
        self,
        tipo_impuesto: str,
        fecha: 'date'
    ) -> Decimal:
        """
        Resolve tax rate for a specific date.

        Lookup TarifaImpuesto with:
        - fecha_inicio <= transaction_date
        - fecha_fin >= transaction_date (or NULL for open-ended)
        - vigente=True

        Args:
            tipo_impuesto: Tax type (IVA, RETEFUENTE, SALUD_EMPLEADO, etc.)
            fecha: Transaction date

        Returns:
            Tax rate as Decimal (e.g., Decimal('0.19') for 19% IVA)

        Raises:
            TarifaNoVigenteError: If no rate found for date
        """
        from ..models import TarifaImpuesto
        from datetime import date as date_class

        key = (tipo_impuesto, fecha)
        if key in self._cache_tarifas:
            return self._cache_tarifas[key]

        tarifa = TarifaImpuesto.objects.filter(
            empresa_id=self.empresa_id,
            tipo=tipo_impuesto,
            fecha_inicio__lte=fecha,
            vigente=True
        ).filter(
            models.Q(fecha_fin__isnull=True) | models.Q(fecha_fin__gte=fecha)
        ).first()

        if not tarifa:
            raise TarifaNoVigenteError(
                f"Tarifa {tipo_impuesto} no vigente para {fecha} (empresa {self.empresa_id})"
            )

        valor = Decimal(str(tarifa.valor_porcentaje / 100))
        self._cache_tarifas[key] = valor
        return valor

    def resolver_tarifa_patron_parafiscal(
        self,
        tipo: str,  # CAJA, ICBF, SENA, ARL
        salario_base: Decimal,
        fecha: 'date'
    ) -> Decimal:
        """
        Resolve employer payroll tax with exoneration logic (art. 114-1 ET).

        Exoneration applies if monthly salary < 10 SMMLV.
        Returns 0 if exonerated, otherwise returns configured rate.

        Args:
            tipo: Parafiscal type
            salario_base: Employee's monthly salary
            fecha: Payroll date

        Returns:
            Tax rate (0 if exonerated, otherwise configured rate)
        """
        from ..models import TarifaImpuesto
        from django.utils.timezone import now as tz_now

        # Get current SMMLV (simplified: hardcode 2026 value)
        # TODO: Link to salary_master.SMMLVHistorico
        SMMLV_2026 = Decimal('1315000')  # Colombian 2026 minimum monthly salary
        UMBRAL_EXONERACION = SMMLV_2026 * 10  # 10 SMMLV

        if salario_base < UMBRAL_EXONERACION:
            return Decimal('0')

        return self.resolver_tarifa(tipo, fecha)


# Import models for query building
from django.db import models
