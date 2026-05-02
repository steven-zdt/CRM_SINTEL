"""
Servicio de integración con DIAN (Dirección de Impuestos y Aduanas Nacionales).

Este servicio maneja la comunicación con los servicios web de la DIAN para:
- Validación de facturas electrónicas
- Consulta de estados de documentos
- Envío de documentos electrónicos
- Consulta de información tributaria

WARNING: IMPORTANTE: Usa schema_context para operaciones específicas de tenant.
"""
from typing import Any

import requests
from django.conf import settings


class DIANService:
    """
    Servicio para interactuar con los servicios web de la DIAN.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        ambiente: str = 'pruebas'  # 'pruebas' o 'produccion'
    ):
        """
        Inicializa el servicio DIAN.
        
        Args:
            api_key: API key para autenticación (opcional, puede venir de settings)
            base_url: URL base de la API DIAN (opcional)
            ambiente: Ambiente a usar ('pruebas' o 'produccion')
        """
        self.api_key = api_key or getattr(settings, 'DIAN_API_KEY', None)
        self.ambiente = ambiente
        
        if ambiente == 'produccion':
            self.base_url = base_url or getattr(settings, 'DIAN_API_URL_PRODUCTION', 'https://api.dian.gov.co')
        else:
            self.base_url = base_url or getattr(settings, 'DIAN_API_URL_TEST', 'https://api-test.dian.gov.co')
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            })
    
    def validar_factura_electronica(
        self,
        xml_content: bytes,
        schema_name: str | None = None
    ) -> dict[str, Any]:
        """
        Valida una factura electrónica con la DIAN.
        
        WARNING: IMPORTANTE: Si se proporciona schema_name, usa schema_context.
        
        Args:
            xml_content: Contenido XML de la factura
            schema_name: Nombre del esquema del tenant (opcional)
            
        Returns:
            Diccionario con resultado de la validación
        """
        resultado = {
            'valido': False,
            'mensaje': '',
            'errores': [],
        }
        
        try:
            # Endpoint de validación
            url = f'{self.base_url}/api/factura-electronica/validar'
            
            # Enviar XML
            response = self.session.post(
                url,
                files={'xml': xml_content},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                resultado['valido'] = data.get('valido', False)
                resultado['mensaje'] = data.get('mensaje', '')
                resultado['errores'] = data.get('errores', [])
            else:
                resultado['errores'].append(f'Error HTTP {response.status_code}: {response.text}')
        
        except requests.exceptions.RequestException as e:
            resultado['errores'].append(f'Error de conexión: {str(e)}')
        except Exception as e:
            resultado['errores'].append(f'Error inesperado: {str(e)}')
        
        return resultado
    
    def consultar_estado_documento(
        self,
        cufe: str,
        schema_name: str | None = None
    ) -> dict[str, Any]:
        """
        Consulta el estado de un documento electrónico en la DIAN.
        
        Args:
            cufe: CUFE del documento
            schema_name: Nombre del esquema del tenant (opcional)
            
        Returns:
            Diccionario con estado del documento
        """
        resultado = {
            'encontrado': False,
            'estado': '',
            'fecha_aceptacion': None,
            'errores': [],
        }
        
        try:
            url = f'{self.base_url}/api/factura-electronica/consultar/{cufe}'
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                resultado['encontrado'] = True
                resultado['estado'] = data.get('estado', '')
                resultado['fecha_aceptacion'] = data.get('fecha_aceptacion')
            elif response.status_code == 404:
                resultado['mensaje'] = 'Documento no encontrado en la DIAN'
            else:
                resultado['errores'].append(f'Error HTTP {response.status_code}: {response.text}')
        
        except requests.exceptions.RequestException as e:
            resultado['errores'].append(f'Error de conexión: {str(e)}')
        except Exception as e:
            resultado['errores'].append(f'Error inesperado: {str(e)}')
        
        return resultado
    
    def enviar_factura_electronica(
        self,
        xml_content: bytes,
        schema_name: str | None = None
    ) -> dict[str, Any]:
        """
        Envía una factura electrónica a la DIAN.
        
        Args:
            xml_content: Contenido XML de la factura
            schema_name: Nombre del esquema del tenant (opcional)
            
        Returns:
            Diccionario con resultado del envío
        """
        resultado = {
            'enviado': False,
            'cufe': '',
            'qr_code': '',
            'errores': [],
        }
        
        try:
            url = f'{self.base_url}/api/factura-electronica/enviar'
            
            response = self.session.post(
                url,
                files={'xml': xml_content},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                resultado['enviado'] = True
                resultado['cufe'] = data.get('cufe', '')
                resultado['qr_code'] = data.get('qr_code', '')
            else:
                resultado['errores'].append(f'Error HTTP {response.status_code}: {response.text}')
        
        except requests.exceptions.RequestException as e:
            resultado['errores'].append(f'Error de conexión: {str(e)}')
        except Exception as e:
            resultado['errores'].append(f'Error inesperado: {str(e)}')
        
        return resultado


def obtener_servicio_dian(schema_name: str | None = None) -> DIANService:
    """
    Obtiene una instancia del servicio DIAN.
    
    Args:
        schema_name: Nombre del esquema del tenant (opcional)
        
    Returns:
        Instancia de DIANService
    """
    return DIANService()
