from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancerecord',
            name='clock_in_photo',
            field=models.ImageField(blank=True, null=True, upload_to='attendance/proofs/%Y/%m/%d/'),
        ),
        migrations.AddField(
            model_name='attendancerecord',
            name='clock_out_photo',
            field=models.ImageField(blank=True, null=True, upload_to='attendance/proofs/%Y/%m/%d/'),
        ),
    ]
