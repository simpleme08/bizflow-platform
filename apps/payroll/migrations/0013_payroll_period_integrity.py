from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('payroll', '0012_payroll_provenance')]

    operations = [
        migrations.AddConstraint(
            model_name='payrollperiod',
            constraint=models.CheckConstraint(
                condition=Q(end_date__gte=models.F('start_date')),
                name='payroll_period_valid_dates',
            ),
        ),
        migrations.AddConstraint(
            model_name='payrollperiod',
            constraint=models.UniqueConstraint(
                fields=('organization', 'start_date', 'end_date'),
                name='unique_payroll_period_dates_per_organization',
            ),
        ),
    ]
