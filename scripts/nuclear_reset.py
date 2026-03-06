#!/usr/bin/env python3
"""
Script de "Nuclear Reset" para SINTEL - Reinicio Total del Proyecto

Este script automatiza el proceso completo de limpieza y arranque inicial,
asegurando que no queden conflictos de migraciones anteriores.

Uso:
    python scripts/nuclear_reset.py

Requisitos:
    - Docker y Docker Compose instalados
    - Python 3.8+
    - Acceso a la base de datos PostgreSQL

⚠️ ADVERTENCIA: Este script elimina:
    - Todas las carpetas __pycache__ y archivos .pyc
    - Todas las migraciones (excepto __init__.py)
    - Volúmenes de Docker
    - Datos de la base de datos
"""
import os
import sys
import shutil
import subprocess
import time
import platform
from pathlib import Path

# Colores para terminal (compatible con Windows y Unix)
class Colors:
    """Códigos de color ANSI para terminal."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# En Windows, habilitar colores ANSI si es posible
if platform.system() == 'Windows':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def print_step(message: str, step: int = None, total: int = None):
    """Imprime un paso del proceso con formato."""
    if step and total:
        prefix = f"[{step}/{total}]"
    else:
        prefix = "[*]"
    print(f"{Colors.OKCYAN}{prefix} {message}{Colors.ENDC}")


def print_success(message: str):
    """Imprime un mensaje de éxito."""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_error(message: str):
    """Imprime un mensaje de error."""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Imprime un mensaje de advertencia."""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")


def print_info(message: str):
    """Imprime un mensaje informativo."""
    print(f"{Colors.OKBLUE}ℹ️  {message}{Colors.ENDC}")


def get_project_root():
    """Obtiene la raíz del proyecto (directorio que contiene manage.py)."""
    current = Path(__file__).resolve().parent.parent
    if (current / 'manage.py').exists():
        return current
    raise FileNotFoundError("No se encontró manage.py. Asegúrate de ejecutar el script desde la raíz del proyecto.")


def clean_pycache(root_path: Path):
    """Elimina todas las carpetas __pycache__ y archivos .pyc."""
    print_step("Limpiando archivos Python compilados (__pycache__, .pyc)...")
    
    removed_dirs = 0
    removed_files = 0
    
    # Buscar y eliminar __pycache__
    for pycache_dir in root_path.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache_dir)
            removed_dirs += 1
        except Exception as e:
            print_warning(f"No se pudo eliminar {pycache_dir}: {e}")
    
    # Buscar y eliminar .pyc
    for pyc_file in root_path.rglob('*.pyc'):
        try:
            pyc_file.unlink()
            removed_files += 1
        except Exception as e:
            print_warning(f"No se pudo eliminar {pyc_file}: {e}")
    
    print_success(f"Eliminados {removed_dirs} directorios __pycache__ y {removed_files} archivos .pyc")


def clean_migrations(root_path: Path):
    """Elimina todos los archivos de migración excepto __init__.py."""
    print_step("Limpiando historial de migraciones (excepto __init__.py)...")
    
    removed_files = 0
    
    # Buscar todas las carpetas migrations/
    for migrations_dir in root_path.rglob('migrations'):
        if not migrations_dir.is_dir():
            continue
        
        # Buscar todos los .py excepto __init__.py
        for migration_file in migrations_dir.glob('*.py'):
            if migration_file.name == '__init__.py':
                continue
            
            try:
                migration_file.unlink()
                removed_files += 1
            except Exception as e:
                print_warning(f"No se pudo eliminar {migration_file}: {e}")
    
    print_success(f"Eliminados {removed_files} archivos de migración")


def run_command(cmd: list, check: bool = True, cwd: Path = None, shell: bool = False):
    """
    Ejecuta un comando del sistema.
    
    Args:
        cmd: Lista de argumentos del comando o string si shell=True
        check: Si True, lanza excepción si el comando falla
        cwd: Directorio de trabajo
        shell: Si True, ejecuta en shell (Windows)
    """
    if platform.system() == 'Windows' and not shell:
        # En Windows, algunos comandos necesitan shell=True
        shell = True
    
    try:
        result = subprocess.run(
            cmd,
            check=check,
            cwd=str(cwd) if cwd else None,
            shell=shell,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout, end='')
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Error ejecutando comando: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        raise


def clean_docker():
    """Limpia contenedores y volúmenes de Docker."""
    print_step("Limpiando contenedores y volúmenes de Docker...")
    
    # docker compose down -v
    print_info("Ejecutando: docker compose down -v")
    run_command(['docker', 'compose', 'down', '-v'], check=False)
    
    # Preguntar si desea limpiar sistema Docker
    print_warning("¿Deseas ejecutar 'docker system prune -f' para limpiar basura del sistema?")
    print_info("Esto eliminará imágenes, contenedores y volúmenes no utilizados.")
    respuesta = input(f"{Colors.WARNING}Continuar? (s/N): {Colors.ENDC}").strip().lower()
    
    if respuesta in ('s', 'si', 'sí', 'y', 'yes'):
        print_info("Ejecutando: docker system prune -f")
        run_command(['docker', 'system', 'prune', '-f'], check=False)
        print_success("Sistema Docker limpiado")
    else:
        print_info("Omitiendo limpieza del sistema Docker")


def build_and_start_docker():
    """Construye y arranca los contenedores Docker."""
    print_step("Construyendo y arrancando contenedores Docker...")
    
    print_info("Ejecutando: docker compose up -d --build")
    run_command(['docker', 'compose', 'up', '-d', '--build'])
    
    print_success("Contenedores construidos y arrancados")


def wait_for_database(max_attempts: int = 30, delay: int = 2):
    """Espera a que el contenedor de base de datos esté saludable."""
    print_step("Esperando a que la base de datos esté lista...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Verificar healthcheck del contenedor db
            result = run_command(
                ['docker', 'compose', 'ps', 'db'],
                check=False,
                shell=platform.system() == 'Windows'
            )
            
            if 'healthy' in result.stdout.lower() or '(healthy)' in result.stdout:
                print_success("Base de datos lista")
                return True
            
            print_info(f"Intento {attempt}/{max_attempts}: Base de datos aún no está lista, esperando {delay}s...")
            time.sleep(delay)
        except Exception as e:
            print_warning(f"Error verificando estado de la BD: {e}")
            time.sleep(delay)
    
    print_error("La base de datos no está lista después de varios intentos")
    print_warning("Continuando de todas formas...")
    return False


def run_django_command(command: list, description: str):
    """Ejecuta un comando de Django dentro del contenedor web."""
    print_step(description)
    
    cmd = ['docker', 'compose', 'exec', '-T', 'web', 'python', 'manage.py'] + command
    
    try:
        result = run_command(cmd, check=True, shell=platform.system() == 'Windows')
        print_success(f"{description} completado")
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Error ejecutando: {description}")
        raise


def create_superuser():
    """Crea un superusuario por defecto para desarrollo."""
    print_step("Creando superusuario por defecto (admin/admin)...")
    
    # Usar variables de entorno para crear superusuario sin interacción
    env = os.environ.copy()
    env['DJANGO_SUPERUSER_USERNAME'] = 'admin'
    env['DJANGO_SUPERUSER_EMAIL'] = 'admin@sintel.com'
    env['DJANGO_SUPERUSER_PASSWORD'] = 'admin'
    
    cmd = ['docker', 'compose', 'exec', '-T', 'web', 'python', 'manage.py', 'createsuperuser', '--noinput']
    
    try:
        # Crear superusuario usando variables de entorno
        result = subprocess.run(
            cmd,
            env=env,
            check=False,  # No fallar si el usuario ya existe
            shell=platform.system() == 'Windows',
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("Superusuario creado: admin/admin")
        else:
            # Si falla, puede ser que el usuario ya existe
            if 'already exists' in result.stderr.lower() or 'ya existe' in result.stderr.lower():
                print_warning("El superusuario 'admin' ya existe, omitiendo creación")
            else:
                print_warning(f"No se pudo crear superusuario: {result.stderr}")
    except Exception as e:
        print_warning(f"Error creando superusuario: {e}")


def main():
    """Función principal del script."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}🚀 NUCLEAR RESET - SINTEL Multi-tenant SaaS{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")
    
    print_warning("Este script realizará una limpieza completa del proyecto.")
    print_warning("Se eliminarán migraciones, archivos compilados y datos de Docker.\n")
    
    respuesta = input(f"{Colors.WARNING}¿Estás seguro de continuar? (s/N): {Colors.ENDC}").strip().lower()
    if respuesta not in ('s', 'si', 'sí', 'y', 'yes'):
        print_info("Operación cancelada.")
        sys.exit(0)
    
    try:
        # Obtener raíz del proyecto
        root_path = get_project_root()
        print_success(f"Proyecto encontrado en: {root_path}\n")
        
        # FASE 1: Limpieza del Sistema de Archivos
        print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}FASE 1: Limpieza del Sistema de Archivos{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")
        
        clean_pycache(root_path)
        clean_migrations(root_path)
        
        # FASE 2: Limpieza de Docker
        print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}FASE 2: Limpieza de Docker{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")
        
        clean_docker()
        
        # FASE 3: Construcción y Arranque
        print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}FASE 3: Construcción y Arranque de Docker{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")
        
        build_and_start_docker()
        
        # FASE 4: Esperar Base de Datos
        print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}FASE 4: Esperando Base de Datos{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")
        
        wait_for_database()
        
        # FASE 5: Inicialización de Django
        print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}FASE 5: Inicialización de Django{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")
        
        # 1. makemigrations accounts
        run_django_command(
            ['makemigrations', 'accounts'],
            "Creando migraciones para accounts"
        )
        
        # 2. makemigrations (resto de apps)
        run_django_command(
            ['makemigrations'],
            "Creando migraciones para el resto de apps"
        )
        
        # 3. migrate_schemas --shared
        run_django_command(
            ['migrate_schemas', '--shared'],
            "Aplicando migraciones del esquema public (shared)"
        )
        
        # 4. setup_public_tenant
        run_django_command(
            ['setup_public_tenant'],
            "Configurando tenant público"
        )
        
        # 5. poblar_catalogo_dian
        run_django_command(
            ['poblar_catalogo_dian'],
            "Poblando catálogo DIAN"
        )
        
        # 6. createsuperuser
        create_superuser()
        
        # Resumen final
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}✅ NUCLEAR RESET COMPLETADO EXITOSAMENTE{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}{'='*70}{Colors.ENDC}\n")
        
        print_success("El proyecto ha sido reiniciado completamente.")
        print_info("Puedes acceder a:")
        print_info("  - Consola de administración: http://localhost:8000/console/")
        print_info("  - Admin de Django: http://localhost:8000/admin/")
        print_info("  - Credenciales: admin/admin")
        print()
        
    except KeyboardInterrupt:
        print_error("\nOperación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nError durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
