#!/usr/bin/env python3
"""
Script para mover partials de Core a sus apps correspondientes (PASO 3)
Basado en AUDITORIA_PARTIALS_CORE_PASO1.json
"""

import os
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CORE_PARTIALS_DIR = BASE_DIR / "apps/tenant/core/templates/tenant/core/partials"
AUDIT_JSON = BASE_DIR / "AUDITORIA_PARTIALS_CORE_PASO1.json"

# Mapeo de apps y sus rutas de destino
APP_PATHS = {
    "clientes": "apps/tenant/clientes/templates/tenant/clientes/partials",
    "contabilidad": "apps/tenant/contabilidad/templates/tenant/contabilidad/partials",
    "facturas": "apps/tenant/facturas/templates/tenant/facturas/partials",
    "inventario": "apps/tenant/inventario/templates/tenant/inventario/partials",
    "gastos": "apps/tenant/gastos/templates/tenant/gastos/partials",
    "empleados": "apps/tenant/empleados/templates/tenant/empleados/partials",
    "empresa": "apps/tenant/empresa/templates/tenant/empresa/partials",
    "perfil": "apps/tenant/perfil/templates/tenant/perfil/partials",
    "proveedores": "apps/tenant/proveedores/templates/tenant/proveedores/partials",
    "dashboard": "apps/tenant/dashboard/templates/tenant/dashboard/partials",
    "landing": "apps/tenant/landing/templates/tenant/landing/partials",
    "mail": "apps/tenant/mail/templates/tenant/mail/partials",
    "mailinbox": "apps/tenant/mailinbox/templates/tenant/mailinbox/partials",
}

def clean_assets_file(src_path, app_name):
    """Limpia un archivo assets_*.html removiendo helpers Core duplicados"""
    if not src_path.exists():
        return None
    
    content = src_path.read_text(encoding='utf-8')
    
    # Remover líneas que cargan helpers Core (ya vienen de assets_core.html)
    lines_to_remove = [
        "core/js/lib/http.js",
        "core/js/lib/api-helpers.js",
        "core/js/lib/dom-utils.js",
        "core/js/lib/datatables-utils.js",
        "core/js/helpers/routes.js",
        "core/js/helpers/crud.js",
        "core/js/helpers/module.js",
    ]
    
    lines = content.split('\n')
    cleaned_lines = []
    skip_next = False
    
    for i, line in enumerate(lines):
        # Si la línea contiene un script de helper Core, saltarla
        if any(helper in line for helper in lines_to_remove):
            continue
        cleaned_lines.append(line)
    
    # Agregar comentario al inicio indicando que debe incluir assets_core.html primero
    if cleaned_lines and not cleaned_lines[0].startswith('{% load static %}'):
        # Ya tiene load static, solo agregar comentario
        pass
    
    # Insertar comentario después de load static
    result_lines = []
    for line in cleaned_lines:
        result_lines.append(line)
        if line.strip() == '{% load static %}' or (line.strip().startswith('{% load static') and i == 0):
            result_lines.append('{# [WARNING] PASO 3: Helpers Core removidos (ya vienen de assets_core.html) #}')
            result_lines.append('{# Incluir primero: {% include \'tenant/core/partials/assets_core.html\' %} #}')
    
    return '\n'.join(result_lines) if result_lines else content

def main():
    print("=== PASO 3: Moviendo partials de Core a sus apps ===")
    print()
    
    # Cargar auditoría
    if not AUDIT_JSON.exists():
        print(f"ERROR: No se encuentra {AUDIT_JSON}")
        return 1
    
    with open(AUDIT_JSON, 'r', encoding='utf-8') as f:
        audit_data = json.load(f)
    
    moved_files = []
    cleaned_assets = []
    errors = []
    
    # Procesar cada archivo de la auditoría
    for file_data in audit_data.get('files', []):
        file_path = file_data['file']
        classification = file_data.get('classification', '')
        app = file_data.get('app', '')
        
        src = CORE_PARTIALS_DIR / file_path
        
        if not src.exists():
            print(f"[WARN] Archivo no existe: {src}")
            continue
        
        # CORE_VALIDO: No mover
        if classification == 'CORE_VALIDO':
            print(f"[OK] Mantener en Core: {file_path}")
            continue
        
        # CORE_INVALIDO_APP_SPECIFIC: Mover a app
        if classification == 'CORE_INVALIDO_APP_SPECIFIC' and app:
            if app not in APP_PATHS:
                print(f"[WARNING]  App no encontrada en mapeo: {app} (archivo: {file_path})")
                errors.append(f"App no mapeada: {app} para {file_path}")
                continue
            
            dest_dir = BASE_DIR / APP_PATHS[app]
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Determinar nombre de destino
            filename = os.path.basename(file_path)
            dest = dest_dir / filename
            
            # Si es un archivo assets_*.html, limpiarlo primero
            if filename.startswith('assets_') and filename.endswith('.html'):
                cleaned_content = clean_assets_file(src, app)
                if cleaned_content:
                    dest.write_text(cleaned_content, encoding='utf-8')
                    cleaned_assets.append((str(src), str(dest)))
                    print(f"[MOVED+CLEANED] {file_path} -> {APP_PATHS[app]}/{filename}")
                else:
                    shutil.copy2(src, dest)
                    moved_files.append((str(src), str(dest)))
                    print(f"[MOVED] {file_path} -> {APP_PATHS[app]}/{filename}")
            else:
                # Copiar archivo tal cual
                shutil.copy2(src, dest)
                moved_files.append((str(src), str(dest)))
                print(f"[MOVED] {file_path} -> {APP_PATHS[app]}/{filename}")
        
        # CORE_LEGACY_DUPLICADO: Mover y consolidar
        elif classification == 'CORE_LEGACY_DUPLICADO' and app:
            if app not in APP_PATHS:
                print(f"[WARNING]  App no encontrada en mapeo: {app} (archivo: {file_path})")
                errors.append(f"App no mapeada: {app} para {file_path}")
                continue
            
            dest_dir = BASE_DIR / APP_PATHS[app]
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            filename = os.path.basename(file_path)
            dest = dest_dir / filename
            
            # Limpiar si es assets
            if filename.startswith('assets_') and filename.endswith('.html'):
                cleaned_content = clean_assets_file(src, app)
                if cleaned_content:
                    dest.write_text(cleaned_content, encoding='utf-8')
                    cleaned_assets.append((str(src), str(dest)))
                    print(f"[MOVED+CLEANED LEGACY] {file_path} -> {APP_PATHS[app]}/{filename}")
                else:
                    shutil.copy2(src, dest)
                    moved_files.append((str(src), str(dest)))
                    print(f"[MOVED LEGACY] {file_path} -> {APP_PATHS[app]}/{filename}")
            else:
                shutil.copy2(src, dest)
                moved_files.append((str(src), str(dest)))
                print(f"[MOVED LEGACY] {file_path} -> {APP_PATHS[app]}/{filename}")
    
    print()
    print(f"=== Resumen ===")
    print(f"Archivos movidos: {len(moved_files)}")
    print(f"Assets limpiados: {len(cleaned_assets)}")
    print(f"Errores: {len(errors)}")
    
    if errors:
        print("\n[ERRORS] Errores encontrados:")
        for error in errors:
            print(f"  - {error}")
    
    return 0 if not errors else 1

if __name__ == '__main__':
    exit(main())
