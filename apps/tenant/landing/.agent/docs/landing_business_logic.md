# 🧠 Lógica de Negocio: Módulo Landing (SSoT)

Este documento centraliza las reglas de presentación y gestión de marca.

---

## 1. Gestión de Marca (Branding SSoT)

- **Logo Corporativo**: Única ubicación autorizada para la URL del logo que se utiliza en facturas, correos y cabeceras de la aplicación.
- **Paleta de Colores**: Definición de variables CSS (`--primary`, `--secondary`) que el núcleo (Core) consume para tematizar la interfaz del tenant.
- **Textos Públicos**: Gestión de eslóganes, misión/visión y metadatos SEO específicos del inquilino.

---

## 2. Aislamiento de Capas

- **Cero Lógica de Negocio**: Este módulo NO procesa transacciones, cálculos de nómina ni gestión de inventarios. Su única función es descriptiva.
- **Delegación de Seguridad**: Todas las rutas que requieran autenticación (`@login_required`) deben delegar el flujo de control a `apps.tenant.core`.

---

## 3. Resolución de Identidad Singleton

- **Coherencia con Empresa**: La información de la landing debe estar sincronizada con el modelo `Empresa`. Si se actualiza el nombre legal en `Empresa`, la landing debe reflejarlo de manera reactiva (o mediante el servicio compartido).

---

## 4. SEO y Rendimiento

- **Meta-Tags Dinámicos**: Los servicios de landing deben proveer los metadatos necesarios para que el renderizador incluya etiquetas OpenGraph personalizadas por inquilino.
- **Zero-Waste Assets**: Prohibido cargar librerías pesadas (ej. Tabulator, Charts) en la página de inicio pública a menos que sea estrictamente necesario para la presentación.
