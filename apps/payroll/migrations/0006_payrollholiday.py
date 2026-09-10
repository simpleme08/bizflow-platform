import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('payroll', '0005_payroll_completion')]

    operations = [
        migrations.CreateModel(
            name='PayrollHoliday',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('holiday_date', models.DateField()),
                ('name', models.CharField(max_length=150)),
                ('kind', models.CharField(choices=[('REGULAR', 'Regular holiday'), ('SPECIAL_NON_WORKING', 'Special non-working day'), ('SPECIAL_WORKING', 'Special working day')], max_length=30)),
                ('is_double', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payroll_holidays', to='organization.organization')),
            ],
            options={'ordering': ('holiday_date',)},
        ),
        migrations.AddConstraint(
            model_name='payrollholiday',
            constraint=models.UniqueConstraint(fields=('organization', 'holiday_date'), name='unique_payroll_holiday_per_org_date'),
        ),
    ]
