"""
Servicio de gestión de perfiles de colaboradores.

Este servicio centraliza la lógica de negocio para la gestión de perfiles
de colaboradores dentro de tenants, siguiendo el principio de Service Layer Pattern.

Principios:
- Service Layer Pattern: Lógica de negocio separada de modelos y vistas
- Cero Signals: Toda la lógica es explícita
- Tenant Isolation: Operaciones dentro del contexto del tenant

Uso:
    from apps.services.perfil.perfil_service import obtener_o_crear_perfil, actualizar_configuracion_ui
    
    # Obtener o crear perfil
    perfil = obtener_o_crear_perfil(user)
    
    # Actualizar configuración de UI
    actualizar_configuracion_ui(user, 'modo_oscuro', True)
"""
