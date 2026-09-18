"""
Servicio de Documentos de Proyecto (Ciclo de Vida Controlado v4.0)

Service Layer para el expediente documental (DocumentoProyecto): catalogo de
tipos, resolucion de requisitos por transicion de fase (gates), validacion de
archivo (extension + tamano + firma binaria real, sin dependencias externas),
y CRUD con reemplazo automatico para tipos de "unico vigente".

Patron: CRUD Service + Business Service, igual que tareas_service.py /
presupuesto_service.py de este mismo modulo.
"""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from ..models import DocumentoProyecto

TipoDocumento = DocumentoProyecto.TipoDocumento


# ==============================================================================
# SSoT: DOCUMENTO_FIELDS para Zero Waste (LIST/DETAIL)
# ==============================================================================

DOCUMENTO_FIELDS = [
    'id', 'uuid', 'proyecto_id', 'empresa_id', 'fase', 'tipo_documento',
    'nombre', 'archivo', 'fecha_documento', 'observaciones', 'subido_por_id',
    'activo', 'created_at', 'updated_at',
]


# ==============================================================================
# CHECKLIST DOCUMENTAL POR TRANSICION (informativo, NO bloqueante)
# ==============================================================================
# Decision de producto (2026-09-18): estos documentos son RECOMENDADOS, no
# obligatorios. Antes eran un gate duro que abortaba `cambiar_fase_proyecto`
# con 400 -- un proyecto real quedaba atascado en su fase por no tener un
# papel cargado, bloqueando el flujo operativo completo. Ahora el checklist
# se sigue calculando y exponiendo igual (`requisitos_siguiente_fase` en el
# serializer, para que la UI muestre que falta), pero NUNCA impide avanzar.
#
# Para reactivar el bloqueo de un requisito puntual en el futuro, marcar ese
# item con 'obligatorio': True y restaurar la verificacion en
# business_service.cambiar_fase_proyecto() -- hoy ninguno lo esta.

REQUISITOS_TRANSICION = {
    ('BORRADOR', 'INICIO'): [],  # solo datos basicos del proyecto
    ('INICIO', 'PLANEACION'): [
        {'tipos': (TipoDocumento.ORDEN_COMPRA, TipoDocumento.ORDEN_PEDIDO),
         'label': 'Orden de Compra / Orden de Pedido'},
        {'tipos': (TipoDocumento.AUTORIZACION,), 'label': 'Autorizacion'},
        {'tipos': (TipoDocumento.COTIZACION_APROBADA,), 'label': 'Cotizacion aprobada'},
    ],
    ('PLANEACION', 'EJECUCION'): [
        {'tipos': (TipoDocumento.ACTA_INICIO,), 'label': 'Acta de inicio'},
        {'tipos': (TipoDocumento.CRONOGRAMA,), 'label': 'Cronograma'},
    ],
    ('EJECUCION', 'CIERRE'): [
        {'tipos': (TipoDocumento.ACTA_ENTREGA,), 'label': 'Acta de entrega'},
        {'tipos': (TipoDocumento.INFORME_FINAL,), 'label': 'Informe final'},
    ],
}


def resolver_requisitos_transicion(proyecto, fase_actual, nueva_fase):
    """
    Resuelve el checklist de documentos recomendados para una transicion de
    fase puntual. Lo consume el frontend (serializer:
    `requisitos_siguiente_fase`) para mostrar que documentos faltan.

    `obligatorio` viaja explicito en cada item para que la UI pueda rotularlos
    como opcionales y no como un bloqueo -- hoy siempre False.

    Returns:
        list[dict]: [{"label": str, "cumplido": bool, "obligatorio": bool}, ...]
    """
    requisitos = REQUISITOS_TRANSICION.get((fase_actual, nueva_fase), [])
    resultado = []
    for requisito in requisitos:
        cumplido = DocumentoProyecto.objects.filter(
            proyecto=proyecto,
            empresa_id=proyecto.empresa_id,
            tipo_documento__in=requisito['tipos'],
            activo=True,
        ).exists()
        resultado.append({
            'label': requisito['label'],
            'cumplido': cumplido,
            'obligatorio': requisito.get('obligatorio', False),
        })
    return resultado


def documentos_faltantes(proyecto, fase_actual, nueva_fase):
    """
    Labels de los documentos recomendados aun NO cargados. Informativo: lo usa
    la UI para el checklist. NO bloquea el avance de fase (ver nota de
    REQUISITOS_TRANSICION arriba).
    """
    return [
        r['label'] for r in resolver_requisitos_transicion(proyecto, fase_actual, nueva_fase)
        if not r['cumplido']
    ]


def documentos_obligatorios_faltantes(proyecto, fase_actual, nueva_fase):
    """
    Subconjunto de `documentos_faltantes` marcado explicitamente como
    obligatorio. Hoy siempre vacio (todos los documentos son opcionales) --
    es el unico punto que puede bloquear una transicion, si en el futuro se
    marca algun requisito con 'obligatorio': True.
    """
    return [
        r['label'] for r in resolver_requisitos_transicion(proyecto, fase_actual, nueva_fase)
        if not r['cumplido'] and r['obligatorio']
    ]


# ==============================================================================
# VALIDACION DE ARCHIVO (sin dependencias externas)
# ==============================================================================

EXTENSIONES_PERMITIDAS = ('.pdf', '.xls', '.xlsx')
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10MB

# Firmas binarias (magic bytes) reales por extension. Django advierte
# explicitamente que validar solo la extension no demuestra el tipo real del
# contenido -- esto se resuelve leyendo los primeros bytes, sin agregar
# ninguna dependencia nueva (python-magic, filetype, etc.).
_FIRMAS_BINARIAS = {
    '.pdf': (b'%PDF-',),
    '.xlsx': (b'PK\x03\x04',),
    '.xls': (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',),
}


def validar_archivo(uploaded_file):
    """
    Valida un archivo subido para el expediente documental.

    1. Extension permitida (.pdf, .xls, .xlsx)
    2. Tamano maximo (10MB)
    3. Firma binaria (magic bytes) real, coherente con la extension declarada

    Raises:
        ValidationError si el archivo no pasa alguna validacion.
    """
    nombre = (uploaded_file.name or '').lower()
    extension = next((ext for ext in EXTENSIONES_PERMITIDAS if nombre.endswith(ext)), None)
    if extension is None:
        raise ValidationError({
            'archivo': f'Extension no permitida. Solo se aceptan: {", ".join(EXTENSIONES_PERMITIDAS)}.'
        })

    if uploaded_file.size > TAMANO_MAXIMO_BYTES:
        raise ValidationError({
            'archivo': f'El archivo excede el tamano maximo permitido ({TAMANO_MAXIMO_BYTES // (1024 * 1024)}MB).'
        })

    firmas_validas = _FIRMAS_BINARIAS.get(extension, ())
    uploaded_file.seek(0)
    cabecera = uploaded_file.read(8)
    uploaded_file.seek(0)
    if firmas_validas and not any(cabecera.startswith(firma) for firma in firmas_validas):
        raise ValidationError({
            'archivo': 'El contenido del archivo no corresponde a su extension declarada.'
        })


# ==============================================================================
# CRUD SERVICE - Persistencia
# ==============================================================================

class DocumentosCRUDService:
    """
    Persistencia de DocumentoProyecto.
    Metodos transaccionales @transaction.atomic.
    """

    @staticmethod
    @transaction.atomic
    def save_documento(documento, update_fields=None):
        """Guarda un DocumentoProyecto."""
        documento.save(update_fields=update_fields)
        return documento


# ==============================================================================
# BUSINESS SERVICE - Logica de Negocio
# ==============================================================================

class DocumentosBusinessService:
    """
    Logica de negocio del expediente documental:
    - DSV (empresa_id se deriva SIEMPRE de proyecto.empresa_id, nunca de un
      parametro externo, para que no exista forma de inyectar un mismatch)
    - Validacion de archivo
    - Reemplazo automatico para tipos de "unico vigente": nunca duplica
      silenciosamente el requisito de un gate (Fase 41/42)
    """

    @staticmethod
    def _validar_tipo_documento(tipo_documento):
        if tipo_documento not in dict(DocumentoProyecto.TipoDocumento.choices):
            raise ValidationError({'tipo_documento': f'Tipo de documento invalido: {tipo_documento}'})

    @staticmethod
    @transaction.atomic
    def crear_documento(proyecto, tipo_documento, archivo, fase=None, fecha_documento=None,
                         observaciones='', subido_por=None, nombre=''):
        """
        Crea un nuevo DocumentoProyecto. Si el tipo es de "unico vigente"
        (todos salvo DOCUMENTO_EJECUCION), desactiva cualquier documento
        activo previo del mismo tipo en la misma transaccion -- conserva el
        archivo viejo (soft), nunca dos documentos activos del mismo tipo
        gated simultaneamente.
        """
        DocumentosBusinessService._validar_tipo_documento(tipo_documento)
        validar_archivo(archivo)

        if tipo_documento not in DocumentoProyecto.TIPOS_MULTIPLES:
            DocumentoProyecto.objects.filter(
                proyecto=proyecto,
                empresa_id=proyecto.empresa_id,
                tipo_documento=tipo_documento,
                activo=True,
            ).update(activo=False)

        documento = DocumentoProyecto(
            proyecto=proyecto,
            empresa_id=proyecto.empresa_id,
            fase=fase or proyecto.fase_actual,
            tipo_documento=tipo_documento,
            nombre=nombre or getattr(archivo, 'name', ''),
            archivo=archivo,
            fecha_documento=fecha_documento,
            observaciones=observaciones,
            subido_por=subido_por,
        )
        DocumentosCRUDService.save_documento(documento)
        return documento

    @staticmethod
    @transaction.atomic
    def desactivar_documento(documento):
        """Soft-delete: nunca borra el archivo fisico del storage privado."""
        documento.activo = False
        DocumentosCRUDService.save_documento(documento, update_fields=['activo', 'updated_at'])
        return documento

    @staticmethod
    def listar_documentos(proyecto, tipo_documento=None, solo_activos=True):
        qs = DocumentoProyecto.objects.filter(
            proyecto=proyecto,
            empresa_id=proyecto.empresa_id,
        ).only(*DOCUMENTO_FIELDS)
        if solo_activos:
            qs = qs.filter(activo=True)
        if tipo_documento:
            qs = qs.filter(tipo_documento=tipo_documento)
        return qs.order_by('-created_at')

    @staticmethod
    def obtener_documento(proyecto, documento_uuid):
        """
        Resuelve un documento verificando pertenencia DOBLE: al proyecto de
        la URL y a la empresa de ese proyecto (DSV). Devuelve None si el
        UUID existe pero pertenece a otro proyecto/tenant -- el caller debe
        traducir eso a 404, nunca a 403 (no confirmar existencia cruzada).
        """
        return DocumentoProyecto.objects.filter(
            proyecto=proyecto,
            empresa_id=proyecto.empresa_id,
            uuid=documento_uuid,
        ).first()
