#!/usr/bin/env bash
set -euo pipefail

# ============ CONFIG ============
BASE_URL="${BASE_URL:-https://<tu-dominio-tenant>}"   # p.ej., https://home.sintel.com
XML_FILE="${XML_FILE:-./samples/invoice_min.xml}"     # ruta al XML a subir
COOKIE_JAR="${COOKIE_JAR:-./cookies.txt}"             # asume sesión ya autenticada en este jar
CURL="curl -sS --fail-with-body"
JQ="${JQ:-jq}"                                        # requiere 'jq'
POLL_INTERVAL="${POLL_INTERVAL:-2}"                   # segundos
POLL_MAX="${POLL_MAX:-90}"                            # intentos

# ============ HELPERS ============
log()  { echo -e "[SMOKE] $*"; }
die()  { echo -e "[SMOKE:ERROR] $*" >&2; exit 1; }

# ============ STEP 0: Health ============
log "Healthcheck..."
$CURL -b "$COOKIE_JAR" "${BASE_URL}/api/v1/core/health/" | $JQ .

# ============ STEP 1: Upload (async) ============
log "Subiendo XML (async=true) ..."
UPLOAD_JSON=$($CURL -b "$COOKIE_JAR" -F "file=@${XML_FILE}" \
  "${BASE_URL}/api/v1/facturas/upload-ubl/?async=true")
echo "$UPLOAD_JSON" | $JQ .
TASK_ID=$(echo "$UPLOAD_JSON" | $JQ -r '.task_id // empty') || true
[[ -n "$TASK_ID" ]] || die "No se recibió task_id en upload"

# ============ STEP 2: Poll status ============
log "Haciendo polling de estado (task_id=$TASK_ID) ..."
ATTEMPT=0
DTO=""
while (( ATTEMPT < POLL_MAX )); do
  ((ATTEMPT++))
  sleep "$POLL_INTERVAL"
  STATUS_JSON=$($CURL -b "$COOKIE_JAR" "${BASE_URL}/api/v1/facturas/ingest/${TASK_ID}/status/")
  STATE=$(echo "$STATUS_JSON" | $JQ -r '.state // empty')
  if [[ "$STATE" == "SUCCESS" ]]; then
    DTO=$(echo "$STATUS_JSON" | $JQ -c '.result')
    break
  elif [[ "$STATE" == "FAILURE" ]]; then
    echo "$STATUS_JSON" | $JQ .
    die "La ingesta falló."
  fi
done
[[ -n "$DTO" ]] || die "Timeout esperando SUCCESS"

# ============ STEP 3: Materialize ============
log "Materializando factura ..."
MAT_JSON=$($CURL -b "$COOKIE_JAR" -H "Content-Type: application/json" \
  -d "{\"dto\": ${DTO}, \"persist_anexos\": true}" \
  -X POST "${BASE_URL}/api/v1/facturas/materialize/")
echo "$MAT_JSON" | $JQ .
FACT_ID=$(echo "$MAT_JSON" | $JQ -r '.id // empty')
FACT_NUM=$(echo "$MAT_JSON" | $JQ -r '.numero // empty')
[[ -n "$FACT_ID" ]] || die "No se obtuvo id de factura"

# ============ STEP 4: List y ver Naturaleza ============
log "Listando facturas (ver Naturaleza) ..."
LIST_JSON=$($CURL -b "$COOKIE_JAR" "${BASE_URL}/api/v1/facturas/?ordering=-fecha_emision&page=1&page_size=10")
echo "$LIST_JSON" | $JQ '[.results[] | {numero, naturaleza}]'

# ============ STEP 5: Detail y anexos ============
log "Detalle de factura id=$FACT_ID ..."
DET_JSON=$($CURL -b "$COOKIE_JAR" "${BASE_URL}/api/v1/facturas/${FACT_ID}/")
echo "$DET_JSON" | $JQ .
HAS_UBL=$(echo "$DET_JSON" | $JQ -r '.has_ubl_xml')
HAS_APP=$(echo "$DET_JSON" | $JQ -r '.has_application_response_xml')

if [[ "$HAS_UBL" == "true" ]]; then
  log "Descargando/verificando UBL ..."
  $CURL -b "$COOKIE_JAR" "${BASE_URL}/api/v1/facturas/${FACT_ID}/xml/" | head -c 200 | sed 's/.*/& .../g'
fi

if [[ "$HAS_APP" == "true" ]]; then
  log "Descargando/verificando ApplicationResponse ..."
  $CURL -b "$COOKIE_JAR" "${BASE_URL}/api/v1/facturas/${FACT_ID}/app-response/" | head -c 200 | sed 's/.*/& .../g'
fi

log "SMOKE OK (upload → status → materialize → list → detail → anexos)"
