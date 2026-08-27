import pytest
import datetime
from decimal import Decimal
from django.db import IntegrityError
from django_tenants.utils import schema_context
from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.cotizaciones.models import Cotizacion

@pytest.mark.django_db
def test_crear_cotizacion_valida(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'items': [
            {
                'tipo_item': 'PRODUCTO',
                'descripcion': 'Equipo de prueba',
                'cantidad': 2,
                'costo_unitario': 500,
                'porcentaje_utilidad': 10,
                'unidad': 'UND',
                'orden': 1
            }
        ]
    }
    with schema_context(tenant.schema_name):
        # We need to make sure there's a configuration for the company as well
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
        ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={
                'dias_validez': 15,
                'nombre_configuracion': 'Perfil General',
                'es_activo': True
            }
        )
        
        cotizacion = CotizacionService.crear_preforma(empresa, payload)
        assert cotizacion.empresa_id == empresa.id
        assert cotizacion.cliente_id == cliente.id
        assert cotizacion.total_con_impuestos == Decimal("1309.00")
        assert Cotizacion.objects.filter(empresa_id=empresa.id).count() == 1
        # Regresion real (auditoria REL Cotizaciones FASE 0/6, 2026-08-26):
        # fecha_emision tenia auto_now_add=True en el modelo, asi que Django
        # ignoraba silenciosamente el valor calculado aqui y siempre
        # persistia timezone.now().date(). Este test ya mandaba una fecha
        # explicita en el payload (2026-03-30) pero nunca la aseveraba --
        # por eso el bug nunca se detecto.
        assert cotizacion.fecha_emision == datetime.date(2026, 3, 30)
        assert cotizacion.fecha_vencimiento == datetime.date(2026, 3, 30) + datetime.timedelta(days=15)


@pytest.mark.django_db
def test_cliente_de_otra_empresa_es_rechazado(tenant, factory_empresa, factory_cliente):
    """
    Gap de cobertura real (auditoria de modernizacion Cotizaciones, FASE 44,
    2026-08-27): el codigo de get_cliente_for_empresa() ya era DSV-seguro
    (re-verifica empresa_id contra el objeto real, no confia en el ID
    crudo), pero no existia ningun test que lo demostrara. Empresa es un
    singleton por schema (constraint de BD) -- no se puede crear una
    segunda Empresa real en el mismo schema para simular "cliente ajeno",
    asi que se prueba el limite de seguridad al nivel del service (mismo
    resultado que veria un intento real: un empresa_id que no coincide con
    el empresa_id real del Cliente).
    """
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        otra_empresa_id = empresa.id + 999999

        with pytest.raises(ValueError, match="does not belong to tenant empresa"):
            CotizacionService.get_cliente_for_empresa(cliente, otra_empresa_id)

        with pytest.raises(ValueError, match="not found for tenant empresa"):
            CotizacionService.get_cliente_for_empresa(cliente.id, otra_empresa_id)


@pytest.mark.django_db
def test_configuracion_de_otra_empresa_es_rechazada(tenant, factory_empresa):
    """Mismo hallazgo y mismo patron que test_cliente_de_otra_empresa_es_rechazado."""
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        configuracion = ConfiguracionCotizacion.objects.create(
            empresa=empresa, nombre_configuracion="Perfil Ajeno Test", dias_validez=15,
        )
        otra_empresa_id = empresa.id + 999999

        with pytest.raises(ValueError, match="does not belong to tenant empresa"):
            CotizacionService.get_configuracion_for_empresa(configuracion, otra_empresa_id)

        with pytest.raises(ValueError, match="not found for tenant empresa"):
            CotizacionService.get_configuracion_for_empresa(configuracion.id, otra_empresa_id)


@pytest.mark.django_db
def test_configuracion_nombre_duplicado_viola_constraint_de_bd(tenant, factory_empresa):
    """
    TOCTOU real (auditoria de modernizacion, FASE 45, 2026-08-27): mismo
    patron exacto que Producto.codigo antes del fix del CRUD audit de hoy
    -- la validacion de unicidad de nombre_configuracion solo vivia en
    ConfiguracionCotizacionDetailSerializer.validate() (query + exception,
    sin select_for_update). Ahora hay un UniqueConstraint de BD como ultima
    linea de defensa real contra la condicion de carrera.
    """
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        ConfiguracionCotizacion.objects.create(
            empresa=empresa, nombre_configuracion="Perfil Duplicado Test", dias_validez=15,
        )
        with pytest.raises(IntegrityError):
            ConfiguracionCotizacion.objects.create(
                empresa=empresa, nombre_configuracion="Perfil Duplicado Test", dias_validez=20,
            )
