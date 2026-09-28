from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('talent', '0001_initial')]
    operations = [
        migrations.AddField(model_name='offboardingrecord', name='required_document_types', field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name='offboardingrecord', name='required_clearances', field=models.JSONField(blank=True, default=list)),
    ]
