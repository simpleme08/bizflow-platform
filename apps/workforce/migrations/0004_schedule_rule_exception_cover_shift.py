import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('workforce', '0003_shifttemplate_organization'),
        ('organization', '0003_costcenter_department_employmenttype_position'),
        ('employees', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduleRule',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('pattern', models.CharField(choices=[('WEEKLY', 'Weekly'), ('ROTATING', 'Rotating')], default='WEEKLY', max_length=20)),
                ('weekdays', models.JSONField(default=list)),
                ('cycle_weeks', models.PositiveIntegerField(default=1)),
                ('rotation_shifts', models.JSONField(blank=True, default=list, help_text='Ordered shift UUIDs used by rotating cycles.')),
                ('rest_days', models.JSONField(default=list)),
                ('priority', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='schedule_rules', to='employees.employee')),
                ('shift_template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='schedule_rules', to='workforce.shifttemplate')),
            ],
            options={'ordering': ('-priority', '-effective_from', '-created_at'), 'indexes': [models.Index(fields=['employee', 'effective_from'], name='schedule_rule_emp_date_idx')]},
        ),
        migrations.CreateModel(
            name='ScheduleException',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('work_date', models.DateField()),
                ('is_rest_day', models.BooleanField(default=False)),
                ('reason', models.CharField(max_length=255)),
                ('approved', models.BooleanField(default=False)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='approved_schedule_exceptions', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='schedule_exceptions', to='employees.employee')),
                ('shift_template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='schedule_exceptions', to='workforce.shifttemplate')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('employee', 'work_date'), name='unique_schedule_exception_employee_date')]},
        ),
        migrations.CreateModel(
            name='CoverShift',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('work_date', models.DateField()),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=20)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='approved_cover_shifts', to=settings.AUTH_USER_MODEL)),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cover_shifts', to='workforce.client')),
                ('client_site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cover_shifts', to='workforce.clientsite')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cover_shifts', to='employees.employee')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='requested_cover_shifts', to=settings.AUTH_USER_MODEL)),
                ('shift_template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cover_shifts', to='workforce.shifttemplate')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('employee', 'work_date'), name='unique_cover_shift_employee_date')], 'indexes': [models.Index(fields=['employee', 'work_date', 'status'], name='cover_shift_emp_date_status_idx')]},
        ),
    ]
