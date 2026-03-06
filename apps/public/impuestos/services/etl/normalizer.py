"""
Normalizador para convertir tokens en entidades canónicas.

Mapea tokens a modelos: TipoImpuesto, TarifaIVA, ConceptoRetencion, etc.
"""
from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
from datetime import date


def normalize_payload(tokens: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Normaliza tokens en entidades canónicas para upsert.
    
    Args:
        tokens: Lista de tokens del tokenizer
        
    Returns:
        dict con claves:
        - 'tipos': List[Dict] para TipoImpuesto
        - 'tarifas': List[Dict] para TarifaIVA
        - 'retenciones': List[Dict] para ConceptoRetencion
        - 'codigos': List[Dict] para CodigoTributario
        - 'actividades': List[Dict] para ActividadEconomica
        - 'normas': List[Dict] para NormaTributaria
    """
    payload = {
        'tipos': [],
        'tarifas': [],
        'retenciones': [],
        'codigos': [],
        'actividades': [],
        'normas': [],
    }
    
    for token in tokens:
        # Normalizar norma tributaria
        norma = {
            'articulo': token.get('articulo'),
            'tema': token.get('tema'),
            'impuesto': token.get('impuesto'),
            'vigencia_desde': token.get('vigencia_desde'),
            'vigencia_hasta': token.get('vigencia_hasta'),
            'texto_plano': token.get('texto', ''),
            'texto_html': None,  # TODO: convertir a HTML si es necesario
            'referencias': token.get('referencias', []),
        }
        payload['normas'].append(norma)
        
        # Extraer información de impuestos
        impuesto = token.get('impuesto')
        if impuesto:
            # Normalizar tipo de impuesto
            tipo_impuesto = _normalize_tipo_impuesto(impuesto, token)
            if tipo_impuesto:
                payload['tipos'].append(tipo_impuesto)
            
            # Si es IVA, intentar extraer tarifa
            if 'IVA' in impuesto.upper() or 'VALOR AGREGADO' in impuesto.upper():
                tarifa = _normalize_tarifa_iva(token)
                if tarifa:
                    payload['tarifas'].append(tarifa)
            
            # Si es retención, normalizar concepto
            if 'RETENCION' in impuesto.upper() or 'RETENCIÓN' in impuesto.upper():
                retencion = _normalize_retencion(token)
                if retencion:
                    payload['retenciones'].append(retencion)
        
        # Extraer códigos tributarios
        codigo = _extract_codigo_tributario(token)
        if codigo:
            payload['codigos'].append(codigo)
        
        # Extraer actividades económicas
        actividad = _extract_actividad_economica(token)
        if actividad:
            payload['actividades'].append(actividad)
    
    # Eliminar duplicados por clave natural
    payload = _deduplicate_payload(payload)
    
    return payload


def _normalize_tipo_impuesto(impuesto: str, token: Dict) -> Dict[str, Any] | None:
    """Normaliza un tipo de impuesto."""
    # Mapeo de nombres comunes a códigos
    impuesto_map = {
        'IVA': '01',
        'VALOR AGREGADO': '01',
        'RETENCION': '02',
        'RETENCIÓN': '02',
        'ICA': '03',
        'RENTA': '04',
        'CREE': '05',
    }
    
    codigo = None
    for key, code in impuesto_map.items():
        if key in impuesto.upper():
            codigo = code
            break
    
    if not codigo:
        return None
    
    return {
        'codigo': codigo,
        'nombre': impuesto.strip(),
        'descripcion': token.get('texto', '')[:500],  # Limitar descripción
        'activo': True,
        'fecha_vigencia': token.get('vigencia_desde') or date.today(),
        'fecha_fin_vigencia': token.get('vigencia_hasta'),
    }


def _normalize_tarifa_iva(token: Dict) -> Dict[str, Any] | None:
    """Normaliza una tarifa de IVA."""
    texto = token.get('texto', '')
    
    # Buscar porcentaje en el texto
    porcentaje = _extract_porcentaje(texto)
    if porcentaje is None:
        return None
    
    # Determinar tipo de tarifa
    tipo_tarifa = 'general'
    texto_lower = texto.lower()
    if 'reducida' in texto_lower:
        tipo_tarifa = 'reducida'
    elif 'excluido' in texto_lower or 'excluida' in texto_lower:
        tipo_tarifa = 'excluido'
    elif 'exento' in texto_lower or 'exenta' in texto_lower:
        tipo_tarifa = 'exento'
    
    # Generar código único
    codigo = f"IVA-{porcentaje}-{tipo_tarifa[:2]}"
    
    return {
        'codigo': codigo,
        'nombre': f"IVA {porcentaje}% ({tipo_tarifa})",
        'porcentaje': porcentaje,
        'tipo_tarifa': tipo_tarifa,
        'descripcion': texto[:500],
        'activo': True,
        'fecha_vigencia': token.get('vigencia_desde') or date.today(),
        'fecha_fin_vigencia': token.get('vigencia_hasta'),
    }


def _normalize_retencion(token: Dict) -> Dict[str, Any] | None:
    """Normaliza un concepto de retención."""
    texto = token.get('texto', '')
    impuesto = token.get('impuesto', '')
    
    # Determinar tipo de retención
    tipo_retencion = 'otro'
    texto_lower = texto.lower()
    impuesto_lower = impuesto.lower()
    
    if 'ica' in impuesto_lower or 'industria' in texto_lower:
        tipo_retencion = 'ica'
    elif 'iva' in impuesto_lower:
        tipo_retencion = 'iva'
    elif 'renta' in impuesto_lower or 'renta' in texto_lower:
        tipo_retencion = 'renta'
    elif 'cree' in impuesto_lower or 'cree' in texto_lower:
        tipo_retencion = 'cree'
    
    # Extraer porcentaje
    porcentaje = _extract_porcentaje(texto)
    
    # Extraer base mínima
    base_minima = _extract_base_minima(texto)
    
    # Generar código
    codigo = f"RET-{tipo_retencion[:2]}-{porcentaje or 'VAR'}"
    
    return {
        'codigo': codigo,
        'nombre': token.get('tema') or impuesto or 'Retención',
        'tipo_retencion': tipo_retencion,
        'porcentaje': porcentaje,
        'base_minima': base_minima or Decimal('0'),
        'descripcion': texto[:500],
        'activo': True,
        'fecha_vigencia': token.get('vigencia_desde') or date.today(),
        'fecha_fin_vigencia': token.get('vigencia_hasta'),
    }


def _extract_codigo_tributario(token: Dict) -> Dict[str, Any] | None:
    """Extrae código tributario del token."""
    texto = token.get('texto', '')
    
    # Buscar patrones de código (ej: "Responsabilidad 01", "Régimen 48")
    import re
    codigo_pattern = re.compile(r'(?:Código|Codigo|Cód\.?)\s*:?\s*(\d{1,2})', re.IGNORECASE)
    match = codigo_pattern.search(texto)
    
    if not match:
        return None
    
    codigo = match.group(1)
    
    # Determinar tipo
    tipo = 'Otro'
    texto_lower = texto.lower()
    if 'responsabilidad' in texto_lower:
        tipo = 'Responsabilidad'
    elif 'régimen' in texto_lower or 'regimen' in texto_lower:
        tipo = 'Régimen'
    elif 'obligación' in texto_lower or 'obligacion' in texto_lower:
        tipo = 'Obligación'
    
    return {
        'codigo': codigo,
        'nombre': token.get('tema') or f"{tipo} {codigo}",
        'tipo': tipo,
        'descripcion': texto[:500],
        'activo': True,
        'fecha_vigencia': token.get('vigencia_desde') or date.today(),
        'fecha_fin_vigencia': token.get('vigencia_hasta'),
    }


def _extract_actividad_economica(token: Dict) -> Dict[str, Any] | None:
    """Extrae actividad económica del token."""
    texto = token.get('texto', '')
    
    # Buscar código CIIU (4 dígitos)
    import re
    ciiu_pattern = re.compile(r'CIIU[:\s]*(\d{4})', re.IGNORECASE)
    match = ciiu_pattern.search(texto)
    
    if not match:
        return None
    
    codigo = match.group(1)
    
    return {
        'codigo': codigo,
        'nombre': token.get('tema') or f"Actividad {codigo}",
        'descripcion': texto[:500],
        'activo': True,
    }


def _extract_porcentaje(texto: str) -> Decimal | None:
    """Extrae porcentaje del texto."""
    import re
    
    # Patrones: "19%", "19.00%", "19 por ciento", "19,00%"
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*%',
        r'(\d+(?:[.,]\d+)?)\s+por\s+ciento',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            try:
                valor_str = match.group(1).replace(',', '.')
                valor = Decimal(valor_str)
                # Validar rango 0-100
                if 0 <= valor <= 100:
                    return valor
            except (InvalidOperation, ValueError):
                continue
    
    return None


def _extract_base_minima(texto: str) -> Decimal | None:
    """Extrae base mínima del texto."""
    import re
    
    # Patrones: "base mínima $100.000", "mínimo $100000"
    patterns = [
        r'(?:base\s+)?mínima[:\s]*\$?\s*([\d.,]+)',
        r'mínimo[:\s]*\$?\s*([\d.,]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            try:
                valor_str = match.group(1).replace('.', '').replace(',', '.')
                return Decimal(valor_str)
            except (InvalidOperation, ValueError):
                continue
    
    return None


def _deduplicate_payload(payload: Dict) -> Dict:
    """Elimina duplicados del payload por clave natural."""
    # Para cada tipo de entidad, agrupar por clave natural
    deduplicated = {}
    
    for key, items in payload.items():
        seen = {}
        for item in items:
            # Generar clave única según el tipo
            if key == 'tipos':
                unique_key = item.get('codigo')
            elif key == 'tarifas':
                unique_key = (item.get('codigo'), item.get('fecha_vigencia'))
            elif key == 'retenciones':
                unique_key = (item.get('codigo'), item.get('fecha_vigencia'))
            elif key == 'codigos':
                unique_key = (item.get('codigo'), item.get('tipo'))
            elif key == 'actividades':
                unique_key = item.get('codigo')
            elif key == 'normas':
                unique_key = (
                    item.get('articulo'),
                    item.get('tema'),
                    item.get('impuesto'),
                )
            else:
                unique_key = None
            
            if unique_key and unique_key not in seen:
                seen[unique_key] = item
            elif unique_key:
                # Si ya existe, actualizar con información más completa
                existing = seen[unique_key]
                # Preferir valores no nulos
                for k, v in item.items():
                    if v and not existing.get(k):
                        existing[k] = v
        
        deduplicated[key] = list(seen.values())
    
    return deduplicated
