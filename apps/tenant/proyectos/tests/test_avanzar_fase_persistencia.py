"""
Regresion (2026-09-12): POST .../avanzar-fase/ devolvia 200 con la fase
nueva en el body, pero la fila real en Postgres nunca cambiaba.

Causa raiz: cambiar_fase_proyecto() solo muta proyecto.fase_actual (y los
campos de responsable) EN MEMORIA. El unico .save() que corria despues era
el de calcular_indicadores_financieros(), con
update_fields=['costo_mano_obra_real','costo_materiales_real',
'utilidad_estimada','margen_rentabilidad'] -- Django genera un UPDATE que
solo toca esas 4 columnas, asi que fase_actual se perdia en silencio. La
respuesta HTTP parecia correcta porque serializa el objeto Python ya
mutado, no lo que quedo persistido.

Ver docs/remediation/AUDIT_BASELINE_20260912.md hallazgo P-1.
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework import status

from apps.tenant.proyectos.models import Proyecto
from apps.tenant.empresa.models import Empresa
from apps.public.accounts.models import User


@pytest.mark.django_db
class TestAvanzarFasePersistencia:

    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        self.tenant = tenant1
        with schema_context('public'):
            self.user = User.objects.create_user(
                email='avanzar-fase@test.com', password='test123'
            )
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.update_or_create(
                client=self.tenant,
                user=self.user,
                defaults={'rol': 'ADMIN', 'is_active': True, 'is_primary_admin': True},
            )
        with schema_context(self.tenant.schema_name):
            from apps.tenant.perfil.models import TenantProfile
            self.empresa = Empresa.objects.first()
            TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol='ADMIN')

    def test_avanzar_fase_persiste_en_bd_no_solo_en_la_respuesta(self, tenant1):
        with schema_context(tenant1.schema_name):
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Avanzar Fase', empresa=self.empresa, fase_actual='BORRADOR',
            )

            client = APIClient()
            client.force_authenticate(user=self.user)

            response = client.post(
                f'/api/v1/proyectos/{proyecto.uuid}/avanzar-fase/',
                {'fase': 'INICIO'},
                format='json',
                HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
            )

            assert response.status_code == status.HTTP_200_OK, \
                f"Expected 200, got {response.status_code}. Body: {response.data}"
            # La respuesta ya mostraba la fase nueva incluso con el bug (objeto
            # en memoria) -- la asercion real es contra una relectura fresca.
            assert response.data['fase_actual'] == 'INICIO'

            # Relectura real desde Postgres, no el objeto Python de la request.
            proyecto_en_bd = Proyecto.objects.get(pk=proyecto.pk)
            assert proyecto_en_bd.fase_actual == 'INICIO', (
                "fase_actual no se persistio en BD -- avanzar-fase respondio "
                "200 pero la fila real sigue en la fase anterior."
            )

    def test_avanzar_fase_persiste_snapshot_de_responsable(self, tenant1):
        """
        cambiar_fase_proyecto() tambien asigna responsable_comercial_id/
        nombre (para fase INICIO) en memoria -- debe sobrevivir el mismo
        save() que persiste fase_actual.
        """
        with schema_context(tenant1.schema_name):
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Avanzar Fase Responsable', empresa=self.empresa,
                fase_actual='BORRADOR',
            )

            client = APIClient()
            client.force_authenticate(user=self.user)

            response = client.post(
                f'/api/v1/proyectos/{proyecto.uuid}/avanzar-fase/',
                {'fase': 'INICIO', 'responsable_nombre': 'Responsable Comercial Test'},
                format='json',
                HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
            )

            assert response.status_code == status.HTTP_200_OK, response.data

            proyecto_en_bd = Proyecto.objects.get(pk=proyecto.pk)
            assert proyecto_en_bd.fase_actual == 'INICIO'
            assert proyecto_en_bd.responsable_comercial_nombre == 'Responsable Comercial Test'
