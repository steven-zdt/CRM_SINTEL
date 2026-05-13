"""
Tareas Celery para la app contabilidad (v3.5).
Aislamiento por esquema mediante django-tenants.
"""
import logging
from celery import shared_task
from django_tenants.utils import schema_context
from apps.tenant.contabilidad.services.business_service import ContabilidadBusinessService
from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)

@shared_task(name="apps.tenant.contabilidad.tasks.ejecutar_integracion_contable_task")
def ejecutar_integracion_contable_task(schema_name: str):
    """
    Tarea Celery tenant-aware para ejecutar el proceso ETL contable completo.
    Sincroniza Facturas, Gastos e Inventario hacia el Libro Mayor.
    """
    logger.info(f"[CELERY:CONTABILIDAD] Iniciando integracion para schema: {schema_name}")
    
    with schema_context(schema_name):
        try:
            empresa = Empresa.objects.first()
            if not empresa:
                msg = f"No se encontro empresa configurada en el esquema {schema_name}"
                logger.error(f"[CELERY:CONTABILIDAD] {msg}")
                return {"status": "error", "message": msg}
            
            # Orquestacion via Business Service
            service = ContabilidadBusinessService()
            resumen = service.ejecutar_integracion_completa(empresa.id)
            
            logger.info(f"[CELERY:CONTABILIDAD] Integracion exitosa en {schema_name}. Resumen: {resumen}")
            return {
                "status": "success",
                "schema": schema_name,
                "resumen": resumen
            }
        except Exception as e:
            logger.exception(f"[CELERY:CONTABILIDAD] Fallo critico en tarea para {schema_name}")
            return {
                "status": "error", 
                "message": str(e),
                "schema": schema_name
            }

@shared_task(name="apps.tenant.contabilidad.tasks.integracion_contable_global_task")
def integracion_contable_global_task():
    """
    Tarea broadcast: recorre todos los tenants y encola su integracion individual.
    Util para ejecucion periodica (Beats).
    """
    from django_tenants.utils import get_tenant_model
    TenantModel = get_tenant_model()
    # Excluimos el esquema publico (home)
    tenants = TenantModel.objects.exclude(schema_name='public').values_list('schema_name', flat=True)
    
    for schema in tenants:
        ejecutar_integracion_contable_task.delay(schema)
    
    return {"enqueued_tenants": len(tenants)}
