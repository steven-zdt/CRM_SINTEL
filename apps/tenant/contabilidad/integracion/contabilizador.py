"""
Main orchestrator for materializing economic transactions into journal entries.

The Contabilizador is the single entry point for all accounting integration.
It takes a TransaccionEconomica DTO, resolves accounts and tax rates,
validates the entry, and persists it atomically.

Usage:
    from apps.tenant.contabilidad.integracion.dtos import TransaccionEconomica, TipoTransaccion
    from apps.tenant.contabilidad.integracion.contabilizador import Contabilizador

    # Source app builds DTO
    dto = TransaccionEconomica(...)

    # Contabilizador materializes it
    asiento = Contabilizador(empresa_id=1).contabilizar(dto)
"""

import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils.timezone import now as tz_now

from ..models import AsientoContable, MovimientoContable, PeriodoContable, ImpuestoDocumento
from .dtos import TransaccionEconomica, LineaTransaccion
from .excepciones import AsientoYaExisteError
from .resolver import ResolverCuentas
from .validadores import (
    validar_cuadratura,
    validar_no_vacio,
    validar_periodo_abierto,
)


class Contabilizador:
    """
    Materializes TransaccionEconomica DTOs into journal entries.

    Responsibilities:
    1. Validate transaction data and source document
    2. Infer accounting period from transaction date
    3. Resolve PUC accounts for each line (via ReglaContable + ResolverCuentas)
    4. Build balanced journal entry (must have debit lines and credit lines)
    5. Check idempotence (no duplicate entries for same source document)
    6. Persist atomically with all MovimientoContable records
    7. Handle errors with proper logging and alerting

    Non-responsibilities (handled by caller):
    - Approval/workflow (entries created in BORRADOR state)
    - Blocking business operations (should alert, not prevent)
    - Async processing (caller should handle background vs. sync)
    """

    def __init__(self, empresa_id: int):
        """
        Initialize contabilizador for a specific tenant.

        Args:
            empresa_id: Tenant identifier
        """
        self.empresa_id = empresa_id
        self.resolver = ResolverCuentas(empresa_id)

    def contabilizar(self, transaccion: TransaccionEconomica) -> AsientoContable:
        """
        Materialize economic transaction into journal entry.

        Atomic operation: either succeeds completely or rolls back entirely.

        Args:
            transaccion: Economic transaction DTO

        Returns:
            Created AsientoContable instance

        Raises:
            Various ContabilidadError subclasses on validation failure
        """
        try:
            with transaction.atomic():
                # 1. Resolve period from transaction date
                periodo = self._resolver_periodo(transaccion.fecha)
                validar_periodo_abierto(periodo)

                # 3. Check idempotence: no entry exists for this source document
                self._validar_no_existe(transaccion.documento_origen)

                # 4. Build balanced entry with resolved accounts
                asiento = self._construir_asiento(transaccion, periodo)

                # 5. Validate balanced and non-empty
                validar_no_vacio(asiento.debe_total, asiento.haber_total)
                validar_cuadratura(asiento.debe_total, asiento.haber_total)

                # 6. Persist
                asiento.save()

                # 7. Persist movements
                # WARNING: [PERF-A2] bulk_create en vez de .save() por linea -- un
                # extractor procesando un backlog de cientos de documentos pendientes
                # llama contabilizar() una vez por documento; cada linea individual
                # guardada con .save() multiplica los INSERTs (ver
                # extractores/base.py:contabilizar_pendientes). Ninguno de los 2
                # modelos tiene save() propio (solo el de SintelTenantBaseModel, que
                # valida empresa_id -- ya viene seteado explicitamente al construir
                # cada instancia en _construir_asiento(), asi que bulk_create es seguro
                # aqui). Sigue habiendo una escritura a BD por asiento (no se agrupan
                # movimientos de distintos documentos), preservando el aislamiento de
                # fallos por documento que ya tenia el codigo original.
                movimientos = asiento.movimientos_por_guardar
                for movimiento in movimientos:
                    movimiento.asiento = asiento
                if movimientos:
                    MovimientoContable.objects.bulk_create(movimientos)

                # 8. Persist taxes (ImpuestoDocumento)
                impuestos_doc = getattr(asiento, 'impuestos_documento_por_guardar', [])
                for imp_doc in impuestos_doc:
                    imp_doc.asiento = asiento
                if impuestos_doc:
                    ImpuestoDocumento.objects.bulk_create(impuestos_doc)

                return asiento
        except IntegrityError as exc:
            # WARNING: [PERF-C1] Respaldo del UniqueConstraint
            # uniq_asiento_documento_origen_no_reversado (AsientoContable.Meta).
            # El .exists() de _validar_no_existe() no es atomico frente a otra
            # transaccion concurrente contabilizando el mismo documento_origen; si
            # ambas lo pasan antes de hacer commit, la constraint de base de datos
            # rechaza el segundo INSERT. Se traduce a AsientoYaExisteError para que
            # el llamador (p. ej. BaseExtractor.contabilizar_pendientes) lo trate
            # igual que la ruta normal de idempotencia (conteo en "omitidos").
            if 'uniq_asiento_documento_origen_no_reversado' in str(exc):
                raise AsientoYaExisteError(
                    f"Asiento contable ya existe para {transaccion.documento_origen.app_label}."
                    f"{transaccion.documento_origen.modelo}[{transaccion.documento_origen.id}] "
                    f"(detectado por constraint de base de datos ante condicion de carrera)"
                ) from exc
            raise

    def existe_asiento_para(
        self,
        app_label: str,
        modelo: str,
        id: int
    ) -> bool:
        """
        Check if entry already exists for source document (idempotence check).

        Args:
            app_label: Origin app
            modelo: Model name
            id: Document PK

        Returns:
            True if entry exists, False otherwise
        """
        return AsientoContable.objects.filter(
            empresa_id=self.empresa_id,
            documento_origen_app=app_label,
            documento_origen_modelo=modelo,
            documento_origen_id=id,
            documento_origen_reversado=False,  # Count only original, not reverses
        ).exists()

    def reversar_asiento(self, asiento_original: AsientoContable) -> AsientoContable:
        """
        Create reversal entry (opposite signs) for existing journal entry.

        Used for document cancellations, corrections, etc.
        Reversal is linked to original via documento_origen_reversado.

        Args:
            asiento_original: Entry to reverse

        Returns:
            New reversed AsientoContable

        Raises:
            PeriodoCerradoError: If current period is closed (but original can be in past period)
        """
        with transaction.atomic():
            periodo = self._resolver_periodo(tz_now().date())
            validar_periodo_abierto(periodo)

            # Create reversed entry with opposite signs
            fecha_reversal = tz_now().date()
            asiento_reversal = AsientoContable.objects.create(
                empresa_id=self.empresa_id,
                fecha=fecha_reversal,
                numero=f"RVER-{fecha_reversal.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                descripcion=f"REVERSAL: {asiento_original.descripcion}",
                periodo_contable=periodo,
                estado='BORRADOR',
                documento_origen_app=asiento_original.documento_origen_app,
                documento_origen_modelo=asiento_original.documento_origen_modelo,
                documento_origen_id=asiento_original.documento_origen_id,
                documento_origen_reversado=True,
                asiento_reversado_id=asiento_original.id,
            )

            # Mirror movements with inverted signs
            for movimiento_orig in asiento_original.movimientos.all():
                movimiento_orig.id = None  # Reset PK for insert
                movimiento_orig.asiento = asiento_reversal
                movimiento_orig.debe, movimiento_orig.haber = (
                    movimiento_orig.haber,
                    movimiento_orig.debe,
                )
                movimiento_orig.save()

            # Mirror taxes with inverted signs if present
            for imp_orig in asiento_original.impuestos_documento.all():
                from ..models import ImpuestoDocumento
                ImpuestoDocumento.objects.create(
                    empresa_id=self.empresa_id,
                    asiento=asiento_reversal,
                    tipo=imp_orig.tipo,
                    base=imp_orig.base,
                    porcentaje=imp_orig.porcentaje,
                    valor=-imp_orig.valor,
                    cuenta_codigo=imp_orig.cuenta_codigo,
                    documento_origen_app=imp_orig.documento_origen_app,
                    documento_origen_modelo=imp_orig.documento_origen_modelo,
                    documento_origen_id=imp_orig.documento_origen_id,
                )

            return asiento_reversal

    # ========== Private methods ==========

    def _resolver_periodo(self, fecha) -> PeriodoContable:
        """
        Infer accounting period from transaction date.

        Periods are expected to be monthly, year-aligned.
        Raises PeriodoCerradoError if period closed or not found.

        Args:
            fecha: Transaction date

        Returns:
            Matching PeriodoContable instance
        """
        periodo = PeriodoContable.objects.filter(
            empresa_id=self.empresa_id,
            fecha_inicio__lte=fecha,
            fecha_fin__gte=fecha,
        ).first()

        if not periodo:
            raise ValueError(
                f"No existe periodo contable para {fecha} (empresa {self.empresa_id})"
            )

        return periodo

    def _validar_no_existe(self, documento_origen) -> None:
        """
        Verify no entry already exists for this source document.

        Idempotence check: prevents duplicate materialization.

        Raises:
            AsientoYaExisteError: If entry exists
        """
        if self.existe_asiento_para(
            documento_origen.app_label,
            documento_origen.modelo,
            documento_origen.id,
        ):
            raise AsientoYaExisteError(
                f"Asiento contable ya existe para {documento_origen.app_label}."
                f"{documento_origen.modelo}[{documento_origen.id}]"
            )

    def _construir_asiento(
        self,
        transaccion: TransaccionEconomica,
        periodo: PeriodoContable,
    ) -> AsientoContable:
        """
        Build journal entry object with resolved accounts and movements.

        Does NOT persist; returns unsaved instance with movements queued.

        Args:
            transaccion: Economic transaction DTO
            periodo: Target accounting period

        Returns:
            Unsaved AsientoContable with movimientos_por_guardar queued
        """
        asiento = AsientoContable(
            empresa_id=self.empresa_id,
            fecha=transaccion.fecha,
            numero=f"ASI-{transaccion.fecha.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            descripcion=transaccion.descripcion,
            periodo_contable=periodo,
            estado='BORRADOR',
            documento_origen_app=transaccion.documento_origen.app_label,
            documento_origen_modelo=transaccion.documento_origen.modelo,
            documento_origen_id=transaccion.documento_origen.id,
            documento_origen_numero=transaccion.documento_origen.numero,
            documento_origen_reversado=False,
        )

        movimientos = []
        debe_total = Decimal('0')
        haber_total = Decimal('0')

        for linea in transaccion.lineas:
            # Resolve PUC account
            cuenta_codigo = self.resolver.resolver_cuenta(
                linea.concepto,
                transaccion.tipo.value,
                linea.cuenta_hint,
                lado=linea.lado
            )

            # Build movement for principal line using lado to determine DEBE/HABER
            debe_principal = linea.monto if linea.lado == 'DEBE' else Decimal('0')
            haber_principal = linea.monto if linea.lado == 'HABER' else Decimal('0')

            movimiento_principal = MovimientoContable(
                empresa_id=self.empresa_id,
                asiento=asiento,  # Will be set on save
                cuenta_codigo=cuenta_codigo,
                descripcion=linea.concepto,
                debe=debe_principal,
                haber=haber_principal,
                tercero_nit=transaccion.tercero.nit if transaccion.tercero else None,
                tercero_razon_social=(
                    transaccion.tercero.razon_social if transaccion.tercero else None
                ),
                centro_costo_id=linea.centro_costo_id,
            )
            movimientos.append(movimiento_principal)
            debe_total += movimiento_principal.debe
            haber_total += movimiento_principal.haber

            # Build movements for each tax/deduction line using lado to determine DEBE/HABER
            for impuesto in linea.impuestos:
                cuenta_impuesto = self.resolver.resolver_cuenta(
                    impuesto.tipo,
                    transaccion.tipo.value,
                    lado=impuesto.lado
                )

                debe_impuesto = impuesto.valor if impuesto.lado == 'DEBE' else Decimal('0')
                haber_impuesto = impuesto.valor if impuesto.lado == 'HABER' else Decimal('0')

                movimiento_impuesto = MovimientoContable(
                    empresa_id=self.empresa_id,
                    asiento=asiento,
                    cuenta_codigo=cuenta_impuesto,
                    descripcion=f"{impuesto.tipo} ({impuesto.porcentaje}%)",
                    debe=debe_impuesto,
                    haber=haber_impuesto,
                    tercero_nit=(
                        transaccion.tercero.nit if transaccion.tercero else None
                    ),
                    tercero_razon_social=(
                        transaccion.tercero.razon_social if transaccion.tercero else None
                    ),
                    centro_costo_id=linea.centro_costo_id,
                )
                movimientos.append(movimiento_impuesto)
                debe_total += movimiento_impuesto.debe
                haber_total += movimiento_impuesto.haber

        asiento.debe_total = debe_total
        asiento.haber_total = haber_total
        asiento.movimientos_por_guardar = movimientos

        # Build ImpuestoDocumento instances from transaction level taxes
        impuestos_documento = []
        for imp_dto in transaccion.impuestos:
            cuenta_codigo = imp_dto.cuenta_codigo
            if not cuenta_codigo:
                try:
                    cuenta_codigo = self.resolver.resolver_cuenta(
                        imp_dto.tipo_impuesto,
                        transaccion.tipo.value,
                        lado='HABER'
                    )
                except Exception:
                    cuenta_codigo = None

            imp_doc = ImpuestoDocumento(
                empresa_id=self.empresa_id,
                tipo=imp_dto.tipo_impuesto,
                base=imp_dto.base_imponible,
                porcentaje=imp_dto.porcentaje,
                valor=imp_dto.valor,
                cuenta_codigo=cuenta_codigo,
                documento_origen_app=transaccion.documento_origen.app_label,
                documento_origen_modelo=transaccion.documento_origen.modelo,
                documento_origen_id=transaccion.documento_origen.id,
            )
            impuestos_documento.append(imp_doc)
        asiento.impuestos_documento_por_guardar = impuestos_documento

        return asiento
