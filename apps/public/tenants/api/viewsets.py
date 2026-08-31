"""
ViewSets para la app tenants.

WARNING: IMPORTANTE: Solo administradores pueden gestionar tenants.
- Autenticación: SessionAuthentication para permitir cookies de sesión desde la UI

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""

from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.public.tenants.api.filters import ClientFilter
from apps.public.tenants.api.serializers import ClientSerializer, DomainSerializer
from apps.public.tenants.models import Client, Domain


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD completo para Client (solo administradores).

    WARNING: IMPORTANTE:
    - CRUD completo para uso administrativo exclusivo (requiere IsAdminUser)
    - La creación de tenants puede hacerse mediante el servicio de onboarding o por API
    - Todas las operaciones requieren permisos de administrador
    - Autenticación: SessionAuthentication (cookies de sesión desde UI)
    """

    authentication_classes = [SessionAuthentication]
    # Queryset optimizado: solo campos necesarios, sin prefetch pesado de membresías
    # WARNING: OPTIMIZACIÓN: No hacer prefetch de membresías para evitar 500 y reducir carga
    # Para API pública/admin: usar only() para reducir carga
    # Excluir el tenant público y el tenant de prueba ('test') que se crea durante
    # la ejecución de tests para evitar que aparezca en APIs públicas.
    queryset = (
        Client.objects.exclude(schema_name__in=["public", "test"]).only(
            "id", "schema_name", "nombre", "created_on", "is_active", "on_trial", "paid_until"
        )
        .prefetch_related("domains")
        .order_by("-created_on")
    )
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAdminUser]  # Solo admins

    def get_queryset(self):
        """
        Queryset optimizado según la acción.

        WARNING: OPTIMIZACIÓN: No hacer prefetch de membresías para evitar 500 y reducir carga.
        Si se necesitan membresías en admin, usar un serializer separado.
        """
        import logging

        logger = logging.getLogger(__name__)
        try:
            # Snapshot current clients for debug in tests (schema_name and nombre)
            snapshot = list(Client.objects.values("id", "schema_name", "nombre"))
            logger.info("ClientViewSet.get_queryset snapshot count=%s clients=%s", len(snapshot), snapshot)
        except Exception:
            logger.exception("ClientViewSet.get_queryset: failed to snapshot clients")

        return super().get_queryset()

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ClientFilter  # Usar FilterSet personalizado para booleanos
    search_fields = ["nombre", "schema_name"]
    ordering_fields = ["nombre", "created_on", "paid_until"]
    ordering = ["-created_on"]

    def _log_console_action(self, request, *, action: str, client=None, target_user=None, metadata: dict = None):
        """
        Registra una accion administrativa en ConsoleActionLog.

        CONSOLE_TENANTS_CRUD (docs/console/TENANT_LIFECYCLE.md, hallazgo
        E2E-05 de la auditoria de onboarding previa): antes de esto,
        ninguna accion de ClientViewSet dejaba rastro auditable pese a que
        el modelo y sus choices (TENANT_CREATE/UPDATE/DELETE) existen
        desde la migracion inicial. `metadata` nunca debe incluir
        passwords/tokens/secretos -- solo datos operativos (estados,
        fechas, motivos).
        """
        import logging

        logger = logging.getLogger(__name__)
        try:
            from apps.public.console.models import ConsoleActionLog

            actor = request.user if getattr(request.user, "is_authenticated", False) else None
            ConsoleActionLog.objects.create(
                action=action,
                actor=actor,
                tenant=client,
                target_user=target_user,
                metadata=metadata or {},
            )
        except Exception:
            # La auditoria nunca debe romper la operacion administrativa real.
            logger.error("[ConsoleActionLog] No se pudo registrar accion=%s", action, exc_info=True)

    @action(detail=False, methods=["post"], url_path="onboard", url_name="onboard")
    def onboard(self, request):
        """
        Endpoint para onboarding completo de un tenant con propietario.

        WARNING: CONTRATO ESTABLE: Retorna dict {"client_id", "domain", "membership_id", "login_url"} con 201
        Aunque el seed de perfil falle, siempre retorna login_url si User, Client, Domain y Membership se crearon.

        Crea un tenant completo con:
        - Usuario global (public) - idempotente por email, set_unusable_password() (v2.29: sin password en onboarding)
        - Client (tenant) - auto_create_schema=True crea esquema + migra TENANT_APPS automáticamente
        - Domain (dominio principal) - sin puerto ni www (normalizado)
        - TenantMembership (usuario propietario) - en public, rol=ADMIN, is_primary_admin=True
        - (Opcional) Seed de perfil si la tabla existe - dentro de schema_context, solo si tabla existe

        WARNING: PERMISOS: Requiere IsAdminUser (solo staff puede crear tenants)

        Payload esperado:
        {
            "nombre": "Empresa X",  # Requerido
            "schema_name": "empresa_x",  # Requerido
            "dominio_fqdn": "empresa-x.localhost",  # Opcional (se autogenera como <schema>.<TENANT_DOMAIN_BASE>)
            "owner_email": "owner@empresa-x.com",  # Requerido (si no se proporciona admin_user_id)
            # WARNING: v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
            "admin_user_id": 1,  # Opcional (alternativa a owner_email)
            "owner_is_staff": false,  # Opcional, default: false (E2E-03 -- owners de tenant NO son staff del sistema)
            "owner_is_active": true,  # Opcional, default: true
            "paid_until": "2024-12-31",  # Opcional
            "on_trial": true  # Opcional, default: true
        }

        Returns:
            Response 201 Created con dict: {
                "client_id": int,
                "domain": str,
                "membership_id": int,
                "login_url": str
            }

        Raises:
            Response 400 Bad Request: Si hay errores de validación (ValidationError, ValueError)
            Response 403 Forbidden: Si el usuario no es staff (IsAdminUser)
            Response 500 Internal Server Error: Si hay errores inesperados
        """
        # Compat: algunos clientes/tests usan el endpoint legacy '/tenants/create/'
        # con keys 'nombre', 'dominio' y 'email_admin' que esperan que se invoque
        # a `apps.services.onboarding.empresa_service.crear_empresa`.
        # Soporte ambos flujos: el API moderno (OnboardTenantWithOwnerSerializer)
        # y el legacy (dominio/email_admin) para mantener compatibilidad.
        import logging

        from apps.public.tenants.api.serializers import OnboardTenantWithOwnerSerializer
        from apps.services.onboarding.empresa_service import (
            crear_empresa,
            crear_tenant_con_owner,
        )

        logger = logging.getLogger(__name__)

        # Legacy payload support (console UI and older tests)
        if isinstance(request.data, dict) and (
            "email_admin" in request.data or "dominio" in request.data
        ):
            # Map legacy keys to crear_empresa signature. The service accepts
            # arbitrary kwargs, so passing 'dominio' for compatibility is fine
            nombre = request.data.get("nombre")
            dominio = request.data.get("dominio")
            email_admin = request.data.get("email_admin")
            on_trial = request.data.get("on_trial", True)

            if not nombre or not email_admin:
                return Response({"error": "Faltan campos requeridos"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                payload = crear_empresa(nombre=nombre, email_admin=email_admin, dominio=dominio, on_trial=on_trial)
                logger.info("OK: Onboarding (legacy) exitoso: nombre=%s, dominio=%s", nombre, dominio)
                self._log_console_action(
                    request, action="TENANT_CREATE", client=payload.get("client"),
                    metadata={"flujo": "legacy", "nombre": nombre, "dominio": dominio},
                )
                return Response(payload, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.exception("Onboarding (legacy) error: %s", e)
                return Response({"error": "Error al crear el tenant"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = OnboardTenantWithOwnerSerializer(data=request.data)
        if not serializer.is_valid():
            # Errores de validación del serializer (campos requeridos, formatos, etc.)
            errors = serializer.errors
            # Log detallado por campo
            for field, field_errors in errors.items():
                logger.warning(
                    "Onboarding 400 - Campo '%s': %s | Payload recibido: nombre=%s, schema_name=%s, dominio_fqdn=%s, owner_email=%s",
                    field,
                    field_errors,
                    request.data.get("nombre", "N/A"),
                    request.data.get("schema_name", "N/A"),
                    request.data.get("dominio_fqdn", "N/A"),
                    request.data.get("owner_email", "N/A"),
                )
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Crear tenant usando el servicio (retorna dict estable)
            # WARNING: CONTRATO ESTABLE: Siempre retorna dict con client_id, domain, membership_id, login_url
            # Aunque el seed de perfil falle, el onboarding debe retornar 201 con login_url
            payload = crear_tenant_con_owner(**serializer.validated_data)
            logger.info(
                "OK: Onboarding exitoso: client_id=%s, domain=%s, membership_id=%s",
                payload.get("client_id"),
                payload.get("domain"),
                payload.get("membership_id"),
            )
            client_obj = Client.objects.filter(pk=payload.get("client_id")).only("id").first()
            self._log_console_action(
                request, action="TENANT_CREATE", client=client_obj,
                metadata={
                    "flujo": "onboard",
                    "domain": payload.get("domain"),
                    "membership_id": payload.get("membership_id"),
                },
            )
            return Response(payload, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Errores de validación (dominio duplicado, schema inválido, etc.)
            error_detail = str(e)
            logger.warning(
                "Onboarding 400 - ValidationError: %s | Payload: nombre=%s, schema_name=%s, dominio_fqdn=%s",
                error_detail,
                serializer.validated_data.get("nombre", "N/A"),
                serializer.validated_data.get("schema_name", "N/A"),
                serializer.validated_data.get("dominio_fqdn", "N/A"),
            )
            return Response({"detail": error_detail}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            # Errores de valor (campos requeridos faltantes, etc.)
            error_detail = str(e)
            logger.warning(
                "Onboarding 400 - ValueError: %s | Payload: nombre=%s, schema_name=%s, owner_email=%s",
                error_detail,
                serializer.validated_data.get("nombre", "N/A"),
                serializer.validated_data.get("schema_name", "N/A"),
                serializer.validated_data.get("owner_email", "N/A"),
            )
            return Response({"detail": error_detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Errores inesperados
            logger.error(
                "Onboarding 500 - Error inesperado: %s | Payload: %s",
                str(e),
                serializer.validated_data,
                exc_info=True,
            )
            return Response(
                {"detail": "Error al crear el tenant. Por favor, contacte al administrador."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="toggle-active", url_name="toggle-active")
    def toggle_active(self, request, pk=None):
        """
        Activa o desactiva un tenant (toggle de is_active).

        WARNING: CONTRATO: POST /api/public/v1/tenants/{id}/toggle-active/
        - Sin prefetch redundantes
        - Cambia is_active y retorna {"id", "is_active", "message"}

        Cambia el estado de is_active del tenant:
        - Si is_active=True → is_active=False (suspende manualmente --
          se distingue de una desactivacion por trial vencido, ver
          docs/console/TENANT_LIFECYCLE.md)
        - Si is_active=False → is_active=True (activa)

        CONSOLE_TENANTS_CRUD (Fase 26): reactivar un tenant cuyo trial
        esta vencido (EXPIRED) NO debe limitarse a poner is_active=True --
        el middleware lo volveria a desactivar en el siguiente request
        (la fecha sigue siendo la fuente de verdad). Para reactivar un
        EXPIRED de forma persistente sin inventar un sistema de
        facturacion que no existe, esta accion saca al tenant del regimen
        de trial (on_trial=False) -- "activacion administrativa" explicita,
        sin fecha de expiracion. Si en cambio se quiere dar mas dias de
        prueba, usar la accion dedicada `extend-trial`.

        WARNING: PERMISOS: Requiere IsAdminUser (solo staff puede cambiar estado de tenants)

        Returns:
            Response 200 OK con: {
                "id": int,
                "is_active": bool,
                "message": str
            }
        """
        try:
            from apps.public.tenants.services.lifecycle import compute_lifecycle_status

            client = self.get_object()
            estado_antes = compute_lifecycle_status(client)
            nuevo_is_active = not client.is_active

            update_fields = ["is_active"]
            client.is_active = nuevo_is_active

            reactivacion_administrativa = nuevo_is_active and estado_antes == "EXPIRED"
            if reactivacion_administrativa:
                client.on_trial = False
                update_fields.append("on_trial")

            client.save(update_fields=update_fields)

            self._log_console_action(
                request,
                action="TENANT_UPDATE",
                client=client,
                metadata={
                    "operacion": "toggle_active",
                    "estado_lifecycle_antes": estado_antes,
                    "is_active_despues": nuevo_is_active,
                    "reactivacion_administrativa": reactivacion_administrativa,
                },
            )

            serializer = self.get_serializer(client)
            action = "activado" if client.is_active else "desactivado"
            message = f'Tenant "{client.nombre}" {action} exitosamente'
            if reactivacion_administrativa:
                message += " (retirado del regimen de prueba -- activacion administrativa)"

            return Response(
                {
                    "id": client.id,
                    "is_active": client.is_active,
                    "message": message,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error al cambiar estado del tenant: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="extend-trial", url_name="extend-trial")
    def extend_trial(self, request, pk=None):
        """
        Extiende (o define) el periodo de prueba de un tenant.

        POST /api/public/v1/tenants/{id}/extend-trial/
        Body: {"days": int} O {"paid_until": "YYYY-MM-DD"}, "motivo": str (opcional)

        CONSOLE_TENANTS_CRUD (Fase 25): accion auditada, autorizada
        (IsAdminUser, mismo permiso que el resto del ViewSet) e
        idempotente (llamarla dos veces con el mismo `paid_until` produce
        el mismo resultado final, sin efectos acumulativos duplicados --
        `days` SI acumula sobre el paid_until actual/hoy, por diseño,
        pero no es "silenciosa": siempre queda registrada en
        ConsoleActionLog con estado antes/despues, actor y motivo.

        Si el tenant estaba EXPIRED o SUSPENDED_BY_ADMIN, esta accion lo
        reactiva (is_active=True, on_trial=True) siempre que la nueva
        fecha sea futura -- resuelve el lifecycle explicitamente en vez
        de solo tocar is_active (Fase 26).

        Returns 200: {"id", "paid_until", "on_trial", "is_active", "lifecycle_status"}
        Returns 400: sin days/paid_until, fecha invalida, o fecha no futura
        """
        import logging

        from django.utils import timezone

        from apps.public.tenants.services.lifecycle import compute_lifecycle_status

        logger = logging.getLogger(__name__)
        client = self.get_object()

        days = request.data.get("days")
        paid_until_raw = request.data.get("paid_until")
        motivo = (request.data.get("motivo") or "").strip()

        if not days and not paid_until_raw:
            return Response(
                {"detail": "Se requiere 'days' (int) o 'paid_until' (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        estado_antes = compute_lifecycle_status(client)
        paid_until_antes = client.paid_until

        if paid_until_raw:
            from datetime import date

            try:
                nueva_fecha = date.fromisoformat(str(paid_until_raw))
            except ValueError:
                return Response(
                    {"detail": "paid_until invalido. Formato esperado: YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                dias_int = int(days)
            except (TypeError, ValueError):
                return Response({"detail": "'days' debe ser un entero."}, status=status.HTTP_400_BAD_REQUEST)
            if dias_int <= 0:
                return Response({"detail": "'days' debe ser positivo."}, status=status.HTTP_400_BAD_REQUEST)
            base = client.paid_until if (client.paid_until and client.paid_until >= timezone.localdate()) else timezone.localdate()
            nueva_fecha = base + timezone.timedelta(days=dias_int)

        if nueva_fecha <= timezone.localdate():
            return Response(
                {"detail": "La nueva fecha de expiracion debe ser futura."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client.paid_until = nueva_fecha
        client.on_trial = True
        update_fields = ["paid_until", "on_trial"]
        if not client.is_active:
            client.is_active = True
            update_fields.append("is_active")
        client.save(update_fields=update_fields)

        estado_despues = compute_lifecycle_status(client)

        self._log_console_action(
            request,
            action="EXTEND_TRIAL",
            client=client,
            metadata={
                "paid_until_antes": paid_until_antes.isoformat() if paid_until_antes else None,
                "paid_until_despues": nueva_fecha.isoformat(),
                "estado_lifecycle_antes": estado_antes,
                "estado_lifecycle_despues": estado_despues,
                "motivo": motivo or None,
            },
        )
        logger.info(
            "[LIFECYCLE] Trial extendido: schema=%s paid_until %s -> %s (actor=%s)",
            client.schema_name, paid_until_antes, nueva_fecha,
            getattr(request.user, "email", "?"),
        )

        return Response(
            {
                "id": client.id,
                "paid_until": client.paid_until.isoformat(),
                "on_trial": client.on_trial,
                "is_active": client.is_active,
                "lifecycle_status": estado_despues,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="resend-invitation", url_name="resend-invitation")
    def resend_invitation(self, request, pk=None):
        """
        Regenera y reenvía el email de invitación al admin primario del tenant.

        POST /api/public/v1/tenants/{id}/resend-invitation/

        Util cuando:
        - El token de activación expiró (TTL 24h) o fue corrompido en tránsito
        - El email original no fue recibido (backend console en desarrollo)
        - Usuario con set_unusable_password() aún no ha activado su cuenta

        WARNING: PERMISOS: Requiere IsAdminUser.
        WARNING: Se bloquea si el usuario ya tiene contraseña usable (ya activado).

        Returns 200: {"activation_url", "user_email", "email_sent", "detail"}
        Returns 400: admin primario no encontrado o sin dominio primario
        Returns 409: usuario ya activó su cuenta
        """
        import logging

        from apps.public.tenants.models import TenantMembership

        logger = logging.getLogger(__name__)

        client = self.get_object()

        # Obtener admin primario del tenant
        membership = (
            TenantMembership.objects.filter(
                client=client,
                is_primary_admin=True,
                is_active=True,
            )
            .select_related("user")
            .only("user__id", "user__email", "user__password")
            .first()
        )

        if not membership:
            return Response(
                {"detail": "No se encontro el admin primario del tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = membership.user

        # Bloquear reenvío si el usuario ya tiene contraseña usable (ya activado)
        if user.has_usable_password():
            return Response(
                {"detail": "El usuario ya activo su cuenta. No se requiere reenvio de invitacion."},
                status=status.HTTP_409_CONFLICT,
            )

        # Obtener dominio primario del tenant
        domain = (
            Domain.objects.filter(tenant=client, is_primary=True)
            .only("domain")
            .first()
        )

        if not domain:
            return Response(
                {"detail": "El tenant no tiene un dominio primario configurado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.public.tenants.services.invitations import (
                build_activation_url,
                generate_invitation_token,
                send_invitation_email,
            )

            token = generate_invitation_token(user_id=user.id, tenant_id=client.id)
            activation_url = build_activation_url(domain.domain, token)
            sent = send_invitation_email(user, client, activation_url)

            if sent:
                logger.info(
                    "[RESEND-INVITATION] Enviada: user=%s, tenant=%s",
                    user.email, client.schema_name,
                )
            else:
                logger.warning(
                    "[RESEND-INVITATION] Email no enviado: user=%s, tenant=%s | url=%s",
                    user.email, client.schema_name, activation_url,
                )

            return Response(
                {
                    "detail": "Invitacion reenviada.",
                    "activation_url": activation_url,
                    "user_email": user.email,
                    "email_sent": sent,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                "[RESEND-INVITATION] Error: tenant=%s | %s",
                client.schema_name, str(e), exc_info=True,
            )
            return Response(
                {"detail": f"Error al reenviar invitacion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="manual-activate", url_name="manual-activate")
    def manual_activate(self, request, pk=None):
        """
        Genera link de activacion para el admin primario SIN enviar email.

        POST /api/public/v1/tenants/{id}/manual-activate/

        Uso de emergencia cuando el token de invitacion no llego o expiro.
        El admin puede copiar la URL de activacion y enviarsela al owner por
        cualquier otro canal (WhatsApp, Slack, etc.).

        Returns 200: {"activation_url", "user_email", "expires_in"}
        Returns 409: usuario ya activo su cuenta
        Returns 400: sin admin primario o sin dominio primario
        """
        import logging

        from apps.public.tenants.models import TenantMembership

        logger = logging.getLogger(__name__)
        client = self.get_object()

        membership = (
            TenantMembership.objects.filter(
                client=client,
                is_primary_admin=True,
                is_active=True,
            )
            .select_related("user")
            .only("user__id", "user__email", "user__password")
            .first()
        )

        if not membership:
            return Response(
                {"detail": "No se encontro el admin primario del tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = membership.user

        if user.has_usable_password():
            return Response(
                {"detail": "El usuario ya activo su cuenta. No necesita activacion."},
                status=status.HTTP_409_CONFLICT,
            )

        domain = Domain.objects.filter(tenant=client, is_primary=True).only("domain").first()
        if not domain:
            return Response(
                {"detail": "El tenant no tiene un dominio primario configurado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.public.tenants.services.invitations import (
                build_activation_url,
                generate_invitation_token,
            )

            token = generate_invitation_token(user_id=user.id, tenant_id=client.id, ttl_hours=48)
            activation_url = build_activation_url(domain.domain, token)

            logger.info(
                "[MANUAL-ACTIVATE] URL generada sin email: user=%s, tenant=%s",
                user.email, client.schema_name,
            )

            return Response(
                {
                    "activation_url": activation_url,
                    "user_email": user.email,
                    "expires_in": "48 horas",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                "[MANUAL-ACTIVATE] Error: tenant=%s | %s",
                client.schema_name, str(e), exc_info=True,
            )
            return Response(
                {"detail": f"Error generando URL de activacion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="admin-set-password", url_name="admin-set-password")
    def admin_set_password(self, request, pk=None):
        """
        Establece una contrasena directamente para el owner del tenant.

        POST /api/public/v1/tenants/{id}/admin-set-password/
        Body: {"password": "..."}

        Activacion de emergencia total — bypassa completamente el flujo de token.
        El admin elige la contrasena que luego puede compartir con el owner.

        Returns 200: {"detail", "user_email"}
        Returns 400: contrasena invalida o sin admin primario
        """
        import logging

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        from apps.public.tenants.models import TenantMembership

        logger = logging.getLogger(__name__)
        client = self.get_object()

        password = request.data.get("password", "").strip()
        if not password:
            return Response(
                {"detail": "Se requiere el campo 'password'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(password) < 8:
            return Response(
                {"detail": "La contrasena debe tener al menos 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = (
            TenantMembership.objects.filter(
                client=client,
                is_primary_admin=True,
                is_active=True,
            )
            .select_related("user")
            .only("user__id", "user__email", "user__is_active")
            .first()
        )

        if not membership:
            return Response(
                {"detail": "No se encontro el admin primario del tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = membership.user

        try:
            validate_password(password, user=user)
        except DjangoValidationError as ve:
            return Response(
                {"detail": " ".join(ve.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])

        logger.warning(
            "[ADMIN-SET-PASSWORD] Contrasena establecida por admin de consola: "
            "user=%s, tenant=%s, admin=%s",
            user.email, client.schema_name, request.user.email,
        )

        return Response(
            {
                "detail": f"Contrasena establecida correctamente para {user.email}.",
                "user_email": user.email,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Hard Delete de tenant (eliminación permanente).

        WARNING: OPERACIÓN IRREVERSIBLE:
        - Elimina el esquema PostgreSQL del tenant (drop schema)
        - Elimina Client, Domain(s) y TenantMembership(s) del esquema public

        WARNING: PRECONDICIONES OBLIGATORIAS:
        1. schema != 'public' (el tenant público NO puede eliminarse)
        2. is_active == False (el tenant debe estar suspendido antes de eliminarlo)

        WARNING: MECANISMO:
        - Activar auto_drop_schema=True temporalmente
        - client.delete() para drop del esquema (mecanismo soportado por django-tenants)
        - Limpiar relaciones en public (Domains/Memberships) si no hay CASCADE

        WARNING: PERMISOS: Requiere IsAdminUser (solo staff puede eliminar tenants)

        WARNING: AUDITORÍA: Logs de seguridad registrados en logger 'security.tenants'

        Returns:
            Response 204 No Content si se elimina exitosamente
            Response 400 Bad Request si el tenant está activo
            Response 403 Forbidden si se intenta eliminar el tenant público

        Referencias:
        - django-tenants: https://django-tenants.readthedocs.io/en/latest/use.html
        - auto_drop_schema: https://django-tenants.readthedocs.io/en/latest/use.html#deleting-tenants
        """
        from apps.public.tenants.services.deletion_service import hard_delete_tenant

        try:
            client = self.get_object()

            # BLOQUEO ABSOLUTO DEL TENANT PÚBLICO (defensa en profundidad - capa API)
            from django_tenants.utils import get_public_schema_name

            public_schema = get_public_schema_name()
            if client.schema_name == public_schema:
                import logging

                logger = logging.getLogger("security.tenants")
                import datetime

                logger.critical(
                    f"🚨 API: INTENTO DE ELIMINAR TENANT PÚBLICO RECHAZADO | "
                    f"schema={public_schema} | "
                    f"user_id={request.user.id if request.user.is_authenticated else None} | "
                    f"ip={request.META.get('REMOTE_ADDR', 'unknown')} | "
                    f"time={datetime.datetime.now().isoformat()}"
                )
                return Response(
                    {
                        "error": "El esquema público no puede eliminarse bajo ningún motivo.",
                        "detail": "El tenant público es el núcleo del sistema y es indeletable.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Precondición: is_active == False
            if client.is_active:
                return Response(
                    {
                        "error": "El tenant debe estar suspendido (is_active=False) antes de eliminarlo definitivamente.",
                        "detail": 'Primero desactiva el tenant usando el botón "Desactivar" o el endpoint /toggle-active/.',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Obtener ID del usuario que ejecuta la acción (para auditoría)
            actor_user_id = request.user.id if request.user.is_authenticated else None

            # Ejecutar hard delete y eliminar usuarios huérfanos asociados al tenant
            # (usuarios cuyo único TenantMembership era este tenant y que no son staff/superuser)
            hard_delete_tenant(
                client_id=client.id, actor_user_id=actor_user_id, delete_orphan_users=True
            )

            return Response(
                {"message": f'Tenant "{client.nombre}" eliminado permanentemente'},
                status=status.HTTP_204_NO_CONTENT,
            )

        except ValidationError as e:
            # Error de validación (incluye bloqueo de tenant público)
            error_msg = str(e)
            if "público" in error_msg.lower() or "public" in error_msg.lower():
                return Response({"error": error_msg}, status=status.HTTP_403_FORBIDDEN)
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error en hard delete tenant: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Error al eliminar el tenant: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DomainViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet ReadOnly para Domain (solo administradores).

    WARNING: IMPORTANTE:
    - Solo lectura para uso administrativo
    - La creación de dominios debe hacerse mediante el servicio de onboarding
    """

    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [permissions.IsAdminUser]  # Solo admins
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_primary", "tenant"]
    search_fields = ["domain"]
    ordering_fields = ["domain", "is_primary"]
    ordering = ["domain"]


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r"tenants", ClientViewSet, "tenant"),
    (r"domains", DomainViewSet, "domain"),
]
