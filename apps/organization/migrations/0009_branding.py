from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('organization', '0008_attendance_policy')]
    operations = [
        migrations.AddField(model_name='organization', name='brand_name', field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name='organization', name='logo_url', field=models.URLField(blank=True)),
        migrations.AddField(model_name='organization', name='primary_color', field=models.CharField(default='#1f2937', max_length=20)),
    ]
