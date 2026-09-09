"""Cache de embeddings de queries (AI-VECTOR-11A, optimizacion de L2).

El mismo texto+modelo siempre produce el mismo vector -- cachearlo evita
re-correr la inferencia ONNX local en `RetrievalService.search()` para
consultas repetidas (~25-28ms medidos en AI-VECTOR-11.1).

Redis directo (no `django.core.cache.cache`, que es `LocMemCache` por
defecto -- no compartido entre procesos `web`/`celery`, ver settings.py).
Mismo patron de conexion que `apps/tenant/core/services/password_reset.py`,
con una diferencia deliberada: aqui el cliente se cachea a nivel de proceso
en vez de recrearse en cada llamada. Medido en AI-VECTOR-11A: crear una
conexion nueva por get/set (el patron de password_reset.py) anadia ~2s por
llamada en Windows dev local (resolucion de "localhost" prueba IPv6 antes
que IPv4 y hace timeout -- mismo problema ya documentado para nginx en
docker-compose.yaml) -- inaceptable en un hot path como retrieval, a
diferencia de un reset de password (raro). Un cliente reutilizado paga ese
costo una sola vez por proceso.
"""
from __future__ import annotations

import hashlib
import json
import logging

from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

_DEFAULT_TTL_S = 6 * 3600  # el vector de un texto+modelo no "vence"; el TTL solo acota memoria

_client = None  # cliente Redis cacheado a nivel de proceso (ver docstring)


def _redis():
    global _client
    if _client is None:
        import redis as _redis_lib
        _client = _redis_lib.from_url(
            getattr(settings, "REDIS_URL", "redis://redis:6379/0"),
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def _cache_key(query: str, model: str) -> str:
    # SHA-256 del texto normalizado -- nunca el texto en claro en la key
    # (mismo criterio de "logging seguro" de FastEmbedProvider, AI-VECTOR-04).
    digest = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
    # schema_name + modelo: aisla entre tenants (evita cruzar cache, mismo
    # criterio que password_reset.py) y auto-invalida si cambia el modelo.
    return f"ai_embed_query:{connection.schema_name}:{model}:{digest}"


def get_cached_embedding(query: str, model: str) -> list[float] | None:
    """Devuelve el vector cacheado, o None (cache miss o Redis no disponible)."""
    try:
        raw = _redis().get(_cache_key(query, model))
    except Exception:
        logger.warning("[QueryEmbeddingCache] redis get fallo, sigue sin cache", exc_info=True)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("[QueryEmbeddingCache] valor cacheado invalido, se ignora")
        return None


def set_cached_embedding(query: str, model: str, vector: list[float], ttl_s: int | None = None) -> None:
    """Guarda el vector en cache. Fail-open: nunca propaga un fallo de Redis."""
    try:
        _redis().set(
            _cache_key(query, model),
            json.dumps(vector),
            ex=ttl_s or getattr(settings, "AI_EMBED_CACHE_TTL_S", _DEFAULT_TTL_S),
        )
    except Exception:
        logger.warning("[QueryEmbeddingCache] redis set fallo, no bloquea la busqueda", exc_info=True)
