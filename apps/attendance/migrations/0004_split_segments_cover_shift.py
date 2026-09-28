import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0003_flexible_clocking'),
        ('workforce', '0004_schedule_rule_exception_cover_shift'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancerecord',
            name='segment_number',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='attendancerecord',
            name='cover_shift',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attendance_records', to='workforce.covershift'),
        ),
        migrations.RemoveConstraint(
            model_name='attendancerecord',
            name='unique_employee_attendance_date',
        ),
        migrations.AddConstraint(
            model_name='attendancerecord',
            constraint=models.UniqueConstraint(fields=('employee', 'attendance_date', 'segment_number'), name='unique_employee_attendance_date_segment'),
        ),
    ]
