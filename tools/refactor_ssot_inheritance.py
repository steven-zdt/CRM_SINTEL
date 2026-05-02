#!/usr/bin/env python
"""
Script de Refactorización Masiva SSoT v2.61.4

Automatiza la refactorización de TODOS los modelos en TENANT_APPS para:
1. Heredar de SintelTenantBaseModel
2. Remover campo empresa redundante (ya heredado)
3. Remover created_at/updated_at redundantes (ya heredados)
4. Verificar indexes incluyen empresa

Ejecutar:
    python scripts/refactor_ssot_inheritance.py --dry-run   # Ver cambios
    python scripts/refactor_ssot_inheritance.py --execute   # Aplicar cambios
"""

import os
import re
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

TENANT_APPS = [
    'apps/tenant/core',
    'apps/tenant/empresa',
    'apps/tenant/facturas',
    'apps/tenant/contabilidad',
    'apps/tenant/inventario',
    'apps/tenant/empleados',
    'apps/tenant/gastos',
    'apps/tenant/cotizaciones',
    'apps/tenant/proveedores',
    'apps/tenant/clientes',
    'apps/tenant/proyectos',
    'apps/tenant/perfil',
    'apps/tenant/landing',
    'apps/tenant/dashboard',
]

MODELS_TO_SKIP_EMPRESA = {
    'Empresa',  # SSoT singleton
    'MailInboxConfig',  # Configuration
    'CatalogoMaestroNIIF',  # Reference
}

# ============================================================================
# REFACTORING FUNCTIONS
# ============================================================================

def find_models_files():
    """Encuentra todos los models.py en TENANT_APPS."""
    models_files = []
    for app in TENANT_APPS:
        models_path = Path(app) / 'models.py'
        if models_path.exists():
            models_files.append(models_path)
    return models_files


def read_file(path):
    """Lee archivo con encoding UTF-8."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path, content):
    """Escribe archivo con encoding UTF-8."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def refactor_models_file(filepath, dry_run=True):
    """
    Refactoriza un archivo models.py para herencia SSoT.
    
    Returns:
        (modified: bool, changes: list of str)
    """
    content = read_file(filepath)
    original_content = content
    changes = []
    
    # ========================================================================
    # STEP 1: Actualizar imports
    # ========================================================================
    
    # Si no tiene import de SintelTenantBaseModel, agregarlo
    if 'SintelTenantBaseModel' not in content:
        # Buscar línea de import más alla de otros imports de tenant
        if 'from apps.tenant.' in content and 'from apps.tenant.core.models import SintelTenantBaseModel' not in content:
            # Ya hay imports de tenant.*, agregar el de core justo despuésEmpresa
            import_pattern = r'(from django\.db import models\n)'
            replacement = r'from django.db import models\nfrom apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT\n'
            if not re.search(replacement.replace('\\n', '\n'), content):
                new_content = re.sub(
                    import_pattern,
                    replacement,
                    content,
                    count=1
                )
                if new_content != content:
                    changes.append("[IMPORTS] Agregado: from apps.tenant.core.models import SintelTenantBaseModel")
                    content = new_content
    
    # ========================================================================
    # STEP 2: Cambiar class declarations de models.Model a SintelTenantBaseModel
    # ========================================================================
    
    # Patrón: class NombreModelo(models.Model):
    class_pattern = r'class\s+(\w+)\s*\(\s*models\.Model\s*\):'
    
    for match in re.finditer(class_pattern, content):
        model_name = match.group(1)
        
        # Skip SSoT models and abstract models
        if model_name in MODELS_TO_SKIP_EMPRESA:
            continue
        
        # Skip if it's an abstract model
        docstring_start = content.find('"""', match.end())
        docstring_end = content.find('"""', docstring_start + 3) if docstring_start != -1 else -1
        next_class_or_meta = min([
            content.find('class ', match.end()),
            content.find('class Meta:', match.end()),
            len(content)
        ])
        
        if docstring_end != -1 and docstring_end < next_class_or_meta:
            section = content[match.end():docstring_end]
            if 'abstract = True' in section:
                continue  # Skip abstract models
        
        # Reemplazar models.Model con SintelTenantBaseModel
        old_declaration = match.group(0)
        new_declaration = f"class {model_name}(SintelTenantBaseModel):"
        
        if old_declaration != new_declaration:
            content = content.replace(old_declaration, new_declaration, 1)
            changes.append(f"[CLASS] {model_name}: heredar de SintelTenantBaseModel")
    
    # ========================================================================
    # STEP 3: Remover campo empresa redundante
    # ========================================================================
    
    # Patrón: empresa = models.ForeignKey(...)
    empresa_fk_pattern = r'\n\s+empresa\s*=\s*models\.ForeignKey\([^)]*Empresa[^}]*\)[^\n]*\n'
    if re.search(empresa_fk_pattern, content):
        content = re.sub(empresa_fk_pattern, '\n', content)
        changes.append("[FIELDS] Removido: campo 'empresa' FK redundante (heredado de SintelTenantBaseModel)")
    
    # ========================================================================
    # STEP 4: Remover created_at y updated_at redundantes
    # ========================================================================
    
    # Buscar definiciones de created_at y updated_at que sean auto_now_add=True / auto_now=True
    created_at_pattern = r'\n\s+created_at\s*=\s*models\.DateTimeField\([^)]*auto_now_add\s*=\s*True[^)]*\)[^\n]*\n'
    updated_at_pattern = r'\n\s+updated_at\s*=\s*models\.DateTimeField\([^)]*auto_now\s*=\s*True[^)]*\)[^\n]*\n'
    
    if re.search(created_at_pattern, content):
        content = re.sub(created_at_pattern, '\n', content)
        changes.append("[FIELDS] Removido: campo 'created_at' redundante (heredado)")
    
    if re.search(updated_at_pattern, content):
        content = re.sub(updated_at_pattern, '\n', content)
        changes.append("[FIELDS] Removido: campo 'updated_at' redundante (heredado)")
    
    # ========================================================================
    # STEP 5: Agregar comentario si se removieron campos
    # ========================================================================
    
    if any('Removido' in c for c in changes):
        # Buscar línea que introduzca el próximo campo no heredado o class Meta
        # Agregar comentario: # [v2.61.4] created_at y updated_at heredados de SintelTenantBaseModel
        
        # Buscar línea "class Meta:" y agregarle un comentario antes
        meta_pattern = r'(\n\s+)(class Meta:)'
        if re.search(meta_pattern, content):
            replacement = r'\1# [v2.61.4] campos inherited: empresa, created_at, updated_at\n\1\2'
            content = re.sub(meta_pattern, replacement, content, count=1)
    
    # ========================================================================
    # VERIFY: Asegurarse que indexes incluyen empresa
    # ========================================================================
    
    # Buscar Meta class y verificar que indexes incluya empresa
    meta_pattern = r'class Meta:.*?(?=\n    (?:class|def|$))'
    meta_match = re.search(meta_pattern, content, re.DOTALL)
    
    if meta_match:
        meta_section = meta_match.group(0)
        if 'indexes' in meta_section and 'empresa' not in meta_section:
            changes.append("[WARNING] Meta.indexes no incluye 'empresa' - revisar manualmente")
    
    # ========================================================================
    # DECIDE: Aplicar cambios?
    # ========================================================================
    
    modified = (content != original_content)
    
    if modified and not dry_run:
        write_file(filepath, content)
        print(f"OK: {filepath}: {len(changes)} cambio(s) aplicado(s)")
    elif modified:
        print(f"📝 {filepath}: {len(changes)} cambio(s) a aplicar")
    else:
        print(f"✓ {filepath}: sin cambios requeridos")
    
    return modified, changes


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecuta refactorización masiva."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Refactorización masiva SSoT v2.61.4')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Ver cambios sin aplicar (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Aplicar cambios a archivos')
    
    args = parser.parse_args()
    
    if args.execute:
        args.dry_run = False
    
    print(f"\n{'='*70}")
    print(f"Refactorización Masiva SSoT v2.61.4")
    print(f"Modo: {'DRY-RUN (sin aplicar)' if args.dry_run else 'EXECUTE (aplicando cambios)'}")
    print(f"{'='*70}\n")
    
    models_files = find_models_files()
    print(f"Encontrados {len(models_files)} archivos models.py en TENANT_APPS\n")
    
    total_changes = 0
    modified_files = 0
    
    for filepath in models_files:
        modified, changes = refactor_models_file(filepath, dry_run=args.dry_run)
        
        if modified:
            modified_files += 1
            for change in changes:
                print(f"  - {change}")
            total_changes += len(changes)
    
    print(f"\n{'='*70}")
    print(f"RESUMEN:")
    print(f"  - Archivos modificados: {modified_files}/{len(models_files)}")
    print(f"  - Total cambios: {total_changes}")
    print(f"  - Modo: {'DRY-RUN' if args.dry_run else 'EXECUTED'}")
    
    if args.dry_run:
        print(f"\n💡 Para aplicar cambios, ejecutar:")
        print(f"   python scripts/refactor_ssot_inheritance.py --execute")
    else:
        print(f"\nOK: Cambios aplicados exitosamente")
    
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
