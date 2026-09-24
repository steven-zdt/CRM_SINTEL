#!/bin/bash
# docker/entrypoint-single.sh -- entrypoint del contenedor unico de desarrollo
# (Dockerfile.single). A diferencia de entrypoint.sh (multi-contenedor, que
# orquesta migraciones/espera de un solo proceso Django), aqui supervisord es
# quien orquesta los 9 procesos -- cada uno con su propio script de arranque
# en docker/start-*.sh (esperas e idempotencia via docker/wait-for.sh). Este
# entrypoint solo debe arrancar supervisord como root (necesario: supervisord
# hace setuid a postgres/appuser por programa via `user=` en supervisord.conf,
# y nginx necesita bind en el puerto 80/443).
set -e
exec supervisord -c /app/docker/supervisord.conf
