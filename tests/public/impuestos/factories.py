"""
Factories para modelos de impuestos (factory_boy).

Facilitan la creación de datos de prueba.
"""
import factory
from django.utils import timezone
from datetime import timedelta
from apps.public.impuestos.models import (
    TipoImpuesto,
    TarifaIVA,
    ConceptoRetencion,
    CodigoTributario,
    ActividadEconomica,
    NormaTributaria,
    DocumentoFuente,
)


class TipoImpuestoFactory(factory.django.DjangoModelFactory):
    """Factory para TipoImpuesto."""
    
    class Meta:
        model = TipoImpuesto
    
    codigo = factory.Sequence(lambda n: f"T{n:03d}")
    nombre = factory.Faker("word", locale="es_ES")
    descripcion = factory.Faker("sentence", locale="es_ES", nb_words=6)
    activo = True
    fecha_vigencia = factory.LazyFunction(lambda: timezone.now().date())


class TarifaIVAFactory(factory.django.DjangoModelFactory):
    """Factory para TarifaIVA."""
    
    class Meta:
        model = TarifaIVA
    
    codigo = factory.Sequence(lambda n: f"TAR{n:03d}")
    nombre = factory.Faker("word", locale="es_ES")
    porcentaje = factory.Iterator([0, 19, 5])
    tipo_tarifa = factory.Iterator(["GENERAL", "REDUCIDA", "EXENTA"])
    activo = True
    fecha_vigencia = factory.LazyFunction(lambda: timezone.now().date())


class ConceptoRetencionFactory(factory.django.DjangoModelFactory):
    """Factory para ConceptoRetencion."""
    
    class Meta:
        model = ConceptoRetencion
    
    codigo = factory.Sequence(lambda n: f"RET{n:03d}")
    nombre = factory.Faker("word", locale="es_ES")
    tipo_retencion = factory.Iterator(["ICA", "IVA", "RENTA"])
    activo = True
    fecha_vigencia = factory.LazyFunction(lambda: timezone.now().date())


class CodigoTributarioFactory(factory.django.DjangoModelFactory):
    """Factory para CodigoTributario."""
    
    class Meta:
        model = CodigoTributario
    
    codigo = factory.Sequence(lambda n: f"COD{n:03d}")
    nombre = factory.Faker("word", locale="es_ES")
    tipo = factory.Iterator(["RESPONSABILIDAD", "REGIMEN"])
    activo = True
    fecha_vigencia = factory.LazyFunction(lambda: timezone.now().date())


class ActividadEconomicaFactory(factory.django.DjangoModelFactory):
    """Factory para ActividadEconomica."""
    
    class Meta:
        model = ActividadEconomica
    
    codigo = factory.Sequence(lambda n: f"ACT{n:04d}")
    nombre = factory.Faker("company", locale="es_ES")
    descripcion = factory.Faker("sentence", locale="es_ES", nb_words=8)
    activo = True


class DocumentoFuenteFactory(factory.django.DjangoModelFactory):
    """Factory para DocumentoFuente."""
    
    class Meta:
        model = DocumentoFuente
    
    fuente = factory.Iterator(["DIAN", "DOF", "SUIN"])
    tipo = factory.Iterator(["PDF", "HTML", "CSV"])
    estado = "RECIBIDO"
    fecha_publicacion = factory.LazyFunction(lambda: timezone.now().date())
    hash_sha256 = factory.LazyFunction(lambda: "a" * 64)  # Hash dummy


class NormaTributariaFactory(factory.django.DjangoModelFactory):
    """Factory para NormaTributaria."""
    
    class Meta:
        model = NormaTributaria
    
    documento_fuente = factory.SubFactory(DocumentoFuenteFactory)
    articulo = factory.Sequence(lambda n: f"Art. {n}")
    impuesto = factory.Iterator(["IVA", "ICA", "RENTA"])
    tema = factory.Iterator(["Exento", "Gravado", "Retención"])
    vigencia_desde = factory.LazyFunction(lambda: timezone.now().date())
    vigencia_hasta = None
    texto_plano = factory.Faker("paragraph", locale="es_ES", nb_sentences=3)
    referencias = factory.LazyFunction(list)
