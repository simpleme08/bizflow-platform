from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('organization', '0003_costcenter_department_employmenttype_position'),
        ('workforce', '0002_client_clientsite_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='shifttemplate',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='shift_templates',
                to='organization.organization',
            ),
        ),
    ]
