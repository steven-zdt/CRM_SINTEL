import factory
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresas.models import Empresa
from apps.tenant.clientes.models import Cliente

class EmpresaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Empresa
    nombre = factory.Faker('company')

class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cliente
    empresa = factory.SubFactory(EmpresaFactory)
    razon_social = factory.Faker('name')

class CotizacionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cotizacion
    empresa = factory.SubFactory(EmpresaFactory)
    cliente = factory.SubFactory(ClienteFactory)
    total = 1000
    fecha = factory.Faker('date_this_year')
