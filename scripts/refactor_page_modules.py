#!/usr/bin/env python3
"""
Script para aplicar el patrón de refactorización a módulos *.page.js
Reemplaza getCookie, fetch, document.getElementById, etc. por helpers centralizados
"""

import re
import os
from pathlib import Path

# Módulos a refactorizar
MODULES = [
    'proveedores', 'clientes', 'cuentas', 'asientos',
    'catalogo', 'activos', 'movimientos'
]

BASE_DIR = Path('apps/tenant/core/static/core/js')

def refactor_module(module_name):
    """Aplica el patrón de refactorización a un módulo"""
    file_path = BASE_DIR / module_name / f'{module_name}.page.js'
    
    if not file_path.exists():
        print(f"⚠️  {file_path} no existe, omitiendo...")
        return False
    
    print(f"📝 Refactorizando {module_name}.page.js...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Reemplazar IIFE inicial
    if '(function ()' in content and 'const MOD =' in content:
        # Buscar el patrón y reemplazar
        pattern = r'\(function \(\) \{\s*\'use strict\';\s*const MOD = \'([^\']+)\';\s*const API_INDEX = `([^`]+)`;\s*const TABLE_ID = \'([^\']+)\';\s*// URL de colección[^\n]+\s*let ([A-Z_]+)_COLLECTION_URL = null;\s*// Helper para obtener CSRF token\s*function getCookie\(name\) \{[^}]+\}\s*const CSRF = getCookie\(\'csrftoken\'\);'
        
        replacement = f'''(function (w, d) {{
  'use strict';

  const NS = '[{module_name}.page]';
  const MOD = '{module_name}';
  const API_INDEX = `${{w.API_HELPERS?.API_BASE || '/api/v1'}}{module_name}/`;
  const TABLE_ID = '#table-{module_name}';
  
  // Estado del módulo
  let state = {{
    initialized: false,
    listenersAttached: false,
    table: null,
    urls: {{ collection: null }}
  }};

  // Helpers de logging
  function log(...args) {{
    if (w.__DEBUG__) console.debug(NS, ...args);
  }}
  function error(...args) {{
    console.error(NS, ...args);
  }}
  function warn(...args) {{
    console.warn(NS, ...args);
  }}'''
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # 2. Reemplazar referencias a COLLECTION_URL
    collection_var = f'{module_name.upper()}_COLLECTION_URL'
    content = content.replace(f'{collection_var}', 'state.urls.collection')
    content = content.replace(f'let {collection_var}', '// state.urls.collection')
    
    # 3. Reemplazar getCookie y CSRF
    content = re.sub(r'const CSRF = getCookie\(\'csrftoken\'\);', '', content)
    content = re.sub(r'function getCookie\(name\) \{[^}]+\}', '', content)
    
    # 4. Reemplazar fetch por safeFetchJson (patrones comunes)
    # discoverCollectionUrl
    content = re.sub(
        r'const idxRes = await fetch\(API_INDEX, \{[^}]+\}\);',
        'const idxPayload = await w.API_HELPERS.safeFetchJson(API_INDEX, { method: \'GET\' });',
        content
    )
    
    # 5. Reemplazar document.getElementById por d.getElementById
    content = content.replace('document.getElementById', 'd.getElementById')
    content = content.replace('document.querySelector', 'd.querySelector')
    content = content.replace('document.addEventListener', 'd.addEventListener')
    
    # 6. Reemplazar dtInstance por state.table
    content = content.replace('dtInstance', 'state.table')
    content = content.replace('let state.table = null;', '// state.table en state object')
    
    # 7. Reemplazar console.info/warn/error por log/warn/error
    content = re.sub(r'console\.info\(`\[` \+ MOD \+ `\.page\]', 'log(', content)
    content = re.sub(r'console\.warn\(`\[` \+ MOD \+ `\.page\]', 'warn(', content)
    content = re.sub(r'console\.error\(`\[` \+ MOD \+ `\.page\]', 'error(', content)
    
    # 8. Actualizar función de detalle URL
    detail_url_pattern = rf'function {module_name}DetailUrl\(id\) \{{[^}}]+\}}'
    new_detail_url = f'''  function {module_name}DetailUrl(id) {{
    if (!state.urls.collection) {{
      warn('COLLECTION_URL no descubierta, usando fallback');
      return w.API_HELPERS.buildDetailUrl(API_INDEX, id);
    }}
    return w.API_HELPERS.buildDetailUrl(state.urls.collection, id);
  }}'''
    content = re.sub(detail_url_pattern, new_detail_url, content, flags=re.DOTALL)
    
    # 9. Actualizar initDataTable para usar helpers
    # Esto requiere más contexto, se hará manualmente
    
    # 10. Actualizar initModule para usar patrón protegido
    init_pattern = rf'async function init{module_name.capitalize()}Module\(\) \{{[^}}]+console\.info\(`\[` \+ MOD \+ `\.page\] Inicializando[^}}]+\}}'
    # Esto se hará manualmente por la complejidad
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {module_name}.page.js refactorizado")
        return True
    else:
        print(f"⚠️  {module_name}.page.js no tuvo cambios")
        return False

if __name__ == '__main__':
    print("🚀 Iniciando refactorización de módulos...\n")
    for module in MODULES:
        try:
            refactor_module(module)
        except Exception as e:
            print(f"❌ Error en {module}: {e}")
    print("\n✅ Refactorización completada")
