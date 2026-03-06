"""
Servicios de orquestación para Core API.

⚠️ POLÍTICA:
- No duplicar lógica de negocio de las apps "dueñas"
- Solo orquestar/componer datos de múltiples apps
- Mantener tenant-awareness (django-tenants maneja el aislamiento)
"""
from typing import Dict, Any, Optional
from django.db import connection
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta


def get_empresa_summary(tenant) -> Dict[str, Any]:
    """
    Obtiene resumen de datos de la empresa del tenant.
    
    ⚠️ POLÍTICA SSoT: Usa el servicio provider de empresa para evitar duplicación.
    
    Args:
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con datos de empresa (razon_social, logo, etc.)
    """
    try:
        # ⚠️ POLÍTICA SSoT: Usar servicio provider en lugar de consulta ORM directa
        from apps.tenant.empresa.services import get_empresa_data
        
        empresa_data = get_empresa_data()
        
        if empresa_data:
            return {
                'id': empresa_data['id'],
                'razon_social': empresa_data['razon_social'],
                'nit': empresa_data['nit'],
                'dv': empresa_data['dv'],
                'nit_completo': empresa_data['nit_completo'],
                'logo_url': empresa_data['logo'],  # Ya es URL relativa del servicio
                'website': empresa_data['website'],
                'moneda': empresa_data['moneda'],
                'regimen_tributario': empresa_data['regimen_tributario'],
                'email_contacto': empresa_data['email_contacto'],
                'telefono': empresa_data['telefono'],
            }
    except Exception:
        pass
    
    # Fallback: datos del tenant
    return {
        'razon_social': getattr(tenant, 'nombre', 'Empresa'),
        'nit': None,
        'dv': None,
        'nit_completo': None,
        'logo_url': None,
        'website': None,
        'moneda': 'COP',
        'regimen_tributario': None,
        'email_contacto': None,
        'telefono': None,
    }


def get_facturas_resumen(tenant, user=None) -> Dict[str, Any]:
    """
    Obtiene resumen de facturas del tenant.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado (opcional, para filtros por permisos)
        
    Returns:
        Dict con estadísticas de facturas
    """
    try:
        from apps.tenant.facturas.models import Factura
        
        # Estadísticas generales
        total_facturas = Factura.objects.count()
        
        # Facturas por estado
        facturas_pendientes = Factura.objects.filter(estado='PENDIENTE').count()
        facturas_aceptadas = Factura.objects.filter(estado='ACEPTADA').count()
        facturas_rechazadas = Factura.objects.filter(estado='RECHAZADA').count()
        
        # Facturas del mes actual
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        facturas_mes = Factura.objects.filter(
            fecha_emision__gte=inicio_mes,
            fecha_emision__lte=hoy
        )
        
        total_mes = facturas_mes.aggregate(
            total=Sum('total'),
            subtotal=Sum('subtotal'),
            impuestos=Sum('impuestos')
        )
        
        # Últimas facturas (5 más recientes)
        ultimas_facturas = Factura.objects.order_by('-fecha_emision')[:5].values(
            'id', 'numero', 'prefijo', 'consecutivo', 'estado',
            'fecha_emision', 'receptor_razon_social', 'total'
        )
        
        return {
            'total': total_facturas,
            'pendientes': facturas_pendientes,
            'aceptadas': facturas_aceptadas,
            'rechazadas': facturas_rechazadas,
            'mes_actual': {
                'cantidad': facturas_mes.count(),
                'total': float(total_mes['total'] or 0),
                'subtotal': float(total_mes['subtotal'] or 0),
                'impuestos': float(total_mes['impuestos'] or 0),
            },
            'ultimas': list(ultimas_facturas),
        }
    except Exception:
        # Si no existe el modelo o hay error, retornar valores por defecto
        return {
            'total': 0,
            'pendientes': 0,
            'aceptadas': 0,
            'rechazadas': 0,
            'mes_actual': {
                'cantidad': 0,
                'total': 0.0,
                'subtotal': 0.0,
                'impuestos': 0.0,
            },
            'ultimas': [],
        }


def get_contabilidad_resumen(tenant, user=None) -> Dict[str, Any]:
    """
    Obtiene resumen de contabilidad del tenant.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado (opcional, para filtros por permisos)
        
    Returns:
        Dict con estadísticas de contabilidad
    """
    try:
        from apps.tenant.contabilidad.models import (
            CuentaContable,
            AsientoContable,
            MovimientoContable
        )
        from django.db.models import Sum
        
        # Estadísticas generales
        total_cuentas = CuentaContable.objects.count()
        total_asientos = AsientoContable.objects.count()
        
        # Movimientos del mes actual
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        movimientos_mes = MovimientoContable.objects.filter(
            fecha__gte=inicio_mes,
            fecha__lte=hoy
        )
        
        # Totales de movimientos (débitos y créditos)
        totales_mes = movimientos_mes.aggregate(
            total_debitos=Sum('debito'),
            total_creditos=Sum('credito')
        )
        
        # Últimos asientos (5 más recientes)
        ultimos_asientos = AsientoContable.objects.order_by('-fecha')[:5].values(
            'id', 'numero', 'fecha', 'descripcion', 'tipo'
        )
        
        return {
            'total_cuentas': total_cuentas,
            'total_asientos': total_asientos,
            'mes_actual': {
                'total_movimientos': movimientos_mes.count(),
                'total_debitos': float(totales_mes['total_debitos'] or 0),
                'total_creditos': float(totales_mes['total_creditos'] or 0),
            },
            'ultimos_asientos': list(ultimos_asientos),
        }
    except Exception:
        # Si no existe el modelo o hay error, retornar valores por defecto
        return {
            'total_cuentas': 0,
            'total_asientos': 0,
            'mes_actual': {
                'total_movimientos': 0,
                'total_debitos': 0.0,
                'total_creditos': 0.0,
            },
            'ultimos_asientos': [],
        }


def get_perfil_resumen(user, tenant) -> Dict[str, Any]:
    """
    Obtiene resumen del perfil del usuario en el tenant.
    
    Args:
        user: Usuario autenticado
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con datos del perfil del usuario
    """
    try:
        from apps.tenant.perfil.models import TenantProfile
        
        # ⚠️ CORRECCIÓN: El campo es 'user', no 'usuario'
        perfil = TenantProfile.objects.filter(user=user).first()
        
        if perfil:
            return {
                'id': perfil.id,
                'nombre_completo': user.get_full_name() or user.email,
                'telefono': getattr(perfil, 'telefono_corporativo', None),
                'cargo': getattr(perfil, 'cargo', None),
                'departamento': getattr(perfil, 'departamento', None),
                'foto_url': perfil.foto.url if hasattr(perfil, 'foto') and perfil.foto else None,
            }
    except Exception:
        pass
    
    # Fallback: datos básicos del usuario
    return {
        'nombre_completo': user.get_full_name() or user.email,
        'telefono': None,
        'cargo': None,
        'departamento': None,
        'foto_url': None,
    }


def get_dashboard_completo(user, tenant) -> Dict[str, Any]:
    """
    Obtiene datos completos del dashboard compuestos de múltiples apps.
    
    Args:
        user: Usuario autenticado
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con todos los datos del dashboard
    """
    from apps.tenant.core.branding import get_tenant_branding
    from apps.tenant.dashboard.services import (
        get_user_role_in_tenant,
        get_dashboard_redirect_url,
    )
    from django.http import HttpRequest
    
    # Crear request mock para branding
    request = HttpRequest()
    request.tenant = tenant
    
    # Obtener datos de cada app
    empresa_data = get_empresa_summary(tenant)
    facturas_data = get_facturas_resumen(tenant, user)
    contabilidad_data = get_contabilidad_resumen(tenant, user)
    perfil_data = get_perfil_resumen(user, tenant)
    branding = get_tenant_branding(request)
    
    # Obtener rol y redirect
    user_role = get_user_role_in_tenant(user, tenant)
    redirect_url = get_dashboard_redirect_url(user, tenant, absolute=False)
    
    return {
        'tenant': {
            'id': tenant.id,
            'nombre': getattr(tenant, 'nombre', 'Tenant'),
            'schema_name': getattr(tenant, 'schema_name', None),
        },
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.get_full_name() or user.email,
            'role': user_role,
        },
        'empresa': empresa_data,
        'facturas': facturas_data,
        'contabilidad': contabilidad_data,
        'perfil': perfil_data,
        'branding': branding,
        'redirect_url': redirect_url or '/dashboard/',
    }
