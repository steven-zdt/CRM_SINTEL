#!/usr/bin/env python
"""
Script de verificación: Valida que la integración de "Aplicar Nota Crédito" esté completa.

Verifica:
1. Modal HTML existe en template
2. JavaScript tiene funciones necesarias
3. Endpoint backend maneja preview y persistencia
4. Handlers de eventos están conectados

Uso:
    python scripts/verify_aplicar_nc_integration.py
"""
import os
import re
import sys
from pathlib import Path

# Colores para output (Windows compatible)
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Símbolos ASCII para compatibilidad Windows
CHECK = '[OK]'
CROSS = '[X]'
WARN = '[!]'

def check_file_exists(filepath):
    """Verifica que un archivo existe."""
    return Path(filepath).exists()

def check_pattern_in_file(filepath, patterns, description):
    """Verifica que patrones existan en un archivo."""
    if not check_file_exists(filepath):
        return False, f"Archivo no existe: {filepath}"
    
    try:
        content = Path(filepath).read_text(encoding='utf-8')
        missing = []
        for pattern in patterns:
            if not re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                missing.append(pattern)
        
        if missing:
            return False, f"Faltan patrones en {filepath}: {missing}"
        return True, f"OK: {description}"
    except Exception as e:
        return False, f"Error al leer {filepath}: {e}"

def main():
    """Función principal de verificación."""
    print("=" * 70)
    print("Verificacion: Integracion 'Aplicar Nota Credito'")
    print("=" * 70)
    print()
    
    root_dir = Path(__file__).parent.parent
    errors = []
    warnings = []
    
    # 1. Verificar template HTML
    print("1. Verificando template HTML...")
    template_path = root_dir / "apps/tenant/core/templates/tenant/core/workspace.html"
    
    template_checks = [
        (r'id="aplicarNCModal"', "Modal aplicarNCModal existe"),
        (r'id="form-aplicar-nc"', "Formulario form-aplicar-nc existe"),
        (r'id="nc-file"', "Campo de archivo nc-file existe"),
        (r'id="nc-preview"', "Checkbox preview nc-preview existe"),
        (r'id="nc-feedback"', "Feedback nc-feedback existe"),
        (r'id="nc-factura-numero"', "Campo factura numero existe"),
        (r'id="nc-factura-cufe"', "Campo factura cufe existe"),
    ]
    
    for pattern, desc in template_checks:
        ok, msg = check_pattern_in_file(template_path, [pattern], desc)
        if ok:
            print(f"  {GREEN}{CHECK}{RESET} {msg}")
        else:
            print(f"  {RED}{CROSS}{RESET} {msg}")
            errors.append(msg)
    
    # 2. Verificar JavaScript
    print("\n2. Verificando JavaScript...")
    js_path = root_dir / "apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js"
    
    js_checks = [
        (r'function abrirModalAplicarNC', "Funcion abrirModalAplicarNC existe"),
        (r'function previewNC', "Funcion previewNC existe"),
        (r'function persistNC', "Funcion persistNC existe"),
        (r'link-aplicar-nc', "Clase link-aplicar-nc usada"),
        (r'data-factura-id', "Atributo data-factura-id usado"),
        (r'data-factura-numero', "Atributo data-factura-numero usado"),
        (r'data-factura-cufe', "Atributo data-factura-cufe usado"),
        (r'/api/v1/facturas/upload-ubl/\?preview=true', "Endpoint preview usado"),
        (r'/api/v1/facturas/upload-ubl/', "Endpoint persistencia usado"),
        (r'creditnote\.ubl21', "Validacion tipo documento"),
        (r'dto\.referencia', "Validacion referencia factura"),
    ]
    
    for pattern, desc in js_checks:
        ok, msg = check_pattern_in_file(js_path, [pattern], desc)
        if ok:
            print(f"  {GREEN}{CHECK}{RESET} {msg}")
        else:
            print(f"  {RED}{CROSS}{RESET} {msg}")
            errors.append(msg)
    
    # 3. Verificar handler de eventos
    print("\n3. Verificando handlers de eventos...")
    handler_checks = [
        (r'link-aplicar-nc.*closest', "Handler click para link-aplicar-nc"),
        (r'form-aplicar-nc.*addEventListener.*submit', "Handler submit del formulario"),
    ]
    
    for pattern, desc in handler_checks:
        ok, msg = check_pattern_in_file(js_path, [pattern], desc)
        if ok:
            print(f"  {GREEN}{CHECK}{RESET} {msg}")
        else:
            print(f"  {YELLOW}{WARN}{RESET} {msg}")
            warnings.append(msg)
    
    # 4. Verificar backend
    print("\n4. Verificando backend...")
    viewsets_path = root_dir / "apps/tenant/facturas/api/viewsets.py"
    
    backend_checks = [
        (r'@action.*upload-ubl', "Action upload-ubl existe"),
        (r'preview_mode.*=.*request\.query_params\.get\(.*preview', "Preview mode detectado"),
        (r'ingest_xml.*preview=True', "Preview mode usa ingest_xml"),
        (r'ingest_xml.*preview=False', "Persistencia usa ingest_xml"),
        (r'FEATURE_XML_PIPELINE', "Feature flag verificado"),
    ]
    
    for pattern, desc in backend_checks:
        ok, msg = check_pattern_in_file(viewsets_path, [pattern], desc)
        if ok:
            print(f"  {GREEN}{CHECK}{RESET} {msg}")
        else:
            print(f"  {RED}{CROSS}{RESET} {msg}")
            errors.append(msg)
    
    # 5. Verificar que el botón se renderiza condicionalmente
    print("\n5. Verificando renderizado condicional...")
    render_checks = [
        (r'!row\.has_nc.*Aplicar NC', "Botón Aplicar NC condicional"),
        (r'row\.has_nc.*Ver NC', "Botón Ver NC condicional"),
    ]
    
    for pattern, desc in render_checks:
        ok, msg = check_pattern_in_file(js_path, [pattern], desc)
        if ok:
            print(f"  {GREEN}{CHECK}{RESET} {msg}")
        else:
            print(f"  {YELLOW}{WARN}{RESET} {msg}")
            warnings.append(msg)
    
    # Resumen
    print("\n" + "=" * 70)
    if errors:
        print(f"{RED}ERRORES ENCONTRADOS: {len(errors)}{RESET}")
        for err in errors:
            print(f"  - {err}")
        return 1
    elif warnings:
        print(f"{YELLOW}ADVERTENCIAS: {len(warnings)}{RESET}")
        for warn in warnings:
            print(f"  - {warn}")
        print(f"\n{GREEN}Integracion basica OK, pero revisa las advertencias.{RESET}")
        return 0
    else:
        print(f"{GREEN}{CHECK} TODAS LAS VERIFICACIONES PASARON{RESET}")
        print("\nLa integracion 'Aplicar Nota Credito' esta completa.")
        print("Puedes proceder con pruebas manuales desde el workspace.")
        return 0

if __name__ == '__main__':
    sys.exit(main())
