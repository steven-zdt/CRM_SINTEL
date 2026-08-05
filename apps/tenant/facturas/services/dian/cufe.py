"""
Calculo del CUFE (Codigo Unico de Factura Electronica).

Ref: Anexo Tecnico FE DIAN v1.9 seccion 5.4.3.
Formula: SHA-384(
    NumFac + FecFac + HorFac +
    ValFac + CodImp1 + ValImp1 +
    CodImp2 + ValImp2 + CodImp3 + ValImp3 +
    ValTot + NitOFE + NumAdq +
    ClTecn + TipAmb
)

Donde:
  NumFac  -- Numero de la factura (prefijo + consecutivo)
  FecFac  -- Fecha emision AAAA-MM-DD
  HorFac  -- Hora emision HH:MM:SS-05:00
  ValFac  -- Valor total sin impuestos (2 decimales, sin puntos)
  CodImp1 -- "01" (IVA)
  ValImp1 -- Valor IVA (2 decimales)
  CodImp2 -- "04" (INC)
  ValImp2 -- Valor INC (2 decimales, 0.00 si no aplica)
  CodImp3 -- "03" (ICA)
  ValImp3 -- Valor ICA (2 decimales, 0.00 si no aplica)
  ValTot  -- Valor total con impuestos (2 decimales)
  NitOFE  -- NIT emisor (sin DV)
  NumAdq  -- Documento identidad receptor
  ClTecn  -- Clave tecnica (64 hex chars) de la resolucion DIAN
  TipAmb  -- "1" produccion, "2" habilitacion/pruebas
"""
import hashlib
from decimal import Decimal, ROUND_HALF_UP


class CufeService:
    """Calcula el CUFE segun la formula oficial DIAN."""

    TWO_DEC = Decimal("0.01")

    @classmethod
    def _fmt(cls, valor) -> str:
        """Redondea a 2 decimales y retorna string sin separadores de miles."""
        d = Decimal(str(valor)).quantize(cls.TWO_DEC, rounding=ROUND_HALF_UP)
        return str(d)

    @classmethod
    def calcular(
        cls,
        num_fac: str,
        fec_fac: str,
        hor_fac: str,
        val_fac,
        val_imp1,
        val_imp2,
        val_imp3,
        val_tot,
        nit_ofe: str,
        num_adq: str,
        cl_tecn: str,
        tip_amb: str,
    ) -> str:
        """
        Retorna el CUFE en hexadecimal (96 chars).

        val_fac  -- subtotal (sin impuestos)
        val_imp1 -- IVA (codigo 01)
        val_imp2 -- INC (codigo 04), puede ser 0
        val_imp3 -- ICA (codigo 03), puede ser 0
        val_tot  -- total con todos los impuestos
        cl_tecn  -- clave tecnica de 64 hex chars
        tip_amb  -- "2" pruebas, "1" produccion
        """
        partes = [
            str(num_fac),
            str(fec_fac),
            str(hor_fac),
            cls._fmt(val_fac),
            "01",
            cls._fmt(val_imp1),
            "04",
            cls._fmt(val_imp2),
            "03",
            cls._fmt(val_imp3),
            cls._fmt(val_tot),
            str(nit_ofe),
            str(num_adq),
            str(cl_tecn),
            str(tip_amb),
        ]
        cadena = "".join(partes)
        return hashlib.sha384(cadena.encode("utf-8")).hexdigest()

    @classmethod
    def calcular_desde_dto(cls, dto: dict) -> str:
        """
        Atajo que extrae los campos del DTO canonico construido por
        VentaBusinessService._construir_dto_factura() y calcula el CUFE.

        Espera en dto:
          num_fac, fec_fac, hor_fac
          totales.subtotal, totales.impuestos, totales.total
          emisor.nit, receptor.nit
          dian_software.cl_tecn  (o dian_software vacio -> usa settings)
          tip_amb
          impuestos_discriminados[] -> busca IVA (01), INC (04), ICA (03)
        """
        from django.conf import settings

        num_fac = dto["num_fac"]
        fec_fac = dto["fec_fac"]
        hor_fac = dto["hor_fac"]

        val_fac = Decimal(str(dto["totales"]["subtotal"]))
        val_tot = Decimal(str(dto["totales"]["total"]))

        # Distribuir impuestos por codigo DIAN
        val_iva = Decimal("0.00")
        val_inc = Decimal("0.00")
        val_ica = Decimal("0.00")
        for imp in dto.get("impuestos_discriminados", []):
            ts_id = imp.get("tax_scheme_id", "01")
            val = Decimal(str(imp.get("valor", "0")))
            if ts_id == "01":
                val_iva += val
            elif ts_id == "04":
                val_inc += val
            elif ts_id == "03":
                val_ica += val

        nit_ofe = dto["emisor"]["nit"]
        num_adq = dto["receptor"]["nit"]
        cl_tecn = (
            dto.get("dian_software", {}).get("cl_tecn")
            or getattr(settings, "DIAN_CL_TECN", "")
        )
        tip_amb = dto.get("tip_amb", getattr(settings, "DIAN_TIP_AMB", "2"))

        return cls.calcular(
            num_fac=num_fac,
            fec_fac=fec_fac,
            hor_fac=hor_fac,
            val_fac=val_fac,
            val_imp1=val_iva,
            val_imp2=val_inc,
            val_imp3=val_ica,
            val_tot=val_tot,
            nit_ofe=nit_ofe,
            num_adq=num_adq,
            cl_tecn=cl_tecn,
            tip_amb=tip_amb,
        )

    @classmethod
    def generar_qr_string(cls, cufe: str, dto: dict) -> str:
        """
        Genera la URL del QR DIAN.
        Formato: https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey=<CUFE>
        tip_amb "1" -> vpfe (produccion)
        tip_amb "2" -> vpfe-hab (habilitacion)
        """
        tip_amb = dto.get("tip_amb", "2")
        if tip_amb == "1":
            base = "https://catalogo-vpfe.dian.gov.co/document/searchqr"
        else:
            base = "https://catalogo-vpfe-hab.dian.gov.co/document/searchqr"
        return f"{base}?documentkey={cufe}"
