from django.db import migrations, models
import apps.core.upload_validation


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0004_employee_master_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeedocument',
            name='file',
            field=models.FileField(
                blank=True,
                upload_to='employee-documents/%Y/%m/',
                validators=[apps.core.upload_validation.validate_private_document],
            ),
        ),
    ]
