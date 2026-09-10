from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0002_employeelifecycle'),
        ('employees', '0003_employee_department_employee_employment_type_and_more'),
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
        migrations.AddIndex(model_name='employee', index=models.Index(fields=['organization','status'], name='employee_org_status_idx')),
    ]
