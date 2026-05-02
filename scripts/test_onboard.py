#!/usr/bin/env python
import os
import time
from urllib.parse import urlparse
from django.template.loader import render_to_string

# Inicializar Django cuando se ejecuta como script independiente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Ejecutar dentro del contenedor donde Django está configurado
from apps.services.onboarding.empresa_service import crear_tenant_con_owner

schema = f'testsync{int(time.time())}'
nombre = 'Test Sync Tenant'
owner_email = 'invite+test@example.com'

print('Creating tenant', schema, 'owner=', owner_email)
res = crear_tenant_con_owner(nombre=nombre, schema_name=schema, owner_email=owner_email)

print('\n=== ONBOARD RESULT ===')
for k, v in res.items():
    try:
        if hasattr(v, 'id'):
            print(f'{k}:', getattr(v, 'id'))
        else:
            print(f'{k}:', v)
    except Exception:
        print(f'{k}:', v)

activation = res.get('activation_url')
print('\nactivation_url:', activation)
if activation:
    parsed = urlparse(activation)
    login_url = f"{parsed.scheme}://{parsed.netloc}/"
    context = {
        'user': res.get('user'),
        'tenant': res.get('client'),
        'activation_url': activation,
        'login_url': login_url,
        'tenant_name': getattr(res.get('client'), 'nombre', 'Tenant')
    }
    print('\n---- RENDERED TEXT EMAIL ----')
    try:
        print(render_to_string('emails/owner_invitation.txt', context))
    except Exception as e:
        print('Error rendering text template:', e)
    print('\n---- RENDERED HTML EMAIL (truncated 1200 chars) ----')
    try:
        html = render_to_string('emails/owner_invitation.html', context)
        print(html[:1200])
    except Exception as e:
        print('Error rendering html template:', e)
else:
    print('No activation_url available in result')
