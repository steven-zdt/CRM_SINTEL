import datetime
import io

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.tenant.bancos.models import (
    CuentaBancaria,
    ExtractoBancario,
    TransaccionBancaria,
)
from apps.tenant.bancos.services.business_service import ExtractoBancarioBusinessService
from apps.tenant.bancos.services.crud_service import ExtractoBancarioCRUDService
from tests.tenant.base_test import SintelTenantTestCase


class TestExtractoBancarioCRUD(SintelTenantTestCase):
    """
    Integration tests for ExtractoBancario CRUD and ETL parser operations.
    """

    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.perfil.models import TenantProfile

        self.empresa = Empresa.objects.create(
            razon_social="Test Empresa Bancos",
            nit="900000222",
            dv="1",
            direccion="Calle Bancaria 456",
            telefono="7654321",
            email_contacto="bancos@test.com",
            regimen_tributario="Responsable de IVA",
            moneda="COP",
        )
        self.profile = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="ADMIN",
        )
        # Create a CuentaBancaria for linking statements
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa,
            nombre="Cuenta Corriente Test",
            banco="BANCOLOMBIA",
            tipo="CORRIENTE",
            numero="111222333",
        )

    def _create_mock_excel(self, data_rows):
        """Helper to create an Excel file in memory."""
        output = io.BytesIO()
        df = pd.DataFrame(data_rows)
        # Write to stream without headers to match parser logic (header=None)
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, header=False)
        output.seek(0)
        return SimpleUploadedFile(
            "extracto.xlsx",
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_create_extracto_via_service(self):
        """Test: Create a statement record via CRUD Service."""
        data = {
            "cuenta": self.cuenta,
            "mes": 5,
            "anio": 2026,
            "saldo_inicial": 10000.00,
            "saldo_final": 15000.00,
        }
        extracto = ExtractoBancarioCRUDService.crear_extracto(data, self.empresa)
        self.assertEqual(extracto.mes, 5)
        self.assertEqual(extracto.anio, 2026)
        self.assertFalse(extracto.procesado)

        # Check uniqueness constraint
        with self.assertRaises(ValidationError):
            ExtractoBancarioCRUDService.crear_extracto(data, self.empresa)

    def test_process_extracto_etl(self):
        """Test: Load and process Excel file into transactions."""
        # 1. Create extracto first
        extracto = ExtractoBancario.objects.create(
            empresa=self.empresa,
            cuenta=self.cuenta,
            mes=4,
            anio=2026,
            saldo_inicial=5000.00,
            saldo_final=8000.00,
        )

        # 2. Mock Excel content
        # Column 0: date pattern "d/m", description, sucursal, dcto, valor, saldo
        rows = [
            ["01/04", "CONSIGNACION", "BOGOTA", "12345", 5000.00, 10000.00],
            ["15/04", "RETIRO CAJERO", "MEDELLIN", "", -2000.00, 8000.00],
            ["NOT A DATE", "INFO ROW", "", "", 0.00, 0.00],
        ]
        excel_file = self._create_mock_excel(rows)
        extracto.archivo_s3 = excel_file
        extracto.save()

        # 3. Process
        count = ExtractoBancarioBusinessService.procesar_archivo_extracto(extracto)
        self.assertEqual(count, 2)

        # Verify database records
        txs = TransaccionBancaria.objects.filter(extracto=extracto).order_by("fecha")
        self.assertEqual(txs.count(), 2)

        tx1 = txs[0]
        self.assertEqual(tx1.fecha, datetime.date(2026, 4, 1))
        self.assertEqual(tx1.descripcion, "CONSIGNACION")
        self.assertEqual(tx1.valor, 5000.00)

        tx2 = txs[1]
        self.assertEqual(tx2.fecha, datetime.date(2026, 4, 15))
        self.assertEqual(tx2.valor, -2000.00)

        # Check idempotency: Re-processing the same extracto should not double transactions
        excel_file_2 = self._create_mock_excel(rows)
        extracto.archivo_s3 = excel_file_2
        extracto.save()

        count_2 = ExtractoBancarioBusinessService.procesar_archivo_extracto(extracto)
        self.assertEqual(count_2, 2)
        self.assertEqual(
            TransaccionBancaria.objects.filter(extracto=extracto).count(), 2
        )

    def test_process_invalid_excel(self):
        """Test: Processing invalid structure should raise validation error."""
        extracto = ExtractoBancario.objects.create(
            empresa=self.empresa,
            cuenta=self.cuenta,
            mes=4,
            anio=2026,
            saldo_inicial=5000.00,
            saldo_final=8000.00,
        )
        # Invalid shape: < 6 columns
        rows = [["01/04", "CONSIGNACION", "BOGOTA"]]
        excel_file = self._create_mock_excel(rows)
        extracto.archivo_s3 = excel_file
        extracto.save()

        with self.assertRaises(ValidationError):
            ExtractoBancarioBusinessService.procesar_archivo_extracto(extracto)

    def test_extracto_api_flow(self):
        """Test: End-to-end REST API CRUD and processing for ExtractoBancario."""
        list_url = reverse("bancos-extractos-list")

        # 1. CREATE via POST
        create_data = {
            "cuenta": str(self.cuenta.uuid),
            "mes": 6,
            "anio": 2026,
            "saldo_inicial": "12000.00",
            "saldo_final": "15000.00",
        }
        response = self.api_client.post(list_url, create_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        res_data = response.json()
        self.assertIn("uuid", res_data)
        extracto_uuid = res_data["uuid"]

        # 2. DETAIL
        detail_url = reverse("bancos-extractos-detail", kwargs={"uuid": extracto_uuid})
        response = self.api_client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["mes"], 6)

        # 3. ATTACH FILE AND PROCESS via POST to 'procesar' action
        extracto = ExtractoBancario.objects.get(uuid=extracto_uuid)
        rows = [
            ["10/06", "PAGO SERVICIOS", "ONLINE", "999", -3000.00, 9000.00],
        ]
        excel_file = self._create_mock_excel(rows)
        extracto.archivo_s3 = excel_file
        extracto.save()

        process_url = reverse(
            "bancos-extractos-procesar", kwargs={"uuid": extracto_uuid}
        )
        response = self.api_client.post(process_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify transaction ingested
        self.assertEqual(
            TransaccionBancaria.objects.filter(extracto=extracto).count(), 1
        )

        # 4. DELETE
        response = self.api_client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ExtractoBancario.objects.filter(uuid=extracto_uuid).exists())
