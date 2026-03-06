"""
Servicios de orquestación para Core API.

⚠️ POLÍTICA:
- No duplicar lógica de negocio de las apps "dueñas"
- Solo orquestar/componer datos de múltiples apps
- Mantener tenant-awareness (django-tenants maneja el aislamiento)
"""
