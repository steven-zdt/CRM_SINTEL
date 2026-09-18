"""
F33.9/F33.6/F33.8: primitivas de UI compartidas server-side.

No son componentes JS -- este proyecto es HTMX + Bootstrap 5.3 +
django-tables2, sin build step; una card o un badge son presentacionales,
se renderizan del lado del servidor igual que {% render_table %}. Ver
documentacion/F33_CORE_UI_CONTRACT.md para el razonamiento completo.

Cada tag renderiza EXACTAMENTE el markup ya identificado en
documentacion/F33_SHARED_UI_INVENTORY.md -- no se cambia ningun pixel de
lo que ya funciona, solo se deja de copiar-pegar.
"""
from django import template

register = template.Library()


@register.inclusion_tag('tenant/core/partials/ui/kpi_card.html')
def sintel_kpi_card(icon, color, value, label, col_class='col-6 col-md-4 col-xl-2', value_id=None):
    """
    Card de metrica (icono en circulo + numero + label), F33.0 §1 --
    copiada verbatim en 7 archivos antes de esta consolidacion.

    Uso: {% sintel_kpi_card icon="people" color="primary" value=kpis.total label="Total" %}

    `value_id` (opcional): id HTML en el div del valor, para modulos que aun
    no migraron su grilla a django-tables2+HTMX (Fase 5-BIS) y actualizan el
    KPI via JS client-side (`document.getElementById(...)`) en vez de
    recibirlo ya resuelto en el context del render server-side.
    """
    return {
        'icon': icon,
        'color': color,
        'value': value,
        'label': label,
        'col_class': col_class,
        'value_id': value_id,
    }


@register.inclusion_tag('tenant/core/partials/ui/empty_state.html')
def sintel_empty_state(entity_label, data_attr=None):
    """
    Estado vacio (icono bi-inbox + texto), F33.0 §3b -- patron hand-rolled
    encontrado en 6 archivos + 1 sub-variante.

    Uso: {% sintel_empty_state "No hay contactos registrados" data_attr="contactos" %}
    """
    return {
        'entity_label': entity_label,
        'data_attr': data_attr,
    }
