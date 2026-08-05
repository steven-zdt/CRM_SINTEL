"""
Tablas server-rendered (django-tables2) para el listado de Perfil.

Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md) del patron ya
aplicado en gastos/facturas/compras/contabilidad/ventas/bancos/empleados.

La columna de acciones replica exactamente la logica de permisos que antes
vivia en perfil.page.js (getColumns -> formatter de "Acciones"): usa
get_available_actions() (SSoT en apps/tenant/perfil/api/permissions.py) para
el rol del solicitante, y aplica el guard [SEG-5] que prohibe mostrar el
boton de eliminar sobre la propia fila del usuario autenticado.
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe

_SIN_DATO = mark_safe('<span class="text-muted">-</span>')

from apps.tenant.perfil.models import TenantProfile

_ROL_BADGE_MAP = {
    "ADMIN": "bg-danger",
    "OPERADOR": "bg-primary",
    "VISOR": "bg-secondary",
}


class PerfilTable(tables.Table):
    # empty_values=(): django-tables2 solo llama a render_<campo>() cuando el
    # valor no esta en empty_values (por defecto (None, '')) -- con blank=True
    # o FK nula, el valor vacio nunca invocaria el render y mostraria el
    # placeholder generico de la libreria en vez de "-" / el texto propio.
    usuario = tables.Column(accessor="user", verbose_name="Usuario", orderable=False)
    cargo = tables.Column(verbose_name="Cargo", empty_values=())
    departamento = tables.Column(accessor="departamento__nombre", verbose_name="Departamento", order_by=("departamento__nombre",), empty_values=())
    telefono_corporativo = tables.Column(verbose_name="Teléfono", empty_values=())
    rol = tables.Column(verbose_name="Rol", empty_values=())
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="Avatar")
    acciones = tables.Column(empty_values=(), orderable=False, verbose_name="")

    class Meta:
        model = TenantProfile
        fields = ()
        sequence = ("usuario", "cargo", "departamento", "telefono_corporativo", "rol", "avatar", "acciones")
        attrs = {"class": "table table-hover align-middle mb-0", "id": "tabla-perfiles"}
        empty_text = "No hay perfiles registrados"
        order_by = "user__first_name"

    def __init__(self, *args, requestor_actions=None, requestor_user_id=None, **kwargs):
        self.requestor_actions = requestor_actions or []
        self.requestor_user_id = requestor_user_id
        super().__init__(*args, **kwargs)

    def render_usuario(self, record):
        nombre = (f"{record.user.first_name} {record.user.last_name}".strip()
                  or record.user.username or record.user.email or "—")
        email = record.user.email or ""
        return format_html(
            '<div><strong>{}</strong>{}</div>',
            nombre,
            format_html('<br><small class="text-muted">{}</small>', email) if email else "",
        )

    def render_cargo(self, value):
        return value or _SIN_DATO

    def render_departamento(self, record):
        return record.departamento.nombre if record.departamento_id else _SIN_DATO

    def render_telefono_corporativo(self, value):
        return value or _SIN_DATO

    def render_rol(self, value):
        if not value:
            return _SIN_DATO
        cls = _ROL_BADGE_MAP.get(value, "bg-secondary")
        return format_html('<span class="badge {}">{}</span>', cls, value)

    def render_avatar(self, record):
        if record.avatar:
            return format_html(
                '<img src="{}" alt="Avatar" class="rounded-circle" style="width:40px;height:40px;object-fit:cover;">',
                record.avatar.url,
            )
        return mark_safe('<i class="fas fa-user-circle text-muted" style="font-size:40px;"></i>')

    def render_acciones(self, record):
        # [SEG-5] Prohibido auto-eliminacion: nunca mostrar el boton "eliminar"
        # sobre la propia fila del usuario autenticado, aunque su rol lo permita.
        is_self = self.requestor_user_id is not None and record.user_id == self.requestor_user_id
        can_edit = "edit" in self.requestor_actions
        can_assign_rol = "assign_rol" in self.requestor_actions
        can_delete = "delete" in self.requestor_actions and not is_self

        btns = format_html(
            '<button type="button" class="btn btn-outline-primary" data-action="ver" data-id="{}" title="Ver Perfil">'
            '<i class="fas fa-eye"></i></button>',
            record.uuid,
        )
        if can_edit:
            btns += format_html(
                '<button type="button" class="btn btn-outline-success" data-action="editar" data-id="{}" title="Editar Perfil">'
                '<i class="fas fa-edit"></i></button>',
                record.uuid,
            )
        if can_assign_rol:
            btns += format_html(
                '<button type="button" class="btn btn-outline-warning" data-action="asignar-rol" data-id="{}" title="Asignar Rol">'
                '<i class="fas fa-user-shield"></i></button>',
                record.uuid,
            )
        if can_delete:
            btns += format_html(
                '<button type="button" class="btn btn-outline-danger" data-action="eliminar" data-id="{}" title="Eliminar Perfil">'
                '<i class="fas fa-trash"></i></button>',
                record.uuid,
            )
        return format_html('<div class="btn-group btn-group-sm" role="group">{}</div>', btns)
