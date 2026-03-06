"""
Document Parser Service Layer (Low-level parsing/normalization).

⚠️ PRINCIPIOS:
- Única fuente de verdad para parsing de documentos (XML, PDF, XLS/XLSX, CSV, TXT)
- Agnóstico del dominio: no conoce modelos Django
- Reutilizable: puede ser usado por cualquier app que necesite parsear documentos
- Extensible: permite agregar nuevos tipos sin tocar la orquestación principal
- ⚠️ v2.40: Separado por app (facturas, cotizaciones) con parsers independientes

Estructura (v2.40):
- dto.py: DTO unificado JSON (genérico)
- normalizers.py: Normalización UTF-8, limpieza de texto (genérico)
- detector.py: Detección de tipo de documento
- facturas/: Parsers específicos para facturas (PDF, Excel)
- cotizaciones/: Parsers específicos para cotizaciones (Excel para catálogos)
- xml_parser/: Parsers genéricos para XML (UBL 2.1, etc.)
- pdf_parser/: Parsers genéricos para PDF (fallback)
- excel_parser/: Parsers genéricos para Excel (fallback)
- csv_parser/: Parsers genéricos para CSV
- txt_parser/: Parsers genéricos para texto plano
- register_parsers.py: Registro automático de parsers por app
"""

# ⚠️ v2.40: Registrar automáticamente los parsers de cada app
try:
    from . import register_parsers  # noqa: F401
except ImportError:
    # Si hay un error al importar, continuar sin registro automático
    pass
