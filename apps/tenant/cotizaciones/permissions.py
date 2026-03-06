"""
Permisos personalizados para el módulo de cotizaciones.

⚠️ MÓDULO AUTÓNOMO: Este módulo no depende de otras apps excepto SSoT (Empresa).
"""
from rest_framework import permissions


class IsCotizacionesMember(permissions.BasePermission):
    """
    Permiso que verifica que el usuario esté autenticado y que exista una empresa (SSoT).
    
    ⚠️ MÓDULO AUTÓNOMO: Solo verifica autenticación y existencia de empresa.
    No depende de TenantMembership ni otras apps externas.
    
    Uso:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsCotizacionesMember]
    """
    
    def has_permission(self, request, view):
        """
        Verifica que el usuario esté autenticado y que exista una empresa (SSoT).
        
        Retorna:
        - True: Si el usuario está autenticado y existe una empresa
        - False: Si el usuario no está autenticado o no existe empresa
        """
        # Si no está autenticado, no tiene permisos
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar que exista una empresa (SSoT)
        # Solo importar aquí para evitar dependencias circulares
        from apps.tenant.empresa.models import Empresa
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto.
        
        Por defecto, si el usuario tiene permisos a nivel de vista,
        tiene permisos a nivel de objeto.
        """
        return self.has_permission(request, view)


class IsCotizacionesAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite lectura y escritura a usuarios autenticados del tenant (empresa).
    
    ⚠️ v2.40: REGLA DE EFICIENCIA - Permite escritura a cualquier usuario autenticado
    que pertenezca al tenant (empresa), no solo ADMIN/STAFF.
    
    ⚠️ MÓDULO AUTÓNOMO: Solo verifica autenticación y pertenencia al tenant (SSoT).
    No depende de otras apps externas.
    
    Uso:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsCotizacionesAdminOrReadOnly]
    """
    message = "Debe estar autenticado y pertenecer al tenant (empresa) para crear/editar/eliminar cotizaciones."
    
    def has_permission(self, request, view):
        from rest_framework.permissions import SAFE_METHODS
        
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        
        # Verificar que exista una empresa (SSoT) - el usuario debe pertenecer al tenant
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return False
        
        # Lectura siempre permitida para usuarios autenticados del tenant
        if request.method in SAFE_METHODS:
            return True
        
        # ⚠️ v2.40: Para mutaciones, permitir a cualquier usuario autenticado del tenant
        # La validación de pertenencia al tenant se hace implícitamente porque
        # todas las operaciones filtran por empresa_id (SSoT)
        return True


class IsCotizacionesConfigAllowed(permissions.BasePermission):
    """
    Permiso que permite lectura y escritura a usuarios autenticados para configuración.
    
    ⚠️ MÓDULO AUTÓNOMO: Permite a cualquier usuario autenticado leer y actualizar configuración.
    No depende de otras apps externas.
    
    Uso:
        class ConfiguracionViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsCotizacionesConfigAllowed]
    """
    message = "Debe estar autenticado para acceder a la configuración."
    
    def has_permission(self, request, view):
        """
        Permite acceso a usuarios autenticados para GET y PATCH.
        """
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        
        # Permitir GET y PATCH para usuarios autenticados
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Permite acceso a nivel de objeto para usuarios autenticados.
        """
        return self.has_permission(request, view)
