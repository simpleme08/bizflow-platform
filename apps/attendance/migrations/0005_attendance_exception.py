import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('attendance', '0004_split_segments_cover_shift')]
    operations = [
        migrations.CreateModel(
            name='AttendanceException',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=40)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('OPEN','Open'),('RESOLVED','Resolved'),('WAIVED','Waived')], default='OPEN', max_length=20)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('attendance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exceptions', to='attendance.attendancerecord')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='resolved_attendance_exceptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('attendance','code'),name='unique_attendance_exception_code')], 'indexes':[models.Index(fields=('status','created_at'),name='attendance_exception_status_idx')]},
        ),
    ]
