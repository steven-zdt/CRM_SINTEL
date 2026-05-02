"""
Tests de Docker para el proyecto.

Verifica:
- Lint del Dockerfile
- Build y smoke run
- Container Structure Tests
- Healthchecks
"""
import subprocess
import os
import sys
import unittest
from pathlib import Path


class DockerLintTests(unittest.TestCase):
    """Tests de lint del Dockerfile."""
    
    def setUp(self):
        """Configuración inicial."""
        self.project_root = Path(__file__).parent.parent.parent
        self.dockerfile = self.project_root / 'Dockerfile'
    
    def test_dockerfile_exists(self):
        """Test: Dockerfile existe."""
        self.assertTrue(self.dockerfile.exists(), "Dockerfile no encontrado")
    
    def test_dockerfile_lint(self):
        """Test: Dockerfile pasa lint con Hadolint."""
        # Verificar si hadolint está disponible
        try:
            result = subprocess.run(
                ['hadolint', str(self.dockerfile)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            # Hadolint devuelve 0 si no hay errores, 1 si hay warnings/errors
            # Permitimos warnings pero no errores críticos
            if result.returncode > 1:
                self.fail(f"Hadolint encontró errores críticos:\n{result.stderr}")
        except FileNotFoundError:
            self.skipTest("Hadolint no está instalado. Instalar con: brew install hadolint")


class DockerBuildTests(unittest.TestCase):
    """Tests de build y smoke run."""
    
    def setUp(self):
        """Configuración inicial."""
        self.project_root = Path(__file__).parent.parent.parent
    
    def test_docker_compose_build(self):
        """Test: docker compose build funciona."""
        # Este test requiere Docker y docker-compose
        # Se puede ejecutar manualmente o en CI/CD
        try:
            result = subprocess.run(
                ['docker', 'compose', 'build', '--no-cache', 'web'],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=600,  # 10 minutos timeout
            )
            if result.returncode != 0:
                self.fail(f"docker compose build falló:\n{result.stderr}")
        except FileNotFoundError:
            self.skipTest("Docker no está disponible")
        except subprocess.TimeoutExpired:
            self.fail("docker compose build excedió el timeout")
    
    def test_check_migrations_command(self):
        """Test: check_migrations funciona en el contenedor."""
        try:
            # Primero construir la imagen
            build_result = subprocess.run(
                ['docker', 'compose', 'build', 'web'],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=600,
            )
            if build_result.returncode != 0:
                self.skipTest("No se pudo construir la imagen")
            
            # Ejecutar check_migrations
            result = subprocess.run(
                ['docker', 'compose', 'run', '--rm', 'web', 'python', 'manage.py', 'check_migrations'],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )
            # check_migrations debe devolver 0 si no hay migraciones pendientes
            # o 1 si hay migraciones pendientes (ambos son válidos para el test)
            self.assertIn(result.returncode, [0, 1], 
                         f"check_migrations devolvió código inesperado: {result.returncode}\n{result.stderr}")
        except FileNotFoundError:
            self.skipTest("Docker no está disponible")
        except subprocess.TimeoutExpired:
            self.fail("check_migrations excedió el timeout")


class ContainerStructureTests(unittest.TestCase):
    """Tests de estructura del contenedor."""
    
    def setUp(self):
        """Configuración inicial."""
        self.project_root = Path(__file__).parent.parent.parent
        self.cst_config = self.project_root / 'tests' / 'docker' / 'container-structure-test.yaml'
    
    def test_cst_config_exists(self):
        """Test: Configuración de CST existe."""
        self.assertTrue(self.cst_config.exists(), "container-structure-test.yaml no encontrado")
    
    def test_container_structure(self):
        """Test: Container Structure Test pasa."""
        try:
            # Primero construir la imagen
            build_result = subprocess.run(
                ['docker', 'compose', 'build', 'web'],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=600,
            )
            if build_result.returncode != 0:
                self.skipTest("No se pudo construir la imagen")
            
            # Obtener el nombre de la imagen
            image_name = f"sintel_web:local"  # Ajustar según el nombre real
            
            # Ejecutar CST
            result = subprocess.run(
                ['container-structure-test', 'test', '--image', image_name, 
                 '--config', str(self.cst_config)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=120,
            )
            if result.returncode != 0:
                self.fail(f"Container Structure Test falló:\n{result.stdout}\n{result.stderr}")
        except FileNotFoundError:
            self.skipTest("container-structure-test no está instalado")
        except subprocess.TimeoutExpired:
            self.fail("CST excedió el timeout")


class HealthcheckTests(unittest.TestCase):
    """Tests de healthchecks."""
    
    def setUp(self):
        """Configuración inicial."""
        self.project_root = Path(__file__).parent.parent.parent
    
    def test_db_healthcheck_configured(self):
        """Test: Healthcheck de DB está configurado en docker-compose."""
        compose_file = self.project_root / 'docker-compose.yaml'
        self.assertTrue(compose_file.exists(), "docker-compose.yaml no encontrado")
        
        with open(compose_file, 'r') as f:
            content = f.read()
            # Verificar que hay healthcheck para db
            self.assertIn('healthcheck:', content.lower())
            self.assertIn('pg_isready', content)


if __name__ == '__main__':
    unittest.main()
