"""
Script de auditoría para verificar estructura de templates y archivos estáticos.

Verifica:
1. Templates están en templates/<app>/... con {% extends %} y {% include %}
2. NO existen URLs absolutas (http:///https://) en shells estáticos (excepto CDNs)
3. Archivos estáticos están en static/<app>/...
"""
import os
import re
from pathlib import Path
from typing import List, Tuple
import sys

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
TENANT_APPS_DIR = BASE_DIR / 'apps' / 'tenant'

# Patrones de URLs absolutas (prohibidas excepto CDNs)
ABSOLUTE_URL_PATTERN = re.compile(r'(http://|https://)(?!cdn\.tailwindcss\.com|cdnjs\.cloudflare\.com)[^\s"\'<>]+')

# CDNs permitidos
ALLOWED_CDNS = [
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com',
]

# Expresiones regulares para templates
EXTENDS_PATTERN = re.compile(r'{%\s*extends\s*["\'](?P<template_name>[^"\']+)["\']\s*%}')
INCLUDE_PATTERN = re.compile(r'{%\s*include\s*["\'](?P<template_name>[^"\']+)["\']\s*%}')
BLOCK_PATTERN = re.compile(r'{%\s*block\s+\w+\s*%}.*?{%\s*endblock\s+\w+\s*%}', re.DOTALL)

# Errores encontrados
errors: List[Tuple[str, str, int]] = []
warnings: List[Tuple[str, str, int]] = []


def check_template_structure(file_path: Path) -> None:
    """Verifica estructura de template Django."""
    content = file_path.read_text(encoding='utf-8')
    file_name = file_path.name

    # Excluir partials de la verificación de {% extends %}
    is_partial = "partials" in file_path.parts or file_name.startswith('_')

    if not is_partial:
        if not EXTENDS_PATTERN.search(content):
            warnings.append((str(file_path), f"Template sin {{% extends %}}", 0))
        
        # Si extiende, verificar que los includes estén dentro de bloques
        if EXTENDS_PATTERN.search(content) and INCLUDE_PATTERN.search(content):
            if not BLOCK_PATTERN.search(content):
                warnings.append((str(file_path), f"Template con {{% include %}} pero sin bloques", 0))


def check_static_file(file_path: Path) -> None:
    """Verifica archivos estáticos (HTML/JS) para URLs absolutas."""
    content = file_path.read_text(encoding='utf-8')
    
    # Buscar URLs absolutas
    for match in ABSOLUTE_URL_PATTERN.finditer(content):
        url = match.group(0)
        
        # Verificar si es un CDN permitido
        is_allowed = any(cdn in url for cdn in ALLOWED_CDNS)
        
        if not is_allowed:
            errors.append((str(file_path), f"URL absoluta encontrada: {url}", 0))


def run_audit():
    """Ejecuta todas las auditorías."""
    sys.stdout.buffer.write(("INFO: Auditoría de templates y archivos estáticos...\\n").encode('utf-8'))
    sys.stdout.buffer.write(b"======================================================================\n\n")

    # Recorrer apps/tenant para templates y static
    for app_dir in TENANT_APPS_DIR.iterdir():
        if app_dir.is_dir():
            app_name = app_dir.name
            
            # Templates
            templates_dir = app_dir / 'templates' / app_name
            if templates_dir.is_dir():
                for root, _, files in os.walk(templates_dir):
                    for file_name in files:
                        if file_name.endswith('.html'):
                            check_template_structure(Path(root) / file_name)
            
            # Static HTML/JS
            static_dir = app_dir / 'static' / 'tenant'
            if static_dir.is_dir():
                for root, _, files in os.walk(static_dir):
                    for file_name in files:
                        if file_name.endswith(('.html', '.js')):
                            check_static_file(Path(root) / file_name)

    sys.stdout.buffer.write(b"[OK] Verificaciones completadas\n")
    sys.stdout.buffer.write(b"   - Templates revisados\n")
    sys.stdout.buffer.write(("   - Archivos estáticos revisados\\n\\n").encode('utf-8'))

    if warnings:
        sys.stdout.buffer.write(b"[WARNING]  ADVERTENCIAS (%d):\n" % len(warnings))
        for file, msg, _ in warnings:
            sys.stdout.buffer.write(f"   {file}:0 - {msg}\n".encode('utf-8'))
        sys.stdout.buffer.write(b"\n")

    if errors:
        sys.stdout.buffer.write(b"[ERROR] ERRORES (%d):\n" % len(errors))
        for file, msg, _ in errors:
            sys.stdout.buffer.write(f"   {file}:0 - {msg}\n".encode('utf-8'))
        sys.stdout.buffer.write(("\\n[ERROR] Auditoría FALLIDA\\n\\n").encode('utf-8'))
        sys.exit(1)
    else:
        sys.stdout.buffer.write(("[OK] Auditoría EXITOSA\\n\\n").encode('utf-8'))
        sys.exit(0)


if __name__ == "__main__":
    run_audit()
