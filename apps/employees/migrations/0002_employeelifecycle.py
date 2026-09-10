from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0001_initial'),
        ('organization', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmploymentHistory',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('ONBOARDING','Onboarding'),('PROBATIONARY','Probationary'),('REGULAR','Regular'),('SUSPENDED','Suspended'),('RESIGNED','Resigned'),('TERMINATED','Terminated'),('SEPARATED','Separated')], max_length=20)),
                ('effective_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='organization.department')),
                ('employment_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='organization.employmenttype')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employment_history', to='employees.employee')),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='managed_employment_history', to='employees.employee')),
                ('position', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='organization.position')),
            ],
            options={'ordering': ('-effective_date', '-created_at')},
        ),
        migrations.AddIndex(model_name='employmenthistory', index=models.Index(fields=['employee', '-effective_date'], name='employment_hist_emp_date_idx')),
        migrations.CreateModel(
            name='EmployeeDocument',
            fields=[
                ('id', models.UUIDField(default=__import__('uuid').uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document_type', models.CharField(max_length=80)),
                ('name', models.CharField(max_length=160)),
                ('file', models.FileField(blank=True, upload_to='employee-documents/%Y/%m/')),
                ('issued_date', models.DateField(blank=True, null=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('is_required', models.BooleanField(default=False)),
                ('status', models.CharField(default='ACTIVE', max_length=20)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documents', to='employees.employee')),
            ],
            options={'ordering': ('expiry_date', 'name')},
        ),
        migrations.AddIndex(model_name='employeedocument', index=models.Index(fields=['employee', 'expiry_date'], name='employee_doc_expiry_idx')),
    ]
