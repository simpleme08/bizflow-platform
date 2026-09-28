from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('onboarding', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='onboardingworkflow',
            name='required_document_types',
            field=models.JSONField(blank=True, default=list, help_text='Document type names required before onboarding can be completed.'),
        ),
    ]
