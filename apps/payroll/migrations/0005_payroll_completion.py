from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('payroll', '0004_payrollrecord_employer_statutory')]
    operations = [
        migrations.AddField(model_name='payrollrecord', name='holiday_pay', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='night_differential', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='allowances', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='commissions', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='bonuses', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='taxable_supplementary', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='thirteenth_month', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='leave_without_pay', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.AddField(model_name='payrollrecord', name='loan_deductions', field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
        migrations.CreateModel(
            name='PayrollAdjustment',
            fields=[
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('EARNING', 'Earning'), ('DEDUCTION', 'Deduction')], max_length=20)),
                ('description', models.CharField(max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('taxable', models.BooleanField(default=True)),
                ('approved', models.BooleanField(default=False)),
                ('payroll_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='adjustments', to='payroll.payrollrecord')),
            ],
        ),
    ]
