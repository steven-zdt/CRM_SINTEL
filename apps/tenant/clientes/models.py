import uuid
from django.db import models

from apps.tenant.core.models import SintelTenantBaseModel


class Cliente(SintelTenantBaseModel):
    """Legal and commercial customer record for a tenant."""

    TIPO_PERSONA = [
        ("NATURAL", "Persona natural"),
        ("JURIDICA", "Persona juridica"),
    ]
    TIPO_DOCUMENTO = [
        ("CC", "Cedula de ciudadania"),
        ("CE", "Cedula de extranjeria"),
        ("NIT", "NIT"),
        ("PA", "Pasaporte"),
    ]
    REGIMEN = [
        ("SIMPLE", "Regimen Simple"),
        ("ORDINARIO", "Regimen Ordinario"),
        ("NO_RESP", "No responsable de IVA"),
    ]

    # UUID Lookup Field (AGENTS.md §14)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA)
    tipo_documento = models.CharField(max_length=5, choices=TIPO_DOCUMENTO)
    numero_documento = models.CharField(max_length=32)
    razon_social = models.CharField(max_length=180)
    nombre_comercial = models.CharField(max_length=180, blank=True)
    regimen_tributario = models.CharField(max_length=15, choices=REGIMEN)
    
    # Retenciones (NUEVO v3.5.0)
    es_retenedor = models.BooleanField(default=False, verbose_name="Es Agente Retenedor")
    aplica_retefuente = models.BooleanField(default=False, verbose_name="Aplica Retención en la Fuente")
    retefuente_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Porcentaje Retefuente")
    aplica_reteica = models.BooleanField(default=False, verbose_name="Aplica Retención de ICA")
    reteica_porcentaje = models.DecimalField(max_digits=5, decimal_places=3, default=0, verbose_name="Porcentaje ReteICA")
    aplica_reteiva = models.BooleanField(default=False, verbose_name="Aplica Retención de IVA")
    reteiva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Porcentaje ReteIVA")
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=32, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=80, blank=True)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True, help_text="Observaciones adicionales")

    # [NEW v3.5.0] Vinculación con Contabilidad
    cuenta_contable_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Cartera)"
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_documento", "numero_documento"],
                name="uniq_doc_cliente_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activo"]),
            models.Index(fields=["numero_documento"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.numero_documento})"


class ContactoCliente(SintelTenantBaseModel):
    """Contact record attached to a customer."""

    # UUID Lookup Field (AGENTS.md §14)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="contactos",
        help_text="Cliente propietario del contacto",
    )
    nombre_completo = models.CharField(max_length=180, help_text="Nombre del contacto")
    cargo = models.CharField(max_length=100, blank=True, help_text="Cargo del contacto")
    email = models.EmailField(help_text="Correo del contacto")
    telefono = models.CharField(max_length=32, blank=True, help_text="Telefono del contacto")
    activo = models.BooleanField(default=True, help_text="Estado del contacto")
    is_principal = models.BooleanField(default=False, help_text="Marca el contacto principal")

    class Meta:
        verbose_name = "Contacto de Cliente"
        verbose_name_plural = "Contactos de Clientes"
        ordering = ["-is_principal", "nombre_completo"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "email"],
                name="uniq_contacto_cliente_email",
            )
        ]
        indexes = [
            models.Index(fields=["cliente", "activo"]),
            models.Index(fields=["cliente", "is_principal"]),
        ]

    def __str__(self):
        return f"{self.nombre_completo} ({self.email})"
