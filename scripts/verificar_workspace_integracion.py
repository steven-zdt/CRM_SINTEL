#!/usr/bin/env python
"""
Script de verificación de integración del workspace.

[WARNING] v2.37: Verifica que todos los módulos estén correctamente integrados
sin requerir base de datos.
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.template.loader import get_template
from django.template import Context


def verificar_archivos_requeridos():
    """Verifica que todos los archivos requeridos existan."""
    print("=" * 80)
    print("VERIFICACIÓN DE ARCHIVOS REQUERIDOS")
    print("=" * 80)
    
    base_path = Path(BASE_DIR) / "apps" / "tenant" / "core" / "templates" / "tenant" / "core" / "partials"
    static_base = Path(BASE_DIR) / "apps" / "tenant" / "core" / "static" / "core" / "js"
    
    modulos = {
        "empresa": {
            "list": "empresa/empresa_list.html",
            "modals": "empresa/modals.html",
            "assets": "empresa/assets_empresa.html",
            "js": "empresa/empresa.page.js"
        },
        "facturas": {
            "list": "facturas/list.html",
            "modals": "facturas/modals.html",
            "assets": "facturas/assets_facturas.html",
            "js": "facturas/facturas.page.js"
        },
        "contabilidad_cuentas": {
            "list": "contabilidad/list_cuentas.html",
            "modals": "contabilidad/modals_cuentas.html",
            "assets": "contabilidad/assets_cuentas.html",
            "js": "contabilidad/cuentas.page.js"
        },
        "contabilidad_asientos": {
            "list": "contabilidad/list_asientos.html",
            "modals": "contabilidad/modals_asientos.html",
            "assets": "contabilidad/assets_asientos.html",
            "js": "contabilidad/asientos.page.js"
        },
        "inventario_catalogo": {
            "list": "inventario/list_catalogo.html",
            "modals": "inventario/modals_catalogo.html",
            "assets": "inventario/assets_inventario.html",
            "js": "inventario/catalogo.page.js"
        },
        "inventario_activos": {
            "list": "inventario/list_activos.html",
            "modals": "inventario/modals_activos.html",
            "assets": "inventario/assets_inventario.html",
            "js": "inventario/activos.page.js"
        },
        "inventario_movimientos": {
            "list": "inventario/list_movimientos.html",
            "modals": "inventario/modals_movimientos.html",
            "assets": "inventario/assets_inventario.html",
            "js": "inventario/movimientos.page.js"
        },
        "empleados": {
            "list": "empleados/list.html",
            "modals": "empleados/modals.html",
            "assets": "empleados/assets_empleados.html",
            "js": "empleados/empleados.page.js"
        },
        "gastos": {
            "list": "gastos/list.html",
            "modals": "gastos/modals.html",
            "assets": "gastos/assets_gastos.html",
            "js": "gastos/gastos.page.js"
        },
        "proveedores": {
            "list": "proveedores/list.html",
            "modals": "proveedores/modals.html",
            "assets": "proveedores/assets_proveedores.html",
            "js": "proveedores/proveedores.page.js"
        },
        "clientes": {
            "list": "clientes/list.html",
            "modals": "clientes/modals.html",
            "assets": "clientes/assets_clientes.html",
            "js": "clientes/clientes.page.js"
        },
        "perfil": {
            "list": "perfil/list.html",
            "modals": "perfil/modals.html",
            "assets": "perfil/assets_perfil.html",
            "js": "perfil/perfil.page.js"
        },
    }
    
    errores = []
    exitosos = []
    
    for modulo, archivos in modulos.items():
        print(f"\n[Modulo] {modulo}")
        
        # Verificar list.html
        list_path = base_path / archivos["list"]
        if list_path.exists():
            print(f"  [OK] list.html: {archivos['list']}")
            exitosos.append(f"{modulo}.list")
        else:
            print(f"  [ERROR] list.html: {archivos['list']} - NO ENCONTRADO")
            errores.append(f"{modulo}.list")
        
        # Verificar modals.html
        modals_path = base_path / archivos["modals"]
        if modals_path.exists():
            print(f"  [OK] modals.html: {archivos['modals']}")
            exitosos.append(f"{modulo}.modals")
        else:
            print(f"  [ERROR] modals.html: {archivos['modals']} - NO ENCONTRADO")
            errores.append(f"{modulo}.modals")
        
        # Verificar assets.html
        assets_path = base_path / archivos["assets"]
        if assets_path.exists():
            print(f"  [OK] assets.html: {archivos['assets']}")
            exitosos.append(f"{modulo}.assets")
        else:
            print(f"  [ERROR] assets.html: {archivos['assets']} - NO ENCONTRADO")
            errores.append(f"{modulo}.assets")
        
        # Verificar JS
        js_path = static_base / archivos["js"]
        if js_path.exists():
            print(f"  [OK] JS: {archivos['js']}")
            exitosos.append(f"{modulo}.js")
        else:
            print(f"  [ERROR] JS: {archivos['js']} - NO ENCONTRADO")
            errores.append(f"{modulo}.js")
    
    print("\n" + "=" * 80)
    print(f"RESUMEN: {len(exitosos)} archivos encontrados, {len(errores)} archivos faltantes")
    print("=" * 80)
    
    if errores:
        print("\n[ERROR] ERRORES ENCONTRADOS:")
        for error in errores:
            print(f"  - {error}")
        return False
    else:
        print("\n[OK] TODOS LOS ARCHIVOS REQUERIDOS ESTAN PRESENTES")
        return True


def verificar_workspace_html():
    """Verifica que workspace.html incluya todos los partials."""
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE INTEGRACIÓN EN workspace.html")
    print("=" * 80)
    
    try:
        # Leer el archivo directamente en lugar de renderizar
        workspace_path = Path(BASE_DIR) / "apps" / "tenant" / "core" / "templates" / "tenant" / "core" / "workspace.html"
        with open(workspace_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar includes de list.html
        list_includes = [
            'empresa/empresa_list.html',
            'facturas/list.html',
            'contabilidad/list_cuentas.html',
            'contabilidad/list_asientos.html',
            'inventario/list_catalogo.html',
            'inventario/list_activos.html',
            'inventario/list_movimientos.html',
            'empleados/list.html',
            'gastos/list.html',
            'proveedores/list.html',
            'clientes/list.html',
            'perfil/list.html',
        ]
        
        # Verificar includes de modals.html
        modals_includes = [
            'empresa/modals.html',
            'facturas/modals.html',
            'contabilidad/modals_cuentas.html',
            'contabilidad/modals_asientos.html',
            'inventario/modals_catalogo.html',
            'inventario/modals_activos.html',
            'inventario/modals_movimientos.html',
            'empleados/modals.html',
            'gastos/modals.html',
            'proveedores/modals.html',
            'clientes/modals.html',
            'perfil/modals.html',
        ]
        
        # Verificar includes de assets.html
        assets_includes = [
            'empresa/assets_empresa.html',
            'facturas/assets_facturas.html',
            'contabilidad/assets_cuentas.html',
            'contabilidad/assets_asientos.html',
            'inventario/assets_inventario.html',
            'empleados/assets_empleados.html',
            'gastos/assets_gastos.html',
            'proveedores/assets_proveedores.html',
            'clientes/assets_clientes.html',
            'perfil/assets_perfil.html',
        ]
        
        errores = []
        exitosos = []
        
        print("\n[Verificando] includes de list.html:")
        for include in list_includes:
            if include in content:
                print(f"  [OK] {include}")
                exitosos.append(f"list.{include}")
            else:
                print(f"  [ERROR] {include} - NO ENCONTRADO")
                errores.append(f"list.{include}")
        
        print("\n[Verificando] includes de modals.html:")
        for include in modals_includes:
            if include in content:
                print(f"  [OK] {include}")
                exitosos.append(f"modals.{include}")
            else:
                print(f"  [ERROR] {include} - NO ENCONTRADO")
                errores.append(f"modals.{include}")
        
        print("\n[Verificando] includes de assets.html:")
        for include in assets_includes:
            if include in content:
                print(f"  [OK] {include}")
                exitosos.append(f"assets.{include}")
            else:
                print(f"  [ERROR] {include} - NO ENCONTRADO")
                errores.append(f"assets.{include}")
        
        print("\n" + "=" * 80)
        print(f"RESUMEN: {len(exitosos)} includes encontrados, {len(errores)} includes faltantes")
        print("=" * 80)
        
        if errores:
            print("\n[ERROR] ERRORES ENCONTRADOS:")
            for error in errores:
                print(f"  - {error}")
            return False
        else:
            print("\n[OK] TODOS LOS INCLUDES ESTAN PRESENTES EN workspace.html")
            return True
            
    except Exception as e:
        print(f"\n[ERROR] ERROR AL CARGAR TEMPLATE: {e}")
        return False


def verificar_js_exports():
    """Verifica que los módulos JS exporten las funciones correctas."""
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE EXPORTS JS")
    print("=" * 80)
    
    static_base = Path(BASE_DIR) / "apps" / "tenant" / "core" / "static" / "core" / "js"
    
    modulos_js = {
        "empresa": "empresa/empresa.page.js",
        "gastos": "gastos/gastos.page.js",
        "proveedores": "proveedores/proveedores.page.js",
        "clientes": "clientes/clientes.page.js",
        "empleados": "empleados/empleados.page.js",
        "perfil": "perfil/perfil.page.js",
        "cuentas": "contabilidad/cuentas.page.js",
        "asientos": "contabilidad/asientos.page.js",
        "catalogo": "inventario/catalogo.page.js",
        "activos": "inventario/activos.page.js",
        "movimientos": "inventario/movimientos.page.js",
    }
    
    errores = []
    exitosos = []
    
    for modulo, ruta in modulos_js.items():
        js_path = static_base / ruta
        if not js_path.exists():
            print(f"  [ERROR] {modulo}: Archivo no encontrado - {ruta}")
            errores.append(f"{modulo}.file")
            continue
        
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar export de window.<modulo>DT
            export_pattern = f"window.{modulo}DT"
            if export_pattern in content:
                print(f"  [OK] {modulo}: Export encontrado ({export_pattern})")
                exitosos.append(f"{modulo}.export")
            else:
                print(f"  [ERROR] {modulo}: Export no encontrado ({export_pattern})")
                errores.append(f"{modulo}.export")
                
            # Verificar función init
            if "init" in content and export_pattern in content:
                print(f"    [OK] {modulo}: Funcion init() presente")
                exitosos.append(f"{modulo}.init")
            else:
                print(f"    [WARN] {modulo}: Funcion init() no verificada")
                
        except Exception as e:
            print(f"  [ERROR] {modulo}: Error al leer archivo - {e}")
            errores.append(f"{modulo}.read")
    
    print("\n" + "=" * 80)
    print(f"RESUMEN: {len(exitosos)} exports encontrados, {len(errores)} errores")
    print("=" * 80)
    
    if errores:
        print("\n[ERROR] ERRORES ENCONTRADOS:")
        for error in errores:
            print(f"  - {error}")
        return False
    else:
        print("\n[OK] TODOS LOS EXPORTS JS ESTAN CORRECTOS")
        return True


def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE INTEGRACIÓN WORKSPACE v2.37")
    print("=" * 80)
    
    resultados = []
    
    # Verificar archivos requeridos
    resultados.append(verificar_archivos_requeridos())
    
    # Verificar integración en workspace.html
    resultados.append(verificar_workspace_html())
    
    # Verificar exports JS
    resultados.append(verificar_js_exports())
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    
    if all(resultados):
        print("\n[OK] TODAS LAS VERIFICACIONES PASARON")
        print("\nEl workspace esta completamente integrado y listo para pruebas CRUD.")
        return 0
    else:
        print("\n[ERROR] ALGUNAS VERIFICACIONES FALLARON")
        print("\nRevisa los errores arriba y corrige los archivos faltantes.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
