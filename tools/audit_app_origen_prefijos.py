#!/usr/bin/env python
"""
Auditoría: Verificar que APP_ORIGEN_PREFIJOS es el Single Source of Truth (SSoT)

Este script detecta hardcoded prefixes en apps de negocio que deberían importar desde:
    apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS

Uso:
    python tools/audit_app_origen_prefijos.py
    python tools/audit_app_origen_prefijos.py --app=gastos
    python tools/audit_app_origen_prefijos.py --fix
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Apps to audit (source apps, excluding contabilidad itself)
BUSINESS_APPS = [
    'facturas',
    'clientes',
    'gastos',
    'empleados',
    'inventario',
    'proveedores'
]

# Patterns that indicate hardcoded prefixes (red flags)
HARDCODED_PATTERNS = [
    # Variable assignments like PREFIJOS = [...]
    r"^\s*[A-Z_]*PREFIJOS\s*=\s*\[",
    r"^\s*[A-Z_]*CODIGO[S]*\s*=\s*\[",

    # Dictionary assignments like CUENTA_CODES = {...}
    r"^\s*[A-Z_]*CUENTA[S]*\s*=\s*\{",

    # Hardcoded lists of codes in filter
    r"codigo__in\s*=\s*\[",
    r"codigo__in\s*=\s*\(",

    # Generic 4-5 digit codes (PUC pattern: 1305, 5110, etc)
    r"'[0-9]{4,5}'",
    r'"[0-9]{4,5}"',
]

# Whitelist: files where hardcoding is OK
WHITELIST_FILES = [
    'contabilidad/services/selectors.py',
    'audit_app_origen_prefijos.py',
    'test_app_origen_prefijos.py',
]

def get_python_files(app_dir: Path) -> List[Path]:
    """Recursively find all .py files in app directory."""
    return list(app_dir.glob('**/*.py'))

def check_file_for_hardcoded_prefixes(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Check a file for hardcoded prefix patterns.

    Returns:
        List of (line_number, line_text, pattern_matched)
    """
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️  Could not read {file_path}: {e}")
        return findings

    for line_num, line in enumerate(lines, start=1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Check each pattern
        for pattern in HARDCODED_PATTERNS:
            if re.search(pattern, line):
                # Extra: Exclude false positives (e.g., tests, fixtures with specific codes)
                if 'test' in str(file_path).lower() or 'factory' in str(file_path).lower():
                    continue

                findings.append((line_num, line.rstrip(), pattern))
                break

    return findings

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Audit APP_ORIGEN_PREFIJOS usage across business apps'
    )
    parser.add_argument(
        '--app',
        help='Audit specific app (e.g., gastos, inventario)',
        choices=BUSINESS_APPS
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Try to auto-fix (not implemented)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show all checked files, not just findings'
    )

    args = parser.parse_args()

    # Determine apps to check
    apps_to_check = [args.app] if args.app else BUSINESS_APPS

    # Get project root
    project_root = Path(__file__).parent.parent
    apps_root = project_root / 'apps' / 'tenant'

    total_issues = 0
    checked_files = 0

    print(f"🔍 Auditing APP_ORIGEN_PREFIJOS usage...\n")
    print(f"Apps to check: {', '.join(apps_to_check)}")
    print(f"Project root: {project_root}\n")
    print("-" * 80)

    for app_name in apps_to_check:
        app_dir = apps_root / app_name

        if not app_dir.exists():
            print(f"⚠️  App '{app_name}' not found at {app_dir}")
            continue

        print(f"\n📦 Checking app: {app_name}")
        print(f"   Path: {app_dir}\n")

        py_files = get_python_files(app_dir)
        app_issues = 0

        for py_file in py_files:
            # Skip whitelisted files
            if any(whitelist in str(py_file) for whitelist in WHITELIST_FILES):
                continue

            checked_files += 1
            relative_path = py_file.relative_to(apps_root)

            findings = check_file_for_hardcoded_prefixes(py_file)

            if findings:
                print(f"   ❌ {relative_path}")
                for line_num, line_text, pattern in findings:
                    print(f"      Line {line_num}: {line_text[:70]}")
                    app_issues += len(findings)
                    total_issues += 1
            elif args.verbose:
                print(f"   ✅ {relative_path}")

        if app_issues == 0:
            print(f"   ✅ No hardcoded prefixes found\n")
        else:
            print(f"\n   Found {app_issues} issue(s)\n")

    print("-" * 80)
    print(f"\n📊 Summary:")
    print(f"   Files checked: {checked_files}")
    print(f"   Issues found: {total_issues}")

    if total_issues > 0:
        print(f"\n⚠️  ACTION REQUIRED:")
        print(f"   Replace hardcoded prefixes with imports from:")
        print(f"   from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS")
        print(f"\n   See: .agents/skills/backend/app-origen-prefijos-sso-t.md")
        sys.exit(1)
    else:
        print(f"\n✅ All checks passed! APP_ORIGEN_PREFIJOS is properly centralized.")
        sys.exit(0)

if __name__ == '__main__':
    main()
