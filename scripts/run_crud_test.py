#!/usr/bin/env python3
import os
import json
import http.client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from apps.public.tenants.models import Domain
from django.db import connection
from apps.public.tenants.models import TenantMembership as TM
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient

User = get_user_model()

def ensure_user_and_membership():
    user, created = User.objects.get_or_create(email='apitest2@sintel.local', defaults={'username':'apitest2','is_staff':True,'is_superuser':True})
    if created:
        user.set_password('ChangeMe123!')
        user.save()
    d = Domain.objects.get(domain='home.sintel.com')
    client = d.tenant
    current = connection.schema_name
    connection.set_schema_to_public()
    TM.objects.get_or_create(client=client, user=user, defaults={'rol':'ADMIN','is_primary_admin':True,'is_active':True})
    connection.set_schema(current)
    return user, d

def get_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def do(method, path, headers, body=None):
    conn = http.client.HTTPConnection('127.0.0.1', 8000, timeout=30)
    body_bytes = None
    if body is not None:
        body_bytes = json.dumps(body).encode('utf-8')
    conn.request(method, path, body=body_bytes, headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode('utf-8')
    print(f"\n>>> {method} {path} -> {resp.status} {resp.reason}\n{data[:2000]}")
    conn.close()
    return resp.status, data

def main():
    user, domain = ensure_user_and_membership()
    token = get_token(user)
    host = 'home.sintel.com'
    headers = {'Host': host, 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # Empresa list
    do('GET', '/api/v1/empresas/', headers)

    # MailInboxConfig CRUD
    base = '/api/v1/empresas/mail-inbox-config/'
    payload = {
        'nombre': 'Test Inbox',
        'email_address': 'inbox-test@example.com',
        'provider': 'custom',
        'protocol': 'imap',
        'imap_host': 'imap.example.com',
        'imap_port': 993,
        'imap_ssl': True,
        'is_active': True
    }
    # Use DRF APIClient to ensure Authorization header handling matches test environment
    api_client = APIClient()
    # Attempt session login to allow /console/jwt/from-session/ to return tokens
    logged_in = api_client.login(username=user.username, password='ChangeMe123!')
    print('APIClient session login:', logged_in)
    # Ensure Host header for tenant resolution
    api_client.defaults['HTTP_HOST'] = host

    # If session login succeeded, attempt to get JWT from session
    if logged_in:
        jwt_resp = api_client.get('/console/jwt/from-session/')
        print('GET /console/jwt/from-session/ ->', jwt_resp.status_code)
        if jwt_resp.status_code == 200:
            try:
                jdata = jwt_resp.json()
                access_from_session = jdata.get('access')
                if access_from_session:
                    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_from_session}')
            except Exception:
                pass

    # Fallback: if we already had an access in headers, set it
    if not api_client._credentials:
        # set from earlier token if available
        try:
            token_val = headers.get('Authorization').split()[1]
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_val}')
        except Exception:
            pass

    post_resp = api_client.post(base, payload, format='json')
    status = post_resp.status_code
    data = post_resp.content.decode('utf-8')
    print(f"\n>>> APIClient POST {base} -> {status} {post_resp.reason_phrase}\n{data[:2000]}")
    # If POST failed due to missing credentials, try obtaining JWT via /api/token/ using user's password
    if status in (401, 403):
        print('\nAuthentication failed using RefreshToken.for_user(). Attempting credential login to obtain access token...')
        # Attempt to login via /api/token/
        login_payload = {'username': user.username, 'password': 'ChangeMe123!'}
        try:
            conn = http.client.HTTPConnection('127.0.0.1', 8000, timeout=30)
            lp = json.dumps(login_payload).encode('utf-8')
            conn.request('POST', '/api/token/', body=lp, headers={'Content-Type': 'application/json', 'Host': host})
            resp = conn.getresponse()
            data_login = resp.read().decode('utf-8')
            conn.close()
            print('Login attempt:', resp.status, resp.reason, data_login[:500])
            if resp.status == 200:
                j = json.loads(data_login)
                new_access = j.get('access')
                if new_access:
                    headers['Authorization'] = f'Bearer {new_access}'
                    print('Retrying POST with new access token...')
                    status, data = do('POST', base, headers, payload)
        except Exception as e:
            print('Login attempt failed:', e)
    created_id = None
    if status in (200,201):
        try:
            j = json.loads(data)
            created_id = j.get('id')
        except Exception:
            pass
    do('GET', base, headers)
    if created_id:
        do('PATCH', f'{base}{created_id}/', headers, {'nombre': 'Test Inbox Updated'})
        do('GET', f'{base}{created_id}/', headers)
        do('DELETE', f'{base}{created_id}/', headers)
        do('GET', base, headers)

    print('\nCRUD test finished')

if __name__ == '__main__':
    main()
