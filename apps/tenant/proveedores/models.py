"""
Modelo de datos para el modulo Proveedores.

SSoT: AUDITORIA_FLUJO_PROVEEDORES.md
Herencia: SintelTenantBaseModel (inyecta empresa, created_at, updated_at, save-guard)
UUID Lookup Field: AGENTS.md SS14
"""
import uuid

from django.db import models

from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa


class Proveedor(SintelTenantBaseModel):
    """
    Proveedor / Acreedor bajo normativa fiscal colombiana.

    SSoT: apps.tenant.empresa (Empresa FK)
    Campos heredados de SintelTenantBaseModel: empresa, created_at, updated_at
    """

    TIPO_PERSONA = [
        ("NATURAL", "Persona natural"),
        ("JURIDICA", "Persona juridica"),
    ]
    TIPO_DOCUMENTO = [
        ("NIT", "NIT"),
        ("CC", "Cedula de ciudadania"),
        ("CE", "Cedula de extranjeria"),
        ("PA", "Pasaporte"),
    ]
    REGIMEN = [
        ("SIMPLE", "Regimen Simple"),
        ("ORDINARIO", "Regimen Ordinario"),
        ("NO_RESP", "No responsable de IVA"),
    ]
    TIPO_CUENTA_BANCARIA = [
        ("AHORROS", "Ahorros"),
        ("CORRIENTE", "Corriente"),
    ]

    # --- UUID Lookup Field (AGENTS.md SS14) ---
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
    )

    # --- SSoT: Empresa (sobreescribe el FK generico de SintelTenantBaseModel) ---
    # NOTA: SintelTenantBaseModel ya inyecta empresa FK. Se mantiene aqui el
    # related_name personalizado para mantener compatibilidad con el ORM existente.
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="proveedores",
        db_index=True,
        help_text="SSoT Empresa del tenant",
    )

    # --- Identificacion Legal ---
    tipo_persona = models.CharField(
        max_length=10,
        choices=TIPO_PERSONA,
        default="JURIDICA",
    )
    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPO_DOCUMENTO,
        default="NIT",
    )
    numero_documento = models.CharField(
        max_length=32,
        help_text="Sin digito de verificacion",
    )
    digito_verificacion = models.CharField(
        max_length=1,
        blank=True,
        null=True,
    )
    razon_social = models.CharField(
        max_length=200,
        help_text="Nombre legal completo",
    )
    nombre_comercial = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nombre de marca o fantasia",
    )

    # --- Tributario (Critico para Colombia) ---
    regimen_tributario = models.CharField(
        max_length=15,
        choices=REGIMEN,
        default="ORDINARIO",
    )
    actividad_economica_ciiu = models.CharField(
        max_length=10,
        blank=True,
        help_text="Codigo CIIU Principal",
    )
    responsable_iva = models.BooleanField(default=True)
    gran_contribuyente = models.BooleanField(default=False)
    autoretenedor = models.BooleanField(default=False)

    # --- Retenciones (v3.5.0) ---
    es_retenedor = models.BooleanField(
        default=False,
        verbose_name="Es Agente Retenedor",
    )
    aplica_retefuente = models.BooleanField(
        default=False,
        verbose_name="Aplica Retencion en la Fuente",
    )
    retefuente_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Porcentaje Retefuente",
    )
    aplica_reteica = models.BooleanField(
        default=False,
        verbose_name="Aplica Retencion de ICA",
    )
    reteica_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=0,
        verbose_name="Porcentaje ReteICA",
    )
    aplica_reteiva = models.BooleanField(
        default=False,
        verbose_name="Aplica Retencion de IVA",
    )
    reteiva_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Porcentaje ReteIVA",
    )

    # --- Contacto y Ubicacion ---
    email_contacto = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=50, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    departamento = models.CharField(max_length=100, blank=True)

    # --- Informacion Comercial ---
    plazo_pago_dias = models.PositiveIntegerField(
        default=30,
        help_text="Dias de credito estandar",
    )

    # --- Informacion Bancaria ---
    banco = models.CharField(max_length=100, blank=True)
    tipo_cuenta = models.CharField(
        max_length=20,
        choices=TIPO_CUENTA_BANCARIA,
        blank=True,
    )
    numero_cuenta = models.CharField(max_length=50, blank=True)


    # --- Estado ---
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_documento", "numero_documento"],
                name="uniq_proveedor_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activo"]),
            models.Index(fields=["numero_documento"]),
            models.Index(fields=["razon_social"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.numero_documento})"


class CuentasPagar(SintelTenantBaseModel):

    """
    Cuentas por pagar a proveedores.

    Registra el estado de pago de cada factura de compra emitida por un proveedor.
    Permite saber exactamente cuanto debe la empresa a cada proveedor.

    Bounded Context (AGENTS.md SS2):
    - factura_uuid es referencia blanda a la app Facturas (sin FK directa).
    - La lectura de datos de factura se hace via FacturaInterAppAPI.

    Reglas de negocio (calculadas en save()):
    - saldo = valor_total - valor_pagado
    - estado SIN_PAGO  → valor_pagado == 0
    - estado PARCIAL   → 0 < valor_pagado < valor_total
    - estado PAGADA    → valor_pagado >= valor_total
    """

    ESTADO_PAGO = [
        ("SIN_PAGO", "Sin pago"),
        ("PARCIAL",  "Pago parcial"),
        ("PAGADA",   "Pagada"),
    ]

    uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False,
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="cuentas_pagar",
        db_index=True,
        help_text="SSoT Empresa del tenant",
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name="cuentas_pagar",
        db_index=True,
        help_text="Proveedor acreedor de la deuda",
    )

    # --- Factura de origen (Bounded Context) ---
    numero_factura = models.CharField(
        max_length=50,
        help_text="Numero de factura de compra o documento equivalente",
    )
    # Referencia blanda — sin FK directa a app facturas
    factura_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID de la Factura COMPRA de origen (soft reference, sin FK).",
    )
    fecha_emision = models.DateField(
        help_text="Fecha de expedicion de la factura de compra",
    )
    fecha_vencimiento = models.DateField(
        db_index=True,
        help_text="Fecha limite pactada para el pago",
    )

    # --- Control financiero ---
    valor_total = models.DecimalField(
        max_digits=18, decimal_places=2,
        help_text="Valor total de la factura incluyendo impuestos y retenciones",
    )
    valor_pagado = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Monto acumulado de abonos o pagos realizados",
    )
    saldo = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        editable=False,
        help_text="Saldo remanente = valor_total - valor_pagado (calculado automaticamente)",
    )

    estado_pago = models.CharField(
        max_length=15, choices=ESTADO_PAGO, default="SIN_PAGO", db_index=True,
    )

    # --- Trazabilidad del pago ---
    fecha_ultimo_pago = models.DateField(
        null=True, blank=True,
        help_text="Fecha del ultimo abono registrado",
    )
    referencia_pago = models.CharField(
        max_length=100, blank=True,
        help_text="Numero de comprobante o referencia del ultimo pago",
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Cuentas por Pagar"
        verbose_name_plural = "Cuentas por Pagar"
        ordering = ["fecha_vencimiento", "numero_factura"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "proveedor", "numero_factura"],
                name="uniq_cuentas_pagar_factura_proveedor",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "estado_pago"]),
            models.Index(fields=["empresa", "proveedor", "estado_pago"]),
            models.Index(fields=["numero_factura"]),
            models.Index(fields=["fecha_vencimiento"]),
            models.Index(fields=["factura_uuid"]),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} — {self.proveedor.razon_social} — {self.estado_pago}"

    def save(self, *args, **kwargs):
        """
        Calcula saldo y actualiza estado_pago antes de persistir.
        AGENTS.md: logica minima de calculo en save() — sin efectos secundarios.
        """
        from decimal import Decimal

        # 1. Sanitizar valor_pagado primero (ANTES de calcular saldo)
        if self.valor_pagado is None or self.valor_pagado < Decimal("0"):
            self.valor_pagado = Decimal("0")

        # 2. Calcular saldo con valor_pagado ya sanitizado
        self.saldo = self.valor_total - self.valor_pagado

        # 3. Derivar estado segun saldos
        if self.valor_pagado == Decimal("0"):
            self.estado_pago = "SIN_PAGO"
        elif self.saldo <= Decimal("0"):
            self.saldo = Decimal("0")
            self.estado_pago = "PAGADA"
        else:
            self.estado_pago = "PARCIAL"

        super().save(*args, **kwargs)


class Representante(SintelTenantBaseModel):
    """
    Representante legal o encargado autorizado de un Proveedor.

    SSoT: apps.tenant.empresa (Empresa FK), apps.tenant.proveedores (Proveedor FK)
    Campos heredados de SintelTenantBaseModel: empresa, created_at, updated_at
    Patrón: 1 Proveedor → N Representantes (pero normalmente 1 es principal)
    """

    TIPO_DOCUMENTO = [
        ("CC", "Cedula de ciudadania"),
        ("CE", "Cedula de extranjeria"),
        ("PA", "Pasaporte"),
        ("NIT", "NIT"),
    ]

    # --- UUID Lookup Field (AGENTS.md SS14) ---
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
    )

    # --- SSoT: Empresa (multi-tenant isolation) ---
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="representantes_proveedor",
        db_index=True,
        help_text="SSoT Empresa del tenant",
    )

    # --- SSoT: Proveedor (parent) ---
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name="representantes",
        db_index=True,
        help_text="Proveedor al que representa",
    )

    # --- Identificacion ---
    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPO_DOCUMENTO,
        default="CC",
        help_text="Tipo de documento de identificacion",
    )
    numero_documento = models.CharField(
        max_length=32,
        help_text="Numero de documento (sin digito verificador)",
    )
    nombre_completo = models.CharField(
        max_length=255,
        help_text="Nombre completo de la persona",
    )

    # --- Contacto ---
    email_contacto = models.EmailField(
        blank=True,
        help_text="Email de contacto directo",
    )
    telefono_contacto = models.CharField(
        max_length=50,
        blank=True,
        help_text="Numero de telefono de contacto",
    )

    # --- Organizacional ---
    cargo = models.CharField(
        max_length=100,
        default="Representante Legal",
        help_text="Titulo o rol en la organizacion",
    )
    es_principal = models.BooleanField(
        default=True,
        help_text="Si es True, es el representante principal para correspondencia oficial",
    )

    class Meta:
        verbose_name = "Representante"
        verbose_name_plural = "Representantes"
        ordering = ["-es_principal", "nombre_completo"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "proveedor", "numero_documento"],
                name="uniq_representante_empresa_proveedor_doc",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "proveedor"]),
            models.Index(fields=["empresa", "es_principal"]),
            models.Index(fields=["numero_documento"]),
            models.Index(fields=["email_contacto"]),
        ]

    def __str__(self):
        return f"{self.nombre_completo} ({self.numero_documento}) — {self.proveedor.razon_social}"