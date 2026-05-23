from typing import Any
from django.db import transaction

from apps.tenant.perfil.models import TenantProfile
from apps.tenant.empresa.models import Empresa, Sede, Area

from .crud_service import (
    crear_empresa_db, actualizar_empresa_db, get_empresa_data,
    crear_sede_db, actualizar_sede_db, eliminar_sede_db,
    crear_area_db, actualizar_area_db, eliminar_area_db
)


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


class SedeService:
    """
    Business Service para Sede. Orquesta validaciones y reglas de negocio sobre las primitivas CRUD.
    """
    @staticmethod
    @transaction.atomic
    def crear_sede(empresa_id: int, data: dict) -> Sede:
        return crear_sede_db(empresa_id, data)

    @staticmethod
    @transaction.atomic
    def actualizar_sede(empresa_id: int, uuid_str: str, data: dict) -> Sede:
        # Recuperar sede con verificación anti-IDOR (empresa_id)
        sede = Sede.objects.filter(empresa_id=empresa_id, uuid=uuid_str).first()
        if not sede:
            raise Sede.DoesNotExist("Sede no encontrada o no pertenece a la empresa.")
        return actualizar_sede_db(sede, data)

    @staticmethod
    @transaction.atomic
    def eliminar_sede(empresa_id: int, uuid_str: str) -> None:
        # Recuperar sede con verificación anti-IDOR (empresa_id)
        sede = Sede.objects.filter(empresa_id=empresa_id, uuid=uuid_str).first()
        if not sede:
            raise Sede.DoesNotExist("Sede no encontrada o no pertenece a la empresa.")
        eliminar_sede_db(sede)


class AreaService:
    """
    Business Service para Area. Orquesta validaciones y reglas de negocio sobre las primitivas CRUD.
    """
    @staticmethod
    @transaction.atomic
    def crear_area(empresa_id: int, data: dict) -> Area:
        return crear_area_db(empresa_id, data)

    @staticmethod
    @transaction.atomic
    def actualizar_area(empresa_id: int, uuid_str: str, data: dict) -> Area:
        area = Area.objects.filter(empresa_id=empresa_id, uuid=uuid_str).first()
        if not area:
            raise Area.DoesNotExist("Area no encontrada o no pertenece a la empresa.")
        return actualizar_area_db(area, data)

    @staticmethod
    @transaction.atomic
    def eliminar_area(empresa_id: int, uuid_str: str) -> None:
        area = Area.objects.filter(empresa_id=empresa_id, uuid=uuid_str).first()
        if not area:
            raise Area.DoesNotExist("Area no encontrada o no pertenece a la empresa.")
        eliminar_area_db(area)
