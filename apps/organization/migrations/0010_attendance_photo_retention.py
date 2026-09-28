from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('organization', '0009_branding')]
    operations = [migrations.AddField(model_name='organization', name='attendance_photo_retention_days', field=models.PositiveIntegerField(default=90))]
