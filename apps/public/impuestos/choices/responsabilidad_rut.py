# apps/public/impuestos/choices/responsabilidad_rut.py
# -*- coding: utf-8 -*-
"""
Choices para el campo 'codigo' del modelo ResponsabilidadRUT.
Basado en el listado de responsabilidades RUT (DIAN). Ver:
- Portal DIAN (fuente oficial, páginas dinámicas).  # cite: turn15search28
- Compilaciones públicas de códigos de responsabilidad.          # cite: turn15search19 turn15search21

Si la DIAN emite cambios, actualizar este archivo (SSoT local de choices).
"""

from __future__ import annotations

from typing import List, Tuple

RESPONSABILIDAD_RUT_CHOICES: List[Tuple[str, str]] = [
    ("01", "Aporte especial para la administración de justicia"),
    ("02", "Gravamen a los movimientos financieros"),
    ("03", "Impuesto al patrimonio"),
    ("04", "Impuesto sobre la renta y complementario – Régimen especial"),
    ("05", "Impuesto sobre la renta y complementario – Régimen ordinario"),
    ("06", "Ingresos y patrimonio"),
    ("07", "Retención en la fuente a título de renta"),
    ("08", "Retención – Timbre nacional"),
    ("09", "Retención en la fuente en el impuesto sobre las ventas"),
    ("10", "Obligado/usuario aduanero"),
    ("13", "Gran contribuyente"),
    ("14", "Informante de exógena"),
    ("15", "Autorretenedor"),
    ("16", "Obligación de facturar por ingresos de bienes y/o servicios excluidos"),
    ("17", "Profesionales de compra y venta de divisas"),
    ("18", "Precios de transferencia"),
    ("19", "Productor y/o exportador de bienes exentos"),
    ("20", "Obtención de NIT"),
    ("21", "Declarar ingreso o salida del país de divisas o moneda"),
    ("22", "Obligado a cumplir deberes formales a nombre de terceros"),
    ("23", "Agente de retención en el impuesto sobre las ventas"),
    # En algunos listados aparecen 24/26 separados; priorizamos 26 (Declaración Informativa Individual PT).
    ("26", "Declaración Informativa Individual de Precios de Transferencia"),
    ("32", "Impuesto Nacional a la Gasolina y al ACPM"),
    ("33", "Impuesto Nacional al Consumo"),
    ("36", "Establecimiento Permanente"),
    ("37", "Obligado a facturar electrónicamente"),
    ("38", "Facturación electrónica voluntaria"),
    ("39", "Proveedor de Servicios Tecnológicos – PST"),
    ("41", "Declaración anual de activos en el exterior"),
    ("42", "Obligado a llevar contabilidad"),
    ("45", "Autorretenedor de rendimientos financieros"),
    ("46", "IVA – Prestadores de servicios desde el exterior"),
    ("47", "Régimen Simple de Tributación – SIMPLE"),
    ("48", "Impuesto sobre las ventas – IVA"),
    ("49", "No responsable de IVA"),
    ("50", "No responsable de consumo – restaurantes y bares"),
    ("51", "Agente de retención del impoconsumo de bienes inmuebles"),
    ("52", "Facturador electrónico"),
    ("53", "Persona jurídica – No responsable de IVA"),
    ("54", "Intercambio Automático de Información – CRS"),
    ("55", "Informante de beneficiarios finales"),
    ("56", "Impuesto al carbono"),
]

def get_responsabilidad_rut_choices() -> List[Tuple[str, str]]:
    """
    Provee los choices en runtime por si se prefiere inyectarlos
    dinámicamente en serializers/forms (recomendado).
    """
    return RESPONSABILIDAD_RUT_CHOICES[:]