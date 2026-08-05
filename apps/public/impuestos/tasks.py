"""
Tareas Celery para ingesta de documentos tributarios.

Referencia: https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
"""

import hashlib
import ipaddress
import os
import socket
import time
from datetime import datetime
from mimetypes import guess_extension
from urllib.parse import urlparse

import requests
from celery import shared_task
from django.core.files.base import ContentFile

from apps.public.impuestos.models import DocumentoFuente, IngestaLog
from apps.public.impuestos.services.etl.detectors import detect_kind
from apps.public.impuestos.services.robots import check_robots

UA = "SINTEL-ImpuestosBot/1.0 (+contacto@sintel.local)"  # User agent identificable


def _validar_url_ssrf(url: str) -> None:
    """
    [SEC-M1] Bloquea SSRF antes de descargar url_origen (cargado por un usuario
    STAFF via la consola, pero el worker Celery puede tener alcance de red mas
    amplio que la capa web). Solo permite http/https hacia hosts que resuelvan
    a IPs publicas -- rechaza loopback, link-local, privadas y reservadas.

    Limitacion conocida: no protege contra DNS rebinding (la IP se resuelve aqui
    y `requests` resuelve de nuevo al conectar); suficiente para bloquear el caso
    comun de URL directa a metadata/red interna.

    Raises:
        ValueError: si la URL no es segura para descargar.
    """
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Esquema de URL no permitido: {parsed.scheme!r}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sin host valido")
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"No se pudo resolver el host: {hostname}") from exc
    for _family, _type, _proto, _canon, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError(f"URL resuelve a una IP no permitida ({ip})")


def _log(
    doc: DocumentoFuente,
    etapa: str,
    nivel: str,
    mensaje: str,
    payload: dict | None = None,
    duration_ms: int | None = None,
):
    """
    Helper para crear logs de ingesta con métricas de duración.

    Args:
        doc: DocumentoFuente
        etapa: Etapa del procesamiento
        nivel: Nivel del log (INFO, ERROR, WARNING)
        mensaje: Mensaje descriptivo
        payload: Datos adicionales en formato JSON
        duration_ms: Duración en milisegundos (opcional)
    """
    if duration_ms is not None:
        payload = payload or {}
        payload["duration_ms"] = duration_ms

    IngestaLog.objects.create(
        documento=doc, etapa=etapa, nivel=nivel, mensaje=mensaje, payload=payload
    )


def _save_file_to_doc(doc: DocumentoFuente, content: bytes, content_type: str, suggested_name: str):
    """
    Guarda el contenido descargado en el FileField del documento.

    Args:
        doc: Instancia de DocumentoFuente
        content: Contenido del archivo en bytes
        content_type: Content-Type del archivo
        suggested_name: Nombre sugerido del archivo
    """
    ext = os.path.splitext(suggested_name)[1].lower()
    if not ext and content_type:
        ext = guess_extension(content_type) or ""

    name = f"src-{doc.pk}{ext or ''}"
    doc.archivo.save(name, ContentFile(content), save=False)
    doc.size_bytes = len(content)
    doc.content_type = content_type or ""
    doc.extension = ext

    # Actualizar tipo por detector
    detection = detect_kind(doc)
    doc.tipo = detection.get("kind", doc.tipo or "OTRO")

    doc.save(update_fields=["archivo", "size_bytes", "content_type", "extension", "tipo"])


@shared_task(
    bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5, queue="descarga"
)
def descargar_fuente(self, documento_id: int):
    """
    Descargar documento desde URL.

    Respetando robots.txt, descarga el archivo y lo guarda en FileField.
    """
    start_time = datetime.now()
    doc = DocumentoFuente.objects.get(id=documento_id)

    _log(doc, "descarga", "INFO", f"Descarga URL: {doc.url_origen}")

    try:
        # 0) [SEC-M1] Bloquear SSRF antes de cualquier red hacia url_origen
        try:
            _validar_url_ssrf(doc.url_origen)
        except ValueError as exc:
            _log(
                doc, "descarga", "ERROR", f"URL rechazada por politica SSRF: {exc}",
                payload={"policy": "ssrf-deny", "url": doc.url_origen},
            )
            doc.estado = "ERROR"
            doc.save(update_fields=["estado"])
            raise

        # 1) Verificar robots.txt
        allowed, crawl_delay = check_robots(doc.url_origen, UA)
        doc.robots_observado = bool(allowed)
        doc.crawl_delay_s = crawl_delay or 0
        doc.user_agent = UA
        doc.save(update_fields=["robots_observado", "crawl_delay_s", "user_agent"])

        # Log de política robots.txt (allow/deny y delay)
        _log(
            doc,
            "descarga",
            "INFO",
            f"Robots.txt policy: allow={allowed}, crawl_delay={crawl_delay}s",
            payload={"policy": "allow" if allowed else "deny", "crawl_delay": crawl_delay},
        )

        if not allowed:
            _log(
                doc,
                "descarga",
                "ERROR",
                "Bloqueado por robots.txt",
                payload={"policy": "deny", "robots_url": doc.url_origen},
            )
            doc.estado = "ERROR"
            doc.save(update_fields=["estado"])
            raise ValueError("robots.txt no permite el scraping")

        # Aplicar crawl_delay (con límite para evitar demoras excesivas)
        if crawl_delay:
            time.sleep(min(crawl_delay, 5))

        # 2) Descargar con streaming
        headers = {"User-Agent": UA}
        with requests.get(doc.url_origen, headers=headers, timeout=30, stream=True) as r:
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "").split(";")[0].strip()
            content = r.content

        # 3) Guardar archivo y metadatos
        suggested = os.path.basename(urlparse(doc.url_origen).path) or "download"
        _save_file_to_doc(doc, content, content_type, suggested)

        # 4) Calcular hash
        doc.hash_sha256 = hashlib.sha256(content).hexdigest()
        doc.save(update_fields=["hash_sha256"])

        # 5) Idempotencia: verificar si ya existe otro documento con el mismo hash
        duplicate = (
            DocumentoFuente.objects.exclude(pk=doc.pk).filter(hash_sha256=doc.hash_sha256).first()
        )
        if duplicate:
            _log(
                doc,
                "descarga",
                "INFO",
                f"Documento duplicado por hash; se omitirá reprocesamiento (duplicado: #{duplicate.id})",
                payload={"hash": doc.hash_sha256, "duplicate_id": duplicate.id},
            )
            doc.estado = "PROCESADO"
            doc.save(update_fields=["estado"])
            return  # No procesar duplicado

        # 6) Marcar como EN_PROCESO y pasar a ETL
        doc.estado = "EN_PROCESO"
        doc.save(update_fields=["estado"])

        _log(doc, "descarga", "INFO", "Descarga completada")

        # 7) Registrar duración
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        _log(doc, "descarga", "INFO", "Descarga completada", duration_ms=duration_ms)

        # 8) Pasar a ETL
        procesar_fuente.delay(doc.id)

    except Exception as exc:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        doc.estado = "ERROR"
        doc.save(update_fields=["estado"])

        # DLQ: si alcanzó max_retries, no reintentar
        if self.request.retries >= self.max_retries:
            _log(
                doc,
                "descarga",
                "ERROR",
                "DLQ reached - sin más reintentos",
                payload={"error": str(exc), "retries": self.request.retries},
                duration_ms=duration_ms,
            )
            return  # No relanzar

        _log(
            doc,
            "descarga",
            "ERROR",
            f"Error en descarga: {str(exc)}",
            payload={"error": str(exc), "retries": self.request.retries},
            duration_ms=duration_ms,
        )
        raise


@shared_task(
    bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5, queue="parseo"
)
def procesar_fuente(self, documento_id: int):
    """
    Procesar documento (parseo y normalización ETL).

    Ejecuta el pipeline completo: parse -> tokenize -> normalize -> validate -> upsert
    """
    from django.core.exceptions import ValidationError

    from apps.public.impuestos.services.etl.pipeline import run_etl

    start_time = datetime.now()
    doc = DocumentoFuente.objects.get(id=documento_id)

    _log(doc, "parseo", "INFO", "Inicio ETL (parse -> tokenize -> normalize -> validate -> upsert)")

    try:
        # Ejecutar pipeline ETL
        stats = run_etl(doc)

        # Registrar duración
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Actualizar estado
        doc.estado = "PROCESADO"
        doc.save(update_fields=["estado"])

        # Registrar estadísticas con duración
        _log(
            doc,
            "parseo",
            "INFO",
            "ETL completado exitosamente",
            payload=stats,
            duration_ms=duration_ms,
        )

        # Indexar en OpenSearch (Fase C)
        index_start = datetime.now()
        try:
            from apps.public.impuestos.search.indexer import bulk_index_normas

            # Indexar solo las normas del documento actual
            normas_qs = doc.normas.all()
            if normas_qs.exists():
                stats_idx = bulk_index_normas(normas_qs)
                index_duration_ms = int((datetime.now() - index_start).total_seconds() * 1000)
                _log(
                    doc,
                    "indexado",
                    "INFO",
                    "Indexado OpenSearch completado",
                    payload=stats_idx,
                    duration_ms=index_duration_ms,
                )
        except Exception as idx_exc:
            # No fallar el ETL si falla la indexación (puede reintentarse)
            index_duration_ms = int((datetime.now() - index_start).total_seconds() * 1000)
            _log(
                doc,
                "indexado",
                "ERROR",
                f"Error en indexación OpenSearch: {str(idx_exc)}",
                payload={"error": str(idx_exc)},
                duration_ms=index_duration_ms,
            )

    except ValidationError as exc:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        doc.estado = "ERROR"
        doc.save(update_fields=["estado"])
        _log(
            doc,
            "parseo",
            "ERROR",
            f"Error de validación en ETL: {str(exc)}",
            payload={"error": str(exc), "errors": exc.messages if hasattr(exc, "messages") else []},
            duration_ms=duration_ms,
        )
        raise

    except ValueError as exc:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        doc.estado = "ERROR"
        doc.save(update_fields=["estado"])
        _log(
            doc,
            "parseo",
            "ERROR",
            f"Error en ETL: {str(exc)}",
            payload={"error": str(exc)},
            duration_ms=duration_ms,
        )
        raise

    except Exception as exc:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        doc.estado = "ERROR"
        doc.save(update_fields=["estado"])

        # DLQ: si alcanzó max_retries, no reintentar
        if self.request.retries >= self.max_retries:
            _log(
                doc,
                "parseo",
                "ERROR",
                "DLQ reached - sin más reintentos",
                payload={"error": str(exc), "retries": self.request.retries},
                duration_ms=duration_ms,
            )
            return  # No relanzar

        _log(
            doc,
            "parseo",
            "ERROR",
            f"Error inesperado en ETL: {str(exc)}",
            payload={"error": str(exc), "retries": self.request.retries},
            duration_ms=duration_ms,
        )
        raise
