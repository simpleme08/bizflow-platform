from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('payroll', '0010_employeeloan')]

    operations = [
        migrations.AddField(
            model_name='payrolladjustment',
            name='applied',
            field=models.BooleanField(default=False),
        ),
    ]
