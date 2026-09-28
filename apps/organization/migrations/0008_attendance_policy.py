import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('organization', '0007_retention_settings')]
    operations = [
        migrations.AddField(model_name='organization', name='attendance_grace_minutes', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='organization', name='attendance_rounding_minutes', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='organization', name='meal_break_minutes', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='organization', name='overtime_rounding_minutes', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='organization', name='overtime_after_minutes', field=models.PositiveIntegerField(default=0)),
    ]
