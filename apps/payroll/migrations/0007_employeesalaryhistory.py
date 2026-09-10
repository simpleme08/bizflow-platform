import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('payroll', '0006_payrollholiday')]

    operations = [
        migrations.CreateModel(
            name='EmployeeSalaryHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('basic_salary', models.DecimalField(decimal_places=2, max_digits=12)),
                ('effective_date', models.DateField()),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salary_history', to='employees.employee')),
            ],
            options={'ordering': ('-effective_date', '-created_at')},
        ),
        migrations.AddConstraint(
            model_name='employeesalaryhistory',
            constraint=models.UniqueConstraint(fields=('employee', 'effective_date'), name='unique_employee_salary_history_date'),
        ),
        migrations.AddConstraint(
            model_name='employeesalaryhistory',
            constraint=models.CheckConstraint(condition=Q(basic_salary__gte=0), name='salary_history_non_negative'),
        ),
    ]
