#!/usr/bin/env python
"""
Script de inicialización para el proyecto SINTEL.

Este script automatiza la configuración inicial del sistema multi-tenant:
1. Ejecuta migraciones del esquema public
2. Crea el tenant público con dominio localhost
3. Verifica la configuración

Uso:
    python setup_tenants.py
    docker compose exec web python setup_tenants.py
"""
import os
import sys
import django

# Configurar Django
if __name__ == '__main__':
    # Asegurar que estamos en el directorio correcto
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # Inicializar Django
    django.setup()
    
    # Importar después de setup
    from django.core.management import call_command
    from django.db import connection
    from django_tenants.utils import schema_exists
    from apps.public.tenants.models import Client, Domain

    print("🚀 Iniciando configuración del sistema SINTEL...")
    print("=" * 60)

    # 1. Ejecutar migraciones del esquema public
    print("\n📦 Paso 1: Ejecutando migraciones del esquema public...")
    try:
        call_command('migrate_schemas', '--shared', verbosity=1)
        print("✅ Migraciones del esquema public completadas")
    except Exception as e:
        print(f"❌ Error en migraciones: {e}")
        sys.exit(1)

    # 2. Verificar que el esquema public existe
    if not schema_exists('public'):
        print("❌ El esquema public no existe. Abortando.")
        sys.exit(1)

    # 3. Configurar el tenant público
    print("\n🔍 Paso 2: Configurando tenant público...")
    try:
        # Las apps en SHARED_APPS están automáticamente en el esquema public
        # No necesitamos cambiar el tenant explícitamente

        # Crear o obtener el tenant público
        tenant, created = Client.objects.get_or_create(
            schema_name='public',
            defaults={
                'nombre': 'SINTEL Global',
                'on_trial': False,
            }
        )

        if created:
            print(f"✅ Tenant público creado: {tenant.nombre}")
        else:
            print(f"ℹ️  Tenant público ya existe: {tenant.nombre}")

        # 4. Crear dominios
        # ⚠️ ESTÁNDAR: Solo creamos localhost (principal) y 127.0.0.1 (adicional)
        # No creamos dominios con puerto
        print("\n🔍 Paso 3: Configurando dominios...")
        domains_to_create = [
            ('localhost', True),
            ('127.0.0.1', False),
        ]

        created_domains = []
        for domain_name, is_primary in domains_to_create:
            domain, domain_created = Domain.objects.get_or_create(
                domain=domain_name,
                defaults={
                    'tenant': tenant,
                    'is_primary': is_primary,
                }
            )

            if domain_created:
                print(f"✅ Dominio creado: {domain.domain} (primary: {is_primary})")
                created_domains.append(domain.domain)
            else:
                # Actualizar si el tenant cambió
                if domain.tenant != tenant:
                    domain.tenant = tenant
                    domain.is_primary = is_primary
                    domain.save()
                    print(f"✅ Dominio actualizado: {domain.domain}")
                else:
                    print(f"ℹ️  Dominio ya existe: {domain.domain}")

        # 5. Resumen
        print("\n" + "=" * 60)
        print("🎉 Configuración completada exitosamente!")
        print("\n📋 Resumen:")
        print(f"   - Tenant: {tenant.nombre} (schema: {tenant.schema_name})")
        all_domains = Domain.objects.filter(tenant=tenant)
        print(f"   - Dominios configurados: {len(all_domains)}")
        for domain in all_domains:
            primary_mark = " (PRIMARY)" if domain.is_primary else ""
            print(f"     • {domain.domain}{primary_mark}")
        print("\n✅ El sistema está listo para usar!")
        print("   Accede a: http://localhost:8000/admin/")

    except Exception as e:
        print(f"\n❌ Error durante la configuración: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
