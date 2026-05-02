# 🖥️ Guía de Configuración de Windows Terminal

## Configurar Ctrl+C para Copiar en Windows Terminal

### Método 1: Configuración Manual (Recomendado)

1. **Abrir Windows Terminal**
   - Presiona `Win + X` y selecciona "Windows Terminal"
   - O busca "Windows Terminal" en el menú inicio

2. **Abrir Configuración**
   - Presiona `Ctrl + ,` (Ctrl + coma)
   - O haz clic en la flecha hacia abajo (▼) junto al botón "+" y selecciona "Configuración"

3. **Ir a Atajos de Teclado**
   - En la barra lateral izquierda, busca y haz clic en "Atajos de teclado" o "Keyboard shortcuts"
   - O busca "keybindings" en la barra de búsqueda superior

4. **Configurar Ctrl+C para Copiar**
   - Busca "copy" en la lista de acciones
   - Haz clic en el ícono de lápiz o "+" junto a "copy"
   - Presiona `Ctrl + C` cuando te pida la combinación de teclas
   - Guarda los cambios

5. **Configurar Ctrl+V para Pegar**
   - Busca "paste" en la lista de acciones
   - Haz clic en el ícono de lápiz o "+" junto a "paste"
   - Presiona `Ctrl + V` cuando te pida la combinación de teclas
   - Guarda los cambios

6. **Configurar Ctrl+Shift+C como alternativa (opcional)**
   - Si quieres mantener Ctrl+C para copiar y también tener una alternativa:
   - Busca "copy" y agrega una segunda combinación: `Ctrl + Shift + C`

### Método 2: Editar Archivo JSON Directamente

1. **Abrir el archivo de configuración**
   - Presiona `Ctrl + ,` para abrir Configuración
   - Haz clic en "Abrir archivo JSON" en la parte inferior
   - O navega manualmente a: `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json`

2. **Agregar los keybindings**
   - Busca la sección `"keybindings"` o `"actions"` en el JSON
   - Si no existe, créala dentro del objeto principal

3. **Agregar estas líneas** (dentro del array de keybindings):

```json
{
    "command": "copy",
    "keys": "ctrl+c"
},
{
    "command": "paste",
    "keys": "ctrl+v"
},
{
    "command": "copy",
    "keys": "ctrl+shift+c"
},
{
    "command": "paste",
    "keys": "ctrl+shift+v"
}
```

### Método 3: Usar el archivo de configuración completo

He creado un archivo `windows_terminal_settings.json` con una configuración completa que puedes usar como referencia o reemplazar tu archivo actual.

## ⚠️ Nota Importante sobre Ctrl+C

**IMPORTANTE**: Si configuras `Ctrl+C` para copiar, perderás la funcionalidad de interrumpir procesos. Considera estas opciones:

### Opción A: Usar Ctrl+Shift+C para copiar (Recomendado)
- Mantiene `Ctrl+C` para interrumpir procesos
- Usa `Ctrl+Shift+C` para copiar
- Usa `Ctrl+Shift+V` para pegar

### Opción B: Usar Ctrl+C para copiar
- `Ctrl+C` copia texto seleccionado
- Para interrumpir procesos, usa `Ctrl+Break` o configura otra tecla

### Opción C: Modo de selección
- Selecciona texto con el mouse
- Presiona `Enter` para copiar automáticamente (si QuickEdit está activado)
- Click derecho para pegar

## 🔧 Configuración Adicional Útil

### Habilitar selección de texto mejorada

En el archivo JSON, puedes agregar estas configuraciones:

```json
{
    "profiles": {
        "defaults": {
            "copyOnSelect": true,
            "copyFormatting": false
        }
    }
}
```

- `copyOnSelect: true` - Copia automáticamente al seleccionar texto
- `copyFormatting: false` - No copia formato, solo texto plano

### Configuración de perfil PowerShell

```json
{
    "profiles": {
        "list": [
            {
                "name": "PowerShell",
                "commandline": "powershell.exe",
                "copyOnSelect": true,
                "font": {
                    "face": "Cascadia Code",
                    "size": 11
                }
            }
        ]
    }
}
```

## 📋 Comandos Útiles de Windows Terminal

- `Ctrl + ,` - Abrir configuración
- `Ctrl + Shift + ,` - Abrir archivo JSON de configuración
- `Ctrl + Shift + P` - Abrir paleta de comandos
- `Ctrl + T` - Nueva pestaña
- `Ctrl + W` - Cerrar pestaña
- `Ctrl + Tab` - Cambiar entre pestañas
- `Alt + Shift + D` - Dividir panel
- `Ctrl + Shift + F` - Buscar en terminal

## 🐛 Solución de Problemas

### Si Ctrl+C no funciona después de configurarlo:

1. **Reinicia Windows Terminal** completamente
2. **Verifica que no haya conflictos** con otros atajos
3. **Revisa el archivo JSON** por errores de sintaxis (usa un validador JSON)
4. **Prueba con Ctrl+Shift+C** primero antes de cambiar Ctrl+C

### Si el archivo JSON tiene errores:

1. Usa un validador JSON online
2. O usa el editor de configuración visual (`Ctrl + ,`)
3. Haz backup del archivo antes de editarlo

## 📝 Ejemplo de Configuración Completa

Ver el archivo `windows_terminal_settings.json` en este proyecto para un ejemplo completo de configuración.
