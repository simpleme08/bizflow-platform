import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('payroll', '0009_payrollwagerate')]

    operations = [
        migrations.CreateModel(
            name='EmployeeLoan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('lender', models.CharField(max_length=120)),
                ('loan_type', models.CharField(max_length=80)),
                ('reference_number', models.CharField(blank=True, max_length=80)),
                ('principal', models.DecimalField(decimal_places=2, max_digits=12)),
                ('interest', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('installment_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('balance', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('PAID', 'Paid'), ('SUSPENDED', 'Suspended'), ('CANCELLED', 'Cancelled')], default='ACTIVE', max_length=20)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loans', to='employees.employee')),
            ],
            options={'ordering': ('start_date', 'created_at')},
        ),
        migrations.AddConstraint(model_name='employeeloan', constraint=models.CheckConstraint(condition=Q(principal__gt=0), name='employee_loan_positive_principal')),
        migrations.AddConstraint(model_name='employeeloan', constraint=models.CheckConstraint(condition=Q(interest__gte=0), name='employee_loan_nonnegative_interest')),
        migrations.AddConstraint(model_name='employeeloan', constraint=models.CheckConstraint(condition=Q(installment_amount__gt=0), name='employee_loan_positive_installment')),
        migrations.AddConstraint(model_name='employeeloan', constraint=models.CheckConstraint(condition=Q(balance__gte=0), name='employee_loan_nonnegative_balance')),
        migrations.AddConstraint(model_name='employeeloan', constraint=models.CheckConstraint(condition=Q(end_date__gte=models.F('start_date')), name='employee_loan_valid_dates')),
    ]
