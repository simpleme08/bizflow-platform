import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('payroll', '0008_payrollhardening')]

    operations = [
        migrations.AddField(
            model_name='payrollprofile', name='wage_region',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='payrollprofile', name='wage_category',
            field=models.CharField(blank=True, default='NON_AGRICULTURE', max_length=40),
        ),
        migrations.CreateModel(
            name='PayrollWageRate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('region_code', models.CharField(max_length=20)),
                ('category', models.CharField(default='NON_AGRICULTURE', max_length=40)),
                ('daily_rate', models.DecimalField(decimal_places=2, max_digits=10)),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('wage_order', models.CharField(blank=True, max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payroll_wage_rates', to='organization.organization')),
            ],
            options={'ordering': ('-effective_from', '-created_at')},
        ),
        migrations.AddConstraint(
            model_name='payrollwagerate',
            constraint=models.CheckConstraint(condition=Q(daily_rate__gt=0), name='payroll_wage_rate_positive'),
        ),
        migrations.AddConstraint(
            model_name='payrollwagerate',
            constraint=models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gte=models.F('effective_from')), name='payroll_wage_rate_valid_dates'),
        ),
    ]
