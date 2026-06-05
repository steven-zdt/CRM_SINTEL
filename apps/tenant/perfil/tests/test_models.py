from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile


class TenantProfileModelTest(TenantTestCase):
    def test_create_tenant_profile_and_unique_together(self):
        User = get_user_model()
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')
        # Crear empresa mínima requerida
        empresa = Empresa.objects.create(razon_social='Empresa Test', nit='9000001', direccion='Calle 123')
        profile = TenantProfile.objects.create(user=user, empresa=empresa, cargo='Dev')
        self.assertEqual(TenantProfile.objects.count(), 1)
        # Intentar crear duplicado debe lanzar IntegrityError por unique_together
        with self.assertRaises(IntegrityError):
            TenantProfile.objects.create(user=user, empresa=empresa)
