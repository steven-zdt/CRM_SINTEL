# apps/public/impuestos/choices/ciiu.py
"""
Choices dinámicos para Actividad Económica (CIIU) según DIAN (CIIU Rev. 4 A.C.),
adoptado en Colombia por la Resolución DIAN 000114 de 2020.           # cite: turn15search13
El catálogo debe estar poblado en el esquema 'public'
(ver apps.public.impuestos.models.ActividadEconomica).
La DIAN publica la sección 'Su actividad económica' como referencia oficial.  # cite: turn15search25
"""

from __future__ import annotations

import logging
from functools import lru_cache

from django.db.models import QuerySet
from django_tenants.utils import schema_context

from apps.public.impuestos.models import ActividadEconomica

log = logging.getLogger("impuestos.ciiu.choices")

CHOICE = tuple[str, str]  # (value=code, label="code — descripcion")


# --------- Utilidades de normalización/validación ---------


def normalize_ciiu_code(code: str | None) -> str | None:
    """
    Normaliza un código CIIU a 4 dígitos (ej.: '80' -> '0080').
    Acepta 1–4 dígitos numéricos. Devuelve None si el formato es inválido.
    """
    if not code:
        return None
    s = str(code).strip()
    if not s.isdigit() or not (1 <= len(s) <= 4):
        return None
    return s.zfill(4)


# --------- Resolvedores ---------


@lru_cache(maxsize=1024)
def get_ciiu_label(code: str) -> str | None:
    """
    Devuelve la descripción (label) de un código CIIU si existe en catálogo.
    """
    canon = normalize_ciiu_code(code)
    if not canon:
        return None
    with schema_context("public"):
        obj = ActividadEconomica.objects.only("codigo", "descripcion").filter(codigo=canon).first()
        return obj.descripcion if obj else None


# --------- Choices dinámicos ---------


def _qs_all() -> QuerySet:
    """
    QuerySet base (público) para CIIU. Usa only() para menor carga.
    """
    with schema_context("public"):
        return ActividadEconomica.objects.only("codigo", "descripcion")


def _to_choice_pairs(rows) -> list[CHOICE]:
    """
    Transforma filas en [(value, label), ...] usando formato 'XXXX — Descripción'.
    """
    out: list[CHOICE] = []
    for r in rows:
        code = getattr(r, "codigo", None) or r.get("codigo")
        desc = getattr(r, "descripcion", None) or r.get("descripcion")
        if code and desc:
            out.append((code, f"{code} — {desc}"))
    return out


@lru_cache(maxsize=1)
def get_ciiu_choices_all(limit: int = 5000) -> list[CHOICE]:
    """
    Devuelve una lista grande (capada por 'limit') de choices (solo si realmente lo necesitas).
    NO recomendado para selects masivos en UI; mejor usar prefijo/paginación.

    Uso típico: administración o exportaciones.
    """
    limit = max(1, min(int(limit or 5000), 20000))
    qs = _qs_all().order_by("codigo")[:limit]
    rows = qs.values("codigo", "descripcion")
    return _to_choice_pairs(rows)


def get_ciiu_choices_prefix(prefix: str, limit: int = 50) -> list[CHOICE]:
    """
    Devuelve choices filtrados por prefijo de código (1–4 dígitos) o por búsqueda simple.
    - Si 'prefix' es numérico 1–4 dígitos, aplica startswith al código (zfill si hace falta).
    - Si no es numérico o es corto, retorna [] (evita cargas).
    """
    s = (prefix or "").strip()
    limit = max(1, min(int(limit or 50), 500))
    if s.isdigit() and 1 <= len(s) <= 4:
        canon = s.zfill(4)
        with schema_context("public"):
            qs = (
                ActividadEconomica.objects.only("codigo", "descripcion")
                .filter(codigo__startswith=canon[: len(s)])
                .order_by("codigo")[:limit]
            )
            rows = qs.values("codigo", "descripcion")
            return _to_choice_pairs(rows)
    return []


def get_ciiu_choices_search(query: str, limit: int = 50) -> list[CHOICE]:
    """
    Devuelve choices por búsqueda en descripción (mín. 2 caracteres) o por código exacto.
    - Si 'query' es numérica 1–4 dígitos → buscar por prefijo de código.
    - Si 'query' tiene ≥2 chars → icontains en descripción.
    """
    q = (query or "").strip()
    limit = max(1, min(int(limit or 50), 500))

    # rama numérica (1–4 dígitos)
    if q.isdigit() and 1 <= len(q) <= 4:
        return get_ciiu_choices_prefix(q, limit=limit)

    # rama textual (mín. 2)
    if len(q) < 2:
        return []
    with schema_context("public"):
        qs = (
            ActividadEconomica.objects.only("codigo", "descripcion")
            .filter(descripcion__icontains=q)
            .order_by("descripcion")[:limit]
        )
        rows = qs.values("codigo", "descripcion")
        return _to_choice_pairs(rows)


def invalidate_ciiu_cache() -> None:
    """
    Limpia cachés (usar tras poblar/actualizar catálogo).
    """
    get_ciiu_label.cache_clear()
    get_ciiu_choices_all.cache_clear()
