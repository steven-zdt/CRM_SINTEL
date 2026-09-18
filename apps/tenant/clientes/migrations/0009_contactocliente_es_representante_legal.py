from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenant_clientes", "0008_cartera"),
    ]

    operations = [
        migrations.AddField(
            model_name="contactocliente",
            name="es_representante_legal",
            field=models.BooleanField(
                default=False,
                help_text="Marca a este contacto como el representante legal del cliente (requerido si Cliente.tipo_persona=JURIDICA)",
            ),
        ),
    ]
