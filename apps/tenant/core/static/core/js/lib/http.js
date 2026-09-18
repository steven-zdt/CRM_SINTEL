/**
 * HTTP Helper - API-First con SessionAuth + CSRF
 * 
 * ⚠️ POLÍTICA API-First:
 * - Todas las apps consumen APIs DRF (JSON-only)
 * - URLs siempre relativas (sin dominio absoluto)
 * - Manejo automático de CSRF y cookies de sesión
 * - Manejo de errores 401 no críticos localmente
 * 
 * Compatible con ES6 modules y uso global (window.http)
 */

(function() {
  'use strict';

  /**
   * Obtiene el valor de una cookie por nombre.
   * @param {string} name - Nombre de la cookie
   * @returns {string|null} Valor de la cookie o null si no existe
   */
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop().split(";").shift());
    }
    return null;
  }

  /**
   * Realiza una petición HTTP con manejo automático de CSRF y SessionAuth.
   * 
   * @param {string} method - Método HTTP (GET, POST, PUT, PATCH, DELETE)
   * @param {string} url - URL relativa (ej: '/api/v1/core/empresa/')
   * @param {Object|FormData|undefined} body - Cuerpo de la petición (opcional)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function http(method, url, body) {
    // ⚠️ POLÍTICA: URLs siempre relativas
    if (url.startsWith('http://') || url.startsWith('https://')) {
      console.warn('[http] URL absoluta detectada, usando como está:', url);
    }

    const init = {
      method: method.toUpperCase(),
      headers: { "Accept": "application/json" },
      credentials: "same-origin", // SessionAuth
    };

    // [FE-C3] Inyectar JWT si esta disponible. BaseTenantViewSet (Dual-Auth) intenta
    // JWTAuthentication antes que SessionAuthentication; sin esta cabecera, este
    // cliente (el que efectivamente se carga al final en assets_core.html y gana
    // sobre window.http) dependia unicamente de la cookie de sesion, anulando la
    // mitad del contrato Dual-Auth documentado en AGENTS.md.
    try {
      if (window.jwtAuth && typeof window.jwtAuth.getValidAccessToken === 'function') {
        const token = await window.jwtAuth.getValidAccessToken();
        if (token) {
          init.headers["Authorization"] = `Bearer ${token}`;
        }
      }
    } catch (_) {
      // silencioso: jwtAuth es opcional, SessionAuth sigue funcionando como fallback
    }

    // ⚠️ CSRF: Requerido para métodos que modifican estado
    const needsCsrf = ["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase());
    if (needsCsrf || body !== undefined) {
      const csrf = getCookie("csrftoken");
      if (csrf) {
        init.headers["X-CSRFToken"] = csrf;
      } else {
        console.warn("[http] CSRF cookie NO encontrada al enviar write:", url);
      }
    }

    // Manejo del body
    if (body !== undefined) {
      if (body instanceof FormData) {
        // ⚠️ v2.60: FormData - NO establecer Content-Type (el navegador lo calcula automáticamente con boundary)
        // ⚠️ CRÍTICO: NO usar JSON.stringify() para FormData
        init.body = body;
        
        // ⚠️ IMPORTANTE: Eliminar Content-Type del header si existe (el navegador lo establecerá automáticamente)
        // No establecerlo explícitamente permite que el navegador agregue el boundary correcto
        delete init.headers["Content-Type"];
        
        // Agregar CSRF al FormData para compatibilidad Django tradicional
        if (needsCsrf) {
          const csrf = getCookie("csrftoken");
          if (csrf) {
            body.append("csrfmiddlewaretoken", csrf);
          }
        }
        // ⚠️ DEBUG: Log FormData para diagnóstico
        console.log('[http] Enviando FormData (multipart/form-data):', url);
        for (const [key, value] of body.entries()) {
          if (value instanceof File) {
            console.log(`[http] FormData[${key}]: File(${value.name}, ${value.size} bytes, ${value.type})`);
          } else {
            console.log(`[http] FormData[${key}]:`, value, typeof value);
          }
        }
      } else {
        // ⚠️ CRÍTICO: Asegurar que el body sea un objeto JSON, no FormData ni HTMLFormElement
        if (body instanceof HTMLFormElement) {
          console.error('[http] ⚠️ ERROR CRÍTICO: Se recibió un HTMLFormElement en lugar de un objeto JSON. Esto no está permitido.');
          throw new Error('No se puede enviar un HTMLFormElement directamente. Debe convertirse a objeto JSON primero.');
        }
        
        // ⚠️ CRÍTICO: Forzar Content-Type a application/json y serializar como JSON
        init.headers["Content-Type"] = "application/json";
        
        // ⚠️ CRÍTICO: Verificar que el body no contenga valores de texto descriptivo para cliente
        // Si el body tiene un campo 'cliente' que es string y contiene '(', forzar conversión a número
        if (body && typeof body === 'object' && !Array.isArray(body) && body.cliente !== undefined) {
          // ⚠️ CRÍTICO: Si cliente es string, intentar convertirlo a número
          if (typeof body.cliente === 'string') {
            // Si contiene paréntesis, es texto descriptivo
            if (body.cliente.includes('(')) {
              console.error('[http] ⚠️ ERROR CRÍTICO: El body.cliente contiene texto descriptivo antes de serializar:', body.cliente);
              // Intentar extraer el ID numérico del texto (último recurso)
              const match = body.cliente.match(/\((\d+)\)/);
              if (match && match[1]) {
                const extractedId = parseInt(match[1], 10);
                if (!isNaN(extractedId)) {
                  console.warn('[http] ⚠️ CORRECCIÓN: Extrayendo ID del texto descriptivo:', extractedId);
                  body.cliente = extractedId;
                } else {
                  console.error('[http] ⚠️ ERROR: No se pudo extraer ID numérico del texto:', body.cliente);
                }
              } else {
                console.error('[http] ⚠️ ERROR: No se encontró patrón de ID en el texto:', body.cliente);
              }
            } else {
              // Si es string pero no contiene paréntesis, intentar parsearlo como número
              const parsedId = parseInt(body.cliente.trim(), 10);
              if (!isNaN(parsedId) && parsedId > 0) {
                console.warn('[http] ⚠️ CORRECCIÓN: Convirtiendo string a número:', parsedId);
                body.cliente = parsedId;
              } else {
                console.error('[http] ⚠️ ERROR: El string de cliente no es un número válido:', body.cliente);
              }
            }
          }
          
          // ⚠️ CRÍTICO: Asegurar que cliente sea un número entero
          if (typeof body.cliente !== 'number' || !Number.isInteger(body.cliente)) {
            console.error('[http] ⚠️ ERROR CRÍTICO: body.cliente no es un número entero después de la corrección:', {
              value: body.cliente,
              type: typeof body.cliente,
              isNumber: typeof body.cliente === 'number',
              isInteger: Number.isInteger(body.cliente)
            });
          }
        }
        
        const bodyString = JSON.stringify(body);
        init.body = bodyString;
        // ⚠️ DEBUG: Log JSON body para diagnóstico
        console.log('[http] Enviando JSON:', url, bodyString);
        // Verificar que el JSON contiene los valores correctos
        try {
          const parsed = JSON.parse(bodyString);
          if (parsed.cliente !== undefined) {
            console.log('[http] Verificación cliente en JSON:', {
              value: parsed.cliente,
              type: typeof parsed.cliente,
              isNumber: typeof parsed.cliente === 'number',
              isString: typeof parsed.cliente === 'string',
              isInteger: Number.isInteger(parsed.cliente),
              stringValue: String(parsed.cliente),
              rawBodyString: bodyString.substring(0, 200) // Primeros 200 caracteres del JSON
            });
            // ⚠️ CRÍTICO: Verificar que el valor no sea el texto descriptivo
            if (typeof parsed.cliente === 'string' && parsed.cliente.includes('(')) {
              console.error('[http] ⚠️ ERROR CRÍTICO: El valor de cliente parece ser texto descriptivo:', parsed.cliente);
            }
          }
          // Verificar también configuracion
          if (parsed.configuracion !== undefined) {
            console.log('[http] Verificación configuracion en JSON:', {
              value: parsed.configuracion,
              type: typeof parsed.configuracion,
              isNumber: typeof parsed.configuracion === 'number',
              isInteger: Number.isInteger(parsed.configuracion)
            });
          }
        } catch (e) {
          console.error('[http] Error al parsear JSON para verificación:', e);
        }
      }
    }

    const res = await fetch(url, init);

    // ⚠️ Manejo de 401 Unauthorized - redirección inteligente
    // Módulos no-críticos: no forzar logout, solo retornar error
    if (res.status === 401) {
      const nonCriticalModules = [
        "/api/v1/gastos/",
        "/api/v1/clientes/",
        "/api/v1/proveedores/",
        "/api/v1/inventario/",
      ];
      
      const isNonCritical = nonCriticalModules.some(prefix => url.includes(prefix));
      
      if (isNonCritical) {
        // Retornar respuesta de error para que el módulo lo maneje localmente
        const text = await res.text();
        let data = null;
        try { data = text ? JSON.parse(text) : null; } catch (err) { data = { detail: text }; }
        return { ok: false, status: 401, data: data || { detail: "No autorizado en módulo no crítico" } };
      }
      
      // Endpoints críticos: redirigir a login
      const loginUrl = new URL("/login/", window.location.origin);
      loginUrl.searchParams.set("reason", "401");
      loginUrl.searchParams.set("next", window.location.pathname + window.location.hash);
      window.location.assign(loginUrl.toString());
      return { ok: false, status: 401, data: { detail: "Unauthorized" } };
    }

    // Parsear respuesta
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (err) {
      data = { detail: text };
    }

    // ⚠️ Diagnóstico mejorado para 403
    if (res.status === 403) {
      const csrfCookie = getCookie("csrftoken");
      console.warn("[http] 403 Forbidden en", method, url, {
        status: 403,
        detail: data?.detail,
        csrfCookie: csrfCookie ? "presente" : "ausente",
        sentHeader: init.headers?.["X-CSRFToken"] ? "presente" : "ausente",
        url,
        origin: window.location.origin,
      });
    }

    return { ok: res.ok, status: res.status, data };
  }

  // Exportar para uso global (sin ES6 modules)
  if (typeof window !== 'undefined') {
    window.http = http;
    window.getCookie = getCookie;
  }

  // Exportar para ES6 modules (si se usa)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { http, getCookie };
  }
})();
