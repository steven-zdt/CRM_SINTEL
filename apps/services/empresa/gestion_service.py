"""
Servicio de gestión de empresa.

Este servicio centraliza la lógica de negocio para la gestión de datos de empresa,
incluyendo el cálculo del Dígito de Verificación (DV) según la norma DIAN Colombia.

Principios:
- Service Layer Pattern: Lógica de negocio separada de modelos y vistas
- Cero Signals: Toda la lógica es explícita
- Tenant Isolation: Operaciones dentro del contexto del tenant

Uso:
    from apps.services.empresa.gestion_service import calcular_dv, crear_o_actualizar_empresa
    
    # Calcular DV
    dv = calcular_dv("900123456")
    
    # Crear o actualizar empresa (singleton por tenant)
    empresa = crear_o_actualizar_empresa(
        razon_social="Mi Empresa S.A.",
        nit="900123456",
        direccion="Calle 123 #45-67",
        telefono="6012345678",
        email_contacto="contacto@miempresa.com",
        regimen_tributario="Responsable de IVA"
    )
"""
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

# Multiplicadores primos según norma DIAN (Módulo 11)
# Referencia: Resolución 000042 de 2015 de la DIAN
MULTIPLICADORES_DIAN = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def calcular_dv(nit: str) -> str:
    """
    Calcula el Dígito de Verificación (DV) de un NIT usando el algoritmo Módulo 11 de la DIAN.
    
    El algoritmo funciona así:
    1. Se toman los dígitos del NIT (sin el DV si viene incluido)
    2. Se multiplican de derecha a izquierda por los multiplicadores primos
    3. Se suman todos los productos
    4. Se calcula el módulo 11 de la suma
    5. Si el módulo es 0 o 1, el DV es ese valor
    6. Si el módulo es >= 2, el DV es 11 - módulo
    
    Args:
        nit: Número de Identificación Tributaria (con o sin DV)
              Ejemplos: "900123456", "900123456-1"
        
    Returns:
        Dígito de verificación como string (0-9 o letra según norma)
        
    Raises:
        ValidationError: Si el NIT no es válido
        
    Ejemplo:
        >>> calcular_dv("900123456")
        '1'
        >>> calcular_dv("900123456-1")
        '1'
    """
    if not nit:
        raise ValidationError("El NIT no puede estar vacío")
    
    # Limpiar NIT: quitar guiones y espacios, solo números
    nit_limpio = nit.replace('-', '').replace(' ', '').strip()
    
    # Si el NIT incluye el DV (último carácter), quitarlo
    # El DV puede ser un dígito (0-9) o una letra según casos especiales
    if len(nit_limpio) > 9:
        # Asumir que el último carácter es el DV
        nit_limpio = nit_limpio[:-1]
    
    # Validar que solo contenga dígitos
    if not nit_limpio.isdigit():
        raise ValidationError(f"El NIT debe contener solo números: {nit}")
    
    # Validar longitud (NIT colombiano típico: 9 dígitos, máximo 10)
    if len(nit_limpio) < 8 or len(nit_limpio) > 10:
        raise ValidationError(f"El NIT debe tener entre 8 y 10 dígitos (recibido: {len(nit_limpio)}): {nit}")
    
    # Convertir a lista de enteros (de izquierda a derecha)
    digitos = [int(d) for d in nit_limpio]
    
    # Invertir para multiplicar de derecha a izquierda
    digitos_reversa = list(reversed(digitos))
    
    # Multiplicar cada dígito por su multiplicador correspondiente
    suma = 0
    for i, digito in enumerate(digitos_reversa):
        # Usar el multiplicador correspondiente (cíclico si hay más dígitos que multiplicadores)
        multiplicador = MULTIPLICADORES_DIAN[i % len(MULTIPLICADORES_DIAN)]
        suma += digito * multiplicador
    
    # Calcular módulo 11
    modulo = suma % 11
    
    # Determinar DV según regla DIAN
    if modulo == 0 or modulo == 1:
        dv = str(modulo)
    else:
        dv = str(11 - modulo)
    
    return dv


@transaction.atomic
def crear_o_actualizar_empresa(
    razon_social: str,
    nit: str,
    direccion: str,
    telefono: str,
    email_contacto: str,
    regimen_tributario: str | None = None,  # Legacy, deprecado
    dv: str | None = None,
    moneda: str = 'COP',
    logo: Any | None = None,
    website: str | None = None,
    # Campos de configuración tributaria (autónomos)
    tipo_contribuyente_clase: str | None = None,
    tipo_contribuyente_segmento: str | None = None,
    regimen_renta_codigo: str | None = None,
    responsabilidades_rut_codigos: list | None = None,
    actividad_economica: str | None = None,
    **kwargs
):
    """
    Crea o actualiza la empresa del tenant actual (patrón Singleton).
    
    Esta función implementa la lógica de "Singleton" para la empresa:
    - Si ya existe una empresa para el tenant actual, la actualiza
    - Si no existe, crea una nueva
    
    El Dígito de Verificación (DV) se calcula automáticamente si no se proporciona.
    
    WARNING: IMPORTANTE:
    - Esta función debe ejecutarse dentro del contexto del tenant (django-tenants)
    - Usa transaction.atomic() para garantizar consistencia
    - NO usa signals, toda la lógica es explícita
    
    Args:
        razon_social: Razón social de la empresa
        nit: Número de Identificación Tributaria (con o sin DV)
        direccion: Dirección completa de la empresa
        telefono: Teléfono de contacto
        email_contacto: Email de contacto
        regimen_tributario: Régimen tributario (debe ser uno de los valores válidos)
        dv: Dígito de verificación (opcional, se calcula si no se proporciona)
        moneda: Código de moneda (default: 'COP')
        logo: Archivo de logo (opcional)
        website: URL del sitio web (opcional)
        **kwargs: Campos adicionales del modelo Empresa
        
    Returns:
        Instancia de Empresa (creada o actualizada)
        
    Raises:
        ValidationError: Si los datos son inválidos
        ImportError: Si el modelo Empresa no está disponible (contexto tenant)
    """
    # Importar aquí para evitar problemas de importación circular
    # y asegurar que se importa dentro del contexto del tenant
    from apps.tenant.empresa.models import Empresa
    
    # Validar NIT
    if not nit:
        raise ValidationError("El NIT es obligatorio")
    
    # Limpiar NIT: quitar guiones y espacios
    nit_limpio = nit.replace('-', '').replace(' ', '').strip()
    
    # Calcular DV si no se proporciona
    if dv is None:
        dv = calcular_dv(nit_limpio)
    
    # Validar régimen tributario (legacy, opcional si se usan nuevos campos)
    if regimen_tributario:
        REGIMENES_VALIDOS = [
            'Responsable de IVA',
            'No Responsable',
            'Régimen Simple',
            'Gran Contribuyente'
        ]
        if regimen_tributario not in REGIMENES_VALIDOS:
            raise ValidationError(
                f"Régimen tributario inválido. Debe ser uno de: {', '.join(REGIMENES_VALIDOS)}"
            )
    
    # Buscar empresa existente (singleton por tenant)
    # django-tenants ya filtra por esquema automáticamente
    empresa = Empresa.objects.first()
    
    # Preparar datos para crear/actualizar
    datos_empresa = {
        'razon_social': razon_social,
        'nit': nit_limpio,
        'dv': dv,
        'direccion': direccion,
        'telefono': telefono,
        'email_contacto': email_contacto,
        'moneda': moneda,
    }
    
    # Campos legacy (opcionales)
    if regimen_tributario is not None:
        datos_empresa['regimen_tributario'] = regimen_tributario
    
    # Campos de configuración tributaria (autónomos)
    if tipo_contribuyente_clase is not None:
        datos_empresa['tipo_contribuyente_clase'] = tipo_contribuyente_clase
    if tipo_contribuyente_segmento is not None:
        datos_empresa['tipo_contribuyente_segmento'] = tipo_contribuyente_segmento
    if regimen_renta_codigo is not None:
        # Validar régimen usando choices locales
        try:
            from apps.tenant.empresa.choices.regimen import get_regimen_by_codigo
            if not get_regimen_by_codigo(regimen_renta_codigo):
                raise ValidationError(f"Régimen de renta no válido: {regimen_renta_codigo}")
        except ImportError:
            pass  # Si no hay choices, permitir cualquier valor
        datos_empresa['regimen_renta_codigo'] = regimen_renta_codigo
    if responsabilidades_rut_codigos is not None:
        # Validar responsabilidades usando choices locales
        try:
            from apps.tenant.empresa.choices.responsabilidad_rut import (
                validate_responsabilidades_rut,
            )
            validate_responsabilidades_rut(responsabilidades_rut_codigos)
        except (ImportError, ValueError) as e:
            if isinstance(e, ValueError):
                raise ValidationError(str(e))
        datos_empresa['responsabilidades_rut_codigos'] = responsabilidades_rut_codigos
    if actividad_economica is not None:
        datos_empresa['actividad_economica'] = actividad_economica
    
    # Agregar campos opcionales si se proporcionan
    if logo is not None:
        datos_empresa['logo'] = logo
    if website is not None:
        datos_empresa['website'] = website
    
    # Agregar campos adicionales de kwargs (solo si existen en el modelo)
    campos_validos = [
        'razon_social', 'nit', 'dv', 'direccion', 'telefono', 
        'email_contacto', 'regimen_tributario', 'logo', 'website', 'moneda',
        # Campos de configuración tributaria (autónomos)
        'tipo_contribuyente_clase', 'tipo_contribuyente_segmento',
        'regimen_renta_codigo', 'responsabilidades_rut_codigos',
        'actividad_economica',
    ]
    for campo, valor in kwargs.items():
        if campo in campos_validos:
            datos_empresa[campo] = valor
    
    # Crear o actualizar
    if empresa:
        # Actualizar empresa existente
        for campo, valor in datos_empresa.items():
            setattr(empresa, campo, valor)
        empresa.save()
    else:
        # Crear nueva empresa (singleton_key se establece automáticamente por default=1)
        empresa = Empresa.objects.create(**datos_empresa)
    
    return empresa
