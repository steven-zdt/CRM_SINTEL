"""
Pruebas de humo para verificar la invocación correcta de migrate_schemas.

Verifica que cuando TENANTS=all, el código construye el comando sin el argumento
extra 'all' después de --tenant.
"""
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


@pytest.mark.django_db
class TestMigrateCommandInvocation:
    """Pruebas para verificar la invocación correcta de migrate_schemas."""
    
    def test_safe_migrate_tenants_all_mode(self):
        """Verifica que TENANTS=all construye el comando correctamente."""
        with patch('scripts.safe_migrate_tenants.call_command') as mock_call:
            # Simular TENANTS=all
            with patch.dict(os.environ, {'TENANTS': 'all'}):
                # Re-importar el módulo para que lea el nuevo env
                import importlib
                import scripts.safe_migrate_tenants
                importlib.reload(scripts.safe_migrate_tenants)
                
                # Ejecutar la función
                result = scripts.safe_migrate_tenants.main()
                
                # Verificar que se llamó con los argumentos correctos
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                
                # Verificar que el comando es 'migrate_schemas'
                assert call_args[0][0] == 'migrate_schemas'
                
                # Verificar que los argumentos son correctos (sin 'all')
                # call_args[1] contiene los kwargs, pero los args posicionales están en call_args[0]
                # Necesitamos verificar que --tenant está presente y que NO hay 'all'
                args_list = list(call_args[0][1:])  # Todos los args después del comando
                
                # Debe contener '--tenant' pero NO 'all'
                assert '--tenant' in args_list
                assert 'all' not in args_list
                assert '--fake-initial' in args_list
    
    def test_safe_migrate_tenants_specific_schema(self):
        """Verifica que TENANTS=<schema> construye el comando correctamente."""
        with patch('scripts.safe_migrate_tenants.call_command') as mock_call:
            # Simular TENANTS=mi_empresa
            with patch.dict(os.environ, {'TENANTS': 'mi_empresa'}):
                # Re-importar el módulo para que lea el nuevo env
                import importlib
                import scripts.safe_migrate_tenants
                importlib.reload(scripts.safe_migrate_tenants)
                
                # Ejecutar la función
                result = scripts.safe_migrate_tenants.main()
                
                # Verificar que se llamó con los argumentos correctos
                mock_call.assert_called_once()
                call_args = mock_call.call_args
                
                # Verificar que el comando es 'migrate_schemas'
                assert call_args[0][0] == 'migrate_schemas'
                
                # Verificar que los argumentos son correctos
                args_list = list(call_args[0][1:])
                
                # Debe contener '--schema' y 'mi_empresa' pero NO '--tenant'
                assert '--schema' in args_list
                assert 'mi_empresa' in args_list
                assert '--tenant' not in args_list
                assert '--fake-initial' in args_list
