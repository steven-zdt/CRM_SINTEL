#!/usr/bin/env python
"""
Script de Diagnóstico Completo para Creación de Tenants.

Audita todas las fases del proceso de creación de tenants desde la consola
hasta la ejecución de la tarea Celery.

Uso:
    python scripts/diagnostico_tenant_creation.py <task_id>
    # Ejemplo:
    python scripts/diagnostico_tenant_creation.py 261514e4-35d4-4e2d-87d4-09b01f702565
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from celery.result import AsyncResult
from django.db import connection
from django_tenants.utils import schema_exists, get_public_schema_name
from apps.public.tenants.models import Client, Domain, TenantMembership
from django.contrib.auth import get_user_model

User = get_user_model()


def diagnostico_completo(task_id: str):
    """Ejecuta diagnóstico completo del proceso de creación de tenant."""
    
    print("=" * 80)
    print("🔍 AUDITORÍA COMPLETA: Creación de Tenants Privados")
    print("=" * 80)
    print(f"Task ID: {task_id}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # ============================================================
    # FASE 1: Verificación de Celery
    # ============================================================
    print("📋 FASE 1: Verificación de Celery")
    print("-" * 80)
    
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        
        # Verificar workers activos
        active_workers = inspect.active()
        if active_workers:
            print(f"✅ Workers activos: {len(active_workers)}")
            for worker, tasks in active_workers.items():
                print(f"   - {worker}: {len(tasks)} tareas activas")
        else:
            print("❌ ERROR CRÍTICO: No hay workers de Celery activos")
            print("   💡 Solución: Ejecutar 'celery -A config worker -l info'")
            return False
        
        # Verificar tareas registradas
        registered = inspect.registered()
        if registered:
            all_tasks = set()
            for worker, tasks in registered.items():
                all_tasks.update(tasks)
            if 'apps.public.tenants.tasks.onboard_tenant_task' in all_tasks:
                print("✅ Tarea 'onboard_tenant_task' está registrada")
            else:
                print("❌ ERROR: Tarea 'onboard_tenant_task' NO está registrada")
                print(f"   Tareas disponibles: {list(all_tasks)[:10]}...")
        else:
            print("⚠️  No se pudieron obtener tareas registradas")
    except Exception as e:
        print(f"❌ Error al verificar Celery: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # ============================================================
    # FASE 2: Estado de la Tarea Celery
    # ============================================================
    print("📋 FASE 2: Estado de la Tarea Celery")
    print("-" * 80)
    
    try:
        result = AsyncResult(task_id)
        
        print(f"Estado: {result.state}")
        print(f"Listo: {result.ready()}")
        print(f"Exitoso: {result.successful()}")
        print(f"Fallido: {result.failed()}")
        
        if result.info:
            print(f"Info: {result.info}")
        
        if result.traceback:
            print(f"Traceback: {result.traceback}")
        
        # Estados posibles:
        # - PENDING: Tarea esperando ser ejecutada
        # - STARTED: Tarea en ejecución
        # - SUCCESS: Tarea completada exitosamente
        # - FAILURE: Tarea falló
        # - RETRY: Tarea en reintento
        # - REVOKED: Tarea cancelada
        
        if result.state == 'PENDING':
            print()
            print("⚠️  DIAGNÓSTICO: Tarea en estado PENDING")
            print("   Posibles causas:")
            print("   1. Celery worker no está procesando tareas")
            print("   2. La tarea no se encoló correctamente")
            print("   3. El worker está sobrecargado")
            print("   4. Hay un problema de conexión con el broker (Redis/RabbitMQ)")
            print()
            print("   Verificaciones:")
            
            # Verificar si la tarea está en la cola
            try:
                from celery import current_app
                inspect = current_app.control.inspect()
                scheduled = inspect.scheduled()
                reserved = inspect.reserved()
                
                if scheduled:
                    print(f"   - Tareas programadas: {len(scheduled)}")
                    for worker, tasks in scheduled.items():
                        for task in tasks:
                            if task.get('request', {}).get('id') == task_id:
                                print(f"     ✅ Tarea encontrada en cola programada de {worker}")
                
                if reserved:
                    print(f"   - Tareas reservadas: {len(reserved)}")
                    for worker, tasks in reserved.items():
                        for task in tasks:
                            if task.get('request', {}).get('id') == task_id:
                                print(f"     ✅ Tarea encontrada en cola reservada de {worker}")
                
                if not scheduled and not reserved:
                    print("   ❌ Tarea NO encontrada en ninguna cola")
                    print("   💡 La tarea puede no haberse encolado correctamente")
            except Exception as e:
                print(f"   ⚠️  No se pudo verificar colas: {e}")
        
        elif result.state == 'STARTED':
            print()
            print("ℹ️  Tarea en ejecución (STARTED)")
            print("   Esto es normal si la tarea está procesándose actualmente")
        
        elif result.state == 'SUCCESS':
            print()
            print("✅ Tarea completada exitosamente")
            if result.result:
                print(f"   Resultado: {result.result}")
        
        elif result.state == 'FAILURE':
            print()
            print("❌ Tarea falló")
            if result.info:
                print(f"   Error: {result.info}")
            if result.traceback:
                print(f"   Traceback: {result.traceback}")
        
    except Exception as e:
        print(f"❌ Error al consultar estado de tarea: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # ============================================================
    # FASE 3: Verificación de Base de Datos
    # ============================================================
    print("📋 FASE 3: Verificación de Base de Datos")
    print("-" * 80)
    
    try:
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        public_schema = get_public_schema_name()
        print(f"Esquema actual: {public_schema}")
        
        # Verificar si se creó algún Client recientemente
        # (podría haberse creado antes de que la tarea fallara)
        clients_recientes = Client.objects.filter(
            created_on__gte=datetime.now().replace(hour=0, minute=0, second=0)
        ).order_by('-created_on')[:5]
        
        print(f"Clientes creados hoy: {clients_recientes.count()}")
        for client in clients_recientes:
            print(f"   - {client.nombre} (schema: {client.schema_name}, creado: {client.created_on})")
        
        # Verificar si hay algún Client sin Domain (incompleto)
        clients_sin_domain = []
        for client in Client.objects.all():
            domain = Domain.objects.filter(tenant=client, is_primary=True).first()
            if not domain:
                clients_sin_domain.append(client)
        
        if clients_sin_domain:
            print(f"⚠️  Clientes sin dominio principal: {len(clients_sin_domain)}")
            for client in clients_sin_domain:
                print(f"   - {client.nombre} (schema: {client.schema_name})")
        else:
            print("✅ Todos los clientes tienen dominio principal")
        
    except Exception as e:
        print(f"❌ Error al verificar base de datos: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # ============================================================
    # FASE 4: Verificación de Logs de Celery
    # ============================================================
    print("📋 FASE 4: Verificación de Logs de Celery")
    print("-" * 80)
    print("💡 Para ver logs en tiempo real, ejecutar:")
    print("   docker-compose logs -f celery")
    print("   # o")
    print("   celery -A config worker -l info")
    print()
    
    # ============================================================
    # FASE 5: Recomendaciones
    # ============================================================
    print("📋 FASE 5: Recomendaciones")
    print("-" * 80)
    
    if result.state == 'PENDING':
        print("🔧 Acciones recomendadas:")
        print("   1. Verificar que Celery worker esté corriendo:")
        print("      docker-compose ps celery")
        print("      # o")
        print("      ps aux | grep celery")
        print()
        print("   2. Reiniciar Celery worker:")
        print("      docker-compose restart celery")
        print("      # o")
        print("      pkill -f 'celery worker' && celery -A config worker -l info")
        print()
        print("   3. Verificar conexión con broker (Redis):")
        print("      docker-compose ps redis")
        print("      redis-cli ping")
        print()
        print("   4. Reintentar creación del tenant desde la consola")
        print()
        print("   5. Si persiste, verificar logs:")
        print("      docker-compose logs celery | grep -i error")
    
    print()
    print("=" * 80)
    print("✅ Diagnóstico completado")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/diagnostico_tenant_creation.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    try:
        diagnostico_completo(task_id)
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
