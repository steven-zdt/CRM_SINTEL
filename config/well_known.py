"""
Handlers para rutas .well-known (estándares web).

Este módulo maneja requests a rutas .well-known que son comunes
en desarrollo, como la sonda de Chrome DevTools.
"""
from django.http import JsonResponse


def chrome_devtools(request):
    """
    Handler para Chrome DevTools Automatic Workspace Folders.
    
    Chrome DevTools envía una request a esta ruta para detectar
    si el servidor soporta "Automatic Workspace Folders".
    Retornamos un JSON vacío para silenciar el 404.
    
    Referencia: chrome://flags/#devtools-project-settings
    """
    return JsonResponse({}, status=200)
