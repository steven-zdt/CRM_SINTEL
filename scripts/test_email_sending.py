#!/usr/bin/env python
"""
Script de prueba para verificar el envío de emails de invitación.

Este script prueba:
1. Configuración del backend de email
2. Renderizado de templates
3. Envío real de email (console o SMTP)
4. Logging detallado de cada paso

Uso:
    docker compose exec web python scripts/test_email_sending.py [email_destino]
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
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, get_connection
from django.template.loader import render_to_string
from apps.public.tenants.models import Client, Domain
from apps.public.tenants.services.invitations import (
    generate_invitation_token,
    send_invitation_email,
    build_activation_url,
)
from django_tenants.utils import schema_context
import logging

# Configurar logging para ver todos los mensajes
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s'
)

User = get_user_model()
logger = logging.getLogger(__name__)


def test_email_backend():
    """Prueba la configuración del backend de email."""
    print("=" * 60)
    print("🔍 PRUEBA 1: Configuración del Backend de Email")
    print("=" * 60)
    
    print(f"\n📋 Configuración:")
    print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or '(no configurado)'}")
    print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    # Probar conexión
    print(f"\n🔌 Probando conexión...")
    try:
        connection = get_connection()
        connection.open()
        print("  ✅ Conexión exitosa")
        connection.close()
        return True
    except Exception as e:
        print(f"  ⚠️  Error de conexión: {e}")
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            print("  ℹ️  Backend de consola (normal en desarrollo)")
            return True
        return False


def test_template_rendering():
    """Prueba el renderizado de templates de email."""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 2: Renderizado de Templates")
    print("=" * 60)
    
    context = {
        'user': type('User', (), {'email': 'test@example.com', 'first_name': 'Test'})(),
        'tenant': type('Tenant', (), {'nombre': 'Test Tenant', 'schema_name': 'test'})(),
        'activation_url': 'http://test.sintel.com/activate?token=test123',
        'tenant_name': 'Test Tenant',
    }
    
    try:
        print("\n📝 Renderizando template HTML...")
        html = render_to_string('emails/owner_invitation.html', context)
        print(f"  ✅ Template HTML renderizado ({len(html)} caracteres)")
        
        print("\n📝 Renderizando template texto plano...")
        text = render_to_string('emails/owner_invitation.txt', context)
        print(f"  ✅ Template texto plano renderizado ({len(text)} caracteres)")
        
        return True
    except Exception as e:
        print(f"  ❌ Error renderizando templates: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_email(dest_email: str):
    """Prueba el envío de un email simple."""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 3: Envío de Email Simple")
    print("=" * 60)
    
    print(f"\n📤 Enviando email de prueba a: {dest_email}")
    
    try:
        send_mail(
            subject='✅ Prueba de Email - SINTEL',
            message='Este es un email de prueba desde SINTEL. Si recibes este mensaje, la configuración de email está funcionando correctamente.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[dest_email],
            fail_silently=False,
        )
        print(f"  ✅ Email enviado exitosamente")
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            print("  ℹ️  (En desarrollo, el email se muestra arriba en la consola)")
        return True
    except Exception as e:
        print(f"  ❌ Error enviando email: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invitation_email(dest_email: str):
    """Prueba el envío completo de email de invitación."""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 4: Envío de Email de Invitación (Flujo Completo)")
    print("=" * 60)
    
    with schema_context('public'):
        # Obtener o crear tenant de prueba
        try:
            tenant = Client.objects.filter(schema_name='public').first()
            if not tenant:
                print("  ❌ No se encontró tenant público")
                return False
        except Exception as e:
            print(f"  ❌ Error obteniendo tenant: {e}")
            return False
        
        # Obtener o crear usuario de prueba
        try:
            user = User.objects.filter(email=dest_email).first()
            if user:
                print(f"  ✅ Usuario de prueba existente: {user.email}")
            else:
                # Crear usuario directamente (para pruebas)
                # Usar un username único basado en email
                from django.utils.text import slugify
                base_username = slugify(dest_email.split('@')[0])[:150]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"[:150]
                    counter += 1
                
                user = User.objects.create(
                    email=dest_email,
                    username=username,
                    first_name='Test',
                    last_name='User',
                    is_staff=False,
                    is_active=True,
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])
                print(f"  ✅ Usuario de prueba creado: {user.email}")
        except Exception as e:
            print(f"  ❌ Error obteniendo/creando usuario: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Generar token
        print(f"\n🔑 Generando token de invitación...")
        try:
            token = generate_invitation_token(
                user_id=user.id,
                tenant_id=tenant.id,
                ttl_hours=24,
            )
            print(f"  ✅ Token generado")
        except Exception as e:
            print(f"  ❌ Error generando token: {e}")
            return False
        
        # Construir URL
        print(f"\n🌐 Construyendo URL de activación...")
        try:
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            if not domain:
                print("  ⚠️  No hay dominio primario, usando sintel.com")
                domain_name = 'sintel.com'
            else:
                domain_name = domain.domain
            
            activation_url = build_activation_url(domain_name, token)
            print(f"  ✅ URL construida: {activation_url}")
        except Exception as e:
            print(f"  ❌ Error construyendo URL: {e}")
            return False
        
        # Enviar email
        print(f"\n📤 Enviando email de invitación...")
        print("  (Revisa los logs arriba para ver el proceso detallado)")
        try:
            result = send_invitation_email(user, tenant, activation_url)
            if result:
                print(f"  ✅ Email de invitación enviado exitosamente")
                print(f"  📧 Destinatario: {user.email}")
                print(f"  🔗 URL de activación: {activation_url}")
                return True
            else:
                print(f"  ⚠️  Email NO enviado (pero proceso completado)")
                return False
        except Exception as e:
            print(f"  ❌ Error en send_invitation_email: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "=" * 60)
    print("🧪 PRUEBAS DE ENVÍO DE EMAIL DE INVITACIÓN")
    print("=" * 60)
    
    # Email de destino (argumento o por defecto)
    if len(sys.argv) > 1:
        dest_email = sys.argv[1]
    elif settings.DEFAULT_FROM_EMAIL and '@' in settings.DEFAULT_FROM_EMAIL:
        dest_email = settings.DEFAULT_FROM_EMAIL
    elif settings.EMAIL_HOST_USER and '@' in settings.EMAIL_HOST_USER:
        dest_email = settings.EMAIL_HOST_USER
    else:
        print("❌ ERROR: No se puede determinar email de destino.")
        print("   Especifica un email como argumento: python scripts/test_email_sending.py tu-email@example.com")
        return 1
    
    print(f"\n📧 Email de destino: {dest_email}")
    print(f"   (Puedes especificar otro email como argumento)")
    
    # Ejecutar pruebas
    results = []
    
    results.append(("Backend de Email", test_email_backend()))
    results.append(("Renderizado de Templates", test_template_rendering()))
    results.append(("Email Simple", test_simple_email(dest_email)))
    results.append(("Email de Invitación", test_invitation_email(dest_email)))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    all_passed = all(result[1] for result in results)
    
    for name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"  {status}: {name}")
    
    if all_passed:
        print("\n✅ Todas las pruebas pasaron correctamente")
        print("\n💡 Próximos pasos:")
        print("   1. Revisa los logs arriba para ver el proceso detallado")
        print("   2. Si usas console backend, el email se muestra en la consola")
        print("   3. Si usas SMTP, verifica tu bandeja de entrada")
        print("   4. Prueba crear un tenant desde la consola para ver el flujo completo")
        return 0
    else:
        print("\n❌ Algunas pruebas fallaron")
        print("   Revisa los errores arriba y verifica la configuración")
        return 1


if __name__ == '__main__':
    sys.exit(main())
