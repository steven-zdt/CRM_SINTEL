#!/bin/bash
# Script de pruebas para endpoints del módulo Empresa
# Uso: ./scripts/test_empresa_endpoints.sh [BASE_URL] [SESSIONID] [CSRFTOKEN]
#
# Ejemplo:
#   ./scripts/test_empresa_endpoints.sh http://home.sintel.net.co abc123... xyz789...

BASE_URL="${1:-http://localhost:8000}"
SESSIONID="${2:-}"
CSRFTOKEN="${3:-}"

echo "=========================================="
echo "PRUEBAS: Módulo Empresa v2.40"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para hacer peticiones
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5
    
    echo -n "Testing: $description... "
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            -H "Cookie: sessionid=$SESSIONID" \
            -H "X-CSRFToken: $CSRFTOKEN" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            -H "Cookie: sessionid=$SESSIONID" \
            -H "X-CSRFToken: $CSRFTOKEN" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (Status: $http_code)"
        if [ -n "$body" ] && [ "$body" != "null" ]; then
            echo "  Response: $(echo "$body" | head -c 200)..."
        fi
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_status, Got: $http_code)"
        echo "  Response: $body"
        return 1
    fi
}

# Contador de pruebas
passed=0
failed=0

echo "=== PRUEBA 1: Listar Empresas (Paginado) ==="
if test_endpoint "GET" "/api/v1/empresas/?page_size=1" "" "200" "GET /api/v1/empresas/ (paginado)"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 2: Mi Empresa (Singleton) ==="
if test_endpoint "GET" "/api/v1/empresas/mi-empresa/" "" "200" "GET /api/v1/empresas/mi-empresa/ (200 o 204)"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 3: Detalle por ID ==="
# Nota: Requiere que exista una empresa con ID conocido
if test_endpoint "GET" "/api/v1/empresas/34/" "" "200" "GET /api/v1/empresas/34/"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 4: Crear Empresa (POST) ==="
create_data='{
  "razon_social": "Empresa Test Script",
  "nit": "999999999",
  "dv": "9",
  "direccion": "Calle Test",
  "telefono": "1234567890",
  "email_contacto": "test@example.com",
  "regimen_tributario": "NO_RESPONDE",
  "moneda": "COP"
}'
if test_endpoint "POST" "/api/v1/empresas/" "$create_data" "201" "POST /api/v1/empresas/ (crear)"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 5: Crear Empresa Duplicada (409) ==="
if test_endpoint "POST" "/api/v1/empresas/" "$create_data" "409" "POST /api/v1/empresas/ (singleton violation)"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 6: Core Orchestrator - Upsert (PATCH) ==="
upsert_data='{
  "razon_social": "Empresa Actualizada vía Core",
  "telefono": "9876543210"
}'
if test_endpoint "PATCH" "/api/v1/core/empresa/" "$upsert_data" "200" "PATCH /api/v1/core/empresa/ (upsert)"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 7: MailInboxConfig - Listar ==="
if test_endpoint "GET" "/api/v1/empresas/mail-inbox-config/" "" "200" "GET /api/v1/empresas/mail-inbox-config/"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=== PRUEBA 8: MailInboxConfig - Crear ==="
mailinbox_data='{
  "nombre": "Buzón Test",
  "email_address": "test@example.com",
  "provider": "custom",
  "imap_host": "imap.example.com",
  "imap_port": 993,
  "imap_username": "test@example.com",
  "imap_password": "test123",
  "imap_ssl": true,
  "is_active": true
}'
if test_endpoint "POST" "/api/v1/empresas/mail-inbox-config/" "$mailinbox_data" "201" "POST /api/v1/empresas/mail-inbox-config/ (crear)"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

# Resumen
echo "=========================================="
echo "RESUMEN"
echo "=========================================="
echo -e "${GREEN}Pruebas exitosas: $passed${NC}"
echo -e "${RED}Pruebas fallidas: $failed${NC}"
echo "Total: $((passed + failed))"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✓ TODAS LAS PRUEBAS PASARON${NC}"
    exit 0
else
    echo -e "${RED}✗ ALGUNAS PRUEBAS FALLARON${NC}"
    exit 1
fi
