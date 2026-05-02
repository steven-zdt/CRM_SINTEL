"""
Utilidades para descomprimir archivos (ZIP/RAR/7z).

Detecta tipos de archivo comprimido y los expande en listas de archivos individuales.

WARNING: FASE 1: Solo stubs y validaciones de seguridad, sin dependencias externas.
WARNING: SEGURIDAD: Prevención de path traversal, validación de tamaños, límite de archivos.
"""

from .exceptions import ArchiveExpansionError, PathTraversalError
from .schemas import ExtractedFileDTO


def is_supported_archive(filename: str, content_type: str) -> bool:
    """
    Detecta si un archivo es un formato de compresión soportado.
    
    Formatos soportados: ZIP, RAR, 7z
    
    Args:
        filename: Nombre del archivo
        content_type: Content-Type MIME declarado
        
    Returns:
        True si el archivo parece ser un archivo comprimido soportado
        
    Ejemplo:
        is_supported_archive("facturas.zip", "application/zip")  # True
        is_supported_archive("documento.pdf", "application/pdf")  # False
    """
    # Detección por extensión
    filename_lower = filename.lower()
    if filename_lower.endswith(('.zip', '.rar', '.7z')):
        return True
    
    # Detección por content-type
    content_type_lower = content_type.lower()
    if any(t in content_type_lower for t in ['zip', 'rar', '7z', 'x-7z-compressed']):
        return True
    
    return False


def expand_archive(file: ExtractedFileDTO) -> list[ExtractedFileDTO]:
    """
    Descomprime un archivo y retorna lista de archivos extraídos.
    
    WARNING: SEGURIDAD CRÍTICA:
    - Rechaza rutas con '..' (path traversal)
    - Rechaza rutas absolutas
    - Normaliza rutas relativas
    - Limita número máximo de archivos extraídos (p. ej., 100)
    - Valida tamaños individuales
    
    WARNING: FASE 1: STUB - Solo validaciones de seguridad básicas.
    TODO FASE 2: Implementar descompresión real con zipfile, rarfile, py7zr
    
    Args:
        file: ExtractedFileDTO con el archivo comprimido
        
    Returns:
        Lista de ExtractedFileDTO con archivos descomprimidos
        
    Raises:
        ArchiveExpansionError: Si el archivo está corrupto o no se puede descomprimir
        PathTraversalError: Si se detecta intento de path traversal
        
    Ejemplo:
        zip_file = ExtractedFileDTO(
            filename="facturas.zip",
            guessed_type="zip",
            size_bytes=1024,
            content=b"PK\x03\x04..."
        )
        files = expand_archive(zip_file)
        # Retorna: [ExtractedFileDTO(filename="FAC-123.xml", ...), ...]
    """
    # WARNING: SEGURIDAD: Validar nombre de archivo antes de procesar
    filename = file.get("filename", "")
    
    # Rechazar path traversal
    if ".." in filename or filename.startswith("/"):
        raise PathTraversalError(
            f"Nombre de archivo rechazado por seguridad: '{filename}'. "
            "No se permiten rutas relativas con '..' ni rutas absolutas."
        )
    
    # Normalizar ruta (eliminar ./ y normalizar separadores)
    import os
    normalized = os.path.normpath(filename).replace("\\", "/")
    if normalized.startswith("/") or ".." in normalized:
        raise PathTraversalError(f"Ruta normalizada rechazada: '{normalized}'")
    
    # WARNING: SEGURIDAD: Límites de seguridad
    MAX_FILES = 100  # Máximo de archivos a extraer
    MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB total descomprimido
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB por archivo individual
    
    content = file.get("content", b"")
    file_type = file.get("guessed_type", "unknown")
    
    extracted_files: list[ExtractedFileDTO] = []
    total_size = 0
    
    try:
        if file_type == "zip":
            import io
            import zipfile
            
            # Abrir ZIP desde bytes
            zip_buffer = io.BytesIO(content)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                # Validar número de archivos
                file_list = zip_ref.namelist()
                if len(file_list) > MAX_FILES:
                    raise ArchiveExpansionError(
                        f"El archivo ZIP contiene demasiados archivos ({len(file_list)} > {MAX_FILES})"
                    )
                
                # Extraer cada archivo
                for member_name in file_list:
                    # WARNING: SEGURIDAD: Validar nombre de archivo (path traversal)
                    if ".." in member_name or member_name.startswith("/"):
                        continue  # Saltar archivos con path traversal
                    
                    # Normalizar ruta
                    normalized = os.path.normpath(member_name).replace("\\", "/")
                    if normalized.startswith("/") or ".." in normalized:
                        continue  # Saltar rutas normalizadas inválidas
                    
                    try:
                        # Obtener información del archivo
                        member_info = zip_ref.getinfo(member_name)
                        
                        # Validar tamaño individual
                        if member_info.file_size > MAX_FILE_SIZE:
                            continue  # Saltar archivos muy grandes
                        
                        # Validar tamaño total acumulado
                        if total_size + member_info.file_size > MAX_TOTAL_SIZE:
                            raise ArchiveExpansionError(
                                f"El tamaño total descomprimido excedería el límite ({MAX_TOTAL_SIZE / 1024 / 1024}MB)"
                            )
                        
                        # Extraer contenido
                        file_content = zip_ref.read(member_name)
                        total_size += len(file_content)
                        
                        # Adivinar tipo del archivo extraído
                        from .detectors import guess_file_kind
                        guessed_type = guess_file_kind(normalized, "", file_content[:1024])
                        
                        extracted_files.append(ExtractedFileDTO(
                            filename=normalized,
                            guessed_type=guessed_type,
                            size_bytes=len(file_content),
                            content=file_content
                        ))
                    except Exception:
                        # Continuar con otros archivos si uno falla
                        continue
        
        elif file_type == "rar":
            # WARNING: RAR requiere rarfile que a su vez requiere unrar
            # Por ahora, lanzar error indicando que no está soportado
            raise ArchiveExpansionError(
                "Descompresión de archivos RAR no está implementada. "
                "Requiere la librería 'rarfile' y el binario 'unrar'."
            )
        
        elif file_type == "7z":
            # WARNING: 7z requiere py7zr
            # Por ahora, lanzar error indicando que no está soportado
            raise ArchiveExpansionError(
                "Descompresión de archivos 7z no está implementada. "
                "Requiere la librería 'py7zr'."
            )
        
        else:
            raise ArchiveExpansionError(f"Tipo de archivo comprimido no soportado: {file_type}")
    
    except zipfile.BadZipFile:
        raise ArchiveExpansionError("El archivo ZIP está corrupto o no es válido")
    except Exception as e:
        if isinstance(e, ArchiveExpansionError):
            raise
        raise ArchiveExpansionError(f"Error al descomprimir archivo: {str(e)}")
    
    return extracted_files
