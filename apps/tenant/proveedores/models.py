import uuid
from django.db import models

from apps.tenant.core.models import SintelTenantBaseModel  # auto-inserted by autocorrect
from apps.tenant.empresa.models import Empresa  # SSoT


class Proveedor(SintelTenantBaseModel):
    """
    Gestión de Proveedores y Acreedores (Normativa Colombia).
    SSoT: apps.tenant.empresa
    """
    TIPO_PERSONA = [("NATURAL", "Persona natural"), ("JURIDICA", "Persona jurídica")]
    TIPO_DOCUMENTO = [("NIT", "NIT"), ("CC", "Cédula de ciudadanía"), ("CE", "Cédula de extranjería"), ("PA", "Pasaporte")]
    REGIMEN = [("SIMPLE", "Régimen Simple"), ("ORDINARIO", "Régimen Ordinario"), ("NO_RESP", "No responsable de IVA")]
    
    # UUID Lookup Field (AGENTS.md §14)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    # SSoT
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='proveedores', db_index=True, help_text='SSoT Empresa')

    # Identificación Legal
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA, default="JURIDICA")
    tipo_documento = models.CharField(max_length=5, choices=TIPO_DOCUMENTO, default="NIT")
    numero_documento = models.CharField(max_length=32, help_text="Sin dígito de verificación")
    digito_verificacion = models.CharField(max_length=1, blank=True, null=True)
    razon_social = models.CharField(max_length=200, help_text="Nombre legal completo")
    nombre_comercial = models.CharField(max_length=200, blank=True, help_text="Nombre de marca o fantasía")

    
    # Tributario (Crítico para Colombia)
    regimen_tributario = models.CharField(max_length=15, choices=REGIMEN, default="ORDINARIO")
    actividad_economica_ciiu = models.CharField(max_length=10, blank=True, help_text="Código CIIU Principal")
    responsable_iva = models.BooleanField(default=True)
    gran_contribuyente = models.BooleanField(default=False)
    autoretenedor = models.BooleanField(default=False)

    # Retenciones (NUEVO v3.5.0)
    es_retenedor = models.BooleanField(default=False, verbose_name="Es Agente Retenedor")
    aplica_retefuente = models.BooleanField(default=False, verbose_name="Aplica Retención en la Fuente")
    retefuente_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Porcentaje Retefuente")
    aplica_reteica = models.BooleanField(default=False, verbose_name="Aplica Retención de ICA")
    reteica_porcentaje = models.DecimalField(max_digits=5, decimal_places=3, default=0, verbose_name="Porcentaje ReteICA")
    aplica_reteiva = models.BooleanField(default=False, verbose_name="Aplica Retención de IVA")
    reteiva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Porcentaje ReteIVA")


    # Contacto y Ubicación
    email_contacto = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=50, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)

    # Información Comercial y Bancaria
    plazo_pago_dias = models.PositiveIntegerField(default=30, help_text="Días de crédito estándar")
    banco = models.CharField(max_length=100, blank=True)
    tipo_cuenta = models.CharField(max_length=20, choices=[("AHORROS", "Ahorros"), ("CORRIENTE", "Corriente")], blank=True)
    numero_cuenta = models.CharField(max_length=50, blank=True)
    
    # Estado
    activo = models.BooleanField(default=True)
    
    # Mapeo Contable NIIF (v2.61.8)
    # WARNING: v2.61.8: Solo se permiten codigos de subcuenta (nivel 6) para Pasivos (Clase 2).
    # Este campo permite mapear el proveedor a una cuenta por pagar especifica.
    codigo_contable = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        help_text="Codigo NIIF de subcuenta (Clase 2)",
        db_index=True
    )

    cuenta_contable_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Pasivos/Proveedores)"
    )
    
    observaciones = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "tipo_documento", "numero_documento"], name="uniq_proveedor_empresa")
        ]
        indexes = [
            models.Index(fields=["empresa", "activo"]),
            models.Index(fields=["numero_documento"]),
            models.Index(fields=["razon_social"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.numero_documento})"