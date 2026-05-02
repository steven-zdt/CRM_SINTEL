"""
Script de auditoría para detectar duplicación de datos empresariales.

[WARNING] POLÍTICA SSoT: apps/tenant/empresa/api es la ÚNICA fuente de verdad.
Este script detecta campos duplicados en otras TENANT_APPS.
"""
import os
import re
from pathlib import Path
from typing import List, Tuple
import sys
import ast

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
TENANT_APPS_DIR = BASE_DIR / 'apps' / 'tenant'

# Campos empresariales canónicos (definidos en EmpresaSerializer)
EMPRESA_CANONICAL_FIELDS = [
    'razon_social',
    'nit',
    'dv',
    'nit_completo',
    'direccion',
    'telefono',
    'email_contacto',
    'regimen_tributario',
    'logo',
    'website',
    'moneda',
]

# Variantes de nombres que indican duplicación
EMPRESA_FIELD_VARIANTS = {
    'razon_social': ['razon_social', 'razonSocial', 'razon-social', 'nombre_empresa', 'empresa_nombre', 'emisor_razon_social', 'receptor_razon_social'],
    'nit': ['nit', 'NIT', 'numero_identificacion', 'identificacion', 'emisor_nit', 'receptor_nit'],
    'email_contacto': ['email_contacto', 'email', 'email_empresa', 'correo_contacto', 'contacto_email'],
    'telefono': ['telefono', 'telefono_contacto', 'tel_contacto', 'phone'],
    'logo': ['logo', 'logo_url', 'logo_empresa', 'empresa_logo'],
}

# Errores encontrados
errors: List[Tuple[str, str, int]] = []
warnings: List[Tuple[str, str, int]] = []


def check_model_fields(file_path: Path) -> None:
    """Verifica campos de modelos en busca de duplicación empresarial."""
    content = file_path.read_text(encoding='utf-8')
    
    # Buscar definiciones de modelos
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Verificar si es un modelo Django
                if any(base.id == 'Model' for base in node.bases if isinstance(base, ast.Name)):
                    # Buscar campos que coincidan con campos empresariales
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    field_name = target.id
                                    
                                    # Verificar si el campo es una variante de campo empresarial
                                    for canonical_field, variants in EMPRESA_FIELD_VARIANTS.items():
                                        if field_name in variants and canonical_field != 'razon_social':  # Permitir razon_social en otros contextos
                                            # Verificar si no es el modelo Empresa
                                            if 'empresa' not in file_path.parts or 'models.py' not in str(file_path):
                                                # Verificar si el campo tiene contexto de emisor/receptor (facturas)
                                                if 'emisor' in field_name or 'receptor' in field_name:
                                                    # Esto es aceptable para facturas (datos históricos)
                                                    continue
                                                
                                                # Campo duplicado encontrado
                                                line_num = node.lineno
                                                errors.append((
                                                    str(file_path),
                                                    f"Campo '{field_name}' duplica campo empresarial '{canonical_field}'. "
                                                    f"Usa apps.tenant.empresa.services.get_empresa_data() o la API.",
                                                    line_num
                                                ))
    except SyntaxError:
        # Si no se puede parsear, usar búsqueda de texto simple
        for canonical_field, variants in EMPRESA_FIELD_VARIANTS.items():
            for variant in variants:
                # Buscar definiciones de campo (CharField, EmailField, etc.)
                pattern = rf'{variant}\s*=\s*models\.(CharField|EmailField|ImageField|URLField)'
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Verificar que no sea el modelo Empresa
                    if 'empresa' not in file_path.parts or 'models.py' not in str(file_path):
                        # Verificar contexto (emisor/receptor es aceptable)
                        if 'emisor' in variant or 'receptor' in variant:
                            continue
                        
                        line_num = content[:match.start()].count('\n') + 1
                        errors.append((
                            str(file_path),
                            f"Campo '{variant}' duplica campo empresarial '{canonical_field}'. "
                            f"Usa apps.tenant.empresa.services.get_empresa_data() o la API.",
                            line_num
                        ))


def check_direct_orm_queries(file_path: Path) -> None:
    """Verifica consultas ORM directas a Empresa que deberían usar el servicio."""
    content = file_path.read_text(encoding='utf-8')
    
    # Buscar consultas directas a Empresa.objects
    pattern = r'Empresa\.objects\.(get|filter|first|all|exists)'
    matches = re.finditer(pattern, content)
    
    for match in matches:
        # Verificar que no sea en el servicio provider o en la app empresa
        if 'empresa/services.py' in str(file_path) or 'empresa/api' in str(file_path):
            continue
        
        # Verificar que no esté usando el servicio
        context_before = content[max(0, match.start()-100):match.start()]
        if 'get_empresa_data' in context_before or 'empresa.services' in context_before:
            continue
        
        line_num = content[:match.start()].count('\n') + 1
        warnings.append((
            str(file_path),
            f"Consulta ORM directa a Empresa.objects encontrada. "
            f"Considera usar apps.tenant.empresa.services.get_empresa_data() para consumo interno.",
            line_num
        ))


def run_audit():
    """Ejecuta todas las auditorías."""
    sys.stdout.buffer.write(("INFO: Auditoría: Detección de duplicación de datos empresariales...\\n").encode('utf-8'))
    sys.stdout.buffer.write(b"======================================================================\n\n")

    # Recorrer apps/tenant (excluyendo empresa)
    for app_dir in TENANT_APPS_DIR.iterdir():
        if app_dir.is_dir() and app_dir.name != 'empresa':
            app_name = app_dir.name
            
            # Buscar modelos
            models_file = app_dir / 'models.py'
            if models_file.is_file():
                check_model_fields(models_file)
            
            # Buscar servicios y vistas
            for root, _, files in os.walk(app_dir):
                for file_name in files:
                    if file_name.endswith('.py') and file_name not in ['__init__.py', 'admin.py']:
                        file_path = Path(root) / file_name
                        check_direct_orm_queries(file_path)

    sys.stdout.buffer.write(b"[OK] Verificaciones completadas\n")
    sys.stdout.buffer.write(b"   - Modelos revisados\n")
    sys.stdout.buffer.write(b"   - Consultas ORM revisadas\n\n")

    if warnings:
        sys.stdout.buffer.write(b"[WARNING]  ADVERTENCIAS (%d):\n" % len(warnings))
        for file, msg, line in warnings:
            sys.stdout.buffer.write(f"   {file}:{line} - {msg}\n".encode('utf-8'))
        sys.stdout.buffer.write(b"\n")

    if errors:
        sys.stdout.buffer.write(b"[ERROR] ERRORES (%d):\n" % len(errors))
        for file, msg, line in errors:
            sys.stdout.buffer.write(f"   {file}:{line} - {msg}\n".encode('utf-8'))
        sys.stdout.buffer.write(("\\n[ERROR] Auditoría FALLIDA\\n\\n").encode('utf-8'))
        sys.exit(1)
    else:
        sys.stdout.buffer.write(("[OK] Auditoría EXITOSA\\n\\n").encode('utf-8'))
        sys.exit(0)


if __name__ == "__main__":
    run_audit()
