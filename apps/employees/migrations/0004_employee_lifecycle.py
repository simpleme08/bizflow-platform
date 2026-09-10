# Generated manually for employee lifecycle management.
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0003_employee_department_employee_employment_type_and_more'),
        ('organization', '0003_costcenter_department_employmenttype_position'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name='employee', name='manager', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='direct_reports', to='employees.employee')),
        migrations.AddField(model_name='employee', name='birth_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='employee', name='sex', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='employee', name='personal_email', field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name='employee', name='work_email', field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name='employee', name='mobile_number', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='employee', name='address', field=models.TextField(blank=True)),
        migrations.AddField(model_name='employee', name='emergency_contact_name', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='employee', name='emergency_contact_phone', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='employee', name='hire_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='employee', name='regularization_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='employee', name='separation_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='employee', name='status', field=models.CharField(choices=[('ONBOARDING','Onboarding'),('PROBATIONARY','Probationary'),('REGULAR','Regular'),('SUSPENDED','Suspended'),('RESIGNED','Resigned'),('TERMINATED','Terminated'),('SEPARATED','Separated')], default='ONBOARDING', max_length=20)),
        migrations.AddIndex(model_name='employee', index=models.Index(fields=['organization','status'], name='employees_e_organiz_9c2e6e_idx')),
        migrations.CreateModel(
            name='EmployeeEmploymentHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(choices=[('ONBOARD','Onboard'),('REGULARIZE','Regularize'),('PROMOTE','Promote'),('TRANSFER','Transfer'),('SUSPEND','Suspend'),('REINSTATE','Reinstate'),('RESIGN','Resign'),('TERMINATE','Terminate'),('SEPARATE','Separate'),('PROFILE_UPDATE','Profile update')], max_length=30)),
                ('effective_date', models.DateField()), ('end_date', models.DateField(blank=True, null=True)), ('status', models.CharField(choices=[('ONBOARDING','Onboarding'),('PROBATIONARY','Probationary'),('REGULAR','Regular'),('SUSPENDED','Suspended'),('RESIGNED','Resigned'),('TERMINATED','Terminated'),('SEPARATED','Separated')], max_length=20)), ('reason', models.CharField(blank=True, max_length=255)), ('notes', models.TextField(blank=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employee_history_actions', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.department')), ('position', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.position')), ('employment_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.employmenttype')), ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employment_history_as_manager', to='employees.employee')), ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employment_history', to='employees.employee')),
            ],
            options={'ordering': ('-effective_date','-created_at')},
        ),
        migrations.AddConstraint(model_name='employeeemploymenthistory', constraint=models.UniqueConstraint(fields=('employee','action','effective_date'), name='uniq_employee_history_action_date')),
        migrations.CreateModel(
            name='EmployeeDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('document_type', models.CharField(choices=[('CONTRACT','Contract'),('GOVERNMENT_ID','Government ID'),('TAX','Tax'),('COMPANY','Company'),('CERTIFICATION','Certification'),('OTHER','Other')], max_length=30)), ('name', models.CharField(max_length=150)), ('reference_number', models.CharField(blank=True, max_length=100)), ('issued_date', models.DateField(blank=True, null=True)), ('expiry_date', models.DateField(blank=True, null=True)), ('file_url', models.URLField(blank=True)), ('notes', models.TextField(blank=True)), ('is_verified', models.BooleanField(default=False)), ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_employee_documents', to=settings.AUTH_USER_MODEL)), ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documents', to='employees.employee')),
            ],
            options={'ordering': ('expiry_date','name')},
        ),
    ]
