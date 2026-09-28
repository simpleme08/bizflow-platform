from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('organization', '0006_billing_records')]
    operations = [
        migrations.AddField(
            model_name='organization',
            name='audit_retention_days',
            field=models.PositiveIntegerField(default=3650),
        ),
        migrations.AddField(
            model_name='organization',
            name='document_retention_days',
            field=models.PositiveIntegerField(default=3650),
        ),
    ]
