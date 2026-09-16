from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0013_payroll_period_integrity'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='payrollperiod',
            options={'ordering': ('-end_date', '-start_date')},
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='employee',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='payroll_records',
                to='employees.employee',
            ),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='payroll_period',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='records',
                to='payroll.payrollperiod',
            ),
        ),
    ]
