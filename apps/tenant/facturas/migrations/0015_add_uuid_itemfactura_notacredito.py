import uuid
from django.db import migrations, models


def populate_uuid_itemfactura(apps, schema_editor):
    ItemFactura = apps.get_model('facturas', 'ItemFactura')
    for item in ItemFactura.objects.filter(uuid__isnull=True).iterator():
        item.uuid = uuid.uuid4()
        item.save(update_fields=['uuid'])


def populate_uuid_notacredito(apps, schema_editor):
    NotaCredito = apps.get_model('facturas', 'NotaCredito')
    for nota_credito in NotaCredito.objects.filter(uuid__isnull=True).iterator():
        nota_credito.uuid = uuid.uuid4()
        nota_credito.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('facturas', '0014_migrate_mail_ingestion_to_mail_inbox'),
    ]

    operations = [
        # Step 1: Add nullable (safe for existing rows)
        migrations.AddField(
            model_name='itemfactura',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name='notacredito',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),

        # Step 2: Populate for existing records
        migrations.RunPython(populate_uuid_itemfactura, migrations.RunPython.noop),
        migrations.RunPython(populate_uuid_notacredito, migrations.RunPython.noop),

        # Step 3: Make required and unique
        migrations.AlterField(
            model_name='itemfactura',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='notacredito',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
