from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0002_clock_photos'),
        ('workforce', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendancerecord',
            name='assignment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attendance_records', to='employees.employeeassignment'),
        ),
        migrations.AddField(
            model_name='attendancerecord',
            name='clock_in_mode',
            field=models.CharField(choices=[('SCHEDULED', 'Scheduled shift'), ('COVER', 'Cover shift'), ('UNSCHEDULED', 'Unscheduled work')], default='SCHEDULED', max_length=20),
        ),
        migrations.AddField(
            model_name='attendancerecord',
            name='clock_shift',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='clock_attendance_records', to='workforce.shifttemplate'),
        ),
    ]
