"""
Comando de management para diagnosticar problemas en la creación de tenants.

Uso:
    python manage.py diagnostico_tenant <task_id>
"""
from django.core.management.base import BaseCommand
from celery.result import AsyncResult
from django.db import connection
from django_tenants.utils import schema_exists, get_public_schema_name
from apps.public.tenants.models import Client, Domain
from datetime import datetime


class Command(BaseCommand):
    help = 'Diagnostica problemas en la creación de tenants'

    def add_arguments(self, parser):
        parser.add_argument('task_id', type=str, help='ID de la tarea Celery')

    def handle(self, *args, **options):
        task_id = options['task_id']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('🔍 AUDITORÍA COMPLETA: Creación de Tenants Privados'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'Task ID: {task_id}')
        self.stdout.write(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write('')
        
        # FASE 1: Verificación de Celery
        self.stdout.write('📋 FASE 1: Verificación de Celery')
        self.stdout.write('-' * 80)
        
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            
            active_workers = inspect.active()
            if active_workers:
                self.stdout.write(self.style.SUCCESS(f'✅ Workers activos: {len(active_workers)}'))
                for worker, tasks in active_workers.items():
                    self.stdout.write(f'   - {worker}: {len(tasks)} tareas activas')
            else:
                self.stdout.write(self.style.ERROR('❌ ERROR CRÍTICO: No hay workers de Celery activos'))
                self.stdout.write(self.style.WARNING('   💡 Solución: Ejecutar "celery -A config worker -l info"'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al verificar Celery: {e}'))
            return
        
        self.stdout.write('')
        
        # FASE 2: Estado de la Tarea
        self.stdout.write('📋 FASE 2: Estado de la Tarea Celery')
        self.stdout.write('-' * 80)
        
        try:
            result = AsyncResult(task_id)
            
            self.stdout.write(f'Estado: {result.state}')
            self.stdout.write(f'Listo: {result.ready()}')
            self.stdout.write(f'Exitoso: {result.successful()}')
            self.stdout.write(f'Fallido: {result.failed()}')
            
            if result.info:
                self.stdout.write(f'Info: {result.info}')
            
            if result.traceback:
                self.stdout.write(self.style.ERROR(f'Traceback: {result.traceback}'))
            
            if result.state == 'PENDING':
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('⚠️  DIAGNÓSTICO: Tarea en estado PENDING'))
                self.stdout.write('   Posibles causas:')
                self.stdout.write('   1. Celery worker no está procesando tareas')
                self.stdout.write('   2. La tarea no se encoló correctamente')
                self.stdout.write('   3. El worker está sobrecargado')
                self.stdout.write('   4. Hay un problema de conexión con el broker (Redis/RabbitMQ)')
                
                # Verificar colas
                try:
                    scheduled = inspect.scheduled()
                    reserved = inspect.reserved()
                    
                    if scheduled:
                        for worker, tasks in scheduled.items():
                            for task in tasks:
                                if task.get('request', {}).get('id') == task_id:
                                    self.stdout.write(self.style.SUCCESS(f'     ✅ Tarea encontrada en cola programada de {worker}'))
                    
                    if reserved:
                        for worker, tasks in reserved.items():
                            for task in tasks:
                                if task.get('request', {}).get('id') == task_id:
                                    self.stdout.write(self.style.SUCCESS(f'     ✅ Tarea encontrada en cola reservada de {worker}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  No se pudo verificar colas: {e}'))
            
            elif result.state == 'SUCCESS':
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✅ Tarea completada exitosamente'))
                if result.result:
                    self.stdout.write(f'   Resultado: {result.result}')
            
            elif result.state == 'FAILURE':
                self.stdout.write('')
                self.stdout.write(self.style.ERROR('❌ Tarea falló'))
                if result.info:
                    self.stdout.write(self.style.ERROR(f'   Error: {result.info}'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al consultar estado: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
        
        self.stdout.write('')
        
        # FASE 3: Base de Datos
        self.stdout.write('📋 FASE 3: Verificación de Base de Datos')
        self.stdout.write('-' * 80)
        
        try:
            connection.set_schema_to_public()
            clients_recientes = Client.objects.filter(
                created_on__gte=datetime.now().replace(hour=0, minute=0, second=0)
            ).order_by('-created_on')[:5]
            
            self.stdout.write(f'Clientes creados hoy: {clients_recientes.count()}')
            for client in clients_recientes:
                self.stdout.write(f'   - {client.nombre} (schema: {client.schema_name})')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('✅ Diagnóstico completado'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
