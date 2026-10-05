"""
Package de Servicios para Proyectos v3.5

Este paquete implementa la arquitectura modular SINTEL v3.5:
- selectors.py: Consultas optimizadas (Zero Waste)
- crud_service.py: Persistencia atomica
- business_service.py: Logica de negocio y orquestacion
"""

from .api_mixins import TareaCortaServiceMixin
from .business_service import (
    TareasCortasBusinessService,
    asignar_snapshot_cliente,
    asignar_snapshot_responsable,
    calcular_ejecucion_tiempo,
    calcular_indicadores_financieros,
    cambiar_fase_proyecto,
    orchestrate_create_proyecto,
    orchestrate_update_proyecto,
)
from .cotizacion_planeacion_service import (
    ProyectoCotizacionPlaneacionService,
    mapear_tipo_item_a_recurso,
)
from .crud_service import (
    delete_asignacion,
    delete_pedido,
    delete_proyecto,
    delete_tarea_corta,
    save_asignacion,
    save_pedido,
    save_proyecto,
    save_tarea_corta,
)
from .documentos_service import (
    DOCUMENTO_FIELDS,
    DocumentosBusinessService,
    DocumentosCRUDService,
    documentos_faltantes,
    documentos_obligatorios_faltantes,
    resolver_requisitos_transicion,
    validar_archivo,
)
from .gastos_proyecto_service import GastosProyectoService
from .presupuesto_service import ITEM_FIELDS as PRESUPUESTO_ITEM_FIELDS
from .presupuesto_service import PresupuestoBusinessService
from .selectors import (
    DETAIL_FIELDS,
    LIST_FIELDS,
    TAREA_CORTA_FIELDS,
    TareaCortaSelector,
    qs_detail,
    qs_list,
)
from .tareas_service import (
    TAREA_FIELDS,
    TareasDiariasBusinessService,
    TareasDiariasCRUDService,
    TareasDiariasSelector,
)

# Re-exports publicos del Service Layer (SSoT) -- declarados explicitamente
# para que ruff (F401) no los marque como "importados pero no usados": el
# proposito de este __init__.py es precisamente exponerlos a otros modulos
# via `from apps.tenant.proyectos.services import X`.
__all__ = [
    "TareaCortaServiceMixin",
    "TareasCortasBusinessService",
    "asignar_snapshot_cliente",
    "asignar_snapshot_responsable",
    "calcular_ejecucion_tiempo",
    "calcular_indicadores_financieros",
    "cambiar_fase_proyecto",
    "orchestrate_create_proyecto",
    "orchestrate_update_proyecto",
    "ProyectoCotizacionPlaneacionService",
    "mapear_tipo_item_a_recurso",
    "delete_asignacion",
    "delete_pedido",
    "delete_proyecto",
    "delete_tarea_corta",
    "save_asignacion",
    "save_pedido",
    "save_proyecto",
    "save_tarea_corta",
    "DOCUMENTO_FIELDS",
    "DocumentosBusinessService",
    "DocumentosCRUDService",
    "documentos_faltantes",
    "documentos_obligatorios_faltantes",
    "resolver_requisitos_transicion",
    "validar_archivo",
    "GastosProyectoService",
    "PRESUPUESTO_ITEM_FIELDS",
    "PresupuestoBusinessService",
    "DETAIL_FIELDS",
    "LIST_FIELDS",
    "TAREA_CORTA_FIELDS",
    "TareaCortaSelector",
    "qs_detail",
    "qs_list",
    "TAREA_FIELDS",
    "TareasDiariasBusinessService",
    "TareasDiariasCRUDService",
    "TareasDiariasSelector",
]
