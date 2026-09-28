from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('payroll', '0014_alter_payrollperiod_options_and_more')]

    operations = [
        migrations.AddField(model_name='payrollprofile', name='bank_name', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='payrollprofile', name='bank_account_name', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='payrollprofile', name='bank_account_number', field=models.CharField(blank=True, max_length=40)),
    ]
