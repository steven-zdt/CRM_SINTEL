"""Allowlist de orígenes indexables -- la FRONTERA DE SEGURIDAD del POC.

Un `(modelo, campo)` solo se puede embeber si aparece aquí. Es una lista
CURADA a mano, no derivada por reflexión: agregar un origen es una decisión
explícita, revisable en el diff. Los campos clasificados FORBIDDEN/MASKED en
`docs/ai/AI_SECURITY_MODEL.md` (salarios, `eps`/`afp`/`arl`, `numero` de
cuenta, `saldo*`, `notas_conciliacion`, ...) simplemente NO están en esta
lista y nunca deben añadirse.

AI-VECTOR-05: define la estructura + los 2 orígenes del POC.
AI-VECTOR-06: el test exhaustivo de no-fuga.
AI-VECTOR-08: el pipeline que itera estos orígenes sobre datos reales.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexableSource:
    """Un campo de texto libre autorizado para indexación semántica."""

    source_type: str          # identificador estable, se guarda en AIKnowledgeDocument
    model_label: str          # app_label.ModelName (para el pipeline de AI-VECTOR-08)
    text_field: str           # nombre del campo de texto a indexar
    description: str           # por qué es seguro / qué contiene
    # Campos del modelo de origen que van a `metadata` del documento (nunca
    # texto sensible: solo ids/enums para filtrado -- sede, area, tipo).
    metadata_fields: tuple[str, ...] = ()


# --- Allowlist del POC ------------------------------------------------------
# SOLO texto libre generado por operación normal del ERP, sin nómina / bancos
# / contabilidad / fiscal (mandato AI-VECTOR §3 y §17).
INDEXABLE_SOURCES: tuple[IndexableSource, ...] = (
    IndexableSource(
        source_type="cliente_observaciones",
        model_label="tenant_clientes.Cliente",
        text_field="observaciones",
        description=(
            "Notas operativas del cliente escritas por el usuario. SAFE: no "
            "contiene PII estructurada ni datos financieros (esos viven en "
            "campos propios: numero_documento, retenciones, etc.)."
        ),
        metadata_fields=(),  # Cliente no tiene sede/area
    ),
    IndexableSource(
        source_type="producto_descripcion",
        model_label="tenant_inventario.Producto",
        text_field="descripcion",
        description="Descripción libre del producto/servicio. SAFE: dato de catálogo.",
        metadata_fields=(),
    ),
)

_BY_TYPE = {s.source_type: s for s in INDEXABLE_SOURCES}


def get_source(source_type: str) -> IndexableSource | None:
    return _BY_TYPE.get(source_type)


def is_indexable(source_type: str) -> bool:
    """True solo si `source_type` está en la allowlist."""
    return source_type in _BY_TYPE
