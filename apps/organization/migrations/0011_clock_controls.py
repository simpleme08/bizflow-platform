from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('organization', '0010_attendance_photo_retention')]
    operations = [
        migrations.AddField(model_name='organization', name='clock_geofence_enabled', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='organization', name='clock_geofence_latitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='organization', name='clock_geofence_longitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='organization', name='clock_geofence_radius_meters', field=models.PositiveIntegerField(default=250)),
        migrations.AddField(model_name='organization', name='clock_device_ids', field=models.JSONField(blank=True, default=list)),
    ]
