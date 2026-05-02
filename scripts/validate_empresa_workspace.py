#!/usr/bin/env python
"""
Script de validación del módulo Empresa en workspace.

[WARNING] v2.37: Ejecutar ANTES de modificar el módulo Empresa para validar integridad.

Uso:
    python scripts/validate_empresa_workspace.py

Salida:
    - [OK] PASS: Todos los checks pasaron
    - [ERROR] FAIL: Algunos checks fallaron (revisar documentación)
"""
import os
import sys
import re
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

def check_serializer():
    """Valida EmpresaListSerializer."""
    from apps.tenant.empresa.api.serializers import EmpresaListSerializer
    
    print("📋 Validando EmpresaListSerializer...")
    
    # Verificar campos
    expected_fields = {'nit', 'direccion', 'telefono', 'email_contacto', 'regimen_tributario', 'moneda'}
    actual_fields = set(EmpresaListSerializer.Meta.fields)
    
    if expected_fields != actual_fields:
        print(f"  [ERROR] FAIL: Campos no coinciden")
        print(f"     Esperados: {expected_fields}")
        print(f"     Actuales: {actual_fields}")
        return False
    
    # Verificar que NO incluye campos prohibidos
    prohibited_fields = {'id', 'razon_social', 'logo', 'website', 'created_at', 'updated_at'}
    if prohibited_fields & actual_fields:
        print(f"  [ERROR] FAIL: Se expusieron campos prohibidos: {prohibited_fields & actual_fields}")
        return False
    
    print("  [OK] PASS: Serializer correcto")
    return True

def check_html():
    """Valida empresa_list.html."""
    html_path = PROJECT_ROOT / 'apps' / 'tenant' / 'core' / 'templates' / 'tenant' / 'core' / 'partials' / 'empresa' / 'empresa_list.html'
    
    print("📋 Validando empresa_list.html...")
    
    if not html_path.exists():
        print(f"  [ERROR] FAIL: Archivo no encontrado: {html_path}")
        return False
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar selector
    if 'id="tabla-empresa"' not in content:
        print("  [ERROR] FAIL: No se encontró id='tabla-empresa'")
        return False
    
    # Verificar columnas
    expected_columns = ['NIT', 'Dirección', 'Teléfono', 'Email', 'Régimen', 'Moneda', 'Acciones']
    th_matches = re.findall(r'<th[^>]*>(.*?)</th>', content, re.DOTALL)
    th_texts = [re.sub(r'<[^>]+>', '', th).strip() for th in th_matches]
    
    if len(th_texts) != 7:
        print(f"  [ERROR] FAIL: Debe tener 7 columnas, pero tiene {len(th_texts)}")
        return False
    
    for i, expected in enumerate(expected_columns):
        if expected not in th_texts[i]:
            print(f"  [ERROR] FAIL: Columna {i+1} debe ser '{expected}', pero es '{th_texts[i]}'")
            return False
    
    print("  [OK] PASS: HTML correcto")
    return True

def check_js():
    """Valida empresa.page.js."""
    js_path = PROJECT_ROOT / 'apps' / 'tenant' / 'core' / 'static' / 'core' / 'js' / 'empresa' / 'empresa.page.js'
    
    print("📋 Validando empresa.page.js...")
    
    if not js_path.exists():
        print(f"  [ERROR] FAIL: Archivo no encontrado: {js_path}")
        return False
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar selector
    if "TABLE_ID = '#tabla-empresa'" not in content and "const TABLE_ID = '#tabla-empresa'" not in content:
        print("  [ERROR] FAIL: No se encontró TABLE_ID = '#tabla-empresa'")
        return False
    
    # Verificar función fetchEmpresaList
    if 'async function fetchEmpresaList()' not in content and 'function fetchEmpresaList()' not in content:
        print("  [ERROR] FAIL: No se encontró función fetchEmpresaList()")
        return False
    
    # Verificar columnas
    campos_serializer = ['nit', 'direccion', 'telefono', 'email_contacto', 'regimen_tributario', 'moneda']
    for campo in campos_serializer:
        pattern = rf"data:\s*['\"]{campo}['\"]"
        if not re.search(pattern, content, re.IGNORECASE):
            print(f"  [ERROR] FAIL: Campo '{campo}' no está en las columnas de JS")
            return False
    
    print("  [OK] PASS: JS correcto")
    return True

def check_endpoint():
    """Valida que el endpoint existe y funciona."""
    from django.test import Client
    from django.contrib.auth import get_user_model
    from apps.tenant.empresa.models import Empresa
    
    print("📋 Validando endpoint /api/v1/empresas/...")
    
    User = get_user_model()
    client = Client()
    
    # Crear usuario de prueba
    user = User.objects.create_user(username='test_user', password='test_pass')
    client.force_login(user)
    
    # Probar endpoint
    response = client.get('/api/v1/empresas/', HTTP_ACCEPT='application/json')
    
    if response.status_code != 200:
        print(f"  [ERROR] FAIL: Endpoint retornó {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print(f"  [ERROR] FAIL: Endpoint debe retornar array, pero retornó {type(data)}")
        return False
    
    print("  [OK] PASS: Endpoint correcto")
    return True

def main():
    """Ejecuta todas las validaciones."""
    print("=" * 60)
    print("🔍 Validación del Módulo Empresa en Workspace v2.37")
    print("=" * 60)
    print()
    
    checks = [
        check_serializer,
        check_html,
        check_js,
        check_endpoint,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] ERROR: {e}")
            results.append(False)
        print()
    
    print("=" * 60)
    if all(results):
        print("[OK] TODOS LOS CHECKS PASARON")
        print("   El módulo está correctamente configurado.")
        return 0
    else:
        print("[ERROR] ALGUNOS CHECKS FALLARON")
        print("   Revisar documentacion/WORKSPACE_MODULO_EMPRESA_v2.37.md")
        return 1

if __name__ == '__main__':
    sys.exit(main())
