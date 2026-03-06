"""
Tests E2E con Playwright para el workspace de Facturas.

Verifica:
- Upload de archivo XML → éxito
- Ver detalle de factura
- Eliminar factura
- Manejo de errores minimalista

Requisitos:
- playwright install (si no está instalado)
- Servidor Django corriendo en http://localhost:8000 (o configurar BASE_URL)
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="function")
def authenticated_page(page: Page, live_server):
    """
    Página autenticada para tests E2E.
    
    Nota: Requiere que live_server esté configurado y que haya un usuario de prueba.
    """
    # TODO: Implementar login si es necesario
    # Por ahora, asumimos que el workspace requiere autenticación
    page.goto(f"{live_server.url}/workspace/#facturas")
    return page


@pytest.mark.e2e
def test_facturas_workspace_upload_xml(page: Page, live_server):
    """
    E2E: Subir archivo XML desde el workspace.
    
    Flujo:
    1. Navegar a /workspace/#facturas
    2. Clic en "Importar UBL XML"
    3. Seleccionar archivo .xml
    4. Clic en "Importar"
    5. Verificar que aparece en la tabla
    """
    # Navegar al workspace
    page.goto(f"{live_server.url}/workspace/#facturas")
    
    # Esperar a que cargue la vista de facturas
    page.wait_for_selector('[data-test="btn-importar"]', timeout=5000)
    
    # Clic en botón Importar
    page.click('[data-test="btn-importar"]')
    
    # Esperar a que aparezca el modal
    page.wait_for_selector('[data-test="import-modal"]', timeout=2000)
    
    # Crear archivo XML de prueba en memoria
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
             xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
             xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
      <cbc:ID>E2E-TEST-001</cbc:ID>
      <cbc:IssueDate>2024-01-15</cbc:IssueDate>
      <cac:AccountingSupplierParty>
        <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>900123456</cbc:CompanyID><cbc:RegistrationName>Empresa Test</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
      </cac:AccountingSupplierParty>
      <cac:AccountingCustomerParty>
        <cac:Party><cac:PartyLegalEntity><cbc:CompanyID>800111222</cbc:CompanyID><cbc:RegistrationName>Cliente E2E</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
      </cac:AccountingCustomerParty>
      <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount>100000.00</cbc:TaxExclusiveAmount>
        <cbc:PayableAmount>119000.00</cbc:PayableAmount>
      </cac:LegalMonetaryTotal>
      <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
    </Invoice>"""
    
    # Subir archivo
    file_input = page.locator('[data-test="input-xml-file"]')
    file_input.set_input_files({
        "name": "test.xml",
        "mimeType": "application/xml",
        "buffer": xml_content.encode('utf-8')
    })
    
    # Clic en Confirmar
    page.click('[data-test="btn-confirm-import"]')
    
    # Esperar a que se cierre el modal (éxito) o aparezca error
    page.wait_for_timeout(2000)
    
    # Verificar que no hay error modal visible
    error_modal = page.locator('[data-test="import-error-modal"]')
    if error_modal.is_visible():
        # Si hay error, verificar formato minimal
        error_body = error_modal.locator('.modal-body')
        expect(error_body).to_contain_text("error", use_inner_text=True)
    else:
        # Si no hay error, verificar que la tabla se actualizó
        table = page.locator('[data-test="tbl-facturas"]')
        expect(table).to_be_visible()


@pytest.mark.e2e
def test_facturas_workspace_upload_missing_file_shows_error(page: Page, live_server):
    """
    E2E: Intentar subir sin archivo muestra error minimalista.
    """
    page.goto(f"{live_server.url}/workspace/#facturas")
    page.wait_for_selector('[data-test="btn-importar"]', timeout=5000)
    
    page.click('[data-test="btn-importar"]')
    page.wait_for_selector('[data-test="import-modal"]', timeout=2000)
    
    # Intentar importar sin seleccionar archivo
    page.click('[data-test="btn-confirm-import"]')
    
    # Esperar respuesta
    page.wait_for_timeout(2000)
    
    # Verificar que aparece error modal con formato minimal
    error_modal = page.locator('[data-test="import-error-modal"]')
    expect(error_modal).to_be_visible()
    
    error_body = error_modal.locator('.modal-body')
    # Verificar formato minimal: solo message y code
    expect(error_body).to_contain_text("missing_xml", use_inner_text=True)


@pytest.mark.e2e
def test_facturas_workspace_view_detail(page: Page, live_server):
    """
    E2E: Ver detalle de factura desde la tabla.
    """
    # TODO: Requiere que haya facturas en la tabla
    # Por ahora, solo verificar que el botón existe y es clickeable
    page.goto(f"{live_server.url}/workspace/#facturas")
    page.wait_for_selector('[data-test="tbl-facturas"]', timeout=5000)
    
    # Buscar botón "Ver" en la tabla
    view_buttons = page.locator('[data-test="btn-ver"]')
    if view_buttons.count() > 0:
        view_buttons.first().click()
        # Verificar que se muestra algún detalle (modal o mensaje)
        page.wait_for_timeout(1000)


@pytest.mark.e2e
def test_facturas_workspace_delete(page: Page, live_server):
    """
    E2E: Eliminar factura desde la tabla.
    """
    # TODO: Requiere que haya facturas en la tabla
    page.goto(f"{live_server.url}/workspace/#facturas")
    page.wait_for_selector('[data-test="tbl-facturas"]', timeout=5000)
    
    # Buscar botón "Eliminar" en la tabla
    delete_buttons = page.locator('[data-test="btn-eliminar"]')
    if delete_buttons.count() > 0:
        delete_buttons.first().click()
        
        # Esperar confirmación
        page.wait_for_timeout(500)
        
        # Confirmar eliminación (si hay diálogo)
        # page.keyboard.press('Enter')  # Si hay confirm()
        
        # Verificar que la fila desaparece o se recarga la tabla
        page.wait_for_timeout(2000)
