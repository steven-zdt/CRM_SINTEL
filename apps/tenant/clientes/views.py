"""
Vistas Django tradicionales para UI del módulo Clientes v2.60.
⚠️ API-First: Estas vistas solo retornan HTML parcial para HTMX, no procesan datos.
"""
from django.shortcuts import render
from django.views import View
from apps.tenant.empresa.models import Empresa
from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services import qs_detail


class ClienteOffcanvasView(View):
    """
    ⚠️ v2.60: Vista Django tradicional para retornar Offcanvas HTML.
    
    Retorna ÚNICAMENTE el HTML renderizado del Offcanvas (sin layout base).
    Si recibe un `id`, busca el cliente (validando el tenant) para edición; si no, es modo creación.
    
    ⚠️ Zero Trust: Valida explícitamente que el cliente pertenezca a la empresa del tenant.
    """
    
    def get(self, request, *args, **kwargs):
        """
        Retorna el template del Offcanvas.
        
        Query params:
        - id: ID del cliente para edición (opcional)
        """
        cliente_id = request.GET.get('id')
        cliente = None
        contactos = []
        
        if cliente_id:
            # ⚠️ Zero Trust: Obtener empresa del tenant (SSoT)
            empresa = Empresa.objects.only('id').first()
            if not empresa:
                # Si no hay empresa, retornar offcanvas vacío (modo creación)
                return render(
                    request,
                    'tenant/core/partials/clientes/offcanvas_form.html',
                    {
                        'cliente': None,
                        'contactos': [],
                        'modo': 'crear'
                    }
                )
            
            # ⚠️ Zero Trust: Buscar cliente validando tenant
            cliente = qs_detail(empresa.id, cliente_id)
            
            if cliente:
                # ⚠️ PERFORMANCE BIBLE: Cargar contactos con .only()
                from apps.tenant.clientes.models import ContactoCliente
                contactos = ContactoCliente.objects.filter(cliente=cliente).only(
                    'id', 'nombre_completo', 'cargo', 'email', 'telefono', 'activo', 'is_principal'
                ).order_by('-is_principal', 'nombre_completo')
                modo = 'editar'
            else:
                # Cliente no encontrado o no pertenece al tenant
                modo = 'crear'
        else:
            modo = 'crear'
        
        return render(
            request,
            'tenant/core/partials/clientes/offcanvas_form.html',
            {
                'cliente': cliente,
                'contactos': contactos,
                'modo': modo
            }
        )
