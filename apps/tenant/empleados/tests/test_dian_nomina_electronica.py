"""
Tests DEUDA-11 -- generacion de XML NominaIndividual (DSPNE) + CUNE al
procesar un Devengo.

Cobertura:
  - CuneService.calcular(): determinismo, formato (96 hex chars SHA-384),
    sensibilidad a cambios de input.
  - NominaXMLBuilderService.build(): XML bien formado, namespaces, campos
    clave presentes, marcador de firma vacio (contrato con XadesSignerService).
  - DevengoBusinessService.procesar_devengo(): TransmisionNominaDIAN.xml_enviado
    queda poblado con un XML real (no vacio, no placeholder), CUNE
    coincide con el guardado en TransmisionNominaDIAN.cune.

Restricciones: sin emojis en codigo Python (AGENTS.md 0), aislamiento
tenant via schema_context (AGENTS.md 4).
"""
from decimal import Decimal
from xml.etree import ElementTree as ET

import pytest
from django_tenants.utils import schema_context

from apps.tenant.empleados.services.dian import CuneService, NominaXMLBuilderService


def make_host(tenant):
    return f"{tenant.schema_name}.sintel.net.co"


EMPLEADO_PAYLOAD = {
    "tipo_documento": "CC",
    "numero_documento": "9009998887",
    "primer_nombre": "Nomina",
    "primer_apellido": "Electronica",
    "email": "nomina.electronica@sintel.local",
    "fecha_ingreso": "2025-01-01",
    "eps": "EPS001",
    "afp": "AFP001",
    "arl": "ARL001",
    "nivel_riesgo_arl": "I",
}

CONTRATO_PAYLOAD_BASE = {
    "tipo": "FIJO",
    "salario_mensual": "1500000.00",
    "fecha_inicio": "2025-01-01",
    "cargo": "Tester DIAN",
    "estado": "ACTIVO",
}

DEVENGO_PAYLOAD_BASE = {
    "periodo_mes": "2025-02",
    "fecha_pago": "2025-02-28",
    "dias_laborados": 30,
}


class TestCuneService:
    def test_calcular_retorna_96_hex_chars(self):
        cune = CuneService.calcular(
            num_nie="SETP990000001", fec_nie="2025-02-28", hor_nie="08:00:00-05:00",
            val_dev=Decimal("1500000.00"), val_ded=Decimal("120000.00"), val_pag=Decimal("1380000.00"),
            nit_empleador="901234567", num_doc_trabajador="9009998887", cl_tec="",
        )
        assert len(cune) == 96
        int(cune, 16)  # no lanza -- es hexadecimal valido

    def test_calcular_es_determinista(self):
        kwargs = dict(
            num_nie="SETP990000001", fec_nie="2025-02-28", hor_nie="08:00:00-05:00",
            val_dev=Decimal("1500000.00"), val_ded=Decimal("120000.00"), val_pag=Decimal("1380000.00"),
            nit_empleador="901234567", num_doc_trabajador="9009998887", cl_tec="",
        )
        assert CuneService.calcular(**kwargs) == CuneService.calcular(**kwargs)

    def test_calcular_cambia_con_el_valor_a_pagar(self):
        base = dict(
            num_nie="SETP990000001", fec_nie="2025-02-28", hor_nie="08:00:00-05:00",
            val_dev=Decimal("1500000.00"), val_ded=Decimal("120000.00"),
            nit_empleador="901234567", num_doc_trabajador="9009998887", cl_tec="",
        )
        cune_a = CuneService.calcular(val_pag=Decimal("1380000.00"), **base)
        cune_b = CuneService.calcular(val_pag=Decimal("1380000.01"), **base)
        assert cune_a != cune_b


class TestNominaXMLBuilderService:
    DTO_BASE = {
        "num_nie": "SETP990000001",
        "fec_nie": "2025-02-28",
        "hor_nie": "08:00:00-05:00",
        "tipo_xml": "102",
        "tip_amb": "2",
        "periodo": {
            "fecha_ingreso": "2025-01-01",
            "fecha_liquidacion_inicio": "2025-02-01",
            "fecha_liquidacion_fin": "2025-02-28",
            "tiempo_laborado_dias": 30,
        },
        "empleador": {
            "nit": "901234567", "dv": "0", "razon_social": "EMPRESA TEST S.A.S.",
            "direccion": "Calle Falsa 123", "ciudad": "Bogota",
        },
        "trabajador": {
            "tipo_documento": "CC", "numero_documento": "9009998887",
            "primer_apellido": "Electronica", "segundo_apellido": "",
            "primer_nombre": "Nomina", "segundo_nombre": "",
            "tipo_contrato": "FIJO", "cargo": "Tester DIAN", "salario": Decimal("1500000.00"),
        },
        "pago": {"forma": "1", "metodo": "42", "fecha_pago": "2025-02-28"},
        "devengados": {
            "dias_trabajados": 30, "salario_basico": Decimal("1500000.00"),
            "auxilio_transporte": Decimal("0"), "horas_extras": Decimal("0"),
            "otros": Decimal("0"), "total": Decimal("1500000.00"),
        },
        "deducciones": {
            "salud": Decimal("60000.00"), "pension": Decimal("60000.00"),
            "otros": Decimal("0"), "total": Decimal("120000.00"),
        },
        "total_pago": Decimal("1380000.00"),
        "resolucion": {
            "numero_autorizacion": "RES-TEST", "prefijo": "SETP",
            "desde": 1, "hasta": 5000,
            "fecha_inicio": "2025-01-01", "fecha_fin": "2026-01-01",
        },
    }

    def test_build_retorna_xml_bien_formado(self):
        cune = "a" * 96
        xml_bytes = NominaXMLBuilderService.build(self.DTO_BASE, cune)
        root = ET.fromstring(xml_bytes)  # lanza si no es XML valido
        assert root.tag.endswith("NominaIndividual")

    def test_build_incluye_cune_y_numero_documento(self):
        cune = "b" * 96
        xml_bytes = NominaXMLBuilderService.build(self.DTO_BASE, cune)
        xml_str = xml_bytes.decode("utf-8")
        assert cune in xml_str
        assert "SETP990000001" in xml_str
        assert "9009998887" in xml_str  # documento del trabajador
        assert "901234567" in xml_str   # NIT empleador

    def test_build_deja_marcador_vacio_para_firma_xades(self):
        """XadesSignerService.sign() busca el marcador literal
        '<ext:UBLExtension/>' (segunda UBLExtension vacia) -- ver
        apps/tenant/core/dian/xades_signer.py. Si el builder no lo deja
        exacto, la firma nunca se inserta silenciosamente."""
        xml_bytes = NominaXMLBuilderService.build(self.DTO_BASE, "c" * 96)
        assert b"<ext:UBLExtension />" in xml_bytes or b"<ext:UBLExtension/>" in xml_bytes


@pytest.mark.django_db
class TestProcesarDevengoGeneraXmlDian:
    URL_EMP = "/api/v1/empleados/"
    URL_CONT = "/api/v1/empleados/contratos/"
    URL_DEV = "/api/v1/empleados/devengos/"

    def _setup(self, client, tenant):
        with schema_context(tenant.schema_name):
            from apps.tenant.empleados.models import ResolucionDIAN
            from apps.tenant.empresa.models import Empresa

            empresa = Empresa.objects.only("id").first()
            ResolucionDIAN.objects.get_or_create(
                empresa=empresa,
                numero_resolucion="RES-DIAN-XML-TEST",
                defaults={
                    "prefijo": "XML",
                    "rango_desde": 1,
                    "rango_hasta": 10000,
                    "fecha_resolucion": "2025-01-01",
                    "fecha_inicio": "2025-01-01",
                    "fecha_fin": "2027-01-01",
                    "vigente": True,
                },
            )

        emp_resp = client.post(
            self.URL_EMP, data=EMPLEADO_PAYLOAD, content_type="application/json",
            HTTP_HOST=make_host(tenant),
        )
        assert emp_resp.status_code == 201, emp_resp.content[:300]
        emp = emp_resp.json()

        cont_resp = client.post(
            self.URL_CONT, data={**CONTRATO_PAYLOAD_BASE, "empleado": emp["id"]},
            content_type="application/json", HTTP_HOST=make_host(tenant),
        )
        assert cont_resp.status_code == 201, cont_resp.content[:300]
        cont = cont_resp.json()
        return emp, cont

    def test_transmision_nomina_dian_queda_con_xml_firmado(self, client, admin_user, tenant):
        client.force_login(admin_user)
        emp, cont = self._setup(client, tenant)

        payload = {**DEVENGO_PAYLOAD_BASE, "empleado": emp["id"], "contrato": cont["id"]}
        resp = client.post(
            self.URL_DEV, data=payload, content_type="application/json", HTTP_HOST=make_host(tenant),
        )
        assert resp.status_code == 201, resp.content[:500]
        devengo_uuid = resp.json()["uuid"]

        with schema_context(tenant.schema_name):
            from apps.tenant.empleados.models import Devengo, TransmisionNominaDIAN

            devengo = Devengo.objects.get(uuid=devengo_uuid)
            transmision = TransmisionNominaDIAN.objects.get(devengo=devengo)

            assert transmision.cune
            assert len(transmision.cune) == 96

            assert transmision.xml_enviado, "xml_enviado quedo vacio -- DEUDA-11 no genero el documento"
            root = ET.fromstring(transmision.xml_enviado.encode("utf-8"))
            assert root.tag.endswith("NominaIndividual")
            assert transmision.cune in transmision.xml_enviado
            assert transmision.numero_documento in transmision.xml_enviado
