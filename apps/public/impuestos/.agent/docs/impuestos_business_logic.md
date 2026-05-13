# 🧠 Lógica de Negocio: Módulo Impuestos (SSoT)

Este documento centraliza las reglas normativas y tributarias compartidas.

---

## 1. Integridad del Catálogo DIAN

- **Códigos Canónicos**: Todos los registros deben coincidir con los códigos definidos en los anexos técnicos de la DIAN (ej. `01` para IVA, `04` para INC).
- **Inmutabilidad Histórica**: Las tarifas que han sido utilizadas en documentos legales (Facturas) no deben ser eliminadas. Si una tarifa deja de ser vigente, se marca como inactiva para nuevas operaciones pero se preserva para auditoría.

---

## 2. Reglas de Cálculo e Inferencia

- **Inferencia de Retención**: La aplicación de retenciones se basa en la combinación de (Actividad Económica + Topes de UVT + Calidad Tributaria del Emisor/Receptor).
- **Tratamiento de IVA**: El sistema distingue entre Exento, Excluido y Gravado basándose en el `DocumentoFuente` y la clasificación del producto/servicio en el catálogo global.

---

## 3. Aislamiento del Proveedor (Provider Pattern)

- **Read-Only Enforcement**: Las apps tenant nunca deben realizar operaciones `save()` o `delete()` sobre los modelos de este módulo. Toda interacción de escritura es exclusiva de la administración global.
- **DTOs de Salida**: El `ImpuestosProvider` debe retornar objetos de datos planos (DTOs) para evitar que las apps tenant manipulen directamente las instancias del modelo público.

---

## 4. Gestión de Actividades Económicas (CIIU)

- **Jerarquía**: Soporte para Secciones, Divisiones, Grupos y Clases según la clasificación industrial internacional uniforme adaptada para Colombia.
- **Asociación**: Cada perfil de empresa o tercero debe estar vinculado a una o más actividades CIIU válidas del catálogo.

---

## 5. Validación de Dígito de Verificación (DV)

- **Algoritmo de Módulo 11**: El sistema incluye la lógica canónica para calcular y validar el DV de un NIT, asegurando la consistencia en todos los registros de identificación tributaria de la plataforma.
