import uuid

from django.db import migrations, models


def populate_itemfactura_uuid(apps, schema_editor):
    ItemFactura = apps.get_model("facturas", "ItemFactura")
    for item in ItemFactura.objects.filter(uuid__isnull=True).iterator():
        item.uuid = uuid.uuid4()
        item.save(update_fields=["uuid"])


def populate_notacredito_uuid(apps, schema_editor):
    NotaCredito = apps.get_model("facturas", "NotaCredito")
    for nota in NotaCredito.objects.filter(uuid__isnull=True).iterator():
        nota.uuid = uuid.uuid4()
        nota.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("facturas", "0022_factura_proveedor_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemfactura",
            name="uuid",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                editable=False,
                help_text="Identificador publico del item de factura",
                null=True,
                verbose_name="UUID",
            ),
        ),
        migrations.AddField(
            model_name="notacredito",
            name="uuid",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                editable=False,
                help_text="Identificador publico de la nota credito",
                null=True,
                verbose_name="UUID",
            ),
        ),
        migrations.RunPython(populate_itemfactura_uuid, migrations.RunPython.noop),
        migrations.RunPython(populate_notacredito_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="itemfactura",
            name="uuid",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                help_text="Identificador publico del item de factura",
                unique=True,
                verbose_name="UUID",
            ),
        ),
        migrations.AlterField(
            model_name="notacredito",
            name="uuid",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                help_text="Identificador publico de la nota credito",
                unique=True,
                verbose_name="UUID",
            ),
        ),
    ]
