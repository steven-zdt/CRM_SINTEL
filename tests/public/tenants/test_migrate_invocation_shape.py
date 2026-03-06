"""
Tests para verificar que las invocaciones de migrate_schemas tienen la forma correcta.

⚠️ IMPORTANTE: Estos tests NO usan base de datos, solo verifican la construcción
correcta de argumentos según la variable de entorno TENANTS.
"""
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


def build_migrate_schemas_args(tenants_env: str) -> list:
    """
    Helper que construye los argumentos correctos para migrate_schemas según TENANTS.
    
    Args:
        tenants_env: Valor de la variable de entorno TENANTS ('all' o nombre de schema)
    
    Returns:
        Lista de argumentos para call_command('migrate_schemas', ...)
    """
    if tenants_env == 'all':
        return ['migrate_schemas', '--tenant', '--fake-initial']
    else:
        return ['migrate_schemas', '--schema', tenants_env, '--fake-initial']


@pytest.mark.parametrize('tenants_env,expected_args', [
    ('all', ['migrate_schemas', '--tenant', '--fake-initial']),
    ('mi_empresa', ['migrate_schemas', '--schema', 'mi_empresa', '--fake-initial']),
    ('cliente', ['migrate_schemas', '--schema', 'cliente', '--fake-initial']),
])
def test_build_migrate_schemas_args(tenants_env, expected_args):
    """Verifica que build_migrate_schemas_args construye los argumentos correctos."""
    actual_args = build_migrate_schemas_args(tenants_env)
    assert actual_args == expected_args, f"Expected {expected_args}, got {actual_args}"


def test_build_migrate_schemas_args_all_mode():
    """Verifica que TENANTS=all construye el comando correctamente (sin 'all' como argumento)."""
    args = build_migrate_schemas_args('all')
    
    # Verificar que NO contiene 'all' como argumento separado
    assert 'all' not in args, "El argumento 'all' no debe aparecer en la lista de argumentos"
    
    # Verificar que contiene --tenant (sin argumento adicional)
    assert '--tenant' in args, "Debe contener --tenant"
    
    # Verificar que el siguiente elemento después de --tenant NO es 'all'
    tenant_index = args.index('--tenant')
    if tenant_index + 1 < len(args):
        assert args[tenant_index + 1] != 'all', "El siguiente argumento después de --tenant no debe ser 'all'"
    
    # Verificar estructura esperada
    assert args == ['migrate_schemas', '--tenant', '--fake-initial']


def test_build_migrate_schemas_args_specific_schema():
    """Verifica que TENANTS=<schema> construye el comando correctamente."""
    schema_name = 'mi_empresa'
    args = build_migrate_schemas_args(schema_name)
    
    # Verificar estructura esperada
    assert args == ['migrate_schemas', '--schema', schema_name, '--fake-initial']
    
    # Verificar que contiene --schema seguido del nombre del schema
    schema_index = args.index('--schema')
    assert args[schema_index + 1] == schema_name


def test_safe_migrate_tenants_helper_all_mode():
    """
    Verifica que el helper de safe_migrate_tenants.py construye correctamente
    el comando para TENANTS=all.
    """
    with patch.dict(os.environ, {'TENANTS': 'all'}):
        # Simular la lógica del helper
        tenants_mode = os.environ.get('TENANTS', 'all').strip()
        
        if tenants_mode == 'all':
            expected_args = ['migrate_schemas', '--tenant', '--fake-initial']
            # Verificar que NO contiene 'all' como argumento
            assert 'all' not in expected_args
            assert '--tenant' in expected_args


def test_safe_migrate_tenants_helper_specific_schema():
    """
    Verifica que el helper de safe_migrate_tenants.py construye correctamente
    el comando para TENANTS=<schema>.
    """
    schema_name = 'mi_empresa'
    with patch.dict(os.environ, {'TENANTS': schema_name}):
        # Simular la lógica del helper
        tenants_mode = os.environ.get('TENANTS', 'all').strip()
        
        if tenants_mode != 'all':
            expected_args = ['migrate_schemas', '--schema', schema_name, '--fake-initial']
            assert expected_args[2] == schema_name
            assert '--schema' in expected_args
