from django.db import migrations, models
import django.db.models.deletion


def backfill_organizations(apps, schema_editor):
    PayrollPeriod = apps.get_model('payroll', 'PayrollPeriod')
    PayrollRecord = apps.get_model('payroll', 'PayrollRecord')

    for period in PayrollPeriod.objects.all().iterator():
        organization_ids = set(
            PayrollRecord.objects.filter(payroll_period_id=period.pk)
            .values_list('employee__organization_id', flat=True)
            .distinct()
        )
        organization_ids.discard(None)
        if len(organization_ids) != 1:
            raise RuntimeError(
                f'Cannot safely assign organization to payroll period {period.pk}: '
                f'found {len(organization_ids)} organizations across its payroll records. '
                'Resolve the data before applying this migration.'
            )
        period.organization_id = organization_ids.pop()
        period.save(update_fields=['organization'])


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0001_initial'),
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollperiod',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='payroll_periods',
                to='organization.organization',
            ),
        ),
        migrations.RunPython(backfill_organizations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='payrollperiod',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='payroll_periods',
                to='organization.organization',
            ),
        ),
        migrations.AddConstraint(
            model_name='payrollperiod',
            constraint=models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
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
