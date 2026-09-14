"""
BankTransactionMatchingService (Fase 8-12, mision Bancos v3.0).

Motor de sugerencias: produce candidatos, nunca escribe datos ni
contabiliza en silencio. Un CREDITO (valor >= 0) busca Factura VENTA +
Cliente; un DEBITO busca Factura COMPRA + Proveedor + DocumentoSoporte
(Gasto).

Prioridad de matching (orden de la mision, Fase 8):
    1. referencia/documento bancario (dcto de la transaccion == numero de factura)
    2. NIT detectado en la descripcion
    3. nombre/razon social detectada en la descripcion
    4. numero de factura detectado en la descripcion
    5. monto (coincidencia exacta o cercana)
    6. proximidad de fecha
    7. texto de descripcion (fallback generico, ya cubierto por 2/3)

No asume que un monto igual es automaticamente la factura correcta -- el
score combina multiples señales, nunca una sola.
"""
import re
import unicodedata
from decimal import Decimal

_TOLERANCIA_MONTO_EXACTO = Decimal("0.01")
_TOLERANCIA_MONTO_CERCANO = Decimal("0.05")  # 5%
_MAX_CANDIDATOS = 8


def _normalizar(texto: str) -> str:
    texto = (texto or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _score_monto(monto_tx: Decimal, monto_doc: Decimal) -> tuple:
    if not monto_doc:
        return Decimal("0"), None
    diff = abs(monto_tx - monto_doc)
    if diff <= _TOLERANCIA_MONTO_EXACTO:
        return Decimal("0.40"), "monto coincide exactamente"
    pct = diff / monto_doc if monto_doc else Decimal("1")
    if pct <= _TOLERANCIA_MONTO_CERCANO:
        return Decimal("0.20"), "monto coincide aproximadamente (dentro de 5%)"
    return Decimal("0"), None


def _score_fecha(fecha_tx, fecha_doc) -> tuple:
    if not fecha_doc or not fecha_tx:
        return Decimal("0"), None
    delta = abs((fecha_tx - fecha_doc).days)
    if delta == 0:
        return Decimal("0.20"), "misma fecha"
    if delta <= 3:
        return Decimal("0.10"), "fecha cercana (<=3 dias)"
    if delta <= 15:
        return Decimal("0.05"), "fecha en el mismo periodo (<=15 dias)"
    return Decimal("0"), None


def _score_texto(descripcion_norm: str, nit: str, razon_social: str, numero_doc: str, dcto_tx: str):
    """Devuelve (score, [razones]) combinando señales 1-4 de la mision."""
    score = Decimal("0")
    razones = []

    if dcto_tx and numero_doc and _normalizar(dcto_tx) == _normalizar(numero_doc):
        score += Decimal("0.30")
        razones.append("documento bancario (dcto) coincide con el numero del documento")

    if nit:
        nit_norm = re.sub(r"\D", "", nit)
        if nit_norm and nit_norm in re.sub(r"\D", "", descripcion_norm):
            score += Decimal("0.30")
            razones.append(f"NIT {nit} detectado en la descripcion")

    if razon_social:
        palabras = [p for p in _normalizar(razon_social).split() if len(p) > 3]
        if palabras and any(p in descripcion_norm for p in palabras):
            score += Decimal("0.25")
            razones.append("nombre/razon social detectado en la descripcion")

    if numero_doc:
        numero_norm = _normalizar(str(numero_doc))
        if numero_norm and numero_norm in descripcion_norm:
            score += Decimal("0.20")
            razones.append("numero de documento detectado en la descripcion")

    return score, razones


class BankTransactionMatchingService:
    """Genera candidatos de aplicacion para una TransaccionBancaria. Solo
    lectura -- nunca escribe MovimientoBancarioAplicacion."""

    @staticmethod
    def sugerir(transaccion) -> list:
        descripcion_norm = _normalizar(transaccion.descripcion)
        candidatos = []

        if transaccion.valor >= 0:
            candidatos += BankTransactionMatchingService._sugerir_facturas(
                transaccion, descripcion_norm, naturaleza="VENTA"
            )
            candidatos += BankTransactionMatchingService._sugerir_clientes(transaccion, descripcion_norm)
        else:
            candidatos += BankTransactionMatchingService._sugerir_facturas(
                transaccion, descripcion_norm, naturaleza="COMPRA"
            )
            candidatos += BankTransactionMatchingService._sugerir_proveedores(transaccion, descripcion_norm)
            candidatos += BankTransactionMatchingService._sugerir_gastos(transaccion, descripcion_norm)

        candidatos.sort(key=lambda c: c["score"], reverse=True)
        return candidatos[:_MAX_CANDIDATOS]

    @staticmethod
    def _sugerir_facturas(transaccion, descripcion_norm, naturaleza):
        from apps.tenant.facturas.models import Factura

        monto_tx = abs(transaccion.valor)
        qs = (
            Factura.objects.filter(empresa_id=transaccion.empresa_id, naturaleza=naturaleza)
            .only("id", "uuid", "numero", "prefijo", "naturaleza", "total", "fecha_emision",
                  "receptor_nit", "receptor_razon_social", "emisor_nit", "emisor_razon_social")
            .order_by("-fecha_emision")[:200]
        )
        candidatos = []
        for factura in qs:
            total = factura.total or Decimal("0")
            if naturaleza == "VENTA":
                nit, nombre = factura.receptor_nit, factura.receptor_razon_social
            else:
                nit, nombre = factura.emisor_nit, factura.emisor_razon_social

            score_monto, razon_monto = _score_monto(monto_tx, total)
            if score_monto == 0:
                continue  # sin coincidencia minima de monto, no vale la pena sugerir

            fecha_doc = factura.fecha_emision.date() if hasattr(factura.fecha_emision, "date") else factura.fecha_emision
            score_fecha, razon_fecha = _score_fecha(transaccion.fecha, fecha_doc)
            score_texto, razones_texto = _score_texto(
                descripcion_norm, nit, nombre, factura.numero, transaccion.dcto
            )

            score = min(score_monto + score_fecha + score_texto, Decimal("0.99"))
            razones = [r for r in ([razon_monto, razon_fecha] + razones_texto) if r]
            candidatos.append({
                "tipo": "FACTURA_VENTA" if naturaleza == "VENTA" else "FACTURA_COMPRA",
                "uuid": str(factura.uuid),
                "descripcion": f"{factura.prefijo or ''}{factura.numero} — {nombre or '—'}",
                "monto": str(total),
                "score": float(score.quantize(Decimal("0.0001"))),
                "reason": razones,
            })
        return candidatos

    @staticmethod
    def _sugerir_clientes(transaccion, descripcion_norm):
        from apps.tenant.clientes.models import Cliente

        qs = (
            Cliente.objects.filter(empresa_id=transaccion.empresa_id, activo=True)
            .only("id", "uuid", "numero_documento", "razon_social", "nombre_comercial")[:300]
        )
        candidatos = []
        for cliente in qs:
            score, razones = _score_texto(
                descripcion_norm, cliente.numero_documento, cliente.razon_social, None, None
            )
            if cliente.nombre_comercial:
                palabras = [p for p in _normalizar(cliente.nombre_comercial).split() if len(p) > 3]
                if palabras and any(p in descripcion_norm for p in palabras) and "nombre/razon social" not in " ".join(razones):
                    score += Decimal("0.25")
                    razones.append("nombre comercial detectado en la descripcion")
            if score == 0:
                continue
            candidatos.append({
                "tipo": "CLIENTE",
                "uuid": str(cliente.uuid),
                "descripcion": cliente.nombre_comercial or cliente.razon_social,
                "monto": None,
                "score": float(min(score, Decimal("0.99")).quantize(Decimal("0.0001"))),
                "reason": razones,
            })
        return candidatos

    @staticmethod
    def _sugerir_proveedores(transaccion, descripcion_norm):
        from apps.tenant.proveedores.models import Proveedor

        qs = (
            Proveedor.objects.filter(empresa_id=transaccion.empresa_id, activo=True)
            .only("id", "uuid", "numero_documento", "razon_social", "nombre_comercial")[:300]
        )
        candidatos = []
        for proveedor in qs:
            score, razones = _score_texto(
                descripcion_norm, proveedor.numero_documento, proveedor.razon_social, None, None
            )
            if proveedor.nombre_comercial:
                palabras = [p for p in _normalizar(proveedor.nombre_comercial).split() if len(p) > 3]
                if palabras and any(p in descripcion_norm for p in palabras) and "nombre/razon social" not in " ".join(razones):
                    score += Decimal("0.25")
                    razones.append("nombre comercial detectado en la descripcion")
            if score == 0:
                continue
            candidatos.append({
                "tipo": "PROVEEDOR",
                "uuid": str(proveedor.uuid),
                "descripcion": proveedor.nombre_comercial or proveedor.razon_social,
                "monto": None,
                "score": float(min(score, Decimal("0.99")).quantize(Decimal("0.0001"))),
                "reason": razones,
            })
        return candidatos

    @staticmethod
    def _sugerir_gastos(transaccion, descripcion_norm):
        """DocumentoSoporte es el equivalente real de 'Gasto' en este
        proyecto (ver apps/tenant/gastos/models.py) -- no existe un modelo
        Gasto propiamente dicho."""
        try:
            from apps.tenant.gastos.models import DocumentoSoporte
        except ImportError:
            return []

        monto_tx = abs(transaccion.valor)
        qs = (
            DocumentoSoporte.objects.filter(empresa_id=transaccion.empresa_id)
            .select_related("proveedor")
            .only("id", "uuid", "subtotal", "fecha", "numero_documento_proveedor",
                  "proveedor__razon_social", "proveedor__numero_documento")[:200]
        )
        candidatos = []
        for doc in qs:
            score_monto, razon_monto = _score_monto(monto_tx, doc.subtotal or Decimal("0"))
            if score_monto == 0:
                continue
            score_fecha, razon_fecha = _score_fecha(transaccion.fecha, doc.fecha)
            nombre = doc.proveedor.razon_social if doc.proveedor_id else None
            nit = doc.proveedor.numero_documento if doc.proveedor_id else None
            score_texto, razones_texto = _score_texto(
                descripcion_norm, nit, nombre, doc.numero_documento_proveedor, transaccion.dcto
            )
            score = min(score_monto + score_fecha + score_texto, Decimal("0.99"))
            razones = [r for r in ([razon_monto, razon_fecha] + razones_texto) if r]
            candidatos.append({
                "tipo": "GASTO",
                "uuid": str(doc.uuid),
                "descripcion": f"Doc. soporte — {nombre or '—'}",
                "monto": str(doc.subtotal),
                "score": float(score.quantize(Decimal("0.0001"))),
                "reason": razones,
            })
        return candidatos
