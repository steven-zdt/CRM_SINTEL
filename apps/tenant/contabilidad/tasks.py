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

@shared_task(
    name="apps.tenant.contabilidad.tasks.ejecutar_integracion_contable_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def ejecutar_integracion_contable_task(self, schema_name: str):
    """
    Tarea Celery tenant-aware para ejecutar el proceso ETL contable completo.
    Sincroniza Facturas, Gastos e Inventario hacia el Libro Mayor.
    """
    logger.info(f"[CELERY:CONTABILIDAD] Iniciando integracion para schema: {schema_name} [retry={self.request.retries}]")
    
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
            logger.error(
                f"[CELERY:CONTABILIDAD] Fallo en tarea para {schema_name} [retry={self.request.retries}/{self.max_retries}]: {e}",
                exc_info=True,
            )
            if self.request.retries >= self.max_retries:
                from apps.tenant.core.services.membership import registrar_failed_task
                registrar_failed_task(
                    task_id=self.request.id,
                    task_name=self.name,
                    args=[schema_name],
                    kwargs={},
                    exception=e,
                    schema_name=schema_name,
                    retries=self.request.retries,
                )
                logger.error(
                    f"[DLQ] ejecutar_integracion_contable_task registrada en FailedTenantTask tras {self.request.retries} intentos | schema={schema_name}"
                )
                return {
                    "status": "failed_dlq",
                    "schema": schema_name,
                    "message": str(e)
                }
            raise self.retry(exc=e)

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
