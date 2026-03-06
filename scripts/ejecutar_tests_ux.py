#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar UX Smoke Tests
Verifica el servidor y abre el navegador automáticamente
"""

import sys
import webbrowser
import urllib.request
import urllib.error

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_server(port=8000):
    """Verifica si el servidor Django está corriendo"""
    try:
        urllib.request.urlopen(f'http://localhost:{port}/health', timeout=2)
        return True
    except:
        return False

def main():
    print('=' * 60)
    print('Ejecutor de UX Smoke Tests')
    print('=' * 60)
    print()
    
    port = 8000
    url = f'http://localhost:{port}/workspace/?uxsmoke=1'
    
    # Verificar servidor
    print('Verificando servidor Django...')
    if check_server(port):
        print(f'[OK] Servidor Django corriendo en puerto {port}')
    else:
        print(f'[WARN] Servidor Django NO esta corriendo en puerto {port}')
        print()
        print('Inicia el servidor con:')
        print('  python manage.py runserver')
        print()
        respuesta = input('¿Continuar de todas formas? (s/n): ').strip().lower()
        if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
            print('Cancelado')
            sys.exit(0)
    
    print()
    print(f'Abriendo navegador en: {url}')
    print()
    
    try:
        webbrowser.open(url)
        print('[OK] Navegador abierto')
        print()
        print('=' * 60)
        print('INSTRUCCIONES PARA EJECUTAR LOS TESTS:')
        print('=' * 60)
        print()
        print('1. En el navegador, busca el panel de test en la parte superior')
        print('   (Panel oscuro con botones de colores)')
        print()
        print('2. Haz click en "Ejecutar Todo" para ejecutar todas las suites')
        print('   O haz click en un boton individual para una suite especifica')
        print()
        print('3. Observa el log en tiempo real:')
        print('   - [OK] Operaciones exitosas')
        print('   - [WARN] Advertencias (elementos no encontrados)')
        print('   - [ERROR] Errores (fallos en la ejecucion)')
        print()
        print('4. Los tests simulan un usuario real:')
        print('   - Clicks en botones reales')
        print('   - Apertura de modales reales')
        print('   - Llenado de formularios')
        print('   - Navegacion entre tabs')
        print()
        print('=' * 60)
        print()
    except Exception as e:
        print(f'[ERROR] No se pudo abrir el navegador: {e}')
        print()
        print(f'Abre manualmente el navegador en: {url}')
        sys.exit(1)

if __name__ == '__main__':
    main()
