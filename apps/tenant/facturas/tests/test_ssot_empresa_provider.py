"""
Tests para validar el SSoT de Empresa (provider canónico).
"""
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.empresa.services import EmpresaNotConfiguredError, get_empresa_emisor_data


class SSoTEmpresaProviderTests(TenantTestCase):
    """Tests para validar el contrato del provider SSoT de Empresa."""
    
    def test_sin_empresa_lanza(self):
        """Valida que sin Empresa configurada, lanza EmpresaNotConfiguredError."""
        with self.assertRaises(EmpresaNotConfiguredError):
            get_empresa_emisor_data()
    
    def test_sin_nit_lanza(self):
        """Valida que si Empresa existe pero sin NIT, lanza EmpresaNotConfiguredError."""
        # Hallazgo real: Empresa.nit es requerido (blank=False) a nivel de
        # modelo -- Empresa.objects.create(nit="") ahora es rechazado por
        # full_clean() (Model.save() lo llama explicitamente, ver
        # apps/tenant/empresa/models.py:217) antes de que este test llegue
        # a probar la rama defensiva de get_empresa_emisor_data(). Se usa
        # .update() (queryset, no invoca full_clean()) para simular el
        # registro con nit vacio que la rama defensiva debe seguir
        # manejando (p.ej. datos legacy/corruptos insertados antes de que
        # la validacion del modelo se endureciera).
        empresa = Empresa.objects.create(
            razon_social="SINTEL",
            nit="900000000",
            dv="",
            direccion="Calle 123",
            telefono="3001234567",
        )
        Empresa.objects.filter(pk=empresa.pk).update(nit="")

        with self.assertRaises(EmpresaNotConfiguredError):
            get_empresa_emisor_data()
    
    def test_con_empresa_ok(self):
        """Valida que con Empresa y NIT configurados, retorna datos correctos."""
        Empresa.objects.create(
            razon_social="SINTEL TECNOLOGY SAS",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567"
        )
        
        data = get_empresa_emisor_data()
        
        # Validar que retorna dict (no None)
        self.assertIsNotNone(data, "get_empresa_emisor_data() nunca debe retornar None")
        self.assertIsInstance(data, dict, "Debe retornar un dict")
        
        # Validar campos requeridos
        self.assertEqual(data.get("nit"), "901123299", "NIT debe coincidir")
        self.assertEqual(data.get("razon_social"), "SINTEL TECNOLOGY SAS", "Razón social debe coincidir")
        self.assertIn("nit", data, "Debe incluir campo 'nit'")
        self.assertIn("razon_social", data, "Debe incluir campo 'razon_social'")
    
    def test_contrato_nunca_none(self):
        """Valida el contrato: get_empresa_emisor_data() nunca retorna None."""
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567",
        )
        
        data = get_empresa_emisor_data()
        
        # El contrato establece que nunca retorna None; o lanza excepción o retorna dict
        self.assertIsNotNone(data, "Contrato: nunca None; o lanza excepción o retorna dict")
        self.assertIsInstance(data, dict, "Debe retornar dict si no lanza excepción")
