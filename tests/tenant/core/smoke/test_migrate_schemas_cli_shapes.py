"""
Pruebas para verificar que el helper reconoce correctamente los modos.

Verifica que:
- TENANTS=all → construye "--tenant"
- TENANTS=<schema> → construye "--schema=<schema>"
"""
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path

try:
    import playwright  # noqa: F401
    import cryptography  # noqa: F401
except Exception:
    pytest.skip("Skipping heavy smoke test: missing playwright/cryptography", allow_module_level=True)

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


class TestMigrateSchemasCLIShapes:
    """Pruebas para verificar las formas CLI del helper."""
    
    def test_helper_recognizes_all_mode(self):
        """Verifica que TENANTS=all construye el comando con --tenant (sin argumento)."""
        with patch('scripts.safe_migrate_tenants.call_command') as mock_call:
            # Simular TENANTS=all
            original_env = os.environ.get('TENANTS')
            os.environ['TENANTS'] = 'all'
            
            try:
                # Re-importar para que lea el nuevo env
                import importlib
                if 'scripts.safe_migrate_tenants' in sys.modules:
                    importlib.reload(sys.modules['scripts.safe_migrate_tenants'])
                else:
                    import scripts.safe_migrate_tenants
                
                # Ejecutar
                from scripts.safe_migrate_tenants import main
                main()
                
                # Verificar la llamada
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                
                # Verificar estructura del comando
                assert call_args[0][0] == 'migrate_schemas'
                args = list(call_args[0][1:])
                
                # Debe tener --tenant pero NO 'all'
                assert '--tenant' in args
                assert 'all' not in args
                assert '--fake-initial' in args
                
            finally:
                # Restaurar env original
                if original_env:
                    os.environ['TENANTS'] = original_env
                elif 'TENANTS' in os.environ:
                    del os.environ['TENANTS']
    
    def test_helper_recognizes_specific_schema(self):
        """Verifica que TENANTS=<schema> construye el comando con --schema=<schema>."""
        with patch('scripts.safe_migrate_tenants.call_command') as mock_call:
            # Simular TENANTS=mi_empresa
            original_env = os.environ.get('TENANTS')
            os.environ['TENANTS'] = 'mi_empresa'
            
            try:
                # Re-importar para que lea el nuevo env
                import importlib
                if 'scripts.safe_migrate_tenants' in sys.modules:
                    importlib.reload(sys.modules['scripts.safe_migrate_tenants'])
                else:
                    import scripts.safe_migrate_tenants
                
                # Ejecutar
                from scripts.safe_migrate_tenants import main
                main()
                
                # Verificar la llamada
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                
                # Verificar estructura del comando
                assert call_args[0][0] == 'migrate_schemas'
                args = list(call_args[0][1:])
                
                # Debe tener --schema y mi_empresa pero NO --tenant
                assert '--schema' in args
                assert 'mi_empresa' in args
                assert '--tenant' not in args
                assert '--fake-initial' in args
                
            finally:
                # Restaurar env original
                if original_env:
                    os.environ['TENANTS'] = original_env
                elif 'TENANTS' in os.environ:
                    del os.environ['TENANTS']
