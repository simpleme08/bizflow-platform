from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0003_payrollprofile_statutory'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrecord',
            name='sss_employer',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='philhealth_employer',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='pagibig_employer',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
    ]
