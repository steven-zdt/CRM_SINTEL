from django.db import models
from apps.tenant.empresa.models import Empresa  # SSoT

class Proveedor(models.Model):
    """
    Gestión de Proveedores y Acreedores (Normativa Colombia).
    SSoT: apps.tenant.empresa
    """
    TIPO_PERSONA = [("NATURAL", "Persona natural"), ("JURIDICA", "Persona jurídica")]
    TIPO_DOCUMENTO = [("NIT", "NIT"), ("CC", "Cédula de ciudadanía"), ("CE", "Cédula de extranjería"), ("PA", "Pasaporte")]
    REGIMEN = [("SIMPLE", "Régimen Simple"), ("ORDINARIO", "Régimen Ordinario"), ("NO_RESP", "No responsable de IVA")]
    
    # SSoT
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='proveedores', help_text='SSoT Empresa')

    # Identificación Legal
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA, default="JURIDICA")
    tipo_documento = models.CharField(max_length=5, choices=TIPO_DOCUMENTO, default="NIT")
    numero_documento = models.CharField(max_length=32, help_text="Sin dígito de verificación")
    digito_verificacion = models.CharField(max_length=1, blank=True, null=True)
    razon_social = models.CharField(max_length=200, help_text="Nombre legal completo")
    nombre_comercial = models.CharField(max_length=200, blank=True)

    # Tributario (Crítico para Colombia)
    regimen_tributario = models.CharField(max_length=15, choices=REGIMEN, default="ORDINARIO")
    actividad_economica_ciiu = models.CharField(max_length=10, blank=True, help_text="Código CIIU Principal")
    responsable_iva = models.BooleanField(default=True)
    gran_contribuyente = models.BooleanField(default=False)
    autoretenedor = models.BooleanField(default=False)

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