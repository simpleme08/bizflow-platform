from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('payroll', '0007_employeesalaryhistory')]

    operations = [
        migrations.AddConstraint(
            model_name='employeesalary',
            constraint=models.CheckConstraint(condition=Q(basic_salary__gte=0), name='employee_salary_non_negative'),
        ),
    ]
