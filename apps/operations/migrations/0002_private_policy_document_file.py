from django.db import migrations, models
import apps.core.upload_validation


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeedocument',
            name='file',
            field=models.FileField(
                blank=True,
                upload_to='organization-documents/%Y/%m/',
                validators=[apps.core.upload_validation.validate_private_document],
            ),
        ),
    ]
