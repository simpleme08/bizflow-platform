from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('organization', '0003_costcenter_department_employmenttype_position')]

    operations = [
        migrations.AddField(model_name='organization', name='plan_code', field=models.CharField(choices=[('FREE', 'Free'), ('STARTER', 'Starter'), ('GROWTH', 'Growth'), ('BUSINESS', 'Business')], default='FREE', max_length=20)),
        migrations.AddField(model_name='organization', name='subscription_status', field=models.CharField(choices=[('TRIALING', 'Trialing'), ('ACTIVE', 'Active'), ('PAST_DUE', 'Past due'), ('CANCELED', 'Canceled')], default='TRIALING', max_length=20)),
        migrations.AddField(model_name='organization', name='trial_ends_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='organization', name='billing_customer_id', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='organization', name='overage_rate', field=models.DecimalField(decimal_places=2, default=50, max_digits=10)),
    ]
