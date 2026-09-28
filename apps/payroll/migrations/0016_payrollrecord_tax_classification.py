from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('payroll', '0015_payrollprofile_bank_details')]
    operations = [migrations.AddField(model_name='payrollrecord', name='tax_classification', field=models.JSONField(blank=True, default=dict, help_text='Explicit taxable/non-taxable classification snapshot for payroll components.'))]
