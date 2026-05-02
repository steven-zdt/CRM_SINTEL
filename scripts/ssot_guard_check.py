#!/usr/bin/env python3
"""
SSoT Guard: verify tenant apps do not reference settings.AUTH_USER_MODEL

Checks for occurrences of `settings.AUTH_USER_MODEL` under `apps/tenant/` except
for the allowed path `apps/tenant/perfil/` (the TenantProfile model itself).

Exit code 0 on success, 1 if violations found.
"""
import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
TENANT_DIR = ROOT / 'apps' / 'tenant'
ALLOWED_DIR = TENANT_DIR / 'perfil'

PATTERN = re.compile(r"settings\.AUTH_USER_MODEL")

violations = []

for p in TENANT_DIR.rglob('*.py'):
    try:
        # skip allowed directory
        if ALLOWED_DIR in p.parents or p == ALLOWED_DIR:
            continue
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    if PATTERN.search(text):
        violations.append(str(p.relative_to(ROOT)))

if violations:
    print("[SSoT GUARD] ERROR: Forbidden references found:")
    for v in violations:
        print(f" - {v}")
    print("\nRule: tenant apps must reference 'perfil.TenantProfile' for tenant operators.\n")
    sys.exit(1)
else:
    print("[SSoT GUARD] OK: No forbidden references found in apps/tenant/ (excluding perfil).")
    sys.exit(0)
