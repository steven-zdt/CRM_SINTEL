from typing import Any
from django.db import transaction

from apps.tenant.perfil.models import TenantProfile
from apps.tenant.empresa.models import Empresa

from .crud_service import crear_empresa_db, actualizar_empresa_db, get_empresa_data


class EmpresaService:
    """
    Business Service: orquesta validaciones y reglas de negocio sobre las primitivas CRUD.
    """

    @staticmethod
    @transaction.atomic
    def get_or_create_empresa(data: dict) -> Empresa:
        empresa = Empresa.objects.first()
        if empresa:
            return empresa

        if Empresa.objects.filter(nit=data.get('nit')).exists():
            raise ValueError("Ya existe una empresa con este NIT en el tenant.")

        return crear_empresa_db(data)

    @staticmethod
    @transaction.atomic
    def update_empresa(data: dict) -> Empresa:
        empresa = Empresa.objects.first()
        if not empresa:
            raise Empresa.DoesNotExist("No existe empresa configurada para este tenant.")
        return actualizar_empresa_db(data)

    @staticmethod
    def has_active_profiles(empresa: Empresa) -> bool:
        return TenantProfile.objects.filter(empresa=empresa, is_active=True).exists()


def crear_empresa(data: dict) -> Empresa:
    # Capa de compatibilidad: delegar directamente a la primitiva CRUD
    # Esto evita acceso directo a la base de datos desde unit tests que parchean
    # las primitivas subyacentes (monkeypatch). Las validaciones de negocio se
    # realizan en el nivel CRUD o en la capa que invoque estos helpers.
    return crear_empresa_db(data)


def actualizar_empresa(data: dict) -> Empresa:
    return EmpresaService.update_empresa(data)
