from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('payroll', '0009_payrollwagerate')]

    operations = [
        migrations.AddField(
            model_name='payrolladjustment',
            name='applied',
            field=models.BooleanField(default=False),
        ),
    ]
