import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


def seed_baseline_rule_set(apps, schema_editor):
    PayrollRuleSet = apps.get_model('payroll', 'PayrollRuleSet')
    PayrollRuleSet.objects.get_or_create(
        organization=None,
        version='2025-01-baseline',
        defaults={
            'effective_from': '2025-01-01',
            'source_name': 'SSS / PhilHealth / Pag-IBIG / BIR official schedules; DOLE/NWPC wage orders',
            'source_url': 'https://www.sss.gov.ph/',
            'notes': 'Baseline registry entry. Verify all agency rules and regional wage orders before production payroll. This record provides provenance; it does not certify legal compliance.',
            'rules': {
                'sss': {'employee_rate': '0.05', 'employer_rate': '0.10', 'minimum_msc': '5000.00', 'maximum_msc': '35000.00'},
                'philhealth': {'rate': '0.05', 'minimum_base': '10000.00', 'maximum_base': '100000.00'},
                'pagibig': {'employee_rate_low': '0.01', 'employee_rate_high': '0.02', 'employer_rate': '0.02', 'threshold': '1500.00', 'maximum_base': '5000.00'},
                'bir': {'thirteenth_month_exemption': '90000.00'},
                'night_differential': {'rate': '0.10', 'start': '22:00', 'end': '06:00'},
            },
            'is_active': True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0011_payrolladjustment_applied'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PayrollRuleSet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version', models.CharField(max_length=80)),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('source_name', models.CharField(max_length=200)),
                ('source_url', models.URLField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('rules', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payroll_rule_sets', to='organization.organization')),
            ],
            options={'ordering': ('-effective_from', '-created_at')},
        ),
        migrations.AddField(model_name='payrollperiod', name='processed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='processed_payroll_periods', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='payrollperiod', name='approved_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='approved_payroll_periods', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='payrollperiod', name='paid_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='paid_payroll_periods', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='payrollperiod', name='confidence_status', field=models.CharField(choices=[('READY', 'Ready'), ('REVIEW', 'Review'), ('BLOCKED', 'Blocked')], default='REVIEW', max_length=10)),
        migrations.AddField(model_name='payrollperiod', name='confidence_summary', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='payrollperiod', name='rule_set', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payroll_periods', to='payroll.payrollruleset')),
        migrations.AddField(model_name='payrollrecord', name='calculation_rule_version', field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name='payrollrecord', name='calculation_input_hash', field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name='payrollrecord', name='calculation_output_hash', field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name='payrollrecord', name='calculation_snapshot', field=models.JSONField(blank=True, default=dict)),
        migrations.AddConstraint(model_name='payrollruleset', constraint=models.UniqueConstraint(fields=('organization', 'version'), name='unique_payroll_ruleset_org_version')),
        migrations.AddConstraint(model_name='payrollruleset', constraint=models.CheckConstraint(condition=Q(effective_to__isnull=True) | Q(effective_to__gte=models.F('effective_from')), name='payroll_ruleset_valid_dates')),
        migrations.RunPython(seed_baseline_rule_set, migrations.RunPython.noop),
    ]
