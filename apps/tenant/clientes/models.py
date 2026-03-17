from django.db import models
from apps.tenant.empresa.models import Empresa  # SSoT

class Cliente(models.Model):
    """
    Información legal y comercial de clientes (Microempresa Colombia).
    SSoT: apps.tenant.empresa
    """
    TIPO_PERSONA = [("NATURAL", "Persona natural"), ("JURIDICA", "Persona jurídica")]
    TIPO_DOCUMENTO = [("CC", "Cédula de ciudadanía"), ("CE", "Cédula de extranjería"), ("NIT", "NIT"), ("PA", "Pasaporte")]
    REGIMEN = [("SIMPLE", "Régimen Simple"), ("ORDINARIO", "Régimen Ordinario"), ("NO_RESP", "No responsable de IVA")]

    # Identificación
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='clientes', help_text='SSoT')
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA)
    tipo_documento = models.CharField(max_length=5, choices=TIPO_DOCUMENTO)
    numero_documento = models.CharField(max_length=32)
    razon_social = models.CharField(max_length=180)
    nombre_comercial = models.CharField(max_length=180, blank=True)

    # Tributario & Contacto
    regimen_tributario = models.CharField(max_length=15, choices=REGIMEN)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=32, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=80, blank=True)
    
    # Comercial
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "tipo_documento", "numero_documento"], name="uniq_doc_cliente_empresa")
        ]
        indexes = [
            models.Index(fields=["empresa", "activo"]),
            models.Index(fields=["numero_documento"]),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.numero_documento})"


class ContactoCliente(models.Model):
    """
    Contactos asociados a un cliente (personas de contacto).
    Permite múltiples contactos por cliente con información de cargo, email y teléfono.
    """
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='contactos',
        help_text='Cliente al que pertenece este contacto'
    )
    nombre_completo = models.CharField(max_length=180, help_text='Nombre completo del contacto')
    cargo = models.CharField(max_length=100, blank=True, help_text='Cargo o posición del contacto')
    email = models.EmailField(help_text='Email de contacto')
    telefono = models.CharField(max_length=32, blank=True, help_text='Teléfono de contacto')
    activo = models.BooleanField(default=True, help_text='Indica si el contacto está activo')
    is_principal = models.BooleanField(
        default=False, 
        help_text='Indica si este es el contacto principal del cliente'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contacto de Cliente"
        verbose_name_plural = "Contactos de Clientes"
        ordering = ["-is_principal", "nombre_completo"]
        unique_together = [
            ['cliente', 'email']  # Evita emails duplicados en el mismo cliente
        ]
        indexes = [
            models.Index(fields=["cliente", "activo"]),  # Para filtrado por cliente y estado
            models.Index(fields=["cliente", "is_principal"]),  # Para buscar contacto principal
        ]

    def __str__(self):
        return f"{self.nombre_completo} ({self.email}) - {self.cliente.razon_social}"