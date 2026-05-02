"""
Core API para composición y orquestación de datos de TENANT_APPS.

# WARNING: POLÍTICA:
- Esta API NO reemplaza los CRUD de las apps individuales
- Solo agrega/compose endpoints para presentación
- Reutiliza servicios y serializers de las apps "dueñas"
- Mantiene tenant-awareness y branding dinámico

# WARNING: CENTRALIZACIÓN:
- Toda la lógica de presentación de datos está centralizada aquí
- Manejadores de error personalizados (404, 403) en handlers.py
- Endpoints de composición en views.py
- Servicios de orquestación en services/orchestration.py
"""
