"""
Calculo del CUNE (Codigo Unico de Nomina Electronica) -- DSPNE.

################################################################################
# ADVERTENCIA -- FORMULA NO VERIFICADA CONTRA EL ANEXO TECNICO OFICIAL        #
################################################################################
Reconstruida con conocimiento publico general del "Anexo Tecnico Documento
Soporte de Pago de Nomina Electronica" (DIAN, Resolucion 000013 de 2021,
v1.0) -- mismo criterio de honestidad que
`apps/tenant/core/dian/adapters.py` (DIANAdapter) ya aplica: el ORDEN y
NOMBRE exacto de cada campo de la concatenacion, y si el algoritmo es
SHA-384 (igual que CUFE) o SHA-256, NO estan confirmados contra el PDF
oficial ni contra un caso de prueba DIAN real (no hay WSDL/sandbox
accesible desde este entorno, ver docs/nomina/NOMINA_DIAN_AUDIT.md §7).

NO USAR PARA TRANSMITIR A PRODUCCION sin, en este orden:
  1. Confirmar la formula exacta contra el Anexo Tecnico vigente a la
     fecha (los anexos DIAN cambian con resoluciones nuevas).
  2. Validar el CUNE calculado contra al menos un caso de prueba oficial
     de la DIAN (ambiente de habilitacion).

Formula implementada (mejor esfuerzo, misma estructura que CufeService --
ver apps/tenant/facturas/services/dian/cufe.py -- adaptada a los campos
propios de Nomina Electronica en vez de Factura Electronica):

  CUNE = SHA-384(
      NumNIE + FecNIE + HorNIE +
      ValDev + ValDed + ValPag +
      NitEmpleador + NumDocTrabajador +
      TipoXML + ClTec + TipAmb
  )

Donde:
  NumNIE            -- Numero del documento (prefijo + consecutivo)
  FecNIE            -- Fecha generacion AAAA-MM-DD
  HorNIE            -- Hora generacion HH:MM:SS-05:00
  ValDev            -- Valor total devengado (2 decimales, sin separadores)
  ValDed            -- Valor total deducciones (2 decimales)
  ValPag            -- Valor a pagar / neto (2 decimales)
  NitEmpleador      -- NIT de la empresa empleadora (sin DV)
  NumDocTrabajador  -- Numero de documento del trabajador
  TipoXML           -- "102" NominaIndividual | "103" NominaIndividualDeAjuste
  ClTec             -- Clave tecnica de la resolucion DIAN (ResolucionDIAN.clave_tecnica)
  TipAmb            -- "1" produccion, "2" habilitacion/pruebas
"""
import hashlib
from decimal import Decimal, ROUND_HALF_UP


class CuneService:
    """Calcula el CUNE con la formula reconstruida (ver advertencia del modulo)."""

    TWO_DEC = Decimal("0.01")

    @classmethod
    def _fmt(cls, valor) -> str:
        d = Decimal(str(valor)).quantize(cls.TWO_DEC, rounding=ROUND_HALF_UP)
        return str(d)

    @classmethod
    def calcular(
        cls,
        num_nie: str,
        fec_nie: str,
        hor_nie: str,
        val_dev,
        val_ded,
        val_pag,
        nit_empleador: str,
        num_doc_trabajador: str,
        cl_tec: str,
        tipo_xml: str = "102",
        tip_amb: str = "2",
    ) -> str:
        """Retorna el CUNE en hexadecimal (96 chars, SHA-384)."""
        partes = [
            str(num_nie),
            str(fec_nie),
            str(hor_nie),
            cls._fmt(val_dev),
            cls._fmt(val_ded),
            cls._fmt(val_pag),
            str(nit_empleador),
            str(num_doc_trabajador),
            str(tipo_xml),
            str(cl_tec or ""),
            str(tip_amb),
        ]
        cadena = "".join(partes)
        return hashlib.sha384(cadena.encode("utf-8")).hexdigest()
