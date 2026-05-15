from django.db import migrations

def migrate_mail_configs(apps, schema_editor):
    MailIngestionConfig = apps.get_model('facturas', 'MailIngestionConfig')
    MailInboxConfig = apps.get_model('empresa', 'MailInboxConfig')
    
    for old_config in MailIngestionConfig.objects.all():
        # Avoid duplicates based on username and host
        if not MailInboxConfig.objects.filter(
            empresa=old_config.empresa,
            imap_username=old_config.username,
            imap_host=old_config.host
        ).exists():
            MailInboxConfig.objects.create(
                empresa=old_config.empresa,
                nombre=f"Migracion: {old_config.username}",
                email_address=old_config.username if "@" in old_config.username else old_config.username,
                provider="custom",
                # Legacy fields
                host=old_config.host,
                port=old_config.port,
                protocol=old_config.protocol,
                ssl=old_config.ssl,
                username=old_config.username,
                password=old_config.password,
                mailbox=old_config.mailbox,
                mark_as_seen=old_config.mark_as_seen,
                move_processed_to=old_config.move_processed_to,
                max_attachment_mb=old_config.max_attachment_mb,
                # New IMAP fields
                imap_host=old_config.host,
                imap_port=old_config.port,
                imap_ssl=old_config.ssl,
                imap_username=old_config.username,
                imap_password=old_config.password,
                imap_mailbox=old_config.mailbox,
                imap_mark_as_seen=old_config.mark_as_seen,
                imap_move_processed_to=old_config.move_processed_to,
                imap_max_attachment_mb=old_config.max_attachment_mb,
                is_active=old_config.is_active
            )

def rollback_mail_configs(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('facturas', '0013_alter_factura_uuid'),
        ('empresa', '0007_empresa_owner_email'),
    ]

    operations = [
        migrations.RunPython(migrate_mail_configs, rollback_mail_configs),
    ]
