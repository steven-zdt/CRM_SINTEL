"""
Comando de management para garantizar que el tenant público tenga el dominio correcto.

⚠️ POLÍTICA ESTRICTA DE SUBDOMINIOS:
- El tenant PÚBLICO siempre debe responder en {TENANT_DOMAIN_BASE}
- Ejemplo: Si TENANT_DOMAIN_BASE='sintel.com', el tenant público debe tener dominio 'sintel.com'
- Si el tenant público tiene otro dominio (ej: 'localhost'), se actualiza automáticamente

Este comando:
1. Busca el tenant con schema_name='public'
2. Verifica que su dominio principal sea exactamente settings.TENANT_DOMAIN_BASE
3. Si no coincide, actualiza el dominio o lo crea si no existe
4. Marca el dominio correcto como is_primary=True
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = 'Garantiza que el tenant público tenga el dominio correcto según TENANT_DOMAIN_BASE'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización incluso si el dominio ya existe',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('🔍 Verificando dominio del tenant público...'))
        self.stdout.write(f'   TENANT_DOMAIN_BASE: {settings.TENANT_DOMAIN_BASE}')
        
        try:
            # 1. Obtener el tenant público
            try:
                tenant = Client.objects.get(schema_name='public')
                self.stdout.write(f'✅ Tenant público encontrado: {tenant.nombre}')
            except Client.DoesNotExist:
                self.stdout.write(self.style.ERROR('❌ El tenant público no existe. Ejecuta primero: python manage.py setup_public_tenant'))
                return
            
            # 2. Verificar dominio esperado
            dominio_esperado = settings.TENANT_DOMAIN_BASE
            self.stdout.write(f'   Dominio esperado: {dominio_esperado}')
            
            # 3. Buscar dominio existente del tenant público
            dominios_existentes = Domain.objects.filter(tenant=tenant)
            dominio_principal = dominios_existentes.filter(is_primary=True).first()
            
            if dominio_principal:
                self.stdout.write(f'   Dominio principal actual: {dominio_principal.domain}')
            
            # 4. Verificar si el dominio esperado ya existe
            dominio_esperado_obj = Domain.objects.filter(domain=dominio_esperado).first()
            
            if dominio_esperado_obj:
                # El dominio esperado existe
                if dominio_esperado_obj.tenant == tenant:
                    # Ya está asignado al tenant público
                    if dominio_esperado_obj.is_primary:
                        self.stdout.write(self.style.SUCCESS(f'✅ El dominio {dominio_esperado} ya está configurado correctamente como dominio principal'))
                    else:
                        # Actualizar para que sea principal
                        dominio_esperado_obj.is_primary = True
                        dominio_esperado_obj.save()
                        # Desmarcar otros dominios como no principales
                        Domain.objects.filter(tenant=tenant, is_primary=True).exclude(pk=dominio_esperado_obj.pk).update(is_primary=False)
                        self.stdout.write(self.style.SUCCESS(f'✅ Dominio {dominio_esperado} actualizado como dominio principal'))
                else:
                    # El dominio está asignado a otro tenant
                    if force:
                        # Forzar reasignación
                        old_tenant = dominio_esperado_obj.tenant
                        dominio_esperado_obj.tenant = tenant
                        dominio_esperado_obj.is_primary = True
                        dominio_esperado_obj.save()
                        # Desmarcar otros dominios como no principales
                        Domain.objects.filter(tenant=tenant, is_primary=True).exclude(pk=dominio_esperado_obj.pk).update(is_primary=False)
                        self.stdout.write(self.style.WARNING(f'⚠️  Dominio {dominio_esperado} reasignado desde {old_tenant.nombre} al tenant público'))
                    else:
                        self.stdout.write(self.style.ERROR(
                            f'❌ El dominio {dominio_esperado} está asignado a otro tenant: {dominio_esperado_obj.tenant.nombre}. '
                            f'Usa --force para reasignarlo.'
                        ))
                        return
            else:
                # El dominio esperado no existe, crearlo
                dominio_esperado_obj = Domain.objects.create(
                    domain=dominio_esperado,
                    tenant=tenant,
                    is_primary=True
                )
                # Desmarcar otros dominios como no principales
                Domain.objects.filter(tenant=tenant, is_primary=True).exclude(pk=dominio_esperado_obj.pk).update(is_primary=False)
                self.stdout.write(self.style.SUCCESS(f'✅ Dominio {dominio_esperado} creado como dominio principal'))
            
            # 5. Verificar que el dominio principal sea el esperado
            dominio_principal_final = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            if dominio_principal_final and dominio_principal_final.domain == dominio_esperado:
                self.stdout.write(self.style.SUCCESS(f'\n🎉 Configuración correcta:'))
                self.stdout.write(f'   - Tenant: {tenant.nombre} (schema: {tenant.schema_name})')
                self.stdout.write(f'   - Dominio principal: {dominio_principal_final.domain}')
                
                # Mostrar todos los dominios del tenant público
                todos_dominios = Domain.objects.filter(tenant=tenant)
                if todos_dominios.count() > 1:
                    self.stdout.write(f'\n📋 Todos los dominios del tenant público:')
                    for d in todos_dominios:
                        primary_mark = ' (PRIMARY)' if d.is_primary else ''
                        self.stdout.write(f'   - {d.domain}{primary_mark}')
            else:
                self.stdout.write(self.style.ERROR(
                    f'❌ Error: El dominio principal no coincide con el esperado. '
                    f'Esperado: {dominio_esperado}, Actual: {dominio_principal_final.domain if dominio_principal_final else "None"}'
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al verificar dominio del tenant público: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return