#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación para UX Smoke Runner
Verifica que los archivos estén correctos y listos para ejecutar
"""

import os
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.getcwd()
WORKSPACE_HTML = os.path.join(ROOT, 'apps/tenant/core/templates/tenant/core/workspace.html')
UX_SMOKE_JS = os.path.join(ROOT, 'apps/tenant/core/static/core/js/tests/workspace_ux_smoke.js')

print('Verificando UX Smoke Runner...\n')

errors = []
warnings = []

# 1. Verificar que workspace.html existe y tiene el panel
if os.path.exists(WORKSPACE_HTML):
    with open(WORKSPACE_HTML, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'ux-smoke-panel' not in content:
        errors.append('[ERROR] workspace.html no contiene ux-smoke-panel')
    else:
        print('[OK] Panel de test encontrado en workspace.html')
    
    if 'ux-btn-run-all' not in content:
        errors.append('[ERROR] workspace.html no contiene boton ux-btn-run-all')
    else:
        print('[OK] Boton "Ejecutar Todo" encontrado')
    
    if 'ux-log' not in content:
        errors.append('[ERROR] workspace.html no contiene area de log (ux-log)')
    else:
        print('[OK] Area de log encontrada')
    
    if 'workspace_ux_smoke.js' not in content:
        errors.append('[ERROR] workspace.html no carga workspace_ux_smoke.js')
    else:
        print('[OK] Script workspace_ux_smoke.js referenciado')
else:
    errors.append(f'[ERROR] workspace.html no encontrado: {WORKSPACE_HTML}')

# 2. Verificar que workspace_ux_smoke.js existe
if os.path.exists(UX_SMOKE_JS):
    with open(UX_SMOKE_JS, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar funciones principales
    required_functions = ['function click', 'function type', 'function select', 'function waitFor', 'function navigateToTab']
    for fn in required_functions:
        if fn not in content:
            warnings.append(f'[WARN] Funcion {fn} no encontrada')
    
    # Verificar suites
    suites = [
        'clientes', 'proveedores', 'gastos', 'empleados',
        'facturas', 'contabilidad_cuentas', 'contabilidad_asientos',
        'inventario_catalogo', 'inventario_activos', 'empresa', 'perfil'
    ]
    
    suites_found = 0
    for suite in suites:
        if f'async {suite}()' in content:
            suites_found += 1
        else:
            warnings.append(f'[WARN] Suite {suite} no encontrada')
    
    print(f'[OK] workspace_ux_smoke.js encontrado y verificado')
    print(f'   - {suites_found}/{len(suites)} suites definidas')
else:
    errors.append(f'[ERROR] workspace_ux_smoke.js no encontrado: {UX_SMOKE_JS}')

# 3. Resumen
print('\n' + '=' * 50)
if len(errors) == 0 and len(warnings) == 0:
    print('[OK] Verificacion completada sin errores\n')
    print('Para ejecutar los tests:')
    print('   1. Inicia el servidor Django')
    print('   2. Visita: http://localhost:8000/workspace/?uxsmoke=1')
    print('   3. El panel aparecera en la parte superior')
    print('   4. Haz click en "Ejecutar Todo" o en una suite individual\n')
    sys.exit(0)
else:
    if errors:
        print('\n[ERROR] Errores encontrados:')
        for e in errors:
            print(f'   {e}')
    if warnings:
        print('\n[WARN] Advertencias:')
        for w in warnings:
            print(f'   {w}')
    print('')
    sys.exit(1 if errors else 0)
