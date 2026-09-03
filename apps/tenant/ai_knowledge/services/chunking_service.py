"""Troceado de texto de origen en chunks (AI-VECTOR-05).

Capa PURA de texto: recibe un string ya saneado y devuelve una lista de
fragmentos. No lee la BD, no llama al proveedor de embeddings, no sabe nada
de tenants.

Seguridad (mandato AI-VECTOR-06): este servicio NUNCA debe recibir texto de
campos clasificados FORBIDDEN/MASKED en `AI_SECURITY_MODEL.md`. Esa exclusion
se decide ANTES, en `sources.py` (allowlist de orígenes indexables) -- el
`ChunkingService` confía en que el texto que le llega ya está permitido.
"""

from __future__ import annotations

import re

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
# Fin de oración: . ! ? seguido de espacio/EOL. Simplificado a propósito
# (no vale la pena un tokenizer de oraciones para observaciones/descripciones).
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_CHARS = 80
MIN_CHUNK_CHARS = 1  # por debajo de esto, se descarta (ruido)


class ChunkingService:
    """Trocea texto en fragmentos aptos para embeber."""

    @staticmethod
    def chunk(
        text: str | None,
        *,
        max_chars: int = DEFAULT_MAX_CHARS,
        overlap_chars: int = DEFAULT_OVERLAP_CHARS,
    ) -> list[str]:
        """Devuelve los chunks de `text`.

        Estrategia: partir por párrafos; cada párrafo que exceda `max_chars`
        se reparte en ventanas por oración con solapamiento de
        `overlap_chars`. Texto vacío/espacios -> `[]`.
        """
        if not text or not text.strip():
            return []
        if overlap_chars >= max_chars:
            raise ValueError("overlap_chars debe ser menor que max_chars")

        chunks: list[str] = []
        for paragraph in _PARAGRAPH_SPLIT.split(text.strip()):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) <= max_chars:
                chunks.append(paragraph)
                continue
            chunks.extend(
                ChunkingService._split_long(paragraph, max_chars, overlap_chars)
            )

        return [c for c in (c.strip() for c in chunks) if len(c) >= MIN_CHUNK_CHARS]

    @staticmethod
    def _split_long(paragraph: str, max_chars: int, overlap_chars: int) -> list[str]:
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(paragraph) if s.strip()]
        if not sentences:
            sentences = [paragraph]

        out: list[str] = []
        current = ""
        for sentence in sentences:
            # Una sola oración más larga que max_chars: cortar duro por caracteres.
            if len(sentence) > max_chars:
                if current:
                    out.append(current)
                    current = ""
                out.extend(ChunkingService._hard_wrap(sentence, max_chars, overlap_chars))
                continue

            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                out.append(current)
                tail = current[-overlap_chars:] if overlap_chars else ""
                current = f"{tail} {sentence}".strip() if tail else sentence
        if current:
            out.append(current)
        return out

    @staticmethod
    def _hard_wrap(s: str, max_chars: int, overlap_chars: int) -> list[str]:
        step = max_chars - overlap_chars
        return [s[i : i + max_chars] for i in range(0, len(s), step)]
