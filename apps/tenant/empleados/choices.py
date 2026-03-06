"""
Choices Legales Colombia - v2.95
Listado de Entidades de Seguridad Social (EPS, AFP, ARL).
"""

# EPS autorizadas y activas
EPS_CHOICES = [
    ('EPS001', 'Nueva EPS'),
    ('EPS002', 'Salud Total'),
    ('EPS003', 'Sanitas'),
    ('EPS004', 'Sura'),
    ('EPS005', 'Compensar'),
    ('EPS006', 'Coosalud'),
    ('EPS007', 'Mutual Ser'),
    ('EPS008', 'Famisanar'),
    ('EPS009', 'Ecopetrol (Régimen Especial)'),
    ('EPS010', 'Salud Mía'),
]

# Administradoras de Fondos de Pensiones (AFP)
AFP_CHOICES = [
    ('AFP001', 'Protección'),
    ('AFP002', 'Porvenir'),
    ('AFP003', 'Colfondos'),
    ('AFP004', 'Skandia'),
    ('AFP005', 'Colpensiones (Régimen de Prima Media)'),
]

# Administradoras de Riesgos Laborales (ARL)
ARL_CHOICES = [
    ('ARL001', 'Positiva ARL'),
    ('ARL002', 'ARL Sura'),
    ('ARL003', 'ARL Seguros Bolívar'),
    ('ARL004', 'ARL Colmena'),
    ('ARL005', 'ARL AXA Colpatria'),
    ('ARL006', 'ARL La Equidad'),
    ('ARL007', 'ARL Liberty Seguros'),
]

# Niveles de Riesgo ARL (Clases de Riesgo)
RIESGO_ARL_CHOICES = [
    ('I', 'Clase I (Riesgo Mínimo)'),
    ('II', 'Clase II (Riesgo Bajo)'),
    ('III', 'Clase III (Riesgo Medio)'),
    ('IV', 'Clase IV (Riesgo Alto)'),
    ('V', 'Clase V (Riesgo Máximo)'),
]