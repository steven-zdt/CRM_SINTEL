#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar UX Smoke Tests
Abre el navegador en la URL correcta con el parámetro uxsmoke=1
"""

import sys
import webbrowser
import time

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    print('=' * 60)
    print('UX Smoke Runner - Ejecutor de Tests')
    print('=' * 60)
    print()
    
    # URL del workspace con parámetro uxsmoke=1
    url = 'http://localhost:8000/workspace/?uxsmoke=1'
    
    print(f'URL de test: {url}')
    print()
    print('Asegurate de que:')
    print('  1. El servidor Django este corriendo (python manage.py runserver)')
    print('  2. Estes autenticado en el sistema')
    print('  3. El workspace este accesible')
    print()
    
    respuesta = input('¿Abrir navegador ahora? (s/n): ').strip().lower()
    
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        print()
        print('Abriendo navegador...')
        try:
            webbrowser.open(url)
            print('[OK] Navegador abierto')
            print()
            print('Instrucciones:')
            print('  1. El panel de test aparecera en la parte superior')
            print('  2. Haz click en "Ejecutar Todo" para ejecutar todas las suites')
            print('  3. O haz click en un boton individual para una suite especifica')
            print('  4. Observa el log en tiempo real')
            print()
        except Exception as e:
            print(f'[ERROR] No se pudo abrir el navegador: {e}')
            print()
            print(f'Abre manualmente: {url}')
            sys.exit(1)
    else:
        print()
        print(f'Abre manualmente el navegador en: {url}')
        sys.exit(0)

if __name__ == '__main__':
    main()
