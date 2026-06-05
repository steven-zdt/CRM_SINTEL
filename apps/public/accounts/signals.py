"""
Signals del modulo accounts (esquema public).

global_user_hard_deleting
--------------------------
Se emite ANTES de eliminar fisicamente un usuario global de la BD.
Permite que apps tenant reaccionen de forma desacoplada limpiando datos
propios que referencian al usuario (ej.: TenantProfile en cada schema).

Uso:
    from apps.public.accounts.signals import global_user_hard_deleting
    global_user_hard_deleting.send(sender=User, user=<instancia User>)

Patron de aislamiento:
    El signal se define en apps.public (esquema public).
    Los receivers se registran en apps.tenant.core (bridge autorizado).
    Esto garantiza la unidireccionalidad: tenant importa de public,
    nunca al reves.
"""
from django.dispatch import Signal

global_user_hard_deleting = Signal()
