"""
Document Ingest Service Layer (Orchestration/routing/validation).

WARNING: PRINCIPIOS:
- Orquestación: Coordina parsing, normalización, validación y opcionalmente persistencia
- Agnóstico del dominio: No conoce modelos Django, delega persistencia a services de dominio
- Preview mode: Permite parsear sin persistir
- Transaccional: Todo o nada (transaction.atomic)
- WARNING: v2.40: Routing por app - cada app tiene sus parsers y validadores independientes

Estructura (FASE 1 + v2.40):
- router.py: Enrutamiento de documentos a parsers (incluye registry simplificado)
- app_router.py: Router específico por app (v2.40)
- ingest_service.py: Servicio principal de ingesta
- validators.py: Validación de integridad y campos obligatorios
- validations/: Validadores específicos por app
"""
# WARNING: v2.40: Auto-importar parsers de apps para registro automático
try:
    # Importar registro de parsers (registra automáticamente todos los parsers de todas las apps)
    from apps.services.document_parser import register_parsers  # noqa: F401
except ImportError:
    # Si hay un error, intentar importar directamente los módulos de apps
    try:
        import apps.services.document_parser.cotizaciones  # noqa: F401
        import apps.services.document_parser.facturas  # noqa: F401
    except ImportError:
        pass  # Si no está disponible, continuar sin error