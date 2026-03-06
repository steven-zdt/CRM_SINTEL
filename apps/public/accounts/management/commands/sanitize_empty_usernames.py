"""
Comando de management para sanear usuarios con username='' (cadena vacía).

Este comando corrige usuarios existentes que tienen username='' (cadena vacía),
generando un username único a partir del email para evitar violaciones de unicidad.

Uso:
    python manage.py sanitize_empty_usernames
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


def _generate_unique_username(base: str) -> str:
    """
    Genera un username único a partir de una base.
    Evita colisiones añadiendo sufijos -1, -2, ...
    """
    base = slugify(base or "user")
    if not base:
        base = "user"
    candidate = base[:150]  # tamaño seguro (max_length de username en AbstractUser)
    if not User.objects.filter(username=candidate).exists():
        return candidate
    i = 1
    while True:
        cand = f"{base}-{i}"[:150]
        if not User.objects.filter(username=cand).exists():
            return cand
        i += 1


class Command(BaseCommand):
    help = 'Sanear usuarios con username=\'\' (cadena vacía) generando username único desde email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué usuarios se corregirían sin hacer cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Buscar usuarios con username='' o None
        users_to_fix = User.objects.filter(username__in=['', None]) | User.objects.filter(username='')
        
        count = users_to_fix.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay usuarios con username vacío. Todo está correcto.'))
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'⚠️  Encontrados {count} usuario(s) con username vacío.'
            )
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY-RUN: No se realizarán cambios.'))
        
        fixed_count = 0
        errors = []
        
        with transaction.atomic():
            for user in users_to_fix:
                email = user.email or ""
                local = email.split("@")[0] if email else "user"
                
                if not local or local.strip() == "":
                    local = "user"
                
                new_username = _generate_unique_username(local)
                
                if dry_run:
                    self.stdout.write(
                        f'  - Usuario ID {user.id} ({email}): username=\'{user.username}\' → \'{new_username}\''
                    )
                else:
                    try:
                        user.username = new_username
                        user.save(update_fields=["username"])
                        fixed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ Usuario ID {user.id} ({email}): username corregido a \'{new_username}\''
                            )
                        )
                    except Exception as e:
                        error_msg = f'  ❌ Error corrigiendo usuario ID {user.id} ({email}): {str(e)}'
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
        
        if not dry_run:
            if fixed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ {fixed_count} usuario(s) corregido(s) exitosamente.'
                    )
                )
            
            if errors:
                self.stdout.write(
                    self.style.ERROR(
                        f'\n❌ {len(errors)} error(es) al corregir usuarios:'
                    )
                )
                for error in errors:
                    self.stdout.write(self.style.ERROR(f'  {error}'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 DRY-RUN: Se corregirían {count} usuario(s). Ejecuta sin --dry-run para aplicar cambios.'
                )
            )
