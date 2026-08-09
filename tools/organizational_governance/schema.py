"""
Vocabulario del grafo organizacional (F13.1) - SSoT de node labels y
relationship types de este paquete. Los extractores solo deben usar labels
definidos aqui (mismo principio que tools/ekg/schema.py, no copiado de ahi
- ver __init__.py sobre por que este modulo es independiente).
"""
from __future__ import annotations

# --- Node labels ------------------------------------------------------------

NODE_TENANT = "Tenant"
NODE_EMPRESA = "Empresa"
NODE_SEDE = "Sede"
NODE_AREA = "Area"
NODE_APP = "App"
NODE_MODEL = "Model"
NODE_VIEWSET = "ViewSet"
NODE_PERMISSION = "Permission"
NODE_ORG_CONTEXT = "OrganizationalContext"
NODE_ORG_SCOPE = "OrganizationalScope"
NODE_ADR = "ADR"
NODE_GIT_COMMIT = "GitCommit"
NODE_TEST_FILE = "TestFile"

NODE_LABELS = frozenset(
    {
        NODE_TENANT,
        NODE_EMPRESA,
        NODE_SEDE,
        NODE_AREA,
        NODE_APP,
        NODE_MODEL,
        NODE_VIEWSET,
        NODE_PERMISSION,
        NODE_ORG_CONTEXT,
        NODE_ORG_SCOPE,
        NODE_ADR,
        NODE_GIT_COMMIT,
        NODE_TEST_FILE,
    }
)

# --- Relationship types -------------------------------------------------

REL_OWNS = "OWNS"                    # Tenant OWNS Empresa, App OWNS Model/ViewSet
REL_HAS = "HAS"                      # Empresa HAS Sede, Sede HAS Area
REL_INHERITS = "INHERITS"            # Model INHERITS base class
REL_USES_PERMISSION = "USES_PERMISSION"   # ViewSet USES_PERMISSION Permission
REL_USES_CONTEXT = "USES_CONTEXT"    # ViewSet/App USES_CONTEXT OrganizationalContext
REL_USES_SCOPE = "USES_SCOPE"        # ViewSet/App USES_SCOPE OrganizationalScope
REL_GOVERNS = "GOVERNS"              # ADR GOVERNS App/Model/Component
REL_MODIFIES = "MODIFIES"            # GitCommit MODIFIES App
REL_TESTS = "TESTS"                  # TestFile TESTS App/Component

REL_TYPES = frozenset(
    {
        REL_OWNS,
        REL_HAS,
        REL_INHERITS,
        REL_USES_PERMISSION,
        REL_USES_CONTEXT,
        REL_USES_SCOPE,
        REL_GOVERNS,
        REL_MODIFIES,
        REL_TESTS,
    }
)

# --- Model scope classification (F13.5) -------------------------------

SCOPE_NONE = "none"                  # sin empresa (no deberia pasar, Zero-Trust)
SCOPE_EMPRESA = "empresa_scoped"
SCOPE_SEDE = "sede_scoped"           # SedeAwareModel real, sede obligatoria
SCOPE_SEDE_LEGACY_NULLSAFE = "sede_legacy_null_safe"  # campo sede informativo, filtrado null-safe
SCOPE_AREA = "area_scoped"

MODEL_SCOPES = frozenset(
    {SCOPE_NONE, SCOPE_EMPRESA, SCOPE_SEDE, SCOPE_SEDE_LEGACY_NULLSAFE, SCOPE_AREA}
)
