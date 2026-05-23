"""
Package de Servicios para Proyectos v3.5

Este paquete implementa la arquitectura modular SINTEL v3.5:
- selectors.py: Consultas optimizadas (Zero Waste)
- crud_service.py: Persistencia atómica
- business_service.py: Lógica de negocio y orquestación
"""

from .selectors import (
    LIST_FIELDS,
    DETAIL_FIELDS,
    qs_list,
    qs_detail
)

from .crud_service import (
    save_proyecto,
    delete_proyecto,
    save_asignacion,
    delete_asignacion,
    save_pedido,
    delete_pedido
)

from .business_service import (
    calcular_indicadores_financieros,
    asignar_snapshot_cliente,
    asignar_snapshot_responsable,
    cambiar_fase_proyecto,
    orchestrate_create_proyecto,
    orchestrate_update_proyecto
)

from .presupuesto_service import (
    PresupuestoBusinessService,
    ITEM_FIELDS as PRESUPUESTO_ITEM_FIELDS
)

from .tareas_service import (
    TareasDiariasCRUDService,
    TareasDiariasBusinessService,
    TareasDiariasSelector,
    TAREA_FIELDS
)

from .api_mixins import ProyectoServiceMixin
