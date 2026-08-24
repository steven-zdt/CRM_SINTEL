# apps/tenant/facturas/models.py
"""
Modelos de facturación por tenant.

# WARNING: TENANT_APPS: cada tenant tiene sus propias facturas/ítems (aislamiento por esquema).
SSoT histórico: snapshots de emisor/receptor al momento de emisión.
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT


class Factura(SintelTenantBaseModel):
    class TipoFactura(models.TextChoices):
        FE = 'FE', _('Factura Electrónica')
        NC = 'NC', _('Nota Crédito')
        ND = 'ND', _('Nota Débito')

    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', _('Borrador')
        ENVIADA  = 'ENVIADA',  _('Enviada')
        ACEPTADA = 'ACEPTADA', _('Aceptada')
        RECHAZADA= 'RECHAZADA',_('Rechazada')
        # FISCAL-03: distingue "la DIAN rechazo el documento" (RECHAZADA,
        # respuesta real recibida) de "el intento de transmision fallo antes
        # de obtener una respuesta" (timeout, adaptador no configurado, error
        # de red -- ver ElectronicDocumentTransportPort.send(), FISCAL-02).
        ERROR_TRANSMISION = 'ERROR_TRANSMISION', _('Error de transmisión')
        ANULADA  = 'ANULADA',  _('Anulada')

    class EstadoPago(models.TextChoices):
        NO_PAGADA = 'NO_PAGADA', _('No Pagada')
        PAGO_PARCIAL = 'PAGO_PARCIAL', _('Pago Parcial')
        PAGADA = 'PAGADA', _('Pagada')

    # Naturaleza frente al tenant (compra/venta)
    class Naturaleza(models.TextChoices):
        VENTA  = 'VENTA',  _('Venta (emitida por el tenant)')
        COMPRA = 'COMPRA', _('Compra (recibida por el tenant)')

    # Clasificación de lo facturado (según ítems)
    class Categoria(models.TextChoices):
        PRODUCTO = 'PRODUCTO', _('Productos')
        SERVICIO = 'SERVICIO', _('Servicios')
        MIXTO    = 'MIXTO',    _('Mixto')

    # [v2.61.4] empresa FK heredada de SintelTenantBaseModel

    # Identificador único (v3.7.1: requerido para API lookup)
    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador único universal (usado en API URLs)'),
        null=False, blank=False
    )

    # Información básica
    numero = models.CharField(
        max_length=200, unique=True, verbose_name=_('Número de Factura'),
        help_text=_('Numero UBL: puede ser alfanumerico (FAxxxx) o hash SHA256 (96 chars). Max real encontrado: 96.')
    )
    prefijo = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Prefijo'))
    consecutivo = models.IntegerField(verbose_name=_('Consecutivo'))

    tipo = models.CharField(max_length=2, choices=TipoFactura.choices,
                            default=TipoFactura.FE, verbose_name=_('Tipo'))
    estado = models.CharField(max_length=20, choices=Estado.choices,
                              default=Estado.BORRADOR, verbose_name=_('Estado'))
    estado_pago = models.CharField(max_length=20, choices=EstadoPago.choices,
                                   default=EstadoPago.NO_PAGADA, verbose_name=_('Estado de Pago'))

    # Naturaleza frente al tenant y categoría de la operación
    # # WARNING: v2.60: Se calcula automáticamente comparando NIT del emisor con NIT de la empresa del tenant (SSoT)
    naturaleza = models.CharField(
        max_length=10, choices=Naturaleza.choices, null=True, blank=True,
        verbose_name=_('Naturaleza (venta/compra)'),
        help_text=_('VENTA si el tenant es emisor; COMPRA si el tenant es receptor. Se calcula automáticamente en importación UBL comparando NITs normalizados.')
    )
    categoria = models.CharField(
        max_length=10, choices=Categoria.choices, default=Categoria.SERVICIO,
        verbose_name=_('Categoría (producto/servicio/mixto)')
    )

    # UBL/DIAN metadatos
    ubl_version = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('UBL Version'))
    customization_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('CustomizationID'))
    profile_id = models.CharField(max_length=80, blank=True, null=True, verbose_name=_('ProfileID'))
    profile_execution_id = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('ProfileExecutionID'))
    invoice_type_code = models.CharField(max_length=4, blank=True, null=True, verbose_name=_('InvoiceTypeCode'))

    # Fechas
    fecha_emision = models.DateTimeField(verbose_name=_('Fecha/hora de Emisión'))
    fecha_vencimiento = models.DateField(blank=True, null=True, verbose_name=_('Fecha de Vencimiento'))

    # Snapshot emisor (empresa del tenant al momento de emisión)
    emisor_nit = models.CharField(max_length=20, verbose_name=_('NIT Emisor'))
    emisor_razon_social = models.CharField(max_length=200, verbose_name=_('Razón Social Emisor'))
    emisor_direccion = models.CharField(max_length=300, blank=True, null=True, verbose_name=_('Dirección Emisor'))
    emisor_email = models.CharField(max_length=120, blank=True, null=True, verbose_name=_('Email Emisor'))
    emisor_telefono = models.CharField(max_length=40, blank=True, null=True, verbose_name=_('Teléfono Emisor'))
    emisor_actividad_ciiu = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('CIIU Emisor'))

    # Snapshot receptor
    receptor_nit = models.CharField(max_length=20, verbose_name=_('NIT Receptor'))
    receptor_razon_social = models.CharField(max_length=200, verbose_name=_('Razón Social Receptor'))
    receptor_direccion = models.CharField(max_length=300, blank=True, null=True, verbose_name=_('Dirección Receptor'))
    receptor_email = models.CharField(max_length=120, blank=True, null=True, verbose_name=_('Email Receptor'))
    receptor_telefono = models.CharField(max_length=40, blank=True, null=True, verbose_name=_('Teléfono Receptor'))

    # Totales
    moneda = models.CharField(max_length=3, default='COP', verbose_name=_('Moneda'))
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                   validators=[MinValueValidator(Decimal('0.00'))])
    impuestos = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                    validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                validators=[MinValueValidator(Decimal('0.00'))])

    # Retenciones (v3.7.1: DEPRECATED - Movidas a Contabilidad.Retencion)

    # Formas de pago
    forma_pago = models.CharField(max_length=30, blank=True, null=True, verbose_name=_('Forma de pago'))
    medio_pago_codigo = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('PaymentMeansCode'))
    payment_due_date = models.DateField(blank=True, null=True, verbose_name=_('Fecha límite de pago'))
    
    # Vinculación Contable (v3.7)

    # Vinculación Cotización (v3.9.3) — Soft reference
    cotizacion_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("UUID de cotizacion vinculada (soft reference, permite orfandad)")
    )
    # Snapshot numero cotizacion (v3.10.1) — Evita N+1 en listado Tabulator
    cotizacion_numero = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Numero de la cotizacion vinculada (snapshot para Zero Waste queries)")
    )

    cliente_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("UUID del cliente vinculado para facturas de venta")
    )

    proveedor_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("UUID del proveedor vinculado para facturas de compra")
    )

    # DIAN / QR / CUFE y autorización
    # # WARNING: v2.60: Índice único para garantizar idempotencia en guardar_factura_desde_dto()
    # Django permite múltiples NULLs en campos únicos, así que esto garantiza unicidad cuando hay valor
    # # WARNING: v2.61.2: Pre-validación de idempotencia: fast_get_cufe() extrae CUFE con regex antes del parsing completo
    # Esto permite verificar duplicados en los primeros milisegundos sin cargar todo el XML en memoria
    cufe = models.CharField(
        max_length=200,   # max real encontrado: 96 chars. Ampliado para CUFEs largos futuros.
        blank=True,
        null=True,
        unique=True,  # # WARNING: CRÍTICO: Garantiza idempotencia por CUFE (clave legal de la DIAN)
        db_index=True,  # Índice adicional para búsquedas rápidas (usado por fast_get_cufe para pre-validación)
        verbose_name=_('CUFE'), 
        help_text=_('Código Único de Facturación Electrónica (clave legal de la DIAN para idempotencia). Usado para pre-validación rápida en batch processing.')
    )
    qr_code = models.TextField(blank=True, null=True, verbose_name=_('QR raw'), help_text=_('Texto multilínea del código QR'))
    qr_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name=_('URL QR DIAN'), help_text=_('URL del código QR (puede ser muy larga)'))
    autorizacion_numero = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Autorización DIAN'))
    autorizacion_prefijo = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Prefijo autorizado'))
    autorizacion_rango_desde = models.IntegerField(blank=True, null=True, verbose_name=_('Rango desde'))
    autorizacion_rango_hasta = models.IntegerField(blank=True, null=True, verbose_name=_('Rango hasta'))
    autorizacion_vigencia_inicio = models.DateField(blank=True, null=True, verbose_name=_('Vigencia inicio'))
    autorizacion_vigencia_fin = models.DateField(blank=True, null=True, verbose_name=_('Vigencia fin'))

    # Respuesta DIAN (ApplicationResponse) / estado de validación
    dian_validation_code = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Código Validación DIAN'))
    dian_validation_desc = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Descripción Validación'))
    dian_validation_fecha = models.DateField(blank=True, null=True, verbose_name=_('Fecha Validación'))
    dian_validation_hora = models.TimeField(blank=True, null=True, verbose_name=_('Hora Validación'))
    dian_response_xml = models.TextField(blank=True, null=True, verbose_name=_('ApplicationResponse XML'))

    # XML (# WARNING: DEPRECADO: usar FacturaAnexos.ubl_xml en su lugar)
    # Mantenido por compatibilidad durante migración
    xml_content = models.TextField(blank=True, null=True, verbose_name=_('XML UBL completo (Deprecado)'))
    # F26: xml_file_path removido -- auditoria de codigo real confirmo 0
    # escritores y 0 lectores en todo el repo (solo aparecia en admin.py sin
    # uso real), y 0 filas con dato en las 3 empresas del entorno
    # (SELECT COUNT(*) WHERE xml_file_path IS NOT NULL AND != '' = 0 en
    # home/qaisotest/shelltest1). Ver F26_FINDINGS.md y migracion
    # 0032_remove_factura_xml_file_path.py.

    # Sede — vinculacion para indicadores y KPIs por sede (DT-SEDE-02)
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas',
        verbose_name=_('Sede'),
        help_text=_('Sede de la empresa que emite o recibe la factura. '
                    'Opcional — si no se asigna aplica a toda la empresa.'),
        db_index=True,
    )

    # [v2.61.4] created_at y updated_at heredados de SintelTenantBaseModel

    class Meta:
        verbose_name = _('Factura')
        verbose_name_plural = _('Facturas')
        ordering = ['-fecha_emision', '-consecutivo']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['fecha_emision'], condition=models.Q(estado='ACEPTADA'), name='idx_fact_aceptadas_fecha'),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['estado']),
            models.Index(fields=['naturaleza']),  # # WARNING: v2.60: Índice para filtrar por VENTA/COMPRA
            # # WARNING: v2.60: cufe tiene unique=True y db_index=True, no necesita índice adicional aquí
            models.Index(fields=['empresa_id', 'cliente_uuid'], name='idx_fact_empresa_cliente_uuid'),
            models.Index(fields=['empresa_id', 'proveedor_uuid'], name='idx_fact_empresa_prov_uuid'),
        ]
        # # WARNING: v2.60: Constraint único por cufe garantiza idempotencia (definido en el campo con unique=True)
        # Django permite múltiples NULLs en campos únicos, así que esto funciona correctamente

    @property
    def tiene_nota_credito(self) -> bool:
        """Verifica si la factura tiene una nota crédito asociada."""
        return hasattr(self, "nota_credito")

    # WARNING: [ARQ-C1] Las 3 properties de retencion delegan en RetencionesService
    # (Pull Model, ADR-001) en vez de consultar apps.tenant.contabilidad.models.Retencion
    # directamente. Ademas de respetar la capa de servicio, RetencionesService exige
    # empresa_id (Zero-Trust) -- las consultas directas anteriores no filtraban por
    # empresa_id.

    @property
    def total_retencion_fuente(self) -> Decimal:
        """Lee RETEFUENTE desde Contabilidad via RetencionesService (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            return RetencionesService.total_retenciones_por_documento(
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=self.id,
                empresa_id=self.empresa_id,
                tipo='RETEFUENTE',
            )
        except Exception:
            return Decimal('0.00')

    @property
    def total_reteica(self) -> Decimal:
        """Lee RETEICA desde Contabilidad via RetencionesService (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            return RetencionesService.total_retenciones_por_documento(
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=self.id,
                empresa_id=self.empresa_id,
                tipo='RETEICA',
            )
        except Exception:
            return Decimal('0.00')

    @property
    def total_reteiva(self) -> Decimal:
        """Lee RETEIVA desde Contabilidad via RetencionesService (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            return RetencionesService.total_retenciones_por_documento(
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=self.id,
                empresa_id=self.empresa_id,
                tipo='RETEIVA',
            )
        except Exception:
            return Decimal('0.00')

    # ── Pull Model: Bancos (v3.11.0, ADR-001) ──────────────────────────────
    # medio_pago_codigo == '10' significa "Efectivo" segun catalogo DIAN.
    # Para pagos en efectivo no se requiere conciliacion bancaria.

    @property
    def total_pagado_bancos(self) -> Decimal:
        """
        [Pull Model v3.11.0] Total conciliado en bancos para esta factura.
        Lee de TransaccionBancaria via BancosBridge (sin FK directa).
        Retorna 0.00 si el objeto no esta guardado aun.
        """
        if not self.pk or not self.empresa_id:
            return Decimal('0.00')
        try:
            from apps.tenant.facturas.services.selectors import BancosBridge
            return BancosBridge.obtener_total_conciliado(self.empresa_id, self.uuid)
        except Exception:
            return Decimal('0.00')

    @property
    def saldo_pendiente(self) -> Decimal:
        """
        [Pull Model v3.11.0] Diferencia entre total factura y lo conciliado en bancos.
        Nunca negativo: max(0, total - total_pagado_bancos).
        """
        return max(Decimal('0.00'), (self.total or Decimal('0.00')) - self.total_pagado_bancos)

    def __str__(self):
        cufe_str = f" | {self.cufe}" if self.cufe else ""
        return f"{self.numero}{cufe_str}"

    def save(self, *args, **kwargs):
        # SSoT singleton fallback for legacy creation paths/tests.
        if not self.empresa_id:
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.only('id').first()
            if empresa:
                self.empresa = empresa
        if self.consecutivo is None:
            self.consecutivo = 0
        if not self.fecha_emision:
            self.fecha_emision = timezone.now()
        if self.total is None or self.total == Decimal('0.00'):
            self.total = (self.subtotal or Decimal('0.00')) + (self.impuestos or Decimal('0.00'))
        super().save(*args, **kwargs)


class ItemFactura(SintelTenantBaseModel):
    class TipoItemInventario(models.TextChoices):
        PRODUCTO = 'PRODUCTO', _('Producto de Inventario')
        SERVICIO = 'SERVICIO', _('Servicio de Inventario')

    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador publico del item de factura'),
    )
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items', verbose_name=_('Factura'))
    
    # [v2.61.4] empresa FK heredada de SintelTenantBaseModel
    
    # UBL: ID de línea y codificación estándar si existe
    linea_id = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('ID línea UBL'))
    codigo = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Código del ítem'))
    descripcion = models.CharField(max_length=500, verbose_name=_('Descripción'))

    # Referencia blanda hacia Inventario (no FK, respeta snapshot documental)
    item_inventario_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text=_('UUID del Producto o Servicio de Inventario. Referencia soft, sin FK.')
    )
    item_inventario_tipo = models.CharField(
        max_length=10,
        choices=TipoItemInventario.choices,
        null=True, blank=True,
        help_text=_('Tipo de item de inventario referenciado.')
    )
    item_inventario_codigo = models.CharField(
        max_length=50, null=True, blank=True,
        help_text=_('Snapshot del codigo de inventario al momento de vincular.')
    )

    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'),
                                   validators=[MinValueValidator(Decimal('0.01'))])
    unidad_medida = models.CharField(max_length=10, default='UND', verbose_name=_('Unidad de Medida'),
                                     help_text=_('Ej: UN, ZZ, UND'))
    valor_unitario = models.DecimalField(max_digits=15, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0.00'))])

    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])
    valor_iva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                    validators=[MinValueValidator(Decimal('0.00'))])

    # Retenciones por ítem (v3.7.1: DEPRECATED - Movidas a Contabilidad.Retencion)
    porcentaje_retefuente = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                                validators=[MinValueValidator(Decimal('0.00'))],
                                                null=True, blank=True, editable=False,
                                                verbose_name=_('% Retención Fuente [DEPRECATED v3.7.1]'))
    valor_retefuente = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                           validators=[MinValueValidator(Decimal('0.00'))],
                                           null=True, blank=True, editable=False,
                                           verbose_name=_('Valor Retención Fuente [DEPRECATED v3.7.1]'))
    porcentaje_reteiva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                             validators=[MinValueValidator(Decimal('0.00'))],
                                             null=True, blank=True, editable=False,
                                             verbose_name=_('% ReteIVA [DEPRECATED v3.7.1]'))
    valor_reteiva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                        validators=[MinValueValidator(Decimal('0.00'))],
                                        null=True, blank=True, editable=False,
                                        verbose_name=_('Valor ReteIVA [DEPRECATED v3.7.1]'))
    porcentaje_reteica = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                             validators=[MinValueValidator(Decimal('0.00'))],
                                             null=True, blank=True, editable=False,
                                             verbose_name=_('% ReteICA [DEPRECATED v3.7.1]'))
    valor_reteica = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                        validators=[MinValueValidator(Decimal('0.00'))],
                                        null=True, blank=True, editable=False,
                                        verbose_name=_('Valor ReteICA [DEPRECATED v3.7.1]'))

    subtotal = models.DecimalField(max_digits=15, decimal_places=2,
                                   validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2,
                                validators=[MinValueValidator(Decimal('0.00'))])

    # Derivación: servicio vs producto (heurística por unitCode y/o keywords)
    es_servicio = models.BooleanField(default=False, verbose_name=_('¿Es servicio?'))

    orden = models.IntegerField(default=1, verbose_name=_('Orden'))

    class Meta:
        verbose_name = _('Ítem de Factura')
        verbose_name_plural = _('Ítems de Factura')
        ordering = ['factura', 'orden']

    def __str__(self):
        return f"{self.factura.numero} - {self.descripcion[:50]}"

    def save(self, *args, **kwargs):
        # # WARNING: v2.40: Auto-asignar empresa desde factura si no está asignada
        if not self.empresa_id and self.factura_id:
            self.empresa = self.factura.empresa

        self.subtotal = (self.cantidad or Decimal('0.00')) * (self.valor_unitario or Decimal('0.00'))
        self.valor_iva = (self.subtotal or Decimal('0.00')) * ((self.porcentaje_iva or Decimal('0.00')) / Decimal('100.00'))
        self.total = (self.subtotal or Decimal('0.00')) + (self.valor_iva or Decimal('0.00'))
        # Heurística simple: unitCode 'ZZ' suele usarse en servicios (ajustable por catálogo propio)
        if self.unidad_medida and self.unidad_medida.upper() in {'ZZ'}:
            self.es_servicio = True
        super().save(*args, **kwargs)

    # WARNING: [ARQ-C1] Delegar en RetencionesService (Pull Model, ADR-001) en vez de
    # consultar apps.tenant.contabilidad.models.Retencion directamente -- ver nota en
    # Factura.total_retencion_fuente.

    @property
    def total_retefuente_item(self) -> Decimal:
        """[v3.7.1 Backward Compat] Suma total de Retencion(tipo='RETEFUENTE') para este item."""
        if not self.pk:
            return self.valor_retefuente or Decimal('0.00')
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            return RetencionesService.total_retenciones_por_documento(
                documento_origen_app='facturas',
                documento_origen_modelo='ItemFactura',
                documento_origen_id=self.id,
                empresa_id=self.empresa_id,
                tipo='RETEFUENTE',
            )
        except Exception:
            return self.valor_retefuente or Decimal('0.00')

    @property
    def total_reteiva_item(self) -> Decimal:
        """[v3.7.1 Backward Compat] Suma total de Retencion(tipo='RETEIVA') para este item."""
        if not self.pk:
            return self.valor_reteiva or Decimal('0.00')
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            return RetencionesService.total_retenciones_por_documento(
                documento_origen_app='facturas',
                documento_origen_modelo='ItemFactura',
                documento_origen_id=self.id,
                empresa_id=self.empresa_id,
                tipo='RETEIVA',
            )
        except Exception:
            return self.valor_reteiva or Decimal('0.00')

    @property
    def total_reteica_item(self) -> Decimal:
        """[v3.7.1 Backward Compat] Suma total de Retencion(tipo='RETEICA') para este item."""
        if not self.pk:
            return self.valor_reteica or Decimal('0.00')
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            return RetencionesService.total_retenciones_por_documento(
                documento_origen_app='facturas',
                documento_origen_modelo='ItemFactura',
                documento_origen_id=self.id,
                empresa_id=self.empresa_id,
                tipo='RETEICA',
            )
        except Exception:
            return self.valor_reteica or Decimal('0.00')



# --- Tracking de ejecuciones de ingesta por correo (por tenant) ---
class MailIngestionRun(SintelTenantBaseModel):
    """
    Registro de ejecución de ingesta de facturas desde correo.
    
    # WARNING: TENANT_APPS: Cada tenant tiene sus propios registros (aislamiento por esquema).
    # WARNING: CERO SIGNALS: La tarea Celery actualiza este modelo directamente (sin signals).
    """
    STATUS_CHOICES = [
        ("PENDING", "PENDING"),
        ("RUNNING", "RUNNING"),
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),  # Cambiar de FAILURE a FAILED para consistencia
        ("CANCEL_REQUESTED", "CANCEL_REQUESTED"),  # ← Clave para cancelación cooperativa
        ("CANCELED", "CANCELED"),
        ("ABORTED", "ABORTED"),  # Mantener por compatibilidad
    ]
    
    started_by = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mail_ingestion_runs',
        verbose_name=_('Iniciado por'),
        help_text=_('Operador del tenant que inició la ingesta de correo')
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Iniciado'))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Finalizado'))
    task_id = models.CharField(max_length=128, db_index=True, unique=True, verbose_name=_('ID Tarea Celery'))
    naturaleza = models.CharField(
        max_length=10,
        default="VENTA",
        choices=Factura.Naturaleza.choices,
        verbose_name=_('Naturaleza')
    )
    status = models.CharField(
        max_length=20,  # Aumentar para CANCEL_REQUESTED
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,  # Índice para consultas rápidas de estado
        verbose_name=_('Estado')
    )
    # Conteos resumidos y detalles (ligeros) — JSON-only
    counts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Conteos'),
        help_text=_('Métricas: xml_detected, imported, duplicates, errors')
    )
    summary = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Resumen'),
        help_text=_('Detalles de ejecución (JSON)')
    )
    
    class Meta:
        verbose_name = _('Ejecución de Ingesta por Correo')
        verbose_name_plural = _('Ejecuciones de Ingesta por Correo')
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"MailIngestionRun(task={self.task_id}, status={self.status})"


# --- Estado del buzón para procesamiento incremental (por tenant) ---
class MailInboxState(SintelTenantBaseModel):
    """
    Estado del procesamiento IMAP de un buzón de correo.
    
    Rastrea el último UID procesado para permitir procesamiento incremental eficiente.
    
    # WARNING: TENANT_APPS: Cada tenant tiene sus propios estados (aislamiento por esquema).
    # WARNING: SSoT: Relacionado con MailInboxConfig de empresa.
    # WARNING: UID IMAP: Los UIDs son únicos y persistentes por buzón (no cambian al eliminar mensajes).
    
    Reglas:
    - Si last_seen_uid es NULL → primera ejecución (procesar histórico completo desde UID 1).
    - Si existe → solo procesar UIDs mayores a last_seen_uid (incremental).
    """
    mailbox_config = models.ForeignKey(
        'empresa.MailInboxConfig',
        on_delete=models.CASCADE,
        related_name='inbox_states',
        verbose_name=_('Configuración de buzón'),
        help_text=_('Configuración de correo asociada')
    )
    last_seen_uid = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Último UID procesado'),
        help_text=_('Último UID IMAP procesado. NULL = primera ejecución (histórico completo)')
    )
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Última ejecución'),
        help_text=_('Fecha/hora de la última ejecución exitosa')
    )
    total_processed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total procesados'),
        help_text=_('Total acumulado de mensajes procesados')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    class Meta:
        verbose_name = _('Estado de Buzón IMAP')
        verbose_name_plural = _('Estados de Buzón IMAP')
        unique_together = [['mailbox_config']]  # Un estado por configuración
        indexes = [
            models.Index(fields=['mailbox_config', 'last_seen_uid']),
            models.Index(fields=['last_run_at']),
        ]
    
    def __str__(self):
        uid_str = str(self.last_seen_uid) if self.last_seen_uid else "NULL (histórico)"
        return f"MailInboxState(config={self.mailbox_config_id}, last_uid={uid_str})"


class FacturaAnexos(SintelTenantBaseModel):
    """
    Anexos de factura (XMLs grandes separados de la fila principal).
    
    # WARNING: OPTIMIZACIÓN: Evita cargar blobs en listados.
    # WARNING: ONE-TO-ONE: Una factura tiene un único registro de anexos.
    # WARNING: TENANT_APPS: Aislado por esquema (django-tenants).
    """
    factura = models.OneToOneField(
        Factura,
        on_delete=models.CASCADE,
        related_name='anexos',
        verbose_name=_('Factura'),
        help_text=_('Factura asociada')
    )
    
    # UBL principal (invoice)
    ubl_xml = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('XML UBL completo'),
        help_text=_('Contenido completo del XML UBL de la factura')
    )
    
    # ApplicationResponse / AttachedDocument / otros adjuntos DIAN
    application_response_xml = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('ApplicationResponse XML'),
        help_text=_('XML de respuesta de la DIAN (ApplicationResponse)')
    )
    
    # PDF físico (representación gráfica de la factura)
    pdf_file = models.FileField(
        upload_to='facturas/pdfs/',
        null=True,
        blank=True,
        verbose_name=_('Archivo PDF'),
        help_text=_('Archivo PDF de la factura (representación gráfica)')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha de Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha de Actualización'))
    
    class Meta:
        verbose_name = _('Anexo de Factura')
        verbose_name_plural = _('Anexos de Factura')
        db_table = 'facturas_factura_anexos'
    
    def __str__(self):
        return f"FacturaAnexos(factura={self.factura.numero})"

    def save(self, *args, **kwargs):
        # Keep tenant ownership explicit for base-model guardrails.
        if not self.empresa_id and self.factura_id and self.factura.empresa_id:
            self.empresa = self.factura.empresa
        super().save(*args, **kwargs)


class NotaCredito(SintelTenantBaseModel):
    """
    Nota Crédito UBL 2.1 (una por factura). Idempotencia por CUDE.
    
    # WARNING: ONE-TO-ONE: Una factura tiene una única nota crédito.
    # WARNING: PROTECT: Evita borrar nota crédito al borrar factura accidentalmente.
    # WARNING: TENANT_APPS: Aislado por esquema (django-tenants).
    # WARNING: INMUTABILIDAD: Las notas crédito son documentos históricos (solo creación/eliminación).
    """
    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador publico de la nota credito'),
    )
    factura = models.OneToOneField(
        Factura,
        related_name="nota_credito",
        on_delete=models.PROTECT,  # # WARNING: Evita cascada accidental
        help_text=_("Factura a la que aplica esta Nota Crédito (1:1)."),
        verbose_name=_('Factura')
    )
    
    # [v2.61.4] empresa FK heredada de SintelTenantBaseModel
    numero = models.CharField(
        max_length=200,   # alineado con Factura.numero — puede ser hash UBL
        unique=True,
        verbose_name=_('Número de Nota Crédito'),
        help_text=_('Ej: NC135')
    )
    cude = models.CharField(
        max_length=200,   # alineado con Factura.cufe
        blank=True,
        null=True,  # F26-006: permite multiples NC sin CUDE sin chocar la unique constraint (mismo patron que Factura.cufe)
        unique=True,
        verbose_name=_('CUDE'),
        help_text=_('Código Único de Documento Electrónico (identificador legal de la nota)')
    )
    fecha_emision = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Fecha/hora de Emisión')
    )
    moneda = models.CharField(
        max_length=8,
        default="COP",
        verbose_name=_('Moneda')
    )

    # Totales (alineado a LegalMonetaryTotal del XML)
    subtotal = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Subtotal')
    )
    impuestos = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Impuestos')
    )
    total = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total')
    )

    # Retenciones (v2.62: Reversión de retenciones en Nota Crédito)
    retefuente = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                     validators=[MinValueValidator(Decimal('0.00'))],
                                     verbose_name=_('Retención en la Fuente'))
    reteica = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                  validators=[MinValueValidator(Decimal('0.00'))],
                                  verbose_name=_('ReteICA'))
    reteiva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                  validators=[MinValueValidator(Decimal('0.00'))],
                                  verbose_name=_('ReteIVA'))

    # Motivo y referencia a la factura original (redundancia para consultas rápidas)
    motivo = models.TextField(
        blank=True,
        default="",
        verbose_name=_('Motivo'),
        help_text=_('Motivo de la nota crédito')
    )
    ref_factura_numero = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_('Número Factura Referenciada'),
        help_text=_('Número de la factura a la que aplica esta nota crédito')
    )
    ref_factura_cufe = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name=_('CUFE Factura Referenciada'),
        help_text=_('CUFE de la factura a la que aplica esta nota crédito')
    )

    # XML almacenado para endpoint pesado dedicado
    xml_content = models.TextField(
        blank=True,
        default="",
        verbose_name=_('XML UBL completo'),
        help_text=_('Contenido completo del XML UBL de la nota crédito')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Creado')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Actualizado')
    )

    class Meta:
        verbose_name = _('Nota Crédito')
        verbose_name_plural = _('Notas Crédito')
        ordering = ['-fecha_emision', '-created_at']
        indexes = [
            models.Index(fields=['cude']),
            models.Index(fields=['numero']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['factura']),
        ]
        constraints = [
            # # WARNING: COHERENCIA: Si se declara ref CUFE/número, deberían coincidir con la factura
            # (validación en service layer; aquí se omite constraint complejo por portabilidad)
        ]

    def __str__(self):
        return f"NC {self.numero} | {self.cude}"

    @property
    def factura_original(self):
        """Alias de compatibilidad para la factura afectada por la nota credito."""
        return self.factura


class ItemNotaCredito(SintelTenantBaseModel):
    """
    Linea de Nota Credito (CreditNoteLine UBL). Espejo minimo de ItemFactura --
    mismo patron de referencia soft hacia Inventario (item_inventario_uuid,
    sin FK real), sin los campos de retencion por linea (ya deprecados en
    ItemFactura y no requeridos aqui: las retenciones de NC se manejan a nivel
    de cabecera, ver NotaCredito.retefuente/reteica/reteiva).
    """
    class TipoItemInventario(models.TextChoices):
        PRODUCTO = 'PRODUCTO', _('Producto de Inventario')
        SERVICIO = 'SERVICIO', _('Servicio de Inventario')

    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador publico del item de nota credito'),
    )
    nota_credito = models.ForeignKey(
        NotaCredito, on_delete=models.CASCADE, related_name='items',
        verbose_name=_('Nota Credito'),
    )

    # UBL: ID de linea y codificacion estandar si existe
    linea_id = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('ID linea UBL'))
    codigo = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Codigo del item'))
    descripcion = models.CharField(max_length=500, verbose_name=_('Descripcion'))

    # Referencia blanda hacia Inventario (no FK, respeta snapshot documental) --
    # mismo patron que ItemFactura.item_inventario_uuid. Se resuelve por
    # coincidencia de codigo contra el catalogo de Producto al momento de
    # importar la NC (ver FacturaBusinessService.guardar_desde_dto).
    item_inventario_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text=_('UUID del Producto o Servicio de Inventario. Referencia soft, sin FK.')
    )
    item_inventario_tipo = models.CharField(
        max_length=10,
        choices=TipoItemInventario.choices,
        null=True, blank=True,
        help_text=_('Tipo de item de inventario referenciado.')
    )
    item_inventario_codigo = models.CharField(
        max_length=50, null=True, blank=True,
        help_text=_('Snapshot del codigo de inventario al momento de vincular.')
    )

    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'),
                                   validators=[MinValueValidator(Decimal('0.01'))])
    unidad_medida = models.CharField(max_length=10, default='UND', verbose_name=_('Unidad de Medida'))
    valor_unitario = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])

    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])
    valor_iva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                    validators=[MinValueValidator(Decimal('0.00'))])

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                   validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                validators=[MinValueValidator(Decimal('0.00'))])

    es_servicio = models.BooleanField(default=False, verbose_name=_('Es servicio?'))
    orden = models.IntegerField(default=1, verbose_name=_('Orden'))

    class Meta:
        verbose_name = _('Item de Nota Credito')
        verbose_name_plural = _('Items de Nota Credito')
        ordering = ['nota_credito', 'orden']

    def __str__(self):
        return f"{self.nota_credito.numero} - {self.descripcion[:50]}"

    def save(self, *args, **kwargs):
        """Calcula total automáticamente si no está definido."""
        # Auto-asignar empresa desde nota_credito si no está asignada
        if not self.empresa_id and self.nota_credito_id:
            self.empresa = self.nota_credito.empresa

        if self.total is None or self.total == Decimal('0.00'):
            self.total = (self.subtotal or Decimal('0.00')) + (self.valor_iva or Decimal('0.00'))
        super().save(*args, **kwargs)


# Backward-compat alias for legacy imports in tests and old modules.
NaturalezaFactura = Factura.Naturaleza

# SINTEL v3.5 Secure Update Configuration Sets
MANUAL_EDITABLE_FIELDS = [
    'estado',
    'estado_pago',
    'categoria',
    'fecha_vencimiento',
    'payment_due_date',
    'forma_pago',
    'medio_pago_codigo',
    # F26: 'orden_compra' removido -- campo fantasma, Factura nunca lo tuvo
    # (confirmado por auditoria de codigo real, ver F26_FINDINGS.md). Un PATCH
    # que lo incluyera habria llegado a factura.save(update_fields=[...,
    # 'orden_compra']) y Django lo hubiera rechazado con ValueError (campo
    # inexistente en el modelo) -- riesgo real de 500 nunca ejercitado.
    'cotizacion_uuid',
    'cotizacion_numero',
    'sede',  # [OSF Fase F11] antes solo informativa/reporting (DT-SEDE-02)
]

XML_IMMUTABLE_FIELDS = {
    'numero',
    'prefijo',
    'consecutivo',
    'tipo',
    'naturaleza',
    'fecha_emision',
    'emisor_nit',
    'emisor_razon_social',
    'emisor_direccion',
    'emisor_email',
    'emisor_telefono',
    'emisor_actividad_ciiu',
    'receptor_nit',
    'receptor_razon_social',
    'receptor_direccion',
    'receptor_email',
    'receptor_telefono',
    'moneda',
    'subtotal',
    'impuestos',
    'total',
    'cufe',
    'qr_code',
    'qr_url',
    'autorizacion_numero',
    'autorizacion_prefijo',
    'autorizacion_rango_desde',
    'autorizacion_rango_hasta',
    'autorizacion_vigencia_inicio',
    'autorizacion_vigencia_fin',
}


class FacturaImpuesto(SintelTenantBaseModel):
    class TipoImpuesto(models.TextChoices):
        IVA = 'IVA', _('IVA')
        INC = 'INC', _('Impuesto Nacional al Consumo')
        RETEFUENTE = 'RETEFUENTE', _('Retencion en la Fuente')
        RETEIVA = 'RETEIVA', _('Retencion de IVA')
        RETEICA = 'RETEICA', _('Retencion de ICA')
        OTRO = 'OTRO', _('Otro Impuesto')

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name='impuestos_desglosados',
        verbose_name=_('Factura')
    )
    tipo_impuesto = models.CharField(
        max_length=20,
        choices=TipoImpuesto.choices,
        verbose_name=_('Tipo de Impuesto')
    )
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Porcentaje')
    )
    base_imponible = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Base Imponible')
    )
    valor_impuesto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Valor Impuesto')
    )

    class Meta:
        verbose_name = _('Impuesto Desglosado')
        verbose_name_plural = _('Impuestos Desglosados')
        db_table = 'factura_impuestos'

    def __str__(self):
        return f"{self.tipo_impuesto} ({self.porcentaje}%): {self.valor_impuesto}"


