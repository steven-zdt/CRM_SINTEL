#!/usr/bin/env python
"""
Auditoría completa del sistema de routing para identificar por qué los tenants
privados están siendo direccionados al URLConf público.

Este script verifica:
1. Configuración de dominios en BD
2. Orden y funcionamiento del middleware
3. Configuración de URLConf
4. Estado de Docker y servicios
5. Procesos que puedan interferir

Uso:
    docker compose exec web python scripts/auditoria_completa_routing.py [dominio]
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.test import RequestFactory
from django.urls import resolve, Resolver404
from django_tenants.utils import schema_context, get_public_schema_name
from apps.public.tenants.models import Client as TenantClient, Domain
from django.db import connection

def auditoria_completa(domain_name=None):
    """Auditoría completa del sistema de routing."""
    print("=" * 80)
    print("🔍 AUDITORÍA COMPLETA: Sistema de Routing (django-tenants)")
    print("=" * 80)
    
    if domain_name:
        print(f"\n📋 Dominio a auditar: {domain_name}")
    else:
        print("\n📋 Auditoría general del sistema")
    
    errors = []
    warnings = []
    
    # ========================================================================
    # 1. VERIFICACIÓN DE CONFIGURACIÓN BASE
    # ========================================================================
    print("\n" + "=" * 80)
    print("1️⃣ VERIFICACIÓN DE CONFIGURACIÓN BASE")
    print("=" * 80)
    
    # 1.1 URLConf
    print("\n1.1 URLConf:")
    print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
    print(f"   TENANT_URLCONF: {settings.TENANT_URLCONF}")
    
    # Verificar que los archivos existen
    from pathlib import Path
    root_urlconf_path = Path(str(settings.ROOT_URLCONF).replace('.', '/') + '.py')
    tenant_urlconf_path = Path(str(settings.TENANT_URLCONF).replace('.', '/') + '.py')
    
    if root_urlconf_path.exists():
        print(f"   [OK] {settings.ROOT_URLCONF} existe")
    else:
        print(f"   [ERROR] {settings.ROOT_URLCONF} NO existe")
        errors.append(f"ROOT_URLCONF no existe: {root_urlconf_path}")
    
    if tenant_urlconf_path.exists():
        print(f"   [OK] {settings.TENANT_URLCONF} existe")
    else:
        print(f"   [ERROR] {settings.TENANT_URLCONF} NO existe")
        errors.append(f"TENANT_URLCONF no existe: {tenant_urlconf_path}")
    
    # 1.2 Middleware
    print("\n1.2 Orden de Middleware:")
    middleware = settings.MIDDLEWARE
    tenant_middleware_idx = None
    force_no_port_idx = None
    
    for i, m in enumerate(middleware):
        if 'TenantMainMiddleware' in m:
            tenant_middleware_idx = i
        if 'ForceNoPortMiddleware' in m:
            force_no_port_idx = i
    
    if tenant_middleware_idx is not None:
        print(f"   [OK] TenantMainMiddleware en posición {tenant_middleware_idx}")
    else:
        print(f"   [ERROR] TenantMainMiddleware NO encontrado en MIDDLEWARE")
        errors.append("TenantMainMiddleware no está en MIDDLEWARE")
    
    if force_no_port_idx is not None:
        print(f"   [OK] ForceNoPortMiddleware en posición {force_no_port_idx}")
        if force_no_port_idx < tenant_middleware_idx:
            print(f"   [OK] Orden correcto: ForceNoPortMiddleware → TenantMainMiddleware")
        else:
            print(f"   [ERROR] Orden incorrecto: ForceNoPortMiddleware debe ir ANTES de TenantMainMiddleware")
            errors.append("Orden incorrecto de middleware")
    else:
        print(f"   [WARNING]  ForceNoPortMiddleware no encontrado (puede ser opcional)")
    
    # 1.3 Database Backend
    print("\n1.3 Database Backend:")
    db_engine = settings.DATABASES['default']['ENGINE']
    if 'django_tenants' in db_engine:
        print(f"   [OK] Backend correcto: {db_engine}")
    else:
        print(f"   [ERROR] Backend incorrecto: {db_engine}")
        errors.append(f"Backend debe ser django_tenants.postgresql_backend, actual: {db_engine}")
    
    # ========================================================================
    # 2. VERIFICACIÓN DE DOMINIOS EN BASE DE DATOS
    # ========================================================================
    print("\n" + "=" * 80)
    print("2️⃣ VERIFICACIÓN DE DOMINIOS EN BASE DE DATOS")
    print("=" * 80)
    
    with schema_context('public'):
        public_schema = get_public_schema_name()
        print(f"\n2.1 Esquema público: {public_schema}")
        
        # Verificar tenant público
        public_tenant = TenantClient.objects.filter(schema_name=public_schema).first()
        if public_tenant:
            print(f"   [OK] Tenant público encontrado: {public_tenant.nombre}")
        else:
            print(f"   [ERROR] Tenant público NO encontrado")
            errors.append("Tenant público no existe")
        
        # Verificar dominio público
        public_domains = Domain.objects.filter(tenant=public_tenant) if public_tenant else Domain.objects.none()
        print(f"\n2.2 Dominios del tenant público ({len(public_domains)}):")
        for d in public_domains:
            status = "⭐ PRIMARIO" if d.is_primary else "  "
            print(f"   {status} {d.domain}")
        
        # Verificar tenant privado específico
        if domain_name:
            print(f"\n2.3 Verificando dominio: {domain_name}")
            
            # Normalizar dominio (sin puerto)
            normalized_domain = domain_name.split(':')[0].lower().strip()
            
            domain_obj = Domain.objects.filter(domain=normalized_domain).first()
            if domain_obj:
                print(f"   [OK] Dominio encontrado en BD: {domain_obj.domain}")
                print(f"   Tenant: {domain_obj.tenant.nombre} (schema: {domain_obj.tenant.schema_name})")
                print(f"   Primary: {domain_obj.is_primary}")
                print(f"   Tenant activo: {domain_obj.tenant.is_active}")
                
                if domain_obj.tenant.schema_name == public_schema:
                    print(f"   [ERROR] PROBLEMA: El dominio está asociado al tenant PÚBLICO")
                    errors.append(f"Dominio {normalized_domain} está asociado al tenant público")
                else:
                    print(f"   [OK] Dominio asociado a tenant privado correctamente")
            else:
                print(f"   [ERROR] PROBLEMA CRÍTICO: Dominio NO encontrado en BD")
                errors.append(f"Dominio {normalized_domain} no existe en la base de datos")
                
                # Buscar dominios similares
                similar = Domain.objects.filter(domain__icontains=normalized_domain.split('.')[0]).first()
                if similar:
                    print(f"   [IDEA] Dominio similar encontrado: {similar.domain}")
                    warnings.append(f"Dominio similar encontrado: {similar.domain}")
        
        # Listar todos los tenants privados
        print(f"\n2.4 Tenants privados:")
        private_tenants = TenantClient.objects.exclude(schema_name=public_schema)
        print(f"   Total: {private_tenants.count()}")
        
        for tenant in private_tenants[:10]:  # Mostrar primeros 10
            domains = Domain.objects.filter(tenant=tenant, is_primary=True)
            primary_domain = domains.first()
            if primary_domain:
                print(f"   - {tenant.nombre} (schema: {tenant.schema_name}) → {primary_domain.domain}")
            else:
                print(f"   - {tenant.nombre} (schema: {tenant.schema_name}) → [WARNING] SIN DOMINIO PRIMARIO")
                warnings.append(f"Tenant {tenant.schema_name} sin dominio primario")
    
    # ========================================================================
    # 3. SIMULACIÓN DE RESOLUCIÓN DEL MIDDLEWARE
    # ========================================================================
    print("\n" + "=" * 80)
    print("3️⃣ SIMULACIÓN DE RESOLUCIÓN DEL MIDDLEWARE")
    print("=" * 80)
    
    if domain_name:
        normalized_domain = domain_name.split(':')[0].lower().strip()
        
        print(f"\n3.1 Simulando request a: {normalized_domain}")
        
        # Crear request simulado
        factory = RequestFactory()
        request = factory.get('/activate/?token=test')
        request.META['HTTP_HOST'] = normalized_domain
        
        # Simular ForceNoPortMiddleware
        if ':' in normalized_domain:
            normalized_domain = normalized_domain.split(':')[0]
            print(f"   Después de ForceNoPortMiddleware: {normalized_domain}")
        
        # Simular TenantMainMiddleware + TenantURLConfMiddleware
        try:
            from django_tenants.middleware.main import TenantMainMiddleware
            from apps.public.tenants.middleware_urlconf import TenantURLConfMiddleware
            
            # Guardar estado original
            original_schema = connection.schema_name
            
            # Crear instancias de los middlewares
            tenant_middleware = TenantMainMiddleware(get_response=lambda req: None)
            urlconf_middleware = TenantURLConfMiddleware(get_response=lambda req: None)
            
            # Procesar request con TenantMainMiddleware
            tenant_middleware.process_request(request)
            
            # Procesar request con TenantURLConfMiddleware (garantiza request.urlconf)
            urlconf_middleware(request)
            
            # Verificar resultado
            resolved_tenant = getattr(request, 'tenant', None)
            resolved_schema = connection.schema_name
            resolved_urlconf = getattr(request, 'urlconf', None)
            
            print(f"\n3.2 Resultado de la resolución:")
            if resolved_tenant:
                print(f"   [OK] Tenant resuelto: {resolved_tenant.nombre} (schema: {resolved_tenant.schema_name})")
                print(f"   Esquema activo: {resolved_schema}")
                print(f"   URLConf: {resolved_urlconf or 'No establecido'}")
                
                if resolved_schema == public_schema:
                    print(f"   [ERROR] PROBLEMA: Se resolvió como tenant PÚBLICO")
                    errors.append(f"Middleware resolvió {normalized_domain} como tenant público")
                else:
                    print(f"   [OK] Tenant privado resuelto correctamente")
                    
                    # Verificar URLConf
                    if resolved_urlconf == settings.TENANT_URLCONF:
                        print(f"   [OK] URLConf correcto: TENANT_URLCONF")
                    else:
                        print(f"   [ERROR] URLConf incorrecto: {resolved_urlconf} (esperado: {settings.TENANT_URLCONF})")
                        if resolved_urlconf is None:
                            print(f"   [IDEA] NOTA: TenantURLConfMiddleware debería establecer esto automáticamente")
                        errors.append(f"URLConf incorrecto: {resolved_urlconf}")
            else:
                print(f"   [ERROR] PROBLEMA CRÍTICO: No se pudo resolver el tenant")
                print(f"   Esquema activo: {resolved_schema}")
                print(f"   URLConf: {resolved_urlconf or settings.ROOT_URLCONF}")
                errors.append(f"Middleware no pudo resolver tenant para {normalized_domain}")
            
            # Restaurar estado
            connection.set_schema(original_schema)
            
        except Exception as e:
            print(f"   [ERROR] Error al simular middleware: {e}")
            import traceback
            traceback.print_exc()
            errors.append(f"Error al simular middleware: {e}")
    
    # ========================================================================
    # 4. VERIFICACIÓN DE RUTAS EN URLConf
    # ========================================================================
    print("\n" + "=" * 80)
    print("4️⃣ VERIFICACIÓN DE RUTAS EN URLConf")
    print("=" * 80)
    
    # 4.1 ROOT_URLCONF
    print("\n4.1 Rutas en ROOT_URLCONF (config.urls_public):")
    try:
        from config.urls_public import urlpatterns
        public_routes = [str(p.pattern) for p in urlpatterns[:10]]
        print(f"   Primeras 10 rutas:")
        for route in public_routes:
            print(f"   - {route}")
        
        if 'activate' in str(urlpatterns):
            print(f"   [WARNING]  ADVERTENCIA: /activate/ encontrado en ROOT_URLCONF (no debería estar)")
            warnings.append("/activate/ encontrado en ROOT_URLCONF")
    except Exception as e:
        print(f"   [ERROR] Error al cargar ROOT_URLCONF: {e}")
        errors.append(f"Error al cargar ROOT_URLCONF: {e}")
    
    # 4.2 TENANT_URLCONF
    print("\n4.2 Rutas en TENANT_URLCONF (config.urls_tenant):")
    try:
        from config.urls_tenant import urlpatterns
        tenant_routes = [str(p.pattern) for p in urlpatterns[:10]]
        print(f"   Primeras 10 rutas:")
        for route in tenant_routes:
            print(f"   - {route}")
        
        # Verificar que /activate/ está en landing.urls
        from apps.tenant.landing.urls import urlpatterns as landing_urls
        activate_found = any('activate' in str(p.pattern) for p in landing_urls)
        
        if activate_found:
            print(f"   [OK] /activate/ encontrado en apps.tenant.landing.urls")
        else:
            print(f"   [ERROR] /activate/ NO encontrado en apps.tenant.landing.urls")
            errors.append("/activate/ no encontrado en TENANT_URLCONF")
    except Exception as e:
        print(f"   [ERROR] Error al cargar TENANT_URLCONF: {e}")
        errors.append(f"Error al cargar TENANT_URLCONF: {e}")
    
    # ========================================================================
    # 5. VERIFICACIÓN DE CONFIGURACIÓN DE DOCKER
    # ========================================================================
    print("\n" + "=" * 80)
    print("5️⃣ VERIFICACIÓN DE CONFIGURACIÓN DE DOCKER")
    print("=" * 80)
    
    # 5.1 ALLOWED_HOSTS
    print("\n5.1 ALLOWED_HOSTS:")
    allowed_hosts = settings.ALLOWED_HOSTS
    print(f"   Configurado: {allowed_hosts}")
    
    if domain_name:
        normalized_domain = domain_name.split(':')[0].lower().strip()
        if normalized_domain in allowed_hosts or '*' in allowed_hosts or any(normalized_domain.endswith(h.lstrip('.')) for h in allowed_hosts if h.startswith('.')):
            print(f"   [OK] {normalized_domain} permitido en ALLOWED_HOSTS")
        else:
            print(f"   [WARNING]  {normalized_domain} puede no estar permitido en ALLOWED_HOSTS")
            warnings.append(f"Dominio {normalized_domain} puede no estar en ALLOWED_HOSTS")
    
    # 5.2 TENANT_DOMAIN_BASE
    print("\n5.2 TENANT_DOMAIN_BASE:")
    tenant_domain_base = getattr(settings, 'TENANT_DOMAIN_BASE', None)
    print(f"   Configurado: {tenant_domain_base}")
    
    if domain_name and tenant_domain_base:
        if tenant_domain_base in domain_name:
            print(f"   [OK] Dominio contiene TENANT_DOMAIN_BASE")
        else:
            print(f"   [WARNING]  Dominio no contiene TENANT_DOMAIN_BASE")
            warnings.append(f"Dominio {domain_name} no contiene TENANT_DOMAIN_BASE {tenant_domain_base}")
    
    # ========================================================================
    # 6. VERIFICACIÓN DE PROCESOS Y SERVICIOS
    # ========================================================================
    print("\n" + "=" * 80)
    print("6️⃣ VERIFICACIÓN DE PROCESOS Y SERVICIOS")
    print("=" * 80)
    
    # 6.1 Verificar conexión a BD
    print("\n6.1 Conexión a Base de Datos:")
    try:
        connection.ensure_connection()
        print(f"   [OK] Conexión activa")
        print(f"   Esquema actual: {connection.schema_name}")
    except Exception as e:
        print(f"   [ERROR] Error de conexión: {e}")
        errors.append(f"Error de conexión a BD: {e}")
    
    # 6.2 Verificar que el esquema del tenant existe
    if domain_name:
        with schema_context('public'):
            domain_obj = Domain.objects.filter(domain=domain_name.split(':')[0].lower().strip()).first()
            if domain_obj:
                tenant = domain_obj.tenant
                print(f"\n6.2 Verificando esquema del tenant: {tenant.schema_name}")
                try:
                    from django_tenants.utils import schema_exists
                    if schema_exists(tenant.schema_name):
                        print(f"   [OK] Esquema {tenant.schema_name} existe en PostgreSQL")
                    else:
                        print(f"   [ERROR] PROBLEMA CRÍTICO: Esquema {tenant.schema_name} NO existe")
                        errors.append(f"Esquema {tenant.schema_name} no existe en PostgreSQL")
                except Exception as e:
                    print(f"   [WARNING]  No se pudo verificar esquema: {e}")
                    warnings.append(f"No se pudo verificar esquema {tenant.schema_name}")
    
    # ========================================================================
    # RESUMEN Y RECOMENDACIONES
    # ========================================================================
    print("\n" + "=" * 80)
    print("📋 RESUMEN DE AUDITORÍA")
    print("=" * 80)
    
    print(f"\n[OK] Verificaciones exitosas: {80 - len(errors) - len(warnings)}")
    print(f"[WARNING]  Advertencias: {len(warnings)}")
    print(f"[ERROR] Errores críticos: {len(errors)}")
    
    if warnings:
        print("\n[WARNING]  ADVERTENCIAS:")
        for i, w in enumerate(warnings, 1):
            print(f"   {i}. {w}")
    
    if errors:
        print("\n[ERROR] ERRORES CRÍTICOS:")
        for i, e in enumerate(errors, 1):
            print(f"   {i}. {e}")
        
        print("\n🔧 ACCIONES RECOMENDADAS:")
        print("   1. Verificar que el dominio existe en la BD:")
        print("      docker compose exec web python manage.py shell")
        print("      >>> from apps.public.tenants.models import Domain")
        print("      >>> Domain.objects.filter(domain='home.sintel.com').first()")
        print("\n   2. Si el dominio no existe, crearlo:")
        print("      docker compose exec web python manage.py shell")
        print("      >>> from apps.public.tenants.models import Client, Domain")
        print("      >>> tenant = Client.objects.get(schema_name='home')")
        print("      >>> Domain.objects.create(tenant=tenant, domain='home.sintel.com', is_primary=True)")
        print("\n   3. Verificar que el middleware está funcionando:")
        print("      docker compose exec web python scripts/test_hostname_routing.py")
        print("\n   4. Reiniciar servicios de Docker:")
        print("      docker compose restart web")
        
        return 1
    else:
        print("\n[OK] No se encontraron errores críticos")
        if warnings:
            print("   Revisa las advertencias arriba")
        return 0

if __name__ == '__main__':
    domain_name = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(auditoria_completa(domain_name))
