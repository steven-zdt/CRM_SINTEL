"""
App de Perfil Privado del Colaborador.

Esta app almacena datos específicos del usuario DENTRO del tenant
sin "contaminar" el modelo de usuario global (apps.public.accounts.User).

Ejemplos de datos almacenados:
- Cargo, Departamento
- Teléfono corporativo (diferente al personal)
- Avatar
- Preferencias de UI (modo oscuro, densidad de tablas, etc.)
"""
