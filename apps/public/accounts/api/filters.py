"""
Filtros personalizados para la app accounts.

Referencia: https://django-filter.readthedocs.io/
"""

import django_filters

from apps.public.accounts.models import User


class UserFilter(django_filters.FilterSet):
    """
    FilterSet personalizado para User.

    Permite filtrar por campos booleanos correctamente.
    """

    is_active = django_filters.BooleanFilter()
    is_staff = django_filters.BooleanFilter()
    is_superuser = django_filters.BooleanFilter()

    class Meta:
        model = User
        fields = ["is_active", "is_staff", "is_superuser"]
