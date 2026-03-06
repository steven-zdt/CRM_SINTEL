"""
Comando de management para diagnóstico forense de creación de tenants.

Este comando ejecuta pruebas paso a paso para identificar exactamente dónde
se rompe la cadena de creación de tenants.

Uso:
    python manage.py debug_tenant_creation
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction, connection
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_exists
from celery import current_app
from celery.result import AsyncResult
from datetime import datetime
from django.test import override_settings

User = get_user_model()


class Command(BaseCommand):
    help = 'Diagnóstico forense paso a paso para creación de tenants'

    def print_header(self, title: str):
        """Imprime un encabezado formateado."""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS(f"🔍 {title}"))
        self.stdout.write("=" * 80)

    def print_success(self, message: str):
        """Imprime un mensaje de éxito."""
        self.stdout.write(self.style.SUCCESS(f"✅ {message}"))

    def print_error(self, message: str):
        """Imprime un mensaje de error."""
        self.stdout.write(self.style.ERROR(f"❌ {message}"))

    def print_warning(self, message: str):
        """Imprime un mensaje de advertencia."""
        self.stdout.write(self.style.WARNING(f"⚠️  {message}"))

    def print_info(self, message: str):
        """Imprime un mensaje informativo."""
        self.stdout.write(f"ℹ️  {message}")

    # ============================================================
    # PRUEBA 1: Validación de Configuración
    # ============================================================
    def prueba_1_configuracion(self):
        """PRUEBA 1: Validar configuración de Celery."""
        self.print_header("PRUEBA 1: Validación de Configuración (Settings)")
        
        try:
            # Verificar CELERY_BROKER_URL
            broker_url = getattr(settings, 'CELERY_BROKER_URL', None)
            if broker_url:
                self.print_success(f"CELERY_BROKER_URL: {broker_url}")
            else:
                self.print_error("CELERY_BROKER_URL no está configurado")
                return False
            
            # Verificar CELERY_TASK_ROUTES
            task_routes = getattr(settings, 'CELERY_TASK_ROUTES', {})
            self.print_info(f"CELERY_TASK_ROUTES configurado: {len(task_routes)} rutas")
            
            # Verificar ruta específica para onboard_tenant_task
            task_name = 'apps.public.tenants.tasks.onboard_tenant_task'
            if task_name in task_routes:
                route = task_routes[task_name]
                queue = route.get('queue', 'default')
                if queue == 'high_priority':
                    self.print_success(f"Tarea '{task_name}' enrutada a cola 'high_priority'")
                else:
                    self.print_warning(f"Tarea '{task_name}' enrutada a cola '{queue}' (esperado: 'high_priority')")
            else:
                self.print_warning(f"Tarea '{task_name}' NO encontrada en CELERY_TASK_ROUTES")
                self.print_info("Verificando si está en la ruta catch-all '*'...")
                if '*' in task_routes:
                    default_queue = task_routes['*'].get('queue', 'default')
                    self.print_warning(f"Tarea irá a cola por defecto: '{default_queue}'")
            
            # Verificar CELERY_TASK_DEFAULT_QUEUE
            default_queue = getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', 'default')
            self.print_info(f"CELERY_TASK_DEFAULT_QUEUE: {default_queue}")
            
            # Verificar que la app de Celery está configurada
            try:
                app = current_app
                self.print_success(f"Celery app inicializada: {app.main}")
            except Exception as e:
                self.print_error(f"Error al inicializar Celery app: {e}")
                return False
            
            self.print_success("PRUEBA 1: Configuración válida")
            return True
            
        except Exception as e:
            self.print_error(f"Error en PRUEBA 1: {e}")
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return False

    # ============================================================
    # PRUEBA 2: Creación Síncrona (Logic Check)
    # ============================================================
    def prueba_2_creacion_sincrona(self):
        """PRUEBA 2: Crear tenant síncronamente (sin Celery)."""
        self.print_header("PRUEBA 2: Creación Síncrona (Logic Check)")
        
        test_schema = f"test_sync_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        test_nombre = "Test Sync Tenant"
        
        try:
            from apps.services.onboarding.empresa_service import crear_tenant
            from apps.public.tenants.models import Client, Domain, TenantMembership
            
            # Obtener o crear usuario admin de prueba
            admin_user, _ = User.objects.get_or_create(
                email='test-admin@debug.local',
                defaults={
                    'username': 'test-admin',
                    'is_staff': True,
                }
            )
            self.print_info(f"Usuario admin de prueba: {admin_user.email} (ID: {admin_user.id})")
            
            # Asegurar que estamos en esquema public
            connection.set_schema_to_public()
            self.print_info("Esquema actual: public")
            
            # Verificar que el schema no existe
            if Client.objects.filter(schema_name=test_schema).exists():
                self.print_warning(f"Schema '{test_schema}' ya existe, eliminando...")
                Client.objects.filter(schema_name=test_schema).delete()
            
            self.print_info(f"Creando tenant síncronamente: {test_nombre} (schema: {test_schema})")
            
            # Ejecutar creación síncrona
            with transaction.atomic():
                client, domain, login_url = crear_tenant(
                    nombre=test_nombre,
                    schema_name=test_schema,
                    admin_user_id=admin_user.id
                )
                
                # Validar que se creó el Client
                if Client.objects.filter(schema_name=test_schema).exists():
                    self.print_success(f"✅ Client creado: {client.nombre} (ID: {client.id})")
                else:
                    self.print_error("❌ Client NO fue creado en la base de datos")
                    return False
                
                # Validar que se creó el Domain (por señal)
                domain_check = Domain.objects.filter(tenant=client, is_primary=True).first()
                if domain_check:
                    self.print_success(f"✅ Domain creado por señal: {domain_check.domain}")
                else:
                    self.print_error("❌ Domain NO fue creado por la señal post_save")
                    return False
                
                # Validar que se creó el esquema PostgreSQL
                if schema_exists(test_schema):
                    self.print_success(f"✅ Esquema PostgreSQL creado: {test_schema}")
                else:
                    self.print_error(f"❌ Esquema PostgreSQL '{test_schema}' NO existe")
                    return False
                
                # Validar que se creó TenantMembership
                membership = TenantMembership.objects.filter(
                    client=client,
                    user=admin_user
                ).first()
                if membership:
                    self.print_success(f"✅ TenantMembership creado: {admin_user.email} -> {client.nombre} ({membership.rol})")
                else:
                    self.print_error("❌ TenantMembership NO fue creado")
                    return False
                
                self.print_info(f"Login URL: {login_url}")
                
                # Hacer rollback para no ensuciar la BD
                transaction.set_rollback(True)
                self.print_info("Rollback realizado (tenant de prueba no se guardó)")
            
            self.print_success("PRUEBA 2: Creación síncrona exitosa (lógica de negocio correcta)")
            return True
            
        except Exception as e:
            self.print_error(f"Error en PRUEBA 2: {e}")
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return False

    # ============================================================
    # PRUEBA 3: Simulación Asíncrona Local (Eager Mode)
    # ============================================================
    def prueba_3_celery_eager(self):
        """PRUEBA 3: Probar con Celery en modo eager (síncrono)."""
        self.print_header("PRUEBA 3: Simulación Asíncrona Local (Eager Mode)")
        
        test_schema = f"test_eager_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        test_nombre = "Test Eager Tenant"
        
        try:
            from apps.public.tenants.tasks import onboard_tenant_task
            from apps.public.tenants.models import Client
            
            # Obtener usuario admin
            admin_user = User.objects.filter(email='test-admin@debug.local').first()
            if not admin_user:
                admin_user = User.objects.create_user(
                    email='test-admin@debug.local',
                    username='test-admin',
                    is_staff=True,
                )
            
            self.print_info(f"Usuario admin: {admin_user.email} (ID: {admin_user.id})")
            
            # Configurar Celery en modo eager
            self.print_info("Configurando Celery en modo EAGER (ejecución síncrona)...")
            
            with override_settings(
                CELERY_TASK_ALWAYS_EAGER=True,
                CELERY_TASK_EAGER_PROPAGATES=True,
            ):
                # Verificar que el schema no existe
                if Client.objects.filter(schema_name=test_schema).exists():
                    self.print_warning(f"Schema '{test_schema}' ya existe, eliminando...")
                    Client.objects.filter(schema_name=test_schema).delete()
                
                self.print_info(f"Encolando tarea (modo eager): {test_nombre} (schema: {test_schema})")
                
                # Encolar tarea (se ejecutará inmediatamente en modo eager)
                task = onboard_tenant_task.delay(
                    nombre=test_nombre,
                    schema_name=test_schema,
                    admin_user_id=admin_user.id
                )
                
                self.print_info(f"Task ID: {task.id}")
                self.print_info(f"Task ready: {task.ready()}")
                self.print_info(f"Task successful: {task.successful()}")
                
                # En modo eager, la tarea se ejecuta inmediatamente
                if task.ready():
                    if task.successful():
                        result = task.result
                        self.print_success(f"✅ Tarea completada exitosamente en modo eager")
                        self.print_info(f"   Resultado: {result}")
                        
                        # Validar que se creó el tenant
                        client = Client.objects.filter(schema_name=test_schema).first()
                        if client:
                            self.print_success(f"✅ Tenant creado: {client.nombre} (ID: {client.id})")
                            
                            # Limpiar: eliminar tenant de prueba
                            self.print_info("Limpiando tenant de prueba...")
                            client.delete()
                            self.print_info("Tenant de prueba eliminado")
                        else:
                            self.print_error("❌ Tenant NO fue creado (aunque la tarea fue exitosa)")
                            return False
                    else:
                        self.print_error(f"❌ Tarea falló: {task.info}")
                        return False
                else:
                    self.print_error("❌ Tarea no está lista (no debería pasar en modo eager)")
                    return False
            
            self.print_success("PRUEBA 3: Celery eager mode exitoso (tarea se ejecuta correctamente)")
            return True
            
        except Exception as e:
            self.print_error(f"Error en PRUEBA 3: {e}")
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return False

    # ============================================================
    # PRUEBA 4: Inyección de Tarea Real (Queue Check)
    # ============================================================
    def prueba_4_cola_real(self):
        """PRUEBA 4: Probar con cola real de Celery."""
        self.print_header("PRUEBA 4: Inyección de Tarea Real (Queue Check)")
        
        test_schema = f"test_queue_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        test_nombre = "Test Queue Tenant"
        
        try:
            from apps.public.tenants.tasks import onboard_tenant_task
            from apps.public.tenants.models import Client
            import time
            
            # Verificar que NO estamos en modo eager
            is_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
            if is_eager:
                self.print_warning("⚠️  CELERY_TASK_ALWAYS_EAGER está activado. Esta prueba requiere modo real.")
                self.print_info("Continuando de todas formas...")
            
            # Obtener usuario admin
            admin_user = User.objects.filter(email='test-admin@debug.local').first()
            if not admin_user:
                admin_user = User.objects.create_user(
                    email='test-admin@debug.local',
                    username='test-admin',
                    is_staff=True,
                )
            
            self.print_info(f"Usuario admin: {admin_user.email} (ID: {admin_user.id})")
            
            # Verificar que el schema no existe
            if Client.objects.filter(schema_name=test_schema).exists():
                self.print_warning(f"Schema '{test_schema}' ya existe, eliminando...")
                Client.objects.filter(schema_name=test_schema).delete()
            
            # Verificar workers activos
            self.print_info("Verificando workers de Celery...")
            inspect = current_app.control.inspect()
            
            # Verificar workers activos
            active_workers = inspect.active()
            if active_workers:
                self.print_success(f"Workers activos encontrados: {len(active_workers)}")
                for worker, tasks in active_workers.items():
                    self.print_info(f"   - {worker}: {len(tasks)} tareas activas")
            else:
                self.print_error("❌ No hay workers activos de Celery")
                self.print_warning("💡 Solución: Ejecutar 'docker-compose up -d celery' o 'celery -A config worker -l info -Q high_priority,default'")
                return False
            
            # Verificar workers registrados
            registered = inspect.registered()
            if registered:
                all_tasks = set()
                for worker, tasks in registered.items():
                    all_tasks.update(tasks)
                
                task_name = 'apps.public.tenants.tasks.onboard_tenant_task'
                if task_name in all_tasks:
                    self.print_success(f"Tarea '{task_name}' está registrada en workers")
                else:
                    self.print_warning(f"Tarea '{task_name}' NO está registrada en workers")
                    self.print_info(f"Tareas registradas (primeras 10): {list(all_tasks)[:10]}")
            
            # Verificar colas que escuchan los workers
            self.print_info("Verificando colas que escuchan los workers...")
            stats = inspect.stats()
            if stats:
                for worker, worker_stats in stats.items():
                    self.print_info(f"   - {worker}: {worker_stats.get('pool', {}).get('max-concurrency', 'N/A')} workers")
            
            # Encolar tarea real
            self.print_info(f"Encolando tarea real en cola 'high_priority': {test_nombre} (schema: {test_schema})")
            
            task = onboard_tenant_task.delay(
                nombre=test_nombre,
                schema_name=test_schema,
                admin_user_id=admin_user.id
            )
            
            task_id = task.id
            self.print_success(f"✅ Tarea encolada. Task ID: {task_id}")
            
            # Verificar que la tarea está en la cola
            self.print_info("Verificando que la tarea está en la cola...")
            
            # Esperar un momento para que la tarea se encole
            time.sleep(1)
            
            # Verificar tareas programadas
            scheduled = inspect.scheduled()
            if scheduled:
                for worker, tasks in scheduled.items():
                    for t in tasks:
                        if t.get('request', {}).get('id') == task_id:
                            self.print_success(f"✅ Tarea encontrada en cola programada de {worker}")
            
            # Verificar tareas reservadas
            reserved = inspect.reserved()
            if reserved:
                for worker, tasks in reserved.items():
                    for t in tasks:
                        if t.get('request', {}).get('id') == task_id:
                            self.print_success(f"✅ Tarea encontrada en cola reservada de {worker}")
            
            # Verificar estado de la tarea
            result = AsyncResult(task_id)
            self.print_info(f"Estado inicial de la tarea: {result.state}")
            
            # Esperar un momento para ver si el worker la toma
            self.print_info("Esperando 3 segundos para ver si el worker toma la tarea...")
            time.sleep(3)
            
            result = AsyncResult(task_id)
            self.print_info(f"Estado después de 3 segundos: {result.state}")
            
            if result.state == 'PENDING':
                self.print_error("❌ Tarea sigue en PENDING después de 3 segundos")
                self.print_warning("💡 DIAGNÓSTICO: El worker NO está procesando la tarea")
                self.print_warning("💡 Posibles causas:")
                self.print_warning("   1. El worker no está escuchando la cola 'high_priority'")
                self.print_warning("   2. El worker está sobrecargado")
                self.print_warning("   3. Hay un problema de conexión con Redis")
                self.print_warning("   4. La tarea no se encoló en la cola correcta")
                self.print_info("💡 Solución: Verificar comando del worker en docker-compose.yaml")
                self.print_info("   Debe incluir: -Q high_priority,default")
                
                # Limpiar: cancelar tarea si es posible
                try:
                    current_app.control.revoke(task_id, terminate=True)
                    self.print_info("Tarea cancelada")
                except:
                    pass
                
                return False
            elif result.state == 'STARTED':
                self.print_success("✅ Tarea fue tomada por el worker (estado: STARTED)")
                self.print_info("Esperando a que termine...")
                
                # Esperar hasta que termine (máximo 60 segundos)
                for i in range(60):
                    time.sleep(1)
                    result = AsyncResult(task_id)
                    if result.ready():
                        break
                    self.print_info(f"   Esperando... ({i+1}/60) - Estado: {result.state}")
                
                if result.ready():
                    if result.successful():
                        self.print_success("✅ Tarea completada exitosamente")
                        self.print_info(f"   Resultado: {result.result}")
                        
                        # Limpiar: eliminar tenant de prueba
                        client = Client.objects.filter(schema_name=test_schema).first()
                        if client:
                            self.print_info("Limpiando tenant de prueba...")
                            client.delete()
                            self.print_info("Tenant de prueba eliminado")
                    else:
                        self.print_error(f"❌ Tarea falló: {result.info}")
                        return False
                else:
                    self.print_warning("⚠️  Tarea no terminó en 60 segundos")
                    return False
            elif result.state == 'SUCCESS':
                self.print_success("✅ Tarea completada exitosamente")
                self.print_info(f"   Resultado: {result.result}")
                
                # Limpiar: eliminar tenant de prueba
                client = Client.objects.filter(schema_name=test_schema).first()
                if client:
                    self.print_info("Limpiando tenant de prueba...")
                    client.delete()
                    self.print_info("Tenant de prueba eliminado")
            else:
                self.print_warning(f"⚠️  Estado inesperado: {result.state}")
            
            self.print_success("PRUEBA 4: Cola real verificada")
            return True
            
        except Exception as e:
            self.print_error(f"Error en PRUEBA 4: {e}")
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return False

    def handle(self, *args, **options):
        """Ejecuta todas las pruebas secuencialmente."""
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔬 DIAGNÓSTICO FORENSE: Creación de Tenants"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write("")
        
        resultados = {}
        
        # Ejecutar pruebas secuencialmente
        resultados['prueba_1'] = self.prueba_1_configuracion()
        if not resultados['prueba_1']:
            self.print_error("\n❌ PRUEBA 1 FALLÓ: Deteniendo diagnóstico")
            return
        
        resultados['prueba_2'] = self.prueba_2_creacion_sincrona()
        if not resultados['prueba_2']:
            self.print_error("\n❌ PRUEBA 2 FALLÓ: Error en lógica de negocio (crear_tenant)")
            self.print_error("   El problema está en el código Python, no en la infraestructura")
            return
        
        resultados['prueba_3'] = self.prueba_3_celery_eager()
        if not resultados['prueba_3']:
            self.print_error("\n❌ PRUEBA 3 FALLÓ: Error en la tarea Celery (importación o sintaxis)")
            self.print_error("   El problema está en apps/public/tenants/tasks.py")
            return
        
        resultados['prueba_4'] = self.prueba_4_cola_real()
        if not resultados['prueba_4']:
            self.print_error("\n❌ PRUEBA 4 FALLÓ: Error en infraestructura (cola/worker)")
            self.print_error("   El problema está en la configuración de Celery o Docker")
            return
        
        # Resumen final
        self.print_header("RESUMEN FINAL")
        
        todas_pasaron = all(resultados.values())
        
        if todas_pasaron:
            self.print_success("✅ TODAS LAS PRUEBAS PASARON")
            self.print_info("El sistema está funcionando correctamente")
            self.print_info("Si aún tienes problemas, revisa:")
            self.print_info("  1. Logs del worker: docker-compose logs celery")
            self.print_info("  2. Estado de Redis: docker-compose ps redis")
            self.print_info("  3. Configuración de red entre contenedores")
        else:
            self.print_error("❌ ALGUNAS PRUEBAS FALLARON")
            self.print_info("Revisa los errores arriba para identificar el problema")
        
        self.stdout.write("")
        self.stdout.write("=" * 80)
