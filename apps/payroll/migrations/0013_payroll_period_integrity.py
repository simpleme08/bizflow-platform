from django.db import migrations, models
from django.db.models import Q


CREATE_CONSTRAINTS_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'payroll_period_valid_dates'
          AND conrelid = 'payroll_payrollperiod'::regclass
    ) THEN
        ALTER TABLE payroll_payrollperiod
        ADD CONSTRAINT payroll_period_valid_dates
        CHECK (end_date >= start_date);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_payroll_period_dates_per_organization'
          AND conrelid = 'payroll_payrollperiod'::regclass
    ) THEN
        ALTER TABLE payroll_payrollperiod
        ADD CONSTRAINT unique_payroll_period_dates_per_organization
        UNIQUE (organization_id, start_date, end_date);
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [('payroll', '0012_payroll_provenance')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(CREATE_CONSTRAINTS_SQL)],
            state_operations=[
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
            ],
        ),
    ]
