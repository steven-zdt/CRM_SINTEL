# apps/tenant/contabilidad/choices.py
# apps/tenant/contabilidad/choices.py

"""
CATÁLOGO NIIF COLOMBIA - SINTEL v2.61.4
Alineado con:
- Módulo Gastos (31 categorías contables y centros de costo)
- Módulo Facturas (IVA, Retenciones, Notas Crédito)
- Módulo Empleados (Seguridad Social y Parafiscales)
- Módulo Inventario (Kardex y Activos Fijos)
"""

CATALOGO_NIIF_COLOMBIA = [
    # Estructura: [Código, Nombre, Nivel, Naturaleza (D: Débito, C: Crédito)]
    
    # --- 1. ACTIVO ---
    ('1', 'ACTIVO', 1, 'D'),
    ('11', 'EFECTIVO Y EQUIVALENTES DE EFECTIVO', 2, 'D'),
    ('1105', 'CAJA', 4, 'D'),
    ('110505', 'CAJA GENERAL', 6, 'D'),
    ('1110', 'BANCOS', 4, 'D'),
    ('111005', 'MONEDA NACIONAL', 6, 'D'),
    ('12', 'INVERSIONES E INSTRUMENTOS DERIVADOS', 2, 'D'),
    
    # Módulo Clientes y Facturación
    ('13', 'CUENTAS POR COBRAR COMERCIALES Y OTRAS', 2, 'D'),
    ('1305', 'CLIENTES', 4, 'D'),
    ('130505', 'CLIENTES NACIONALES', 6, 'D'),
    ('130510', 'CLIENTES DEL EXTERIOR', 6, 'D'),
    ('1330', 'ANTICIPOS Y AVANCES', 4, 'D'),
    ('133005', 'A PROVEEDORES', 6, 'D'),
    ('1355', 'ANTICIPO DE IMPUESTOS Y CONTRIBUCIONES', 4, 'D'),
    ('135515', 'RETENCIÓN EN LA FUENTE (A FAVOR)', 6, 'D'),
    ('135517', 'IMPUESTO A LAS VENTAS (IVA) PAGADO', 6, 'D'),
    ('135518', 'IMPUESTO DE INDUSTRIA Y COMERCIO (ICA) PAGADO', 6, 'D'),
    ('1399', 'DETERIORO DE VALOR (CARTERA)', 4, 'C'),
    ('139905', 'CLIENTES', 6, 'C'),
    
    # Módulo Inventario y Kardex
    ('14', 'INVENTARIOS', 2, 'D'),
    ('1435', 'MERCANCÍAS NO FABRICADAS POR LA EMPRESA', 4, 'D'),
    ('143505', 'PRODUCTOS TERMINADOS', 6, 'D'),
    ('143510', 'MATERIALES Y SUMINISTROS', 6, 'D'),
    
    # Módulo Activos Fijos
    ('15', 'PROPIEDADES, PLANTA Y EQUIPO', 2, 'D'),
    ('1524', 'EQUIPO DE OFICINA', 4, 'D'),
    ('152405', 'MUEBLES Y ENSERES', 6, 'D'),
    ('1528', 'EQUIPO DE COMPUTACIÓN Y COMUNICACIÓN', 4, 'D'),
    ('1540', 'FLOTA Y EQUIPO DE TRANSPORTE', 4, 'D'),
    ('1592', 'DEPRECIACIÓN ACUMULADA', 4, 'C'),

    # --- 2. PASIVO ---
    ('2', 'PASIVO', 1, 'C'),
    ('21', 'OBLIGACIONES FINANCIERAS', 2, 'C'),
    ('2105', 'BANCOS NACIONALES', 4, 'C'),
    
    # Módulo Proveedores
    ('22', 'PROVEEDORES', 2, 'C'),
    ('2205', 'PROVEEDORES NACIONALES', 4, 'C'),
    ('220501', 'PROVEEDORES NACIONALES - BIENES', 6, 'C'),
    ('220505', 'PROVEEDORES NACIONALES - SERVICIOS', 6, 'C'),
    ('2210', 'PROVEEDORES DEL EXTERIOR', 4, 'C'),
    ('221005', 'PROVEEDORES DEL EXTERIOR - BIENES', 6, 'C'),
    ('221010', 'PROVEEDORES DEL EXTERIOR - SERVICIOS', 6, 'C'),

    # Módulo Gastos Operativos y Documento Soporte
    ('23', 'CUENTAS POR PAGAR COMERCIALES Y OTRAS', 2, 'C'),
    ('2335', 'COSTOS Y GASTOS POR PAGAR', 4, 'C'),
    ('233505', 'GASTOS BANCARIOS', 6, 'C'),
    ('233510', 'HONORARIOS POR PAGAR', 6, 'C'),
    ('233515', 'COMISIONES POR PAGAR', 6, 'C'),
    ('233520', 'ARRENDAMIENTOS POR PAGAR', 6, 'C'),
    ('233525', 'SERVICIOS PÚBLICOS POR PAGAR', 6, 'C'),
    ('233550', 'SERVICIOS PÚBLICOS', 6, 'C'),
    ('233595', 'OTROS COSTOS Y GASTOS', 6, 'C'),
    ('2365', 'RETENCIÓN EN LA FUENTE', 4, 'C'),
    ('236505', 'RETENCIÓN EN LA FUENTE - SALARIOS', 6, 'C'),
    ('236510', 'RETENCIÓN EN LA FUENTE - HONORARIOS', 6, 'C'),
    ('236515', 'RETENCIÓN EN LA FUENTE - SERVICIOS', 6, 'C'),
    ('236525', 'RETENCIÓN EN LA FUENTE - ARRENDAMIENTOS', 6, 'C'),
    ('236540', 'RETENCIÓN EN LA FUENTE - COMPRAS', 6, 'C'),
    ('2368', 'IMPUESTO DE INDUSTRIA Y COMERCIO RETENIDO', 4, 'C'),
    ('236805', 'ICA RETENIDO - ACTIVIDADES COMERCIALES', 6, 'C'),
    
    # Módulo Empleados y Nómina
    ('2370', 'RETENCIONES Y APORTES DE NÓMINA', 4, 'C'),
    ('237005', 'APORTES A SEGURIDAD SOCIAL (EPS)', 6, 'C'),
    ('237006', 'APORTES A RIESGOS LABORALES (ARL)', 6, 'C'),
    ('237010', 'APORTES A FONDOS DE PENSIONES', 6, 'C'),
    ('2380', 'ACREEDORES VARIOS', 4, 'C'),
    ('238030', 'FONDOS DE CESANTÍAS', 6, 'C'),
    ('238095', 'ANTICIPOS RECIBIDOS DE CLIENTES', 6, 'C'),
    
    ('24', 'IMPUESTOS, GRAVÁMENES Y TASAS', 2, 'C'),
    ('2408', 'IMPUESTO SOBRE LAS VENTAS POR PAGAR', 4, 'C'),
    ('240805', 'IVA GENERADO', 6, 'C'),
    ('240810', 'IVA DESCONTABLE', 6, 'C'),
    ('25', 'OBLIGACIONES LABORALES', 2, 'C'),
    ('2505', 'SALARIOS POR PAGAR', 4, 'C'),
    ('2510', 'CESANTÍAS CONSOLIDADAS', 4, 'C'),
    ('2515', 'INTERESES SOBRE CESANTÍAS', 4, 'C'),
    ('2520', 'PRIMA DE SERVICIOS', 4, 'C'),
    ('2525', 'VACACIONES CONSOLIDADAS', 4, 'C'),

    # --- 3. PATRIMONIO ---
    ('3', 'PATRIMONIO', 1, 'C'),
    ('31', 'CAPITAL PROPIO', 2, 'C'),
    ('3105', 'CAPITAL SUSCRITO Y PAGADO', 4, 'C'),
    ('33', 'RESERVAS', 2, 'C'),
    ('3305', 'RESERVA LEGAL', 4, 'C'),
    ('36', 'RESULTADOS DEL EJERCICIO', 2, 'C'),
    ('3605', 'UTILIDAD DEL EJERCICIO', 4, 'C'),
    ('3610', 'PÉRDIDA DEL EJERCICIO', 4, 'D'),

    # --- 4. INGRESOS ---
    ('4', 'INGRESOS', 1, 'C'),
    ('41', 'INGRESOS OPERACIONALES', 2, 'C'),
    ('4135', 'COMERCIO AL POR MAYOR Y AL POR MENOR', 4, 'C'),
    ('413505', 'VENTA DE MERCANCÍAS', 6, 'C'),
    ('413510', 'VENTA DE SERVICIOS', 6, 'C'),
    ('4175', 'DEVOLUCIONES EN VENTAS (DB)', 4, 'D'),
    ('42', 'INGRESOS NO OPERACIONALES', 2, 'C'),
    ('4210', 'FINANCIEROS', 4, 'C'),

    # --- 5. GASTOS ---
    ('5', 'GASTOS', 1, 'D'),
    ('51', 'GASTOS DE ADMINISTRACIÓN', 2, 'D'),
    # Nómina (Módulo Empleados)
    ('5105', 'GASTOS DE PERSONAL', 4, 'D'),
    ('510506', 'SUELDOS', 6, 'D'),
    ('510527', 'AUXILIO DE TRANSPORTE', 6, 'D'),
    ('510530', 'CESANTÍAS', 6, 'D'),
    ('510533', 'INTERESES SOBRE CESANTÍAS', 6, 'D'),
    ('510536', 'PRIMA DE SERVICIOS', 6, 'D'),
    ('510539', 'VACACIONES', 6, 'D'),
    ('510568', 'APORTES A SEGURIDAD SOCIAL INTEGRAL', 6, 'D'),
    ('510570', 'APORTES A CAJAS DE COMPENSACIÓN FAMILIAR', 6, 'D'),
    # Gastos Operativos (Alineado con las 31 categorías v2.40)
    ('5110', 'HONORARIOS', 4, 'D'),
    ('511005', 'HONORARIOS PROFESIONALES', 6, 'D'),
    ('5115', 'IMPUESTOS', 4, 'D'),
    ('511505', 'INDUSTRIA Y COMERCIO', 6, 'D'),
    ('5120', 'ARRENDAMIENTOS', 4, 'D'),
    ('512010', 'CONSTRUCCIONES Y EDIFICACIONES', 6, 'D'),
    ('5130', 'SEGUROS', 4, 'D'),
    ('513005', 'SEGURO DE VIDA', 6, 'D'),
    ('513025', 'SEGURO CONTRA INCENDIO', 6, 'D'),
    ('5135', 'SERVICIOS', 4, 'D'),
    ('513505', 'ASEO Y VIGILANCIA', 6, 'D'),
    ('513520', 'ENERGÍA ELÉCTRICA', 6, 'D'),
    ('513525', 'ACUEDUCTO Y ALCANTARILLADO', 6, 'D'),
    ('513530', 'GAS NATURAL', 6, 'D'),
    ('513535', 'TELÉFONO / INTERNET', 6, 'D'),
    ('5140', 'GASTOS LEGALES', 4, 'D'),
    ('5145', 'MANTENIMIENTO Y REPARACIONES', 4, 'D'),
    ('514510', 'CONSTRUCCIONES Y EDIFICACIONES', 6, 'D'),
    ('514525', 'EQUIPO DE COMPUTACIÓN', 6, 'D'),
    ('5150', 'ADECUACIÓN E INSTALACIÓN', 4, 'D'),
    ('5155', 'GASTOS DE VIAJE / VIÁTICOS', 4, 'D'),
    ('5160', 'DEPRECIACIONES', 4, 'D'),
    ('5195', 'DIVERSOS', 4, 'D'),
    ('519525', 'ELEMENTOS DE ASEO Y CAFETERÍA', 6, 'D'),
    ('519530', 'ÚTILES, PAPELERÍA Y FOTOCOPIAS', 6, 'D'),
    ('5199', 'DETERIORO DE VALOR (GASTO)', 4, 'D'),
    ('52', 'GASTOS DE VENTAS', 2, 'D'),

    # --- 6. COSTOS DE VENTAS ---
    ('6', 'COSTOS DE VENTAS', 1, 'D'),
    ('61', 'COSTO DE VENTAS Y DE PRESTACIÓN DE SERVICIOS', 2, 'D'),
    ('6135', 'COMERCIO AL POR MAYOR Y AL POR MENOR', 4, 'D'),
    ('613505', 'COSTO DE MERCANCÍAS VENDIDAS', 6, 'D'),
    ('613510', 'COSTO DE SERVICIOS PRESTADOS', 6, 'D'),
]