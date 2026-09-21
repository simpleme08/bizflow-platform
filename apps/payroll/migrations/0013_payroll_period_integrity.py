from django.db import migrations, models
from django.db.models import Q


POSTGRES_CREATE_SQL = """
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

POSTGRES_REVERSE_SQL = """
ALTER TABLE payroll_payrollperiod
    DROP CONSTRAINT IF EXISTS payroll_period_valid_dates;
ALTER TABLE payroll_payrollperiod
    DROP CONSTRAINT IF EXISTS unique_payroll_period_dates_per_organization;
"""

SQLITE_CREATE_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS
    unique_payroll_period_dates_per_organization
    ON payroll_payrollperiod (organization_id, start_date, end_date);

CREATE TRIGGER IF NOT EXISTS payroll_period_valid_dates_insert
BEFORE INSERT ON payroll_payrollperiod
FOR EACH ROW
WHEN NEW.end_date < NEW.start_date
BEGIN
    SELECT RAISE(ABORT, 'payroll_period_valid_dates');
END;

CREATE TRIGGER IF NOT EXISTS payroll_period_valid_dates_update
BEFORE UPDATE OF start_date, end_date ON payroll_payrollperiod
FOR EACH ROW
WHEN NEW.end_date < NEW.start_date
BEGIN
    SELECT RAISE(ABORT, 'payroll_period_valid_dates');
END;
"""

SQLITE_REVERSE_SQL = """
DROP TRIGGER IF EXISTS payroll_period_valid_dates_insert;
DROP TRIGGER IF EXISTS payroll_period_valid_dates_update;
DROP INDEX IF EXISTS unique_payroll_period_dates_per_organization;
"""


def create_database_integrity(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == 'postgresql':
        statements = [POSTGRES_CREATE_SQL]
    elif connection.vendor == 'sqlite':
        statements = [
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            'unique_payroll_period_dates_per_organization '
            'ON payroll_payrollperiod (organization_id, start_date, end_date)',
            'CREATE TRIGGER IF NOT EXISTS payroll_period_valid_dates_insert '
            'BEFORE INSERT ON payroll_payrollperiod FOR EACH ROW '
            'WHEN NEW.end_date < NEW.start_date '
            "BEGIN SELECT RAISE(ABORT, 'payroll_period_valid_dates'); END",
            'CREATE TRIGGER IF NOT EXISTS payroll_period_valid_dates_update '
            'BEFORE UPDATE OF start_date, end_date ON payroll_payrollperiod '
            'FOR EACH ROW WHEN NEW.end_date < NEW.start_date '
            "BEGIN SELECT RAISE(ABORT, 'payroll_period_valid_dates'); END",
        ]
    else:
        raise RuntimeError(
            f"Unsupported database vendor for payroll integrity migration: {connection.vendor}"
        )

    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def remove_database_integrity(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == 'postgresql':
        statements = [POSTGRES_REVERSE_SQL]
    elif connection.vendor == 'sqlite':
        statements = [
            'DROP TRIGGER IF EXISTS payroll_period_valid_dates_insert',
            'DROP TRIGGER IF EXISTS payroll_period_valid_dates_update',
            'DROP INDEX IF EXISTS unique_payroll_period_dates_per_organization',
        ]
    else:
        raise RuntimeError(
            f"Unsupported database vendor for payroll integrity migration: {connection.vendor}"
        )

    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [('payroll', '0012_payroll_provenance')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    create_database_integrity,
                    remove_database_integrity,
                ),
            ],
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
