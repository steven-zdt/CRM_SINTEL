#!/usr/bin/env python
"""
Script de prueba para verificar la configuración de email.

Uso:
    docker compose exec web python scripts/test_email_config.py
"""
import os
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import get_connection


def test_email_config():
    """Prueba la configuración de email."""
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE CONFIGURACIÓN DE EMAIL")
    print("=" * 60)
    
    # 1. Verificar configuración
    print("\n📋 Configuración actual:")
    print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"  EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or '(no configurado)'}")
    print(f"  EMAIL_HOST_PASSWORD: {'***' if settings.EMAIL_HOST_PASSWORD else '(no configurado)'}")
    print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"  EMAIL_TIMEOUT: {settings.EMAIL_TIMEOUT}")
    
    # 2. Probar conexión
    print("\n🔌 Probando conexión SMTP...")
    try:
        connection = get_connection()
        connection.open()
        print("  [OK] Conexión SMTP exitosa")
        connection.close()
    except Exception as e:
        print(f"  [WARNING]  Error de conexión SMTP: {e}")
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            print("  INFO:  Usando backend de consola (normal en desarrollo)")
        else:
            print("  [ERROR] Revisa la configuración SMTP en .env")
            return False
    
    # 3. Enviar email de prueba
    print("\n📧 Enviando email de prueba...")
    test_email = os.getenv('TEST_EMAIL', settings.DEFAULT_FROM_EMAIL)
    
    try:
        send_mail(
            subject='[OK] Prueba de Email - SINTEL',
            message='Este es un email de prueba desde SINTEL. Si recibes este mensaje, la configuración de email está funcionando correctamente.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        print(f"  [OK] Email de prueba enviado a: {test_email}")
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            print("  INFO:  (En desarrollo, el email se muestra en la consola)")
        return True
    except Exception as e:
        print(f"  [ERROR] Error enviando email: {e}")
        print("  [IDEA] Verifica:")
        print("     - Credenciales SMTP correctas en .env")
        print("     - Para Gmail: usar App Password (no contraseña normal)")
        print("     - Firewall/proxy no bloquea conexiones SMTP")
        return False


def test_invitation_service():
    """Prueba el servicio de invitaciones."""
    print("\n" + "=" * 60)
    print("🔍 VERIFICACIÓN DE SERVICIO DE INVITACIONES")
    print("=" * 60)
    
    try:
        from apps.public.tenants.services.invitations import (
            generate_invitation_token,
            verify_invitation_token,
            build_activation_url,
        )
        
        # Generar token de prueba
        print("\n🔑 Generando token de prueba...")
        token = generate_invitation_token(user_id=1, tenant_id=1, ttl_hours=24)
        print(f"  [OK] Token generado: {token[:50]}...")
        
        # Verificar token
        print("\n🔍 Verificando token...")
        payload = verify_invitation_token(token)
        if payload:
            print(f"  [OK] Token válido: user_id={payload['user_id']}, tenant_id={payload['tenant_id']}")
        else:
            print("  [ERROR] Token inválido")
            return False
        
        # Construir URL de activación
        print("\n🌐 Construyendo URL de activación...")
        url = build_activation_url('test.localhost', token)
        print(f"  [OK] URL construida: {url}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Error en servicio de invitaciones: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "=" * 60)
    print("🧪 PRUEBAS DE CONFIGURACIÓN DE EMAIL E INVITACIONES")
    print("=" * 60)
    
    # Prueba 1: Configuración de email
    email_ok = test_email_config()
    
    # Prueba 2: Servicio de invitaciones
    invitation_ok = test_invitation_service()
    
    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    
    if email_ok and invitation_ok:
        print("[OK] Todas las pruebas pasaron correctamente")
        print("\n[IDEA] Próximos pasos:")
        print("   1. Crear un tenant desde la consola pública")
        print("   2. Verificar que se envía el email de invitación")
        print("   3. Acceder al link de activación en el subdominio del tenant")
        print("   4. Establecer contraseña y activar la cuenta")
        return 0
    else:
        print("[ERROR] Algunas pruebas fallaron")
        if not email_ok:
            print("  - Configuración de email tiene problemas")
        if not invitation_ok:
            print("  - Servicio de invitaciones tiene problemas")
        return 1


if __name__ == '__main__':
    sys.exit(main())
