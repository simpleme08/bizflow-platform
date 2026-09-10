from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0002_payrollperiod_organization'),
    ]

    operations = [
        migrations.CreateModel(
            name='PayrollProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sss_number', models.CharField(blank=True, max_length=20)),
                ('philhealth_number', models.CharField(blank=True, max_length=20)),
                ('pagibig_number', models.CharField(blank=True, max_length=20)),
                ('tin', models.CharField(blank=True, max_length=20)),
                ('minimum_wage_earner', models.BooleanField(default=False)),
                ('employee', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='payroll_profile', to='employees.employee')),
            ],
            options={'abstract': False},
        ),
        migrations.AddField(
            model_name='payrollperiod',
            name='frequency',
            field=models.CharField(choices=[('SEMI_MONTHLY', 'Semi-monthly'), ('MONTHLY', 'Monthly')], default='SEMI_MONTHLY', max_length=20),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='sss_employee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='philhealth_employee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='pagibig_employee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='withholding_tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
