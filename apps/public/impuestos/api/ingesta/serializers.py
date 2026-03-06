"""
Serializers para la API de Ingesta.

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
import hashlib
import os
from rest_framework import serializers
from apps.public.impuestos.models import DocumentoFuente, IngestaLog


ALLOWED_EXTS = {
    ".pdf": "PDF",
    ".xlsx": "XLS",
    ".xls": "XLS",
    ".csv": "CSV",
    ".html": "HTML",
    ".htm": "HTML",
}
MAX_SIZE_MB = 50


class DocumentoFuenteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear DocumentoFuente.
    
    Valida mutua exclusión: archivo XOR url_origen.
    Normaliza fuente y precalcula hash_sha256 si archivo presente.
    """
    FUENTE_CHOICES = [
        "DIAN",
        "DOF",
        "SUIN",
        "DiarioOficial",
        "OTRO",
    ]
    
    class Meta:
        model = DocumentoFuente
        fields = [
            "archivo",
            "url_origen",
            "fuente",
            "fecha_publicacion",
        ]
    
    def validate(self, attrs):
        """Validar mutua exclusión: archivo XOR url_origen y validar tipos/tamaño."""
        file = self.initial_data.get("archivo")
        url = self.initial_data.get("url_origen")
        
        if not file and not url:
            raise serializers.ValidationError(
                "Debes proporcionar un archivo o una URL."
            )
        
        if file and url:
            raise serializers.ValidationError(
                "Proporciona archivo o URL, no ambos."
            )
        
        # Validar archivo si está presente
        if file:
            f = file if hasattr(file, "name") else None
            if not f:
                raise serializers.ValidationError("Archivo inválido.")
            
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXTS:
                raise serializers.ValidationError(
                    "Extensión no permitida. Usa PDF, XLSX/XLS, CSV o HTML."
                )
            
            size_mb = f.size / (1024 * 1024)
            if size_mb > MAX_SIZE_MB:
                raise serializers.ValidationError(
                    f"El archivo supera {MAX_SIZE_MB}MB."
                )
        
        return attrs
    
    def validate_fuente(self, value):
        """Normalizar fuente (opcional: validar contra choices)."""
        if value:
            value = value.upper().strip()
        return value
    
    def create(self, validated_data):
        """Crear DocumentoFuente y precalcular hash/metadatos si archivo presente."""
        archivo = validated_data.get("archivo")
        
        # Si hay archivo, calcular metadatos
        if archivo:
            archivo.seek(0)  # Resetear posición del archivo
            
            # Calcular hash
            hash_obj = hashlib.sha256()
            for chunk in archivo.chunks():
                hash_obj.update(chunk)
            hash_sha256 = hash_obj.hexdigest()
            validated_data["hash_sha256"] = hash_sha256
            
            # Idempotencia: verificar si ya existe otro documento con el mismo hash
            duplicate = DocumentoFuente.objects.filter(hash_sha256=hash_sha256).first()
            if duplicate:
                # No crear duplicado, pero permitir que el usuario vea el existente
                # En producción, podrías retornar el existente o lanzar ValidationError
                # Por ahora, creamos la instancia pero marcamos como duplicada
                pass  # Se manejará después del create
            
            # Detectar extensión y tipo
            ext = os.path.splitext(archivo.name)[1].lower()
            validated_data["extension"] = ext
            validated_data["tipo"] = ALLOWED_EXTS.get(ext, "OTRO")
            validated_data["size_bytes"] = archivo.size
            
            # Content type (si está disponible en el request)
            if hasattr(archivo, "content_type"):
                validated_data["content_type"] = archivo.content_type or ""
            
            archivo.seek(0)  # Resetear nuevamente para guardar
        
        instance = super().create(validated_data)
        
        # Verificar idempotencia después de crear (para evitar race conditions)
        if archivo and instance.hash_sha256:
            duplicate = DocumentoFuente.objects.exclude(pk=instance.pk).filter(hash_sha256=instance.hash_sha256).first()
            if duplicate:
                # Marcar como procesado sin ejecutar ETL
                instance.estado = "PROCESADO"
                instance.save(update_fields=["estado"])
                # Log de duplicado
                from apps.public.impuestos.models import IngestaLog
                IngestaLog.objects.create(
                    documento=instance,
                    etapa="creacion",
                    nivel="INFO",
                    mensaje=f"Documento duplicado por hash; se omitirá reprocesamiento (duplicado: #{duplicate.id})",
                    payload={"hash": instance.hash_sha256, "duplicate_id": duplicate.id}
                )
        
        return instance


class IngestaLogSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para IngestaLog.
    """
    class Meta:
        model = IngestaLog
        fields = [
            "id",
            "etapa",
            "nivel",
            "mensaje",
            "payload",
            "ts",
        ]
        read_only_fields = fields


class DocumentoFuenteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle de DocumentoFuente con logs.
    """
    logs = IngestaLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = DocumentoFuente
        fields = [
            "id",
            "archivo",
            "url_origen",
            "fuente",
            "tipo",
            "content_type",
            "extension",
            "size_bytes",
            "hash_sha256",
            "fecha_publicacion",
            "estado",
            "user_agent",
            "robots_observado",
            "crawl_delay_s",
            "created_at",
            "updated_at",
            "logs",
        ]
        read_only_fields = [
            "id",
            "tipo",
            "content_type",
            "extension",
            "size_bytes",
            "hash_sha256",
            "estado",
            "robots_observado",
            "crawl_delay_s",
            "created_at",
            "updated_at",
            "logs",
        ]
