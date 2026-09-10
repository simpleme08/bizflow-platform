from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('organization', '0004_organization_subscription')]
    operations = [
        migrations.AddConstraint(
            model_name='organization',
            constraint=models.CheckConstraint(condition=models.Q(overage_rate__gte=0), name='organization_overage_rate_nonnegative'),
        ),
    ]
