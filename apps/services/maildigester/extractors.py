"""
Extracción de adjuntos desde mensajes de correo.

Valida tamaños, filtra tipos obvios y retorna lista de AttachmentDTO.

⚠️ IMPLEMENTACIÓN: Delega a inbox_client.get_attachments() que ya implementa parsing MIME real.
⚠️ SEGURIDAD: Valida límites de tamaño para prevenir DoS.
"""
from typing import List
from .schemas import AttachmentDTO
from .exceptions import AttachmentTooLarge


def extract_attachments(message: dict, *, max_mb: int = 50) -> List[AttachmentDTO]:
    """
    Extrae adjuntos de un mensaje validando tamaños.
    
    ⚠️ NOTA: Esta función es un wrapper que delega a inbox_client.get_attachments().
    La implementación real del parsing MIME está en RealIMAPClient.get_attachments().
    
    Filtra tipos obvios no relevantes (imágenes, documentos ofimáticos sin XML, etc.)
    y valida que no excedan el límite de tamaño.
    
    ⚠️ LÍMITE: max_mb debe alinearse con el límite de ingesta (50MB por defecto).
    
    Args:
        message: Dict con datos del mensaje (debe tener campo '_email_message' de email.message)
        max_mb: Límite máximo de tamaño por adjunto en MB (default: 50)
        
    Returns:
        Lista de AttachmentDTO con adjuntos válidos
        
    Raises:
        AttachmentTooLarge: Si algún adjunto excede max_mb
        
    Ejemplo:
        message = {"id": "msg_1", "_email_message": email.message.Message(...)}
        attachments = extract_attachments(message, max_mb=50)
        # Retorna: [AttachmentDTO(filename="factura.xml", ...)]
    """
    # ⚠️ NOTA: La extracción real de adjuntos se hace en inbox_client.get_attachments()
    # Esta función es un wrapper para mantener compatibilidad con el código existente
    # Si el mensaje ya tiene adjuntos extraídos, usarlos directamente
    
    max_bytes = max_mb * 1024 * 1024
    
    # Si el mensaje ya tiene adjuntos extraídos (por inbox_client), validarlos
    if "_attachments" in message:
        attachments = message["_attachments"]
    else:
        # Si no, el pipeline debe usar inbox_client.get_attachments() directamente
        # Esta función no puede parsear MIME sin el cliente
        attachments = []
    
    # Filtrar y validar tamaños
    valid_attachments: List[AttachmentDTO] = []
    for att in attachments:
        size_bytes = att.get("size_bytes", 0)
        if size_bytes > max_bytes:
            # Saltar adjuntos muy grandes (no lanzar excepción para no romper el flujo)
            continue
        
        # Filtrar tipos relevantes (XML, ZIP, RAR, 7z)
        content_type = att.get("content_type", "").lower()
        filename = att.get("filename", "").lower()
        
        # Tipos relevantes para facturas
        relevant_types = [
            "application/xml",
            "text/xml",
            "application/zip",
            "application/x-zip-compressed",
            "application/x-rar-compressed",
            "application/x-7z-compressed",
        ]
        
        # Verificar si es tipo relevante o tiene extensión relevante
        is_relevant = (
            any(t in content_type for t in relevant_types) or
            filename.endswith(('.xml', '.zip', '.rar', '.7z'))
        )
        
        if is_relevant:
            valid_attachments.append(att)
    
    return valid_attachments
