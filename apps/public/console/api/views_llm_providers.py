"""
APIViews del LLM Provider Hub (Fase 8,
PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md).

Archivo separado de views.py (dominio distinto: proveedores de IA, no
tenants/usuarios). Mismo patron de autenticacion/permisos que el resto de
la consola: SessionAuthentication + IsAdminUser (ver views.py, docstring
del modulo original).
"""

from __future__ import annotations

import logging

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public.console.models import (
    LLMActiveConfig,
    LLMModelConfig,
    LLMProviderAuditLog,
    LLMProviderConfig,
)

from .llm_connection_schemas import CONNECTION_SCHEMAS, list_connection_schemas
from .serializers_llm_providers import (
    LLMActiveConfigSerializer,
    LLMModelConfigSerializer,
    LLMProviderAuditLogSerializer,
    LLMProviderConfigSerializer,
)

logger = logging.getLogger(__name__)


class LLMConnectionSchemasView(APIView):
    """
    GET /api/admin/v1/console/llm/connection-schemas/

    Fuente de verdad UNICA de que campos necesita cada `provider_type`
    (correccion 2026-09-24: el formulario NO debe hardcodear estas reglas
    en JS -- las lee de aqui). Ver docstring de llm_connection_schemas.py
    para la auditoria real de cada adapter.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response({"schemas": list_connection_schemas()})


def _audit(action: str, *, actor, provider=None, detail=None, result="OK"):
    """Escribe una fila de auditoria. Nunca debe tumbar la vista que la llama
    (una falla al auditar no debe bloquear la accion real ya realizada)."""
    try:
        LLMProviderAuditLog.objects.create(
            action=action,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            provider=provider,
            detail=detail or {},
            result=result,
        )
    except Exception:
        logger.exception("No se pudo escribir LLMProviderAuditLog (accion=%s)", action)


class LLMProvidersView(APIView):
    """
    GET  /api/admin/v1/console/llm/providers/        -> lista de providers + sus modelos
    POST /api/admin/v1/console/llm/providers/         -> crea un provider

    GET/PATCH/DELETE /api/admin/v1/console/llm/providers/{id}/
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, provider_id=None, *args, **kwargs):
        if provider_id is not None:
            try:
                provider = LLMProviderConfig.objects.prefetch_related("models_config").get(
                    pk=provider_id
                )
            except LLMProviderConfig.DoesNotExist:
                return Response({"error": "Provider no encontrado"}, status=404)
            return Response(LLMProviderConfigSerializer(provider).data)

        providers = LLMProviderConfig.objects.prefetch_related("models_config").all()
        return Response(LLMProviderConfigSerializer(providers, many=True).data)

    def post(self, request, *args, **kwargs):
        serializer = LLMProviderConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        provider = serializer.save()
        _audit(
            "PROVIDER_CREATE", actor=request.user, provider=provider, detail={"slug": provider.slug}
        )
        return Response(LLMProviderConfigSerializer(provider).data, status=201)

    def patch(self, request, provider_id=None, *args, **kwargs):
        if provider_id is None:
            return Response({"error": "provider_id requerido"}, status=400)
        try:
            provider = LLMProviderConfig.objects.get(pk=provider_id)
        except LLMProviderConfig.DoesNotExist:
            return Response({"error": "Provider no encontrado"}, status=404)

        serializer = LLMProviderConfigSerializer(provider, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        provider = serializer.save()
        # detail sanitizado -- solo nombres de campo tocados, nunca valores
        # (podrian incluir "secret"). Regla Absoluta del plan "NO REGISTRAR SECRETOS".
        _audit(
            "PROVIDER_UPDATE",
            actor=request.user,
            provider=provider,
            detail={"fields": sorted(request.data.keys())},
        )
        return Response(LLMProviderConfigSerializer(provider).data)

    def delete(self, request, provider_id=None, *args, **kwargs):
        if provider_id is None:
            return Response({"error": "provider_id requerido"}, status=400)
        try:
            provider = LLMProviderConfig.objects.get(pk=provider_id)
        except LLMProviderConfig.DoesNotExist:
            return Response({"error": "Provider no encontrado"}, status=404)

        slug = provider.slug
        # Auditar ANTES de borrar -- el FK de LLMProviderAuditLog.provider es
        # SET_NULL, pero queremos que el detail conserve el slug igual.
        _audit("PROVIDER_DELETE", actor=request.user, provider=None, detail={"slug": slug})
        provider.delete()
        return Response({"mensaje": f"Provider '{slug}' eliminado."})


def _transient_model_config(provider_cfg: LLMProviderConfig, model_identifier: str | None):
    """
    `LLMModelConfig` SIN GUARDAR -- solo para construir el AIProvider real
    (`_build_runtime_provider_from_db` solo necesita `.provider` y
    `.model_identifier`, ambos disponibles en memoria). Permite probar
    conexion / descubrir modelos ANTES de que exista una fila de modelo
    guardada -- necesario para el flujo real de Ollama (validar -> GET
    /api/tags -> recien ahi el usuario elige que modelo guardar, spec
    seccion 13) y para providers "cheap_health=False" donde igual se
    quiere poder probar solo la URL/secreto sin un modelo todavia.
    """
    return LLMModelConfig(provider=provider_cfg, model_identifier=model_identifier or "")


class LLMProviderTestConnectionView(APIView):
    """
    POST /api/admin/v1/console/llm/providers/{id}/test/
    Body opcional: {"model_identifier": "..."}

    Prueba de conexion real: construye el AIProvider real desde la config
    guardada (mas el `model_identifier` del body, o el de un modelo ya
    guardado si no se manda ninguno) y llama a su `.health()` -- NUNCA
    simulado. NO requiere que exista un modelo guardado todavia (ver
    `_transient_model_config`) -- correccion 2026-09-24: antes exigia un
    modelo ya creado, lo que rompia el flujo real "validar primero,
    guardar modelo despues" que pide Ollama.

    AVISO REAL (no cosmetico): para `anthropic`/`openai_compatible`,
    `health()` no esta sobreescrito (ver llm_connection_schemas.py,
    `cheap_health: False`) -- hereda el default de AIProvider, que hace
    una llamada real a `complete()` (max_tokens=1). Si el proveedor cobra
    por uso, esta prueba consume un token/credito real de la cuenta del
    usuario (causa real observada en esta sesion con OpenRouter).
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, provider_id=None, *args, **kwargs):
        if provider_id is None:
            return Response({"error": "provider_id requerido"}, status=400)
        try:
            provider_cfg = LLMProviderConfig.objects.get(pk=provider_id)
        except LLMProviderConfig.DoesNotExist:
            return Response({"error": "Provider no encontrado"}, status=404)

        model_identifier = request.data.get("model_identifier")
        model_cfg = None
        if model_identifier:
            model_cfg = provider_cfg.models_config.filter(model_identifier=model_identifier).first()
        if model_cfg is None:
            model_cfg = provider_cfg.models_config.first()
        if model_cfg is None:
            model_cfg = _transient_model_config(provider_cfg, model_identifier)

        from django.utils.timezone import now

        from apps.services.ai.providers import _build_runtime_provider_from_db

        is_persisted = model_cfg.pk is not None

        try:
            runtime_provider = _build_runtime_provider_from_db(model_cfg)
            health = runtime_provider.health()
        except Exception as exc:
            logger.exception("Fallo construyendo/probando provider %s", provider_cfg.slug)
            if is_persisted:
                model_cfg.last_health_check_at = now()
                model_cfg.last_health_reachable = False
                model_cfg.save(update_fields=["last_health_check_at", "last_health_reachable"])
            _audit(
                "PROVIDER_TEST",
                actor=request.user,
                provider=provider_cfg,
                detail={"model": model_cfg.model_identifier, "error": str(exc)[:300]},
                result="ERROR",
            )
            return Response({"reachable": False, "error": str(exc)[:300]}, status=200)

        if is_persisted:
            # Fase 10 (Health, plan Seccion 29): "ultimo health check" es
            # parte explicita del modelo de datos conceptual -- se persiste
            # SOLO aqui, nunca a mano.
            model_cfg.last_health_check_at = health.checked_at
            model_cfg.last_health_reachable = health.reachable
            model_cfg.save(update_fields=["last_health_check_at", "last_health_reachable"])

        _audit(
            "PROVIDER_TEST",
            actor=request.user,
            provider=provider_cfg,
            detail={
                "model": model_cfg.model_identifier,
                "reachable": health.reachable,
                "latency_ms": health.latency_ms,
            },
            result="OK" if health.reachable else "ERROR",
        )
        return Response(
            {
                # Dimensiones del plan Seccion 29 ("HEALTH"): DNS/connectivity
                # + HTTP + Authentication quedan resumidas en `reachable`
                # (health() ya intenta la conexion real, con auth si aplica
                # -- separarlas requeriria que cada adapter distinga el tipo
                # de fallo, no implementado, NOT_IMPLEMENTED). Model
                # availability = `model_available`. Tools/Structured output
                # = ultimas capacidades YA verificadas (`supports_tools`/
                # `supports_structured_output`, pobladas solo por
                # "Verificar capacidades" -- Regla "NO ASUMIR CAPACIDADES",
                # este endpoint NO las vuelve a adivinar). Latencia =
                # `latency_ms`. Ultima comprobacion = `checked_at` (recien
                # persistida arriba si el modelo existe en DB).
                "reachable": health.reachable,
                "latency_ms": health.latency_ms,
                "model_available": health.model_available,
                "error": health.error,
                "checked_at": health.checked_at.isoformat(),
                "supports_tools": model_cfg.supports_tools if is_persisted else None,
                "supports_structured_output": model_cfg.supports_structured_output
                if is_persisted
                else None,
                "capabilities_verified": model_cfg.verified if is_persisted else False,
            }
        )


class LLMProviderDiscoverModelsView(APIView):
    """
    POST /api/admin/v1/console/llm/providers/{id}/discover-models/

    Descubrimiento REAL de modelos (`list_models()`) -- solo tiene sentido
    para providers con `supports_model_discovery=True` en
    llm_connection_schemas.py (hoy: solo Ollama, via GET /api/tags real).
    Para los demas, `list_models()` hereda `NotImplementedError` de
    AIProvider (base.py) -- esta vista lo traduce a una respuesta clara
    `{"supported": false}`, NUNCA a una lista inventada.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, provider_id=None, *args, **kwargs):
        if provider_id is None:
            return Response({"error": "provider_id requerido"}, status=400)
        try:
            provider_cfg = LLMProviderConfig.objects.get(pk=provider_id)
        except LLMProviderConfig.DoesNotExist:
            return Response({"error": "Provider no encontrado"}, status=404)

        schema = CONNECTION_SCHEMAS.get(provider_cfg.provider_type, {})
        if not schema.get("supports_model_discovery"):
            return Response(
                {
                    "supported": False,
                    "reason": (
                        f"'{provider_cfg.provider_type}' no expone un endpoint de "
                        "descubrimiento de modelos (list_models() no implementado "
                        "para este adapter) -- escribe el identificador del modelo "
                        "manualmente."
                    ),
                }
            )

        from apps.services.ai.providers import _build_runtime_provider_from_db

        transient = _transient_model_config(provider_cfg, None)
        try:
            runtime_provider = _build_runtime_provider_from_db(transient)
            descriptors = runtime_provider.list_models()
        except Exception as exc:
            logger.exception("Fallo descubriendo modelos de %s", provider_cfg.slug)
            return Response({"supported": True, "error": str(exc)[:300], "models": []})

        models = [
            {
                "model_id": d.model_id,
                "display_name": d.display_name,
                "context_window": d.context_window,
                "max_output_tokens": d.max_output_tokens,
                "capabilities": {
                    "chat": d.capabilities.chat,
                    "streaming": d.capabilities.streaming,
                    "tool_calling": d.capabilities.tool_calling,
                    "structured_output": d.capabilities.structured_output,
                    "vision": d.capabilities.vision,
                    "reasoning": d.capabilities.reasoning,
                    "verified": d.capabilities.verified,
                },
            }
            for d in descriptors
        ]
        return Response({"supported": True, "models": models})


class LLMModelsView(APIView):
    """
    GET  /api/admin/v1/console/llm/providers/{provider_id}/models/  -> modelos del provider
    POST /api/admin/v1/console/llm/providers/{provider_id}/models/  -> agrega un modelo

    PATCH/DELETE /api/admin/v1/console/llm/models/{id}/
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, provider_id=None, *args, **kwargs):
        if provider_id is None:
            return Response({"error": "provider_id requerido"}, status=400)
        models = LLMModelConfig.objects.filter(provider_id=provider_id).select_related("provider")
        return Response(LLMModelConfigSerializer(models, many=True).data)

    def post(self, request, provider_id=None, *args, **kwargs):
        if provider_id is None:
            return Response({"error": "provider_id requerido"}, status=400)
        try:
            provider = LLMProviderConfig.objects.get(pk=provider_id)
        except LLMProviderConfig.DoesNotExist:
            return Response({"error": "Provider no encontrado"}, status=404)

        data = dict(request.data)
        data["provider"] = provider.pk
        serializer = LLMModelConfigSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        model_cfg = serializer.save(provider=provider)
        return Response(LLMModelConfigSerializer(model_cfg).data, status=201)

    def patch(self, request, model_id=None, *args, **kwargs):
        if model_id is None:
            return Response({"error": "model_id requerido"}, status=400)
        try:
            model_cfg = LLMModelConfig.objects.get(pk=model_id)
        except LLMModelConfig.DoesNotExist:
            return Response({"error": "Modelo no encontrado"}, status=404)
        # Solo campos editables a mano (capacidades quedan fuera via read_only_fields).
        serializer = LLMModelConfigSerializer(model_cfg, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, model_id=None, *args, **kwargs):
        if model_id is None:
            return Response({"error": "model_id requerido"}, status=400)
        try:
            model_cfg = LLMModelConfig.objects.get(pk=model_id)
        except LLMModelConfig.DoesNotExist:
            return Response({"error": "Modelo no encontrado"}, status=404)
        model_cfg.delete()
        return Response({"mensaje": "Modelo eliminado."})


class LLMModelVerifyCapabilitiesView(APIView):
    """
    POST /api/admin/v1/console/llm/models/{id}/verify/

    Capability probe real (plan Seccion 22) -- llama a get_capabilities()
    del provider real y guarda el resultado. Regla Absoluta del plan
    "NO ASUMIR CAPACIDADES": este es el UNICO camino que puede poner
    verified=True en un LLMModelConfig via API.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, model_id=None, *args, **kwargs):
        if model_id is None:
            return Response({"error": "model_id requerido"}, status=400)
        try:
            model_cfg = LLMModelConfig.objects.select_related("provider").get(pk=model_id)
        except LLMModelConfig.DoesNotExist:
            return Response({"error": "Modelo no encontrado"}, status=404)

        from django.utils.timezone import now

        from apps.services.ai.providers import _build_runtime_provider_from_db

        try:
            runtime_provider = _build_runtime_provider_from_db(model_cfg)
            caps = runtime_provider.get_capabilities()
        except Exception as exc:
            logger.exception("Fallo verificando capacidades de %s", model_cfg)
            return Response({"error": str(exc)[:300]}, status=200)

        if caps.verified:
            model_cfg.supports_tools = caps.tool_calling
            model_cfg.supports_streaming = caps.streaming
            model_cfg.supports_structured_output = caps.structured_output
            model_cfg.supports_vision = caps.vision
            model_cfg.supports_reasoning = caps.reasoning
            model_cfg.verified = True
            model_cfg.verified_at = caps.verified_at or now()
            model_cfg.save(
                update_fields=[
                    "supports_tools",
                    "supports_streaming",
                    "supports_structured_output",
                    "supports_vision",
                    "supports_reasoning",
                    "verified",
                    "verified_at",
                ]
            )

        return Response(LLMModelConfigSerializer(model_cfg).data)


class LLMActivateModelView(APIView):
    """
    POST /api/admin/v1/console/llm/models/{id}/activate/
    Body opcional: {"reason": "..."}

    Activa un modelo (plan Seccion 24/25, "cambiar de modelo sin
    reiniciar"): crea una fila nueva en LLMActiveConfig -- NUNCA borra el
    historial (permite rollback, plan Seccion 27). resolve_active_llm()
    recoge esta fila en la SIGUIENTE llamada, sin reiniciar el contenedor.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, model_id=None, *args, **kwargs):
        if model_id is None:
            return Response({"error": "model_id requerido"}, status=400)
        try:
            model_cfg = LLMModelConfig.objects.select_related("provider").get(pk=model_id)
        except LLMModelConfig.DoesNotExist:
            return Response({"error": "Modelo no encontrado"}, status=404)

        if not model_cfg.enabled or not model_cfg.provider.enabled:
            return Response({"error": "El modelo o su provider estan deshabilitados"}, status=400)

        actor = request.user if request.user.is_authenticated else None
        active = LLMActiveConfig.objects.create(
            model_config=model_cfg,
            activated_by=actor,
            reason=str(request.data.get("reason", ""))[:500],
        )
        _audit(
            "MODEL_ACTIVATE",
            actor=request.user,
            provider=model_cfg.provider,
            detail={"model": model_cfg.model_identifier, "active_config_id": active.pk},
        )
        return Response(LLMActiveConfigSerializer(active).data, status=201)


class LLMActiveConfigView(APIView):
    """
    GET /api/admin/v1/console/llm/active/

    Plan Seccion 5/24: "MODELO ACTUALMENTE EN USO" -- debe reflejar lo que
    `resolve_active_llm()` REALMENTE va a usar en la siguiente llamada, no
    solo la fila mas reciente de LLMActiveConfig. Mismo filtro
    (`model_config__enabled=True`, `model_config__provider__enabled=True`)
    que `_load_active_provider_from_db()` (apps/services/ai/providers/
    __init__.py) -- correccion 2026-09-24: si la activacion mas reciente
    quedo deshabilitada, no se debe mostrar como "en uso" (seria mentirle
    al usuario), se busca la siguiente habilitada en el historial.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        base_qs = LLMActiveConfig.objects.select_related("model_config__provider", "activated_by")
        effective = (
            base_qs.filter(model_config__enabled=True, model_config__provider__enabled=True)
            .order_by("-activated_at")
            .first()
        )
        most_recent = base_qs.order_by("-activated_at").first()

        if effective is None:
            payload = {"active": None, "source": "env"}
            if most_recent is not None:
                # Hay historial, pero la mas reciente esta deshabilitada --
                # avisar por que el sistema NO la esta usando, en vez de
                # dejar la UI en silencio.
                payload["skipped_disabled"] = LLMActiveConfigSerializer(most_recent).data
            return Response(payload)

        payload = {"active": LLMActiveConfigSerializer(effective).data, "source": "db"}
        if most_recent is not None and most_recent.pk != effective.pk:
            payload["skipped_disabled"] = LLMActiveConfigSerializer(most_recent).data
        return Response(payload)


class LLMAuditLogView(APIView):
    """GET /api/admin/v1/console/llm/audit/ -- ultimas 200 entradas."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        logs = LLMProviderAuditLog.objects.select_related("actor", "provider")[:200]
        return Response(LLMProviderAuditLogSerializer(logs, many=True).data)
