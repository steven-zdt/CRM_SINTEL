"""
Serializers del endpoint HTTP de AI-06 (Form Assistant). Solo valida
forma de entrada -- toda la logica real (permisos, contexto, decision
de tool) vive en `apps/services/ai/orchestrator/form_assistant.py`.
"""
from rest_framework import serializers


class AIScreenContextSerializer(serializers.Serializer):
    """Mismo shape que `build_context(screen={...})` ya acepta (Fase 23) --
    exactamente 4 claves conocidas, cualquier otra se descarta aqui mismo
    (antes de llegar siquiera a build_context, que ya las ignora tambien --
    doble capa, no solo una)."""
    app = serializers.CharField(required=False, allow_blank=True, max_length=100)
    entity = serializers.CharField(required=False, allow_blank=True, max_length=100)
    entity_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    operation = serializers.CharField(required=False, allow_blank=True, max_length=50)


class AIAskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, allow_blank=False)
    screen = AIScreenContextSerializer(required=False)
