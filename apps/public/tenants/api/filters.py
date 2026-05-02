"""
Filtros personalizados para la app tenants.

Referencia: https://django-filter.readthedocs.io/
"""

import django_filters

from apps.public.tenants.models import Client


class ClientFilter(django_filters.FilterSet):
    """
    FilterSet personalizado para Client.

    Permite filtrar por campos booleanos correctamente.
    """

    on_trial = django_filters.BooleanFilter()

    class Meta:
        model = Client
        fields = ["on_trial", "paid_until"]
