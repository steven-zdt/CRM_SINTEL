"""
Servicios de gestión de empresa.

Este módulo contiene servicios puros (sin dependencias de Django) para la lógica
de negocio relacionada con la gestión de datos de empresa.

Principios:
- Service Layer Pattern: Lógica de negocio separada de modelos y vistas
- Cero Signals: Toda la lógica es explícita en servicios
- Tenant Isolation: Operaciones dentro del contexto del tenant
"""
